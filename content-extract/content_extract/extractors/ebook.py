from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from .base import BaseExtractor, ExtractConfig
from ..registry import Registry
from ..utils.frontmatter import write_frontmatter_file


# 文件名中不安全的字符
_UNSAFE = re.compile(r'[/\\:*?"<>|]')


def _safe_slug(text: str, max_len: int = 60) -> str:
    return _UNSAFE.sub("-", text)[:max_len].strip("-")


# ── EPUB 辅助 ─────────────────────────────────────────────────────────────────

def _epub_available() -> None:
    """检查 ebooklib / beautifulsoup4 是否已安装，未安装时给出明确提示。"""
    try:
        import ebooklib  # noqa: F401
        import bs4       # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "EPUB 提取需要额外依赖，请运行：pip install ebooklib beautifulsoup4"
        ) from exc


def _html_to_text(html: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
        level = int(tag.name[1])
        tag.replace_with(f"\n{'#' * level} {tag.get_text()}\n")
    for code in soup.find_all("pre"):
        code.replace_with(f"\n```\n{code.get_text()}\n```\n")
    return soup.get_text(separator="\n")


def _extract_toc(book) -> list[dict]:
    """递归遍历 epub TOC，返回 [{level, title, href}] 列表。"""
    from ebooklib import epub
    items: list[dict] = []

    def walk(nodes, level: int = 1) -> None:
        for node in nodes:
            if isinstance(node, epub.Link):
                items.append({"level": level, "title": node.title or "", "href": node.href or ""})
            elif isinstance(node, tuple):
                section, children = node
                items.append({
                    "level": level,
                    "title": section.title or "",
                    "href": getattr(section, "href", "") or "",
                })
                walk(children, level + 1)

    walk(book.toc)
    return items


def _extract_epub(source: str, output_dir: Path, slug: str, reg: Registry,
                  force: bool, log: Callable[[str], None]) -> Path:
    """提取单个 EPUB 文件，返回 toc 文件路径（如无 TOC 则返回第一章路径）。"""
    from ebooklib import epub, ITEM_DOCUMENT

    _epub_available()
    log(f"[EPUB] 解析: {source}")
    book = epub.read_epub(source, options={"ignore_ncx": False})

    title_meta = book.get_metadata("DC", "title")
    author_meta = book.get_metadata("DC", "creator")
    title = title_meta[0][0] if title_meta else Path(source).stem
    author = author_meta[0][0] if author_meta else ""

    out_dir = output_dir / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. TOC ────────────────────────────────────────────────────────────────
    toc_items = _extract_toc(book)
    toc_file: Path | None = None

    if toc_items:
        toc_lines = [
            f"# {title} — 目录结构\n",
            f"> 作者：{author}\n",
            "用途：先读此文件理解全书论点框架，再按 chapter_title 定向读章节。\n",
        ]
        for item in toc_items:
            indent = "  " * (item["level"] - 1)
            toc_lines.append(f"{indent}- {item['title']}")

        toc_filename = f"epub__{_safe_slug(title)}__toc.md"
        toc_file = out_dir / toc_filename
        toc_source = f"{source}#toc"

        if force or not reg.is_processed(toc_source):
            content_hash = write_frontmatter_file(
                path=toc_file,
                content="\n".join(toc_lines),
                source=toc_source,
                type="ebook",
                platform="epub",
                subtype="toc",
                extra_fields={"title": title, "author": author,
                              "toc_count": str(len(toc_items))},
            )
            reg.mark(toc_source, "done",
                     output_file=f"{slug}/{toc_filename}",
                     content_hash=content_hash)
            log(f"  TOC → {toc_filename}（{len(toc_items)} 条目）")

    # ── 2. 构建 href → 章节标题 映射 ─────────────────────────────────────────
    href_to_title: dict[str, str] = {}
    for item in toc_items:
        href_base = item["href"].split("#")[0]
        if href_base and item["title"]:
            href_to_title[href_base] = item["title"]

    # ── 3. 章节全文 ───────────────────────────────────────────────────────────
    chapters = []
    for doc_item in book.get_items_of_type(ITEM_DOCUMENT):
        text = _html_to_text(doc_item.get_content().decode("utf-8", errors="ignore"))
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if len(text) > 100:
            chapter_title = href_to_title.get(doc_item.file_name, "")
            chapters.append({"text": text, "title": chapter_title})

    first_chapter_file: Path | None = None
    for i, ch in enumerate(chapters, 1):
        ch_slug = _safe_slug(title)
        filename = f"epub__{ch_slug}__ch{i:03d}.md"
        ch_file = out_dir / filename
        ch_source = f"{source}#ch{i:03d}"

        if not force and reg.is_processed(ch_source):
            if first_chapter_file is None:
                first_chapter_file = ch_file
            continue

        body_lines = []
        if ch["title"]:
            body_lines.append(f"# {ch['title']}\n")
        body_lines.append(ch["text"])

        extra: dict[str, str] = {"title": title, "author": author, "chapter": str(i)}
        if ch["title"]:
            extra["chapter_title"] = ch["title"]

        content_hash = write_frontmatter_file(
            path=ch_file,
            content="\n".join(body_lines),
            source=ch_source,
            type="ebook",
            platform="epub",
            extra_fields=extra,
        )
        reg.mark(ch_source, "done",
                 output_file=f"{slug}/{filename}",
                 content_hash=content_hash)

        if first_chapter_file is None:
            first_chapter_file = ch_file

    log(f"[EPUB] {title} — TOC {len(toc_items)} 条，{len(chapters)} 章 → {out_dir.name}/")
    return toc_file or first_chapter_file or out_dir / f"epub__{_safe_slug(title)}__ch001.md"


# ── PDF 辅助 ─────────────────────────────────────────────────────────────────

def _pdf_available() -> None:
    try:
        import pymupdf4llm  # noqa: F401
    except ImportError:
        try:
            import pymupdf    # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "PDF 提取需要额外依赖，请运行：pip install pymupdf4llm\n"
                "（复杂排版可选：pip install marker-pdf）"
            ) from exc


def _pdf_pages(pdf_path: str) -> list[str]:
    """按页提取 PDF 文本，优先 pymupdf4llm，回退 pymupdf 纯文本。"""
    try:
        import pymupdf4llm
        import pymupdf
        doc = pymupdf.open(pdf_path)
        return [
            pymupdf4llm.to_markdown(pdf_path, pages=[i]).strip()
            for i in range(len(doc))
        ]
    except ImportError:
        pass

    try:
        import pymupdf
        doc = pymupdf.open(pdf_path)
        return [page.get_text() for page in doc]
    except ImportError:
        pass

    try:
        from marker.convert import convert_single_pdf
        from marker.models import load_all_models
        full_text, _, _ = convert_single_pdf(pdf_path, load_all_models())
        pages = re.split(r"\f|\n{4,}", full_text)
        return [p.strip() for p in pages if p.strip()]
    except ImportError:
        pass

    raise RuntimeError("请安装 pymupdf4llm：pip install pymupdf4llm")


def _extract_pdf(source: str, output_dir: Path, slug: str, reg: Registry,
                 force: bool, log: Callable[[str], None]) -> Path:
    """提取单个 PDF 文件，每 20 页一个 Markdown 文件，返回第一个文件路径。"""
    _pdf_available()
    log(f"[PDF] 解析: {source}")

    title = Path(source).stem
    out_dir = output_dir / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    pages = _pdf_pages(source)
    chunk_size = 20
    total_parts = (len(pages) + chunk_size - 1) // chunk_size
    first_file: Path | None = None

    for part_idx in range(total_parts):
        part = part_idx + 1
        start = part_idx * chunk_size
        end = min(start + chunk_size, len(pages))
        chunk = pages[start:end]

        filename = f"pdf__{_safe_slug(title)}__part{part:03d}.md"
        out_file = out_dir / filename
        part_source = f"{source}#part{part:03d}"

        if not force and reg.is_processed(part_source):
            if first_file is None:
                first_file = out_file
            continue

        content = "\n\n---\n\n".join(chunk)
        content_hash = write_frontmatter_file(
            path=out_file,
            content=content,
            source=part_source,
            type="ebook",
            platform="pdf",
            extra_fields={
                "title": title,
                "part": str(part),
                "pages": f"{start + 1}-{end}",
            },
        )
        reg.mark(part_source, "done",
                 output_file=f"{slug}/{filename}",
                 content_hash=content_hash)

        if first_file is None:
            first_file = out_file

    log(f"[PDF] {title} — {len(pages)} 页 → {total_parts} 个文件")
    return first_file or out_dir / f"pdf__{_safe_slug(title)}__part001.md"


# ── 主提取器 ──────────────────────────────────────────────────────────────────

class EbookExtractor(BaseExtractor):
    """
    提取本地电子书文件或目录。

    支持格式：
    - EPUB：输出 __toc.md（目录结构）+ __ch001.md 等（各章节，frontmatter 含 chapter_title）
    - PDF： 每 20 页一个 part 文件（pymupdf4llm 优先，回退 pymupdf）
    - MOBI/AZW3：不直接支持，提示用 Calibre 先转换为 EPUB

    source 可以是：
    - 单个文件路径（.epub / .pdf）
    - 目录路径（批量处理目录下所有 epub/pdf）
    """

    @property
    def supported_domains(self) -> list[str]:
        return []

    def extract(self, source: str) -> Path:
        src = Path(source).expanduser().resolve()
        if not src.exists():
            raise ValueError(f"路径不存在: {src}")

        output_dir = self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        reg = Registry(output_dir / ".processed.json")

        if src.is_dir():
            return self._extract_dir(src, output_dir, reg)
        return self._extract_file(src, output_dir, reg)

    def _extract_file(self, src: Path, output_dir: Path, reg: Registry) -> Path:
        suffix = src.suffix.lower()
        slug = _safe_slug(src.stem)

        if suffix == ".epub":
            return _extract_epub(str(src), output_dir, slug, reg,
                                 self.config.force, self.log)
        if suffix == ".pdf":
            return _extract_pdf(str(src), output_dir, slug, reg,
                                self.config.force, self.log)
        if suffix in {".mobi", ".azw3", ".azw"}:
            raise RuntimeError(
                f"不支持直接处理 {suffix} 格式。\n"
                "请先用 Calibre 转换为 EPUB：\n"
                f"  ebook-convert \"{src}\" \"{src.with_suffix('.epub')}\"\n"
                "然后再提取转换后的 .epub 文件。"
            )
        raise ValueError(f"不支持的文件格式: {suffix}（支持 .epub / .pdf）")

    def _extract_dir(self, src: Path, output_dir: Path, reg: Registry) -> Path:
        ebooks = sorted(
            [f for f in src.rglob("*") if f.suffix.lower() in {".epub", ".pdf"}]
        )
        if not ebooks:
            raise ValueError(f"目录 {src} 下未找到 epub / pdf 文件")

        self.log(f"[Ebook] 批量处理 {len(ebooks)} 个文件")
        first: Path | None = None
        for f in ebooks:
            try:
                result = self._extract_file(f, output_dir, reg)
                if first is None:
                    first = result
            except Exception as e:
                self.log(f"  [跳过] {f.name}：{e}")

        return first or output_dir
