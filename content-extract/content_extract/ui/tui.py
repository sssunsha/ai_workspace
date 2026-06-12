from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    RichLog,
    Select,
    Static,
    TextArea,
)
from textual import work
from textual.command import Provider, Hit, Hits, DiscoveryHit
from ..cli import _LAUNCH_DIR, get_raw_dir as _get_raw_dir

# TUI 使用启动时锚定的 raw 目录，防止工作目录漂移导致路径嵌套
_RAW_DIR = _get_raw_dir()
_REGISTRY_FILENAME = ".processed.json"
_REGISTRY_PATH = _RAW_DIR / _REGISTRY_FILENAME


# ── 数据模型 ──────────────────────────────────────────────────────────────────

@dataclass
class TaskEntry:
    """内存中的单条任务状态。

    整站爬取聚合为一条（seed_url 是入口 URL，page_count 是已抓页数）。
    单页提取则是一对一。
    """
    source: str        # 入口 URL 或本地路径（seed_url）
    source_type: str
    status: str        # extracting / done / done_partial / failed / needs_transcription
    output_file: str = ""    # 整站时是子目录名；单页时是文件相对路径
    error: str = ""
    extracted_at: str = ""
    page_count: int = 0      # 整站爬取已完成页数；0 表示单页或未知
    total_estimate: int = 0  # 估算目标总数（已完成 + 队列剩余）；0 表示未知或已全部完成


# 状态图标映射
_STATUS_ICONS = {
    "extracting": "⟳",
    "done": "✓",
    "done_partial": "◑",   # 已完成但未全部抓取（到达 limit 上限）
    "failed": "✗",
    "needs_transcription": "⏳",
}

# 输出文件前缀 → 来源类型映射
_PREFIX_TO_TYPE: dict[str, str] = {
    "web__": "web",
    "bili__": "video",
    "dy__": "video",
    "yt__": "video",
    "epub__": "ebook",
    "pdf__": "ebook",
    "code__": "code",
    "docs__": "docs",
    "github__": "code",
    "article__": "article",
    "local__": "local_doc",
}


def _infer_type(output_file: str) -> str:
    """从输出文件路径的前缀推断来源类型。"""
    name = Path(output_file).name if output_file else ""
    for prefix, t in _PREFIX_TO_TYPE.items():
        if name.startswith(prefix):
            return t
    return "—"


# ── 类型自动识别 ──────────────────────────────────────────────────────────────

_VIDEO_DOMAINS = {"bilibili.com", "b23.tv"}


def _netloc(url: str) -> str:
    """提取 URL 的 hostname，用于精确域名匹配，避免子串误判。"""
    from urllib.parse import urlparse
    return urlparse(url).netloc.lower()


def detect_source_type(source: str) -> str:
    """根据 URL 或路径自动识别来源类型。"""
    if not source.startswith(("http://", "https://")):
        return _detect_local_type(source)
    host = _netloc(source)
    if any(host == d or host.endswith("." + d) for d in _VIDEO_DOMAINS):
        return "video"
    if host == "github.com" or host.endswith(".github.com"):
        return "github"
    return "article"


def _detect_local_type(source: str) -> str:
    p = Path(source)
    if p.suffix in {".epub", ".pdf", ".mobi"}:
        return "ebook"
    if p.is_dir():
        return "code" if (p / "package.json").exists() or (p / "pyproject.toml").exists() else "docs"
    return "docs"


def _reset_retryable_failures(reg_path: "Path", reg: "object") -> None:
    """将因 fd 或下载失败的 failed 条目重置为 needs_transcription 以允许重试。"""
    import json

    _RETRYABLE = ("fds_to_keep", "音频下载失败")
    retryable = [
        e for e in reg.get_by_status("failed")
        if any(kw in (e.get("error") or "") for kw in _RETRYABLE)
    ]
    if not retryable:
        return
    data = json.loads(reg_path.read_text(encoding="utf-8"))
    for e in retryable:
        entry = data.get(e["source"])
        if entry:
            entry["status"] = "needs_transcription"
            entry.pop("error", None)
    reg_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def _append_from_needs_file(output_dir: "Path", pending: list) -> None:
    """将 needs_transcription.txt 中不在 pending 里的 URL 追加进去。"""
    needs_file = output_dir / "needs_transcription.txt"
    if not needs_file.exists():
        return
    existing = {e["source"] for e in pending}
    for line in needs_file.read_text(encoding="utf-8").splitlines():
        url = line.strip()
        if url and url not in existing:
            pending.append({"source": url})


def _inject_topic_frontmatter(path: Path, topic: str, topic_role: str) -> None:
    """在已生成的 raw 文件 frontmatter 中追加 topic / topic_role 字段（如尚不存在）。"""
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    # 只检查 frontmatter 区域（第一个 --- 和第二个 --- 之间），避免误判正文内容
    fm_end = text.find("\n---\n", 4)  # 跳过开头的 ---
    if fm_end == -1:
        return
    frontmatter = text[:fm_end]
    if "\ntopic:" in frontmatter or frontmatter.startswith("topic:"):
        return
    insert = f'topic: "{topic}"\n'
    if topic_role:
        insert += f'topic_role: "{topic_role}"\n'
    text = text.replace("---\n\n", f"{insert}---\n\n", 1)
    path.write_text(text, encoding="utf-8")


# ── 消息定义 ──────────────────────────────────────────────────────────────────

class ExtractRequested(Message):
    """用户点击「提取」按钮时发出（单 URL 或整站模式）。"""
    def __init__(self, source: str, source_type: str, update_wiki: bool = False, crawl: bool = False, force: bool = False, extra: dict | None = None) -> None:
        super().__init__()
        self.source = source
        self.source_type = source_type
        self.update_wiki = update_wiki
        self.crawl = crawl
        self.force = force
        self.extra: dict = extra or {}


class ExtractBatchRequested(Message):
    """用户输入多个 URL 时发出，批量抓取到自定义目录。"""
    def __init__(self, urls: list[str], folder_name: str, source_type: str = "web", update_wiki: bool = False) -> None:
        super().__init__()
        self.urls = urls
        self.folder_name = folder_name
        self.source_type = source_type
        self.update_wiki = update_wiki


class TopicAddRequested(Message):
    """Topic 模式下添加资料（在线 URL 或本地文件）到指定 topic。"""
    def __init__(
        self,
        sources: list[str],
        topic: str,
        topic_role: str = "",
        source_type: str = "auto",
        update_wiki: bool = False,
    ) -> None:
        super().__init__()
        self.sources = sources
        self.topic = topic
        self.topic_role = topic_role
        self.source_type = source_type
        self.update_wiki = update_wiki


class ExtractDone(Message):
    """worker 线程提取完成后发出。"""
    def __init__(self, source: str, success: bool, output_file: str = "", error: str = "") -> None:
        super().__init__()
        self.source = source
        self.success = success
        self.output_file = output_file
        self.error = error


# ── 重复来源确认弹窗 ──────────────────────────────────────────────────────────

class DuplicateModal(ModalScreen[str]):
    """检测到来源已存在时弹出，让用户选择操作。"""

    DEFAULT_CSS = """
    DuplicateModal { align: center middle; }
    DuplicateModal > Vertical {
        background: $surface;
        border: thick $warning;
        padding: 2 4;
        width: 76;
        height: auto;
    }
    DuplicateModal Label { margin-bottom: 1; }
    DuplicateModal Horizontal {
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    DuplicateModal Button {
        margin: 0 1;
        min-width: 16;
    }
    """

    def __init__(self, source: str, status: str, extracted_at: str, file_count: int = 0) -> None:
        super().__init__()
        self._source = source
        self._status = status
        self._extracted_at = extracted_at
        self._file_count = file_count

    def compose(self) -> ComposeResult:
        status_text = {
            "done": "✓ 全部完成",
            "done_partial": "◑ 部分完成（曾到达页数上限）",
            "needs_transcription": "⏳ 待转录",
            "failed": "✗ 失败",
        }.get(self._status, self._status)

        info_lines = [
            f"[bold]{self._source[:68]}[/bold]",
            f"状态：{status_text}",
            f"时间：{self._extracted_at[:10] or '未知'}",
        ]
        if self._file_count > 0:
            info_lines.append(f"已抓：{self._file_count} 篇" + (
                "（未全部完成，继续抓取可获取更多）" if self._file_count >= 190 else ""
            ))

        with Vertical():
            yield Label("来源已存在")
            yield Label("\n".join(info_lines))
            with Horizontal():
                yield Button("继续抓取", id="btn-resume", variant="primary")
                yield Button("强制重新获取", id="btn-force", variant="warning")
                yield Button("放弃", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id)


# ── 记录操作弹窗 ──────────────────────────────────────────────────────────────

class RecordActionModal(ModalScreen[str]):
    """对已有记录执行操作：清空数据、继续抓取或强制更新。"""

    DEFAULT_CSS = """
    RecordActionModal { align: center middle; }
    RecordActionModal > Vertical {
        background: $surface;
        border: thick $secondary;
        padding: 2 4;
        width: 76;
        height: auto;
    }
    RecordActionModal Label { margin-bottom: 1; }
    RecordActionModal Horizontal {
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    RecordActionModal Button {
        margin: 0 1;
        min-width: 14;
    }
    """

    def __init__(self, task: "TaskEntry") -> None:
        super().__init__()
        self._task = task

    def compose(self) -> ComposeResult:
        t = self._task
        # 状态中文映射
        status_label = {
            "done": "✓ 全部完成",
            "done_partial": "◑ 部分完成",
            "failed": "✗ 失败",
            "needs_transcription": "⏳ 待转录",
            "extracting": "⟳ 抓取中",
        }.get(t.status, t.status)

        progress_str = ""
        if t.total_estimate > 0:
            progress_str = f"  进度：{t.page_count}/{t.total_estimate}"
        elif t.page_count > 0:
            progress_str = f"  已抓：{t.page_count} 篇"

        with Vertical():
            yield Label("记录操作")
            yield Label(
                f"[bold]{(t.output_file or t.source)[:68]}[/bold]\n"
                f"类型：{t.source_type or '—'}  状态：{status_label}{progress_str}"
            )
            # 第一行：操作按钮
            with Horizontal():
                yield Button("继续抓取", id="btn-resume", variant="primary")
                yield Button("强制更新", id="btn-force", variant="warning")
                yield Button("清空记录", id="btn-clear", variant="error")
            # video 类型额外显示手动转录按钮
            if t.source_type and "video" in t.source_type:
                with Horizontal():
                    yield Button("手动转录", id="btn-transcribe", variant="success")
            # 第二行：取消按钮单独一行，居中
            with Horizontal():
                yield Button("取消", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id)

class WikiModal(ModalScreen):
    """Wiki 更新功能占位弹窗，Skill 实现后替换为实际逻辑。"""

    DEFAULT_CSS = """
    WikiModal {
        align: center middle;
    }
    WikiModal > Vertical {
        background: $surface;
        border: thick $primary;
        padding: 2 4;
        width: 60;
        height: auto;
    }
    WikiModal Label {
        text-align: center;
        margin-bottom: 1;
    }
    WikiModal Horizontal {
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    WikiModal Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Wiki 更新功能")
            yield Label("Wiki 更新功能将在 Claude Code Skill 实现后可用。\n届时将自动调用 claude 命令整理 ./raw/ 内容到 ./wiki/。")
            with Horizontal():
                yield Button("知道了", id="btn-wiki-ok", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()


# ── 添加来源面板 ──────────────────────────────────────────────────────────────

class AddSourcePanel(Static):
    """左侧输入面板：支持单 URL 或多 URL 批量输入，以及 Topic 学习模式。"""

    # 支持批量输入的类型（auto 根据 URL 自动判断）
    _BATCH_SUPPORTED = frozenset({"auto", "web", "video", "article", "docs"})

    # 组件 ID 常量
    _ID_TEXTAREA    = "url-textarea"
    _ID_TYPE_SELECT = "type-select"
    _ID_BATCH_HINT  = "batch-hint"
    _ID_FOLDER_HINT = "folder-hint"
    _ID_FOLDER_INPUT = "folder-input"
    _ID_TOPIC_CHECKBOX = "topic-mode-checkbox"
    _ID_TOPIC_INPUT = "topic-name-input"
    _ID_TOPIC_ROLE_SELECT = "topic-role-select"
    _ID_TOPIC_ROW = "topic-row"
    _ID_TOPIC_HINT = "topic-name-hint"
    _ID_CRAWL_CHECKBOX = "crawl-checkbox"

    DEFAULT_CSS = """
    AddSourcePanel {
        width: 60%;
        height: auto;
        border: round $primary;
        padding: 1 2;
    }
    AddSourcePanel Label { margin-bottom: 0; }
    AddSourcePanel #textarea-row {
        height: 5;
        margin-bottom: 1;
    }
    AddSourcePanel #textarea-row TextArea {
        width: 1fr;
        height: 100%;
        margin-bottom: 0;
    }
    AddSourcePanel #btn-browse {
        width: auto;
        min-width: 8;
        display: none;
        margin-left: 1;
    }
    AddSourcePanel #btn-browse.visible { display: block; }
    AddSourcePanel Input { margin-bottom: 1; }
    AddSourcePanel Select { margin-bottom: 1; }
    AddSourcePanel Checkbox { margin-bottom: 1; }
    AddSourcePanel #folder-row { height: auto; margin-bottom: 1; }
    AddSourcePanel #folder-label { width: auto; margin-right: 1; padding-top: 1; }
    AddSourcePanel #folder-input { width: 1fr; }
    AddSourcePanel #folder-hint { color: $error; display: none; }
    AddSourcePanel #folder-hint.visible { display: block; }
    AddSourcePanel #batch-hint { color: $warning; display: none; margin-bottom: 1; }
    AddSourcePanel #batch-hint.visible { display: block; }
    AddSourcePanel #code-mode-row { display: none; height: auto; margin-bottom: 1; }
    AddSourcePanel #code-mode-row.visible { display: block; }
    AddSourcePanel #topic-row { display: none; height: auto; margin-bottom: 1; }
    AddSourcePanel #topic-row.visible { display: block; }
    AddSourcePanel #topic-name-hint { color: $error; display: none; }
    AddSourcePanel #topic-name-hint.visible { display: block; }
    AddSourcePanel Horizontal { height: auto; }
    AddSourcePanel Button { margin-right: 1; }
    """

    # 类型下拉选项
    _TYPE_OPTIONS = [
        ("自动识别", "auto"),
        ("web 网页（整站/单页）", "web"),
        ("video 视频（Bilibili）", "video"),
        ("article 文章（微信/头条/知乎/通用）", "article"),
        ("docs 本地文档", "docs"),
        ("ebook 电子书（不支持批量）", "ebook"),
        ("code 本地代码工程（不支持批量）", "code"),
        ("local 本地文件（Topic 模式）", "local"),
    ]

    _CODE_MODE_OPTIONS = [
        ("overview — 概览（目录树 + 配置 + git 信息）", "overview"),
        ("priority — 优先级（+ 测试 / 类型定义 / 入口文件）", "priority"),
        ("full — 全量（所有文本文件，增量跳过已处理）", "full"),
    ]

    _TOPIC_ROLE_OPTIONS = [
        ("不指定", ""),
        ("入门概述", "入门概述"),
        ("核心方法论", "核心方法论"),
        ("深度参考", "深度参考"),
        ("代码实例", "代码实例"),
        ("案例研究", "案例研究"),
        ("工具介绍", "工具介绍"),
        ("个人笔记", "个人笔记"),
    ]

    def compose(self) -> ComposeResult:
        yield Label("URL / 路径（多个用逗号、分号或换行分隔）：")
        with Horizontal(id="textarea-row"):
            yield TextArea(id=self._ID_TEXTAREA, language=None)
            yield Button("📂 浏览", id="btn-browse")
        yield Label("来源类型：")
        yield Select(options=self._TYPE_OPTIONS, value="auto", id=self._ID_TYPE_SELECT)
        yield Label("ℹ ebook / code / local 不支持批量输入，请单条使用", id=self._ID_BATCH_HINT)
        yield Checkbox("整站爬取（web 类型单 URL 时生效）", value=True, id=self._ID_CRAWL_CHECKBOX)
        with Static(id="code-mode-row"):
            yield Label("提取深度：")
            yield Select(options=self._CODE_MODE_OPTIONS, value="overview", id="code-mode-select")
        # Topic 模式专用字段（local 类型时显示，其他类型通过 Checkbox 激活）
        yield Checkbox("Topic 学习模式（将资料归入指定主题）", value=False, id=self._ID_TOPIC_CHECKBOX)
        with Static(id=self._ID_TOPIC_ROW):
            with Horizontal():
                yield Label("主题名：", id="topic-label")
                yield Input(placeholder="如：量化投资入门", id=self._ID_TOPIC_INPUT)
            yield Label("主题角色：")
            yield Select(options=self._TOPIC_ROLE_OPTIONS, value="", id=self._ID_TOPIC_ROLE_SELECT)
        yield Label("⚠ 请填写 Topic 主题名", id=self._ID_TOPIC_HINT)
        with Horizontal(id="folder-row"):
            yield Label("保存目录名：", id="folder-label")
            yield Input(placeholder="自定义（多 URL 时必填）", id=self._ID_FOLDER_INPUT)
        yield Label("⚠ 多 URL 批量模式下目录名为必填项", id=self._ID_FOLDER_HINT)
        with Horizontal():
            yield Button("提取", id="btn-extract", variant="primary")
            yield Button("提取并更新 Wiki", id="btn-extract-wiki")

    def _parse_urls(self, text: str) -> list[str]:
        from ..extractors.web import parse_urls
        return parse_urls(text)

    def _is_batch_mode(self) -> bool:
        """当前类型支持批量且已输入多个 URL。"""
        raw_type = str(self.query_one(f"#{self._ID_TYPE_SELECT}", Select).value)
        if raw_type not in self._BATCH_SUPPORTED:
            return False
        return len(self._parse_urls(self.query_one(f"#{self._ID_TEXTAREA}", TextArea).text)) > 1

    def _is_topic_mode(self) -> bool:
        return bool(self.query_one(f"#{self._ID_TOPIC_CHECKBOX}", Checkbox).value)

    def _set_hint_visibility(self, batch: bool, folder: bool) -> None:
        """统一控制两个提示 Label 的显示/隐藏。"""
        bh = self.query_one(f"#{self._ID_BATCH_HINT}", Label)
        fh = self.query_one(f"#{self._ID_FOLDER_HINT}", Label)
        bh.add_class("visible") if batch else bh.remove_class("visible")
        fh.add_class("visible") if folder else fh.remove_class("visible")

    def _update_topic_row_visibility(self) -> None:
        """根据 Topic 模式开关控制 topic 行显示。"""
        topic_row = self.query_one(f"#{self._ID_TOPIC_ROW}", Static)
        if self._is_topic_mode():
            topic_row.add_class("visible")
        else:
            topic_row.remove_class("visible")
            self.query_one(f"#{self._ID_TOPIC_HINT}", Label).remove_class("visible")

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == self._ID_TOPIC_CHECKBOX:
            self._update_topic_row_visibility()
            # 开启 Topic 模式时隐藏整站爬取选项
            cb = self.query_one(f"#{self._ID_CRAWL_CHECKBOX}", Checkbox)
            cb.display = not self._is_topic_mode()

    def on_select_changed(self, event: Select.Changed) -> None:
        """类型切换时更新批量提示、crawl checkbox 和 code 模式选择器可见性。"""
        if event.select.id != self._ID_TYPE_SELECT:
            return
        val = str(event.value)
        not_supported = val not in self._BATCH_SUPPORTED
        if not_supported:
            self._set_hint_visibility(batch=True, folder=False)
        else:
            self._set_hint_visibility(batch=False, folder=self._is_batch_mode())

        cb = self.query_one(f"#{self._ID_CRAWL_CHECKBOX}", Checkbox)
        mode_row = self.query_one("#code-mode-row", Static)
        browse_btn = self.query_one("#btn-browse", Button)
        topic_cb = self.query_one(f"#{self._ID_TOPIC_CHECKBOX}", Checkbox)

        if val == "code":
            cb.display = False
            mode_row.add_class("visible")
            browse_btn.remove_class("visible")
            topic_cb.display = False
        elif val == "ebook":
            cb.display = False
            mode_row.remove_class("visible")
            browse_btn.add_class("visible")
            topic_cb.display = True
        elif val == "local":
            cb.display = False
            mode_row.remove_class("visible")
            browse_btn.add_class("visible")
            # local 类型自动开启 Topic 模式
            topic_cb.value = True
            topic_cb.display = False
            self._update_topic_row_visibility()
        else:
            cb.display = not self._is_topic_mode()
            mode_row.remove_class("visible")
            browse_btn.remove_class("visible")
            topic_cb.display = True

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """输入变化时更新多 URL 提示。"""
        if event.text_area.id != self._ID_TEXTAREA:
            return
        raw_type = str(self.query_one(f"#{self._ID_TYPE_SELECT}", Select).value)
        is_multi = len(self._parse_urls(event.text_area.text)) > 1
        not_supported = raw_type not in self._BATCH_SUPPORTED
        self._set_hint_visibility(
            batch=(not_supported and is_multi),
            folder=(is_multi and not not_supported and not self._is_topic_mode()),
        )

    def _read_extra(self, raw_type: str) -> dict:
        """读取当前类型附加参数（如 code 模式）。"""
        if raw_type == "code":
            mode_select = self.query_one("#code-mode-select", Select)
            return {"code_mode": str(mode_select.value)}
        return {}

    def _emit_single(self, source: str, raw_type: str, update_wiki: bool,
                     crawl: bool, extra: dict) -> None:
        source_type = detect_source_type(source) if raw_type == "auto" else raw_type
        self.post_message(ExtractRequested(
            source=source, source_type=source_type,
            update_wiki=update_wiki, crawl=crawl, extra=extra,
        ))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-browse":
            self._open_file_picker()
            return
        if event.button.id not in ("btn-extract", "btn-extract-wiki"):
            return
        textarea = self.query_one(f"#{self._ID_TEXTAREA}", TextArea)
        text = textarea.text.strip()
        if not text:
            return
        raw_type = str(self.query_one(f"#{self._ID_TYPE_SELECT}", Select).value)
        update_wiki = event.button.id == "btn-extract-wiki"
        urls = self._parse_urls(text)
        if self._is_topic_mode() or raw_type == "local":
            if self._emit_topic(urls or [text], raw_type, update_wiki):
                textarea.clear()
            return
        self._emit_standard(urls, text, raw_type, update_wiki)
        textarea.clear()

    def _emit_topic(self, sources: list[str], raw_type: str, update_wiki: bool) -> bool:
        """Topic 模式提交：校验 topic 名，发送 TopicAddRequested。返回是否成功。"""
        topic_name = self.query_one(f"#{self._ID_TOPIC_INPUT}", Input).value.strip()
        hint = self.query_one(f"#{self._ID_TOPIC_HINT}", Label)
        if not topic_name:
            hint.add_class("visible")
            return False
        hint.remove_class("visible")
        topic_role_val = self.query_one(f"#{self._ID_TOPIC_ROLE_SELECT}", Select).value
        topic_role = str(topic_role_val) if topic_role_val else ""
        self.post_message(TopicAddRequested(
            sources=sources,
            topic=topic_name,
            topic_role=topic_role,
            source_type=raw_type if raw_type != "auto" else "auto",
            update_wiki=update_wiki,
        ))
        return True

    def _emit_standard(self, urls: list[str], text: str, raw_type: str, update_wiki: bool) -> None:
        """标准模式提交：单条或批量，发送对应消息。"""
        folder_input = self.query_one(f"#{self._ID_FOLDER_INPUT}", Input)
        crawl_checkbox = self.query_one(f"#{self._ID_CRAWL_CHECKBOX}", Checkbox)
        folder_name = folder_input.value.strip()
        is_multi = len(urls) > 1
        extra = self._read_extra(raw_type)
        if raw_type not in self._BATCH_SUPPORTED:
            self._emit_single(urls[0] if urls else text, raw_type, update_wiki, False, extra)
            return
        if is_multi:
            if not folder_name:
                self.query_one("#folder-hint", Label).add_class("visible")
                return
            source_type = raw_type if raw_type != "auto" else "web"
            self.post_message(ExtractBatchRequested(
                urls=urls, folder_name=folder_name,
                source_type=source_type, update_wiki=update_wiki,
            ))
        else:
            self._emit_single(
                urls[0] if urls else text, raw_type, update_wiki,
                bool(crawl_checkbox.value), extra,
            )
        folder_input.value = ""
        folder_input.value = ""

    def _open_file_picker(self) -> None:
        """在独立子进程里用 tkinter 文件对话框选择文件，结果填入 TextArea。

        local 类型时支持 md/html/txt，ebook 类型支持 epub/pdf。
        用子进程而非线程，避免 tkinter 和 Textual 的 event loop 冲突。
        """
        import threading
        import sys

        raw_type = str(self.query_one(f"#{self._ID_TYPE_SELECT}", Select).value)
        is_local = raw_type == "local" or self._is_topic_mode()

        if is_local:
            filetypes = (
                "('本地文档', '*.md *.html *.htm *.txt'),"
                "('Markdown', '*.md'),"
                "('HTML', '*.html *.htm'),"
                "('文本', '*.txt'),"
                "('所有文件', '*.*'),"
            )
            title = "选择本地文档文件"
        else:
            filetypes = (
                "('电子书', '*.epub *.pdf *.mobi *.azw3 *.azw'),"
                "('EPUB', '*.epub'),"
                "('PDF', '*.pdf'),"
                "('所有文件', '*.*'),"
            )
            title = "选择电子书文件"

        # tkinter 脚本：选文件后把路径用换行分隔打印到 stdout
        _PICKER_SCRIPT = (
            "import sys, tkinter as tk\n"
            "from tkinter import filedialog\n"
            "root = tk.Tk()\n"
            "root.withdraw()\n"
            "root.call('wm', 'attributes', '.', '-topmost', True)\n"
            f"files = filedialog.askopenfilenames(\n"
            f"    title={title!r},\n"
            f"    filetypes=[{filetypes}],\n"
            ")\n"
            "if files:\n"
            "    print('\\n'.join(files))\n"
        )

        def _pick() -> None:
            try:
                result = subprocess.run(
                    [sys.executable, "-c", _PICKER_SCRIPT],
                    capture_output=True, text=True, timeout=120,
                )
                output = result.stdout.strip()
                if not output:
                    return
                paths = [p.strip() for p in output.splitlines() if p.strip()]
                if paths:
                    self.app.call_from_thread(self._fill_paths, paths)
            except Exception as e:
                self.app.call_from_thread(
                    self.app.log_message, f"[yellow]文件选择器错误：{e}[/yellow]"
                )

        threading.Thread(target=_pick, daemon=True).start()

    def _fill_paths(self, paths: list[str]) -> None:
        """将路径列表填入 TextArea（主线程调用）。"""
        textarea = self.query_one(f"#{self._ID_TEXTAREA}", TextArea)
        textarea.clear()
        textarea.insert("\n".join(paths))




# ── 处理队列面板 ──────────────────────────────────────────────────────────────

class QueuePanel(Static):
    """右侧队列面板：展示所有任务的状态和统计摘要。"""

    DEFAULT_CSS = """
    QueuePanel {
        width: 40%;
        height: auto;
        border: round $secondary;
        padding: 1;
    }
    QueuePanel DataTable {
        height: 10;
    }
    #queue-summary {
        margin-top: 1;
        color: $text-muted;
    }
    """

    def compose(self) -> ComposeResult:
        table = DataTable(id="queue-table", zebra_stripes=True, cursor_type="row")
        table.add_columns("状态", "类型", "名称", "进度", "时间")
        yield table
        yield Label("双击来源行可在 Finder 中打开对应目录", id="queue-tip")
        yield Label("", id="queue-summary")

    @staticmethod
    def _progress_str(t: "TaskEntry") -> str:
        if t.total_estimate > 0:
            return f"{t.page_count}/{t.total_estimate}"
        if t.page_count > 0:
            return f"{t.page_count}/?"
        return "—"

    def _task_name_str(self, t: "TaskEntry") -> str:
        """返回队列表格「名称」列的显示文字。"""
        target_dir = self._resolve_target_dir(t)
        if target_dir != self._raw_dir and target_dir.is_dir():
            return target_dir.name
        fallback = t.output_file or t.source
        return fallback[-45:] if len(fallback) > 45 else fallback

    def refresh_table(self, tasks: list[TaskEntry]) -> None:
        """清空并重绘队列表格，同时更新底部统计摘要。"""
        self._tasks = tasks
        table = self.query_one("#queue-table", DataTable)
        table.clear()
        for t in tasks:
            icon = _STATUS_ICONS.get(t.status, "?")
            type_str = f"{t.source_type}({t.page_count})" if t.page_count > 1 else (t.source_type or "—")
            time_short = t.extracted_at[:10] if t.extracted_at else "—"
            table.add_row(icon, type_str, self._task_name_str(t), self._progress_str(t), time_short)
        self.query_one("#queue-summary", Label).update(self._build_summary(tasks))

    @staticmethod
    def _build_summary(tasks: list[TaskEntry]) -> str:
        """根据任务列表生成底部统计摘要文字。"""
        if not tasks:
            return "暂无记录"

        counts = {"done": 0, "failed": 0, "needs_transcription": 0, "extracting": 0}
        type_counts: dict[str, int] = {}
        for t in tasks:
            counts[t.status] = counts.get(t.status, 0) + 1
            if t.source_type and t.source_type != "—":
                type_counts[t.source_type] = type_counts.get(t.source_type, 0) + 1

        icon_map = {"done": "✓", "done_partial": "◑", "extracting": "⟳", "needs_transcription": "⏳", "failed": "✗"}
        parts = [f"共 {len(tasks)} 条"] + [
            f"{icon_map[k]}{v}" for k, v in icon_map.items() if counts.get(k)
        ]
        status_str = "  ".join(parts)
        type_str = "  ".join(f"{k}:{v}" for k, v in sorted(type_counts.items()))
        return f"{status_str}\n{type_str}" if type_str else status_str

    def __init__(self) -> None:
        super().__init__()
        self._tasks: list[TaskEntry] = []

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """双击或 Enter 选中行时，在 Finder 中打开对应目录。"""
        row = event.cursor_row
        if row < 0 or row >= len(self._tasks):
            return
        task = self._tasks[row]
        self._open_in_finder(task)

    def _open_in_finder(self, task: TaskEntry) -> None:
        """根据 task.output_file 推断目录路径并用 Finder 打开。"""
        target = self._resolve_target_dir(task)
        import subprocess
        subprocess.Popen(["open", str(target)])

    @property
    def _raw_dir(self) -> Path:
        """从 TUIApp 读取当前 raw 目录，不可用时回退模块级默认值。"""
        try:
            return self.app._raw_dir  # type: ignore[attr-defined]
        except Exception:
            return _RAW_DIR

    def _resolve_target_dir(self, task: TaskEntry) -> Path:
        """从 TaskEntry 推断要打开的目录，找不到则回退到 raw 根目录。"""
        output_file = task.output_file or ""
        if output_file:
            return self._dir_from_output_file(output_file)
        if not task.source.startswith("batch::"):
            candidate = self._dir_from_source_url(task.source)
            if candidate is not None:
                return candidate
        return self._raw_dir

    def _dir_from_output_file(self, output_file: str) -> Path:
        """从 output_file 字段（subfolder/file.md）推断子目录。"""
        raw = self._raw_dir
        subfolder = output_file.split("/")[0]
        candidate = raw / subfolder
        if candidate.is_dir():
            return candidate
        full = raw / output_file
        if full.exists():
            return full.parent
        return raw

    def _dir_from_source_url(self, source: str) -> Path | None:
        """从 source URL 推断子目录名，不存在则返回 None。"""
        try:
            from ..extractors.web import _url_to_subfolder
            candidate = self._raw_dir / _url_to_subfolder(source)
            return candidate if candidate.is_dir() else None
        except Exception:
            return None


# ── 实时日志面板 ──────────────────────────────────────────────────────────────

class LogPanel(Static):
    """下方日志面板：实时显示提取进度。"""

    DEFAULT_CSS = """
    LogPanel {
        width: 100%;
        height: 12;
        border: round $accent;
        padding: 0 1;
    }
    LogPanel RichLog {
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        yield RichLog(id="log", highlight=True, markup=True, auto_scroll=True)

    def write(self, msg: str) -> None:
        """追加带时间戳的日志行。"""
        ts = datetime.now().strftime("%H:%M:%S")
        log = self.query_one("#log", RichLog)
        log.write(f"[dim]{ts}[/dim] {msg}")


# ── 抓取总数确认弹窗 ──────────────────────────────────────────────────────────

class LimitChoiceModal(ModalScreen[int]):
    """发现网站总 URL 数超过当前 limit 时弹出，让用户选择抓取策略。"""

    DEFAULT_CSS = """
    LimitChoiceModal { align: center middle; }
    LimitChoiceModal > Vertical {
        background: $surface;
        border: thick $accent;
        padding: 2 4;
        width: 76;
        height: auto;
    }
    LimitChoiceModal Label { margin-bottom: 1; }
    LimitChoiceModal Horizontal {
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    LimitChoiceModal Button { margin: 0 1; min-width: 18; }
    """

    def __init__(self, total: int, already: int, remaining: int, current_limit: int) -> None:
        super().__init__()
        self._total = total
        self._already = already
        self._remaining = remaining
        self._current_limit = current_limit

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("发现网站总资源数")
            yield Label(
                f"共发现 [bold]{self._total}[/bold] 个页面\n"
                f"已抓取：{self._already}  待抓取：{self._remaining}\n"
                f"当前每次上限：{self._current_limit} 页"
            )
            with Horizontal():
                yield Button(f"一次全部抓取（{self._remaining} 页）", id="btn-all", variant="primary")
                yield Button(f"沿用上限（{self._current_limit} 页）", id="btn-keep")
                yield Button("取消", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-all":
            self.dismiss(self._total)   # 返回全量数作为新 limit
        elif event.button.id == "btn-keep":
            self.dismiss(self._current_limit)
        else:
            self.dismiss(0)  # 0 = 取消（不改变 limit）


# ── 命令面板（Ctrl+P）─────────────────────────────────────────────────────────

class AppCommands(Provider):
    """为命令面板提供所有可执行操作，按分组排列。"""

    # (显示名称, 帮助文字, action方法名)
    _COMMANDS = [
        ("提取：继续抓取选中记录",  "对队列中选中行执行「继续/强制/清空」操作",  "record_action"),
        ("提取：重试失败任务",       "重试第一个状态为 failed 的任务",            "retry_failed"),
        ("日志：清空日志面板",       "清除日志区所有内容",                        "clear_log"),
        ("工具：打开 Obsidian",      "macOS 打开 wiki/ 目录作为 Obsidian vault", "open_obsidian"),
        ("帮助：显示操作手册",       "查看所有功能说明、快捷键和 CLI 命令",       "show_help"),
        ("退出应用",                 "关闭 Content Extract（同 Q / Esc）",        "quit"),
    ]

    def _make_callback(self, action: str):
        """生成调用 TUIApp action 的回调。"""
        app = self.app
        action_map = {
            "record_action":  lambda: app.action_record_action(),
            "retry_failed":   lambda: app.action_retry_failed(),
            "clear_log":      lambda: app.action_clear_log(),
            "open_obsidian":  lambda: app.action_open_obsidian(),
            "show_help":      lambda: app.action_show_help(),
            "quit":           lambda: app.action_quit(),
        }
        return action_map.get(action, lambda: None)

    async def discover(self) -> Hits:
        """面板打开时（空查询）展示全部命令。"""
        for name, help_text, action in self._COMMANDS:
            yield DiscoveryHit(
                display=name,
                command=self._make_callback(action),
                text=name,
                help=help_text,
            )

    async def search(self, query: str) -> Hits:
        """有输入时进行模糊匹配。"""
        matcher = self.matcher(query)
        for name, help_text, action in self._COMMANDS:
            score = matcher.match(name)
            if score > 0:
                yield Hit(
                    score=score,
                    match_display=matcher.highlight(name),
                    command=self._make_callback(action),
                    text=name,
                    help=help_text,
                )


# ── 帮助弹窗 ──────────────────────────────────────────────────────────────────

class HelpModal(ModalScreen):
    """操作说明弹窗：分类展示所有功能和快捷键。"""

    DEFAULT_CSS = """
    HelpModal {
        align: center middle;
        padding: 1 2;
    }
    HelpModal > Vertical {
        background: $surface;
        border: thick $primary;
        padding: 1 3;
        width: 100%;
        height: 100%;
    }
    HelpModal #help-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    HelpModal RichLog {
        height: 1fr;
        border: none;
        padding: 0;
    }
    HelpModal Horizontal {
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    """

    _CONTENT = """\
[bold yellow]━━ 提取来源 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold yellow]
  输入 URL 或本地路径，选择来源类型后点击按钮：
  [bold]提取[/bold]            抓取内容到 ./raw/ 目录，断点续传自动跳过已有页面
  [bold]提取并更新 Wiki[/bold]  完成后弹出 Wiki 更新提示（功能待 Skill 实现）
  [bold]来源类型[/bold]         自动识别 / web / video / ebook / code / docs / github / article
  [bold]整站爬取[/bold]         勾选后对 web 类型执行 BFS 整站爬取（默认 limit=200）

[bold yellow]━━ 状态图标说明 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold yellow]
  [green]✓[/green]  done              全部完成（队列已耗尽）
  [yellow]◑[/yellow]  done_partial      部分完成（到达页数上限，仍有未抓内容）
  [cyan]⟳[/cyan]  extracting        正在抓取中
  [red]✗[/red]  failed            抓取失败（可按 [bold]R[/bold] 重试）
  [dim]⏳[/dim]  needs_transcription 视频无字幕，等待 Whisper 转录

[bold yellow]━━ 进度列格式 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold yellow]
  [bold]200/1579[/bold]   已抓 200 篇，估算目标 1579（来自中止时队列剩余数）
  [bold]97/?[/bold]       已抓 97 篇，目标总数未知（旧记录）
  [bold]—[/bold]          单页提取或无法统计

[bold yellow]━━ 快捷键 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold yellow]
  [bold]Ctrl+P[/bold]  打开命令面板（菜单），可搜索所有操作
  [bold]A[/bold]      对队列中选中的记录执行操作（继续抓取 / 强制更新 / 清空记录）
  [bold]R[/bold]      重试第一个失败的任务
  [bold]C[/bold]      清空日志面板
  [bold]O[/bold]      打开 Obsidian（macOS，打开 wiki/ 目录作为 vault）
  [bold]?[/bold]      显示本帮助
  [bold]Q[/bold]      直接退出
  [bold]Esc[/bold]    关闭当前对话框；主界面双击 Esc 退出

[bold yellow]━━ 记录操作（选中行后按 A）━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold yellow]
  [bold]继续抓取[/bold]    从上次断点继续，已有文件自动跳过
  [bold]强制更新[/bold]    忽略已有记录，重新下载覆盖所有文件
  [bold]清空记录[/bold]    从队列和 .processed.json 中彻底删除该任务

[bold yellow]━━ 重复来源检测 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold yellow]
  提交已存在的 URL 时自动弹窗：
  • failed / needs_transcription 状态 → 直接继续，无需确认
  • done_partial（未抓完）→ 弹窗，默认选「继续抓取」
  • done（全部完成）→ 弹窗，需选「继续」或「强制更新」或「放弃」

[bold yellow]━━ 文件存储位置 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold yellow]
  raw/                       所有提取结果的根目录
  raw/{site}/                每个网站独立子目录（如 feelgoodpal-com__zh__blog/）
  raw/.processed.json        统一记录文件（状态、进度、时间戳）
  wiki/                      Claude Code 整理后的结构化知识库（需手动触发）

[bold yellow]━━ CLI 命令（e 是快捷别名）━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold yellow]
  [bold]e web <url> --crawl --limit 500[/bold]    整站爬取，最多 500 页
  [bold]e video <bilibili-url>[/bold]             提取 Bilibili 视频字幕
  [bold]e status[/bold]                           查看队列状态
  [bold]e transcribe[/bold]                       处理 Whisper 转录队列
  [bold]e init[/bold]                             初始化项目（生成 CLAUDE.md 等）
"""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Content Extract — 操作手册", id="help-title")
            log = RichLog(highlight=False, markup=True, auto_scroll=False, id="help-log")
            yield log
            with Horizontal():
                yield Button("关闭", id="btn-close", variant="primary")

    def on_mount(self) -> None:
        """挂载后写入帮助内容。"""
        log = self.query_one("#help-log", RichLog)
        for line in self._CONTENT.splitlines():
            log.write(line)
        log.scroll_home(animate=False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()

    def on_key(self, event) -> None:
        """支持方向键/Page Up/Down 滚动，Escape/Q 关闭。"""
        key = event.key
        log = self.query_one("#help-log", RichLog)
        if key in ("up", "k"):
            log.scroll_up()
        elif key in ("down", "j"):
            log.scroll_down()
        elif key == "page_up":
            log.scroll_page_up()
        elif key == "page_down":
            log.scroll_page_down()
        elif key in ("escape", "q"):
            self.dismiss()


# ── 配置弹窗 ──────────────────────────────────────────────────────────────────

class ConfigModal(ModalScreen):
    """应用配置弹窗：修改 raw 目录等持久化设置，保存到 ~/.content-extract/config.toml。"""

    DEFAULT_CSS = """
    ConfigModal { align: center middle; }
    ConfigModal > Vertical {
        background: $surface;
        border: thick $accent;
        padding: 2 4;
        width: 80;
        height: auto;
    }
    ConfigModal #cfg-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    ConfigModal .cfg-label { margin-top: 1; color: $text-muted; }
    ConfigModal .cfg-hint  { color: $text-disabled; margin-bottom: 1; }
    ConfigModal Input { margin-bottom: 1; }
    ConfigModal #cfg-status {
        color: $success;
        height: 1;
        margin-top: 1;
    }
    ConfigModal Horizontal { height: auto; align: center middle; margin-top: 1; }
    ConfigModal Button { margin: 0 1; min-width: 14; }
    """

    def __init__(self, raw_dir: Path) -> None:
        super().__init__()
        self._raw_dir = raw_dir

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("⚙  设置", id="cfg-title")

            yield Label("Raw 数据目录", classes="cfg-label")
            yield Label(
                "提取内容的存储位置。支持绝对路径，重启后立即生效。",
                classes="cfg-hint",
            )
            yield Input(
                value=str(self._raw_dir),
                placeholder="/Users/你/Documents/ai_workspace/content-extract/raw",
                id="cfg-raw-dir",
            )

            yield Label("", id="cfg-status")

            with Horizontal():
                yield Button("保存", id="btn-cfg-save", variant="primary")
                yield Button("取消", id="btn-cfg-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cfg-cancel":
            self.dismiss(None)
            return
        if event.button.id == "btn-cfg-save":
            raw_input = self.query_one("#cfg-raw-dir", Input).value.strip()
            if not raw_input:
                self.query_one("#cfg-status", Label).update("[red]路径不能为空[/red]")
                return
            new_raw = Path(raw_input).expanduser().resolve()
            self._save_config(new_raw)
            self.dismiss(new_raw)

    def _save_config(self, raw_dir: Path) -> None:
        """将 output.dir 写入 ~/.content-extract/config.toml，合并而不覆盖其他字段。"""
        try:
            try:
                import toml
                _loads = toml.loads
                _dumps = toml.dumps
            except ImportError:
                import tomllib as _tl
                import tomli_w as _tw
                _loads = _tl.loads
                _dumps = _tw.dumps

            cfg_dir = Path.home() / ".content-extract"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            cfg_path = cfg_dir / "config.toml"

            existing: dict = {}
            if cfg_path.exists():
                existing = _loads(cfg_path.read_text(encoding="utf-8"))

            existing.setdefault("output", {})["dir"] = str(raw_dir)
            cfg_path.write_text(_dumps(existing), encoding="utf-8")
        except Exception as e:
            self.query_one("#cfg-status", Label).update(f"[red]保存失败：{e}[/red]")

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)


# ── 主应用 ────────────────────────────────────────────────────────────────────

class TUIApp(App):
    """content-extract 全屏 TUI 主应用。"""

    TITLE = "Content Extract"
    COMMANDS = {AppCommands}        # 注册命令面板，Ctrl+P 触发
    _PROGRESS_BAR_ID = "progress-bar"  # 进度条组件 ID 常量
    BINDINGS = [
        Binding("q", "quit", "退出", show=True),
        Binding("escape", "try_quit", "退出(双击)", show=False),
        Binding("ctrl+p", "command_palette", "菜单", show=True),
        Binding("a", "record_action", "记录操作", show=True),
        Binding("r", "retry_failed", "重试失败", show=True),
        Binding("c", "clear_log", "清空日志", show=True),
        Binding("o", "open_obsidian", "打开Obsidian", show=True),
        Binding("s", "show_settings", "设置", show=True),
        Binding("question_mark", "show_help", "帮助", show=True),
    ]
    DEFAULT_CSS = """
    TUIApp {
        layout: vertical;
    }
    #top-row {
        layout: horizontal;
        height: auto;
        min-height: 12;
    }
    #log-area {
        height: 1fr;
    }
    #progress-bar {
        height: 1;
        margin: 0 1;
        display: none;
    }
    #progress-bar.active {
        display: block;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._tasks: list[TaskEntry] = []
        self._cookies: dict[str, str] = {}
        self._crawl_progress: int = 0
        self._crawl_limit: int = 200
        self._active_limit_ref: list[int] | None = None
        self._last_esc_time: float = 0.0
        # raw 目录：启动时从 config 加载，可通过设置弹窗修改
        self._raw_dir: Path = _RAW_DIR

    @property
    def _registry_path(self) -> Path:
        return self._raw_dir / _REGISTRY_FILENAME

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="top-row"):
            yield AddSourcePanel()
            yield QueuePanel()
        yield LogPanel(id="log-area")
        yield ProgressBar(total=200, show_eta=False, id=self._PROGRESS_BAR_ID)
        yield Footer()

    def on_mount(self) -> None:
        """启动时加载配置、从 registry 加载历史记录。"""
        self._load_config()
        self._load_cookies()
        self._load_registry()

    def _load_config(self) -> None:
        """从 config.toml 加载 raw 目录等设置。"""
        try:
            from ..config import load_config
            cfg = load_config()
            raw_dir_str = cfg.get("output", {}).get("dir", "")
            if raw_dir_str:
                candidate = Path(raw_dir_str).expanduser()
                if not candidate.is_absolute():
                    from ..cli import _LAUNCH_DIR
                    candidate = (_LAUNCH_DIR / candidate).resolve()
                self._raw_dir = candidate
        except Exception:
            pass

    def _load_cookies(self) -> None:
        """从 config.toml 加载 cookie 路径。"""
        try:
            from ..config import load_config
            cfg = load_config()
            self._cookies = {
                k: str(Path(v).expanduser())
                for k, v in cfg.get("cookies", {}).items()
            }
        except Exception:
            pass

    @staticmethod
    def _read_all_entries(raw_dir: Path) -> list[dict]:
        """从根 registry 和所有子目录 registry 读取全部条目，统一加子目录前缀。

        扫描两层深度：
        - raw/*/.processed.json        （来源驱动目录）
        - raw/topics/*/.processed.json （Topic 学习目录）
        """
        from ..registry import Registry
        all_entries: list[dict] = []
        statuses = ("done", "done_partial", "failed", "needs_transcription")
        registry_path = raw_dir / _REGISTRY_FILENAME
        if registry_path.exists():
            for e in (e for s in statuses for e in Registry(registry_path).get_by_status(s)):
                all_entries.append(e)

        def _read_sub(sub_reg_path: Path, prefix: str) -> None:
            for e in (e for s in statuses for e in Registry(sub_reg_path).get_by_status(s)):
                if e.get("output_file"):
                    e = {**e, "output_file": f"{prefix}/{e['output_file']}"}
                all_entries.append(e)

        # 一层子目录（来源驱动）
        for sub_reg_path in sorted(raw_dir.glob(f"*/{_REGISTRY_FILENAME}")):
            parent = sub_reg_path.parent
            if parent.name == "topics":
                continue  # topics 目录本身不是任务目录
            _read_sub(sub_reg_path, parent.name)

        # 两层子目录（topics/<topic名>）
        for sub_reg_path in sorted(raw_dir.glob(f"topics/*/{_REGISTRY_FILENAME}")):
            topic_dir = sub_reg_path.parent
            prefix = f"topics/{topic_dir.name}"
            _read_sub(sub_reg_path, prefix)

        return all_entries

    def _load_registry(self) -> None:
        """从 raw/.processed.json 及各子目录的 .processed.json 加载并聚合历史任务记录。"""
        if not self._raw_dir.exists():
            return
        try:
            groups = self._group_entries(self._read_all_entries(self._raw_dir))
            for g in groups.values():
                self._tasks.append(self._build_task_entry(g))
            self._refresh_queue()
            total_pages = sum(t.page_count for t in self._tasks)
            self.log_message(f"已加载 {len(self._tasks)} 个任务（共 {total_pages} 页记录）")
        except Exception as e:
            self.log_message(f"[yellow]加载历史记录失败：{e}[/yellow]")

    @staticmethod
    def _group_entries(all_entries: list[dict]) -> dict[str, dict]:
        """将 registry 条目按输出子目录聚合：整站同目录合并，单页各自一条。"""
        groups: dict[str, dict] = {}
        for entry in all_entries:
            output_file = entry.get("output_file", "")
            source = entry["source"]
            parts = output_file.split("/") if output_file else []
            if len(parts) >= 2:
                subfolder = parts[0]
                if subfolder not in groups:
                    groups[subfolder] = {"subfolder": subfolder, "entries": []}
                groups[subfolder]["entries"].append(entry)
            else:
                key = f"single::{source}"
                groups[key] = {"subfolder": output_file, "entries": [entry]}
        return groups

    @staticmethod
    def _build_task_entry(g: dict) -> "TaskEntry":
        """从聚合分组构建单条 TaskEntry。"""
        _priority = {"failed": 3, "needs_transcription": 2, "done_partial": 1, "done": 0}
        entries = g["entries"]
        subfolder = g["subfolder"]
        worst = max(entries, key=lambda e, p=_priority: p.get(e.get("status", "done"), 0))
        latest = max(entries, key=lambda e: e.get("extracted_at", ""))
        # 找出代表性 seed URL：与子目录名匹配度最高的（匹配片段最多），平局取最短
        clean_parts = [p for p in subfolder.replace("__", "/").replace("-", ".").split("/") if p]
        seed = min(
            (e["source"] for e in entries),
            key=lambda url, cp=clean_parts: (-sum(1 for p in cp if p in url), len(url)),
        )
        # 优先从 output_file 文件名前缀推断；整站多页任务（页数>1 且无明确前缀）判为 web
        sample_file = Path(entries[0].get("output_file", "")).name
        source_type = _infer_type(sample_file)
        if source_type == "—":
            source_type = "web" if len(entries) > 1 else detect_source_type(seed)

        # 计算目标总数估算：已完成页数 + 中止时队列剩余数
        page_count = len(entries)
        queue_remaining = max(
            (e.get("queue_remaining", 0) or 0 for e in entries),
            default=0,
        )
        all_done = all(e.get("status") == "done" for e in entries)
        if queue_remaining > 0:
            total_estimate = page_count + queue_remaining
        elif all_done and page_count > 1:
            # 全部完成且无未知剩余，用实际页数作为总数显示 N/N
            total_estimate = page_count
        else:
            total_estimate = 0

        return TaskEntry(
            source=seed,
            source_type=source_type,
            status=worst.get("status", "done"),
            output_file=subfolder,
            error=worst.get("error", "") or "",
            extracted_at=latest.get("extracted_at", ""),
            page_count=page_count,
            total_estimate=total_estimate,
        )

    def _show_limit_choice(self, total: int, already: int, remaining: int, current_limit: int) -> None:
        """弹出总数确认弹窗，用户可选择一次全部抓取或沿用当前上限。

        用户确认后立即修改 _active_limit_ref[0]，BFS 循环下一次迭代即可感知新上限。
        """
        def handle(new_limit: int | None) -> None:
            if not new_limit:
                return
            if new_limit != current_limit:
                self._crawl_limit = new_limit
                # 直接修改正在运行的 BFS limit 引用，当前任务立即生效
                if self._active_limit_ref is not None:
                    self._active_limit_ref[0] = new_limit
                    self.log_message(f"[cyan]已将本次抓取上限扩展为 {new_limit} 页，继续抓取中…[/cyan]")
                else:
                    self.log_message(f"[cyan]已更新抓取上限为 {new_limit} 页[/cyan]")
                self._show_progress_bar(total=new_limit)
            else:
                self.log_message(f"[dim]沿用当前上限 {current_limit} 页[/dim]")

        self.push_screen(
            LimitChoiceModal(
                total=total,
                already=already,
                remaining=remaining,
                current_limit=current_limit,
            ),
            handle,
        )

    def _refresh_queue(self) -> None:
        """刷新队列面板显示。"""
        queue_panel = self.query_one(QueuePanel)
        queue_panel.refresh_table(self._tasks)

    def log_message(self, msg: str) -> None:
        """向日志面板写入一行消息，线程安全（可从 worker 线程调用）。"""
        # 拦截 __LIMIT_CHOICE__ 信号：不写日志，改为弹窗
        if msg.startswith("__LIMIT_CHOICE__:"):
            parts = msg.split(":")
            if len(parts) == 5:
                total, already, remaining, current = (
                    int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
                )
                # log_message 已在主线程，直接调用即可
                self._show_limit_choice(total, already, remaining, current)
            return

        log_panel = self.query_one(LogPanel)
        log_panel.write(msg)
        # 解析 WebExtractor 的进度日志格式 "[N] url → file"，推进进度条
        m = re.match(r"^\[(\d+)\]", msg)
        if m:
            n = int(m.group(1)) + 1  # 从 0 开始计数，显示为 1-based
            bar = self.query_one(f"#{self._PROGRESS_BAR_ID}", ProgressBar)
            bar.progress = n

    def _show_progress_bar(self, total: int) -> None:
        """显示进度条并重置进度。"""
        bar = self.query_one(f"#{self._PROGRESS_BAR_ID}", ProgressBar)
        bar.total = total
        bar.progress = 0
        bar.add_class("active")

    def _count_files_for(self, source: str) -> int:
        """统计与某个来源对应的 raw 目录下已有文件数。"""
        try:
            from ..extractors.web import _url_to_subfolder
            subfolder = self._raw_dir / _url_to_subfolder(source)
            if subfolder.is_dir():
                return len(list(subfolder.glob("*.md")))
        except Exception:
            pass
        return 0

    def _hide_progress_bar(self) -> None:
        """隐藏进度条。"""
        self.query_one(f"#{self._PROGRESS_BAR_ID}", ProgressBar).remove_class("active")

    def on_extract_requested(self, event: ExtractRequested) -> None:
        """处理提取请求：检查重复后决定是否直接开始或弹窗询问。"""
        existing = next((t for t in self._tasks if t.source == event.source), None)

        if existing and not event.force:
            # 未完成 / 部分完成：直接续跑，不弹窗
            if existing.status in ("needs_transcription", "failed", "done_partial"):
                self._start_extract(event, force=False)
            else:
                # 全部完成（done）：弹窗让用户决定
                def handle_choice(choice: str | None) -> None:
                    if choice == "btn-resume":
                        self._start_extract(event, force=False)
                    elif choice == "btn-force":
                        self._start_extract(event, force=True)

                file_count = self._count_files_for(event.source)
                self.push_screen(
                    DuplicateModal(
                        source=event.source,
                        status=existing.status,
                        extracted_at=existing.extracted_at,
                        file_count=file_count,
                    ),
                    handle_choice,
                )
        else:
            self._start_extract(event, force=event.force)

    def _start_extract(self, event: ExtractRequested, force: bool) -> None:
        """实际启动提取 worker，更新任务列表。"""
        existing = next((t for t in self._tasks if t.source == event.source), None)

        # 整站任务判断：event.crawl 为 True，或已有记录是多页 web 任务
        # 注意：已有记录的 source_type 可能被 _build_task_entry 推断为 article（detect_source_type 的结果），
        # 需要同时检查 page_count > 1 来确认是整站任务，不依赖 source_type 是否为 "web"
        is_crawl_task = (
            event.crawl
            or (existing is not None and existing.page_count > 1)
        )
        # 确保整站任务的 source_type 始终为 web（已有记录可能被推断为 article）
        source_type = "web" if is_crawl_task else event.source_type

        if existing:
            existing.status = "extracting"
            existing.source_type = source_type
            existing.error = ""
        else:
            self._tasks.append(TaskEntry(
                source=event.source,
                source_type=source_type,
                status="extracting",
            ))
        self._refresh_queue()
        crawl_hint = "（整站）" if is_crawl_task else ""
        force_hint = "（强制）" if force else ""
        self.log_message(f"开始提取 [{source_type}]{crawl_hint}{force_hint}: {event.source}")
        if is_crawl_task:
            self._show_progress_bar(total=self._crawl_limit)
        self._run_extract(event.source, source_type, event.update_wiki, is_crawl_task, force, self._crawl_limit, event.extra)

    def on_extract_done(self, event: ExtractDone) -> None:
        """提取完成后更新内存状态，从 registry 重新读取最新进度并刷新队列。"""
        for t in self._tasks:
            if t.source == event.source and t.status == "extracting":
                t.status = "done" if event.success else "failed"
                t.output_file = event.output_file
                t.error = event.error
                break
        # 从 registry 重新加载该任务的最新进度（page_count / total_estimate / extracted_at）
        self._reload_task_from_registry(event.source)
        self._refresh_queue()
        self._hide_progress_bar()
        if event.success:
            self.log_message(f"[green]✓ 完成 → {event.output_file}[/green]")
        else:
            self.log_message(f"[red]✗ 失败：{event.error}[/red]")

    def _reload_task_from_registry(self, source: str) -> None:
        """从 registry 重新加载所有条目，更新内存中匹配的 TaskEntry。"""
        try:
            groups = self._group_entries(self._read_all_entries(self._raw_dir))
            for g in groups.values():
                fresh = self._build_task_entry(g)
                for i, t in enumerate(self._tasks):
                    if t.source == fresh.source:
                        fresh.status = t.status
                        self._tasks[i] = fresh
                        break
        except Exception as e:
            self.log_message(f"[dim]进度刷新失败：{e}[/dim]")

    @work(thread=True)
    def _run_extract(self, source: str, source_type: str, update_wiki: bool, crawl: bool = False, force: bool = False, limit: int = 200, extra: dict | None = None) -> None:
        """在独立线程执行提取，通过 call_from_thread 回调日志。"""
        extra = extra or {}
        def on_progress(msg: str) -> None:
            self.call_from_thread(self.log_message, msg)

        try:
            from ..extractors.base import ExtractConfig
            cfg = ExtractConfig(output_dir=self._raw_dir, cookies=self._cookies, force=force)

            if source_type == "web":
                from ..extractors.web import WebExtractor
                extractor = WebExtractor(config=cfg, on_progress=on_progress)
                if crawl:
                    # 创建可变 limit 引用，主线程修改 _active_limit_ref[0] 即可实时影响 BFS
                    limit_ref: list[int] = [limit]
                    self.call_from_thread(setattr, self, "_active_limit_ref", limit_ref)
                    try:
                        out = extractor.extract(source, crawl=True, limit_ref=limit_ref)
                    finally:
                        self.call_from_thread(setattr, self, "_active_limit_ref", None)
                else:
                    out = extractor.extract(source, crawl=False)
            elif source_type in ("video", "bilibili"):
                from ..extractors import auto_detect_video
                out = auto_detect_video(source, config=cfg)
                self._auto_transcribe(cfg.output_dir, on_progress)
            elif source_type == "article":
                from ..extractors import auto_detect_article
                out = auto_detect_article(source, config=cfg, on_progress=on_progress)
            elif source_type == "ebook":
                from ..extractors.ebook import EbookExtractor
                extractor = EbookExtractor(config=cfg, on_progress=on_progress)
                out = extractor.extract(source)
            elif source_type in ("code", "github"):
                from ..extractors.code import CodeExtractor
                mode = extra.get("code_mode", "overview")
                extractor = CodeExtractor(config=cfg, on_progress=on_progress)
                out = extractor.extract(source, mode=mode)
            else:
                self.post_message(ExtractDone(
                    source=source, success=False,
                    error=f"类型 [{source_type}] 尚未在 Phase 1 实现，请通过 CLI 使用"
                ))
                return

            # output_file は raw/ からの相対パス（subfolder/file.md 形式）で渡す
            # 絶対パスだと _group_entries が subfolder を取れずフォールバックする
            try:
                out_rel = str(Path(out).relative_to(self._raw_dir))
            except ValueError:
                out_rel = str(out)
            self.post_message(ExtractDone(source=source, success=True, output_file=out_rel))

            if update_wiki:
                self.call_from_thread(self.push_screen, WikiModal())

        except Exception as e:
            self.post_message(ExtractDone(source=source, success=False, error=str(e)))

    def on_extract_batch_requested(self, event: ExtractBatchRequested) -> None:
        """处理批量 URL 提取请求：创建任务记录并启动 worker。"""
        source_key = f"batch::{event.folder_name}"
        existing = next((t for t in self._tasks if t.source == source_key), None)
        if existing:
            existing.status = "extracting"
            existing.source_type = event.source_type
            existing.error = ""
        else:
            self._tasks.append(TaskEntry(
                source=source_key,
                source_type=event.source_type,
                status="extracting",
            ))
        self._refresh_queue()
        self.log_message(
            f"开始批量提取 [{event.source_type}] {len(event.urls)} 个 URL → raw/{event.folder_name}/"
        )
        self._run_extract_batch(event.urls, event.folder_name, event.source_type, event.update_wiki)

    @work(thread=True)
    def _run_extract_batch(self, urls: list[str], folder_name: str, source_type: str, update_wiki: bool) -> None:
        """在独立线程批量提取多个 URL 到自定义目录，根据 source_type 路由到对应提取器。"""
        def on_progress(msg: str) -> None:
            self.call_from_thread(self.log_message, msg)

        source_key = f"batch::{folder_name}"
        try:
            from ..extractors.base import ExtractConfig
            cfg = ExtractConfig(output_dir=self._raw_dir, cookies=self._cookies)
            results: list = []

            if source_type in ("web", "article"):
                # web 和 article 都用 WebExtractor 单页抓取
                from ..extractors.web import WebExtractor
                extractor = WebExtractor(config=cfg, on_progress=on_progress)
                results = extractor.extract_batch(urls, folder_name)

            elif source_type == "video":
                # video：逐条调用 auto_detect_video（Bilibili），输出到 raw/<folder_name>/
                from ..extractors import auto_detect_video
                video_cfg = ExtractConfig(
                    output_dir=self._raw_dir / folder_name,
                    cookies=self._cookies,
                )
                for url in urls:
                    try:
                        out = auto_detect_video(url, config=video_cfg)
                        results.append(out)
                        on_progress(f"[完成] {url} → {out.name}")
                    except Exception as err:
                        on_progress(f"[失败] {url}：{err}")
                self._auto_transcribe(video_cfg.output_dir, on_progress)

            elif source_type == "docs":
                # docs：本地文档路径，逐条处理（Phase 2 实现后替换为 local_docs 提取器）
                on_progress(f"[提示] docs 批量提取将在 Phase 2 实现，当前跳过 {len(urls)} 个路径")

            else:
                self.post_message(ExtractDone(
                    source=source_key, success=False,
                    error=f"类型 [{source_type}] 不支持批量模式"
                ))
                return

            if results:
                first = Path(results[0])
                # output_file 用相对格式 folder/filename，供 _group_entries 正确解析
                try:
                    out_file = str(first.relative_to(self._raw_dir))
                except ValueError:
                    out_file = f"{folder_name}/{first.name}"
            else:
                out_file = folder_name
            self.post_message(ExtractDone(source=source_key, success=True, output_file=out_file))
            if update_wiki:
                self.call_from_thread(self.push_screen, WikiModal())
        except Exception as e:
            self.post_message(ExtractDone(source=source_key, success=False, error=str(e)))

    def on_topic_add_requested(self, event: TopicAddRequested) -> None:
        """处理 Topic 模式添加请求：创建任务记录并启动 worker。"""
        source_key = f"topic::{event.topic}"
        existing = next((t for t in self._tasks if t.source == source_key), None)
        if existing:
            existing.status = "extracting"
            existing.error = ""
        else:
            self._tasks.append(TaskEntry(
                source=source_key,
                source_type="topic",
                status="extracting",
                output_file=f"topics/{event.topic}",
            ))
        self._refresh_queue()
        self.log_message(
            f"[Topic] 添加到「{event.topic}」：{len(event.sources)} 个来源"
        )
        self._run_topic_add(event.sources, event.topic, event.topic_role,
                            event.source_type, event.update_wiki)

    @work(thread=True)
    def _run_topic_add(
        self,
        sources: list[str],
        topic: str,
        topic_role: str,
        source_type: str,
        update_wiki: bool,
    ) -> None:
        """在独立线程处理 Topic 添加：本地文件直接导入，在线 URL 路由到对应提取器。"""
        def on_progress(msg: str) -> None:
            self.call_from_thread(self.log_message, msg)

        source_key = f"topic::{topic}"
        topic_dir = self._raw_dir / "topics" / topic
        try:
            from ..extractors.base import ExtractConfig
            results: list = []
            cfg = ExtractConfig(output_dir=self._raw_dir, cookies=self._cookies)

            for src in sources:
                p = Path(src)
                if not src.startswith(("http://", "https://")) and p.exists():
                    out = self._topic_add_local(src, topic, topic_role, cfg, on_progress)
                else:
                    out = self._topic_add_url(src, topic, topic_role, source_type, topic_dir, on_progress)
                if out is not None:
                    results.append(out)

            if any(Path(r).name.startswith("bili__") for r in results):
                self._auto_transcribe(topic_dir, on_progress)

            if results and Path(results[0]).is_relative_to(self._raw_dir):
                out_file = str(Path(results[0]).relative_to(self._raw_dir))
            else:
                out_file = f"topics/{topic}"
            self.post_message(ExtractDone(source=source_key, success=True, output_file=out_file))
            if update_wiki:
                self.call_from_thread(self.push_screen, WikiModal())
        except Exception as e:
            self.post_message(ExtractDone(source=source_key, success=False, error=str(e)))

    def _topic_add_local(
        self, src: str, topic: str, topic_role: str, cfg: "object", on_progress
    ) -> "Path | None":
        """导入单个本地文件到 topic 目录。"""
        from ..extractors.local_topic import LocalTopicExtractor
        p = Path(src)
        try:
            extractor = LocalTopicExtractor(config=cfg, on_progress=on_progress)
            out = extractor.extract(src, topic=topic, topic_role=topic_role)
            on_progress(f"[完成] {p.name} → {out.name}（topic: {topic}）")
            return out
        except Exception as err:
            on_progress(f"[失败] {p.name}：{err}")
            return None

    def _topic_add_url(
        self, src: str, topic: str, topic_role: str, source_type: str,
        topic_dir: Path, on_progress
    ) -> "Path | None":
        """提取单个在线 URL 并归入 topic 目录。"""
        from ..extractors.base import ExtractConfig
        actual_type = detect_source_type(src) if source_type == "auto" else source_type
        url_cfg = ExtractConfig(output_dir=topic_dir, cookies=self._cookies)
        try:
            if actual_type in ("video", "bilibili"):
                from ..extractors import auto_detect_video
                out = auto_detect_video(src, config=url_cfg)
            elif actual_type == "ebook":
                from ..extractors.ebook import EbookExtractor
                out = EbookExtractor(config=url_cfg, on_progress=on_progress).extract(src)
            elif actual_type == "article":
                from ..extractors import auto_detect_article
                out = auto_detect_article(src, config=url_cfg, on_progress=on_progress)
            else:
                from ..extractors.web import WebExtractor
                out = WebExtractor(config=url_cfg, on_progress=on_progress).extract(src)
            _inject_topic_frontmatter(out, topic, topic_role)
            on_progress(f"[完成] {src} → {out.name}")
            return out
        except Exception as err:
            on_progress(f"[失败] {src}：{err}")
            return None

    def _auto_transcribe(self, output_dir: Path, on_progress) -> None:
        """提取完成后，若目录中有待转录条目则自动触发 Whisper 转录。

        通过独立子进程运行，避免 Textual 的 asyncio fd 被 ffmpeg 子进程继承
        导致 'bad value(s) in fds_to_keep' 错误。
        """
        from ..config import load_config

        pending = self._collect_transcription_pending(output_dir)
        if not pending:
            return

        w = load_config().get("whisper", {})
        model = w.get("model", "medium")
        on_progress(f"[转录] 开始自动转录 {len(pending)} 个视频（模型: {model}）…")
        self._run_transcribe_subprocess(
            output_dir=output_dir,
            model=model,
            device=w.get("device", "cpu"),
            compute_type=w.get("compute_type", "int8"),
            on_progress=on_progress,
        )

    @staticmethod
    def _collect_transcription_pending(output_dir: Path) -> list:
        """收集待转录条目，并将可重试的 failed 条目重置为 needs_transcription。"""
        from ..registry import Registry

        reg_path = output_dir / _REGISTRY_FILENAME
        if not reg_path.exists():
            return []

        reg = Registry(reg_path)
        _reset_retryable_failures(reg_path, reg)
        pending = reg.get_by_status("needs_transcription")
        _append_from_needs_file(output_dir, pending)
        return pending

    @staticmethod
    def _run_transcribe_subprocess(
        output_dir: Path, model: str, device: str, compute_type: str, on_progress
    ) -> None:
        """在独立子进程中执行 process_queue，close_fds=True 隔离 Textual fd。"""
        import sys
        import subprocess

        project_root = str(output_dir.parent.parent)
        script = (
            "import sys, os; "
            "os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com'); "
            f"sys.path.insert(0, {project_root!r}); "
            "from content_extract.transcribe.queue import process_queue; "
            "from pathlib import Path; "
            f"process_queue(output_dir=Path({str(output_dir)!r}), "
            f"model={model!r}, device={device!r}, compute_type={compute_type!r})"
        )
        try:
            import subprocess
            proc = subprocess.Popen(
                [sys.executable, "-u", "-c", script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                close_fds=True,
                text=True,
                bufsize=1,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    on_progress(line)
            proc.wait()
            if proc.returncode == 0:
                on_progress("[转录] 自动转录完成")
            else:
                on_progress(f"[转录] 子进程退出码 {proc.returncode}")
        except Exception as e:
            on_progress(f"[转录] 失败: {e}")

    def action_record_action(self) -> None:
        """对队列表格中当前选中行的记录弹出操作菜单。"""
        table = self.query_one("#queue-table", DataTable)
        row_key = table.cursor_row
        if row_key < 0 or row_key >= len(self._tasks):
            self.log_message("[yellow]请先在队列中选中一行[/yellow]")
            return
        task = self._tasks[row_key]

        def handle_action(choice: str | None) -> None:
            if choice == "btn-clear":
                self._clear_record(task)
            elif choice == "btn-resume":
                self.on_extract_requested(ExtractRequested(
                    source=task.source,
                    source_type=task.source_type,
                    crawl=(task.source_type == "web" and task.page_count > 1),
                    force=False,
                ))
            elif choice == "btn-force":
                self.on_extract_requested(ExtractRequested(
                    source=task.source,
                    source_type=task.source_type,
                    crawl=(task.source_type == "web" and task.page_count > 1),
                    force=True,
                ))
            elif choice == "btn-transcribe":
                self._trigger_manual_transcribe(task)

        self.push_screen(RecordActionModal(task), handle_action)

    def _clear_record(self, task: "TaskEntry") -> None:
        """从内存列表和 registry 中删除指定任务的所有记录（按子目录批量清除）。"""
        try:
            from ..registry import Registry
            reg = Registry(self._registry_path)
            if task.output_file:
                count = reg.remove_by_output_prefix(task.output_file)
                self.log_message(f"已清空 {count} 条记录：{task.output_file}")
            else:
                reg.remove(task.source)
                self.log_message(f"已清空记录：{task.source}")
        except Exception as e:
            self.log_message(f"[yellow]清空 registry 记录失败：{e}[/yellow]")
        self._tasks = [t for t in self._tasks if t.source != task.source]
        self._refresh_queue()

    def _trigger_manual_transcribe(self, task: "TaskEntry") -> None:
        """手动触发指定 video 任务的 Whisper 转录。"""
        output_dir = self._raw_dir / task.output_file if task.output_file else self._raw_dir
        self.log_message(f"[转录] 手动触发：{task.output_file or task.source}")
        self._run_transcribe(output_dir)

    @work(thread=True)
    def _run_transcribe(self, output_dir: Path) -> None:
        """在独立线程执行转录，通过 call_from_thread 回调日志。"""
        def on_progress(msg: str) -> None:
            self.call_from_thread(self.log_message, msg)
        self._auto_transcribe(output_dir, on_progress)

    def action_show_help(self) -> None:
        """显示操作手册弹窗。"""
        self.push_screen(HelpModal())

    def action_show_settings(self) -> None:
        """显示配置弹窗，保存后立即更新 raw 目录并重新加载历史记录。"""
        def _on_saved(new_raw: Path | None) -> None:
            if new_raw is None:
                return
            self._raw_dir = new_raw
            new_raw.mkdir(parents=True, exist_ok=True)
            self._tasks.clear()
            self._load_registry()
            self.log_message(f"[green]✓ 配置已保存，Raw 目录切换为：{new_raw}[/green]")

        self.push_screen(ConfigModal(self._raw_dir), _on_saved)

    def action_clear_log(self) -> None:
        """清空日志面板。"""
        self.query_one("#log", RichLog).clear()

    def action_try_quit(self) -> None:
        """单击 Esc 提示，500ms 内再次按下才退出（防误触）。"""
        now = time.monotonic()
        if now - self._last_esc_time < 0.5:
            self.exit()
        else:
            self._last_esc_time = now
            self.log_message("[dim]再按一次 Esc 退出，或按 Q 直接退出[/dim]")

    def action_quit(self) -> None:
        """退出应用。"""
        self.exit()

    def action_retry_failed(self) -> None:
        """重试第一个失败的任务（如有）。"""
        for t in self._tasks:
            if t.status == "failed":
                self.log_message(f"重试：{t.source}")
                t.status = "extracting"
                self._refresh_queue()
                self._run_extract(t.source, t.source_type, False)
                break

    def action_open_obsidian(self) -> None:
        """在 macOS 上打开 Obsidian vault（wiki/ 目录）。"""
        try:
            subprocess.Popen(["open", "obsidian://open?vault=wiki"])
            self.log_message("正在打开 Obsidian…")
        except Exception as e:
            self.log_message(f"[red]打开 Obsidian 失败：{e}[/red]")
