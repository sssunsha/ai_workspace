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

        self._sidebar.new_conversation_requested.connect(self._restart_worker)
        self._sidebar.clear_output_requested.connect(self._chat.clear_output)
        self._sidebar.task_send_requested.connect(self._send)
        self._sidebar.skill_fill_requested.connect(self._chat.fill_input)
        self._chat.send_requested.connect(self._send)

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
