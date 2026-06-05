from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any

from .base import BaseExtractor, ExtractConfig
from ..registry import Registry
from ..utils.frontmatter import write_frontmatter_file


_BILIBILI_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com",
}


def _youtube_dl_class() -> Any:
    try:
        from yt_dlp import YoutubeDL
        return YoutubeDL
    except ImportError as exc:
        raise RuntimeError("yt-dlp 未安装，请运行: pip install yt-dlp") from exc


def _bv_from_url(url: str) -> str | None:
    """从 URL 中提取 BV 号，失败返回 None。"""
    m = re.search(r"/(BV[a-zA-Z0-9]+)", url)
    return m.group(1) if m else None


def _extract_info(url: str, cookie_file: str | None) -> dict:
    ydl_cls = _youtube_dl_class()
    opts: dict[str, Any] = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "http_headers": _BILIBILI_HEADERS,
    }
    if cookie_file:
        opts["cookiefile"] = cookie_file
    try:
        with ydl_cls(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return ydl.sanitize_info(info) or {}
    except Exception as e:
        print(f"[警告] yt-dlp 获取元数据失败: {e}")
        return {}


def _download_subtitles(url: str, cookie_file: str | None, tmp_dir: Path) -> list[Path]:
    """用 yt-dlp Python API 下载 SRT 字幕到 tmp_dir，返回 .srt 文件列表。"""
    ydl_cls = _youtube_dl_class()
    opts: dict[str, Any] = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["zh-Hans", "zh"],
        "convertsubtitles": "srt",
        "quiet": True,
        "no_warnings": True,
        "outtmpl": str(tmp_dir / "%(id)s.%(ext)s"),
        "http_headers": _BILIBILI_HEADERS,
    }
    if cookie_file:
        opts["cookiefile"] = cookie_file
    try:
        with ydl_cls(opts) as ydl:
            ydl.download([url])
    except Exception:
        pass
    return list(tmp_dir.glob("*.srt"))


def _parse_srt(srt_text: str) -> list[tuple[str, str]]:
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
            if entry and entry.get("output_file"):
                return output_dir / entry["output_file"]

        cookie_file = self._resolve_cookie()
        self.log(f"[Bilibili] 获取元数据: {source}")
        meta = _extract_info(source, cookie_file)

        # 元数据获取失败时用 BV 号作为 fallback id，避免多视频覆盖同一 unknown.md
        vid = meta.get("id") or _bv_from_url(source) or "unknown"
        title = meta.get("title") or vid
        transcript = self._get_subtitle(source, vid, cookie_file)

        body = self._build_body(meta, title, transcript)
        slug = re.sub(r'[/\\:*?"<>|]', "-", title[:40]).replace(" ", "_")
        filename = f"bili__{vid}__{slug}.md"
        out_path = output_dir / filename

        content_hash = write_frontmatter_file(
            path=out_path, content=body, source=source, type="video", platform="bilibili",
        )

        if transcript:
            reg.mark(source, "done", output_file=filename, content_hash=content_hash)
        else:
            reg.mark(source, "needs_transcription", output_file=filename, content_hash=content_hash)
            self._append_needs_transcription(output_dir, source)

        self.log(f"[Bilibili] {title} → {filename}")
        return out_path

    def _resolve_cookie(self) -> str | None:
        cookie = self.config.cookies.get("bilibili")
        if not cookie:
            return None
        path = Path(cookie).expanduser()
        if not path.exists():
            self.log("[警告] Bilibili Cookie 文件不存在，尝试无 Cookie 模式（AI 字幕可能不可用）")
            return None
        return str(path)

    def _build_body(self, meta: dict, title: str, transcript: str | None) -> str:
        duration = int(meta.get("duration") or 0)
        chapters = meta.get("chapters") or []
        lines = [
            f"# {title}\n",
            f"- **UP主**: {meta.get('uploader', '')}",
            f"- **时长**: {duration // 60}:{duration % 60:02d}",
        ]
        if chapters:
            lines.append("\n## 章节结构")
            for ch in chapters:
                ts = int(ch.get("start_time", 0))
                m, s = divmod(ts, 60)
                lines.append(f"- [{m:02d}:{s:02d}] {ch['title']}")
        lines.append("\n## 字幕全文")
        lines.append(transcript if transcript else "*无字幕，待 Whisper 转录*")
        return "\n".join(lines)

    def _append_needs_transcription(self, output_dir: Path, source: str) -> None:
        needs_file = output_dir / "needs_transcription.txt"
        existing = needs_file.read_text(encoding="utf-8").splitlines() if needs_file.exists() else []
        if source not in existing:
            with open(needs_file, "a", encoding="utf-8") as f:
                f.write(f"{source}\n")

    def _get_subtitle(self, url: str, video_id: str, cookie_file: str | None) -> str | None:
        tmp_dir = Path(tempfile.mkdtemp(prefix=f"bili_{video_id}_"))
        try:
            srt_files = _download_subtitles(url, cookie_file, tmp_dir)
            if not srt_files:
                return None
            entries = _parse_srt(srt_files[0].read_text(encoding="utf-8"))
            entries = _dedupe_adjacent(entries)
            return "\n".join(f"{ts} {text}" for ts, text in entries)
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
