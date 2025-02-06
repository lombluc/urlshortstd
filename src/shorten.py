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
            cur.execute(f"SELECT redirect FROM url where short_url = ?", (short_url,))
            res = cur.fetchall()
        if res:
            return res[0][0]
        return ""

    def add_to_db(self, short_url: str, redirect: str) -> None:
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.executemany("INSERT INTO url VALUES(?, ?)", [(short_url, redirect)])
            con.commit()
