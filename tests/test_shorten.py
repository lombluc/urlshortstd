from pathlib import Path
import sqlite3
import string
import tempfile
import unittest
from unittest import mock

from src.shorten import URLShortener


class TestURLShortener(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.shortener = URLShortener(Path(self.tmp_dir.name) / "test.db")

    def tearDown(self):
        self.tmp_dir.cleanup()

    def count_rows(self, table: str) -> int:
        with self.shortener._connect() as con:
            return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def test_foreign_key_enforced(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with self.shortener._connect() as con:
                con.execute(
                    "INSERT INTO log VALUES(?, ?)",
                    ("2026-01-01T00:00:00+00:00", "notfound"),
                )

    def test_rollback_on_exception(self):
        with self.assertRaises(RuntimeError):
            with self.shortener._connect() as con:
                con.execute(
                    "INSERT INTO url VALUES(?, ?, ?)",
                    ("abc123", "https://google.com", "2026-01-01T00:00:00+00:00"),
                )
                raise RuntimeError("fail after insert")

        self.assertEqual(self.count_rows("url"), 0)

    def test_redirect_logs_hit(self):
        short_url = self.shortener.shorten_url("https://google.com")

        self.assertEqual(self.shortener.get_redirect(short_url), "https://google.com")
        self.assertEqual(self.count_rows("log"), 1)

    def test_unknown_redirect_not_logged(self):
        self.assertIsNone(self.shortener.get_redirect("notfound"))
        self.assertEqual(self.count_rows("log"), 0)

    def test_short_url_format(self):
        short_url = self.shortener.shorten_url("https://google.com")

        self.assertEqual(len(short_url), 6)
        self.assertTrue(set(short_url) <= set(string.ascii_letters + string.digits))

    def test_collision_retries(self):
        codes = [list("aaaaaa"), list("aaaaaa"), list("bbbbbb")]
        with mock.patch("src.shorten.random.choices", side_effect=codes):
            first = self.shortener.shorten_url("https://google.com")
            second = self.shortener.shorten_url("https://bing.com")

        self.assertEqual(first, "aaaaaa")
        self.assertEqual(second, "bbbbbb")
        self.assertEqual(self.shortener.get_redirect("aaaaaa"), "https://google.com")
        self.assertEqual(self.shortener.get_redirect("bbbbbb"), "https://bing.com")
        self.assertEqual(self.count_rows("url"), 2)

    def test_collision_gives_up(self):
        with mock.patch(
            "src.shorten.random.choices", return_value=list("aaaaaa")
        ) as choices:
            self.shortener.shorten_url("https://google.com")
            with self.assertRaisesRegex(Exception, "Failed to make new shortened url"):
                self.shortener.shorten_url("https://bing.com")

        # 1 successful attempt, then 10 colliding attempts before giving up
        self.assertEqual(choices.call_count, 11)
        self.assertEqual(self.count_rows("url"), 1)

    def test_stats_escapes_html(self):
        url = 'https://example.com/"><script>alert(1)</script>'
        self.shortener.shorten_url(url)

        page = self.shortener.get_stats_as_html()

        self.assertNotIn("<script>", page)
        self.assertIn(
            "https://example.com/&quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt;", page
        )


if __name__ == "__main__":
    unittest.main()
