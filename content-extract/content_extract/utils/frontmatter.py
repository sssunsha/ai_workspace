import hashlib
from datetime import datetime, timezone
from pathlib import Path


def write_frontmatter_file(
    path: Path,
    content: str,
    source: str,
    type: str,
    platform: str | None = None,
    subtype: str | None = None,
    extra_fields: dict | None = None,
) -> str:
    """写入统一 frontmatter + 正文到文件。自动填写 extracted_at 和 content_hash。

    返回 content_hash（SHA256 前 8 位），供调用方写入 registry。
    """
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:8]
    extracted_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    lines = ["---"]
    lines.append(f"source: {source}")
    lines.append(f"type: {type}")
    if platform:
        lines.append(f"platform: {platform}")
    if subtype:
        lines.append(f"subtype: {subtype}")
    lines.append(f"extracted_at: {extracted_at}")
    lines.append(f"content_hash: {content_hash}")
    if extra_fields:
        for k, v in extra_fields.items():
            lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    lines.append(content)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return content_hash
