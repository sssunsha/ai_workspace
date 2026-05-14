import os
import re

import ptyprocess
from PyQt6.QtCore import QThread, pyqtSignal

_ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')


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
        self._process = None
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
