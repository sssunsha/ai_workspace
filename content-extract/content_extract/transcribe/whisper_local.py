from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# HuggingFace 在中国大陆被墙，自动走镜像站
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")


@dataclass
class WhisperConfig:
    """faster-whisper 转录配置。"""
    model: str = "medium"
    device: str = "cpu"
    compute_type: str = "int8"
    language: str = "zh"
    vad_filter: bool = True
    no_speech_threshold: float = 0.6


def transcribe(audio_path: Path, cfg: WhisperConfig | None = None) -> str:
    """
    用 faster-whisper 转录音频文件。
    返回带时间戳的文本，格式：'[MM:SS] 转录文本'，每行一句。
    """
    from faster_whisper import WhisperModel

    if cfg is None:
        cfg = WhisperConfig()

    model = WhisperModel(cfg.model, device=cfg.device, compute_type=cfg.compute_type)
    segments, _info = model.transcribe(
        str(audio_path),
        language=cfg.language,
        vad_filter=cfg.vad_filter,
        no_speech_threshold=cfg.no_speech_threshold,
        condition_on_previous_text=False,
    )

    lines = []
    for seg in segments:
        # faster-whisper 内部已按 no_speech_threshold 过滤，此处只跳过空文本
        if seg.text.strip():
            m, s = divmod(int(seg.start), 60)
            lines.append(f"[{m:02d}:{s:02d}] {seg.text.strip()}")

    result = "\n".join(lines)
    try:
        import zhconv
        result = zhconv.convert(result, "zh-hans")
    except ImportError:
        pass
    return result
