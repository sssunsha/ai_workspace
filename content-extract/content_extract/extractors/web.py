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

        种子页面无论是否已处理都访问一次以获取内链；其他已处理页面直接跳过。
        发现总数超过 limit 时通过 log 发送 __LIMIT_CHOICE__ 信号通知 TUI。
        """
        from crawl4ai import AsyncWebCrawler
        from collections import deque

        seed_netloc = urlparse(site_url).netloc
        seen: set[str] = {site_url}
        results: list[Path] = []
        queue: deque[str] = deque([site_url])
        seed_notified = False

        async with AsyncWebCrawler(verbose=False) as crawler:
            while queue and len(results) < limit:
                url = queue.popleft()
                is_seed = (url == site_url)
                out_path, links = await self._process_url(
                    url, site_url, seed_netloc, seed_lang, reg, crawler,
                    skip_if_done=(not is_seed),
                )
                if out_path is not None:
                    self.log(f"[{len(results)}] {url} → {out_path.relative_to(self.config.output_dir)}")
                    results.append(out_path)
                self._enqueue_links(links, seen, queue)
                if is_seed and not seed_notified:
                    seed_notified = True
                    self._notify_total(seen, reg, limit)

        return self._finish_crawl(site_url, limit, results, queue, reg)

    def _enqueue_links(self, links: list[str], seen: set[str], queue) -> None:
        """将新发现的内链加入 BFS 队列。"""
        for href in links:
            if href not in seen:
                seen.add(href)
                queue.append(href)

    def _notify_total(self, seen: set[str], reg: Registry, limit: int) -> None:
        """种子页面处理完后统计总数，若超过 limit 则发信号给 TUI 弹窗。"""
        total = len(seen)
        already = sum(1 for u in seen if reg.is_processed(u))
        if total > limit:
            self.log(f"__LIMIT_CHOICE__:{total}:{already}:{total - already}")

    def _finish_crawl(
        self, site_url: str, limit: int, results: list[Path], queue, reg: Registry
    ) -> Path:
        """BFS 结束后记录状态并返回入口页路径。"""
        subfolder_dir = self.config.output_dir / _url_to_subfolder(site_url)
        subfolder_name = _url_to_subfolder(site_url)
        if queue:
            remaining = len(queue)
            reg.mark_partial(subfolder_name, queue_remaining=remaining)
            self.log(
                f"已到达页数上限（{limit}），本次写入 {len(results)} 页 → {subfolder_dir}/\n"
                f"队列中还有约 {remaining} 个待处理 URL，可再次运行继续抓取"
            )
        else:
            self.log(f"整站爬取完成，共 {len(results)} 页 → {subfolder_dir}/（队列已全部处理）")
        return results[0] if results else subfolder_dir / "index.md"

    async def _process_url(
        self,
        url: str,
        site_url: str,
        seed_netloc: str,
        seed_lang: str,
        reg: Registry,
        crawler,
        skip_if_done: bool = True,
    ) -> tuple[Path | None, list[str]]:
        """处理单个 URL：返回 (写入路径或None, 内链列表)。

        skip_if_done=True（默认）：已处理的 URL 直接跳过，不发网络请求。
        skip_if_done=False（种子页面用）：即使已处理也要请求一次以获取内链。
        """
        if not self._is_allowed(url, seed_netloc, seed_lang):
            return None, []
        if skip_if_done and not self.config.force and reg.is_processed(url):
            return None, []
        result = await crawler.arun(url=url)
        if not result.success:
            return None, []
        links = [
            urljoin(site_url, link.get("href", ""))
            for link in (result.links.get("internal") or [])
        ]
        if not self.config.force and reg.is_processed(url):
            return None, links
        out_path = self._write_page(url, result.markdown or "", reg, seed_url=site_url)
        return out_path, links

    def _is_allowed(self, url: str, seed_netloc: str, seed_lang: str) -> bool:
        """检查 URL 是否满足域名和语言过滤条件。"""
        if urlparse(url).netloc != seed_netloc:
            return False
        return should_follow(url, seed_lang)

    def _write_page(self, url: str, markdown: str, reg: Registry, seed_url: str) -> Path:
        """写入 raw 文件到对应子目录，更新 registry，返回绝对路径。

        若 content hash 与 registry 中记录的相同，跳过写文件（内容未变化）。
        """
        import hashlib
        subfolder = _url_to_subfolder(seed_url)
        filename = _url_to_page_filename(url, seed_url)
        sub_dir = self.config.output_dir / subfolder
        sub_dir.mkdir(parents=True, exist_ok=True)
        out_path = sub_dir / filename

        # 计算新内容的 hash
        new_hash = hashlib.sha256(markdown.encode("utf-8")).hexdigest()[:8]

        # 若 hash 未变且文件已存在，跳过写入（内容无变化）
        existing = reg._data.get(url, {})
        if not self.config.force and existing.get("content_hash") == new_hash and out_path.exists():
            self.log(f"[无变化] {url}")
            return out_path

        content_hash = write_frontmatter_file(
            path=out_path, content=markdown, source=url, type="web",
        )
        reg.mark(url, "done", output_file=f"{subfolder}/{filename}", content_hash=content_hash)
        return out_path
