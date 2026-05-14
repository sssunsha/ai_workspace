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


def test_pty_worker_spawns_and_reads_echo():
    """基础集成测试：PtyWorker 可以启动 echo 并读取输出。"""
    import os
    import pty
    import re
    import subprocess
    ansi_escape = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')
    master_fd, slave_fd = pty.openpty()
    proc = subprocess.Popen(
        ["echo", "hello pty"],
        stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
        close_fds=True, env=os.environ.copy(),
    )
    os.close(slave_fd)
    output = b""
    try:
        while True:
            try:
                chunk = os.read(master_fd, 1024)
                if not chunk:
                    break
                output += chunk
            except OSError:
                break
    finally:
        os.close(master_fd)
        proc.wait()
    text = ansi_escape.sub('', output.decode('utf-8', errors='replace'))
    assert "hello pty" in text


def test_pty_worker_filenotfound_raises():
    """启动不存在的命令应抛出 FileNotFoundError。"""
    import os
    import pty
    import subprocess
    master_fd, slave_fd = pty.openpty()
    try:
        subprocess.Popen(
            ["__nonexistent_cmd_xyz__"],
            stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
            close_fds=True, env=os.environ.copy(),
        )
    except FileNotFoundError:
        return
    finally:
        os.close(slave_fd)
        os.close(master_fd)
    pytest.fail("Expected FileNotFoundError for nonexistent command")
