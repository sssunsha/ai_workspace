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
