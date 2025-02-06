from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
from sys import argv

from shorten import URLShortener


url_shortener = URLShortener(Path("data/short_url.db"))


class URLHandler(BaseHTTPRequestHandler):
    redirect_path = "/r"

    def do_GET(self):
        if self.path == "/stats":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()

            table = url_shortener.get_stats_as_html()
            self.wfile.write(table.encode("utf-8"))

        elif self.path.startswith(self.redirect_path + "/"):
            redirect_string = self.path[3:]
            new_url = url_shortener.get_redirect(redirect_string)
            if new_url:
                self.send_response(302)
                self.send_header("Location", new_url)
                self.end_headers()
            else:
                self.send_response(404)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Not Valid")
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        if self.path == "/shorten":
            content_length = int(self.headers.get("Content-Length", 0))

            # Read the request body
            post_data = json.loads(self.rfile.read(content_length).decode("utf-8"))
            print(post_data)
            if "url" in post_data:
                shortened_url = url_shortener.shorten_url(post_data.get("url", ""))
                new_url = f"{self.headers["Host"]}{self.redirect_path}/{shortened_url}"

                # b_url = bytearray()
                # b_url.extend(map(ord, new_url))

                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(new_url.encode("utf-8"))
            else:
                self.send_response(404)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Not Found")
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not Found")


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
