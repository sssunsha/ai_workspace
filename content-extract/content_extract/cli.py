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
        from .ui.tui import TUIApp
        TUIApp().run()


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
    """提取视频内容（当前支持 Bilibili）"""
    from .extractors.base import ExtractConfig
    from .extractors import auto_detect_video

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
- `bili__`：Bilibili 视频转录
- `article__`：单篇网络文章

每个 raw/ 文件的 frontmatter 包含：
```yaml
source:        # 原始 URL 或本地路径
type:          # web | video | ebook | code | local_doc | github | article
platform:      # 仅 video/article 有：bilibili
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
