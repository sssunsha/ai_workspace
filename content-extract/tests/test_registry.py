import json
from pathlib import Path
import pytest
from content_extract.registry import Registry


def test_new_registry_is_empty(tmp_path):
    reg = Registry(tmp_path / ".processed.json")
    assert reg.get_by_status("done") == []


def test_is_processed_false_for_unknown(tmp_path):
    reg = Registry(tmp_path / ".processed.json")
    assert reg.is_processed("https://example.com") is False


def test_mark_and_is_processed(tmp_path):
    reg = Registry(tmp_path / ".processed.json")
    reg.mark("https://example.com", "done", output_file="web__example.md")
    assert reg.is_processed("https://example.com") is True


def test_get_by_status(tmp_path):
    reg = Registry(tmp_path / ".processed.json")
    reg.mark("https://a.com", "done", output_file="a.md")
    reg.mark("https://b.com", "needs_transcription", output_file="b.md")
    reg.mark("https://c.com", "failed", error="网络错误")
    assert len(reg.get_by_status("done")) == 1
    assert len(reg.get_by_status("needs_transcription")) == 1
    assert len(reg.get_by_status("failed")) == 1


def test_save_and_reload(tmp_path):
    path = tmp_path / ".processed.json"
    reg = Registry(path)
    reg.mark("https://example.com", "done", output_file="test.md", content_hash="abc12345")
    reg.save()

    reg2 = Registry(path)
    assert reg2.is_processed("https://example.com")
    entries = reg2.get_by_status("done")
    assert entries[0]["content_hash"] == "abc12345"


def test_mark_updates_existing(tmp_path):
    reg = Registry(tmp_path / ".processed.json")
    reg.mark("https://example.com", "needs_transcription", output_file="test.md")
    reg.mark("https://example.com", "done")
    assert reg.is_processed("https://example.com")
    entries = reg.get_by_status("done")
    assert len(entries) == 1


def test_loads_existing_file(tmp_path):
    path = tmp_path / ".processed.json"
    data = {
        "https://example.com": {
            "status": "done",
            "output_file": "test.md",
            "extracted_at": "2026-06-01T10:00:00",
            "content_hash": "deadbeef",
            "retry_count": 0,
            "error": None,
        }
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    reg = Registry(path)
    assert reg.is_processed("https://example.com")
