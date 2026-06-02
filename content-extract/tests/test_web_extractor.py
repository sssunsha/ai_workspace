from content_extract.extractors.web import _url_to_subfolder, _url_to_page_filename


# ── _url_to_subfolder ─────────────────────────────────────────────────────

def test_subfolder_with_path():
    assert _url_to_subfolder("https://feelgoodpal.com/zh/blog/") == "feelgoodpal-com__zh__blog"


def test_subfolder_root():
    assert _url_to_subfolder("https://example.com/") == "example-com"


def test_subfolder_single_segment():
    assert _url_to_subfolder("https://example.com/blog") == "example-com__blog"


def test_subfolder_deep_path():
    assert _url_to_subfolder("https://example.com/a/b/c") == "example-com__a__b__c"


# ── _url_to_page_filename ─────────────────────────────────────────────────

def test_page_filename_seed_itself_is_index():
    seed = "https://feelgoodpal.com/zh/blog/"
    assert _url_to_page_filename(seed, seed) == "index.md"


def test_page_filename_seed_without_trailing_slash():
    seed = "https://example.com/blog"
    assert _url_to_page_filename(seed, seed) == "index.md"


def test_page_filename_child_page():
    seed = "https://feelgoodpal.com/zh/blog/"
    page = "https://feelgoodpal.com/zh/blog/creatine-and-cognition/"
    assert _url_to_page_filename(page, seed) == "creatine-and-cognition.md"


def test_page_filename_nested_child():
    seed = "https://example.com/blog/"
    page = "https://example.com/blog/category/article"
    assert _url_to_page_filename(page, seed) == "category__article.md"


def test_page_filename_outside_seed_path():
    seed = "https://feelgoodpal.com/zh/blog/"
    page = "https://feelgoodpal.com/zh/"
    assert _url_to_page_filename(page, seed) == "zh.md"


def test_page_filename_root_outside_seed():
    seed = "https://example.com/blog/"
    page = "https://example.com/"
    assert _url_to_page_filename(page, seed) == "index.md"


def test_page_filename_query_appends_hash():
    seed = "https://feelgoodpal.com/zh/blog/"
    page1 = "https://feelgoodpal.com/zh/blog/?filter=diet"
    page2 = "https://feelgoodpal.com/zh/blog/?filter=keto"
    name1 = _url_to_page_filename(page1, seed)
    name2 = _url_to_page_filename(page2, seed)
    assert name1 != name2
    assert name1.endswith(".md")


def test_page_filename_same_url_stable():
    seed = "https://example.com/blog/"
    page = "https://example.com/blog/article?v=1"
    assert _url_to_page_filename(page, seed) == _url_to_page_filename(page, seed)
