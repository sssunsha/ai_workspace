from PyQt6.QtCore import pyqtSignal, Qt, QPoint
from PyQt6.QtGui import QTextCursor
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
    """Enter 发送，Shift+Enter 换行。"""
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

        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setStyleSheet(_OUTPUT_STYLE)
        layout.addWidget(self._output, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        for label, prompt in _QUICK_PROMPTS:
            btn = QPushButton(label)
            btn.setStyleSheet(_QUICK_BTN_STYLE)
            btn.clicked.connect(lambda _, p=prompt: self.fill_input(p))
            btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._input = _InputBox()
        self._input.setStyleSheet(_INPUT_STYLE)
        self._input.setMaximumHeight(120)
        self._input.setPlaceholderText(
            "输入消息... (Enter 发送, Shift+Enter 换行, : 触发技能, / 触发命令)"
        )
        self._input.send_triggered.connect(self._on_send)
        self._input.textChanged.connect(self._on_input_changed)
        layout.addWidget(self._input)

        send_row = QHBoxLayout()
        send_row.addStretch()
        send_btn = QPushButton("发送")
        send_btn.setStyleSheet(_SEND_BTN_STYLE)
        send_btn.clicked.connect(self._on_send)
        send_row.addWidget(send_btn)
        layout.addLayout(send_row)

        self._autocomplete = AutoCompleteWidget(skills, commands)
        self._autocomplete.item_selected.connect(self._on_autocomplete_selected)

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
