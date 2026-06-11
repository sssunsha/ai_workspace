from __future__ import annotations

import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from .base import BaseExtractor, ExtractConfig
from ..utils.frontmatter import write_frontmatter_file

_TOPIC_ROLES = [
    "入门概述",
    "核心方法论",
    "深度参考",
    "代码实例",
    "案例研究",
    "工具介绍",
    "个人笔记",
]

SUPPORTED_EXTENSIONS = {".md", ".html", ".htm", ".txt"}


def _extract_html_text(path: Path) -> str:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
        for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
            level = int(tag.name[1])
            tag.replace_with(f"\n{'#' * level} {tag.get_text()}\n")
        for code in soup.find_all("pre"):
            code.replace_with(f"\n```\n{code.get_text()}\n```\n")
        return soup.get_text(separator="\n")
    except ImportError:
        raw = path.read_text(encoding="utf-8", errors="ignore")
        return re.sub(r"<[^>]+>", "", raw)


class LocalTopicExtractor(BaseExtractor):
    """将本地 md/html/txt 文件导入到 Topic 目录，不复制原文件，只生成引用文件。"""

    @property
    def supported_domains(self) -> list[str]:
        return []

    def extract(self, source: str, topic: str = "", topic_role: str = "") -> Path:
        src = Path(source).resolve()
        if not src.exists():
            raise FileNotFoundError(f"文件不存在: {src}")
        if src.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {src.suffix}（支持：{', '.join(SUPPORTED_EXTENSIONS)}）")

        if not topic:
            raise ValueError("Topic 名称不能为空")

        # 读取内容
        if src.suffix.lower() in (".html", ".htm"):
            content = _extract_html_text(src)
        else:
            content = src.read_text(encoding="utf-8", errors="ignore")
        content = re.sub(r"\n{3,}", "\n\n", content).strip()

        # 输出到 raw/topics/<topic>/
        topic_slug = re.sub(r'[/\\:*?"<>|]', "-", topic)
        output_dir = self.config.output_dir / "topics" / topic_slug
        output_dir.mkdir(parents=True, exist_ok=True)

        slug = re.sub(r'[/\\:*?"<>|]', "-", src.stem)[:50]
        filename = f"local__{slug}.md"
        out_path = output_dir / filename

        # 写入引用文件（source 记录原始绝对路径）
        extra_frontmatter = {
            "format": src.suffix.lstrip("."),
            "topic": topic,
        }
        if topic_role:
            extra_frontmatter["topic_role"] = topic_role

        content_hash = hashlib.sha256(content.encode()).hexdigest()[:8]
        _write_topic_file(
            path=out_path,
            content=content,
            source=str(src),
            topic=topic,
            topic_role=topic_role,
            fmt=src.suffix.lstrip("."),
            content_hash=content_hash,
        )

        self.log(f"[LocalTopic] {src.name} → {filename}（topic: {topic}）")
        return out_path


def _write_topic_file(
    path: Path,
    content: str,
    source: str,
    topic: str,
    topic_role: str,
    fmt: str,
    content_hash: str,
) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    lines = [
        "---",
        f"source: {source}",
        f"type: local_doc",
        f"format: {fmt}",
        f"topic: \"{topic}\"",
    ]
    if topic_role:
        lines.append(f"topic_role: \"{topic_role}\"")
    lines += [
        f"extracted_at: {now}",
        f"content_hash: {content_hash}",
        "---",
        "",
        content,
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
