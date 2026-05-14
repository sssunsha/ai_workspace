import os
import re

# Note: PyQt6 import skipped for now (Task 5)
# from PyQt6.QtCore import QThread, pyqtSignal

_ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*[mGKHFJA-Za-z]')


def strip_ansi(text: str) -> str:
    """移除字符串中的ANSI转义码。"""
    return _ANSI_ESCAPE.sub('', text)
