#!/usr/bin/env python3
"""Yahoo!ニュースの各カテゴリの見出しを取得して news.json に保存する。"""
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

BASE = "https://news.yahoo.co.jp/rss/topics/"
# (カテゴリ名, ファイル名, 取る件数)
FEEDS = [
    ("主要", "top-picks.xml", 4),
    ("国内", "domestic.xml", 3),
    ("国際", "world.xml", 3),
    ("経済", "business.xml", 3),
    ("エンタメ", "entertainment.xml", 3),
    ("スポーツ", "sports.xml", 3),
    ("IT", "it.xml", 2),
    ("科学", "science.xml", 2),
]
JST = timezone(timedelta(hours=9))


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (echo-news)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def parse(xml_bytes, cat, limit):
    root = ET.fromstring(xml_bytes)
    items = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        if not title:
            continue
        t = ""
        try:
            t = parsedate_to_datetime(it.findtext("pubDate")).astimezone(JST).strftime("%H:%M")
        except Exception:
            pass
        items.append({"cat": cat, "title": title, "link": link, "time": t})
        if len(items) >= limit:
            break
    return items


def main():
    items, seen = [], set()
    for cat, name, n in FEEDS:
        try:
            for it in parse(fetch(BASE + name), cat, n):
                if it["title"] in seen:
                    continue
                seen.add(it["title"])
                items.append(it)
        except Exception as e:
            print("skip", name, e, file=sys.stderr)
    if not items:
        print("no items", file=sys.stderr)
        sys.exit(1)
    data = {
        "updated": datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
        "source": "Yahoo!ニュース",
        "items": items,
    }
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("saved", len(items), "items")


if __name__ == "__main__":
    main()
