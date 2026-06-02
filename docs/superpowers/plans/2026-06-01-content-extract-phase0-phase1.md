# Content Extract CLI — Phase 0 + Phase 1 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 在 `/Users/I340818/Documents/ai_workspace/content-extract/` 下实现 content-extract CLI 工具的 Phase 0（可运行骨架）和 Phase 1（web / YouTube / Bilibili 三个核心提取器 + Whisper 转录）。

**架构：** 同步 Python CLI（Click），BaseExtractor 抽象基类定义 `extract(source) → Path` 接口，进度通过回调注入。Phase 0 文件全部可并行创建；Phase 1 中 web.py / youtube.py / bilibili.py / whisper_local.py 互相独立，可并行实现。

**技术栈：** Python 3.11+、click>=8.1、toml、crawl4ai、youtube-transcript-api、yt-dlp、faster-whisper、pytest

---

## 文件清单

| 文件 | 新建/修改 | 职责 |
|------|---------|------|
| `content-extract/pyproject.toml` | 新建 | 项目配置，定义 `content-extract` 命令入口 |
| `content-extract/requirements.txt` | 新建 | 分组依赖（core/video/web/transcription） |
| `content-extract/.gitignore` | 新建 | 排除 cookies、raw/、audio/ 等 |
| `content-extract/content_extract/__init__.py` | 新建 | 包入口，暴露版本号 |
| `content-extract/content_extract/cli.py` | 新建 | Click group + 所有子命令注册 |
| `content-extract/content_extract/registry.py` | 新建 | `.processed.json` 读写，状态管理 |
| `content-extract/content_extract/config.py` | 新建 | 配置加载（全局+项目级合并） |
| `content-extract/content_extract/extractors/base.py` | 新建 | `ExtractConfig` dataclass + `BaseExtractor` 抽象基类 |
| `content-extract/content_extract/extractors/__init__.py` | 新建 | `auto_detect_video()` 路由函数 |
| `content-extract/content_extract/extractors/web.py` | 新建 | crawl4ai 单页/整站提取 |
| `content-extract/content_extract/extractors/youtube.py` | 新建 | YouTube 字幕+元数据提取 |
| `content-extract/content_extract/extractors/bilibili.py` | 新建 | Bilibili yt-dlp+SRT清洗提取 |
| `content-extract/content_extract/transcribe/__init__.py` | 新建 | 空包标记 |
| `content-extract/content_extract/transcribe/whisper_local.py` | 新建 | faster-whisper 封装 |
| `content-extract/content_extract/transcribe/queue.py` | 新建 | needs_transcription 队列消费 |
| `content-extract/content_extract/utils/__init__.py` | 新建 | 空包标记 |
| `content-extract/content_extract/utils/frontmatter.py` | 新建 | 统一 frontmatter 写入 |
| `content-extract/tests/test_registry.py` | 新建 | registry 单元测试 |
| `content-extract/tests/test_config.py` | 新建 | config 单元测试 |
| `content-extract/tests/test_frontmatter.py` | 新建 | frontmatter 单元测试 |
| `content-extract/tests/test_base.py` | 新建 | BaseExtractor 接口测试 |

---

## Phase 0：脚手架

### Task 1：项目骨架文件（pyproject.toml / requirements.txt / .gitignore）

**文件：**
- 新建：`content-extract/pyproject.toml`
- 新建：`content-extract/requirements.txt`
- 新建：`content-extract/.gitignore`

- [ ] **步骤 1：创建项目目录**

```bash
mkdir -p /Users/I340818/Documents/ai_workspace/content-extract/content_extract/extractors
mkdir -p /Users/I340818/Documents/ai_workspace/content-extract/content_extract/transcribe
mkdir -p /Users/I340818/Documents/ai_workspace/content-extract/content_extract/utils
mkdir -p /Users/I340818/Documents/ai_workspace/content-extract/tests
```

- [ ] **步骤 2：创建 pyproject.toml**

```toml
# content-extract/pyproject.toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "content-extract"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1",
    "toml>=0.10",
]

[project.scripts]
content-extract = "content_extract.cli:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["content_extract*"]
```

- [ ] **步骤 3：创建 requirements.txt**

```text
# core
click>=8.1
toml>=0.10

# web
crawl4ai

# video
yt-dlp
youtube-transcript-api

# transcription
faster-whisper

# dev/test
pytest>=7.0

# ebook（Phase 2，占位）
# ebooklib
# beautifulsoup4
# pymupdf4llm

# rag（Phase 4，占位）
# chromadb
# sentence-transformers

# ui（Phase 2，占位）
# textual
# streamlit
```

- [ ] **步骤 4：创建 .gitignore**

```gitignore
# Cookie 文件（含登录凭证）
cookies*.txt
bilibili_cookies.txt
douyin_cookies.txt
*.cookies.txt

# 原始内容（体积大，可重新生成）
raw/
audio/
audio_tmp/
chroma-db/

# 环境变量
.env
secrets.json
file_ids.json

# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/
*.egg-info/
dist/
build/
.pytest_cache/
```

- [ ] **步骤 5：验证目录结构**

```bash
find /Users/I340818/Documents/ai_workspace/content-extract -type d | sort
```

预期输出包含 `content_extract/`、`content_extract/extractors`、`content_extract/transcribe`、`content_extract/utils`、`tests/`。

---

### Task 2：utils/frontmatter.py + 测试

**文件：**
- 新建：`content-extract/content_extract/utils/__init__.py`
- 新建：`content-extract/content_extract/utils/frontmatter.py`
- 新建：`content-extract/tests/test_frontmatter.py`

- [ ] **步骤 1：创建 utils/__init__.py**

```python
# content_extract/utils/__init__.py
```

（空文件）

- [ ] **步骤 2：写失败测试**

```python
# content-extract/tests/test_frontmatter.py
import hashlib
from pathlib import Path
import pytest
from content_extract.utils.frontmatter import write_frontmatter_file


def test_write_creates_file(tmp_path):
    out = tmp_path / "test.md"
    write_frontmatter_file(
        path=out,
        content="正文内容",
        source="https://example.com",
        type="web",
    )
    assert out.exists()


def test_frontmatter_contains_required_fields(tmp_path):
    out = tmp_path / "test.md"
    write_frontmatter_file(
        path=out,
        content="正文内容",
        source="https://example.com",
        type="web",
    )
    text = out.read_text(encoding="utf-8")
    assert "source: https://example.com" in text
    assert "type: web" in text
    assert "extracted_at:" in text
    assert "content_hash:" in text


def test_frontmatter_platform_field(tmp_path):
    out = tmp_path / "test.md"
    write_frontmatter_file(
        path=out,
        content="视频内容",
        source="https://youtube.com/watch?v=abc",
        type="video",
        platform="youtube",
    )
    text = out.read_text(encoding="utf-8")
    assert "platform: youtube" in text


def test_frontmatter_content_hash(tmp_path):
    out = tmp_path / "test.md"
    content = "测试内容"
    write_frontmatter_file(path=out, content=content, source="https://example.com", type="web")
    expected_hash = hashlib.sha256(content.encode()).hexdigest()[:8]
    text = out.read_text(encoding="utf-8")
    assert f"content_hash: {expected_hash}" in text


def test_frontmatter_extra_fields(tmp_path):
    out = tmp_path / "test.md"
    write_frontmatter_file(
        path=out,
        content="内容",
        source="https://example.com",
        type="web",
        extra_fields={"custom_key": "custom_value"},
    )
    text = out.read_text(encoding="utf-8")
    assert "custom_key: custom_value" in text


def test_body_content_present(tmp_path):
    out = tmp_path / "test.md"
    write_frontmatter_file(path=out, content="正文在这里", source="https://example.com", type="web")
    text = out.read_text(encoding="utf-8")
    assert "正文在这里" in text
```

- [ ] **步骤 3：运行测试确认失败**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
pip install -e . -q
pytest tests/test_frontmatter.py -v 2>&1 | head -20
```

预期：`ModuleNotFoundError` 或 `ImportError`（frontmatter 尚未实现）。

- [ ] **步骤 4：实现 utils/frontmatter.py**

```python
# content-extract/content_extract/utils/frontmatter.py
import hashlib
from datetime import datetime, timezone
from pathlib import Path


def write_frontmatter_file(
    path: Path,
    content: str,
    source: str,
    type: str,
    platform: str | None = None,
    subtype: str | None = None,
    extra_fields: dict | None = None,
) -> None:
    """写入统一 frontmatter + 正文到文件。自动填写 extracted_at 和 content_hash。"""
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:8]
    extracted_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    lines = ["---"]
    lines.append(f"source: {source}")
    lines.append(f"type: {type}")
    if platform:
        lines.append(f"platform: {platform}")
    if subtype:
        lines.append(f"subtype: {subtype}")
    lines.append(f"extracted_at: {extracted_at}")
    lines.append(f"content_hash: {content_hash}")
    if extra_fields:
        for k, v in extra_fields.items():
            lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    lines.append(content)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
```

- [ ] **步骤 5：运行测试确认通过**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
pytest tests/test_frontmatter.py -v
```

预期：6 个测试全部 PASS。

- [ ] **步骤 6：提交**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
git init
git add content_extract/utils/__init__.py content_extract/utils/frontmatter.py tests/test_frontmatter.py
git commit -m "feat: 添加 utils/frontmatter.py 统一 frontmatter 写入"
```

---

### Task 3：registry.py + 测试

**文件：**
- 新建：`content-extract/content_extract/registry.py`
- 新建：`content-extract/tests/test_registry.py`

- [ ] **步骤 1：写失败测试**

```python
# content-extract/tests/test_registry.py
import json
from pathlib import Path
import pytest
from content_extract.registry import Registry


def test_new_registry_is_empty(tmp_path):
    reg = Registry(tmp_path / ".processed.json")
    assert reg.get_by_status("done") == []


def test_is_processed_false_for_unknown(tmp_path):
    reg = Registry(tmp_path / ".processed.json")
    assert reg.is_processed("https://example.com") is False


def test_mark_and_is_processed(tmp_path):
    reg = Registry(tmp_path / ".processed.json")
    reg.mark("https://example.com", "done", output_file="web__example.md")
    assert reg.is_processed("https://example.com") is True


def test_get_by_status(tmp_path):
    reg = Registry(tmp_path / ".processed.json")
    reg.mark("https://a.com", "done", output_file="a.md")
    reg.mark("https://b.com", "needs_transcription", output_file="b.md")
    reg.mark("https://c.com", "failed", error="网络错误")
    assert len(reg.get_by_status("done")) == 1
    assert len(reg.get_by_status("needs_transcription")) == 1
    assert len(reg.get_by_status("failed")) == 1


def test_save_and_reload(tmp_path):
    path = tmp_path / ".processed.json"
    reg = Registry(path)
    reg.mark("https://example.com", "done", output_file="test.md", content_hash="abc12345")
    reg.save()

    reg2 = Registry(path)
    assert reg2.is_processed("https://example.com")
    entries = reg2.get_by_status("done")
    assert entries[0]["content_hash"] == "abc12345"


def test_mark_updates_existing(tmp_path):
    reg = Registry(tmp_path / ".processed.json")
    reg.mark("https://example.com", "needs_transcription", output_file="test.md")
    reg.mark("https://example.com", "done")
    assert reg.is_processed("https://example.com")
    entries = reg.get_by_status("done")
    assert len(entries) == 1


def test_loads_existing_file(tmp_path):
    path = tmp_path / ".processed.json"
    data = {
        "https://example.com": {
            "status": "done",
            "output_file": "test.md",
            "extracted_at": "2026-06-01T10:00:00",
            "content_hash": "deadbeef",
            "retry_count": 0,
            "error": None,
        }
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    reg = Registry(path)
    assert reg.is_processed("https://example.com")
```

- [ ] **步骤 2：运行测试确认失败**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
pytest tests/test_registry.py -v 2>&1 | head -10
```

预期：`ImportError`（registry 尚未实现）。

- [ ] **步骤 3：实现 registry.py**

```python
# content-extract/content_extract/registry.py
import json
from datetime import datetime, timezone
from pathlib import Path


class Registry:
    """管理已处理来源的状态，持久化到 .processed.json。"""

    def __init__(self, path: Path):
        self._path = path
        self._data: dict[str, dict] = {}
        if path.exists():
            self._data = json.loads(path.read_text(encoding="utf-8"))

    def is_processed(self, source: str) -> bool:
        return source in self._data

    def mark(self, source: str, status: str, **kwargs) -> None:
        """写入或更新记录。status: done / needs_transcription / failed。"""
        existing = self._data.get(source, {"retry_count": 0, "error": None})
        existing.update({"status": status, "extracted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")})
        existing.update(kwargs)
        self._data[source] = existing
        self.save()

    def get_by_status(self, status: str) -> list[dict]:
        return [{"source": k, **v} for k, v in self._data.items() if v.get("status") == status]

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
```

- [ ] **步骤 4：运行测试确认通过**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
pytest tests/test_registry.py -v
```

预期：7 个测试全部 PASS。

- [ ] **步骤 5：提交**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
git add content_extract/registry.py tests/test_registry.py
git commit -m "feat: 添加 registry.py 状态管理"
```

---

### Task 4：config.py + 测试

**文件：**
- 新建：`content-extract/content_extract/config.py`
- 新建：`content-extract/tests/test_config.py`

- [ ] **步骤 1：写失败测试**

```python
# content-extract/tests/test_config.py
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
```

- [ ] **步骤 2：运行测试确认失败**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
pytest tests/test_config.py -v 2>&1 | head -10
```

预期：`ImportError`（config 尚未实现）。

- [ ] **步骤 3：实现 config.py**

```python
# content-extract/content_extract/config.py
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
```

- [ ] **步骤 4：运行测试确认通过**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
pytest tests/test_config.py -v
```

预期：4 个测试全部 PASS。

- [ ] **步骤 5：提交**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
git add content_extract/config.py tests/test_config.py
git commit -m "feat: 添加 config.py 配置加载（全局+项目级合并）"
```

---

### Task 5：extractors/base.py + 测试

**文件：**
- 新建：`content-extract/content_extract/extractors/__init__.py`
- 新建：`content-extract/content_extract/extractors/base.py`
- 新建：`content-extract/tests/test_base.py`

- [ ] **步骤 1：写失败测试**

```python
# content-extract/tests/test_base.py
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
```

- [ ] **步骤 2：运行测试确认失败**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
pytest tests/test_base.py -v 2>&1 | head -10
```

预期：`ImportError`（base 尚未实现）。

- [ ] **步骤 3：实现 extractors/__init__.py 和 base.py**

`content-extract/content_extract/extractors/__init__.py`:
```python
# content_extract/extractors/__init__.py
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import ExtractConfig


def auto_detect_video(url: str, config: "ExtractConfig", **kwargs):
    """根据 URL 自动选择 YouTube 或 Bilibili 提取器。"""
    from .youtube import YouTubeExtractor
    from .bilibili import BilibiliExtractor

    lower = url.lower()
    if "youtube.com" in lower or "youtu.be" in lower:
        return YouTubeExtractor(config=config, **kwargs).extract(url)
    if "bilibili.com" in lower or "b23.tv" in lower:
        return BilibiliExtractor(config=config, **kwargs).extract(url)
    raise ValueError(f"无法识别视频平台: {url}")
```

`content-extract/content_extract/extractors/base.py`:
```python
# content_extract/extractors/base.py
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
```

- [ ] **步骤 4：运行测试确认通过**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
pytest tests/test_base.py -v
```

预期：6 个测试全部 PASS。

- [ ] **步骤 5：提交**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
git add content_extract/extractors/__init__.py content_extract/extractors/base.py tests/test_base.py
git commit -m "feat: 添加 ExtractConfig 和 BaseExtractor 抽象基类"
```

---

### Task 6：__init__.py + cli.py 骨架（init / status 命令）

**文件：**
- 新建：`content-extract/content_extract/__init__.py`
- 新建：`content-extract/content_extract/cli.py`
- 新建：`content-extract/content_extract/transcribe/__init__.py`

- [ ] **步骤 1：创建包 __init__ 文件**

`content-extract/content_extract/__init__.py`:
```python
__version__ = "0.1.0"
```

`content-extract/content_extract/transcribe/__init__.py`:
```python
# 空包标记
```

- [ ] **步骤 2：实现 cli.py（含 init / status 命令）**

```python
# content-extract/content_extract/cli.py
from __future__ import annotations

import click
from pathlib import Path

from .config import load_config
from .registry import Registry


def _get_registry(output_dir: Path) -> Registry:
    return Registry(output_dir / ".processed.json")


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """content-extract — 内容提取与知识库构建工具"""
    if ctx.invoked_subcommand is None:
        click.echo("TUI 即将上线，当前请使用子命令。运行 content-extract --help 查看可用命令。")


@main.command("init")
def init_cmd() -> None:
    """在当前目录初始化 content-extract 项目（生成 wiki/DASHBOARD.md、CLAUDE.md、.gitignore）"""
    cwd = Path.cwd()

    # wiki/DASHBOARD.md
    dashboard_dir = cwd / "wiki"
    dashboard_dir.mkdir(exist_ok=True)
    dashboard_path = dashboard_dir / "DASHBOARD.md"
    if not dashboard_path.exists():
        dashboard_path.write_text(_DASHBOARD_TEMPLATE, encoding="utf-8")
        click.echo(f"已创建: {dashboard_path.relative_to(cwd)}")
    else:
        click.echo(f"已存在: {dashboard_path.relative_to(cwd)}（跳过）")

    # CLAUDE.md
    claude_path = cwd / "CLAUDE.md"
    if not claude_path.exists():
        claude_path.write_text(_CLAUDE_MD_TEMPLATE, encoding="utf-8")
        click.echo(f"已创建: {claude_path.relative_to(cwd)}")
    else:
        click.echo(f"已存在: {claude_path.relative_to(cwd)}（跳过）")

    # .gitignore
    gitignore_path = cwd / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path.write_text(_GITIGNORE_TEMPLATE, encoding="utf-8")
        click.echo(f"已创建: {gitignore_path.relative_to(cwd)}")
    else:
        click.echo(f"已存在: {gitignore_path.relative_to(cwd)}（跳过）")

    click.echo("\n初始化完成。运行 content-extract --help 查看可用命令。")


@main.command("status")
@click.option("--output", default="./raw", help="输出目录路径", type=click.Path())
def status_cmd(output: str) -> None:
    """查看处理队列状态"""
    output_dir = Path(output)
    reg = _get_registry(output_dir)

    done = reg.get_by_status("done")
    needs = reg.get_by_status("needs_transcription")
    failed = reg.get_by_status("failed")

    if not (done or needs or failed):
        click.echo("暂无处理记录。")
        return

    click.echo(f"✓ 已完成: {len(done)}")
    click.echo(f"⏳ 待转录: {len(needs)}")
    click.echo(f"✗ 失败:   {len(failed)}")
    if failed:
        click.echo("\n失败详情:")
        for entry in failed:
            click.echo(f"  {entry['source']}: {entry.get('error', '未知错误')}")


@main.command("web")
@click.argument("url")
@click.option("--crawl", is_flag=True, help="整站爬取模式")
@click.option("--limit", default=200, help="整站爬取最大页数")
@click.option("--output", default="./raw", help="输出目录", type=click.Path())
@click.option("--force", is_flag=True, help="忽略增量登记，强制重新处理")
def web_cmd(url: str, crawl: bool, limit: int, output: str, force: bool) -> None:
    """提取网页内容（单页或整站）"""
    from .extractors.base import ExtractConfig
    from .extractors.web import WebExtractor

    cfg = ExtractConfig(output_dir=Path(output), force=force)
    extractor = WebExtractor(config=cfg)
    result = extractor.extract(url, crawl=crawl, limit=limit)
    click.echo(f"完成: {result}")


@main.command("video")
@click.argument("url")
@click.option("--output", default="./raw", help="输出目录", type=click.Path())
@click.option("--force", is_flag=True, help="忽略增量登记，强制重新处理")
def video_cmd(url: str, output: str, force: bool) -> None:
    """提取视频内容（自动识别 YouTube / Bilibili）"""
    from .extractors.base import ExtractConfig
    from .extractors import auto_detect_video
    from .config import load_config

    raw_cfg = load_config()
    cookies = {k: str(Path(v).expanduser()) for k, v in raw_cfg.get("cookies", {}).items()}
    cfg = ExtractConfig(output_dir=Path(output), force=force, cookies=cookies)
    result = auto_detect_video(url, config=cfg)
    click.echo(f"完成: {result}")


@main.command("transcribe")
@click.option("--output", default="./raw", help="输出目录", type=click.Path())
@click.option("--model", default=None, help="Whisper 模型（覆盖配置文件）")
@click.option("--device", default=None, help="设备：cpu / mps / cuda")
def transcribe_cmd(output: str, model: str | None, device: str | None) -> None:
    """消费 needs_transcription 队列，进行 Whisper 本地转录"""
    from .transcribe.queue import process_queue
    from .config import load_config

    raw_cfg = load_config()
    w_cfg = raw_cfg.get("whisper", {})
    process_queue(
        output_dir=Path(output),
        model=model or w_cfg.get("model", "medium"),
        device=device or w_cfg.get("device", "cpu"),
        compute_type=w_cfg.get("compute_type", "int8"),
    )


# ── 模板内容 ──────────────────────────────────────────────────────────────

_DASHBOARD_TEMPLATE = """\
# 知识库 Dashboard

## 最近更新的概念（过去 7 天）
```dataview
TABLE file.mtime AS "更新时间", sources AS "来源", related AS "关联"
FROM "concepts"
SORT file.mtime DESC
LIMIT 20
```

## 各来源内容量
```dataview
TABLE length(rows) AS "文件数"
FROM "by-source"
GROUP BY file.folder
```

## 待追问的问题（gap 清单）
```dataview
LIST
FROM "concepts"
WHERE contains(file.content, "未解答的问题")
SORT file.mtime DESC
LIMIT 30
```

## 孤立概念（无 related 连线）
```dataview
LIST
FROM "concepts"
WHERE !related
SORT file.name ASC
```
"""

_CLAUDE_MD_TEMPLATE = """\
# 知识库构建规则

你是这批内容的知识管理员。
原始内容在 `./raw/` 目录（Markdown 格式）。
任务：构建结构化 Wiki 到 `./wiki/`。

## 内容来源识别

raw/ 文件名前缀说明：
- `web__`：网页/博客爬取（整站）
- `yt__`：YouTube 视频转录
- `bili__`：Bilibili 视频转录
- `article__`：单篇网络文章

每个 raw/ 文件的 frontmatter 包含：
```yaml
source:        # 原始 URL 或本地路径
type:          # web | video | ebook | code | local_doc | github | article
platform:      # 仅 video/article 有：youtube | bilibili
extracted_at:  # ISO 8601 时间戳
content_hash:  # 源内容 SHA256 前 8 位
```

## Wiki 目录结构

wiki/
├── INDEX.md          # 所有概念索引 + 来源分布图
├── concepts/         # 核心概念（跨来源整合）
├── by-source/        # 按来源分类的摘要
└── changelog.md

## 构建步骤

1. 读取所有 `./raw/*.md` 文件
2. 识别跨来源的核心概念，每个建一个 `concepts/CONCEPT.md`
3. 为每种来源类型生成摘要（`by-source/*.md`）
4. 构建 `INDEX.md`：概念列表 + 来源分布 + 关联关系
"""

_GITIGNORE_TEMPLATE = """\
# Cookie 文件（含登录凭证）
cookies*.txt
bilibili_cookies.txt
douyin_cookies.txt
*.cookies.txt

# 原始内容（体积大，可重新生成）
raw/
audio/
audio_tmp/
chroma-db/

# 环境变量
.env
secrets.json

# Python
__pycache__/
*.pyc
.venv/
venv/
"""
```

- [ ] **步骤 3：安装并验证 CLI**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
pip install -e . -q
content-extract --help
```

预期输出包含：`init`、`status`、`web`、`video`、`transcribe` 子命令。

- [ ] **步骤 4：验证无参数行为**

```bash
content-extract
```

预期：`TUI 即将上线，当前请使用子命令。运行 content-extract --help 查看可用命令。`

- [ ] **步骤 5：验证 init 命令**

```bash
cd /tmp && mkdir ce_test && cd ce_test
content-extract init
ls wiki/ CLAUDE.md .gitignore
```

预期：三个文件均生成，输出"已创建"提示。

- [ ] **步骤 6：验证 status 命令（空队列）**

```bash
content-extract status
```

预期：`暂无处理记录。`

- [ ] **步骤 7：提交**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
git add content_extract/__init__.py content_extract/cli.py content_extract/transcribe/__init__.py pyproject.toml requirements.txt .gitignore
git commit -m "feat: 添加 CLI 骨架，实现 init/status 命令"
```

---

## Phase 1：核心提取器

### Task 7：extractors/web.py（crawl4ai 单页/整站）

**文件：**
- 新建：`content-extract/content_extract/extractors/web.py`

- [ ] **步骤 1：安装 crawl4ai**

```bash
pip install crawl4ai -q
```

- [ ] **步骤 2：实现 web.py**

```python
# content-extract/content_extract/extractors/web.py
from __future__ import annotations

import asyncio
from pathlib import Path
from urllib.parse import urljoin, urlparse

from .base import BaseExtractor, ExtractConfig
from ..registry import Registry
from ..utils.frontmatter import write_frontmatter_file


def _url_to_filename(url: str) -> str:
    """将 URL 转为安全文件名：web__{netloc}__{path_slug}.md"""
    parsed = urlparse(url)
    netloc = parsed.netloc.replace(".", "-")
    path_slug = parsed.path.strip("/").replace("/", "__") or "index"
    # 限制长度防止文件名过长
    path_slug = path_slug[:80]
    return f"web__{netloc}__{path_slug}.md"


class WebExtractor(BaseExtractor):
    @property
    def supported_domains(self) -> list[str]:
        return []  # web 提取器作为兜底，支持任意域名

    def extract(self, source: str, crawl: bool = False, limit: int = 200) -> Path:
        """
        crawl=False（默认）：单页提取
        crawl=True：整站爬取，最多 limit 页
        """
        output_dir = self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        reg = Registry(output_dir / ".processed.json")

        if not self.config.force and reg.is_processed(source):
            self.log(f"[跳过] 已处理: {source}")
            entry = next((e for e in reg.get_by_status("done") if e["source"] == source), None)
            if entry:
                return output_dir / entry["output_file"]

        if crawl:
            return asyncio.run(self._crawl_site(source, limit, reg))
        else:
            return asyncio.run(self._crawl_single(source, reg))

    async def _crawl_single(self, url: str, reg: Registry) -> Path:
        from crawl4ai import AsyncWebCrawler

        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url)

        if not result.success:
            reg.mark(url, "failed", error=f"crawl4ai 返回失败: {url}")
            raise RuntimeError(f"页面提取失败: {url}")

        filename = _url_to_filename(url)
        out_path = self.config.output_dir / filename
        write_frontmatter_file(
            path=out_path,
            content=result.markdown or "",
            source=url,
            type="web",
        )
        reg.mark(url, "done", output_file=filename)
        self.log(f"[完成] {url} → {filename}")
        return out_path

    async def _crawl_site(self, site_url: str, limit: int, reg: Registry) -> Path:
        """整站爬取，深度优先，最多 limit 页，限制在同域名内。"""
        from crawl4ai import AsyncWebCrawler

        visited: set[str] = set()
        results: list[Path] = []

        async def crawl_page(crawler, url: str, depth: int = 0):
            if url in visited or depth > 3 or len(visited) >= limit:
                return
            if urlparse(url).netloc != urlparse(site_url).netloc:
                return
            if not self.config.force and reg.is_processed(url):
                visited.add(url)
                return

            visited.add(url)
            result = await crawler.arun(url=url)
            if not result.success:
                return

            filename = _url_to_filename(url)
            out_path = self.config.output_dir / filename
            write_frontmatter_file(
                path=out_path,
                content=result.markdown or "",
                source=url,
                type="web",
            )
            reg.mark(url, "done", output_file=filename)
            self.log(f"[{len(visited)}] {url} → {filename}")
            results.append(out_path)

            for link in (result.links.get("internal") or []):
                full_url = urljoin(site_url, link.get("href", ""))
                await crawl_page(crawler, full_url, depth + 1)

        async with AsyncWebCrawler(verbose=False) as crawler:
            await crawl_page(crawler, site_url)

        self.log(f"整站爬取完成，共 {len(results)} 页 → {self.config.output_dir}/")
        # 返回第一个文件路径（入口页）
        return results[0] if results else self.config.output_dir / _url_to_filename(site_url)
```

- [ ] **步骤 3：冒烟测试（需要网络）**

```bash
cd /tmp/ce_test
content-extract web https://example.com
ls raw/
```

预期：`raw/web__example-com__*.md` 文件出现，内容含 `source: https://example.com`。

- [ ] **步骤 4：验证 frontmatter 格式**

```bash
head -10 raw/web__example-com__*.md
```

预期输出：
```
---
source: https://example.com
type: web
extracted_at: 2026-...
content_hash: xxxxxxxx
---
```

- [ ] **步骤 5：提交**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
git add content_extract/extractors/web.py
git commit -m "feat: 添加 WebExtractor（crawl4ai 单页/整站）"
```

---

### Task 8：extractors/youtube.py（YouTube 字幕+元数据）

**文件：**
- 新建：`content-extract/content_extract/extractors/youtube.py`

- [ ] **步骤 1：安装依赖**

```bash
pip install youtube-transcript-api yt-dlp -q
```

- [ ] **步骤 2：实现 youtube.py**

```python
# content-extract/content_extract/extractors/youtube.py
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .base import BaseExtractor, ExtractConfig
from ..registry import Registry
from ..utils.frontmatter import write_frontmatter_file


def _extract_video_id(url: str) -> str:
    """从 YouTube URL 提取视频 ID。支持 watch?v=、youtu.be/ 和 /shorts/ 格式。"""
    parsed = urlparse(url)
    if parsed.netloc in ("youtu.be",):
        return parsed.path.lstrip("/")
    qs = parse_qs(parsed.query)
    if "v" in qs:
        return qs["v"][0]
    # /shorts/VIDEO_ID 或 /embed/VIDEO_ID
    match = re.search(r"/(?:shorts|embed)/([a-zA-Z0-9_-]{11})", parsed.path)
    if match:
        return match.group(1)
    raise ValueError(f"无法从 URL 提取视频 ID: {url}")


def _get_video_meta(video_id: str) -> dict:
    """用 yt-dlp 获取视频元数据（标题、时长、章节）。"""
    r = subprocess.run(
        ["yt-dlp", "--skip-download", "-J", f"https://www.youtube.com/watch?v={video_id}"],
        capture_output=True,
        text=True,
    )
    if r.returncode == 0:
        return json.loads(r.stdout)
    return {}


class YouTubeExtractor(BaseExtractor):
    @property
    def supported_domains(self) -> list[str]:
        return ["youtube.com", "youtu.be"]

    def extract(self, source: str) -> Path:
        """提取单个 YouTube 视频（字幕+元数据）。"""
        output_dir = self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        reg = Registry(output_dir / ".processed.json")

        if not self.config.force and reg.is_processed(source):
            self.log(f"[跳过] 已处理: {source}")
            entry = next((e for e in reg.get_by_status("done") + reg.get_by_status("needs_transcription")
                          if e["source"] == source), None)
            if entry:
                return output_dir / entry["output_file"]

        video_id = _extract_video_id(source)
        return self._fetch_video(video_id, source, reg)

    def _fetch_video(self, video_id: str, source: str, reg: Registry) -> Path:
        from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

        self.log(f"[YouTube] 获取元数据: {video_id}")
        meta = _get_video_meta(video_id)
        title = meta.get("title", video_id)
        chapters = meta.get("chapters") or []
        duration = meta.get("duration", 0)

        # 尝试获取字幕，优先中文
        transcript_text = None
        try:
            entries = YouTubeTranscriptApi.get_transcript(video_id, languages=["zh-Hans", "zh", "en"])
            lines = []
            for e in entries:
                ts = int(e["start"])
                m, s = divmod(ts, 60)
                lines.append(f"[{m:02d}:{s:02d}] {e['text']}")
            transcript_text = "\n".join(lines)
            self.log(f"[YouTube] 字幕获取成功: {len(lines)} 行")
        except (TranscriptsDisabled, NoTranscriptFound):
            self.log(f"[YouTube] 无字幕，将加入转录队列: {video_id}")

        # 组装正文
        body_lines = [f"# {title}\n"]
        body_lines.append(f"- **时长**: {duration // 60}:{duration % 60:02d}")
        if chapters:
            body_lines.append("\n## 章节结构")
            for ch in chapters:
                ts = int(ch.get("start_time", 0))
                m, s = divmod(ts, 60)
                body_lines.append(f"- [{m:02d}:{s:02d}] {ch['title']}")
        body_lines.append("\n## 字幕全文")
        body_lines.append(transcript_text if transcript_text else "*无字幕，待 Whisper 转录*")
        body = "\n".join(body_lines)

        filename = f"yt__{video_id}.md"
        out_path = output_dir = self.config.output_dir
        out_path = output_dir / filename

        write_frontmatter_file(
            path=out_path,
            content=body,
            source=source,
            type="video",
            platform="youtube",
        )

        if transcript_text:
            reg.mark(source, "done", output_file=filename)
        else:
            reg.mark(source, "needs_transcription", output_file=filename)
            # 兼容旧格式 needs_transcription.txt
            needs_file = output_dir / "needs_transcription.txt"
            with open(needs_file, "a", encoding="utf-8") as f:
                f.write(f"https://www.youtube.com/watch?v={video_id}\n")

        self.log(f"[YouTube] {title} → {filename}")
        return out_path
```

- [ ] **步骤 3：冒烟测试（需要网络）**

```bash
cd /tmp/ce_test
content-extract video "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
ls raw/yt__dQw4w9WgXcQ.md
```

预期：文件存在。

- [ ] **步骤 4：检查内容**

```bash
head -20 raw/yt__dQw4w9WgXcQ.md
```

预期：frontmatter 含 `type: video`、`platform: youtube`，正文含 `# Never Gonna Give You Up`。

- [ ] **步骤 5：提交**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
git add content_extract/extractors/youtube.py
git commit -m "feat: 添加 YouTubeExtractor（字幕+元数据+章节）"
```

---

### Task 9：extractors/bilibili.py（yt-dlp + SRT清洗）

**文件：**
- 新建：`content-extract/content_extract/extractors/bilibili.py`

- [ ] **步骤 1：实现 bilibili.py**

```python
# content-extract/content_extract/extractors/bilibili.py
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .base import BaseExtractor, ExtractConfig
from ..registry import Registry
from ..utils.frontmatter import write_frontmatter_file


def _ytdlp_json(url: str, cookie_file: str | None) -> dict:
    cmd = ["yt-dlp", "--skip-download", "-J", url]
    if cookie_file:
        cmd = ["yt-dlp", "--cookies", cookie_file, "--skip-download", "-J", url]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        return json.loads(r.stdout)
    return {}


def _parse_srt(srt_text: str) -> list[tuple[str, str]]:
    """解析 SRT 文件，返回 [(时间戳, 文本)] 列表。"""
    blocks = re.split(r"\n{2,}", srt_text.strip())
    result = []
    for block in blocks:
        parts = block.strip().split("\n")
        if len(parts) < 3:
            continue
        ts_str = parts[1].split(" --> ")[0]
        h, m, s = ts_str.replace(",", ".").split(":")
        sec = int(h) * 3600 + int(m) * 60 + float(s)
        mm, ss = divmod(int(sec), 60)
        # 去除 HTML 标签（B站字幕含 <font> 等标签）
        text = re.sub(r"<[^>]+>", "", " ".join(parts[2:]))
        result.append((f"[{mm:02d}:{ss:02d}]", text.strip()))
    return result


def _dedupe_adjacent(entries: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """去除相邻重复行（B站 AI 字幕特有问题：同一句话重复出现）。"""
    deduped = []
    for ts, text in entries:
        if not deduped:
            deduped.append((ts, text))
        elif text == deduped[-1][1]:
            continue
        elif text.startswith(deduped[-1][1]):
            # 后一行包含前一行内容（字幕滚动累积），用较长的版本替换
            deduped[-1] = (ts, text)
        else:
            deduped.append((ts, text))
    return deduped


class BilibiliExtractor(BaseExtractor):
    @property
    def supported_domains(self) -> list[str]:
        return ["bilibili.com", "b23.tv"]

    def extract(self, source: str) -> Path:
        output_dir = self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        reg = Registry(output_dir / ".processed.json")

        if not self.config.force and reg.is_processed(source):
            self.log(f"[跳过] 已处理: {source}")
            entry = next(
                (e for e in reg.get_by_status("done") + reg.get_by_status("needs_transcription")
                 if e["source"] == source),
                None,
            )
            if entry:
                return output_dir / entry["output_file"]

        cookie_file = self.config.cookies.get("bilibili")
        if cookie_file:
            cookie_file = str(Path(cookie_file).expanduser())
            if not Path(cookie_file).exists():
                cookie_file = None
                self.log("[警告] Bilibili Cookie 文件不存在，尝试无 Cookie 模式（AI 字幕可能不可用）")

        self.log(f"[Bilibili] 获取元数据: {source}")
        meta = _ytdlp_json(source, cookie_file)
        vid = meta.get("id", "unknown")
        title = meta.get("title", vid)
        duration = meta.get("duration") or 0
        chapters = meta.get("chapters") or []

        # 尝试下载字幕到临时目录
        transcript = self._get_subtitle(source, vid, cookie_file)

        # 组装正文
        body_lines = [f"# {title}\n"]
        body_lines.append(f"- **UP主**: {meta.get('uploader', '')}")
        body_lines.append(f"- **时长**: {duration // 60}:{duration % 60:02d}")
        if chapters:
            body_lines.append("\n## 章节结构")
            for ch in chapters:
                ts = int(ch.get("start_time", 0))
                m, s = divmod(ts, 60)
                body_lines.append(f"- [{m:02d}:{s:02d}] {ch['title']}")
        body_lines.append("\n## 字幕全文")
        body_lines.append(transcript if transcript else "*无字幕，待 Whisper 转录*")
        body = "\n".join(body_lines)

        slug = re.sub(r'[/\\:*?"<>|]', "-", title[:40]).replace(" ", "_")
        filename = f"bili__{vid}__{slug}.md"
        out_path = output_dir / filename

        write_frontmatter_file(
            path=out_path,
            content=body,
            source=source,
            type="video",
            platform="bilibili",
        )

        if transcript:
            reg.mark(source, "done", output_file=filename)
        else:
            reg.mark(source, "needs_transcription", output_file=filename)
            needs_file = output_dir / "needs_transcription.txt"
            with open(needs_file, "a", encoding="utf-8") as f:
                f.write(f"{source}\n")

        self.log(f"[Bilibili] {title} → {filename}")
        return out_path

    def _get_subtitle(self, url: str, video_id: str, cookie_file: str | None) -> str | None:
        """下载 SRT 字幕并清洗，返回格式化文本。无字幕返回 None。"""
        tmp_dir = Path(tempfile.mkdtemp(prefix=f"bili_{video_id}_"))
        try:
            cmd = ["yt-dlp", "--skip-download", "--write-auto-sub", "--write-sub",
                   "--sub-lang", "zh-Hans,zh", "--convert-subs", "srt",
                   "-o", str(tmp_dir / "%(id)s"), url]
            if cookie_file:
                cmd = ["yt-dlp", "--cookies", cookie_file,
                       "--skip-download", "--write-auto-sub", "--write-sub",
                       "--sub-lang", "zh-Hans,zh", "--convert-subs", "srt",
                       "-o", str(tmp_dir / "%(id)s"), url]
            subprocess.run(cmd, capture_output=True)

            srt_files = list(tmp_dir.glob("*.srt"))
            if not srt_files:
                return None

            entries = _parse_srt(srt_files[0].read_text(encoding="utf-8"))
            entries = _dedupe_adjacent(entries)
            return "\n".join(f"{ts} {text}" for ts, text in entries)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
```

- [ ] **步骤 2：验证 SRT 解析逻辑（离线测试）**

```python
# 在 Python REPL 中验证 _parse_srt 和 _dedupe_adjacent
import sys
sys.path.insert(0, "/Users/I340818/Documents/ai_workspace/content-extract")
from content_extract.extractors.bilibili import _parse_srt, _dedupe_adjacent

srt = """1
00:00:01,000 --> 00:00:03,000
你好世界

2
00:00:03,500 --> 00:00:05,000
你好世界

3
00:00:05,000 --> 00:00:07,000
这是第二句
"""
entries = _parse_srt(srt)
print(entries)  # [('[00:01]', '你好世界'), ('[00:03]', '你好世界'), ('[00:05]', '这是第二句')]
deduped = _dedupe_adjacent(entries)
print(deduped)  # [('[00:01]', '你好世界'), ('[00:05]', '这是第二句')]
assert len(deduped) == 2, "相邻重复行应被去除"
print("✓ SRT 解析测试通过")
```

- [ ] **步骤 3：提交**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
git add content_extract/extractors/bilibili.py
git commit -m "feat: 添加 BilibiliExtractor（yt-dlp + SRT清洗）"
```

---

### Task 10：transcribe/whisper_local.py

**文件：**
- 新建：`content-extract/content_extract/transcribe/whisper_local.py`

- [ ] **步骤 1：安装 faster-whisper**

```bash
pip install faster-whisper -q
```

- [ ] **步骤 2：实现 whisper_local.py**

```python
# content-extract/content_extract/transcribe/whisper_local.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class WhisperConfig:
    """faster-whisper 转录配置。"""
    model: str = "medium"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str = "zh"
    vad_filter: bool = True
    no_speech_threshold: float = 0.6


def transcribe(audio_path: Path, cfg: WhisperConfig | None = None) -> str:
    """
    用 faster-whisper 转录音频文件。
    返回带时间戳的文本，格式：'[MM:SS] 转录文本'，每行一句。
    """
    from faster_whisper import WhisperModel

    if cfg is None:
        cfg = WhisperConfig()

    model = WhisperModel(cfg.model, device=cfg.device, compute_type=cfg.compute_type)
    segments, _info = model.transcribe(
        str(audio_path),
        language=cfg.language,
        vad_filter=cfg.vad_filter,
        no_speech_threshold=cfg.no_speech_threshold,
        condition_on_previous_text=False,
    )

    lines = []
    for seg in segments:
        if seg.no_speech_prob < cfg.no_speech_threshold and seg.text.strip():
            m, s = divmod(int(seg.start), 60)
            lines.append(f"[{m:02d}:{s:02d}] {seg.text.strip()}")

    return "\n".join(lines)
```

- [ ] **步骤 3：验证可导入**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
python -c "from content_extract.transcribe.whisper_local import transcribe, WhisperConfig; print('导入成功')"
```

预期：`导入成功`（不加载模型，只验证语法）。

- [ ] **步骤 4：提交**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
git add content_extract/transcribe/whisper_local.py
git commit -m "feat: 添加 whisper_local.py（faster-whisper 封装）"
```

---

### Task 11：transcribe/queue.py（转录队列消费）

**文件：**
- 新建：`content-extract/content_extract/transcribe/queue.py`

- [ ] **步骤 1：实现 queue.py**

```python
# content-extract/content_extract/transcribe/queue.py
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from .whisper_local import WhisperConfig, transcribe
from ..registry import Registry


def process_queue(
    output_dir: Path,
    model: str = "medium",
    device: str = "cpu",
    compute_type: str = "int8",
) -> None:
    """
    消费转录队列：
    1. 读取 registry 中 needs_transcription 状态的条目
    2. 兼容读取旧格式 needs_transcription.txt
    3. 下载音频 → Whisper 转录 → 更新 raw 文件 → 标记 done
    """
    reg = Registry(output_dir / ".processed.json")
    cfg = WhisperConfig(model=model, device=device, compute_type=compute_type)

    # 从 registry 获取待处理列表
    pending = reg.get_by_status("needs_transcription")

    # 兼容旧格式 needs_transcription.txt
    needs_file = output_dir / "needs_transcription.txt"
    if needs_file.exists():
        existing_sources = {e["source"] for e in pending}
        for line in needs_file.read_text(encoding="utf-8").splitlines():
            url = line.strip()
            if url and url not in existing_sources:
                pending.append({"source": url, "output_file": None})

    if not pending:
        print("转录队列为空，无需处理。")
        return

    print(f"待转录: {len(pending)} 个视频")

    for entry in pending:
        url = entry["source"]
        _transcribe_one(url, entry.get("output_file"), output_dir, reg, cfg)

    # 清空旧格式队列文件
    if needs_file.exists():
        needs_file.write_text("", encoding="utf-8")


def _transcribe_one(
    url: str,
    output_file: str | None,
    output_dir: Path,
    reg: Registry,
    cfg: WhisperConfig,
) -> None:
    # 用 yt-dlp --print id 获取视频 ID，避免手工解析不同平台 URL
    r_id = subprocess.run(
        ["yt-dlp", "--skip-download", "--print", "id", url],
        capture_output=True,
        text=True,
    )
    if r_id.returncode != 0:
        print(f"  [失败] 无法获取 ID: {url}")
        reg.mark(url, "failed", error="yt-dlp 获取 ID 失败")
        return

    vid = r_id.stdout.strip()
    audio_path = Path(tempfile.gettempdir()) / f"transcribe_{vid}.mp3"

    print(f"  下载音频: {url}")
    r_dl = subprocess.run(
        ["yt-dlp", "-x", "--audio-format", "mp3", "--audio-quality", "5",
         "-o", str(audio_path), url],
        capture_output=True,
    )
    if r_dl.returncode != 0 or not audio_path.exists():
        print(f"  [失败] 音频下载失败: {url}")
        reg.mark(url, "failed", error="音频下载失败")
        return

    print(f"  转录中（模型: {cfg.model}，设备: {cfg.device}）...")
    try:
        transcript = transcribe(audio_path, cfg)
    except Exception as e:
        print(f"  [失败] 转录出错: {e}")
        reg.mark(url, "failed", error=str(e))
        return
    finally:
        audio_path.unlink(missing_ok=True)

    # 找到对应的 raw 文件（按 video ID 匹配文件名）
    raw_file = None
    if output_file:
        candidate = output_dir / output_file
        if candidate.exists():
            raw_file = candidate
    if raw_file is None:
        for f in output_dir.glob("*.md"):
            if vid in f.name:
                raw_file = f
                break

    if raw_file and raw_file.exists():
        content = raw_file.read_text(encoding="utf-8")
        content = content.replace("*无字幕，待 Whisper 转录*", transcript)
        raw_file.write_text(content, encoding="utf-8")
        print(f"  → 已更新 {raw_file.name}")
        reg.mark(url, "done", output_file=raw_file.name)
    else:
        print(f"  [警告] 找不到对应 raw 文件，video_id={vid}")
        reg.mark(url, "done")
```

- [ ] **步骤 2：验证可导入**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
python -c "from content_extract.transcribe.queue import process_queue; print('导入成功')"
```

预期：`导入成功`。

- [ ] **步骤 3：验证 transcribe 命令在空队列时的行为**

```bash
cd /tmp/ce_test
content-extract transcribe
```

预期：`转录队列为空，无需处理。`

- [ ] **步骤 4：提交**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
git add content_extract/transcribe/queue.py
git commit -m "feat: 添加 transcribe/queue.py 转录队列消费"
```

---

## 最终验收

### Task 12：完整验收测试

- [ ] **步骤 1：全量安装并运行所有单元测试**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
pip install -e . -q
pytest tests/ -v
```

预期：所有测试 PASS，无 FAIL。

- [ ] **步骤 2：验证 --help 输出**

```bash
content-extract --help
```

预期输出包含：`init`、`status`、`web`、`video`、`transcribe`。

- [ ] **步骤 3：验证 init 命令**

```bash
cd /tmp && rm -rf ce_final && mkdir ce_final && cd ce_final
content-extract init
```

预期：
```
已创建: wiki/DASHBOARD.md
已创建: CLAUDE.md
已创建: .gitignore
初始化完成。...
```

- [ ] **步骤 4：验证 status 命令（空队列）**

```bash
content-extract status
```

预期：`暂无处理记录。`

- [ ] **步骤 5：验证 web 提取（需要网络）**

```bash
content-extract web https://example.com/
ls raw/
head -8 raw/web__example-com__*.md
```

预期：frontmatter 含 `source: https://example.com/`，`type: web`。

- [ ] **步骤 6：验证 YouTube 提取（需要网络）**

```bash
content-extract video "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
ls raw/yt__dQw4w9WgXcQ.md
head -8 raw/yt__dQw4w9WgXcQ.md
```

预期：文件存在，frontmatter 含 `type: video`，`platform: youtube`。

- [ ] **步骤 7：验证 status 显示有记录**

```bash
content-extract status
```

预期：`✓ 已完成: 2`（web + youtube 各一条）。

- [ ] **步骤 8：最终提交**

```bash
cd /Users/I340818/Documents/ai_workspace/content-extract
git add -A
git commit -m "feat: Phase 0 + Phase 1 实现完成（web/youtube/bilibili/whisper）"
```

---

## 自审检查结果

**Spec 覆盖：**
- ✅ Phase 0：pyproject.toml / requirements.txt / .gitignore（Task 1）
- ✅ utils/frontmatter.py（Task 2）
- ✅ registry.py（Task 3）
- ✅ config.py（Task 4）
- ✅ extractors/base.py + ExtractConfig（Task 5）
- ✅ cli.py init/status 命令（Task 6）
- ✅ extractors/web.py（Task 7）
- ✅ extractors/youtube.py（Task 8）
- ✅ extractors/bilibili.py（Task 9）
- ✅ transcribe/whisper_local.py（Task 10）
- ✅ transcribe/queue.py（Task 11）
- ✅ 验收标准逐条（Task 12）

**类型一致性：**
- `ExtractConfig` 在 Task 5 定义，Task 6-9 均正确使用
- `Registry(path).mark(source, status, **kwargs)` 在 Task 3 定义，Task 7-11 均正确调用
- `write_frontmatter_file(path, content, source, type, ...)` 在 Task 2 定义，Task 7-9 均正确调用
- `WhisperConfig` 在 Task 10 定义，Task 11 正确导入和使用
