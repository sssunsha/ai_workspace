from __future__ import annotations

import re
import subprocess
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
)
from textual import work


# ── 数据模型 ──────────────────────────────────────────────────────────────────

@dataclass
class TaskEntry:
    """内存中的单条任务状态，对应 registry 的一个 URL 条目。"""
    source: str
    source_type: str
    status: str  # extracting / done / failed / needs_transcription
    output_file: str = ""
    error: str = ""
    extracted_at: str = ""


# 状态图标映射
_STATUS_ICONS = {
    "extracting": "⟳",
    "done": "✓",
    "failed": "✗",
    "needs_transcription": "⏳",
}


# ── 类型自动识别 ──────────────────────────────────────────────────────────────

def detect_source_type(source: str) -> str:
    """根据 URL 或路径自动识别来源类型。"""
    if source.startswith(("http://", "https://")):
        if "bilibili.com" in source or "b23.tv" in source:
            return "video"
        if "github.com" in source:
            return "github"
        return "article"
    p = Path(source)
    if p.suffix in {".epub", ".pdf", ".mobi"}:
        return "ebook"
    if p.is_dir():
        if (p / "package.json").exists() or (p / "pyproject.toml").exists():
            return "code"
        return "docs"
    return "docs"


# ── 消息定义 ──────────────────────────────────────────────────────────────────

class ExtractRequested(Message):
    """用户点击「提取」按钮时发出。"""
    def __init__(self, source: str, source_type: str, update_wiki: bool = False, crawl: bool = False) -> None:
        super().__init__()
        self.source = source
        self.source_type = source_type
        self.update_wiki = update_wiki
        self.crawl = crawl


class ExtractDone(Message):
    """worker 线程提取完成后发出。"""
    def __init__(self, source: str, success: bool, output_file: str = "", error: str = "") -> None:
        super().__init__()
        self.source = source
        self.success = success
        self.output_file = output_file
        self.error = error


# ── Wiki 占位弹窗 ─────────────────────────────────────────────────────────────

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
    """左侧输入面板：URL/路径输入、类型选择、提取按钮。"""

    DEFAULT_CSS = """
    AddSourcePanel {
        width: 60%;
        height: auto;
        border: round $primary;
        padding: 1 2;
    }
    AddSourcePanel Label {
        margin-bottom: 0;
    }
    AddSourcePanel Input {
        margin-bottom: 1;
    }
    AddSourcePanel Select {
        margin-bottom: 1;
    }
    AddSourcePanel Checkbox {
        margin-bottom: 1;
    }
    AddSourcePanel Horizontal {
        height: auto;
    }
    AddSourcePanel Button {
        margin-right: 1;
    }
    """

    # 类型下拉选项：(显示文本, 值)
    _TYPE_OPTIONS = [
        ("自动识别", "auto"),
        ("web 网页", "web"),
        ("video 视频", "video"),
        ("ebook 电子书", "ebook"),
        ("code 代码", "code"),
        ("docs 文档", "docs"),
        ("github 仓库", "github"),
        ("article 单篇文章", "article"),
    ]

    def compose(self) -> ComposeResult:
        yield Label("URL / 路径：")
        yield Input(placeholder="粘贴 URL 或本地路径…", id="url-input")
        yield Label("来源类型：")
        yield Select(
            options=self._TYPE_OPTIONS,
            value="auto",
            id="type-select",
        )
        yield Checkbox("整站爬取（web 类型时生效）", value=True, id="crawl-checkbox")
        with Horizontal():
            yield Button("提取", id="btn-extract", variant="primary")
            yield Button("提取并更新 Wiki", id="btn-extract-wiki")

    def on_input_changed(self, event: Input.Changed) -> None:
        """输入变化时自动识别类型，仅在用户选「自动识别」时生效。"""
        if event.input.id != "url-input":
            return
        # Select 保持 auto，提交时再根据输入内容解析

    def on_button_pressed(self, event: Button.Pressed) -> None:
        url_input = self.query_one("#url-input", Input)
        type_select = self.query_one("#type-select", Select)
        crawl_checkbox = self.query_one("#crawl-checkbox", Checkbox)
        source = url_input.value.strip()
        if not source:
            return

        # 类型解析：auto 时调用自动识别函数
        raw_type = str(type_select.value)
        source_type = detect_source_type(source) if raw_type == "auto" else raw_type

        update_wiki = event.button.id == "btn-extract-wiki"
        # crawl 标志：勾选时对 web 类型生效，其他类型 worker 里自动忽略
        crawl = bool(crawl_checkbox.value)
        self.post_message(ExtractRequested(
            source=source,
            source_type=source_type,
            update_wiki=update_wiki,
            crawl=crawl,
        ))

        # 清空输入框
        url_input.value = ""


# ── 处理队列面板 ──────────────────────────────────────────────────────────────

class QueuePanel(Static):
    """右侧队列面板：展示所有任务的状态。"""

    DEFAULT_CSS = """
    QueuePanel {
        width: 40%;
        height: auto;
        border: round $secondary;
        padding: 1;
    }
    QueuePanel DataTable {
        height: 12;
    }
    """

    def compose(self) -> ComposeResult:
        table = DataTable(id="queue-table", zebra_stripes=True)
        table.add_columns("状态", "来源", "输出文件")
        yield table

    def refresh_table(self, tasks: list[TaskEntry]) -> None:
        """清空并重绘队列表格。"""
        table = self.query_one("#queue-table", DataTable)
        table.clear()
        for t in tasks:
            icon = _STATUS_ICONS.get(t.status, "?")
            # 来源截断显示，避免过长
            source_short = t.source[-40:] if len(t.source) > 40 else t.source
            if t.output_file:
                output_short = Path(t.output_file).name
            elif t.error:
                output_short = t.error[:30]
            else:
                output_short = "—"
            table.add_row(icon, source_short, output_short)


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


# ── 主应用 ────────────────────────────────────────────────────────────────────

class TUIApp(App):
    """content-extract 全屏 TUI 主应用。"""

    TITLE = "Content Extract"
    _PROGRESS_BAR_ID = "progress-bar"  # 进度条组件 ID 常量
    BINDINGS = [
        Binding("q", "quit", "退出", show=True),
        Binding("r", "retry_failed", "重试失败", show=True),
        Binding("c", "clear_log", "清空日志", show=True),
        Binding("o", "open_obsidian", "打开Obsidian", show=True),
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
        # 内存中的任务列表，启动时从 registry 加载
        self._tasks: list[TaskEntry] = []
        # 从 config 加载的 cookie 路径
        self._cookies: dict[str, str] = {}
        # 当前整站爬取的进度（已写入页数）
        self._crawl_progress: int = 0
        self._crawl_limit: int = 200

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="top-row"):
            yield AddSourcePanel()
            yield QueuePanel()
        yield LogPanel(id="log-area")
        yield ProgressBar(total=200, show_eta=False, id=self._PROGRESS_BAR_ID)
        yield Footer()

    def on_mount(self) -> None:
        """启动时从 registry 加载历史记录。"""
        self._load_cookies()
        self._load_registry()

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

    def _load_registry(self) -> None:
        """从 ./raw/.processed.json 加载历史任务记录。"""
        registry_path = Path("./raw/.processed.json")
        if not registry_path.exists():
            return
        try:
            from ..registry import Registry
            reg = Registry(registry_path)
            for status in ("done", "failed", "needs_transcription"):
                for entry in reg.get_by_status(status):
                    self._tasks.append(TaskEntry(
                        source=entry["source"],
                        source_type="",
                        status=status,
                        output_file=entry.get("output_file", ""),
                        error=entry.get("error", "") or "",
                        extracted_at=entry.get("extracted_at", ""),
                    ))
            self._refresh_queue()
            self.log_message(f"已加载 {len(self._tasks)} 条历史记录")
        except Exception as e:
            self.log_message(f"[yellow]加载历史记录失败：{e}[/yellow]")

    def _refresh_queue(self) -> None:
        """刷新队列面板显示。"""
        queue_panel = self.query_one(QueuePanel)
        queue_panel.refresh_table(self._tasks)

    def log_message(self, msg: str) -> None:
        """向日志面板写入一行消息，线程安全（可从 worker 线程调用）。"""
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

    def _hide_progress_bar(self) -> None:
        """隐藏进度条。"""
        self.query_one(f"#{self._PROGRESS_BAR_ID}", ProgressBar).remove_class("active")

    def on_extract_requested(self, event: ExtractRequested) -> None:
        """处理提取请求：追加任务到列表并启动 worker。"""
        entry = TaskEntry(
            source=event.source,
            source_type=event.source_type,
            status="extracting",
        )
        self._tasks.append(entry)
        self._refresh_queue()
        crawl_hint = "（整站）" if event.crawl else ""
        self.log_message(f"开始提取 [{event.source_type}]{crawl_hint}: {event.source}")
        # 整站 web 爬取时显示进度条，limit 默认 200
        if event.crawl and event.source_type == "web":
            self._show_progress_bar(total=200)
        self._run_extract(event.source, event.source_type, event.update_wiki, event.crawl)

    def on_extract_done(self, event: ExtractDone) -> None:
        """提取完成后更新内存状态并刷新队列。"""
        for t in self._tasks:
            if t.source == event.source and t.status == "extracting":
                t.status = "done" if event.success else "failed"
                t.output_file = event.output_file
                t.error = event.error
                break
        self._refresh_queue()
        self._hide_progress_bar()
        if event.success:
            self.log_message(f"[green]✓ 完成 → {event.output_file}[/green]")
        else:
            self.log_message(f"[red]✗ 失败：{event.error}[/red]")

    @work(thread=True)
    def _run_extract(self, source: str, source_type: str, update_wiki: bool, crawl: bool = False) -> None:
        """在独立线程执行提取，通过 call_from_thread 回调日志。"""
        def on_progress(msg: str) -> None:
            self.call_from_thread(self.log_message, msg)

        try:
            from ..extractors.base import ExtractConfig
            cfg = ExtractConfig(output_dir=Path("./raw"), cookies=self._cookies)

            if source_type == "web":
                from ..extractors.web import WebExtractor
                extractor = WebExtractor(config=cfg, on_progress=on_progress)
                # crawl=True 时触发整站 BFS 爬取，默认 limit=200
                out = extractor.extract(source, crawl=crawl)
            elif source_type in ("video", "bilibili"):
                from ..extractors import auto_detect_video
                out = auto_detect_video(source, config=cfg)
            else:
                self.post_message(ExtractDone(
                    source=source, success=False,
                    error=f"类型 [{source_type}] 尚未在 Phase 1 实现，请通过 CLI 使用"
                ))
                return

            self.post_message(ExtractDone(source=source, success=True, output_file=str(out)))

            if update_wiki:
                self.call_from_thread(self.push_screen, WikiModal())

        except Exception as e:
            self.post_message(ExtractDone(source=source, success=False, error=str(e)))

    def action_clear_log(self) -> None:
        """清空日志面板。"""
        self.query_one("#log", RichLog).clear()

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
