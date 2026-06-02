# Content Extract CLI — Phase 0 + Phase 1 设计文档

> 创建日期：2026-06-01
> 范围：Phase 0（脚手架） + Phase 1（核心提取器：web / youtube / bilibili / whisper）
> 参考文档：
> - `custom-skills/content-extraction.md`（操作手册）
> - `custom-skills/content-extraction-tool-plan.md`（工程设计文档）

---

## 一、目标与范围

### Phase 0：可运行骨架
- 初始化 `content-extract/` Python 项目
- CLI 入口：无参数打印占位提示，有参数分发子命令
- 状态管理（`.processed.json`）、配置加载、frontmatter 工具函数
- `init` / `status` 两条命令端到端可用
- `.gitignore`、`requirements.txt`、`pyproject.toml`

### Phase 1：三个核心提取器
- `extractors/web.py`：crawl4ai 整站 + 单页，含增量去重
- `extractors/youtube.py`：youtube-transcript-api 字幕 + yt-dlp 元数据 + 章节
- `extractors/bilibili.py`：yt-dlp + Cookie + SRT 重复行清洗
- `transcribe/whisper_local.py`：faster-whisper 封装
- `transcribe/queue.py`：消费 `needs_transcription.txt`
- CLI 命令：`content-extract web <url>`、`content-extract video <url>`、`content-extract transcribe`

---

## 二、目录结构

```
content-extract/
├── pyproject.toml
├── requirements.txt
├── .gitignore
└── content_extract/
    ├── __init__.py
    ├── cli.py
    ├── registry.py
    ├── config.py
    ├── extractors/
    │   ├── base.py
    │   ├── web.py
    │   ├── youtube.py
    │   └── bilibili.py
    ├── transcribe/
    │   ├── whisper_local.py
    │   └── queue.py
    └── utils/
        └── frontmatter.py
```

---

## 三、BaseExtractor 接口（已确认方案 A）

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

@dataclass
class ExtractConfig:
    output_dir: Path = Path("./raw")
    force: bool = False
    cookies: dict[str, str] = field(default_factory=dict)  # {"bilibili": "~/.content-extract/bilibili_cookies.txt"}
    extra: dict = field(default_factory=dict)               # 提取器特有参数

class BaseExtractor(ABC):
    def __init__(
        self,
        config: ExtractConfig,
        on_progress: Callable[[str], None] | None = None,
    ):
        self.config = config
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

**设计决策**：
- `config` 在构造时注入，不在 `extract()` 签名重复传，避免歧义
- `on_progress` 回调默认 `print()`，CLI 和 TUI 均可替换
- `supported_domains` 用于后续 `auto_detect_video()` 自动路由

---

## 四、各模块设计

### 4.1 registry.py

读写 `{output_dir}/.processed.json`，结构：

```json
{
  "https://example.com": {
    "status": "done | needs_transcription | failed",
    "output_file": "web__example-com.md",
    "extracted_at": "2026-06-01T10:30:00",
    "content_hash": "a1b2c3d4",
    "retry_count": 0,
    "error": null
  }
}
```

接口：
- `Registry(path)` — 加载文件
- `is_processed(source) -> bool`
- `mark(source, status, **kwargs)` — 写入/更新记录
- `get_by_status(status) -> list[dict]`
- `save()` — 持久化到磁盘

### 4.2 config.py

优先级：项目级 `./content-extract.toml` > 全局 `~/.content-extract/config.toml` > 硬编码默认值。

```python
def load_config(project_dir: Path | None = None) -> dict:
    """加载合并后的配置，返回字典。"""
```

### 4.3 utils/frontmatter.py

```python
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
```

`content_hash`：对 `content` 做 SHA256，取前 8 位十六进制。

### 4.4 extractors/web.py

基于操作手册 1.1 节 `crawl_site.py`，关键扩展：
- 默认单页提取（`depth=0`），`--crawl` 标志触发整站模式
- 增量去重：先查 `Registry`，已处理则跳过
- 文件名格式：`web__{netloc}__{path_slug}.md`（netloc 的 `.` 替换为 `-`）
- frontmatter 写入：`type=web`，无 platform 字段

### 4.5 extractors/youtube.py

基于操作手册 1.2 节 YouTube 部分：
1. `yt-dlp --skip-download -J` 获取元数据（标题、时长、章节）
2. `youtube-transcript-api` 获取字幕，优先 `zh-Hans > zh > en`
3. 无字幕：写入 `*无字幕，待 Whisper 转录*`，调用 `registry.mark(source, "needs_transcription")`
4. 文件名：`yt__{video_id}.md`
5. frontmatter：`type=video, platform=youtube`

### 4.6 extractors/bilibili.py

基于操作手册 1.2 节 Bilibili 部分：
1. `yt-dlp --cookies {cookie_file} --skip-download -J` 获取元数据
2. `yt-dlp --write-auto-sub --convert-subs srt` 下载 SRT 到临时目录
3. SRT 解析 + 去相邻重复行（B站特有问题）
4. 临时目录用 `shutil.rmtree` 清理
5. 文件名：`bili__{vid}__{slug}.md`
6. Cookie 路径从 `config.cookies["bilibili"]` 读取

### 4.7 transcribe/whisper_local.py

```python
@dataclass
class WhisperConfig:
    model: str = "medium"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str = "zh"
    vad_filter: bool = True

def transcribe(audio_path: Path, cfg: WhisperConfig) -> str:
    """返回带时间戳的转录文本，格式 '[MM:SS] text'。"""
```

### 4.8 transcribe/queue.py

消费 `needs_transcription.txt`（旧格式兼容）和 registry 中 `status=needs_transcription` 的条目：
1. 用 `yt-dlp --print id` 获取视频 ID（避免手动解析各平台 URL）
2. 下载 mp3 到 `/tmp/`
3. 调用 `whisper_local.transcribe()`
4. 替换对应 raw 文件中的 `*无字幕，待 Whisper 转录*` 占位符
5. 更新 registry 为 `done`

---

## 五、CLI 命令设计

### 入口（cli.py）

```python
@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx):
    if ctx.invoked_subcommand is None:
        click.echo("TUI 即将上线，当前请使用子命令。运行 content-extract --help 查看可用命令。")
```

### 子命令

```bash
content-extract init              # 初始化项目
content-extract status            # 显示队列状态
content-extract web <url>         # 提取网页（--crawl 整站，--limit N）
content-extract video <url>       # 提取视频（自动识别平台）
content-extract transcribe        # 消费转录队列
```

### init 命令生成的文件

- `wiki/DASHBOARD.md`：Dataview 模板（见操作手册 2.5 节）
- `CLAUDE.md`：知识库构建规则模板（见操作手册 2.2 节）
- `.gitignore`：排除 `cookies*.txt`、`raw/`、`audio/`、`chroma-db/`、`.env`

---

## 六、验收标准

| 命令 | 预期结果 |
|------|---------|
| `pip install -e .` | 成功，无错误 |
| `content-extract --help` | 显示所有子命令 |
| `content-extract init` | 生成 `wiki/DASHBOARD.md`、`CLAUDE.md`、`.gitignore` |
| `content-extract status` | 显示空队列（"暂无处理记录"）|
| `content-extract web https://example.com/article` | 输出 `./raw/web__*.md`，frontmatter 格式正确 |
| `content-extract video https://www.youtube.com/watch?v=dQw4w9WgXcQ` | 输出 `./raw/yt__dQw4w9WgXcQ.md` |

---

## 七、依赖分组（requirements.txt）

```
# core
click>=8.1
toml>=0.10

# video
yt-dlp
youtube-transcript-api

# ebook（Phase 2，占位）
# ebooklib
# pymupdf4llm

# rag（Phase 4，占位）
# chromadb
# sentence-transformers

# ui（Phase 2，占位）
# textual
# streamlit
```

Phase 1 还需要：
```
# web
crawl4ai

# transcription
faster-whisper
```

---

## 八、测试策略

- `registry.py`、`config.py`、`utils/frontmatter.py`：纯单元测试，无外部依赖
- `extractors/`：集成测试用真实 URL（YouTube 公开视频、example.com）
- `transcribe/`：用短音频文件（< 10s）验证输出格式
- 验收测试：按第六节验收标准逐条执行
