from PyQt6.QtCore import pyqtSignal
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

    def __init__(self, skills: list[str], tasks: list[Task], warnings: list[str], parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(220)
        self.setStyleSheet(_STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(6)

        title = QLabel("claude-hunter")
        title.setObjectName("title")
        layout.addWidget(title)
        layout.addWidget(_separator())

        self._new_btn = QPushButton("＋ 新对话")
        self._new_btn.clicked.connect(self.new_conversation_requested)
        layout.addWidget(self._new_btn)

        clear_btn = QPushButton("✕ 清空输出")
        clear_btn.setObjectName("danger")
        clear_btn.clicked.connect(self.clear_output_requested)
        layout.addWidget(clear_btn)

        layout.addWidget(_separator())

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
