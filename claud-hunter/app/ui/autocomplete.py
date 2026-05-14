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
