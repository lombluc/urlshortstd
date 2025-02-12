import datetime
from pathlib import Path
import random
import string
import sqlite3


class URLShortener:
    def __init__(self, db_path: Path, url_length: int = 6):
        self.url_length = url_length
        self.db_path = db_path

    def shorten_url(self, url: str) -> str:
        all_short_urls = self.get_short_urls()
        while True:
            short_url = "".join(
                random.choices(string.ascii_letters + string.digits, k=self.url_length)
            )
            if short_url in all_short_urls:
                continue
            self.add_to_db(short_url, url)
            return short_url

    def get_redirect(self, short_url: str) -> str:
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO log VALUES(?, ?)",
                (datetime.datetime.now(), short_url),
            )
            con.commit()
            cur.execute(f"SELECT redirect FROM url where short_url = ?", (short_url,))
            res = cur.fetchall()
        if res:
            return res[0][0]
        return ""

    def get_short_urls(self) -> set:
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute("SELECT short_url FROM url")
            col = cur.fetchall()
        return set(r[0] for r in col)

    def add_to_db(self, short_url: str, redirect: str) -> None:
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO url VALUES(?, ?, ?)",
                (short_url, redirect, datetime.datetime.now()),
            )
            con.commit()

    def get_stats_as_html(self):
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT
                    u.time_created,
                    u.short_url,
                    u.redirect,
                    COUNT(l.short_url) AS total
                FROM url u
                LEFT JOIN log l
                    ON u.short_url = l.short_url
                GROUP BY u.time_created, u.short_url, u.redirect
                """
            )
            stats = cur.fetchall()
        html = """
            <html>
            <head><title>Item Table</title></head>
            <body>
            <h2>Shortened URL stats</h2>
            <table border='1'>
                <tr><th>Time created</th><th>Short URL</th><th>Redirect</th><th>Times redirected</th></tr>
            """
        for time_created, short_url, redirect, total in stats:
            html += f"<tr><td>{time_created}</td><td>{short_url}</td><td>{redirect}</td><td>{total}</td></tr>"

        html += "</table></body></html>"
        return html
