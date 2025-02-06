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
        while True:
            short_url = "".join(
                random.choices(string.ascii_letters + string.digits, k=self.url_length)
            )
            redirect = self.get_redirect(short_url)
            if redirect:
                continue
            self.add_to_db(short_url, url)
            return short_url

    def get_redirect(self, short_url: str) -> str:
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO log VALUES(?, ?, ?)",
                (datetime.datetime.now(), short_url, False),
            )
            con.commit()
            cur.execute(f"SELECT redirect FROM url where short_url = ?", (short_url,))
            res = cur.fetchall()
        if res:
            return res[0][0]
        return ""

    def add_to_db(self, short_url: str, redirect: str) -> None:
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute("INSERT INTO url VALUES(?, ?)", (short_url, redirect))
            cur.execute(
                "INSERT INTO log VALUES(?, ?, ?)",
                (datetime.datetime.now(), short_url, True),
            )
            con.commit()

    def get_stats_as_html(self):
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT
                    t1.short_url,
                    COUNT(*) AS total,
                    MIN(t2.time) AS time_created
                FROM log t1
                LEFT JOIN log t2
                    ON t1.short_url = t2.short_url and t2.created = 1
                WHERE NOT t1.created
                GROUP BY t1.short_url
                """
            )
            stats = cur.fetchall()
        html = """
            <html>
            <head><title>Item Table</title></head>
            <body>
            <h2>Shortened URL stats</h2>
            <table border='1'>
                <tr><th>Short URL</th><th>Times redirected</th><th>Time created</th></tr>
            """
        for url, total, time_created in stats:
            html += f"<tr><td>{url}</td><td>{total}</td><td>{time_created}</td></tr>"

        html += "</table></body></html>"
        return html
