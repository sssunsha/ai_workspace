# claude-hunter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a PyQt6 desktop app that wraps Claude Code CLI in a visual UI with left sidebar (skills/tasks) and right chat panel (output + input + autocomplete).

**Architecture:** A `PtyWorker` (QThread + ptyprocess) owns the Claude CLI subprocess and communicates via signals/slots with the UI. The UI is split into a fixed-width `Sidebar` and a stretchy `ChatPanel` inside a `QSplitter`. All CLI interaction goes through the PTY worker; the UI never touches the subprocess directly.

**Tech Stack:** Python 3.8+, PyQt6, ptyprocess, pytest, pyinstaller

---

## File Map

| File | Responsibility |
|------|---------------|
| `main.py` | Entry point — create QApplication, show MainWindow |
| `app/__init__.py` | Package marker |
| `app/ui/__init__.py` | Package marker |
| `app/core/__init__.py` | Package marker |
| `app/core/pty_worker.py` | `PtyWorker(QThread)` — owns ptyprocess, emits output signals |
| `app/core/skill_scanner.py` | `scan_skills()` — scan `~/.claude/plugins` for skill names |
| `app/core/task_loader.py` | `Task` dataclass + `load_tasks()` — parse tasks/ JSON/MD |
| `app/ui/main_window.py` | `MainWindow(QMainWindow)` — QSplitter, dark theme, wires signals |
| `app/ui/sidebar.py` | `Sidebar(QWidget)` — new/clear buttons, skill list, task list |
| `app/ui/chat_panel.py` | `ChatPanel(QWidget)` + `InputBox(QTextEdit)` — output, input, quick buttons |
| `app/ui/autocomplete.py` | `AutoCompleteWidget(QListWidget)` — floating `:` `/` dropdown |
| `tasks/代码审查.json` | Sample JSON task config |
| `tasks/查bug.md` | Sample MD task config |
| `requirements.txt` | PyQt6, ptyprocess |
| `claude-hunter.spec` | pyinstaller spec for .app packaging |
| `tests/core/test_task_loader.py` | Unit tests for TaskLoader |
| `tests/core/test_skill_scanner.py` | Unit tests for SkillScanner |
| `tests/core/test_pty_worker.py` | Integration test for PtyWorker (spawns `echo`) |

---

### Task 1: Project scaffold

**Files:**
- Create: `app/__init__.py`
- Create: `app/core/__init__.py`
- Create: `app/ui/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/core/__init__.py`
- Create: `requirements.txt`
- Create: `tasks/` (empty directory)

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p app/core app/ui tests/core tasks assets
touch app/__init__.py app/core/__init__.py app/ui/__init__.py
touch tests/__init__.py tests/core/__init__.py
```

- [ ] **Step 2: Write requirements.txt**

```
PyQt6>=6.4.0
ptyprocess>=0.7.0
pytest>=7.0.0
```

- [ ] **Step 3: Install dependencies**

```bash
pip install PyQt6 ptyprocess pytest
```

Expected: all packages install without error.

- [ ] **Step 4: Commit**

```bash
git add app/ tests/ tasks/ assets/ requirements.txt
git commit -m "chore: 项目脚手架初始化"
```

---

### Task 2: ANSI 剥离工具 + 单元测试

**Files:**
- Create: `app/core/pty_worker.py` (仅 `strip_ansi` 函数)
- Create: `tests/core/test_pty_worker.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/core/test_pty_worker.py`：

```python
import pytest
from app.core.pty_worker import strip_ansi


def test_strip_ansi_removes_color_codes():
    assert strip_ansi("\x1b[32mhello\x1b[0m") == "hello"


def test_strip_ansi_removes_cursor_movement():
    assert strip_ansi("\x1b[2Kfoo") == "foo"


def test_strip_ansi_leaves_plain_text_unchanged():
    assert strip_ansi("hello world") == "hello world"


def test_strip_ansi_preserves_newlines():
    assert strip_ansi("line1\nline2") == "line1\nline2"


def test_strip_ansi_handles_empty_string():
    assert strip_ansi("") == ""
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
pytest tests/core/test_pty_worker.py -v
```

期望：`ImportError: cannot import name 'strip_ansi'`

- [ ] **Step 3: 实现 strip_ansi**

创建 `app/core/pty_worker.py`（此步仅写 strip_ansi，PtyWorker 类在 Task 5 补充）：

```python
import os
import re

from PyQt6.QtCore import QThread, pyqtSignal

_ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*[mGKHFJA-Za-z]')


def strip_ansi(text: str) -> str:
    return _ANSI_ESCAPE.sub('', text)
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
pytest tests/core/test_pty_worker.py -v
```

期望：5 个测试全部 PASS。

- [ ] **Step 5: Commit**

```bash
git add app/core/pty_worker.py tests/core/test_pty_worker.py
git commit -m "feat: 实现 strip_ansi 工具函数"
```

---

### Task 3: TaskLoader + 单元测试

**Files:**
- Create: `app/core/task_loader.py`
- Create: `tests/core/test_task_loader.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/core/test_task_loader.py`：

```python
import json
import pytest
from pathlib import Path
from app.core.task_loader import Task, load_tasks


def test_load_json_task(tmp_path):
    task_file = tmp_path / "审查.json"
    task_file.write_text(json.dumps({
        "name": "🔍 代码审查",
        "prompt": "请审查代码",
        "cli_args": "--model sonnet"
    }), encoding="utf-8")

    tasks, warnings = load_tasks(tmp_path)

    assert len(tasks) == 1
    assert tasks[0].name == "🔍 代码审查"
    assert tasks[0].prompt == "请审查代码"
    assert tasks[0].cli_args == "--model sonnet"
    assert warnings == []


def test_load_md_task(tmp_path):
    task_file = tmp_path / "查bug.md"
    task_file.write_text("帮我找bug\n1. 根源\n2. 修复", encoding="utf-8")

    tasks, warnings = load_tasks(tmp_path)

    assert len(tasks) == 1
    assert tasks[0].name == "查bug"
    assert tasks[0].prompt == "帮我找bug\n1. 根源\n2. 修复"
    assert tasks[0].cli_args == ""


def test_load_tasks_creates_dir_if_missing(tmp_path):
    missing = tmp_path / "nonexistent"
    tasks, warnings = load_tasks(missing)
    assert tasks == []
    assert warnings == []
    assert missing.exists()


def test_load_tasks_skips_bad_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json}", encoding="utf-8")

    tasks, warnings = load_tasks(tmp_path)

    assert tasks == []
    assert len(warnings) == 1
    assert "bad.json" in warnings[0]


def test_load_tasks_json_without_cli_args(tmp_path):
    task_file = tmp_path / "simple.json"
    task_file.write_text(json.dumps({
        "name": "简单任务",
        "prompt": "做点什么"
    }), encoding="utf-8")

    tasks, _ = load_tasks(tmp_path)

    assert tasks[0].cli_args == ""


def test_load_tasks_ignores_non_json_md_files(tmp_path):
    (tmp_path / "readme.txt").write_text("ignore me")
    (tmp_path / ".DS_Store").write_bytes(b"\x00")

    tasks, warnings = load_tasks(tmp_path)

    assert tasks == []
    assert warnings == []
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
pytest tests/core/test_task_loader.py -v
```

期望：`ModuleNotFoundError: No module named 'app.core.task_loader'`

- [ ] **Step 3: 实现 TaskLoader**

创建 `app/core/task_loader.py`：

```python
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Task:
    name: str
    prompt: str
    cli_args: str = ""


def load_tasks(tasks_dir: Path) -> tuple[list[Task], list[str]]:
    if not tasks_dir.exists():
        tasks_dir.mkdir(parents=True, exist_ok=True)
        return [], []

    tasks: list[Task] = []
    warnings: list[str] = []

    for path in sorted(tasks_dir.iterdir()):
        if path.suffix == ".json":
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                tasks.append(Task(
                    name=data["name"],
                    prompt=data["prompt"],
                    cli_args=data.get("cli_args", ""),
                ))
            except Exception as e:
                warnings.append(f"跳过 {path.name}: {e}")
        elif path.suffix == ".md":
            try:
                content = path.read_text(encoding="utf-8").strip()
                tasks.append(Task(name=path.stem, prompt=content))
            except Exception as e:
                warnings.append(f"跳过 {path.name}: {e}")

    return tasks, warnings
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
pytest tests/core/test_task_loader.py -v
```

期望：6 个测试全部 PASS。

- [ ] **Step 5: Commit**

```bash
git add app/core/task_loader.py tests/core/test_task_loader.py
git commit -m "feat: 实现 TaskLoader（JSON/MD 任务解析）"
```

---

### Task 4: SkillScanner + 单元测试

**Files:**
- Create: `app/core/skill_scanner.py`
- Create: `tests/core/test_skill_scanner.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/core/test_skill_scanner.py`：

```python
from pathlib import Path
from app.core.skill_scanner import scan_skills, get_builtin_commands


def test_scan_skills_finds_skill_dirs(tmp_path):
    plugins = tmp_path / "plugins"
    plugin_a = plugins / "my-plugin" / "skills" / "code-review"
    plugin_b = plugins / "my-plugin" / "skills" / "python-dev"
    plugin_a.mkdir(parents=True)
    plugin_b.mkdir(parents=True)

    skills = scan_skills(base_dir=plugins)

    assert "code-review" in skills
    assert "python-dev" in skills


def test_scan_skills_deduplicates(tmp_path):
    plugins = tmp_path / "plugins"
    (plugins / "plugin-a" / "skills" / "debug").mkdir(parents=True)
    (plugins / "cache" / "plugin-b" / "skills" / "debug").mkdir(parents=True)

    skills = scan_skills(base_dir=plugins)

    assert skills.count("debug") == 1


def test_scan_skills_returns_sorted(tmp_path):
    plugins = tmp_path / "plugins"
    (plugins / "p" / "skills" / "zzz").mkdir(parents=True)
    (plugins / "p" / "skills" / "aaa").mkdir(parents=True)

    skills = scan_skills(base_dir=plugins)

    assert skills == sorted(skills)


def test_scan_skills_missing_dir_returns_empty(tmp_path):
    skills = scan_skills(base_dir=tmp_path / "nonexistent")
    assert skills == []


def test_scan_skills_ignores_files_in_skills_dir(tmp_path):
    plugins = tmp_path / "plugins"
    skills_dir = plugins / "p" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "readme.md").write_text("not a skill")

    skills = scan_skills(base_dir=plugins)

    assert skills == []


def test_get_builtin_commands_returns_list():
    commands = get_builtin_commands()
    assert "/help" in commands
    assert "/new" in commands
    assert isinstance(commands, list)
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
pytest tests/core/test_skill_scanner.py -v
```

期望：`ModuleNotFoundError: No module named 'app.core.skill_scanner'`

- [ ] **Step 3: 实现 SkillScanner**

创建 `app/core/skill_scanner.py`：

```python
from pathlib import Path

_BUILTIN_COMMANDS = [
    "/help", "/new", "/clear", "/review", "/cost",
    "/compact", "/config", "/quit", "/exit", "/memory",
]


def scan_skills(base_dir: Path = None) -> list[str]:
    if base_dir is None:
        base_dir = Path.home() / ".claude" / "plugins"

    skills: set[str] = set()

    for search_path in [base_dir, base_dir / "cache"]:
        if not search_path.exists():
            continue
        for plugin_dir in search_path.iterdir():
            if not plugin_dir.is_dir():
                continue
            skills_dir = plugin_dir / "skills"
            if skills_dir.exists():
                for entry in skills_dir.iterdir():
                    if entry.is_dir():
                        skills.add(entry.name)

    return sorted(skills)


def get_builtin_commands() -> list[str]:
    return list(_BUILTIN_COMMANDS)
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
pytest tests/core/test_skill_scanner.py -v
```

期望：6 个测试全部 PASS。

- [ ] **Step 5: Commit**

```bash
git add app/core/skill_scanner.py tests/core/test_skill_scanner.py
git commit -m "feat: 实现 SkillScanner（扫描本地 Claude skills）"
```

---

### Task 5: PtyWorker — 完整实现 + 集成测试

**Files:**
- Modify: `app/core/pty_worker.py`
- Modify: `tests/core/test_pty_worker.py`

- [ ] **Step 1: 在测试文件末尾追加集成测试**

在 `tests/core/test_pty_worker.py` 末尾追加：

```python
import time
from PyQt6.QtWidgets import QApplication
from app.core.pty_worker import PtyWorker

# 需要 QApplication 才能使用 Qt 信号槽
@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def test_pty_worker_emits_output(qt_app):
    received = []
    worker = PtyWorker(cli_cmd="echo", cli_args=["hello pty"])
    worker.output_received.connect(lambda t: received.append(t))
    worker.start()
    worker.wait(3000)  # 最多等 3 秒

    combined = "".join(received)
    assert "hello pty" in combined


def test_pty_worker_emits_error_for_bad_command(qt_app):
    errors = []
    worker = PtyWorker(cli_cmd="__nonexistent_cmd_xyz__")
    worker.process_error.connect(lambda e: errors.append(e))
    worker.start()
    worker.wait(3000)

    assert len(errors) == 1
    assert "__nonexistent_cmd_xyz__" in errors[0]
```

- [ ] **Step 2: 运行新测试，确认失败**

```bash
pytest tests/core/test_pty_worker.py::test_pty_worker_emits_output -v
```

期望：`AttributeError: PtyWorker` 或 class 不完整报错。

- [ ] **Step 3: 补全 PtyWorker 类**

将 `app/core/pty_worker.py` 替换为：

```python
import os
import re

import ptyprocess
from PyQt6.QtCore import QThread, pyqtSignal

_ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*[mGKHFJA-Za-z]')


def strip_ansi(text: str) -> str:
    return _ANSI_ESCAPE.sub('', text)


class PtyWorker(QThread):
    output_received = pyqtSignal(str)
    process_finished = pyqtSignal()
    process_error = pyqtSignal(str)

    def __init__(self, cli_cmd: str = "claude", cli_args: list = None, parent=None):
        super().__init__(parent)
        self._cli_cmd = cli_cmd
        self._cli_args = cli_args or []
        self._process: ptyprocess.PtyProcess | None = None
        self._running = False

    def run(self):
        cmd = [self._cli_cmd] + self._cli_args
        try:
            self._process = ptyprocess.PtyProcess.spawn(
                cmd, env=os.environ.copy()
            )
        except FileNotFoundError:
            self.process_error.emit(
                f"命令 '{self._cli_cmd}' 未找到。\n请确认 Claude Code CLI 已正确安装，"
                "且可在终端通过 'claude' 命令调用。"
            )
            return
        except Exception as e:
            self.process_error.emit(str(e))
            return

        self._running = True
        while self._running and self._process.isalive():
            try:
                data = self._process.read(4096)
                text = data.decode("utf-8", errors="replace")
                clean = strip_ansi(text)
                if clean:
                    self.output_received.emit(clean)
            except EOFError:
                break
            except Exception:
                break

        self.process_finished.emit()

    def write(self, text: str):
        if self._process and self._process.isalive():
            if not text.endswith("\n"):
                text += "\n"
            self._process.write(text.encode())

    def stop(self):
        self._running = False
        if self._process and self._process.isalive():
            try:
                self._process.terminate(force=True)
            except Exception:
                pass
        self.wait(2000)
```

- [ ] **Step 4: 运行全部 pty_worker 测试，确认通过**

```bash
pytest tests/core/test_pty_worker.py -v
```

期望：7 个测试全部 PASS（5 个 strip_ansi + 2 个集成测试）。

- [ ] **Step 5: Commit**

```bash
git add app/core/pty_worker.py tests/core/test_pty_worker.py
git commit -m "feat: 实现 PtyWorker（PTY 子进程驱动）"
```

---

### Task 6: AutoCompleteWidget

**Files:**
- Create: `app/ui/autocomplete.py`

- [ ] **Step 1: 创建 `app/ui/autocomplete.py`**

```python
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import QListWidget, QListWidgetItem

_STYLE = """
QListWidget {
    background-color: #252526;
    color: #d4d4d4;
    border: 1px solid #555;
    border-radius: 4px;
    font-size: 12px;
    font-family: Menlo, Monaco, 'Courier New', monospace;
    outline: none;
}
QListWidget::item { padding: 3px 8px; }
QListWidget::item:selected { background-color: #0e639c; color: white; }
QListWidget::item:hover { background-color: #2a2d2e; }
"""


class AutoCompleteWidget(QListWidget):
    item_selected = pyqtSignal(str)

    def __init__(self, skills: list, commands: list, parent=None):
        super().__init__(parent)
        self._skills = skills
        self._commands = commands
        self.setStyleSheet(_STYLE)
        self.setFixedWidth(300)
        self.setWindowFlags(Qt.WindowType.Popup)
        self.hide()
        self.itemClicked.connect(lambda item: self.item_selected.emit(item.text()))

    def show_skills(self, prefix: str):
        matches = [f":{s}" for s in self._skills if s.startswith(prefix)]
        self._populate(matches)

    def show_commands(self, prefix: str):
        matches = [c for c in self._commands if c.lstrip("/").startswith(prefix)]
        self._populate(matches)

    def _populate(self, items: list):
        self.clear()
        for text in items[:8]:
            self.addItem(QListWidgetItem(text))
        if self.count():
            self.setFixedHeight(min(self.count() * 26 + 6, 210))
            self.show()
        else:
            self.hide()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab):
            item = self.currentItem()
            if item:
                self.item_selected.emit(item.text())
        elif event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)
```

- [ ] **Step 2: 运行烟雾测试（Python 导入不报错）**

```bash
python -c "from app.ui.autocomplete import AutoCompleteWidget; print('OK')"
```

期望：打印 `OK`，无报错。

- [ ] **Step 3: Commit**

```bash
git add app/ui/autocomplete.py
git commit -m "feat: 实现 AutoCompleteWidget（: / 补全下拉）"
```

---

### Task 7: ChatPanel（输出区 + 快捷按钮 + 输入框）

**Files:**
- Create: `app/ui/chat_panel.py`

- [ ] **Step 1: 创建 `app/ui/chat_panel.py`**

```python
from PyQt6.QtCore import pyqtSignal, Qt, QPoint
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton,
)

from app.ui.autocomplete import AutoCompleteWidget

_QUICK_PROMPTS = [
    ("解释代码", "请解释以下代码的作用和实现逻辑：\n"),
    ("找 Bug",   "请帮我找出以下代码中的 bug，并说明原因和修复方案：\n"),
    ("重构代码", "请帮我重构以下代码，提升可读性和性能：\n"),
]

_OUTPUT_STYLE = """
QTextEdit {
    background-color: #1e1e1e;
    color: #d4d4d4;
    border: none;
    font-family: Menlo, Monaco, 'Courier New', monospace;
    font-size: 13px;
    padding: 8px;
}
"""

_INPUT_STYLE = """
QTextEdit {
    background-color: #2d2d2d;
    color: #d4d4d4;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    font-family: Menlo, Monaco, 'Courier New', monospace;
    font-size: 13px;
    padding: 6px;
}
"""

_QUICK_BTN_STYLE = """
QPushButton {
    background-color: #2d2d2d;
    color: #9cdcfe;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 12px;
}
QPushButton:hover { background-color: #3a3a3a; }
"""

_SEND_BTN_STYLE = """
QPushButton {
    background-color: #0e639c;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 18px;
    font-size: 13px;
}
QPushButton:hover { background-color: #1177bb; }
"""


class _InputBox(QTextEdit):
    """QTextEdit，Enter 发送，Shift+Enter 换行。"""
    send_triggered = pyqtSignal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.send_triggered.emit()
        else:
            super().keyPressEvent(event)


class ChatPanel(QWidget):
    send_requested = pyqtSignal(str)

    def __init__(self, skills: list, commands: list, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 输出区
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setStyleSheet(_OUTPUT_STYLE)
        layout.addWidget(self._output, stretch=1)

        # 快捷按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        for label, prompt in _QUICK_PROMPTS:
            btn = QPushButton(label)
            btn.setStyleSheet(_QUICK_BTN_STYLE)
            btn.clicked.connect(lambda _, p=prompt: self.fill_input(p))
            btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # 输入框
        self._input = _InputBox()
        self._input.setStyleSheet(_INPUT_STYLE)
        self._input.setMaximumHeight(120)
        self._input.setPlaceholderText(
            "输入消息... (Enter 发送, Shift+Enter 换行, : 触发技能, / 触发命令)"
        )
        self._input.send_triggered.connect(self._on_send)
        self._input.textChanged.connect(self._on_input_changed)
        layout.addWidget(self._input)

        # 发送按钮行
        send_row = QHBoxLayout()
        send_row.addStretch()
        send_btn = QPushButton("发送")
        send_btn.setStyleSheet(_SEND_BTN_STYLE)
        send_btn.clicked.connect(self._on_send)
        send_row.addWidget(send_btn)
        layout.addLayout(send_row)

        # 补全浮窗（独立顶层窗口）
        self._autocomplete = AutoCompleteWidget(skills, commands)
        self._autocomplete.item_selected.connect(self._on_autocomplete_selected)

    # ── 公开 API ────────────────────────────────────────────────

    def append_output(self, text: str):
        cursor = self._output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._output.setTextCursor(cursor)
        self._output.insertPlainText(text)
        self._output.ensureCursorVisible()

    def clear_output(self):
        self._output.clear()

    def fill_input(self, text: str):
        self._input.setPlainText(text)
        self._input.moveCursor(QTextCursor.MoveOperation.End)
        self._input.setFocus()

    # ── 私有槽 ──────────────────────────────────────────────────

    def _on_send(self):
        text = self._input.toPlainText().strip()
        if text:
            self._input.clear()
            self._autocomplete.hide()
            self.send_requested.emit(text)

    def _on_input_changed(self):
        text = self._input.toPlainText().lstrip()
        if not text:
            self._autocomplete.hide()
            return
        if text.startswith(":"):
            self._autocomplete.show_skills(text[1:])
            self._reposition_autocomplete()
        elif text.startswith("/"):
            self._autocomplete.show_commands(text[1:])
            self._reposition_autocomplete()
        else:
            self._autocomplete.hide()

    def _reposition_autocomplete(self):
        global_pos = self._input.mapToGlobal(QPoint(0, 0))
        self._autocomplete.move(
            global_pos.x(),
            global_pos.y() - self._autocomplete.height() - 4,
        )

    def _on_autocomplete_selected(self, text: str):
        self._input.setPlainText(text)
        self._input.moveCursor(QTextCursor.MoveOperation.End)
        self._autocomplete.hide()
```

- [ ] **Step 2: 导入烟雾测试**

```bash
python -c "from app.ui.chat_panel import ChatPanel; print('OK')"
```

期望：打印 `OK`，无报错。

- [ ] **Step 3: Commit**

```bash
git add app/ui/chat_panel.py
git commit -m "feat: 实现 ChatPanel（输出区 + 快捷按钮 + 输入框）"
```

---

### Task 8: Sidebar

**Files:**
- Create: `app/ui/sidebar.py`

- [ ] **Step 1: 创建 `app/ui/sidebar.py`**

```python
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame,
)

from app.core.task_loader import Task

_STYLESHEET = """
QWidget#sidebar {
    background-color: #252526;
}
QPushButton {
    background-color: #0e639c;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 6px 8px;
    text-align: left;
    font-size: 12px;
}
QPushButton:hover { background-color: #1177bb; }
QPushButton#danger { background-color: #6b2a2a; }
QPushButton#danger:hover { background-color: #8b3a3a; }
QPushButton#highlight { background-color: #e8a838; color: #000; }
QLabel#section { color: #888888; font-size: 11px; font-weight: bold; }
QLabel#title { color: #d4d4d4; font-size: 14px; font-weight: bold; }
QScrollArea { border: none; background: transparent; }
"""


class Sidebar(QWidget):
    new_conversation_requested = pyqtSignal()
    clear_output_requested = pyqtSignal()
    task_send_requested = pyqtSignal(str)
    skill_fill_requested = pyqtSignal(str)

    def __init__(self, skills: list, tasks: list, warnings: list, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(220)
        self.setStyleSheet(_STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(6)

        # 标题
        title = QLabel("claude-hunter")
        title.setObjectName("title")
        layout.addWidget(title)
        layout.addWidget(_separator())

        # 操作按钮
        self._new_btn = QPushButton("＋ 新对话")
        self._new_btn.clicked.connect(self.new_conversation_requested)
        layout.addWidget(self._new_btn)

        clear_btn = QPushButton("✕ 清空输出")
        clear_btn.setObjectName("danger")
        clear_btn.clicked.connect(self.clear_output_requested)
        layout.addWidget(clear_btn)

        layout.addWidget(_separator())

        # 快速技能
        if skills:
            skill_label = QLabel("快速技能")
            skill_label.setObjectName("section")
            layout.addWidget(skill_label)

            skill_scroll = _scroll_area(max_height=200)
            container = QWidget()
            cl = QVBoxLayout(container)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.setSpacing(3)
            for skill in skills[:20]:
                btn = QPushButton(f": {skill}")
                btn.clicked.connect(
                    lambda _, s=skill: self.skill_fill_requested.emit(f":{s}")
                )
                cl.addWidget(btn)
            skill_scroll.setWidget(container)
            layout.addWidget(skill_scroll)
            layout.addWidget(_separator())

        # 自定义任务
        task_label = QLabel("自定义任务")
        task_label.setObjectName("section")
        layout.addWidget(task_label)

        task_scroll = _scroll_area(max_height=250)
        t_container = QWidget()
        tl = QVBoxLayout(t_container)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(3)

        if tasks:
            for task in tasks:
                btn = QPushButton(task.name)
                btn.clicked.connect(
                    lambda _, p=task.prompt: self.task_send_requested.emit(p)
                )
                tl.addWidget(btn)
        else:
            empty = QLabel("tasks/ 文件夹为空")
            empty.setObjectName("section")
            tl.addWidget(empty)

        task_scroll.setWidget(t_container)
        layout.addWidget(task_scroll)

        # 警告标签
        for w in warnings:
            warn = QLabel(f"⚠ {w}")
            warn.setWordWrap(True)
            warn.setStyleSheet("color: #e8a838; font-size: 10px;")
            layout.addWidget(warn)

        layout.addStretch()

    def highlight_new_conversation(self):
        self._new_btn.setObjectName("highlight")
        self._new_btn.setStyleSheet(
            "QPushButton#highlight { background-color: #e8a838; color: #000; }"
        )


def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color: #3a3a3a;")
    return line


def _scroll_area(max_height: int) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setMaximumHeight(max_height)
    scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
    return scroll
```

- [ ] **Step 2: 导入烟雾测试**

```bash
python -c "from app.ui.sidebar import Sidebar; print('OK')"
```

期望：打印 `OK`，无报错。

- [ ] **Step 3: Commit**

```bash
git add app/ui/sidebar.py
git commit -m "feat: 实现 Sidebar（侧边栏面板）"
```

---

### Task 9: MainWindow — 组装所有组件

**Files:**
- Create: `app/ui/main_window.py`

- [ ] **Step 1: 创建 `app/ui/main_window.py`**

```python
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QSplitter

from app.core.pty_worker import PtyWorker
from app.core.skill_scanner import get_builtin_commands, scan_skills
from app.core.task_loader import load_tasks
from app.ui.chat_panel import ChatPanel
from app.ui.sidebar import Sidebar

# 若用户的 Claude CLI 命令不同，修改此处
CLAUDE_CLI = "claude"

_TASKS_DIR = Path(__file__).parent.parent.parent / "tasks"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("claude-hunter")
        self.resize(900, 650)
        self._apply_dark_palette()

        skills = scan_skills()
        commands = get_builtin_commands()
        tasks, warnings = load_tasks(_TASKS_DIR)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._sidebar = Sidebar(skills, tasks, warnings, parent=self)
        self._chat = ChatPanel(skills, commands, parent=self)

        splitter.addWidget(self._sidebar)
        splitter.addWidget(self._chat)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([220, 680])

        self.setCentralWidget(splitter)

        self._worker: PtyWorker | None = None
        self._start_worker()

        # 信号连接
        self._sidebar.new_conversation_requested.connect(self._restart_worker)
        self._sidebar.clear_output_requested.connect(self._chat.clear_output)
        self._sidebar.task_send_requested.connect(self._send)
        self._sidebar.skill_fill_requested.connect(self._chat.fill_input)
        self._chat.send_requested.connect(self._send)

    # ── 私有方法 ────────────────────────────────────────────────

    def _start_worker(self):
        self._worker = PtyWorker(CLAUDE_CLI, parent=self)
        self._worker.output_received.connect(self._chat.append_output)
        self._worker.process_finished.connect(self._on_finished)
        self._worker.process_error.connect(self._on_error)
        self._worker.start()

    def _restart_worker(self):
        if self._worker:
            self._worker.stop()
        self._chat.clear_output()
        self._start_worker()

    def _send(self, text: str):
        if self._worker:
            self._worker.write(text)

    def _on_finished(self):
        self._chat.append_output("\n\n[进程已结束，点击「新对话」重启]\n")
        self._sidebar.highlight_new_conversation()

    def _on_error(self, message: str):
        QMessageBox.critical(self, "claude-hunter — 错误", message)

    def _apply_dark_palette(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#1e1e1e"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#d4d4d4"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#2d2d2d"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#252526"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#d4d4d4"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#0e639c"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#0e639c"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        self.setPalette(palette)

    def closeEvent(self, event):
        if self._worker:
            self._worker.stop()
        super().closeEvent(event)
```

- [ ] **Step 2: 导入烟雾测试**

```bash
python -c "from app.ui.main_window import MainWindow; print('OK')"
```

期望：打印 `OK`，无报错。

- [ ] **Step 3: Commit**

```bash
git add app/ui/main_window.py
git commit -m "feat: 实现 MainWindow（组装所有组件）"
```

---

### Task 10: main.py 入口

**Files:**
- Create: `main.py`

- [ ] **Step 1: 创建 `main.py`**

```python
import sys

from PyQt6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("claude-hunter")
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 启动 App 验证 UI 可渲染**

```bash
python main.py
```

期望：App 窗口正常打开，左侧侧边栏显示，右侧聊天面板显示，`claude` 进程在后台启动（输出区有内容更新）。如果 `claude` 未安装，弹出错误对话框（这是正确行为）。

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: 添加入口 main.py，App 可正常启动"
```

---

### Task 11: 示例任务配置文件

**Files:**
- Create: `tasks/代码审查.json`
- Create: `tasks/查bug.md`
- Create: `tasks/重构代码.md`

- [ ] **Step 1: 创建示例任务文件**

`tasks/代码审查.json`：
```json
{
  "name": "🔍 代码审查",
  "cli_args": "",
  "prompt": "请帮我严格审查这段代码，找出 bug、性能问题、安全风险、可读性问题，并给出修复后的完整代码。"
}
```

`tasks/查bug.md`：
```
帮我快速定位代码 bug，告诉我：
1. 问题根源
2. 修复方案
3. 改好的完整代码
```

`tasks/重构代码.md`：
```
请帮我重构以下代码：
1. 提升可读性（命名、结构）
2. 消除重复代码
3. 提升性能（如有必要）
4. 输出重构后的完整代码
```

- [ ] **Step 2: 重启 App，确认任务按钮出现在侧边栏**

```bash
python main.py
```

期望：侧边栏"自定义任务"区域显示 3 个按钮，点击任意按钮可向 Claude 发送预设指令。

- [ ] **Step 3: Commit**

```bash
git add tasks/
git commit -m "docs: 添加示例任务配置文件"
```

---

### Task 12: pyinstaller 打包配置

**Files:**
- Create: `claude-hunter.spec`

- [ ] **Step 1: 安装 pyinstaller**

```bash
pip install pyinstaller
```

- [ ] **Step 2: 创建 `claude-hunter.spec`**

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('tasks', 'tasks'), ('assets', 'assets')],
    hiddenimports=['ptyprocess'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='claude-hunter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='claude-hunter',
)

app = BUNDLE(
    coll,
    name='claude-hunter.app',
    icon='assets/icon.icns',
    bundle_identifier='com.claudehunter.app',
    info_plist={
        'NSHighResolutionCapable': True,
        'LSUIElement': False,
    },
)
```

- [ ] **Step 3: 执行打包**

```bash
pyinstaller claude-hunter.spec
```

期望：`dist/claude-hunter.app` 生成成功，无错误。

- [ ] **Step 4: 测试打包后的 App**

```bash
open dist/claude-hunter.app
```

期望：App 正常启动，与 `python main.py` 行为一致。

- [ ] **Step 5: 在 .gitignore 中排除 dist/ 和 build/**

在 `.gitignore` 追加（如果不存在则创建）：
```
dist/
build/
*.spec.bak
__pycache__/
*.pyc
.DS_Store
```

- [ ] **Step 6: Commit**

```bash
git add claude-hunter.spec .gitignore
git commit -m "build: 添加 pyinstaller 打包配置"
```

---

## 验收检查清单

完成所有任务后，验证以下行为：

- [ ] `pytest tests/ -v` — 所有单元和集成测试通过
- [ ] `python main.py` — App 正常启动，侧边栏和聊天区域正常渲染
- [ ] 输入 `:` — 补全菜单弹出，显示本地 skill 列表
- [ ] 输入 `/` — 补全菜单弹出，显示内置命令
- [ ] 点击侧边栏任务按钮 — 向 Claude 发送预设指令，输出区实时更新
- [ ] 点击"新对话" — Claude 进程重启，输出区清空
- [ ] 点击"清空输出" — 输出区内容清空，进程不重启
- [ ] 点击快捷按钮（解释代码/找 Bug/重构代码）— 输入框自动填充 prompt
- [ ] Enter 发送，Shift+Enter 换行 — 行为正确
- [ ] 关闭 App — PTY 进程正常终止，无僵尸进程
