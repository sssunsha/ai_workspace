import pytest
from content_extract.utils.lang import detect_lang, should_follow


# ── detect_lang：路径前缀 ────────────────────────────────────────────────

def test_detect_zh_path():
    assert detect_lang("https://example.com/zh/blog/article") == "zh"

def test_detect_zh_cn_path():
    assert detect_lang("https://example.com/zh-CN/blog/") == "zh"

def test_detect_zh_tw_path():
    assert detect_lang("https://example.com/zh-TW/article") == "zh"

def test_detect_zh_hans_path():
    assert detect_lang("https://example.com/zh-Hans/page") == "zh"

def test_detect_en_path():
    assert detect_lang("https://example.com/en/blog/article") == "en"

def test_detect_en_us_path():
    assert detect_lang("https://example.com/en-US/blog/") == "en"

def test_detect_unsupported_path_raises():
    with pytest.raises(ValueError, match="不支持的语言"):
        detect_lang("https://example.com/fr/blog/article")

def test_detect_ar_path_raises():
    with pytest.raises(ValueError, match="不支持的语言"):
        detect_lang("https://feelgoodpal.com/ar/blog/article")


# ── detect_lang：子域名 ──────────────────────────────────────────────────

def test_detect_zh_subdomain():
    assert detect_lang("https://zh.example.com/blog/") == "zh"

def test_detect_en_subdomain():
    assert detect_lang("https://en.example.com/blog/") == "en"

def test_detect_unsupported_subdomain_raises():
    with pytest.raises(ValueError, match="不支持的语言"):
        detect_lang("https://fr.example.com/blog/")

def test_safe_subdomain_www_no_error():
    # www 是安全子域名，不触发语言检测，无语言信号默认英文
    assert detect_lang("https://www.example.com/blog/") == "en"

def test_safe_subdomain_api_no_error():
    assert detect_lang("https://api.example.com/v1/") == "en"


# ── detect_lang：Query 参数 ──────────────────────────────────────────────

def test_detect_zh_query_lang():
    assert detect_lang("https://example.com/blog/?lang=zh") == "zh"

def test_detect_en_query_language():
    assert detect_lang("https://example.com/?language=en-US") == "en"

def test_detect_zh_query_locale():
    assert detect_lang("https://example.com/?locale=zh-CN") == "zh"

def test_detect_unsupported_query_raises():
    with pytest.raises(ValueError, match="不支持的语言"):
        detect_lang("https://example.com/?lang=ja")


# ── detect_lang：无语言信号默认英文 ─────────────────────────────────────

def test_detect_no_signal_defaults_to_en():
    assert detect_lang("https://example.com/blog/article") == "en"

def test_detect_root_defaults_to_en():
    assert detect_lang("https://example.com/") == "en"


# ── should_follow ────────────────────────────────────────────────────────

def test_should_follow_same_lang_zh():
    assert should_follow("https://example.com/zh/blog/article", "zh") is True

def test_should_follow_same_lang_en():
    assert should_follow("https://example.com/en/blog/article", "en") is True

def test_should_not_follow_different_lang():
    # 入口是 zh，链接是 en → 不跟进
    assert should_follow("https://example.com/en/blog/article", "zh") is False

def test_should_not_follow_unsupported_lang():
    # 不支持的语言（阿拉伯语）→ 静默跳过，不抛异常
    assert should_follow("https://feelgoodpal.com/ar/blog/article", "zh") is False

def test_should_not_follow_fr_when_seed_is_en():
    assert should_follow("https://example.com/fr/page", "en") is False

def test_should_follow_no_lang_signal_treated_as_en():
    # 无语言信号默认英文，入口也是英文 → 跟进
    assert should_follow("https://example.com/blog/article", "en") is True

def test_should_not_follow_no_lang_signal_when_seed_is_zh():
    # 无语言信号默认英文，入口是中文 → 不跟进
    assert should_follow("https://example.com/blog/article", "zh") is False
