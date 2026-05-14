import os
import pty
import re
import subprocess
import threading
from typing import Callable, Optional

_ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')


def strip_ansi(text: str) -> str:
    """移除字符串中的ANSI转义码。"""
    return _ANSI_ESCAPE.sub('', text)


class _Signal:
    """最简 signal 替代，支持 connect/emit。"""

    def __init__(self):
        self._handlers: list[Callable] = []

    def connect(self, fn: Callable):
        self._handlers.append(fn)

    def emit(self, *args):
        for handler in self._handlers:
            handler(*args)


class PtyWorker(threading.Thread):
    """在后台线程中驱动 PTY 子进程，通过 signal 将输出传递给调用方。"""

    def __init__(self, cli_cmd: str = "claude", cli_args: list = None, parent=None):
        super().__init__(daemon=True)
        self._cli_cmd = cli_cmd
        self._cli_args = cli_args or []
        self._master_fd: Optional[int] = None
        self._proc: Optional[subprocess.Popen] = None
        self._running = False
        self.output_received = _Signal()
        self.process_finished = _Signal()
        self.process_error = _Signal()

    def run(self):
        cmd = [self._cli_cmd] + self._cli_args
        try:
            master_fd, slave_fd = pty.openpty()
            self._master_fd = master_fd
            self._proc = subprocess.Popen(
                cmd,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
                env=os.environ.copy(),
            )
            os.close(slave_fd)
        except FileNotFoundError:
            self.process_error.emit(
                f"命令 '{self._cli_cmd}' 未找到。\n请确认 Claude Code CLI 已正确安装，"
                "且可在终端通过 'claude' 命令调用。"
            )
            return
        except Exception as exc:
            self.process_error.emit(str(exc))
            return

        self._running = True
        while self._running:
            try:
                data = os.read(self._master_fd, 4096)
                if not data:
                    break
                text = data.decode("utf-8", errors="replace")
                clean = strip_ansi(text)
                if clean:
                    self.output_received.emit(clean)
            except OSError:
                break

        if self._proc:
            self._proc.wait()
        self.process_finished.emit()

    def write(self, text: str):
        """向子进程的 stdin 写入文本。"""
        if self._master_fd is not None and self._running:
            if not text.endswith("\n"):
                text += "\n"
            os.write(self._master_fd, text.encode())

    def stop(self):
        """停止子进程并等待线程退出。"""
        self._running = False
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=2.0)
            except Exception:
                pass
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
            self._master_fd = None
        self.join(timeout=2.0)

    def start(self):
        """启动后台线程（兼容 Qt 风格 API）。"""
        super().start()

    def wait(self, msec: int = 2000):
        """等待线程完成（兼容 Qt 风格 API）。"""
        self.join(timeout=msec / 1000.0)
