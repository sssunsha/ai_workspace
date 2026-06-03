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
)
from textual import work
from textual.command import Provider, Hit, Hits, DiscoveryHit


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
    "github__": "github",
    "article__": "article",
}


def _infer_type(output_file: str) -> str:
    """从输出文件路径的前缀推断来源类型。"""
    name = Path(output_file).name if output_file else ""
    for prefix, t in _PREFIX_TO_TYPE.items():
        if name.startswith(prefix):
            return t
    return "—"


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
    def __init__(self, source: str, source_type: str, update_wiki: bool = False, crawl: bool = False, force: bool = False) -> None:
        super().__init__()
        self.source = source
        self.source_type = source_type
        self.update_wiki = update_wiki
        self.crawl = crawl
        self.force = force


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
                f"[bold]{t.source[:68]}[/bold]\n"
                f"类型：{t.source_type or '—'}  状态：{status_label}{progress_str}"
            )
            # 第一行：操作按钮
            with Horizontal():
                yield Button("继续抓取", id="btn-resume", variant="primary")
                yield Button("强制更新", id="btn-force", variant="warning")
                yield Button("清空记录", id="btn-clear", variant="error")
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
        table = DataTable(id="queue-table", zebra_stripes=True)
        table.add_columns("状态", "类型", "来源", "进度", "时间")
        yield table
        yield Label("", id="queue-summary")

    def refresh_table(self, tasks: list[TaskEntry]) -> None:
        """清空并重绘队列表格，同时更新底部统计摘要。"""
        table = self.query_one("#queue-table", DataTable)
        table.clear()
        for t in tasks:
            icon = _STATUS_ICONS.get(t.status, "?")
            source_short = t.source[-35:] if len(t.source) > 35 else t.source
            time_short = t.extracted_at[:10] if t.extracted_at else "—"
            # 整站任务显示"类型(页数)"，单页显示类型
            type_str = f"{t.source_type}({t.page_count})" if t.page_count > 1 else (t.source_type or "—")
            # 进度列：已抓/目标，目标未知时显示已抓数或"—"
            if t.total_estimate > 0:
                progress_str = f"{t.page_count}/{t.total_estimate}"
            elif t.page_count > 0:
                progress_str = f"{t.page_count}/?"
            else:
                progress_str = "—"
            table.add_row(icon, type_str, source_short, progress_str, time_short)
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
        # 内存中的任务列表，启动时从 registry 加载
        self._tasks: list[TaskEntry] = []
        # 从 config 加载的 cookie 路径
        self._cookies: dict[str, str] = {}
        # 当前整站爬取的进度（已写入页数）
        self._crawl_progress: int = 0
        self._crawl_limit: int = 200
        # 记录上次按 Esc 的时间（用于双击检测）
        self._last_esc_time: float = 0.0

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
        """从 ./raw/.processed.json 加载并聚合历史任务记录。

        整站爬取（output_file 在子目录下）按子目录合并为一条；
        单页提取保持一对一。
        """
        registry_path = Path("./raw/.processed.json")
        if not registry_path.exists():
            return
        try:
            from ..registry import Registry
            reg = Registry(registry_path)
            all_entries = [
                e for status in ("done", "done_partial", "failed", "needs_transcription")
                for e in reg.get_by_status(status)
            ]
            groups = self._group_entries(all_entries)
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
        total_estimate = (page_count + queue_remaining) if queue_remaining > 0 else 0

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

    def _count_files_for(self, source: str) -> int:
        """统计与某个来源对应的 raw 目录下已有文件数。"""
        try:
            from ..extractors.web import _url_to_subfolder
            subfolder = Path("./raw") / _url_to_subfolder(source)
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

        # 若是整站任务（web 类型且已有多页记录），自动补上 crawl=True
        # 防止从 RecordActionModal / DuplicateModal 过来时 crawl 默认为 False
        is_crawl_task = (
            event.crawl
            or (existing is not None and existing.source_type == "web" and existing.page_count > 1)
        )

        if existing:
            existing.status = "extracting"
            existing.error = ""
        else:
            self._tasks.append(TaskEntry(
                source=event.source,
                source_type=event.source_type,
                status="extracting",
            ))
        self._refresh_queue()
        crawl_hint = "（整站）" if is_crawl_task else ""
        force_hint = "（强制）" if force else ""
        self.log_message(f"开始提取 [{event.source_type}]{crawl_hint}{force_hint}: {event.source}")
        if is_crawl_task and event.source_type == "web":
            self._show_progress_bar(total=200)
        self._run_extract(event.source, event.source_type, event.update_wiki, is_crawl_task, force)

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
    def _run_extract(self, source: str, source_type: str, update_wiki: bool, crawl: bool = False, force: bool = False) -> None:
        """在独立线程执行提取，通过 call_from_thread 回调日志。"""
        def on_progress(msg: str) -> None:
            self.call_from_thread(self.log_message, msg)

        try:
            from ..extractors.base import ExtractConfig
            cfg = ExtractConfig(output_dir=Path("./raw"), cookies=self._cookies, force=force)

            if source_type == "web":
                from ..extractors.web import WebExtractor
                extractor = WebExtractor(config=cfg, on_progress=on_progress)
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

        self.push_screen(RecordActionModal(task), handle_action)

    def _clear_record(self, task: "TaskEntry") -> None:
        """从内存列表和 registry 中删除指定任务的所有记录（按子目录批量清除）。"""
        try:
            from ..registry import Registry
            reg = Registry(Path("./raw/.processed.json"))
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

    def action_show_help(self) -> None:
        """显示操作手册弹窗。"""
        self.push_screen(HelpModal())

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
