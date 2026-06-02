# Textual TUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `content-extract`（无参数）启动的全屏 Textual TUI，包含添加来源面板、处理队列面板和实时日志面板。

**Architecture:** TUIApp 继承 Textual App，维护内存中的 `list[TaskEntry]`，启动时从 `./raw/.processed.json` 加载历史，提取任务通过 `@work(thread=True)` 在独立线程运行，进度回调通过 `call_from_thread` 线程安全写入 LogPanel。cli.py 无参数时直接启动 TUIApp，有参数时行为与现在完全相同。

**Tech Stack:** Python 3.11+、textual>=0.61.0、现有 content_extract.extractors、content_extract.registry

---

## 文件清单

| 文件 | 操作 | 职责 |
|------|------|------|
| `content_extract/ui/__init__.py` | 新建 | 空包标记 |
| `content_extract/ui/tui.py` | 新建 | 全部 TUI 代码（数据模型、组件、消息、App） |
| `content_extract/cli.py` | 修改第 18-19 行 | 无参数时启动 TUIApp |
| `pyproject.toml` | 修改 | 添加 `[ui]` optional-dependency |
| `requirements.txt` | 修改 | 添加 `# ui` 分组注释 |
| `tests/test_tui.py` | 新建 | Pilot 测试（5个用例，全 mock extract） |

---

## Task 1：安装依赖 + 更新 pyproject.toml / requirements.txt

**文件：**
- 修改：`content-extract/pyproject.toml`
- 修改：`content-extract/requirements.txt`

- [ ] **步骤 1：安装 textual**

```bash
pip install "textual>=0.61.0"
```

预期：安装成功，无报错。

- [ ] **步骤 2：验证 textual 可导入**

```bash
python3 -c "import textual; print(textual.__version__)"
```

预期：打印版本号（>= 0.61.0）。

- [ ] **步骤 3：更新 pyproject.toml，添加 ui optional-dependency**

将文件内容改为：

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "content-extract"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1",
    "toml>=0.10",
]

[project.optional-dependencies]
# Phase 1 核心提取器依赖（按需安装）
web = ["crawl4ai"]
video = ["yt-dlp", "faster-whisper"]
all = ["crawl4ai", "yt-dlp", "faster-whisper"]
dev = ["pytest>=7.0"]
# TUI 界面
ui = ["textual>=0.61.0"]

[project.scripts]
content-extract = "content_extract.cli:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["content_extract*"]
```

- [ ] **步骤 4：更新 requirements.txt，添加 ui 分组**

在文件末尾 `# ui（Phase 2，占位）` 一行改为：

```text
# core
click>=8.1
toml>=0.10

# web
crawl4ai

# video
yt-dlp
faster-whisper

# dev/test
pytest>=7.0

# ebook（Phase 2，占位）
# ebooklib
# beautifulsoup4
# pymupdf4llm

# rag（Phase 4，占位）
# chromadb
# sentence-transformers

# ui
textual>=0.61.0
# streamlit（Phase 4，占位）
```

- [ ] **步骤 5：提交**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
git add pyproject.toml requirements.txt
git commit -m "feat: 添加 textual 到 ui optional-dependency"
```

---

## Task 2：创建 ui/__init__.py（空包标记）

**文件：**
- 新建：`content-extract/content_extract/ui/__init__.py`

- [ ] **步骤 1：创建目录和空文件**

```bash
mkdir -p /Users/I340818/Documents/ai_workspace/content-extract/content_extract/ui
touch /Users/I340818/Documents/ai_workspace/content-extract/content_extract/ui/__init__.py
```

- [ ] **步骤 2：验证包可识别**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
python3 -c "import content_extract.ui; print('ui 包导入成功')"
```

预期：`ui 包导入成功`

- [ ] **步骤 3：提交**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
git add content_extract/ui/__init__.py
git commit -m "feat: 添加 ui 包目录"
```

---

## Task 3：实现 ui/tui.py（TUI 主体）

**文件：**
- 新建：`content-extract/content_extract/ui/tui.py`

- [ ] **步骤 1：写 tui.py 完整实现**

路径：`/Users/I340818/Documents/ai_workspace/content-extract/content_extract/ui/tui.py`

```python
from __future__ import annotations

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
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Select,
    Static,
)
from textual.worker import work


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
    def __init__(self, source: str, source_type: str, update_wiki: bool = False) -> None:
        super().__init__()
        self.source = source
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
        with Horizontal():
            yield Button("提取", id="btn-extract", variant="primary")
            yield Button("提取并更新 Wiki", id="btn-extract-wiki")

    def on_input_changed(self, event: Input.Changed) -> None:
        """输入变化时自动识别类型，仅在用户选「自动识别」时生效。"""
        if event.input.id != "url-input":
            return
        select = self.query_one("#type-select", Select)
        if select.value == "auto":
            # 根据当前输入内容推测类型，但不强制改变 Select 的选中值
            # （Select 保持 auto，提交时再解析）
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        url_input = self.query_one("#url-input", Input)
        type_select = self.query_one("#type-select", Select)
        source = url_input.value.strip()
        if not source:
            return

        # 类型解析：auto 时调用自动识别函数
        raw_type = str(type_select.value)
        source_type = detect_source_type(source) if raw_type == "auto" else raw_type

        update_wiki = event.button.id == "btn-extract-wiki"
        self.post_message(ExtractRequested(source=source, source_type=source_type, update_wiki=update_wiki))

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
            output_short = Path(t.output_file).name if t.output_file else (t.error[:30] if t.error else "—")
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
    BINDINGS = [
        Binding("q", "quit", "退出", show=True),
        Binding("r", "retry_failed", "重试失败", show=True),
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
    """

    def __init__(self) -> None:
        super().__init__()
        # 内存中的任务列表，启动时从 registry 加载
        self._tasks: list[TaskEntry] = []
        # 从 config 加载 cookie 路径
        self._cookies: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="top-row"):
            yield AddSourcePanel()
            yield QueuePanel()
        yield LogPanel(id="log-area")
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
        """向日志面板写入一行消息，线程安全。"""
        log_panel = self.query_one(LogPanel)
        log_panel.write(msg)

    def on_extract_requested(self, event: ExtractRequested) -> None:
        """处理提取请求：追加任务到列表并启动 worker。"""
        entry = TaskEntry(
            source=event.source,
            source_type=event.source_type,
            status="extracting",
        )
        self._tasks.append(entry)
        self._refresh_queue()
        self.log_message(f"开始提取 [{event.source_type}]: {event.source}")
        self._run_extract(event.source, event.source_type, event.update_wiki)

    def on_extract_done(self, event: ExtractDone) -> None:
        """提取完成后更新内存状态并刷新队列。"""
        for t in self._tasks:
            if t.source == event.source and t.status == "extracting":
                t.status = "done" if event.success else "failed"
                t.output_file = event.output_file
                t.error = event.error
                break
        self._refresh_queue()
        if event.success:
            self.log_message(f"[green]✓ 完成 → {event.output_file}[/green]")
        else:
            self.log_message(f"[red]✗ 失败：{event.error}[/red]")

    @work(thread=True)
    def _run_extract(self, source: str, source_type: str, update_wiki: bool) -> None:
        """在独立线程执行提取，通过 call_from_thread 回调日志。"""
        def on_progress(msg: str) -> None:
            self.call_from_thread(self.log_message, msg)

        try:
            from ..extractors.base import ExtractConfig
            cfg = ExtractConfig(output_dir=Path("./raw"), cookies=self._cookies)

            if source_type == "web":
                from ..extractors.web import WebExtractor
                extractor = WebExtractor(config=cfg, on_progress=on_progress)
                out = extractor.extract(source)
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
                self.call_from_thread(self.app.push_screen, WikiModal())

        except Exception as e:
            self.post_message(ExtractDone(source=source, success=False, error=str(e)))

    def action_quit(self) -> None:
        """退出应用。"""
        self.exit()

    def action_retry_failed(self) -> None:
        """重试当前选中的失败任务（如有）。"""
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
```

- [ ] **步骤 2：验证 tui.py 可导入（不启动 UI）**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
python3 -c "from content_extract.ui.tui import TUIApp, detect_source_type; print('导入成功')"
```

预期：`导入成功`，无报错。

- [ ] **步骤 3：验证 detect_source_type 逻辑**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
python3 -c "
from content_extract.ui.tui import detect_source_type
assert detect_source_type('https://www.bilibili.com/video/BV123') == 'video'
assert detect_source_type('https://github.com/owner/repo') == 'github'
assert detect_source_type('https://example.com/article') == 'article'
assert detect_source_type('./book.epub') == 'ebook'
print('✓ detect_source_type 全部通过')
"
```

预期：`✓ detect_source_type 全部通过`

- [ ] **步骤 4：提交**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
git add content_extract/ui/tui.py
git commit -m "feat: 实现 Textual TUI 主体（TUIApp + 三个面板 + worker 线程）"
```

---

## Task 4：修改 cli.py（替换占位提示）

**文件：**
- 修改：`content-extract/content_extract/cli.py` 第 18-19 行

- [ ] **步骤 1：替换占位提示**

将 `cli.py` 第 18-19 行：
```python
    if ctx.invoked_subcommand is None:
        click.echo("TUI 即将上线，当前请使用子命令。运行 content-extract --help 查看可用命令。")
```
替换为：
```python
    if ctx.invoked_subcommand is None:
        from .ui.tui import TUIApp
        TUIApp().run()
```

- [ ] **步骤 2：验证 CLI 子命令未受影响**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
content-extract --help
content-extract web --help
content-extract status
```

预期：`--help` 正常显示所有子命令；`status` 显示队列状态（不启动 TUI）。

- [ ] **步骤 3：提交**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
git add content_extract/cli.py
git commit -m "feat: cli.py 无参数时启动 TUIApp（替换占位提示）"
```

---

## Task 5：实现 tests/test_tui.py

**文件：**
- 新建：`content-extract/tests/test_tui.py`

- [ ] **步骤 1：写测试文件**

路径：`/Users/I340818/Documents/ai_workspace/content-extract/tests/test_tui.py`

```python
import pytest
from unittest.mock import patch, MagicMock
from textual.testing import Pilot
from content_extract.ui.tui import TUIApp, detect_source_type


# ── detect_source_type 单元测试（无需 Pilot，速度快）─────────────────────────

def test_detect_bilibili_url():
    assert detect_source_type("https://www.bilibili.com/video/BV1abc") == "video"


def test_detect_b23_url():
    assert detect_source_type("https://b23.tv/xxxxx") == "video"


def test_detect_github_url():
    assert detect_source_type("https://github.com/owner/repo") == "github"


def test_detect_generic_url():
    assert detect_source_type("https://example.com/blog/article") == "article"


def test_detect_epub_file():
    assert detect_source_type("./book.epub") == "ebook"


def test_detect_pdf_file():
    assert detect_source_type("/path/to/paper.pdf") == "ebook"


# ── Textual Pilot 集成测试 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_app_launches():
    """app 能正常启动并通过 q 退出。"""
    app = TUIApp()
    async with app.run_test() as pilot:
        await pilot.press("q")


@pytest.mark.asyncio
async def test_log_panel_exists():
    """LogPanel 的 #log RichLog 存在于 DOM。"""
    app = TUIApp()
    async with app.run_test() as pilot:
        log = app.query_one("#log")
        assert log is not None
        await pilot.press("q")


@pytest.mark.asyncio
async def test_queue_empty_on_start(tmp_path, monkeypatch):
    """无 registry 文件时，队列面板初始行数为 0。"""
    # 将工作目录切换到没有 .processed.json 的临时目录
    monkeypatch.chdir(tmp_path)
    app = TUIApp()
    async with app.run_test() as pilot:
        from textual.widgets import DataTable
        table = app.query_one("#queue-table", DataTable)
        assert table.row_count == 0
        await pilot.press("q")


@pytest.mark.asyncio
async def test_keyboard_quit():
    """按 Q 键能正常退出，不抛异常。"""
    app = TUIApp()
    async with app.run_test() as pilot:
        await pilot.press("Q")  # 大写 Q


@pytest.mark.asyncio
async def test_input_url_sets_extract_ready(tmp_path, monkeypatch):
    """在 URL 输入框输入 bilibili URL 后，按 Enter 提交不报错（提取被 mock）。"""
    monkeypatch.chdir(tmp_path)
    # mock 提取器，防止真实网络请求
    with patch("content_extract.ui.tui.TUIApp._run_extract"):
        app = TUIApp()
        async with app.run_test() as pilot:
            await pilot.click("#url-input")
            await pilot.type("https://www.bilibili.com/video/BV1abc")
            # 验证输入框有内容
            from textual.widgets import Input
            url_input = app.query_one("#url-input", Input)
            assert "bilibili" in url_input.value
            await pilot.press("q")
```

- [ ] **步骤 2：安装 pytest-asyncio（Textual 测试需要）**

```bash
pip install pytest-asyncio -q
```

- [ ] **步骤 3：运行测试**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
pytest tests/test_tui.py -v --tb=short 2>&1
```

预期：所有测试通过（detect 6 个 + Pilot 5 个 = 11 个）。

- [ ] **步骤 4：提交**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
git add tests/test_tui.py
git commit -m "test: 添加 TUI 测试（detect_source_type + Pilot 集成测试）"
```

---

## Task 6：全量验收

- [ ] **步骤 1：运行全量测试套件**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
pytest tests/ -v --tb=short 2>&1 | tail -20
```

预期：所有测试 PASS（原有 70 个 + 新增 11 个 = 约 81 个）。

- [ ] **步骤 2：验证 CLI 子命令未被破坏**

```bash
content-extract --help
content-extract web --help
content-extract status
```

预期：正常输出，不启动 TUI。

- [ ] **步骤 3：冒烟测试 TUI 启动**

```bash
cd /tmp && mkdir tui_smoke && cd tui_smoke
content-extract
# 预期：全屏 TUI 启动，显示三个面板
# 按 q 退出
```

- [ ] **步骤 4：验证队列历史加载**

```bash
cd /tmp/ce_bfs   # 使用之前爬取过的测试目录
content-extract
# 预期：TUI 启动后 QueuePanel 显示之前爬取的历史记录
# 按 q 退出
```

- [ ] **步骤 5：最终提交（若有遗漏改动）**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
git status
# 若有未提交文件则 git add + git commit
git log --oneline -5
```

---

## 自审检查结果

**Spec 覆盖：**
- ✅ ui/__init__.py（Task 2）
- ✅ ui/tui.py 完整实现：TUIApp、AddSourcePanel、QueuePanel、LogPanel、WikiModal（Task 3）
- ✅ TaskEntry dataclass（Task 3）
- ✅ ExtractRequested / ExtractDone 消息（Task 3）
- ✅ detect_source_type 函数（Task 3）
- ✅ @work(thread=True) worker 线程（Task 3）
- ✅ cli.py 无参数启动 TUIApp（Task 4）
- ✅ pyproject.toml / requirements.txt 添加 textual（Task 1）
- ✅ tests/test_tui.py 5 个 Pilot 测试 + 6 个单元测试（Task 5）
- ✅ BINDINGS：q 退出、r 重试、o 打开 Obsidian（Task 3）
- ✅ 启动时加载 registry 历史（Task 3 `_load_registry`）

**类型一致性：**
- `TaskEntry.status` 在 Task 3 定义，`_STATUS_ICONS` 键值一致
- `ExtractRequested(source, source_type, update_wiki)` 在 Task 3 定义，`on_extract_requested` 正确使用
- `ExtractDone(source, success, output_file, error)` 在 Task 3 定义，`on_extract_done` 正确使用
- `QueuePanel.refresh_table(tasks: list[TaskEntry])` 签名与 `_refresh_queue` 调用一致
