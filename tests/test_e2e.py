import _thread as thread
from http.server import HTTPServer
import http.client
from pathlib import Path
import sqlite3
import time
import unittest

from src.app import URLHandler
from src.shorten import URLShortener
from tests.html_table_parser import HTMLTableParser

test_db_path = Path("tests/data/test.db")
URLHandler.url_shortener = URLShortener(test_db_path)
server_port = 7775


class TestE2E(unittest.TestCase):
    @classmethod
    def setUp(cls):
        with sqlite3.connect(test_db_path) as con:
            cur = con.cursor()
            cur.execute("DELETE FROM url")
            cur.execute("DELETE FROM log")
            con.commit()

    def make_request(
        self, method: str, url: str, body: str, headers: dict
    ) -> http.client.HTTPResponse:
        con = http.client.HTTPConnection("localhost", server_port)
        con.request(method, url, body, headers)
        response = con.getresponse()
        con.close()
        return response

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

        assert res_table_data == ref_table_data

    def test_base_url(self):
        response = self.make_request("GET", "/", "", {})
        assert response.status == 404
        assert response.reason == "Not Found"

    def test_empty_stats(self):
        response = self.make_request("GET", "/stats", "", {})

        with open("tests/data/empty_stats.txt", "r", encoding="utf-8") as f:
            assert response.read().decode() == f.read()

    def test_wrong_short(self):
        response = self.make_request("GET", "/r/notfound", "", {})

        assert response.status == 404
        assert response.reason == "Not Found"

    def test_single_redirect(self):
        response = self.make_request(
            "POST",
            "/shorten",
            '{"url": "https://google.com"}',
            {"Content-Type": "application/json"},
        )
        redirect = response.read().decode()
        response = self.make_request("GET", redirect[14:], "", {})

        assert response.status == 302
        assert response.getheader("Location") == "https://google.com"

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
        assert response.status == 302
        assert response.getheader("Location") == "https://google.com"

        response = self.make_request("GET", short1[14:], "", {})
        assert response.status == 302
        assert response.getheader("Location") == "https://google.com"

        response = self.make_request("GET", short2[14:], "", {})
        assert response.status == 302
        assert response.getheader("Location") == "https://bing.com"

        response = self.make_request("GET", "/stats", "", {})

        self.compare_stats_tables(
            "tests/data/multiple_redirects.txt", response.read().decode()
        )

    # def test_group_by(self):
    #     response = self.make_request(
    #         "POST",
    #         "/shorten",
    #         '{"url": "https://google.com"}',
    #         {"Content-Type": "application/json"},
    #     )
    #     short1 = response.read().decode()
    #     response = self.make_request(
    #         "POST",
    #         "/shorten",
    #         '{"url": "https://bing.com"}',
    #         {"Content-Type": "application/json"},
    #     )
    #     short2 = response.read().decode()

    #     self.make_request("GET", short1[14:], "", {})
    #     self.make_request("GET", short1[14:], "", {})
    #     self.make_request("GET", short2[14:], "", {})

    #     with sqlite3.connect(test_db_path) as con:
    #         cur = con.cursor()
    #         cur.execute(
    #             "EXPLAIN SELECT time AS last_accessed FROM log GROUP BY short_url"
    #         )
    #         res = cur.fetchall()
    #     print(res)


def setUpModule():
    server_address = ("", server_port)
    server = HTTPServer(server_address, URLHandler)
    print("Starting server...")
    thread.start_new_thread(server.serve_forever, ())
    time.sleep(0.5)
    print("Server started.")


if __name__ == "__main__":
    unittest.main()
