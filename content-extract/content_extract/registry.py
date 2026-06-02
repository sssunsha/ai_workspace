import json
from datetime import datetime, timezone
from pathlib import Path


class Registry:
    """管理已处理来源的状态，持久化到 .processed.json。"""

    def __init__(self, path: Path):
        self._path = path
        self._data: dict[str, dict] = {}
        if path.exists():
            self._data = json.loads(path.read_text(encoding="utf-8"))

    def is_processed(self, source: str) -> bool:
        return source in self._data

    def mark(self, source: str, status: str, **kwargs) -> None:
        """写入或更新记录。status: done / needs_transcription / failed。"""
        existing = self._data.get(source, {"retry_count": 0, "error": None})
        existing.update({"status": status, "extracted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")})
        existing.update(kwargs)
        self._data[source] = existing
        self.save()

    def get_by_status(self, status: str) -> list[dict]:
        return [{"source": k, **v} for k, v in self._data.items() if v.get("status") == status]

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
