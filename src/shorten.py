from collections.abc import Generator
from contextlib import closing, contextmanager
import datetime
import html
from pathlib import Path
from secrets import token_urlsafe
import sqlite3

from src.exceptions import AddURLError


class URLShortener:
    def __init__(self, db_path: Path, url_bytes: int = 6):
        self.url_bytes = url_bytes
        self.db_path = db_path
        self.init_db()

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection]:
        with closing(sqlite3.connect(self.db_path)) as con, con:
            cur = con.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            yield con

    def _generate_code(self) -> str:
        return token_urlsafe(self.url_bytes)

    def shorten_url(self, url: str) -> str:
        for _ in range(10):
            short_url = self._generate_code()
            try:
                self.add_to_db(short_url, url)
                return short_url
            except sqlite3.IntegrityError:
                continue
        else:
            raise AddURLError("Failed to make new shortened url")

    def get_redirect(self, short_url: str) -> str | None:
        with self._connect() as con:
            cur = con.cursor()
            cur.execute("SELECT redirect FROM url where short_url = ?", (short_url,))
            res = cur.fetchall()
            if res:
                cur.execute(
                    "INSERT INTO log VALUES(?, ?)",
                    (datetime.datetime.now(tz=datetime.timezone.utc), short_url),
                )
        if res:
            return res[0][0]
        return None

    def add_to_db(self, short_url: str, redirect: str) -> None:
        with self._connect() as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO url VALUES(?, ?, ?)",
                (short_url, redirect, datetime.datetime.now(tz=datetime.timezone.utc)),
            )

    def get_stats_as_html(self):
        with self._connect() as con:
            cur = con.cursor()
            cur.execute("""
                SELECT
                    u.time_created,
                    u.short_url,
                    u.redirect,
                    COUNT(l.short_url) AS total
                FROM url u
                LEFT JOIN log l
                    ON u.short_url = l.short_url
                GROUP BY u.short_url
                ORDER BY u.time_created, u.rowid
                """)
            stats = cur.fetchall()
        page = """
            <html>
            <head><title>Item Table</title></head>
            <body>
            <h2>Shortened URL stats</h2>
            <table border='1'>
                <tr><th>Time created</th><th>Short URL</th><th>Redirect</th><th>Times redirected</th></tr>
            """
        for time_created, short_url, redirect, total in stats:
            page += f"<tr><td>{html.escape(time_created)}</td><td>{html.escape(short_url)}</td><td>{html.escape(redirect)}</td><td>{html.escape(str(total))}</td></tr>"

        page += "</table></body></html>"
        return page

    def init_db(self):
        self.db_path.parent.mkdir(exist_ok=True, parents=True)
        with self._connect() as con:
            cur = con.cursor()
            cur.execute("""CREATE TABLE IF NOT EXISTS url(
                    short_url text PRIMARY KEY NOT NULL,
                    redirect text NOT NULL,
                    time_created DATETIME NOT NULL
                    )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS log(
                    time DATETIME NOT NULL,
                    short_url text NOT NULL,
                    FOREIGN KEY (short_url)
                        REFERENCES url (short_url)
                    )""")
