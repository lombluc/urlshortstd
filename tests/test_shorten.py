from pathlib import Path
import sqlite3
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
