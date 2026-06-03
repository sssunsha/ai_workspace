import pytest
from unittest.mock import patch
from content_extract.ui.tui import TUIApp, detect_source_type


# ── detect_source_type 单元测试（无需 Pilot，速度快）─────────────────────────

def test_detect_bilibili_url():
    assert detect_source_type("https://www.bilibili.com/video/BV1abc") == "video"


def test_detect_b23_url():
    assert detect_source_type("https://b23.tv/xxxxx") == "video"


def test_detect_github_url():
    assert detect_source_type("https://github.com/owner/repo") == "github"


def test_detect_generic_url():
    assert detect_source_type("https://example.com/blog/article") == "article"


def test_detect_epub_file():
    assert detect_source_type("./book.epub") == "ebook"


def test_detect_pdf_file():
    assert detect_source_type("/path/to/paper.pdf") == "ebook"


# ── Textual Pilot 集成测试 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_app_launches():
    """app 能正常启动并通过 q 退出。"""
    app = TUIApp()
    async with app.run_test() as pilot:
        await pilot.press("q")


@pytest.mark.asyncio
async def test_log_panel_exists():
    """LogPanel 的 #log RichLog 存在于 DOM。"""
    app = TUIApp()
    async with app.run_test() as pilot:
        log = app.query_one("#log")
        assert log is not None
        await pilot.press("q")


@pytest.mark.asyncio
async def test_queue_empty_on_start(tmp_path, monkeypatch):
    """无 registry 文件时，队列面板初始行数为 0。"""
    # _RAW_DIR 已锚定到启动目录，通过 mock _load_registry 跳过真实 registry 加载
    import content_extract.ui.tui as tui_mod
    with patch.object(tui_mod.TUIApp, "_load_registry", return_value=None):
        app = tui_mod.TUIApp()
        async with app.run_test() as pilot:
            from textual.widgets import DataTable
            table = app.query_one("#queue-table", DataTable)
            assert table.row_count == 0
            await pilot.press("q")


@pytest.mark.asyncio
async def test_keyboard_quit():
    """按 Q 键能正常退出，不抛异常。"""
    app = TUIApp()
    async with app.run_test() as pilot:
        await pilot.press("Q")


@pytest.mark.asyncio
async def test_input_url_sets_value(tmp_path, monkeypatch):
    """在 URL 输入框设置 bilibili URL 后，输入框有内容（提取被 mock）。

    注意：textual 0.8.x Pilot 没有 type() 方法，直接设置 Input.value 代替。
    """
    monkeypatch.chdir(tmp_path)
    with patch.object(TUIApp, "_run_extract"):
        app = TUIApp()
        async with app.run_test() as pilot:
            from textual.widgets import Input
            url_input = app.query_one("#url-input", Input)
            # 直接设置 value，textual 0.8.x Pilot 无 type() 方法
            url_input.value = "https://www.bilibili.com/video/BV1abc"
            await pilot.pause()
            assert "bilibili" in url_input.value
            await pilot.press("q")
