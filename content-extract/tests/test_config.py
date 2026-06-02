from pathlib import Path
import pytest
from content_extract.config import load_config


def test_returns_defaults_when_no_files(tmp_path):
    cfg = load_config(project_dir=tmp_path)
    assert cfg["whisper"]["model"] == "medium"
    assert cfg["whisper"]["device"] == "cpu"
    assert cfg["output"]["dir"] == "./raw"


def test_project_config_overrides_defaults(tmp_path):
    config_file = tmp_path / "content-extract.toml"
    config_file.write_text(
        '[whisper]\nmodel = "large-v3"\ndevice = "mps"\n',
        encoding="utf-8",
    )
    cfg = load_config(project_dir=tmp_path)
    assert cfg["whisper"]["model"] == "large-v3"
    assert cfg["whisper"]["device"] == "mps"
    # 未覆盖的字段保持默认值
    assert cfg["whisper"]["compute_type"] == "int8"


def test_global_config_overrides_defaults(tmp_path):
    global_dir = tmp_path / ".content-extract"
    global_dir.mkdir()
    (global_dir / "config.toml").write_text(
        '[output]\ndir = "/data/raw"\n', encoding="utf-8"
    )
    cfg = load_config(project_dir=tmp_path, global_dir=global_dir)
    assert cfg["output"]["dir"] == "/data/raw"


def test_project_config_takes_priority_over_global(tmp_path):
    global_dir = tmp_path / ".content-extract"
    global_dir.mkdir()
    (global_dir / "config.toml").write_text('[whisper]\nmodel = "small"\n', encoding="utf-8")
    (tmp_path / "content-extract.toml").write_text('[whisper]\nmodel = "large-v3"\n', encoding="utf-8")
    cfg = load_config(project_dir=tmp_path, global_dir=global_dir)
    assert cfg["whisper"]["model"] == "large-v3"
