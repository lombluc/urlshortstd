import json
from pathlib import Path
import random
import string


class URLShortener:
    def __init__(self, db_path: Path, url_length: int = 6):
        self.url_length = url_length
        self.db_path = db_path
        self.db = {}
        self.load_db()

    def shorten_url(self, url: str) -> str:
        while True:
            short_url = "".join(
                random.choices(string.ascii_letters + string.digits, k=self.url_length)
            )
            if short_url in self.db:
                continue
            self.db[short_url] = url
            self.save_db()
            return short_url

    def get_redirect(self, redirect_string: str) -> str:
        if redirect_string in self.db:
            return self.db[redirect_string]
        return ""

    def load_db(self) -> None:
        with open(self.db_path, "r") as f:
            self.db = json.load(f)

    def save_db(self) -> None:
        with open(self.db_path, "w") as f:
            json.dump(self.db, f)
