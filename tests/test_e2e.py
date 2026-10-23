import _thread as thread
from http.server import HTTPServer
import http.client
from pathlib import Path
import sqlite3
import time
import unittest
from unittest import mock

from src.app import URLHandler
from src.exceptions import AddURLError
from src.shorten import URLShortener
from tests.html_table_parser import HTMLTableParser

test_db_path = Path("tests/data/test.db")
URLHandler.url_shortener = URLShortener(test_db_path)
server_port = 7775


class TestE2E(unittest.TestCase):
    def setUp(self):
        with sqlite3.connect(test_db_path) as con:
            cur = con.cursor()
            cur.execute("DELETE FROM url")
            cur.execute("DELETE FROM log")
            con.commit()

    def make_request(
        self, method: str, url: str, body: str | bytes, headers: dict
    ) -> http.client.HTTPResponse:
        con = http.client.HTTPConnection("localhost", server_port)
        con.request(method, url, body, headers)
        response = con.getresponse()
        con.close()
        return response

    def shorten(
        self, body: str | bytes, headers: dict | None = None
    ) -> http.client.HTTPResponse:
        return self.make_request(
            "POST",
            "/shorten",
            body,
            {"Content-Type": "application/json", **(headers or {})},
        )

    def compare_stats_tables(self, ref_path: str, res_html: str):
        parser = HTMLTableParser()
        parser.feed(res_html)
        res_table_data = parser.table_data

        with open(ref_path, "r", encoding="utf-8") as f:
            ref_html = f.read()
        parser.feed(ref_html)
        ref_table_data = parser.table_data

        ## remove time created and short_url
        res_table_data["Time created"] = []
        ref_table_data["Time created"] = []
        res_table_data["Short URL"] = []
        ref_table_data["Short URL"] = []

        self.assertEqual(res_table_data, ref_table_data)

    def test_base_url(self):
        response = self.make_request("GET", "/", "", {})
        self.assertEqual(response.status, 404)
        self.assertEqual(response.reason, "Not Found")

    def test_empty_stats(self):
        response = self.make_request("GET", "/stats", "", {})

        with open("tests/data/empty_stats.txt", "r", encoding="utf-8") as f:
            self.assertEqual(response.read().decode(), f.read())

    def test_wrong_short(self):
        response = self.make_request("GET", "/r/notfound", "", {})

        self.assertEqual(response.status, 404)
        self.assertEqual(response.reason, "Not Found")

    def test_single_redirect(self):
        response = self.make_request(
            "POST",
            "/shorten",
            '{"url": "https://google.com"}',
            {"Content-Type": "application/json"},
        )
        redirect = response.read().decode()
        response = self.make_request("GET", redirect[14:], "", {})

        self.assertEqual(response.status, 302)
        self.assertEqual(response.getheader("Location"), "https://google.com")

    def test_single_run(self):
        response = self.make_request(
            "POST",
            "/shorten",
            '{"url": "https://google.com"}',
            {"Content-Type": "application/json"},
        )
        redirect = response.read().decode()
        response = self.make_request("GET", redirect[14:], "", {})
        response = self.make_request("GET", "/stats", "", {})

        self.compare_stats_tables(
            "tests/data/single_redirect.txt", response.read().decode()
        )

    def test_multiple_runs(self):
        response = self.make_request(
            "POST",
            "/shorten",
            '{"url": "https://google.com"}',
            {"Content-Type": "application/json"},
        )
        short1 = response.read().decode()
        response = self.make_request(
            "POST",
            "/shorten",
            '{"url": "https://bing.com"}',
            {"Content-Type": "application/json"},
        )
        short2 = response.read().decode()

        response = self.make_request("GET", short1[14:], "", {})
        self.assertEqual(response.status, 302)
        self.assertEqual(response.getheader("Location"), "https://google.com")

        response = self.make_request("GET", short1[14:], "", {})
        self.assertEqual(response.status, 302)
        self.assertEqual(response.getheader("Location"), "https://google.com")

        response = self.make_request("GET", short2[14:], "", {})
        self.assertEqual(response.status, 302)
        self.assertEqual(response.getheader("Location"), "https://bing.com")

        response = self.make_request("GET", "/stats", "", {})

        self.compare_stats_tables(
            "tests/data/multiple_redirects.txt", response.read().decode()
        )

    def test_shorten_bad_body(self):
        bad_bodies = [
            b"",
            b"not json",
            b"\xff\xfe",
            b"[1]",
            b"5",
            b'"url"',
            b"{}",
            b'{"url": null}',
            b'{"url": 5}',
            b'{"url": ["https://google.com"]}',
        ]
        for body in bad_bodies:
            with self.subTest(body=body):
                response = self.shorten(body)
                self.assertEqual(response.status, 400)

        # server should still be working after bad requests
        response = self.shorten('{"url": "https://google.com"}')
        self.assertEqual(response.status, 200)

    def test_shorten_bad_content_length(self):
        cases = [("abc", 400), ("-1", 400), (str(URLHandler.max_body_bytes + 1), 413)]
        for content_length, expected_status in cases:
            with self.subTest(content_length=content_length):
                response = self.shorten(
                    '{"url": "https://google.com"}',
                    {"Content-Length": content_length},
                )
                self.assertEqual(response.status, expected_status)

        self.assertEqual(self.count_rows("url"), 0)

    def test_shorten_add_url_error(self):
        with mock.patch.object(
            URLHandler.url_shortener,
            "shorten_url",
            side_effect=AddURLError("Failed to make new shortened url"),
        ):
            response = self.shorten('{"url": "https://google.com"}')
        self.assertEqual(response.status, 500)

        response = self.shorten('{"url": "https://google.com"}')
        self.assertEqual(response.status, 200)

    def test_stats_non_ascii(self):
        # http.client sends str bodies as latin-1, so encode as utf-8 explicitly
        response = self.shorten('{"url": "https://example.com/café"}'.encode("utf-8"))
        self.assertEqual(response.status, 200)

        response = self.make_request("GET", "/stats", "", {})
        page = response.read().decode()

        # a Content-Length counted in characters rather than bytes truncates the page
        self.assertTrue(page.endswith("</html>"))
        self.assertIn("https://example.com/café", page)

    def count_rows(self, table: str) -> int:
        with sqlite3.connect(test_db_path) as con:
            return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def setUpModule():
    server_address = ("", server_port)
    server = HTTPServer(server_address, URLHandler)
    print("Starting server...")
    thread.start_new_thread(server.serve_forever, ())
    time.sleep(0.5)
    print("Server started.")


if __name__ == "__main__":
    unittest.main()
