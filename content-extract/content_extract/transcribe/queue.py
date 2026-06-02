from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from .whisper_local import WhisperConfig, transcribe
from ..registry import Registry


def process_queue(
    output_dir: Path,
    model: str = "medium",
    device: str = "cpu",
    compute_type: str = "int8",
) -> None:
    """
    消费转录队列：
    1. 读取 registry 中 needs_transcription 状态的条目
    2. 兼容读取旧格式 needs_transcription.txt
    3. 下载音频 → Whisper 转录 → 更新 raw 文件 → 标记 done
    """
    reg = Registry(output_dir / ".processed.json")
    cfg = WhisperConfig(model=model, device=device, compute_type=compute_type)

    # 从 registry 获取待处理列表
    pending = reg.get_by_status("needs_transcription")

    # 兼容旧格式 needs_transcription.txt
    needs_file = output_dir / "needs_transcription.txt"
    if needs_file.exists():
        existing_sources = {e["source"] for e in pending}
        for line in needs_file.read_text(encoding="utf-8").splitlines():
            url = line.strip()
            if url and url not in existing_sources:
                pending.append({"source": url, "output_file": None})

    if not pending:
        print("转录队列为空，无需处理。")
        return

    print(f"待转录: {len(pending)} 个视频")

    for entry in pending:
        url = entry["source"]
        _transcribe_one(url, entry.get("output_file"), output_dir, reg, cfg)

    # 清空旧格式队列文件
    if needs_file.exists():
        needs_file.write_text("", encoding="utf-8")


def _transcribe_one(
    url: str,
    output_file: str | None,
    output_dir: Path,
    reg: Registry,
    cfg: WhisperConfig,
) -> None:
    # 用 yt-dlp --print id 获取视频 ID，避免手工解析不同平台 URL
    r_id = subprocess.run(
        ["yt-dlp", "--skip-download", "--print", "id", url],
        capture_output=True,
        text=True,
    )
    if r_id.returncode != 0:
        print(f"  [失败] 无法获取 ID: {url}")
        reg.mark(url, "failed", error="yt-dlp 获取 ID 失败")
        return

    vid = r_id.stdout.strip()
    audio_path = Path(tempfile.gettempdir()) / f"transcribe_{vid}.mp3"

    print(f"  下载音频: {url}")
    r_dl = subprocess.run(
        ["yt-dlp", "-x", "--audio-format", "mp3", "--audio-quality", "5",
         "-o", str(audio_path), url],
        capture_output=True,
    )
    if r_dl.returncode != 0 or not audio_path.exists():
        print(f"  [失败] 音频下载失败: {url}")
        reg.mark(url, "failed", error="音频下载失败")
        return

    print(f"  转录中（模型: {cfg.model}，设备: {cfg.device}）...")
    try:
        transcript = transcribe(audio_path, cfg)
    except Exception as e:
        print(f"  [失败] 转录出错: {e}")
        reg.mark(url, "failed", error=str(e))
        return
    finally:
        audio_path.unlink(missing_ok=True)

    # 找到对应的 raw 文件（优先按 output_file，回退按 video ID 匹配文件名）
    raw_file = None
    if output_file:
        candidate = output_dir / output_file
        if candidate.exists():
            raw_file = candidate
    if raw_file is None:
        for f in output_dir.glob("*.md"):
            if vid in f.name:
                raw_file = f
                break

    if raw_file and raw_file.exists():
        content = raw_file.read_text(encoding="utf-8")
        content = content.replace("*无字幕，待 Whisper 转录*", transcript)
        raw_file.write_text(content, encoding="utf-8")
        print(f"  → 已更新 {raw_file.name}")
        reg.mark(url, "done", output_file=raw_file.name)
    else:
        print(f"  [警告] 找不到对应 raw 文件，video_id={vid}")
        reg.mark(url, "done", output_file=None)
