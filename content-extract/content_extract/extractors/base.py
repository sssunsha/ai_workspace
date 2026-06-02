from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class ExtractConfig:
    """提取器统一配置，在构造时注入，不在 extract() 签名重复传。"""
    output_dir: Path = field(default_factory=lambda: Path("./raw"))
    force: bool = False
    cookies: dict[str, str] = field(default_factory=dict)
    extra: dict = field(default_factory=dict)


class BaseExtractor(ABC):
    def __init__(
        self,
        config: ExtractConfig,
        on_progress: Callable[[str], None] | None = None,
    ):
        self.config = config
        # on_progress 默认 print，CLI 和 TUI 可替换
        self.log = on_progress or (lambda msg: print(msg))

    @abstractmethod
    def extract(self, source: str) -> Path:
        """提取单个来源，返回输出文件路径。"""
        ...

    @property
    @abstractmethod
    def supported_domains(self) -> list[str]:
        """用于 URL 自动识别，如 ['youtube.com', 'youtu.be']"""
        ...
