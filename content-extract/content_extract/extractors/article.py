from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from .base import BaseExtractor, ExtractConfig
from ..registry import Registry
from ..utils.frontmatter import write_frontmatter_file


def _detect_platform(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "mp.weixin.qq.com" in host or "weixin.qq.com" in host:
        return "wechat"
    if "toutiao.com" in host or "ixigua.com" in host:
        return "toutiao"
    return "generic"


def _slug_from_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/").replace("/", "__")[:60]
    uid = hashlib.md5(url.encode()).hexdigest()[:6]
    return f"{parsed.netloc.replace('.', '-')}__{path}__{uid}"


# ── 微信抓取（camoufox stealth browser）────────────────────────────────────

def _fetch_wechat(url: str) -> dict | None:
    """用 camoufox 隐身浏览器抓取微信公众号文章，返回 {title, text} 或 None。"""
    try:
        from camoufox import Camoufox, DefaultAddons
    except ImportError:
        return None

    try:
        with Camoufox(
            headless=True,
            exclude_addons=[DefaultAddons.UBO],
            geoip=False,
        ) as browser:
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Mobile/15E148 MicroMessenger/8.0.49(0x28003129) "
                    "NetType/WIFI Language/zh_CN"
                ),
                viewport={"width": 390, "height": 844},
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )
            page = ctx.new_page()
            try:
                page.goto(url, wait_until="load", timeout=30000)
                page.wait_for_timeout(5000)
                page.evaluate(_SCROLL_JS)
                page.wait_for_timeout(3000)
                title = page.title()
                text = page.evaluate("() => document.body.innerText")
                return {"title": title, "text": text}
            finally:
                page.close()
    except Exception:
        return None


# ── 今日头条抓取（playwright）──────────────────────────────────────────────

def _fetch_toutiao(url: str) -> dict | None:
    """用 Playwright Chromium 抓取今日头条文章，返回 {title, text} 或 None。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )
            page = ctx.new_page()
            try:
                page.goto(url, wait_until="load", timeout=30000)
                page.wait_for_timeout(3000)
                page.evaluate(_SCROLL_JS)
                page.wait_for_timeout(2000)
                title = page.title()
                text = page.evaluate("() => document.body.innerText")
                return {"title": title, "text": text}
            finally:
                page.close()
                browser.close()
    except Exception:
        return None


# ── 通用抓取（crawl4ai / Jina Reader 降级）─────────────────────────────────

def _fetch_generic(url: str) -> dict | None:
    """通用网页抓取，优先 crawl4ai，降级 Jina Reader。"""
    # 方案 A：crawl4ai
    try:
        import asyncio
        from crawl4ai import AsyncWebCrawler

        async def _crawl() -> dict | None:
            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.arun(url=url)
                if result.success and result.markdown:
                    return {"title": url, "text": result.markdown}
            return None

        result = asyncio.run(_crawl())
        if result:
            return result
    except Exception:
        pass

    # 方案 B：Jina Reader（无需安装）
    try:
        jina_url = f"https://r.jina.ai/{url}"
        r = subprocess.run(
            ["curl", "-s", "--max-time", "30", "-H", "Accept: text/markdown", jina_url],
            capture_output=True, text=True, timeout=35,
        )
        if r.returncode == 0 and len(r.stdout.strip()) > 100:
            lines = r.stdout.strip().splitlines()
            title = lines[0].lstrip("#").strip() if lines else url
            return {"title": title, "text": r.stdout.strip()}
    except Exception:
        pass

    return None


# ── 共用滚动脚本 ────────────────────────────────────────────────────────────

_SCROLL_JS = """() => new Promise(resolve => {
    let last = 0;
    const step = () => {
        window.scrollTo(0, document.body.scrollHeight);
        if (document.body.scrollHeight === last) { resolve(); }
        else { last = document.body.scrollHeight; setTimeout(step, 500); }
    };
    step();
})"""


# ── 提取器主类 ──────────────────────────────────────────────────────────────

class ArticleExtractor(BaseExtractor):
    """单篇网络文章提取器。

    路由逻辑：
    - 微信公众号 → camoufox stealth browser
    - 今日头条   → Playwright Chromium
    - 其他网页   → crawl4ai → Jina Reader（降级）
    """

    @property
    def supported_domains(self) -> list[str]:
        return []

    def extract(self, source: str) -> Path:
        output_dir = self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        reg = Registry(output_dir / ".processed.json")

        if not self.config.force and reg.is_processed(source):
            self.log(f"[跳过] 已处理: {source}")
            entry = next(
                (e for e in reg.get_by_status("done") if e["source"] == source),
                None,
            )
            if entry and entry.get("output_file"):
                return output_dir / entry["output_file"]

        platform = _detect_platform(source)
        self.log(f"[Article/{platform}] 抓取: {source}")

        result = self._fetch(source, platform)
        if not result:
            raise RuntimeError(f"抓取失败（platform={platform}）: {source}")

        title = result["title"] or source
        text = result["text"] or ""
        body = self._format_body(title, text)

        slug = re.sub(r'[/\\:*?"<>|]', "-", title[:50]).replace(" ", "_")
        filename = f"article__{_slug_from_url(source)[:30]}__{slug}.md"
        out_path = output_dir / filename

        content_hash = write_frontmatter_file(
            path=out_path,
            content=body,
            source=source,
            type="article",
            platform=platform,
        )
        reg.mark(source, "done", output_file=filename, content_hash=content_hash)
        self.log(f"[Article] {title[:60]} → {filename}")
        return out_path

    def _fetch(self, url: str, platform: str) -> dict | None:
        if platform == "wechat":
            result = _fetch_wechat(url)
            if result:
                return result
            self.log("[警告] camoufox 失败，降级 Jina Reader")
            return _fetch_generic(url)

        if platform == "toutiao":
            result = _fetch_toutiao(url)
            if result:
                return result
            self.log("[警告] Playwright 失败，降级 Jina Reader")
            return _fetch_generic(url)

        return _fetch_generic(url)

    @staticmethod
    def _format_body(title: str, text: str) -> str:
        clean = re.sub(r"\n{3,}", "\n\n", text).strip()
        return f"# {title}\n\n{clean}"
