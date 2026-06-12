from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import ExtractConfig


def auto_detect_video(url: str, config: "ExtractConfig", **kwargs):
    """根据 URL 自动选择视频提取器（当前仅支持 Bilibili）。"""
    from .bilibili import BilibiliExtractor

    lower = url.lower()
    if "bilibili.com" in lower or "b23.tv" in lower:
        return BilibiliExtractor(config=config, **kwargs).extract(url)
    raise ValueError(f"不支持的视频平台（当前仅支持 Bilibili）: {url}")


def auto_detect_article(url: str, config: "ExtractConfig", **kwargs):
    """单篇文章提取，自动识别微信 / 头条 / 通用网页。"""
    from .article import ArticleExtractor
    return ArticleExtractor(config=config, **kwargs).extract(url)
