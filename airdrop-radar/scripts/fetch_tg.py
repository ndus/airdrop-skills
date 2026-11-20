"""Baca maksimal 20 postingan dari pratinjau publik Telegram."""

import argparse
import json
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen


BASE = "https://t.me"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"


class PreviewParser(HTMLParser):
    """Ambil isi pesan, tautan, dan waktu dari kartu Telegram."""

    def __init__(self, channel):
        super().__init__()
        self.channel = channel
        self.posts = []
        self.depth = 0
        self.message_depth = None
        self.text_depth = None
        self.post = None
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = (attrs.get("class") or "").split()
        if tag == "div":
            self.depth += 1
            if "tgme_widget_message" in classes and self.post is None:
                self.message_depth = self.depth
                self.post = {"channel": self.channel, "text": "", "links": [], "time": None}
                self.parts = []
            if self.post is not None and "tgme_widget_message_text" in classes:
                self.text_depth = self.depth
        if self.post is None:
            return
        if tag == "time" and attrs.get("datetime") and self.post["time"] is None:
            self.post["time"] = attrs["datetime"]
        if tag == "br" and self.text_depth is not None:
            self.parts.append("\n")
        if tag == "a" and attrs.get("href") and (
            self.text_depth is not None or "tgme_widget_message_link_preview" in classes
        ):
            try:
                link = urljoin(BASE, attrs["href"])
                if urlsplit(link).scheme in {"http", "https"} and link not in self.post["links"]:
                    self.post["links"].append(link)
            except ValueError:
                pass

    def handle_data(self, data):
        if self.text_depth is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag != "div":
            return
        if self.depth == self.text_depth:
            self.text_depth = None
        if self.depth == self.message_depth:
            self.post["text"] = "".join(self.parts).strip()
            self.posts.append(self.post)
            self.message_depth = None
            self.post = None
        self.depth = max(0, self.depth - 1)


def fetch(channel):
    channel = channel.removeprefix("@")
    try:
        if not re.fullmatch(r"[a-zA-Z0-9_]+", channel):
            raise ValueError("username Telegram tidak valid")
        request = Request(f"{BASE}/s/{channel}", headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=10) as response:
            if urlsplit(response.geturl()).path.rstrip("/").lower() != f"/s/{channel.lower()}":
                raise ValueError("pratinjau publik tidak tersedia")
            html = response.read().decode("utf-8", errors="replace")
        parser = PreviewParser(channel)
        parser.feed(html)
        parser.close()
        return parser.posts[-20:]
    except (OSError, ValueError) as exc:
        return {"error": str(exc), "channel": channel}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", required=True)
    args = parser.parse_args()
    print(json.dumps(fetch(args.channel), ensure_ascii=False))


if __name__ == "__main__":
    main()
