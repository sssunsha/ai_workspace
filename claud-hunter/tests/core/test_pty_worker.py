import unittest
from app.core.pty_worker import strip_ansi


class TestStripAnsi(unittest.TestCase):
    def test_strip_ansi_removes_color_codes(self):
        self.assertEqual(strip_ansi("\x1b[32mhello\x1b[0m"), "hello")

    def test_strip_ansi_removes_cursor_movement(self):
        self.assertEqual(strip_ansi("\x1b[2Kfoo"), "foo")

    def test_strip_ansi_leaves_plain_text_unchanged(self):
        self.assertEqual(strip_ansi("hello world"), "hello world")

    def test_strip_ansi_preserves_newlines(self):
        self.assertEqual(strip_ansi("line1\nline2"), "line1\nline2")

    def test_strip_ansi_handles_empty_string(self):
        self.assertEqual(strip_ansi(""), "")


if __name__ == "__main__":
    unittest.main()
