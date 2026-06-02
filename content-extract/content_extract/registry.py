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

    def remove(self, source: str) -> None:
        """删除指定来源的记录并持久化。"""
        self._data.pop(source, None)
        self.save()

    def remove_by_output_prefix(self, prefix: str) -> int:
        """删除所有 output_file 以 prefix/ 开头的记录，返回删除数量。"""
        to_remove = [
            k for k, v in self._data.items()
            if v.get("output_file", "").startswith(prefix + "/") or v.get("output_file", "") == prefix
        ]
        for k in to_remove:
            del self._data[k]
        if to_remove:
            self.save()
        return len(to_remove)

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
