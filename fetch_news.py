#!/usr/bin/env python3
"""Yahoo!ニュース(主要トピックス)の見出しを取得して news.json に保存する。"""
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

RSS_URL = "https://news.yahoo.co.jp/rss/topics/top-picks.xml"
MAX_ITEMS = 10


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (echo-news)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def parse(xml_bytes):
    root = ET.fromstring(xml_bytes)
    items = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        if title:
            items.append({"title": title, "link": link})
        if len(items) >= MAX_ITEMS:
            break
    return items


def main():
    items = parse(fetch(RSS_URL))
    if not items:
        print("no items", file=sys.stderr)
        sys.exit(1)
    jst = timezone(timedelta(hours=9))
    data = {
        "updated": datetime.now(jst).strftime("%Y-%m-%d %H:%M"),
        "source": "Yahoo!ニュース",
        "items": items,
    }
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("saved", len(items), "items")


if __name__ == "__main__":
    main()
