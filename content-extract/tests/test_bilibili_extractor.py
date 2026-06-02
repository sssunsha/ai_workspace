from content_extract.extractors.bilibili import _parse_srt, _dedupe_adjacent

_SAMPLE_SRT = """1
00:00:01,000 --> 00:00:03,000
你好世界

2
00:00:03,500 --> 00:00:05,000
你好世界

3
00:00:05,000 --> 00:00:07,000
这是第二句话

4
00:00:07,200 --> 00:00:09,000
这是第二句话，更完整的版本

5
00:00:09,500 --> 00:00:11,000
第三句
"""


def test_parse_srt_count():
    entries = _parse_srt(_SAMPLE_SRT)
    assert len(entries) == 5


def test_parse_srt_timestamp_format():
    entries = _parse_srt(_SAMPLE_SRT)
    ts, _ = entries[0]
    # 格式 [MM:SS]
    assert ts.startswith("[")
    assert ts.endswith("]")
    assert ":" in ts


def test_parse_srt_strips_html_tags():
    srt = "1\n00:00:01,000 --> 00:00:03,000\n<font color='white'>文字</font>\n\n"
    entries = _parse_srt(srt)
    assert entries[0][1] == "文字"


def test_parse_srt_skips_short_blocks():
    # 少于 3 行的块应被跳过
    srt = "1\n00:00:01,000 --> 00:00:03,000\n\n"
    assert _parse_srt(srt) == []


def test_dedupe_adjacent_removes_exact_duplicates():
    entries = [("[00:01]", "你好世界"), ("[00:03]", "你好世界"), ("[00:05]", "第二句")]
    result = _dedupe_adjacent(entries)
    assert len(result) == 2
    assert result[0][1] == "你好世界"
    assert result[1][1] == "第二句"


def test_dedupe_adjacent_replaces_with_longer_prefix():
    # B站滚动字幕：后一行是前一行的扩展版本
    entries = [("[00:05]", "这是第二句话"), ("[00:07]", "这是第二句话，更完整的版本")]
    result = _dedupe_adjacent(entries)
    assert len(result) == 1
    assert result[0][1] == "这是第二句话，更完整的版本"


def test_dedupe_adjacent_keeps_distinct_entries():
    entries = [("[00:01]", "第一句"), ("[00:05]", "第二句"), ("[00:09]", "第三句")]
    result = _dedupe_adjacent(entries)
    assert len(result) == 3


def test_dedupe_adjacent_empty():
    assert _dedupe_adjacent([]) == []


def test_full_pipeline_deduplication():
    # 完整流水线：parse → dedupe，模拟真实 B站字幕
    entries = _parse_srt(_SAMPLE_SRT)
    deduped = _dedupe_adjacent(entries)
    # 原始 5 条：重复1条+滚动1条，去重后剩 3 条
    assert len(deduped) == 3
