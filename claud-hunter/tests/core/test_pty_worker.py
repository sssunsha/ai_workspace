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


from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication
from app.core.pty_worker import PtyWorker


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def test_pty_worker_emits_output(qt_app):
    received = []
    worker = PtyWorker(cli_cmd="echo", cli_args=["hello pty"])
    worker.output_received.connect(lambda t: received.append(t))
    worker.start()
    worker.wait(3000)
    QCoreApplication.processEvents()

    combined = "".join(received)
    assert "hello pty" in combined


def test_pty_worker_emits_error_for_bad_command(qt_app):
    errors = []
    worker = PtyWorker(cli_cmd="__nonexistent_cmd_xyz__")
    worker.process_error.connect(lambda e: errors.append(e))
    worker.start()
    worker.wait(3000)
    QCoreApplication.processEvents()

    assert len(errors) >= 1
    assert "__nonexistent_cmd_xyz__" in errors[0]
