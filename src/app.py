from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
from sys import argv

from src.exceptions import AddURLError, PayloadTooLargeError
from src.shorten import URLShortener


class URLHandler(BaseHTTPRequestHandler):
    redirect_path = "/r"
    url_shortener = URLShortener(Path("data/short_url.db"))
    max_body_bytes = 10_000

    def do_GET(self):
        if self.path == "/stats":
            self._send(
                200, self.url_shortener.get_stats_as_html(), content_type="text/html"
            )

        elif self.path.startswith(self.redirect_path + "/"):
            redirect_string = self.path[3:]
            new_url = self.url_shortener.get_redirect(redirect_string)
            if new_url:
                self.send_response(302)
                self.send_header("Location", new_url)
                self.end_headers()
            else:
                self._send(404, "Not Valid")
        else:
            self._send(404, "Not Found")

    def do_POST(self):
        if self.path == "/shorten":
            try:
                post_data = self._read_json_body()
            except PayloadTooLargeError as e:
                self._send(413, str(e))
                return
            except ValueError as e:
                self._send(400, str(e))
                return

            url = post_data.get("url")

            if not isinstance(url, str):
                self._send(400, "'url' must be a string")
                return

            try:
                shortened_url = self.url_shortener.shorten_url(url)
            except AddURLError:
                self._send(500, "Internal server error")
                return

            new_url = f"{self.headers["Host"]}{self.redirect_path}/{shortened_url}"

            self._send(200, new_url)
        else:
            self._send(404, "Not Found")

    def _read_json_body(self) -> dict:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            raise ValueError("Content-Length must be a non-negative integer") from None

        if content_length < 0:
            raise ValueError("Content-Length must be a non-negative integer")
        elif content_length > self.max_body_bytes:
            raise PayloadTooLargeError(
                f"Content-Length must be no more than {self.max_body_bytes} bytes"
            )

        try:
            body = self.rfile.read(content_length).decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("Body must be utf-8 encoded") from None

        try:
            post_data = json.loads(body)
        except json.JSONDecodeError:
            raise ValueError("Body must be in a json object") from None

        if not isinstance(post_data, dict):
            raise ValueError("Body must be in a json object")

        return post_data

    def _send(self, status: int, body: str, content_type: str = "text/plain") -> None:
        encoded_body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", len(encoded_body))
        self.end_headers()
        self.wfile.write(encoded_body)


def run(server_class=HTTPServer, handler_class=URLHandler, port=8000):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    print(f"Server running at http://localhost:{port}...")
    httpd.serve_forever()


if __name__ == "__main__":
    port = 8000
    if len(argv) == 2:
        port = int(argv[1])
    run(port=port)
