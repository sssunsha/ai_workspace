# Content Extraction — 内容提取与知识内化操作手册

> 创建日期：2026-06-01 | 持续更新中
>
> **适用场景**：将任意来源的内容（网页、视频、电子书、本地代码、本地文档、GitHub 仓库、单篇网络文章）转化为结构化知识库，支持 LLM 持续查询。

---

## 整体架构：所有内容源共用一条管道

```
Layer 1: 提取层（content-extract CLI）
┌──────────────────────────────────────────────────────────────────────────┐
│                             内容源（Part 1）                               │
│  技术博客  视频网站  电子书  本地代码  本地文档  GitHub仓库  单篇文章       │
│     ↓         ↓       ↓       ↓        ↓          ↓          ↓          │
│  爬取/抓取 字幕/转录 解析  AST分析  读取/解析  gh CLI  Jina/Playwright    │
└───────────────────────────────┬──────────────────────────────────────────┘
                                ↓  ./raw/*.md
Layer 2: 编排层（Claude Code Skill + LLM）
┌───────────────────────────────┴──────────────────────────────────────────┐
│                       通用分析整理与检索（Part 2）                          │
│    LLM Wiki 构建 → ./wiki/  →  查询（Claude Code / RAG）                  │
└───────────────────────────────┬──────────────────────────────────────────┘
                                ↓  ./wiki/*.md
Layer 3: 消费层（Obsidian）
┌───────────────────────────────┴──────────────────────────────────────────┐
│                          Obsidian（人类消费层）                             │
│                    Graph View · Dataview · 移动端阅读                      │
└──────────────────────────────────────────────────────────────────────────┘
```

**核心设计原则**：
- 所有来源最终都输出到 `./raw/*.md`，格式一致
- Part 2 的分析整理流程对所有来源通用，不需要为每种来源重复
- 每种来源只有 Phase 1（获取文本化内容）是独特的

---

# Part 1：内容源获取工作流

---

## 1.1 技术博客 / 文档网站

**适用**：技术博客、官方文档、ReadTheDocs、GitHub Pages、个人站点

**核心挑战**：反爬、动态渲染（JS SPA）、登录墙

### 工具选型

| 工具 | 安装 | 适用场景 |
|------|------|---------|
| crawl4ai | `pip install crawl4ai` | 推荐，支持 JS 渲染，输出干净 Markdown |
| Jina Reader API | 无需安装，直接 curl | 快速处理少量 URL，免注册 |
| Firecrawl CLI | `npm install -g firecrawl-cli` | 商业工具，整站爬取最简单，有免费配额 |
| wget + pandoc | 系统自带 + `brew install pandoc` | 离线存档，最稳定 |

### 整站爬取脚本 `crawl_site.py`

> **增量说明**：脚本用 `./raw/.processed_urls.txt` 记录已处理的 URL，重复运行时自动跳过，不会覆盖已有文件。

```python
import asyncio
import os
from urllib.parse import urljoin, urlparse
from crawl4ai import AsyncWebCrawler

SITE_URL = "https://example-blog.com"
OUTPUT_DIR = "./raw"
MAX_PAGES = 200
PROCESSED_LOG = os.path.join(OUTPUT_DIR, ".processed_urls.txt")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 加载已处理 URL（支持增量运行）
visited: set[str] = set()
if os.path.exists(PROCESSED_LOG):
    with open(PROCESSED_LOG) as f:
        visited.update(l.strip() for l in f if l.strip())

def url_to_filename(url: str) -> str:
    path = urlparse(url).path.strip("/").replace("/", "__") or "index"
    return f"web__{path}.md"

async def crawl_page(crawler, url: str, depth: int = 0):
    if url in visited or depth > 3 or len(visited) >= MAX_PAGES:
        return
    if urlparse(url).netloc != urlparse(SITE_URL).netloc:
        return
    visited.add(url)

    result = await crawler.arun(url=url)
    if not result.success:
        return

    filename = url_to_filename(url)
    with open(os.path.join(OUTPUT_DIR, filename), "w") as f:
        f.write(f"---\nsource: {url}\ntype: web\n---\n\n")
        f.write(result.markdown or "")

    # 记录已处理（追加写入）
    with open(PROCESSED_LOG, "a") as f:
        f.write(url + "\n")

    print(f"[{len(visited)}] {url}")

    for link in (result.links.get("internal") or []):
        full_url = urljoin(SITE_URL, link.get("href", ""))
        await crawl_page(crawler, full_url, depth + 1)

async def main():
    async with AsyncWebCrawler(verbose=False) as crawler:
        await crawl_page(crawler, SITE_URL)
    print(f"完成，{len(visited)} 页 → {OUTPUT_DIR}/")

asyncio.run(main())
```

**动态 JS 渲染（SPA）处理：**

```python
result = await crawler.arun(
    url=url,
    js_code="window.scrollTo(0, document.body.scrollHeight);",
    wait_for="css:.content-loaded",
    delay_before_return_html=2.0,
)
```

**Jina Reader 快速单页方案（无需安装）：**

```bash
curl https://r.jina.ai/https://example.com/article > ./raw/web__article.md

# 批量
while read url; do
    fname=$(echo "$url" | sed 's|https://||;s|/|__|g').md
    curl -s "https://r.jina.ai/$url" > "./raw/web__$fname"
done < urls.txt
```

**登录墙处理（Playwright）：**

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://example.com/login")
    page.fill("#username", "your_email")
    page.fill("#password", "your_password")
    page.click("#submit")
    page.wait_for_load_state("networkidle")
    # 登录后用 crawl4ai 携带 cookies 继续爬取
    cookies = page.context.cookies()
    browser.close()
```

---

## 1.2 视频网站

**适用**：Bilibili、抖音、Vimeo、Coursera、本地视频文件、播客

> **注意**：YouTube 在中国大陆网络环境下不可访问，本文档不再收录 YouTube 相关脚本。如有 VPN 环境可自行适配 Bilibili 脚本，原理相同。

**核心挑战**：文字化（字幕提取 or 音频转录）是唯一额外步骤，之后和博客完全一样。

**字幕优先级**：手动字幕 > 平台 AI 自动字幕 > Whisper 本地转录 > Whisper API

### 工具安装

```bash
pip install yt-dlp faster-whisper
brew install ffmpeg
```

---

### Bilibili

**关键**：B站的 AI 语音识别字幕（大多数视频）需要登录才能访问；UP 主手动上传的 CC 字幕不需要登录也可以拿到。实际操作中统一带 Cookie 处理即可，不影响 CC 字幕的获取。

```bash
# 导出 Cookie（Chrome 安装 "Get cookies.txt LOCALLY" 插件 → 访问 bilibili.com → 导出）
# 或直接从浏览器提取：
yt-dlp --cookies-from-browser chrome --skip-download -J "https://www.bilibili.com/video/BVxxx"
```

```python
# fetch_bilibili.py
import json, os, re, subprocess
from pathlib import Path

OUTPUT_DIR = "./raw"
COOKIES = "./bilibili_cookies.txt"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def ytdlp_json(url: str) -> dict:
    r = subprocess.run(
        ["yt-dlp", "--cookies", COOKIES, "--skip-download", "-J", url],
        capture_output=True, text=True
    )
    return json.loads(r.stdout)


def get_subtitle(url: str, video_id: str) -> str | None:
    tmp = f"/tmp/bili_{video_id}"
    os.makedirs(tmp, exist_ok=True)
    subprocess.run([
        "yt-dlp", "--cookies", COOKIES, "--skip-download",
        "--write-auto-sub", "--write-sub",
        "--sub-lang", "zh-Hans,zh",
        "--convert-subs", "srt",
        "-o", os.path.join(tmp, "%(id)s"), url
    ], capture_output=True)

    srt_files = list(Path(tmp).glob("*.srt"))
    if not srt_files:
        shutil.rmtree(tmp, ignore_errors=True)
        return None

    # 解析 SRT，去除 B站重复行
    blocks = re.split(r"\n{2,}", srt_files[0].read_text(encoding="utf-8").strip())
    texts, deduped = [], []
    for block in blocks:
        parts = block.strip().split("\n")
        if len(parts) < 3: continue
        ts = parts[1].split(" --> ")[0]
        h, m, s = ts.replace(",", ".").split(":")
        sec = int(h)*3600 + int(m)*60 + float(s)
        mm, ss = divmod(int(sec), 60)
        text = re.sub(r"<[^>]+>", "", " ".join(parts[2:]))
        texts.append((f"[{mm:02d}:{ss:02d}]", text))

    # 去相邻重复（B站特有问题）
    for ts, text in texts:
        if not deduped or text != deduped[-1][1]:
            if deduped and text.startswith(deduped[-1][1]):
                deduped[-1] = (ts, text)
            else:
                deduped.append((ts, text))

    shutil.rmtree(tmp, ignore_errors=True)
    return "\n".join(f"{ts} {text}" for ts, text in deduped)


def fetch_bilibili_video(url: str):
    meta = ytdlp_json(url)
    vid = meta.get("id", "unknown")
    title = meta.get("title", vid)
    duration = meta.get("duration") or 0
    chapters = meta.get("chapters") or []

    transcript = get_subtitle(url, vid)

    out = [
        f"---\nsource: {url}\ntype: video\nplatform: bilibili\n---\n",
        f"# {title}\n",
        f"- **UP主**: {meta.get('uploader', '')}",
        f"- **时长**: {duration // 60}:{duration % 60:02d}",
    ]
    if chapters:
        out.append("\n## 章节结构")
        for ch in chapters:
            ts = int(ch.get("start_time", 0)); m, s = divmod(ts, 60)
            out.append(f"- [{m:02d}:{s:02d}] {ch['title']}")

    out.append("\n## 字幕全文")
    if transcript:
        out.append(transcript)
    else:
        out.append("*无字幕，待 Whisper 转录*")
        with open(os.path.join(OUTPUT_DIR, "needs_transcription.txt"), "a") as f:
            f.write(f"{url}\n")

    slug = title[:40].replace("/", "-").replace(" ", "_")
    with open(os.path.join(OUTPUT_DIR, f"bili__{vid}__{slug}.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"[Bilibili] {title}")


def fetch_bilibili_space(uid: str, max_videos: int = 50):
    r = subprocess.run([
        "yt-dlp", "--cookies", COOKIES, "--flat-playlist",
        "--playlist-end", str(max_videos), "-J",
        f"https://space.bilibili.com/{uid}/video"
    ], capture_output=True, text=True)
    for e in json.loads(r.stdout).get("entries", []):
        fetch_bilibili_video(e.get("url") or f"https://www.bilibili.com/video/{e['id']}")
```

---

### 抖音

**关键**：几乎没有字幕，Whisper 转录是主路径；反爬强，必须限速。

```python
# fetch_douyin.py
import json, os, re, shutil, subprocess, time, random
from pathlib import Path
from faster_whisper import WhisperModel

OUTPUT_DIR = "./raw"
COOKIES = "./douyin_cookies.txt"
os.makedirs(OUTPUT_DIR, exist_ok=True)

_model = None
def whisper_model():
    global _model
    if _model is None:
        _model = WhisperModel("large-v3", device="cpu", compute_type="int8")
    return _model


def fetch_douyin_video(url: str):
    r = subprocess.run(
        ["yt-dlp", "--cookies", COOKIES, "--skip-download", "-J", url],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"  [跳过] 元数据获取失败: {url}")
        return
    meta = json.loads(r.stdout)
    vid = meta.get("id", "unknown")
    title = (meta.get("title") or meta.get("description") or "无标题")[:60]
    duration = meta.get("duration") or 0

    # 时长过滤：跳过不足 60 秒的短视频
    if duration < 60:
        print(f"  [跳过] 时长 {duration}s < 60s: {title}")
        return

    slug = re.sub(r'[/\\:*?"<>|]', "-", title).replace(" ", "_")
    fname = f"dy__{vid}__{slug}.md"
    out_path = os.path.join(OUTPUT_DIR, fname)
    if os.path.exists(out_path):
        print(f"  [跳过] 已存在: {fname}")
        return

    # 先尝试获取字幕
    transcript, source = None, "Whisper"
    tmp = f"/tmp/dy_{vid}"
    os.makedirs(tmp, exist_ok=True)
    subprocess.run([
        "yt-dlp", "--cookies", COOKIES, "--skip-download",
        "--write-auto-sub", "--sub-lang", "zh,zh-Hans",
        "--convert-subs", "srt",
        "-o", os.path.join(tmp, "%(id)s"), url
    ], capture_output=True)
    srt_files = list(Path(tmp).glob("*.srt"))
    if srt_files:
        transcript = srt_files[0].read_text(encoding="utf-8")
        source = "平台字幕"
    shutil.rmtree(tmp, ignore_errors=True)

    # 无字幕则下载音频转录
    if not transcript:
        audio = f"/tmp/dy_{vid}.mp3"
        r2 = subprocess.run([
            "yt-dlp", "--cookies", COOKIES, "-x",
            "--audio-format", "mp3", "--audio-quality", "5",
            "-o", audio, url
        ], capture_output=True)
        if r2.returncode == 0 and os.path.exists(audio):
            model = whisper_model()
            segs, info = model.transcribe(
                audio, language="zh", vad_filter=True,
                no_speech_threshold=0.6,
                condition_on_previous_text=False,
            )
            lines = []
            for seg in segs:
                if seg.no_speech_prob < 0.5 and seg.text.strip():
                    m, s = divmod(int(seg.start), 60)
                    lines.append(f"[{m:02d}:{s:02d}] {seg.text.strip()}")
            transcript = "\n".join(lines) if lines else "*无有效语音内容*"
            os.remove(audio)

    out = [
        f"---\nsource: {url}\ntype: video\nplatform: douyin\n---\n",
        f"# {title}\n",
        f"- **时长**: {duration // 60}:{duration % 60:02d}",
        f"- **字幕来源**: {source}",
        "\n## 转录文本",
        transcript or "*转录失败*",
    ]
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"[抖音] {title} ({source})")

    # 随机延迟防封
    time.sleep(random.uniform(5, 12))


def fetch_douyin_user(user_url: str, max_videos: int = 50):
    """
    max_videos: 单次拉取上限。抖音账号可能有数百个视频，
    建议分批处理（每批 50），避免长时间运行触发风控。
    """
    r = subprocess.run([
        "yt-dlp", "--cookies", COOKIES, "--flat-playlist",
        "--playlist-end", str(max_videos), "--sleep-interval", "3", "-J", user_url
    ], capture_output=True, text=True)
    for e in json.loads(r.stdout).get("entries", []):
        fetch_douyin_video(e.get("url") or f"https://www.douyin.com/video/{e['id']}")
```

---

### Whisper 转录（通用兜底，处理 `needs_transcription.txt`）

```python
# transcribe_queue.py — 处理所有需要转录的视频
import os, re, subprocess
from pathlib import Path
from faster_whisper import WhisperModel

NEEDS_FILE = "./raw/needs_transcription.txt"
OUTPUT_DIR = "./raw"
# 中文内容推荐 medium；追求质量/有 GPU 用 large-v3
# M 系 Mac: device="mps", compute_type="float16"
model = WhisperModel("medium", device="cpu", compute_type="int8")

if not os.path.exists(NEEDS_FILE):
    print("无待处理视频")
    exit()

with open(NEEDS_FILE) as f:
    urls = [l.strip() for l in f if l.strip()]

for url in urls:
    # 用 yt-dlp 直接获取视频 ID，避免手工解析不同平台的 URL 格式
    r_meta = subprocess.run(
        ["yt-dlp", "--skip-download", "--print", "id", url],
        capture_output=True, text=True
    )
    if r_meta.returncode != 0:
        print(f"  [失败] 无法获取 ID: {url}")
        continue
    vid = r_meta.stdout.strip()
    audio = f"/tmp/transcribe_{vid}.mp3"
    print(f"转录: {url} (id={vid})")

    r = subprocess.run([
        "yt-dlp", "-x", "--audio-format", "mp3",
        "--audio-quality", "5", "-o", audio, url
    ], capture_output=True)
    if r.returncode != 0 or not os.path.exists(audio):
        print(f"  [失败] 音频下载")
        continue

    segs, info = model.transcribe(audio, language="zh", vad_filter=True)
    lines = []
    for seg in segs:
        m, s = divmod(int(seg.start), 60)
        lines.append(f"[{m:02d}:{s:02d}] {seg.text.strip()}")
    transcript = "\n".join(lines)
    os.remove(audio)

    # 追加到已有的 raw 文件
    for fname in os.listdir(OUTPUT_DIR):
        if vid in fname and fname.endswith(".md"):
            fpath = os.path.join(OUTPUT_DIR, fname)
            content = open(fpath).read()
            content = content.replace("*无字幕，待 Whisper 转录*", transcript)
            open(fpath, "w").write(content)
            print(f"  → 已更新 {fname}")
            break

# 清空队列
open(NEEDS_FILE, "w").close()
```

**Whisper 模型选型速查：**

| 模型 | 磁盘 | CPU 速度 | 中文准确率 | 推荐场景 |
|------|------|---------|-----------|---------|
| small | 465MB | 中 | 较好 | 快速批量处理 |
| medium | 1.5GB | 慢 | 好 | 常规推荐 |
| large-v3 | 3.1GB | 很慢 | 最好 | 抖音、质量要求高 |

> M 系 Mac 加速：`WhisperModel("large-v3", device="mps", compute_type="float16")` 速度提升 3-5x

---

## 1.3 电子书

**适用**：EPUB、PDF、MOBI/AZW3 本地电子书

**格式覆盖说明**：
- **EPUB**：完整支持，结构最整齐，推荐优先使用
- **PDF**：完整支持（文字型 + 扫描版），见下方脚本
- **MOBI / AZW3**：不直接支持，需先用 [Calibre](https://calibre-ebook.com) 转换为 EPUB 再处理：`ebook-convert input.mobi output.epub`

**核心挑战**：PDF 格式混乱（扫描版、公式、表格）；EPUB 结构整齐，优先处理

---

### EPUB（推荐，结构最整齐）

> **设计原则**：EPUB 提取时额外输出两个文件：`__toc.md`（目录/论点结构）和各章节的 `__ch001.md`（章节标题写入 frontmatter）。分析时先读 TOC，再按需定向读章节，避免全书一次塞进上下文。

```bash
pip install ebooklib beautifulsoup4
```

```python
# extract_epub.py
import os, re
from pathlib import Path
from ebooklib import epub, ITEM_DOCUMENT, ITEM_NAVIGATION
from bs4 import BeautifulSoup

OUTPUT_DIR = "./raw"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    # 保留标题层级
    for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
        level = int(tag.name[1])
        tag.replace_with(f"\n{'#' * level} {tag.get_text()}\n")
    # 保留代码块
    for code in soup.find_all("pre"):
        code.replace_with(f"\n```\n{code.get_text()}\n```\n")
    return soup.get_text(separator="\n")


def extract_toc(book: epub.EpubBook) -> list[dict]:
    """提取目录结构，返回 [{order, title, href, level}] 列表。"""
    toc_items = []

    def walk(items, level=1):
        for item in items:
            if isinstance(item, epub.Link):
                toc_items.append({"level": level, "title": item.title, "href": item.href})
            elif isinstance(item, tuple):
                section, children = item
                toc_items.append({"level": level, "title": section.title, "href": getattr(section, "href", "")})
                walk(children, level + 1)

    walk(book.toc)
    return toc_items


def extract_epub(epub_path: str):
    book = epub.read_epub(epub_path)
    title = book.get_metadata("DC", "title")[0][0] if book.get_metadata("DC", "title") else Path(epub_path).stem
    author = book.get_metadata("DC", "creator")[0][0] if book.get_metadata("DC", "creator") else ""
    slug = re.sub(r'[/\\:*?"<>|]', "-", title)

    # ── 1. 提取并输出 TOC（论点结构）────────────────────────────────────
    toc_items = extract_toc(book)
    if toc_items:
        toc_lines = [
            f"---\nsource: {epub_path}\ntype: ebook\nformat: epub\nsubtype: toc\n",
            f"title: {title}\nauthor: {author}\n---\n\n",
            f"# {title} — 目录结构\n\n",
            f"> 作者：{author}\n\n",
            "用途：分析时先读此文件，理解全书论点结构，再按需定向读具体章节。\n\n",
        ]
        for item in toc_items:
            indent = "  " * (item["level"] - 1)
            toc_lines.append(f"{indent}- {item['title']}")
        toc_fname = f"epub__{slug}__toc.md"
        with open(os.path.join(OUTPUT_DIR, toc_fname), "w", encoding="utf-8") as f:
            f.write("\n".join(toc_lines))
        print(f"  TOC: {toc_fname}（{len(toc_items)} 条目）")

    # ── 2. 构建 href → TOC标题 映射（用于章节标题 frontmatter）──────────
    href_to_title: dict[str, str] = {}
    for item in toc_items:
        href_base = item["href"].split("#")[0]  # 去掉锚点
        if href_base and item["title"]:
            href_to_title[href_base] = item["title"]

    # ── 3. 提取章节内容────────────────────────────────────────────────
    chapters = []
    for item in book.get_items_of_type(ITEM_DOCUMENT):
        text = html_to_text(item.get_content().decode("utf-8", errors="ignore"))
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if len(text) > 100:
            chapter_title = href_to_title.get(item.file_name, "")
            chapters.append({"text": text, "title": chapter_title, "href": item.file_name})

    for i, ch in enumerate(chapters, 1):
        fname = f"epub__{slug}__ch{i:03d}.md"
        with open(os.path.join(OUTPUT_DIR, fname), "w", encoding="utf-8") as f:
            f.write(f"---\nsource: {epub_path}\ntype: ebook\nformat: epub\n")
            f.write(f"title: {title}\nauthor: {author}\nchapter: {i}\n")
            if ch["title"]:
                f.write(f"chapter_title: \"{ch['title']}\"\n")  # 关键：章节标题进 frontmatter
            f.write("---\n\n")
            if ch["title"]:
                f.write(f"# {ch['title']}\n\n")
            f.write(ch["text"])
        print(f"  章节 {i:03d}: {ch['title'] or '(无标题)'} → {fname}")

    print(f"[EPUB] {title}，TOC {len(toc_items)} 条目，{len(chapters)} 章")


# 批量处理目录下所有 epub
for f in Path("./ebooks").glob("*.epub"):
    extract_epub(str(f))
```

---

**输出文件命名规则**：
- `epub__书名__toc.md`：目录结构（先读，理解全书框架）
- `epub__书名__ch001.md` ~ `ch0XX.md`：各章节全文（按需读，frontmatter 含 `chapter_title`）

---

### PDF

PDF 分两种情况，处理方式不同：

```bash
pip install pymupdf4llm   # 文字型 PDF（最优先）
pip install marker-pdf    # 复杂排版 PDF（学术论文、教材）
# 扫描版 PDF 需要 OCR，见下方
```

```python
# extract_pdf.py
import os, re
from pathlib import Path

OUTPUT_DIR = "./raw"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def extract_pdf_text_by_page(pdf_path: str) -> list[str]:
    """返回每页文本的列表，优先 pymupdf4llm，回退 marker-pdf。"""
    # 方案1：pymupdf4llm — 直接按页提取，不依赖任何页标记
    try:
        import pymupdf4llm, pymupdf
        doc = pymupdf.open(pdf_path)
        # to_markdown 支持 pages 参数逐页提取
        return [
            pymupdf4llm.to_markdown(pdf_path, pages=[i]).strip()
            for i in range(len(doc))
        ]
    except ImportError:
        pass

    # 方案2：marker-pdf — 整体转换后按换页符切分
    try:
        from marker.convert import convert_single_pdf
        from marker.models import load_all_models
        models = load_all_models()
        full_text, _, _ = convert_single_pdf(pdf_path, models)
        # marker 输出用 \f（换页符）或连续空行分页
        pages = re.split(r"\f|\n{4,}", full_text)
        return [p.strip() for p in pages if p.strip()]
    except ImportError:
        pass

    raise RuntimeError("请安装 pymupdf4llm 或 marker-pdf")


def extract_pdf(pdf_path: str):
    p = Path(pdf_path)
    title = p.stem
    pages = extract_pdf_text_by_page(pdf_path)

    # 每 20 页一个文件
    chunk_size = 20
    for i in range(0, len(pages), chunk_size):
        chunk = pages[i:i + chunk_size]
        part = i // chunk_size + 1
        fname = f"pdf__{title}__part{part:03d}.md"
        with open(os.path.join(OUTPUT_DIR, fname), "w", encoding="utf-8") as f:
            f.write(f"---\nsource: {pdf_path}\ntype: ebook\nformat: pdf\n")
            f.write(f"title: {title}\npart: {part}\npages: {i+1}-{min(i+chunk_size, len(pages))}\n---\n\n")
            f.write("\n\n---\n\n".join(chunk))
        print(f"  Part {part}: {fname}")

    print(f"[PDF] {title}，{len(pages)} 页 → {(len(pages) + chunk_size - 1) // chunk_size} 个文件")


for f in Path("./ebooks").glob("*.pdf"):
    extract_pdf(str(f))
```

**扫描版 PDF（图片型）处理：**

```bash
# 方案1：使用 Tesseract OCR（免费）
brew install tesseract tesseract-lang
pip install pytesseract pdf2image

python -c "
import pytesseract
from pdf2image import convert_from_path
pages = convert_from_path('scanned.pdf', dpi=300)
texts = [pytesseract.image_to_string(p, lang='chi_sim+eng') for p in pages]
open('./raw/pdf__scanned.md', 'w').write('\n\n'.join(texts))
"

# 方案2：使用 Mathpix（付费，对公式、图表支持最好）
# 适合技术教材、学术论文
```

---

## 1.4 本地代码工程

**适用**：开源项目、自己的工程代码、第三方 SDK 源码

**核心挑战**：代码量大、需要理解架构而非逐行阅读、注释和文档散落各处

**策略**：不是"读所有代码"，而是提取**高价值信息层**——架构、接口、注释、测试、变更历史。

---

### Phase 1A：项目全局信息提取

```bash
# project_overview.sh — 生成项目全局概览
PROJECT_DIR="./my-project"
OUTPUT="./raw/code__overview.md"

echo "---" > $OUTPUT
echo "source: $PROJECT_DIR" >> $OUTPUT
echo "type: code" >> $OUTPUT
echo "---" >> $OUTPUT
echo "" >> $OUTPUT
echo "# 项目概览: $(basename $PROJECT_DIR)" >> $OUTPUT

# 目录结构（排除 node_modules / .git / build）
echo "## 目录结构" >> $OUTPUT
find $PROJECT_DIR -type f \
    -not -path "*/node_modules/*" \
    -not -path "*/.git/*" \
    -not -path "*/dist/*" \
    -not -path "*/build/*" \
    -not -path "*/__pycache__/*" \
    | sort | sed "s|$PROJECT_DIR/||" >> $OUTPUT

# package.json / pyproject.toml / Cargo.toml 等项目配置
echo "" >> $OUTPUT
echo "## 项目配置文件" >> $OUTPUT
for config in package.json pyproject.toml Cargo.toml go.mod pom.xml setup.py; do
    if [ -f "$PROJECT_DIR/$config" ]; then
        echo "### $config" >> $OUTPUT
        cat "$PROJECT_DIR/$config" >> $OUTPUT
    fi
done

# README
echo "" >> $OUTPUT
echo "## README" >> $OUTPUT
cat "$PROJECT_DIR/README.md" 2>/dev/null \
    || cat "$PROJECT_DIR/README.rst" 2>/dev/null \
    || echo "*无 README*" >> $OUTPUT

# 最近 Git 提交记录（了解变更历史）
echo "" >> $OUTPUT
echo "## 最近 30 条提交" >> $OUTPUT
git -C $PROJECT_DIR log --oneline -30 >> $OUTPUT 2>/dev/null

# Git 热力图：哪些文件被反复修改（复杂度热点）
echo "" >> $OUTPUT
echo "## 高频变更文件（最近 6 个月 commit 次数 Top 20）" >> $OUTPUT
git -C $PROJECT_DIR log --since="6 months ago" --name-only --format="" 2>/dev/null \
    | grep -v '^$' \
    | sort | uniq -c | sort -rn | head -20 >> $OUTPUT

echo "概览已生成: $OUTPUT"
```

---

### Phase 1C：关键文件变更历史提取（深度理解用）

Git log 的信息密度被严重低估。「最近 30 条提交」只是入门。对陌生工程，某个关键文件的**完整变更历史**是最好的设计决策文档——你能看到它经历了什么取舍、哪些代码被反复修改（说明这里是复杂区域）、哪些功能是后来加进去的。

```bash
# git_file_history.sh — 提取关键文件的完整变更历史
PROJECT_DIR="./my-project"
OUTPUT="./raw/code__git_history.md"

echo "---" > $OUTPUT
echo "source: $PROJECT_DIR (git history)" >> $OUTPUT
echo "type: code" >> $OUTPUT
echo "subtype: git_history" >> $OUTPUT
echo "---" >> $OUTPUT
echo "" >> $OUTPUT
echo "# Git 变更历史 — 关键文件" >> $OUTPUT

# 从热力图中取 Top 5 最频繁修改的文件
HOT_FILES=$(git -C $PROJECT_DIR log --since="6 months ago" --name-only --format="" \
    | grep -v '^$' | sort | uniq -c | sort -rn | head -5 | awk '{print $2}')

for FILE in $HOT_FILES; do
    echo "" >> $OUTPUT
    echo "## $FILE" >> $OUTPUT
    echo "" >> $OUTPUT

    # 该文件的完整提交历史（提交信息 + 作者 + 日期）
    echo "### 提交历史（最近 20 次）" >> $OUTPUT
    git -C $PROJECT_DIR log --follow --oneline -20 -- "$FILE" >> $OUTPUT 2>/dev/null

    # 最近一次重大变更的 diff（了解当前状态从何而来）
    LAST_COMMIT=$(git -C $PROJECT_DIR log --follow -1 --format="%H" -- "$FILE" 2>/dev/null)
    if [ -n "$LAST_COMMIT" ]; then
        echo "" >> $OUTPUT
        echo "### 最近一次变更 diff（$LAST_COMMIT）" >> $OUTPUT
        echo '```diff' >> $OUTPUT
        git -C $PROJECT_DIR show --stat "$LAST_COMMIT" -- "$FILE" | head -30 >> $OUTPUT 2>/dev/null
        echo '```' >> $OUTPUT
    fi
done

echo "Git 历史已生成: $OUTPUT"
```

**何时用这个**：
- 看到热力图里某个文件被改了 30+ 次，想知道为什么
- 想了解某个核心文件的「设计演进」而不只是「当前状态」
- 发现代码里有奇怪的写法，想追溯是什么事情导致了这个决策

```python
# extract_code.py — 提取代码工程的高价值信息层
import os, ast, re
from pathlib import Path

PROJECT_DIR = "./my-project"
OUTPUT_DIR = "./raw"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 配置：关注哪些层
INCLUDE_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".go", ".rs", ".java"}
EXCLUDE_DIRS = {"node_modules", ".git", "dist", "build", "__pycache__", ".venv", "vendor"}
MAX_FILE_SIZE_KB = 50   # 跳过超大文件（通常是生成的代码）


def extract_python_signatures(source: str) -> str:
    """提取 Python 文件的所有函数/类签名 + docstring，按源码行号顺序输出。"""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source[:500]

    lines = []
    # 直接遍历模块顶层节点（保证行号顺序），递归处理类内方法
    def visit(nodes):
        for node in nodes:
            if isinstance(node, ast.ClassDef):
                bases = [b.id for b in node.bases if hasattr(b, "id")]
                lines.append(f"\nclass {node.name}({', '.join(bases)}):")
                docstring = ast.get_docstring(node) or ""
                if docstring:
                    lines.append(f'    """{docstring[:200]}"""')
                visit(node.body)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
                docstring = ast.get_docstring(node) or ""
                args = [a.arg for a in node.args.args]
                lines.append(f"{prefix} {node.name}({', '.join(args)}):")
                if docstring:
                    lines.append(f'    """{docstring[:200]}"""')

    visit(tree.body)
    return "\n".join(lines)


def extract_comments(source: str) -> list[str]:
    """提取所有注释（通常是重要的 WHY）"""
    return [line.strip() for line in source.split("\n")
            if line.strip().startswith("#") and len(line.strip()) > 5]


def process_file(fpath: Path, project_root: Path) -> str:
    rel_path = fpath.relative_to(project_root)
    source = fpath.read_text(encoding="utf-8", errors="ignore")

    lines = [f"## {rel_path}\n"]

    if fpath.suffix == ".py":
        signatures = extract_python_signatures(source)
        if signatures:
            lines.append("```python")
            lines.append(signatures)
            lines.append("```")
        comments = extract_comments(source)
        if comments:
            lines.append("\n**关键注释：**")
            for c in comments[:10]:
                lines.append(f"- {c}")
    else:
        # 非 Python 文件：直接取前 100 行
        preview = "\n".join(source.splitlines()[:100])
        lines.append(f"```{fpath.suffix.lstrip('.')}")
        lines.append(preview)
        lines.append("```")

    return "\n".join(lines)


# 按目录分组，每个顶层子目录一个输出文件
root = Path(PROJECT_DIR)
groups: dict[str, list[str]] = {}

for fpath in sorted(root.rglob("*")):
    if not fpath.is_file(): continue
    if fpath.suffix not in INCLUDE_EXTENSIONS: continue
    if any(ex in fpath.parts for ex in EXCLUDE_DIRS): continue
    if fpath.stat().st_size > MAX_FILE_SIZE_KB * 1024: continue

    # 按顶层目录分组
    try:
        group = fpath.relative_to(root).parts[0]
    except IndexError:
        group = "root"

    if group not in groups:
        groups[group] = []
    groups[group].append(process_file(fpath, root))

for group, contents in groups.items():
    fname = f"code__{group}.md"
    with open(os.path.join(OUTPUT_DIR, fname), "w", encoding="utf-8") as f:
        f.write(f"---\nsource: {PROJECT_DIR}/{group}\ntype: code\n---\n\n")
        f.write(f"# 代码模块: {group}\n\n")
        f.write("\n\n".join(contents))
    print(f"[代码] {group} → {fname}")
```

**重点内容优先策略（代码量大时）：**

```bash
# 只提取接口定义和测试文件（最高信息密度）
# 接口/类型定义
find ./my-project -name "*.ts" | xargs grep -l "interface\|type\|export" \
    | head -30 > priority_files.txt

# 测试文件（反映真实用法）
find ./my-project -name "*.test.*" -o -name "*.spec.*" \
    | head -20 >> priority_files.txt

# 入口文件
find ./my-project -name "index.*" -o -name "main.*" \
    | head -10 >> priority_files.txt
```

---

### TypeScript / Angular 专项提取

对于 TypeScript 项目（尤其是 Angular），前 100 行截取的信息密度远不如专门提取接口、类型和组件元数据。

```python
# extract_typescript.py — 提取 TypeScript/Angular 高价值信息层
import os, re
from pathlib import Path

PROJECT_DIR = "./my-project"
OUTPUT_DIR = "./raw"
EXCLUDE_DIRS = {"node_modules", ".git", "dist", "build", ".angular"}
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 正则：提取 interface / type alias / enum / @Component / @Injectable 等
INTERFACE_RE = re.compile(
    r"(?:export\s+)?(?:interface|type|enum)\s+(\w+)[^{;]*\{[^}]*\}",
    re.DOTALL
)
DECORATOR_RE = re.compile(
    r"@(Component|Injectable|NgModule|Directive|Pipe)\s*\([^)]*\)",
    re.DOTALL
)
CLASS_RE = re.compile(
    r"(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:<[^>]*>)?(?:\s+implements\s+[\w,\s<>]+)?(?:\s+extends\s+[\w<>]+)?\s*\{"
)
METHOD_RE = re.compile(
    r"(?:public|private|protected|readonly|static|async|override)?\s*"
    r"(\w+)\s*\([^)]*\)\s*(?::\s*[\w<>\[\]|&\s]+)?\s*(?:\{|;)",
    re.MULTILINE
)


def extract_ts_structure(source: str, rel_path: str) -> str:
    sections = [f"## {rel_path}\n"]

    # 接口和类型定义（信息密度最高）
    interfaces = INTERFACE_RE.findall(source)
    if interfaces:
        sections.append("**类型/接口定义：**")
        for m in INTERFACE_RE.finditer(source):
            sections.append(f"```typescript\n{m.group(0)[:400]}\n```")

    # Angular 装饰器（组件/服务元数据）
    decorators = DECORATOR_RE.findall(source)
    if decorators:
        sections.append(f"**装饰器：** {', '.join(set(decorators))}")
        for m in DECORATOR_RE.finditer(source):
            sections.append(f"```typescript\n{m.group(0)[:300]}\n```")

    # 类签名（含 implements / extends）
    for m in CLASS_RE.finditer(source):
        sections.append(f"**类：** `{m.group(0).strip()}`")

    # 公开方法签名（只取 public / 无修饰符的方法）
    pub_methods = [
        m.group(0).strip().rstrip("{").strip()
        for m in METHOD_RE.finditer(source)
        if not m.group(0).strip().startswith("private")
        and not m.group(0).strip().startswith("protected")
    ]
    if pub_methods:
        sections.append("**公开方法签名：**")
        for sig in pub_methods[:15]:
            sections.append(f"- `{sig}`")

    return "\n".join(sections)


root = Path(PROJECT_DIR)
groups: dict[str, list[str]] = {}

for fpath in sorted(root.rglob("*.ts")):
    if any(ex in fpath.parts for ex in EXCLUDE_DIRS): continue
    if fpath.suffix not in {".ts", ".tsx"}: continue
    if fpath.stat().st_size > 100 * 1024: continue  # 跳过超大生成文件

    source = fpath.read_text(encoding="utf-8", errors="ignore")
    rel = fpath.relative_to(root)
    group = rel.parts[0] if len(rel.parts) > 1 else "root"

    if group not in groups:
        groups[group] = []
    groups[group].append(extract_ts_structure(source, str(rel)))

for group, contents in groups.items():
    fname = f"code__ts__{group}.md"
    with open(os.path.join(OUTPUT_DIR, fname), "w", encoding="utf-8") as f:
        f.write(f"---\nsource: {PROJECT_DIR}/{group}\ntype: code\nlang: typescript\n---\n\n")
        f.write(f"# TypeScript 模块: {group}\n\n")
        f.write("\n\n".join(contents))
    print(f"[TypeScript] {group} → {fname}")
```

---

## 1.5 本地文档工程

**适用**：Obsidian vault、Notion 导出、Confluence 导出、本地 Markdown 文档、Word/PPT 文件

**核心挑战**：格式多样、内部链接断裂、双链（`[[wikilink]]`）需要解析

---

### Markdown 文档目录（Obsidian / Notion 导出）

```python
# extract_local_docs.py
import os, re, shutil
from pathlib import Path

SOURCE_DIR = "./my-vault"      # 本地文档目录
OUTPUT_DIR = "./raw"
os.makedirs(OUTPUT_DIR, exist_ok=True)

WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def resolve_wikilinks(text: str, all_files: dict[str, str]) -> str:
    """将 [[WikiLink]] 转为 Markdown 链接或纯文本"""
    def replace(m):
        name = m.group(1).strip()
        if name in all_files:
            return f"[{name}]({all_files[name]})"
        return f"**{name}**"
    return WIKILINK_RE.sub(replace, text)


# 建立文件名→路径映射（用于解析 wikilink）
all_md_files = {}
for f in Path(SOURCE_DIR).rglob("*.md"):
    all_md_files[f.stem] = str(f)

for src_path in Path(SOURCE_DIR).rglob("*.md"):
    rel = src_path.relative_to(SOURCE_DIR)
    # 过滤隐藏文件和系统文件
    if any(part.startswith(".") for part in rel.parts):
        continue

    content = src_path.read_text(encoding="utf-8", errors="ignore")
    content = resolve_wikilinks(content, all_md_files)

    # 输出文件名：用目录层级替代 /
    out_name = "docs__" + str(rel).replace(os.sep, "__")
    out_path = os.path.join(OUTPUT_DIR, out_name)

    with open(out_path, "w", encoding="utf-8") as f:
        # 注入 frontmatter
        if not content.startswith("---"):
            f.write(f"---\nsource: {src_path}\ntype: local_doc\n---\n\n")
        f.write(content)

print(f"[本地文档] 处理完成，输出到 {OUTPUT_DIR}/")
```

> **Obsidian 附件说明**：`extract_local_docs.py` 只处理 `.md` 文件。Obsidian vault 中常见的嵌入图片（`![[image.png]]`）和内嵌 PDF 会被跳过。
> - 嵌入图片：如需提取图片文字，对 `./attachments/` 目录下的 `.png/.jpg` 文件用 Tesseract OCR 处理（见 3.4 节）
> - 内嵌 PDF：对 vault 内的 `.pdf` 文件走 1.3 节的 PDF 提取流程
> - 当前脚本会将 `![[image.png]]` 保留为原文本，LLM 在构建 Wiki 时会忽略它，不影响整体流程
```

---

### Word / PowerPoint 文件

```bash
pip install python-docx python-pptx
```

```python
# extract_office.py
import os
from pathlib import Path
from docx import Document
from pptx import Presentation

OUTPUT_DIR = "./raw"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def docx_to_markdown(docx_path: str) -> str:
    doc = Document(docx_path)
    lines = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            lines.append("")
            continue
        style = para.style.name
        if style.startswith("Heading 1"):
            lines.append(f"# {text}")
        elif style.startswith("Heading 2"):
            lines.append(f"## {text}")
        elif style.startswith("Heading 3"):
            lines.append(f"### {text}")
        elif style.startswith("List"):
            lines.append(f"- {text}")
        else:
            lines.append(text)
    return "\n".join(lines)


def pptx_to_markdown(pptx_path: str) -> str:
    prs = Presentation(pptx_path)
    lines = []
    for i, slide in enumerate(prs.slides, 1):
        lines.append(f"\n## 幻灯片 {i}")
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    text = para.text.strip()
                    if text:
                        lines.append(text)
    return "\n".join(lines)


for f in Path("./documents").glob("*.docx"):
    content = docx_to_markdown(str(f))
    fname = f"office__{f.stem}.md"
    with open(os.path.join(OUTPUT_DIR, fname), "w", encoding="utf-8") as out:
        out.write(f"---\nsource: {f}\ntype: local_doc\nformat: docx\n---\n\n")
        out.write(content)
    print(f"[Word] {f.name} → {fname}")

for f in Path("./documents").glob("*.pptx"):
    content = pptx_to_markdown(str(f))
    fname = f"office__{f.stem}.md"
    with open(os.path.join(OUTPUT_DIR, fname), "w", encoding="utf-8") as out:
        out.write(f"---\nsource: {f}\ntype: local_doc\nformat: pptx\n---\n\n")
        out.write(content)
    print(f"[PPT] {f.name} → {fname}")
```

---

## 1.6 GitHub 仓库

**适用**：发现一个优秀的开源工具/框架/工程，想快速理解它的设计思路、使用方式和社区知识。

**核心挑战**：GitHub 仓库的知识散布在多个维度——代码结构、官方文档、Issues 里的设计讨论、Discussions 里的使用经验、Releases 里的变更历史。单看 README 只是入门，真正的理解需要把这几层都纳入。

**信息密度排序**（从高到低）：

| 来源 | 内容类型 | 优先级 |
|------|---------|-------|
| README + docs/ | 设计目标、架构说明、使用方法 | 最高 |
| Issues（特别是 closed） | 设计决策、已知限制、边缘情况 | 高 |
| Releases / CHANGELOG | 演进历史、破坏性变更、重要特性 | 高 |
| 代码结构 + 核心文件 | 实现细节（配合 1.4 节使用） | 中 |
| Discussions | 社区经验、最佳实践、踩坑记录 | 中 |
| Wiki | 深度文档（并非所有仓库都有） | 中 |

### 工具安装

```bash
brew install gh        # GitHub CLI
gh auth login          # 登录（浏览器或 token）
```

### 完整提取脚本 `extract_github.py`

```python
# extract_github.py — 提取 GitHub 仓库的多层知识
import json, os, re, subprocess, tempfile, shutil
from pathlib import Path

OUTPUT_DIR = "./raw"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def gh(args: list[str]) -> dict | list | str:
    r = subprocess.run(["gh"] + args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gh 命令失败: {r.stderr[:200]}")
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return r.stdout


def slug(repo: str) -> str:
    return repo.replace("/", "__")


# ── 1. 仓库基本信息 + README ─────────────────────────────────────────

def extract_repo_overview(repo: str):
    """README、描述、主题标签、Stars 等基本信息"""
    data = gh(["repo", "view", repo, "--json",
               "name,description,homepageUrl,topics,stargazerCount,"
               "primaryLanguage,licenseInfo,createdAt,updatedAt,readme"])

    lines = [
        f"---\nsource: https://github.com/{repo}\ntype: github\nsubtype: overview\n---\n",
        f"# {data.get('name', repo)}\n",
        f"- **描述**: {data.get('description', '')}",
        f"- **主页**: {data.get('homepageUrl', '')}",
        f"- **Stars**: {data.get('stargazerCount', 0):,}",
        f"- **主要语言**: {(data.get('primaryLanguage') or {}).get('name', '')}",
        f"- **话题标签**: {', '.join(data.get('topics', []))}",
        f"- **更新时间**: {data.get('updatedAt', '')[:10]}",
        "",
        "## README",
        data.get("readme", "*无 README*"),
    ]

    fname = f"github__{slug(repo)}__overview.md"
    Path(OUTPUT_DIR, fname).write_text("\n".join(lines), encoding="utf-8")
    print(f"[GitHub] overview → {fname}")


# ── 2. Issues（设计决策 + 问题记录）────────────────────────────────────

def extract_issues(repo: str, limit: int = 100, state: str = "all"):
    """提取 Issues，closed 的往往含更多设计讨论"""
    issues = gh(["issue", "list", "-R", repo,
                 "--state", state, "--limit", str(limit),
                 "--json", "number,title,body,state,labels,comments,createdAt"])

    if not isinstance(issues, list):
        print(f"  [跳过] Issues 获取失败")
        return

    # 按 label 分组，帮助 LLM 理解问题类型
    label_groups: dict[str, list] = {}
    for issue in issues:
        labels = [l["name"] for l in (issue.get("labels") or [])] or ["general"]
        for label in labels:
            label_groups.setdefault(label, []).append(issue)

    # 每 20 个 issue 一个文件（按 label 分组）
    written = set()
    for label, group in sorted(label_groups.items()):
        lines = [
            f"---\nsource: https://github.com/{repo}/issues\n"
            f"type: github\nsubtype: issues\nlabel: {label}\n---\n",
            f"# Issues — {repo} [{label}]\n",
        ]
        for issue in group:
            if issue["number"] in written:
                continue
            written.add(issue["number"])
            lines.append(f"\n## #{issue['number']}: {issue['title']}")
            lines.append(f"*状态: {issue['state']} | {issue['createdAt'][:10]}*\n")
            if issue.get("body"):
                lines.append(issue["body"][:1000])
            for comment in (issue.get("comments") or [])[:5]:
                body = (comment.get("body") or "")[:500]
                if body.strip():
                    lines.append(f"\n> **评论**: {body}")

        label_safe = re.sub(r'[/\\:*?"<>| ]', "-", label)
        fname = f"github__{slug(repo)}__issues__{label_safe}.md"
        Path(OUTPUT_DIR, fname).write_text("\n".join(lines), encoding="utf-8")
        print(f"[GitHub] issues[{label}] → {fname}")


# ── 3. Releases + CHANGELOG ─────────────────────────────────────────

def extract_releases(repo: str, limit: int = 20):
    """版本历史：了解项目演进、破坏性变更、重要特性"""
    releases = gh(["release", "list", "-R", repo,
                   "--limit", str(limit),
                   "--json", "name,tagName,publishedAt,body,isLatest"])

    if not isinstance(releases, list) or not releases:
        # 尝试 CHANGELOG.md
        _try_extract_changelog(repo)
        return

    lines = [
        f"---\nsource: https://github.com/{repo}/releases\n"
        f"type: github\nsubtype: releases\n---\n",
        f"# Releases — {repo}\n",
    ]
    for rel in releases:
        tag = rel.get("tagName", "")
        latest = " ✦ latest" if rel.get("isLatest") else ""
        lines.append(f"\n## {rel.get('name') or tag}{latest}")
        lines.append(f"*{rel.get('publishedAt', '')[:10]}*\n")
        body = (rel.get("body") or "").strip()
        if body:
            lines.append(body[:2000])

    fname = f"github__{slug(repo)}__releases.md"
    Path(OUTPUT_DIR, fname).write_text("\n".join(lines), encoding="utf-8")
    print(f"[GitHub] releases → {fname}")


def _try_extract_changelog(repo: str):
    """仓库没有 Release 时，尝试提取根目录的 CHANGELOG 文件"""
    for fname in ["CHANGELOG.md", "CHANGELOG", "HISTORY.md", "CHANGES.md"]:
        try:
            content = gh(["api", f"repos/{repo}/contents/{fname}",
                          "--jq", ".content"])
            if isinstance(content, str) and content.strip():
                import base64
                text = base64.b64decode(content.strip()).decode("utf-8", errors="ignore")
                out = (f"---\nsource: https://github.com/{repo}/{fname}\n"
                       f"type: github\nsubtype: changelog\n---\n\n{text}")
                out_fname = f"github__{slug(repo)}__changelog.md"
                Path(OUTPUT_DIR, out_fname).write_text(out, encoding="utf-8")
                print(f"[GitHub] changelog → {out_fname}")
                return
        except RuntimeError:
            continue


# ── 4. Discussions ───────────────────────────────────────────────────

def extract_discussions(repo: str, limit: int = 50):
    """社区讨论：最佳实践、踩坑记录、设计问答"""
    owner, name = repo.split("/")
    query = f'''
    {{
      repository(owner: "{owner}", name: "{name}") {{
        discussions(first: {limit}, orderBy: {{field: COMMENTS, direction: DESC}}) {{
          nodes {{
            number title body
            category {{ name }}
            comments(first: 5) {{
              nodes {{ body author {{ login }} }}
            }}
          }}
        }}
      }}
    }}
    '''
    try:
        result = gh(["api", "graphql", "-f", f"query={query}"])
        discussions = (result.get("data", {})
                       .get("repository", {})
                       .get("discussions", {})
                       .get("nodes", []))
    except (RuntimeError, AttributeError):
        print(f"  [跳过] Discussions 不可用（仓库可能未开启）")
        return

    if not discussions:
        return

    lines = [
        f"---\nsource: https://github.com/{repo}/discussions\n"
        f"type: github\nsubtype: discussions\n---\n",
        f"# Discussions — {repo}\n",
    ]
    for d in discussions:
        cat = (d.get("category") or {}).get("name", "")
        lines.append(f"\n## #{d['number']}: {d['title']}")
        if cat:
            lines.append(f"*分类: {cat}*\n")
        if d.get("body"):
            lines.append(d["body"][:800])
        for comment in (d.get("comments") or {}).get("nodes", [])[:3]:
            body = (comment.get("body") or "")[:400]
            author = (comment.get("author") or {}).get("login", "")
            if body.strip():
                lines.append(f"\n> **@{author}**: {body}")

    fname = f"github__{slug(repo)}__discussions.md"
    Path(OUTPUT_DIR, fname).write_text("\n".join(lines), encoding="utf-8")
    print(f"[GitHub] discussions → {fname}")


# ── 5. Wiki ───────────────────────────────────────────────────────────

def extract_wiki(repo: str):
    """克隆 Wiki 仓库（如果存在）"""
    wiki_url = f"https://github.com/{repo}.wiki.git"
    tmp = tempfile.mkdtemp()
    try:
        r = subprocess.run(["git", "clone", "--depth", "1", wiki_url, tmp],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return  # Wiki 不存在，静默跳过

        for md_path in Path(tmp).glob("*.md"):
            content = md_path.read_text(encoding="utf-8", errors="ignore")
            out = (f"---\nsource: https://github.com/{repo}/wiki/{md_path.stem}\n"
                   f"type: github\nsubtype: wiki\n---\n\n{content}")
            fname = f"github__{slug(repo)}__wiki__{md_path.stem}.md"
            Path(OUTPUT_DIR, fname).write_text(out, encoding="utf-8")
            print(f"[GitHub] wiki/{md_path.name} → {fname}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── 6. 代码结构（选用）──────────────────────────────────────────────

def extract_code_structure(repo: str):
    """
    克隆仓库后走 1.4 节的 extract_code.py 流程。
    适合你真的要深入研究某个工具的实现细节时使用。
    日常「了解工具」通常只需要 overview + issues + releases。
    """
    tmp = tempfile.mkdtemp()
    try:
        r = subprocess.run(
            ["git", "clone", "--depth", "1",
             f"https://github.com/{repo}.git", tmp],
            capture_output=True, text=True
        )
        if r.returncode != 0:
            print(f"  [失败] 克隆仓库: {r.stderr[:100]}")
            return

        # 复用 1.4 节的代码提取逻辑
        # 直接调用 extract_code 命令（Phase 1 实现后可用）
        # 或内联项目概览脚本：
        overview_lines = [
            f"---\nsource: https://github.com/{repo}\n"
            f"type: github\nsubtype: code_structure\n---\n",
            f"# 代码结构 — {repo}\n",
            "## 目录结构",
        ]
        root = Path(tmp)
        EXCLUDE = {"node_modules", ".git", "dist", "build", "__pycache__", ".venv"}
        for f in sorted(root.rglob("*")):
            if f.is_file() and not any(ex in f.parts for ex in EXCLUDE):
                rel = f.relative_to(root)
                if len(rel.parts) <= 3:  # 只展示前三层
                    overview_lines.append(f"  {'  ' * (len(rel.parts)-1)}{rel.name}")

        # package.json / pyproject.toml 等配置
        for cfg in ["package.json", "pyproject.toml", "Cargo.toml", "go.mod"]:
            cfg_path = root / cfg
            if cfg_path.exists():
                overview_lines.append(f"\n## {cfg}")
                overview_lines.append("```")
                overview_lines.append(cfg_path.read_text(encoding="utf-8")[:800])
                overview_lines.append("```")

        fname = f"github__{slug(repo)}__code_structure.md"
        Path(OUTPUT_DIR, fname).write_text("\n".join(overview_lines), encoding="utf-8")
        print(f"[GitHub] code_structure → {fname}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── 主函数 ────────────────────────────────────────────────────────────

def extract_github_repo(
    repo: str,
    *,
    issues: bool = True,
    releases: bool = True,
    discussions: bool = True,
    wiki: bool = True,
    code: bool = False,       # 默认关闭，按需开启
    issue_limit: int = 100,
):
    """
    repo: "OWNER/REPO" 格式，例如 "anthropics/claude-code"
    code: 是否同时提取代码结构（仓库大时较慢）
    """
    print(f"\n开始提取: https://github.com/{repo}")
    extract_repo_overview(repo)
    if releases:
        extract_releases(repo)
    if issues:
        extract_issues(repo, limit=issue_limit)
    if discussions:
        extract_discussions(repo)
    if wiki:
        extract_wiki(repo)
    if code:
        extract_code_structure(repo)
    print(f"完成: {repo}\n")


# 使用示例：
# extract_github_repo("anthropics/claude-code")
# extract_github_repo("BerriAI/litellm", code=True)
# extract_github_repo("langchain-ai/langchain", issue_limit=200)
```

---

### 快速单仓库提取（命令行）

```bash
# 安装依赖
brew install gh && gh auth login

# 提取单个仓库（最常用）
python -c "
from extract_github import extract_github_repo
extract_github_repo('OWNER/REPO')
"

# 只取 overview + releases（快速了解）
python -c "
from extract_github import extract_github_repo
extract_github_repo('OWNER/REPO', issues=False, discussions=False, wiki=False)
"

# 深度研究（含代码结构）
python -c "
from extract_github import extract_github_repo
extract_github_repo('OWNER/REPO', code=True, issue_limit=200)
"
```

---

### 输出文件说明

| 文件名模式 | 内容 | 何时有用 |
|-----------|------|---------|
| `github__OWNER__REPO__overview.md` | README + 基本信息 | 始终提取 |
| `github__OWNER__REPO__releases.md` | 版本历史 + 变更说明 | 了解项目演进 |
| `github__OWNER__REPO__issues__bug.md` | Bug 类 Issues | 了解已知问题 |
| `github__OWNER__REPO__issues__enhancement.md` | 功能讨论 Issues | 了解设计决策 |
| `github__OWNER__REPO__discussions.md` | 社区经验 | 最佳实践 |
| `github__OWNER__REPO__wiki__*.md` | Wiki 页面 | 仓库有 Wiki 时 |
| `github__OWNER__REPO__code_structure.md` | 目录结构 + 配置 | 研究实现时 |

---

### 典型场景

**场景：发现一个好工具（如 crawl4ai），想快速搞清楚能用来做什么**

```bash
python -c "
from extract_github import extract_github_repo
extract_github_repo('unclecode/crawl4ai', issues=True, releases=True)
"
# 约 2-3 分钟，输出 5-8 个 raw/ 文件
# 然后用 Claude Code：
# '读取 ./raw/github__unclecode__crawl4ai__*.md，告诉我这个工具的核心能力、典型使用场景和主要限制'
```

**场景：评估一个库是否适合引入项目（了解稳定性、维护状态）**

```bash
python -c "
from extract_github import extract_github_repo
extract_github_repo('TARGET/REPO', releases=True, issues=True, issue_limit=50)
"
# 查询：'根据 releases 和 issues，评估这个库的维护活跃度、breaking change 频率、主要 bug 类型'
```

---

## 1.7 单篇网络文章

**适用**：微信公众号、今日头条/西瓜视频、知乎、Medium、Substack、少数派、掘金、各类博客单篇……任何「刷到一篇好文章想存进知识库」的场景。

**和 1.1 的区别**：1.1 是系统性消化整个网站，1.7 是轻量随手收藏——一行命令，一篇文章，进入 raw/，后续自动纳入 Wiki。

**抓取路由（已实现，`extractors/article.py`）**：

| 平台 | 工具 | 成功率 | 原理 |
|------|------|--------|------|
| 微信公众号 | **Camoufox** stealth browser | 95%+ | 模拟 iPhone 微信内置浏览器 UA，绕过强反爬 |
| 今日头条 / 西瓜 | **Playwright** Chromium | 90%+ | 真实浏览器渲染，绕过 JSVM 加密 |
| 知乎 / 少数派 / 掘金 / 其他 | **crawl4ai** → Jina Reader 降级 | 99%+ | JS 渲染抓取，降级无需安装 |

> 这三条路径都已集成到 `content-extract article` 命令，自动识别平台路由，无需手动选择。

---

### 依赖安装（一次性）

```bash
# 微信专用（隐身浏览器）
pip install camoufox
camoufox fetch          # 下载浏览器内核（约 100MB，一次性）

# 今日头条专用
pip install playwright
playwright install chromium

# 通用网页（已包含在 core 依赖中）
pip install crawl4ai
```

---

### 命令行使用

```bash
# TUI（推荐日常使用）
content-extract                       # 启动 TUI，粘贴 URL 即可
                                      # 微信/头条/通用网页自动路由

# CLI 直接执行
content-extract article https://mp.weixin.qq.com/s/xxxxxxxx    # 微信公众号
content-extract article https://www.toutiao.com/article/xxx    # 今日头条
content-extract article https://zhuanlan.zhihu.com/p/xxxxxxxx  # 知乎
content-extract article --batch article_urls.txt               # 批量（每行一个 URL）
```

---

### 各平台抓取成功率速查

| 平台 | 方法 | 成功率 | 备注 |
|------|------|--------|------|
| 微信公众号 | Camoufox | ★★★★★ | 95%+，全自动，无需手动操作 |
| 今日头条 / 西瓜 | Playwright | ★★★★☆ | 90%+，少数文章被风控可降级 |
| 知乎 | crawl4ai / Jina | ★★★★★ | 直接可用 |
| 少数派 | crawl4ai / Jina | ★★★★★ | 直接可用 |
| Medium | crawl4ai / Jina | ★★★★☆ | 付费文章会截断 |
| Substack | crawl4ai / Jina | ★★★★★ | 直接可用 |
| 掘金 | crawl4ai / Jina | ★★★★★ | 直接可用 |
| 其他博客 | crawl4ai / Jina | ★★★★☆ | 绝大多数可用 |

---

### 浏览器插件辅助（极少数情况）

对于极少数无法自动抓取的场景（如付费墙、需登录的私密公众号），浏览器插件是备用方案：

| 插件 | 支持浏览器 | 功能 |
|------|-----------|------|
| [MarkDownload](https://github.com/deathau/markdownload) | Chrome / Firefox / Safari | 一键把当前页面保存为 Markdown |
| [Copy as Markdown](https://chromewebstore.google.com/detail/copy-as-markdown) | Chrome | 复制选中内容为 Markdown |

**工作流**：打开文章 → 点插件 → 保存文件到 `./raw/` 目录，命名为 `article__平台__标题.md`，然后正常走 Part 2 Wiki 构建流程。

---

### 依赖安装（按需）

```bash
# 基础（通用平台，无需额外安装）
# Jina Reader 直接 curl，不需要任何 Python 包

# Playwright 降级（处理反爬平台）
pip install camoufox && camoufox fetch  # 微信公众号（隐身浏览器，95%+ 成功率）
pip install playwright && playwright install chromium  # 今日头条（Chromium）

# 批量 URL 管理
# 直接用 txt 文件，无需额外依赖
```

---

## 1.8 Topic 模式：本地资料导入

**适用**：Topic 学习模式下的本地文件（md/html/txt），不需要网络，直接读取并写入 frontmatter。

**和其他来源的区别**：
- 不复制原文件到 `raw/`，而是生成一个「引用文件」记录原始路径
- 原文件内容提取后写入引用文件正文
- frontmatter 额外包含 `topic` 和 `topic_role` 字段

### 命令行用法

```bash
# 导入单个本地文件到指定 topic
content-extract local ./笔记/量化策略.md --topic "量化投资入门" --role "个人笔记"

# 导入本地 html 文件
content-extract local ./saved/article.html --topic "量化投资入门" --role "入门概述"

# 批量导入目录下的 md 文件（不递归）
content-extract local ./笔记/ --topic "量化投资入门"
```

### 脚本实现

```python
# extract_local_topic.py — Topic 模式本地文件导入
import os, re, hashlib
from pathlib import Path
from datetime import datetime, timezone

OUTPUT_DIR = "./raw"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def extract_html_text(html_path: Path) -> str:
    """从 HTML 文件提取纯文本（去掉标签）。"""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
        # 保留标题层级
        for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
            level = int(tag.name[1])
            tag.replace_with(f"\n{'#' * level} {tag.get_text()}\n")
        return soup.get_text(separator="\n")
    except ImportError:
        # 无 beautifulsoup4 时降级为正则清理
        text = html_path.read_text(encoding="utf-8", errors="ignore")
        return re.sub(r"<[^>]+>", "", text)


def import_local_file(
    file_path: str,
    topic: str,
    topic_role: str = "",
    output_dir: str = OUTPUT_DIR,
) -> Path:
    """
    导入本地 md/html/txt 文件到 Topic raw 目录。
    不复制原文件，生成引用文件并写入 frontmatter。
    """
    src = Path(file_path).resolve()
    if not src.exists():
        raise FileNotFoundError(f"文件不存在: {src}")

    # 读取内容（按格式处理）
    if src.suffix.lower() in (".html", ".htm"):
        content = extract_html_text(src)
    else:
        content = src.read_text(encoding="utf-8", errors="ignore")

    content = re.sub(r"\n{3,}", "\n\n", content).strip()
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:8]

    # 输出目录：raw/topics/<topic>/
    topic_dir = Path(output_dir) / "topics" / re.sub(r'[/\\:*?"<>|]', "-", topic)
    topic_dir.mkdir(parents=True, exist_ok=True)

    # 输出文件名
    slug = re.sub(r'[/\\:*?"<>|]', "-", src.stem)[:50]
    fname = f"local__{slug}.md"
    out_path = topic_dir / fname

    # 写入引用文件
    lines = [
        f"---",
        f"source: {src}",           # 原始本地路径（绝对路径）
        f"type: local_doc",
        f"format: {src.suffix.lstrip('.')}",
        f"topic: \"{topic}\"",
        f"topic_role: \"{topic_role}\"" if topic_role else "",
        f"extracted_at: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')}",
        f"content_hash: {content_hash}",
        f"---",
        f"",
        content,
    ]
    out_path.write_text("\n".join(l for l in lines if l is not None), encoding="utf-8")
    print(f"[Local] {src.name} → {fname}（topic: {topic}）")
    return out_path


def import_local_dir(
    dir_path: str,
    topic: str,
    extensions: tuple = (".md", ".html", ".htm", ".txt"),
    output_dir: str = OUTPUT_DIR,
) -> list[Path]:
    """批量导入目录下符合扩展名的文件（不递归）。"""
    src_dir = Path(dir_path)
    results = []
    for f in sorted(src_dir.iterdir()):
        if f.is_file() and f.suffix.lower() in extensions:
            try:
                results.append(import_local_file(str(f), topic, output_dir=output_dir))
            except Exception as e:
                print(f"  [跳过] {f.name}: {e}")
    return results


# 使用示例：
# import_local_file("./笔记/量化策略.md", topic="量化投资入门", topic_role="个人笔记")
# import_local_dir("./笔记/", topic="量化投资入门")
```

**输出文件规范**：
- 存放路径：`raw/topics/<topic名>/local__<文件名>.md`
- `source` 字段记录原始绝对路径，便于追溯和更新
- 若原文件更新，重新导入即可（`content_hash` 不同会覆盖）

---

# Part 2：通用分析整理与检索

> 以下流程对所有内容源通用。完成 Part 1 后，`./raw/` 目录下统一是 Markdown 文件，直接进入此流程。
>
> **项目目录约定**：`./raw/`、`./wiki/`、`CLAUDE.md` 均在同一个工作目录下。用 `content-extract init` 可自动生成初始结构（含 `wiki/DASHBOARD.md` 和 `CLAUDE.md` 模板）。`skill/SKILL.md` 安装到 `~/.claude/skills/` 后，在任意目录的 Claude Code 中可通过 `/content-extract` 调用。

---

## 2.1 快速全局理解（当天可完成）

**适用**：第一次接触一个内容集合，需要快速建立整体框架。

```bash
# 合并所有 raw 文件（评估总量）
find ./raw -name "*.md" -exec cat {} \; > ./all_content.md
wc -c ./all_content.md
# Claude 上下文约 200k token ≈ 600KB 文本
# 超过 1MB 时做分层处理（见 Part 3 异常处理）
```

**框架理解 Prompt（直接粘贴给 Claude）：**

```
以下是一批内容的全部文本，内容类型可能包括：技术文章、视频转录、电子书章节、代码注释、文档。

请帮我生成：
1. **核心主题列表**（按重要性排序，每个主题一句话说明）
2. **主题关系图**（文字版：哪些主题相互依赖、补充或冲突）
3. **内容全局定位**（这批内容覆盖什么范围，有什么明显缺失）
4. **推荐学习/阅读路径**（如果我是这个领域的中级从业者，从哪里开始）
5. **高价值内容清单**（最值得精读的 10 个文件/章节，附文件名）

---内容开始---
[粘贴 all_content.md]
```

---

## 2.1B 困惑驱动的第二轮提取（陌生工程专用）

> 适用场景：第一次接触一个陌生工程，用 2.1 节的全局理解之后，发现还有大量「不知道自己不知道的」盲区。

**核心问题**：2.1 节的工作流是单向的——工程 → 提取 → 理解。但你提取了什么，取决于你已经知道什么该提取。对真正陌生的工程，这个前提不成立。

**解法**：让 Claude 先读一遍，列出它不清楚的东西，再用这些问题驱动第二轮有针对性的提取。

---

### Step 1：第一轮提取 + 让 Claude 暴露盲区

```
完成 2.1 节的全局理解后，在 Claude Code 里继续输入：

「现在作为一个需要修改这个工程的工程师，列出你还不清楚的 10 个关键问题。
 不要列「概念性」的问题，只列「如果我要改代码，我必须知道但现在不知道的」问题。
 格式：问题 → 可能在哪里找到答案（文件类型/位置）」
```

Claude 会输出类似：

```
1. 认证流程在哪里处理？JWT 还是 Session？→ 可能在 middleware/ 或 auth/ 目录
2. 数据库 migration 是如何运行的？→ 可能在 db/migrations/ 或 Makefile
3. 有没有外部依赖的 mock？测试能离线跑吗？→ 测试文件的 setup/fixtures
4. 这个 config.py 里的 settings 是如何被不同环境覆盖的？→ .env 文件或环境变量
5. ...
```

---

### Step 2：用问题驱动定向提取

```python
# targeted_extraction.py — 根据 Claude 的问题清单定向提取
import subprocess
from pathlib import Path

PROJECT = "./my-project"
OUTPUT_DIR = "./raw"

# 把 Claude 给出的「可能在哪里」转成具体的搜索模式
# 示例：Claude 说「可能在 middleware/ 或 auth/ 目录」
TARGET_PATTERNS = [
    "**/middleware/**/*.py",
    "**/auth/**/*.py",
    "**/db/migrations/**",
    "**/fixtures/**",
    "**/.env.example",
    "**/Makefile",
    "**/docker-compose*.yml",
]

# 也可以用关键词 grep
TARGET_KEYWORDS = [
    "jwt", "authenticate", "session",    # 从问题1来
    "migrate", "alembic", "flyway",      # 从问题2来
    "mock", "patch", "fixture",          # 从问题3来
]

print("=== 按模式定向提取 ===")
for pattern in TARGET_PATTERNS:
    matches = list(Path(PROJECT).rglob(pattern))
    for f in matches[:5]:
        print(f"  {f}")

print("\n=== 按关键词 grep ===")
for kw in TARGET_KEYWORDS:
    result = subprocess.run(
        ["grep", "-rl", kw, PROJECT, "--include=*.py", "--include=*.ts"],
        capture_output=True, text=True
    )
    files = result.stdout.strip().split("\n")
    if files and files[0]:
        print(f"  [{kw}] → {', '.join(files[:3])}")
```

---

### Step 3：把新提取的文件喂回去，问具体问题

```bash
# 把定向提取的文件加入 raw/
# 然后在 Claude Code 里：

「我刚加入了这些文件：[列出文件名]。
 现在回答之前的问题1：这个工程的认证流程是怎么实现的？
 找到具体的代码位置，用 3-5 句话解释。」
```

---

### 何时停止

两轮提取之后：
- Claude 给出的新问题开始重复 → 信息已经足够
- 剩余问题都是「需要运行才能知道」→ 进入 runtime 阶段（见 2.1C）
- Claude 开始说「根据这些文件，我认为……」→ 已经建立了心智模型

---

## 2.1C Runtime 维度补充（静态提取的盲区）

静态提取（AST、签名、注释）告诉你代码**长什么样**。但「这个系统真正在做什么」有时只在运行时才可见。

以下类型的信息，如果工程有，应该纳入 `raw/`：

| 信息类型 | 提取方式 | 放入 raw/ 的文件名 |
|---------|---------|-----------------|
| 日志样本（生产 or 测试） | 截取 100 行有代表性的日志 | `code__logs_sample.md` |
| 错误类型分布 | `grep -r "raise\|Exception\|Error" src/ \| sort \| uniq -c \| sort -rn` | `code__error_types.md` |
| 性能热路径 | benchmark 结果、profiling 报告、`@timing` 注解 | `code__perf_notes.md` |
| API 实际请求样本 | Postman collection、`curl` 示例、`*.http` 文件 | `code__api_samples.md` |
| 数据库 schema | `schema.sql`、migration 文件列表 | 直接加入 1.4 提取范围 |

```bash
# 快速提取错误类型分布（1 分钟可以做到）
grep -r "raise \|Exception\|Error" ./my-project/src \
    --include="*.py" -h \
    | grep -oP "raise \w+|class \w+Error|class \w+Exception" \
    | sort | uniq -c | sort -rn | head -30 \
    > ./raw/code__error_types.md
```

这个一行命令能告诉你这个工程**最关注什么失败场景**，比读 100 个函数签名更直接。

---

## 2.2 LLM Wiki 构建（持久化知识库）

> 从一次性理解升级为可持续查询的知识库。`./wiki/` 目录是最终输出。

### CLAUDE.md 配置（通用版）

在项目目录创建 `CLAUDE.md`，Claude Code 会自动读取：

```markdown
# 知识库构建规则

你是这批内容的知识管理员。
原始内容在 `./raw/` 目录（Markdown 格式）。
任务：构建结构化 Wiki 到 `./wiki/`。

## 内容来源识别

raw/ 文件名前缀说明：
- `web__`：网页/博客爬取（整站）
- `bili__`：Bilibili 视频转录
- `dy__`：抖音视频转录
- `epub__` / `pdf__`：电子书
- `code__`：代码工程（含 `code__ts__` TypeScript 专项）
- `docs__`：本地 Markdown / Notion / Confluence 文档
- `office__`：Word (.docx) / PowerPoint (.pptx) 文件（属于 local_doc 类型）
- `github__`：GitHub 仓库（含 `__overview` / `__issues__*` / `__releases` / `__discussions` / `__wiki__*` / `__code_structure` 子类型）
- `article__`：单篇网络文章（公众号/头条/知乎等）
- `local__`：Topic 模式下的本地 md/html 引用文件（不复制原文件，只写 frontmatter + 提取内容）

每个 raw/ 文件的 frontmatter 包含：
```yaml
source:        # 原始 URL 或本地路径
type:          # web | video | ebook | code | local_doc | github | article
platform:      # 仅 video/article 有：bilibili | douyin | wechat | toutiao | generic
subtype:       # 仅 github 有：overview | issues | releases | discussions | wiki | code_structure
topic:         # 仅 Topic 模式有：所属主题名（如「量化投资入门」）
topic_role:    # 仅 Topic 模式有：入门概述 | 核心方法论 | 深度参考 | 代码实例 | 案例研究 | 工具介绍
extracted_at:  # ISO 8601 时间戳（由 utils/frontmatter.py 写入，手动脚本可省略）
content_hash:  # 源内容 SHA256 前 8 位（用于增量去重，由 utils/frontmatter.py 写入）
```

> **注意**：Part 1 各节的独立脚本为简洁起见只写了 `source/type` 等核心字段。正式工具（`content-extract` CLI）通过 `utils/frontmatter.py` 统一补全所有字段。

## Wiki 目录结构

wiki/
├── INDEX.md          # 所有概念索引 + 来源分布图
├── concepts/         # 核心概念（跨来源整合）
│   └── CONCEPT.md
├── by-source/        # 按来源分类的摘要
│   ├── web.md
│   ├── video.md
│   ├── book.md
│   └── code.md
└── changelog.md

## 每个概念页面格式（wiki/concepts/CONCEPT.md）

---
sources: [文件名列表]          # 对应 raw/ 里的源文件名
related: [[concept-a]], [[concept-b]]
last-updated: YYYY-MM-DD
---

## 核心定义
（1-3 句话）

## 关键细节
（技术细节、代码片段、重要数据）

## 不同来源的视角
（同一概念在不同来源（文章/视频/书）中的表述差异）

## 未解答的问题
（整理这个概念时仍不清楚的地方）

## 构建步骤

1. 读取所有 `./raw/*.md` 文件
2. 识别跨来源的核心概念，每个建一个 `concepts/CONCEPT.md`
3. 为每种来源类型生成摘要（`by-source/*.md`）
4. 构建 `INDEX.md`：概念列表 + 来源分布 + 关联关系
5. 遇到内容冲突：标注在 `INDEX.md` 底部的「冲突记录」

## 更新规则

新文件加入 raw/ 时：
- 更新受影响的概念页面
- 在 changelog.md 记录
- 如有新概念，添加到 INDEX.md
```

**执行 Wiki 构建：**

```bash
cd /path/to/project
claude
# 指令：
# "读取 ./raw/ 下所有文件，按照 CLAUDE.md 的规则构建 Wiki 到 ./wiki/"
```

---

## 2.3 查询模式

### 模式 A：直接查询 Wiki 目录（最常用）

```bash
# Claude Code 中给出指令：
"根据 ./wiki/INDEX.md，找出和 [主题] 相关的所有概念"
"根据 ./wiki/concepts/xxx.md，解释 [概念] 的工作原理"
"跨来源比较：视频和书籍中关于 [主题] 的观点有什么不同？"
```

### 模式 B：上下文拼接查询

```python
# build_context.py — 按主题拼接相关 wiki 文件
import os

def build_context(topic: str, wiki_dir: str = "./wiki") -> str:
    """拼接与 topic 相关的 wiki 文件"""
    import subprocess
    # 用 grep 快速找相关文件
    result = subprocess.run(
        ["grep", "-rl", topic, wiki_dir],
        capture_output=True, text=True
    )
    related_files = result.stdout.strip().split("\n")

    context = []
    for fpath in related_files[:10]:  # 最多取 10 个相关文件
        if fpath and os.path.exists(fpath):
            with open(fpath) as f:
                context.append(f"# {fpath}\n\n{f.read()}")

    return "\n\n---\n\n".join(context)
```

### 模式 C：RAG 向量检索（Wiki 超大时）

> **中文内容注意**：ChromaDB 默认的 `DefaultEmbeddingFunction` 使用 `all-MiniLM-L6-v2`，该模型对中文内容效果很差。中文 Wiki 必须换用中文优化的 Embedding 模型。

```python
# setup_rag.py — Wiki 内容向量化（中文优化版）
# pip install chromadb sentence-transformers
import chromadb
from chromadb.utils import embedding_functions
import os

client = chromadb.PersistentClient(path="./chroma-db")

# 中文内容：使用 BAAI/bge-small-zh-v1.5（推荐，效果好且轻量）
# 英文内容：使用默认的 DefaultEmbeddingFunction 即可
zh_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="BAAI/bge-small-zh-v1.5"
)
collection = client.get_or_create_collection("wiki", embedding_function=zh_ef)

for root, _, files in os.walk("./wiki"):
    for f in files:
        if f.endswith(".md"):
            path = os.path.join(root, f)
            content = open(path).read()
            collection.upsert(documents=[content], ids=[path])

print("向量库已建立（中文优化 Embedding）")

# 查询
def rag_query(question: str, n: int = 5) -> list[str]:
    results = collection.query(query_texts=[question], n_results=n)
    return results["documents"][0]
```

### 模式 D：Anthropic Files API（小型内容集，最简单）

```python
# files_api_query.py — 上传 Wiki 文件，用 Claude API 查询
import anthropic, json, os

client = anthropic.Anthropic()

def upload_wiki(wiki_dir: str = "./wiki") -> list[str]:
    file_ids = []
    for root, _, files in os.walk(wiki_dir):
        for f in sorted(files):
            if f.endswith(".md"):
                path = os.path.join(root, f)
                with open(path, "rb") as fp:
                    resp = client.beta.files.upload(
                        file=(f, fp, "text/plain"),
                    )
                    file_ids.append(resp.id)
    json.dump(file_ids, open("./file_ids.json", "w"))
    print(f"已上传 {len(file_ids)} 个文件")
    return file_ids

def query(question: str, batch_size: int = 30) -> str:
    """
    Files API 单次请求建议不超过 30 个文件（受上下文窗口限制）。
    文件数超过 batch_size 时分批查询，取第一批结果（INDEX.md + 最相关文件）。
    若需要跨所有文件检索，改用 RAG 模式 C。
    """
    file_ids = json.load(open("./file_ids.json"))
    content = [
        {"type": "document", "source": {"type": "file", "file_id": fid}}
        for fid in file_ids[:batch_size]
    ]
    content.append({"type": "text", "text": question})
    resp = client.beta.messages.create(
        model="claude-sonnet-4-6",   # 查询用 Sonnet；批量摄取/整理用 Haiku 更省成本
        max_tokens=2048,
        messages=[{"role": "user", "content": content}],
        betas=["files-api-2025-04-14"],
    )
    return resp.content[0].text
```

---

## 2.4 持续维护

**新内容加入时的标准流程：**

```bash
# 1. 将新内容处理成 Markdown → raw/
# （按对应 Part 1 的来源类型运行相应脚本）

# 2. 更新 Wiki（Claude Code 指令）：
# "raw/ 目录有新文件：[文件名]。请更新 Wiki：
#  - 补充/更新相关 concepts/ 页面
#  - 更新 by-source/ 摘要
#  - 更新 INDEX.md 和 changelog.md"

# 3. （可选）定时自动化：
# crontab -e
# 0 9 * * 1 cd /path/to/project && python crawl_site.py && claude "更新 wiki"
```

---

## 2.5 Obsidian 集成 — 人类消费层

> `./wiki/` 本身就是一个 Obsidian vault，直接打开即可。Obsidian 不参与生产，只负责让你高效消费 LLM 整理好的知识。

### 角色分工

```
LLM        → 整理知识（往 wiki/ 写）
CLI        → 获取原料（往 raw/ 写）
你         → 策源 + 阅读 + 发现 gap
Obsidian   → 你的那一层：可视化、导航、移动端阅读
```

**关键原则**：`raw/` 是 LLM 的原料，人不读。你只读 `wiki/`，通过 Obsidian。

---

### Step 1：打开 vault

在 Obsidian 中选择「打开文件夹作为 vault」，选 `./wiki/` 目录。

CLAUDE.md 里定义的 `[[concept]]` wikilink 语法天然兼容 Obsidian——所有 `related: [[concept-a]], [[concept-b]]` 立刻变成可点击的双向链接，Graph view 里的节点和连线自动出现，零迁移成本。

---

### Step 2：创建 Dashboard

在 `wiki/` 根目录新建 `DASHBOARD.md`，安装 [Dataview 插件](https://github.com/blacksmithgu/obsidian-dataview) 后以下查询直接生效：

**安装 Dataview 插件（一次性）：**
1. Obsidian → 设置 → 第三方插件 → 关闭安全模式
2. 浏览社区插件 → 搜索 "Dataview" → 安装 → 启用
3. 重启 Obsidian，`DASHBOARD.md` 中的查询块自动渲染

````markdown
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

## 孤立概念（无关联节点）
```dataview
LIST
FROM "concepts"
WHERE !related
SORT file.name ASC
```
````

每次打开 Obsidian 从 Dashboard 开始：看「最近更新」知道 Wiki 新增了什么，看「孤立概念」知道哪里需要补充关联。

---

### Step 3：用 Graph view 发现知识 gap

Graph view 的正确用法不是「看着好看」，是**找孤立节点**。

孤立节点 = 没有 `[[related]]` 连线的概念 = 知识库里的死角。

```bash
# 发现孤立节点后，在 Claude Code 里执行：
# "wiki/concepts/xxx.md 目前没有关联概念，请阅读其内容，
#  找出相关联的其他概念并更新 related 字段"
```

---

### 阅读工作流

| 层 | 用什么读 | 目的 |
|----|---------|------|
| `raw/` | 不读（LLM 的原料） | — |
| `wiki/INDEX.md` | Obsidian，每次的起点 | 全局导航 |
| `wiki/concepts/` | Obsidian，点 `[[链接]]` 跳转 | 深入理解某个概念 |
| `wiki/by-source/` | Obsidian，按来源浏览 | 回顾某个视频/文章的要点 |
| `DASHBOARD.md` | Obsidian，每日入口 | 看新增内容，发现 gap |

**移动端**：`wiki/` 通过 iCloud 或 Obsidian Sync 同步后，iOS/Android app 直接可用。通勤时读 `wiki/concepts/` 里的笔记比读原始文章高效——LLM 已经把 1 小时视频压缩成 300 字结构化笔记。

---

### 维护循环

```
你发现好内容
      ↓
content-extract <type> <url>   ← CLI 写入 raw/
      ↓
Claude Code 更新 wiki/          ← LLM 写入 wiki/
      ↓
Obsidian 里自动出现新节点        ← 你看到
      ↓
Graph view 发现孤立节点
Dashboard 发现未解答问题         ← 你发现 gap
      ↓
告诉 Claude Code 补充关联        ← 循环
```

你在这个循环里只做两件事：**策源**和**发现 gap**。组织和整理是 LLM 的事。

---

### 插件清单（极简）

Obsidian 有几百个插件，装多了会让你把时间花在「整理笔记系统」而不是「消化知识」上。

| 插件 | 必要性 | 用途 |
|------|--------|------|
| [Dataview](https://github.com/blacksmithgu/obsidian-dataview) | **必装** | DASHBOARD.md 的动态查询 |
| [Graph Analysis](https://github.com/SkepticMystic/graph-analysis) | 可选 | 更好的图谱算法，找隐含关联 |
| 其余 | 不装 | — |

---

### 与 CLAUDE.md 的对接

`wiki/concepts/` 里每个文件的 frontmatter 格式（见 2.2 节）已经是 Dataview 可读的：

```yaml
---
sources: [web__xxx.md, bili__yyy.md]
related: [[concept-a]], [[concept-b]]
last-updated: 2026-06-01
---
```

`sources` 字段让你在 Obsidian 里点进某个概念后，知道它来自哪些原始文件。`related` 字段形成图谱的连线。这两个字段是 LLM 在构建 Wiki 时负责填写的——你不需要手动维护。

---

# Part 3：异常情况与补充

---

## 3.1 内容量过大（超出上下文窗口）

**症状**：`./raw/` 总大小超过 1MB，或 `./wiki/` 超过 200k token

**方案 1：分层查询（推荐，不增加复杂度）**

```bash
# 第一层：只看 INDEX.md（通常 < 10k token）
"根据 ./wiki/INDEX.md，这批内容覆盖哪些主题？"

# 第二层：按需读取具体概念
"读取 ./wiki/concepts/[具体概念].md，详细解释..."
```

**方案 2：按来源分批构建 Wiki**

```bash
# 每种来源单独建 Wiki，INDEX.md 做跨来源索引
mkdir -p ./wiki/from-web ./wiki/from-video ./wiki/from-books

# Claude Code 指令：
# "只处理 raw/ 中前缀为 web__ 的文件，构建 wiki/from-web/"
```

**方案 3：启用 RAG（见 Part 2 模式 C）**

适合 Wiki 超过 500 个文件的情况，查询时只取最相关片段。

---

## 3.2 字幕/转录质量差

**症状**：转录文本中大量乱码、重复、无标点

**通用清洗脚本（Claude API）：**

```python
# clean_transcript.py
import anthropic, os

client = anthropic.Anthropic()

def clean(raw_text: str, title: str) -> str:
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",   # 便宜模型做清洗
        max_tokens=4096,
        messages=[{"role": "user", "content": f"""
对以下转录文字做清洗，标题是「{title}」：
1. 添加标点符号
2. 删除口语填充词（"那个""就是""嗯""啊"）
3. 修正明显转录错误（同音字等）
4. 如果内容几乎无信息量，输出"LOW_QUALITY"
不要改变技术术语和原意，直接输出结果。

---
{raw_text[:3000]}
"""}]
    )
    return resp.content[0].text

def is_low_quality(text: str) -> bool:
    import re
    if len(text) < 100: return True
    chinese = len(re.findall(r'[一-鿿]', text))
    if len(text) > 0 and chinese / len(text) < 0.2: return True
    if len(set(text)) / max(len(text), 1) < 0.08: return True
    return False

RAW_DIR = "./raw"
for fname in os.listdir(RAW_DIR):
    if not fname.endswith(".md"): continue
    path = os.path.join(RAW_DIR, fname)
    content = open(path).read()

    # 只处理明显是转录文字的文件（无标点，口语化）
    body = content.split("\n\n", 2)[-1]
    punct_ratio = body.count("。") / max(len(body) / 100, 1)
    if punct_ratio > 2: continue  # 已有标点，跳过

    if is_low_quality(body):
        os.rename(path, path.replace(".md", ".low_quality.md"))
        print(f"[低质量] {fname}")
        continue

    title = content.split("\n")[0].replace("# ", "")
    cleaned = clean(body, title)
    if "LOW_QUALITY" in cleaned:
        os.rename(path, path.replace(".md", ".low_quality.md"))
        continue

    header = "\n".join(content.split("\n")[:5])
    open(path, "w").write(header + "\n\n" + cleaned)
    print(f"[清洗] {fname}")
```

---

## 3.3 反爬 / 访问限制

| 问题 | 表现 | 解决方案 |
|------|------|---------|
| IP 封锁 | 返回 403/429 | 添加 `--sleep-interval 3` 限速；换 IP/代理 |
| Cookie 失效 | 返回登录页内容 | 重新导出 Cookie，抖音约 1-2 周失效一次 |
| JS 渲染失败 | 页面内容为空 | crawl4ai 的 `wait_for` + `delay_before_return_html` |
| 付费墙 | 内容截断 | Playwright 模拟登录后爬取 |
| 版权保护 | yt-dlp 下载失败 | 添加 `--cookies-from-browser chrome` |
| Cloudflare | 5 秒盾 | crawl4ai 内置绕过；或用 Firecrawl（付费但稳定） |

```python
# 通用重试包装器
import time, functools

def with_retry(max_retries: int = 3, delay: float = 5.0):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    print(f"  [重试 {attempt+1}/{max_retries}] {e}")
                    time.sleep(delay * (attempt + 1))
        return wrapper
    return decorator
```

---

## 3.4 PDF 扫描版 / 复杂排版

**PDF 类型识别：**

```python
import pymupdf   # pip install pymupdf

def is_scanned_pdf(pdf_path: str) -> bool:
    """判断 PDF 是否为扫描版（图片型）。
    用文字密度判断：每页平均字符数 < 50 则认为是扫描版。
    不依赖图片计数——双栏扫描一页可能被识别为多张图，计数不可靠。
    """
    doc = pymupdf.open(pdf_path)
    if len(doc) == 0:
        return False
    avg_text = sum(len(page.get_text()) for page in doc) / len(doc)
    return avg_text < 50
```

```bash
# 扫描版：Tesseract OCR
brew install tesseract tesseract-lang
pip install pytesseract pdf2image

python -c "
from pdf2image import convert_from_path
import pytesseract

pages = convert_from_path('scanned.pdf', dpi=300)
texts = []
for i, page in enumerate(pages):
    text = pytesseract.image_to_string(page, lang='chi_sim+eng')
    texts.append(f'<!-- Page {i+1} -->\n{text}')

open('./raw/pdf__scanned.md', 'w').write('\n\n'.join(texts))
"

# 学术论文 / 数学公式：Mathpix API（付费，$0.004/页）
pip install mathpix-markdown-it
```

---

## 3.5 多人对话 / 访谈视频（说话人分离）

```python
# speaker_diarization.py
# pip install pyannote.audio
# 需要在 https://hf.co/pyannote/speaker-diarization-3.1 申请访问权限

from pyannote.audio import Pipeline
from faster_whisper import WhisperModel

HUGGINGFACE_TOKEN = "hf_xxxxxxxxxxxx"

pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    use_auth_token=HUGGINGFACE_TOKEN
)
whisper = WhisperModel("medium", device="cpu", compute_type="int8")


def transcribe_with_speakers(audio_path: str) -> str:
    # 说话人分离
    diarization = pipeline(audio_path)

    # Whisper 全文转录
    segments, _ = whisper.transcribe(audio_path, language="zh", word_timestamps=True)
    words = [(w.start, w.end, w.word) for seg in segments for w in (seg.words or [])]

    # 对齐：每段话分配说话人
    lines = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segment_words = [w for _, end, w in words if turn.start <= end <= turn.end]
        if segment_words:
            text = "".join(segment_words).strip()
            m, s = divmod(int(turn.start), 60)
            lines.append(f"[{m:02d}:{s:02d}] **{speaker}**: {text}")

    return "\n".join(lines)
```

---

## 3.6 代码工程量过大

当工程有 10 万行以上代码时，全量提取不现实。**按信息密度分层处理，不是按目录分层。**

信息密度排序（从高到低）：

| 层 | 文件类型 | 为什么高价值 |
|----|---------|------------|
| **第1层** | 测试文件（`*.test.*`、`*.spec.*`、`test_*.py`） | **唯一直接编码了「这个系统应该做什么、不应该做什么」的机器可读文档**。函数签名告诉你形状，测试告诉你契约 |
| **第2层** | 接口定义（`*.d.ts`、`types.py`、`interfaces.py`） | 公开 API 的完整形状，不含实现噪音 |
| **第3层** | 架构文档（`README*`、`ARCHITECTURE*`、`docs/**/*.md`） | 设计意图和边界说明 |
| **第4层** | 入口文件（`index.*`、`main.*`） | 依赖关系的起点 |
| **第5层** | 最近修改的文件（`git log`） | 活跃代码区域，复杂度热点 |

```python
# priority_code_extraction.py — 按信息价值分层提取
import subprocess
from pathlib import Path

PROJECT = "./large-project"
OUTPUT_DIR = "./raw"

# 第1层：测试文件（最高价值——契约文档）
tests = (
    list(Path(PROJECT).rglob("**/*.test.*")) +
    list(Path(PROJECT).rglob("**/*.spec.*")) +
    list(Path(PROJECT).rglob("**/test_*.py")) +
    list(Path(PROJECT).rglob("**/*_test.py"))
)[:80]

# 第2层：接口定义（类型/接口文件）
interfaces = (
    list(Path(PROJECT).rglob("*.d.ts")) +
    list(Path(PROJECT).rglob("**/types.py")) +
    list(Path(PROJECT).rglob("**/interfaces.py")) +
    list(Path(PROJECT).rglob("**/schema.py")) +
    list(Path(PROJECT).rglob("**/models.py"))
)[:50]

# 第3层：架构文档
docs = (
    list(Path(PROJECT).rglob("README*")) +
    list(Path(PROJECT).rglob("ARCHITECTURE*")) +
    list(Path(PROJECT).rglob("docs/**/*.md"))
)

# 第4层：入口文件
entries = (
    list(Path(PROJECT).rglob("index.*"))[:20] +
    list(Path(PROJECT).rglob("main.*"))[:10]
)

# 第5层：最近修改的文件（活跃热点）
result = subprocess.run(
    ["git", "-C", PROJECT, "log", "--name-only", "--format=", "-50"],
    capture_output=True, text=True
)
recent_files = [PROJECT + "/" + f for f in result.stdout.strip().split("\n") if f.strip()][:30]

priority_files = tests + interfaces + docs + entries + recent_files
print(f"优先处理 {len(priority_files)} 个文件（测试 {len(tests)} + 接口 {len(interfaces)} + 文档 {len(docs)} + 入口 {len(entries)} + 活跃 {len(recent_files)}）")
```

> **为什么测试排第一**：你不知道的不只是「代码怎么写的」，更是「代码应该做什么」。测试是唯一回答后一个问题的东西。对陌生工程，先读测试，后读实现。

---

## 3.7 Whisper 转录速度优化

| 场景 | 配置 | 预期速度 |
|------|------|---------|
| M 系 Mac（推荐） | `device="mps", compute_type="float16"` | 3-5x 提升 |
| NVIDIA GPU | `device="cuda", compute_type="float16"` | 5-10x 提升 |
| 云端 API（大批量） | OpenAI Whisper API `$0.006/分钟` | 不受本地算力限制 |
| 只需准确率不需速度 | `beam_size=5` | 默认，准确率最好 |
| 需要速度牺牲准确率 | `beam_size=1` | 速度提升 ~2x |

```python
# OpenAI Whisper API（付费但快，适合批量处理）
from openai import OpenAI
client = OpenAI()

with open("audio.mp3", "rb") as f:
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=f,
        language="zh",
        response_format="verbose_json",  # 含时间戳
        timestamp_granularities=["segment"]
    )

lines = []
for seg in transcript.segments:
    m, s = divmod(int(seg.start), 60)
    lines.append(f"[{m:02d}:{s:02d}] {seg.text.strip()}")
print("\n".join(lines))
```

---

## 3.8 各内容源成本与时间参考

以「处理 100 个单元内容」为基准估算：

| 内容源 | 单元 | 获取时间 | CPU 转录时间 | MPS 转录时间 | 主要成本 |
|--------|------|---------|------------|------------|---------|
| 技术博客 | 100 篇文章 | 30 分钟 | — | — | 无 |
| Bilibili（混合） | 100 个视频 | 30 分钟 | ~3h（50% 无字幕） | ~50 分钟 | 无 |
| 抖音 | 100 个视频 | 1h（含 cookie） | ~4h（全部转录） | ~1h | $0.5（LLM 清洗） |
| EPUB | 100 章 | 5 分钟 | — | — | 无 |
| PDF（文字型） | 100 页 | 5 分钟 | — | — | 无 |
| PDF（扫描版） | 100 页 | — | ~30 分钟 | — | 无（Tesseract）或 $0.4（Mathpix） |
| 代码工程 | 10 万行 | 10 分钟 | — | — | 无 |
| 本地 Markdown | 100 个文件 | 5 分钟 | — | — | 无 |
| GitHub 仓库 | 1 个仓库 | 3-5 分钟 | — | — | 无 |
| 单篇文章（微信公众号） | 1 篇 | **自动**（camoufox，95%+ 成功率） | — | — | 无 |
| 单篇文章（今日头条） | 1 篇 | **自动**（Playwright，90%+ 成功率） | — | — | 无 |
| 单篇文章（通用） | 1 篇 | 3-5 秒 | — | — | 无 |

> **CPU 基准**：MacBook Pro M3，`medium` 模型，处理 1 小时音频约需 15-20 分钟
> **MPS 加速**：M 系 Mac 使用 `device="mps", compute_type="float16"`，速度提升 3-5x，1 小时音频约需 3-5 分钟

---

## 工具全景速查

| 类别 | 工具 | 安装 | 主要用途 |
|------|------|------|---------|
| 网页爬取 | crawl4ai | `pip install crawl4ai` | 整站爬取，JS 渲染支持 |
| 网页爬取 | Jina Reader | 直接 curl | 快速单页，无需安装 |
| 视频字幕 | yt-dlp | `pip install yt-dlp` | 全平台字幕/音频下载（Bilibili、抖音等） |
| 音频转录 | faster-whisper | `pip install faster-whisper` | 本地 Whisper，推荐 |
| 音频处理 | ffmpeg | `brew install ffmpeg` | 音视频格式转换 |
| PDF 提取 | pymupdf4llm | `pip install pymupdf4llm` | 文字型 PDF |
| PDF 提取 | marker-pdf | `pip install marker-pdf` | 复杂排版 PDF |
| EPUB 提取 | ebooklib | `pip install ebooklib` | EPUB 解析 |
| Word/PPT | python-docx/python-pptx | `pip install python-docx python-pptx` | Office 文件 |
| OCR | tesseract | `brew install tesseract` | 扫描版 PDF |
| 向量检索 | chromadb | `pip install chromadb` | RAG 检索 |
| 大规模 RAG | LlamaIndex | `pip install llama-index` | 生产级检索 |
| 说话人分离 | pyannote.audio | `pip install pyannote.audio` | 访谈/对话视频 |
| GitHub 提取 | gh CLI | `brew install gh` | GitHub 仓库多层知识提取 |
| 单篇文章 | Jina Reader | 直接 curl | 无需安装，通用平台降级备选 |
| 单篇文章（微信） | camoufox | `pip install camoufox && camoufox fetch` | 隐身浏览器，95%+ 成功率 |
| 单篇文章（头条） | playwright | `pip install playwright && playwright install chromium` | Chromium，90%+ 成功率 |
| 知识消费 | Obsidian | [obsidian.md](https://obsidian.md) 下载安装 | 打开 wiki/ 作为 vault，Graph view + Dataview |
| 终端 UI | Textual | `pip install textual` | 无参数启动 content-extract 时的默认 TUI |
| 浏览器 UI | Streamlit | `pip install streamlit` | content-extract --web 启动（可选） |

---

## 3.9 安全注意事项

**敏感文件不要提交到 Git**

本文档中的脚本涉及多个敏感文件，请确保加入 `.gitignore`：

```bash
# 在项目目录创建或更新 .gitignore
cat >> .gitignore << 'EOF'
# 平台 Cookie（包含登录凭证，泄露会导致账号被盗）
bilibili_cookies.txt
douyin_cookies.txt
cookies.txt
*.cookies.txt

# API 密钥
.env
secrets.json
file_ids.json    # 包含已上传文件的 Anthropic file ID

# 原始内容（通常体积大，且可重新生成）
raw/
audio/
audio_tmp/
audio_douyin/
chroma-db/
EOF
```

**脚本中的 Token 不要硬编码**

```python
# 错误写法（不要这样做）
HUGGINGFACE_TOKEN = "hf_xxxxxxxxxxxx"

# 正确写法：从环境变量读取
import os
HUGGINGFACE_TOKEN = os.environ["HUGGINGFACE_TOKEN"]
# 运行前设置：export HUGGINGFACE_TOKEN=hf_xxx
```

---

## Quick Start：5 分钟跑起来

### 启动方式

工具安装后（`pip install -e .`）有三种入口，行为完全不同：

```bash
content-extract                      # 无参数 → 启动全屏 Textual TUI（推荐日常使用）
content-extract --web                # 可选 → 启动 Streamlit 浏览器 UI (localhost:8501)
content-extract init                 # 初始化项目：生成 wiki/DASHBOARD.md、CLAUDE.md、.gitignore
content-extract <type> <url/path>    # 有参数 → 直接在终端执行，不启动任何 UI
```

> **工具尚未实现**（见[计划书 Phase 路线图](./content-extraction-tool-plan.md)）。工具实现前，使用下列各节的独立脚本。脚本与 CLI 命令一一对应，逻辑完全相同。

---

### 场景 A：处理一个技术博客

**工具实现后：**
```bash
content-extract web https://example-blog.com --crawl   # 整站
content-extract web https://example-blog.com/article   # 单页
# 完成后：
claude  # 指令：读取 ./raw/ 下 web__ 前缀文件，生成整体框架分析
```

**工具实现前（独立脚本）：**
```bash
pip install crawl4ai
python crawl_site.py   # 见 1.1 节 crawl_site.py 脚本，修改 SITE_URL 后运行
cd ./my-project && claude
# 指令：读取 ./raw/ 下所有文件，生成一份对这批内容的整体框架分析
```

---

### 场景 B：处理 Bilibili UP 主视频

**工具实现后：**
```bash
content-extract video https://space.bilibili.com/UID/video --limit 50
```

**工具实现前（独立脚本）：**
```bash
pip install yt-dlp faster-whisper
# 见 1.2 节 fetch_bilibili.py 脚本，修改 fetch_bilibili_space("UID") 后运行
# 无字幕视频自动加入 needs_transcription.txt，再运行 transcribe_queue.py
```

---

### 场景 C：处理本地 EPUB

**工具实现后：**
```bash
content-extract ebook ./books/
```

**工具实现前（独立脚本）：**
```bash
pip install ebooklib beautifulsoup4
python extract_epub.py   # 见 1.3 节脚本，修改 Path("./ebooks") 后运行
```

---

### 场景 D：快速了解一个 GitHub 工具仓库

> 详细选项和典型场景见 **1.6 节**（快速了解 / 评估引入 / 深度研究三种模式）。

**工具实现后：**
```bash
content-extract github OWNER/REPO                      # 全量提取
content-extract github OWNER/REPO --only overview,releases  # 仅快速了解
```

**工具实现前（独立脚本）：**
```bash
brew install gh && gh auth login
python -c "
from extract_github import extract_github_repo
extract_github_repo('OWNER/REPO')
"
# 查询：
# '读取 ./raw/github__OWNER__REPO__*.md，告诉我这个工具的核心能力、使用场景和主要限制'
```

---

### 场景 E：随手收藏一篇好文章

**工具实现后：**
```bash
content-extract article https://zhuanlan.zhihu.com/p/xxxxxxxx
content-extract article --batch article_urls.txt
```

**工具实现前（独立脚本）：**
```bash
python -c "
from extract_article import extract_article
extract_article('https://zhuanlan.zhihu.com/p/xxxxxxxx')
"
```


---

## 统一依赖清单

完整安装所有依赖（按需选取）：

```bash
# ── 核心爬取 ──────────────────────────────────
pip install crawl4ai                    # 网页爬取（JS 渲染）
pip install playwright markdownify && playwright install chromium  # 登录墙 + 反爬降级

# ── 视频字幕 ──────────────────────────────────
pip install yt-dlp                      # 全平台视频/字幕下载（Bilibili、抖音等）
brew install ffmpeg                     # 音频处理（Whisper 依赖）

# ── 音频转录 ──────────────────────────────────
pip install faster-whisper              # 本地 Whisper（推荐）

# ── 电子书 ────────────────────────────────────
pip install ebooklib beautifulsoup4     # EPUB 解析
pip install pymupdf4llm                 # PDF 提取（文字型，推荐）
pip install marker-pdf                  # PDF 提取（复杂排版）
pip install pymupdf                     # PDF 类型检测（is_scanned_pdf）
brew install tesseract tesseract-lang   # 扫描版 OCR
pip install pytesseract pdf2image       # tesseract Python 绑定

# ── Office 文件 ───────────────────────────────
pip install python-docx python-pptx    # Word / PowerPoint

# ── RAG 检索 ──────────────────────────────────
pip install chromadb                    # 向量库
pip install sentence-transformers       # 中文 Embedding（BAAI/bge-small-zh-v1.5）
pip install llama-index                 # 大规模 RAG

# ── 特殊场景 ──────────────────────────────────
pip install pyannote.audio              # 说话人分离（访谈视频）
pip install bilibili-api-python         # B站 UP 主视频列表（可选）
brew install gh                         # GitHub 仓库知识提取

# ── UI（content-extract 工具，待实现）────────────────
pip install textual                     # TUI：无参数启动时的默认界面
pip install streamlit                   # Web UI：content-extract --web 启动（可选）
```

> 日常使用只需要前两组：`crawl4ai + yt-dlp + faster-whisper + ffmpeg`，以及 `gh`（GitHub 来源必须）

---

| 日期 | 内容 |
|------|------|
| 2026-06-01 | 整合 llm-wiki-builder、tech-blog-knowledge-extraction、video-knowledge-extraction 三个文档，新增电子书、本地代码、本地文档工程三类来源，重构为三部分结构 |
| 2026-06-01 | 新增 1.6 GitHub 仓库来源（完整脚本：overview/issues/releases/discussions/wiki/代码结构，含按 label 分组 Issues、Releases 自动回退 CHANGELOG、GraphQL Discussions）；原 3.9 节（基础 gh CLI 脚本）升级为完整 1.6 节；安全注意事项从 3.10 重编号为 3.9；更新架构图、工具速查表、Quick Start 场景 D、依赖清单 |
| 2026-06-01 | 新增 1.7 单篇网络文章来源（Jina Reader 通用首选 + Playwright 降级 + 微信公众号专项处理路径 + 浏览器插件辅助方案），更新架构图、CLAUDE.md 前缀表、工具速查表、成本表、Quick Start 场景 E、依赖清单 |
| 2026-06-01 | 新增 2.5 Obsidian 集成（人类消费层）：三步接入流程、DASHBOARD.md Dataview 模板、Graph view gap 发现工作流、分层阅读策略、极简插件清单，更新整体架构图加入 Obsidian 层，更新工具速查表 |
| 2026-06-01 | 全文审查修订：删除头部「整合自」已清理文件的引用；CLAUDE.md 补全 frontmatter 字段规范（platform/subtype/extracted_at）及前缀说明（TypeScript 专项、GitHub subtype 枚举）；修正 changelog 不准确描述；Files API 脚本加模型选择注释；日常依赖提示补 gh；Quick Start 场景 D 加 1.6 节交叉引用 |
| 2026-06-01 | 全文二次审查修订：架构图升级为三层（Layer 1/2/3 明确标注）；Quick Start 改为 CLI-first（工具命令 + 降级脚本双格式）；新增 `content-extract init` 命令；CLAUDE.md 补 `office__` 前缀；frontmatter spec 加 `content_hash` 说明和脚本简化注释；Obsidian 2.5 补 Dataview 安装步骤；Part 2 入口加项目目录约定 |
| 2026-06-12 | 1.7 节重写：抓取方案从「Jina→手动」升级为三条全自动路径（微信用 camoufox stealth browser 95%+ / 头条用 Playwright 90%+ / 通用用 crawl4ai→Jina降级）；删除旧的独立脚本和微信手动指引，改为 content-extract article CLI 命令说明；更新工具速查表、成本表、依赖清单 |

---

*本文档为主文档，持续更新。各来源的实践经验和新工具统一记录于此。*

---

## 关联文档

- **[content-extraction-tool-plan.md](./content-extraction-tool-plan.md)** — 本手册的工程化落地设计，包含 CLI 接口设计、Skill 编排层设计、实现路线图（Phase 0-4）和关键架构决策记录。
