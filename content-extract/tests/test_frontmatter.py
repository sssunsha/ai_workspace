import hashlib
from pathlib import Path
import pytest
from content_extract.utils.frontmatter import write_frontmatter_file


def test_write_creates_file(tmp_path):
    out = tmp_path / "test.md"
    write_frontmatter_file(
        path=out,
        content="正文内容",
        source="https://example.com",
        type="web",
    )
    assert out.exists()


def test_frontmatter_contains_required_fields(tmp_path):
    out = tmp_path / "test.md"
    write_frontmatter_file(
        path=out,
        content="正文内容",
        source="https://example.com",
        type="web",
    )
    text = out.read_text(encoding="utf-8")
    assert "source: https://example.com" in text
    assert "type: web" in text
    assert "extracted_at:" in text
    assert "content_hash:" in text


def test_frontmatter_platform_field(tmp_path):
    out = tmp_path / "test.md"
    write_frontmatter_file(
        path=out,
        content="视频内容",
        source="https://youtube.com/watch?v=abc",
        type="video",
        platform="youtube",
    )
    text = out.read_text(encoding="utf-8")
    assert "platform: youtube" in text


def test_frontmatter_content_hash(tmp_path):
    out = tmp_path / "test.md"
    content = "测试内容"
    write_frontmatter_file(path=out, content=content, source="https://example.com", type="web")
    expected_hash = hashlib.sha256(content.encode()).hexdigest()[:8]
    text = out.read_text(encoding="utf-8")
    assert f"content_hash: {expected_hash}" in text


def test_frontmatter_extra_fields(tmp_path):
    out = tmp_path / "test.md"
    write_frontmatter_file(
        path=out,
        content="内容",
        source="https://example.com",
        type="web",
        extra_fields={"custom_key": "custom_value"},
    )
    text = out.read_text(encoding="utf-8")
    assert "custom_key: custom_value" in text


def test_returns_content_hash(tmp_path):
    out = tmp_path / "test.md"
    content = "返回值测试"
    returned = write_frontmatter_file(path=out, content=content, source="https://example.com", type="web")
    expected = hashlib.sha256(content.encode()).hexdigest()[:8]
    assert returned == expected

