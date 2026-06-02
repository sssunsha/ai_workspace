from pathlib import Path
import pytest
from content_extract.extractors.base import ExtractConfig, BaseExtractor


class ConcreteExtractor(BaseExtractor):
    @property
    def supported_domains(self) -> list[str]:
        return ["example.com"]

    def extract(self, source: str) -> Path:
        self.log(f"提取: {source}")
        return Path("./raw/test.md")


def test_extract_config_defaults():
    cfg = ExtractConfig()
    assert cfg.output_dir == Path("./raw")
    assert cfg.force is False
    assert cfg.cookies == {}


def test_base_extractor_log_default(capsys):
    cfg = ExtractConfig()
    ext = ConcreteExtractor(config=cfg)
    ext.log("测试消息")
    captured = capsys.readouterr()
    assert "测试消息" in captured.out


def test_base_extractor_custom_log():
    messages = []
    cfg = ExtractConfig()
    ext = ConcreteExtractor(config=cfg, on_progress=messages.append)
    ext.log("自定义消息")
    assert messages == ["自定义消息"]


def test_supported_domains():
    cfg = ExtractConfig()
    ext = ConcreteExtractor(config=cfg)
    assert "example.com" in ext.supported_domains


def test_extract_returns_path():
    cfg = ExtractConfig()
    ext = ConcreteExtractor(config=cfg)
    result = ext.extract("https://example.com")
    assert isinstance(result, Path)


def test_cannot_instantiate_base_directly():
    with pytest.raises(TypeError):
        BaseExtractor(config=ExtractConfig())
