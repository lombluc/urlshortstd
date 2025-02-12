import _thread as thread
from http.server import HTTPServer
import http.client
from pathlib import Path
import sqlite3
import time
import unittest
from urllib.parse import urlencode

from src.app import URLHandler
from src.shorten import URLShortener

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

    def test_redirect(self):
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


# # start the server in a background thread
# thread.start_new_thread(start_server, ())

if __name__ == "__main__":
    server_address = ("", server_port)
    server = HTTPServer(server_address, URLHandler)
    print("Starting server...")
    thread.start_new_thread(server.serve_forever, ())
    time.sleep(0.5)
    print("Server started.")
    unittest.main()
