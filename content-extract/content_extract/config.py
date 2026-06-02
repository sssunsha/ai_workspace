from pathlib import Path
import copy

try:
    import toml
except ImportError:
    import tomllib as toml  # Python 3.11+ 内置

_DEFAULTS = {
    "cookies": {
        "bilibili": "~/.content-extract/bilibili_cookies.txt",
        "douyin": "~/.content-extract/douyin_cookies.txt",
    },
    "whisper": {
        "model": "medium",
        "device": "cpu",
        "compute_type": "int8",
        "language": "zh",
    },
    "douyin": {
        "min_duration": 60,
        "sleep_min": 5,
        "sleep_max": 12,
    },
    "output": {
        "dir": "./raw",
    },
    "clean": {
        "enabled": True,
        "model": "claude-haiku-4-5-20251001",
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并两个字典，override 优先。"""
    result = copy.deepcopy(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def load_config(
    project_dir: Path | None = None,
    global_dir: Path | None = None,
) -> dict:
    """加载合并后的配置：默认值 < 全局配置 < 项目配置。"""
    cfg = copy.deepcopy(_DEFAULTS)

    # 全局配置
    _global_dir = global_dir or Path.home() / ".content-extract"
    global_cfg_path = _global_dir / "config.toml"
    if global_cfg_path.exists():
        with open(global_cfg_path, encoding="utf-8") as f:
            cfg = _deep_merge(cfg, toml.loads(f.read()))

    # 项目配置（优先级最高）
    _project_dir = project_dir or Path.cwd()
    project_cfg_path = _project_dir / "content-extract.toml"
    if project_cfg_path.exists():
        with open(project_cfg_path, encoding="utf-8") as f:
            cfg = _deep_merge(cfg, toml.loads(f.read()))

    return cfg
