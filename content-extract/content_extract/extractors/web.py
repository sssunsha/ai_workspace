from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from urllib.parse import urljoin, urlparse

from .base import BaseExtractor, ExtractConfig
from ..registry import Registry
from ..utils.frontmatter import write_frontmatter_file
from ..utils.lang import detect_lang, should_follow


def _url_to_subfolder(seed_url: str) -> str:
    """从 seed URL 生成子目录名（相对于 output_dir）。

    示例：
      https://feelgoodpal.com/zh/blog/ → feelgoodpal-com__zh__blog
      https://example.com/             → example-com
    """
    parsed = urlparse(seed_url)
    netloc = parsed.netloc.replace(".", "-")
    path_slug = parsed.path.strip("/").replace("/", "__")
    return f"{netloc}__{path_slug}" if path_slug else netloc


def _url_to_page_filename(page_url: str, seed_url: str) -> str:
    """生成页面在 seed 子目录内的文件名。

    规则：
      - page == seed（入口页）      → index.md
      - page 在 seed 路径下的子页   → 相对路径段.md
      - page 在 seed 路径外（导航等）→ 完整路径段.md
      - 有 query string             → 追加 md5 前 6 位防碰撞
    """
    parsed = urlparse(page_url)
    seed_parsed = urlparse(seed_url)

    page_path = parsed.path.rstrip("/") or "/"
    seed_path = seed_parsed.path.rstrip("/") or "/"

    if page_path == seed_path:
        slug = "index"
    elif page_path.startswith(seed_path + "/"):
        rel = page_path[len(seed_path) + 1:].strip("/").replace("/", "__")
        slug = rel or "index"
    else:
        slug = page_path.strip("/").replace("/", "__") or "index"

    slug = slug[:80]
    if parsed.query:
        q_hash = hashlib.md5(parsed.query.encode()).hexdigest()[:6]
        return f"{slug}__{q_hash}.md"
    return f"{slug}.md"


class WebExtractor(BaseExtractor):
    @property
    def supported_domains(self) -> list[str]:
        return []

    def extract(self, source: str, crawl: bool = False, limit: int = 200) -> Path:
        """
        crawl=False（默认）：单页提取，输出到 output_dir/{seed_subfolder}/index.md
        crawl=True：整站 BFS 爬取，最多写入 limit 篇新页面

        Raises:
            ValueError: 入口 URL 包含不支持的语言（非 zh/en 系列）
        """
        seed_lang = detect_lang(source)
        self.log(f"[语言] 检测到语言: {seed_lang}，仅爬取 {seed_lang} 内容")

        output_dir = self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        reg = Registry(output_dir / ".processed.json")

        if not crawl and not self.config.force and reg.is_processed(source):
            self.log(f"[跳过] 已处理: {source}")
            entry = next((e for e in reg.get_by_status("done") if e["source"] == source), None)
            if entry and entry.get("output_file"):
                return output_dir / entry["output_file"]

        if crawl:
            return asyncio.run(self._crawl_site(source, limit, reg, seed_lang))
        return asyncio.run(self._crawl_single(source, reg))

    async def _crawl_single(self, url: str, reg: Registry) -> Path:
        from crawl4ai import AsyncWebCrawler

        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url)

        if not result.success:
            reg.mark(url, "failed", error=f"crawl4ai 返回失败: {url}")
            raise RuntimeError(f"页面提取失败: {url}")

        out_path = self._write_page(url, result.markdown or "", reg, seed_url=url)
        self.log(f"[完成] {url} → {out_path.relative_to(self.config.output_dir)}")
        return out_path

    async def _crawl_site(
        self, site_url: str, limit: int, reg: Registry, seed_lang: str
    ) -> Path:
        """整站爬取（BFS），最多写入 limit 篇新页面。

        已处理的 URL 仍请求以获取内链（保证 BFS 能向下展开），但跳过写文件。
        只跟进与 seed_lang 相同语言的内链，其他语言静默跳过。
        """
        from crawl4ai import AsyncWebCrawler
        from collections import deque

        seed_netloc = urlparse(site_url).netloc
        seen: set[str] = {site_url}
        results: list[Path] = []
        queue: deque[str] = deque([site_url])

        async with AsyncWebCrawler(verbose=False) as crawler:
            while queue and len(results) < limit:
                url = queue.popleft()
                out_path, links = await self._process_url(
                    url, site_url, seed_netloc, seed_lang, reg, crawler
                )
                if out_path is not None:
                    self.log(f"[{len(results)}] {url} → {out_path.relative_to(self.config.output_dir)}")
                    results.append(out_path)
                for href in links:
                    if href not in seen:
                        seen.add(href)
                        queue.append(href)

        self.log(f"整站爬取完成，共 {len(results)} 页 → {self.config.output_dir / _url_to_subfolder(site_url)}/")
        subfolder_dir = self.config.output_dir / _url_to_subfolder(site_url)
        return results[0] if results else subfolder_dir / "index.md"

    async def _process_url(
        self,
        url: str,
        site_url: str,
        seed_netloc: str,
        seed_lang: str,
        reg: Registry,
        crawler,
    ) -> tuple[Path | None, list[str]]:
        """处理单个 URL：返回 (写入路径或None, 内链列表)。

        已处理的 URL 仍请求以获取内链，但跳过写文件。
        """
        if not self._is_allowed(url, seed_netloc, seed_lang):
            return None, []
        already_done = not self.config.force and reg.is_processed(url)
        result = await crawler.arun(url=url)
        if not result.success:
            return None, []
        links = [
            urljoin(site_url, link.get("href", ""))
            for link in (result.links.get("internal") or [])
        ]
        if already_done:
            return None, links
        out_path = self._write_page(url, result.markdown or "", reg, seed_url=site_url)
        return out_path, links

    def _is_allowed(self, url: str, seed_netloc: str, seed_lang: str) -> bool:
        """检查 URL 是否满足域名和语言过滤条件。"""
        if urlparse(url).netloc != seed_netloc:
            return False
        return should_follow(url, seed_lang)

    def _write_page(self, url: str, markdown: str, reg: Registry, seed_url: str) -> Path:
        """写入 raw 文件到对应子目录，更新 registry，返回绝对路径。"""
        subfolder = _url_to_subfolder(seed_url)
        filename = _url_to_page_filename(url, seed_url)
        sub_dir = self.config.output_dir / subfolder
        sub_dir.mkdir(parents=True, exist_ok=True)
        out_path = sub_dir / filename
        content_hash = write_frontmatter_file(
            path=out_path, content=markdown, source=url, type="web",
        )
        # output_file 存相对于 output_dir 的路径，供 registry 查找
        reg.mark(url, "done", output_file=f"{subfolder}/{filename}", content_hash=content_hash)
        return out_path
