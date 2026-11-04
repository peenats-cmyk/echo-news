#!/usr/bin/env python3
"""投資信託の基準価額を取得して funds.json に保存する(履歴も蓄積して前月比を計算)。"""
import json
import os
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone

FUNDS = [
    ("オルカン", "0331418A"),
    ("S&P500", "03311187"),
    ("楽天NASDAQ", "9I314241"),
    ("楽天SOX", "9I315241"),
]
URL = "https://apl.wealthadvisor.jp/webasp/yahoo-fund/fund/snp/snp_%s.html"
RTN_URL = "https://apl.wealthadvisor.jp/webasp/yahoo-fund/fund/rtn/rtn_%s.html"
JST = timezone(timedelta(hours=9))
OUT = "funds.json"
KEEP_DAYS = 150


def fetch(code, url=URL):
    req = urllib.request.Request(url % code, headers={"User-Agent": "Mozilla/5.0 (echo-news)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("shift_jis", errors="replace")


def parse(html):
    m = re.search(r"基準日[:：]\s*(\d{4})年(\d{1,2})月(\d{1,2})日", html)
    if not m:
        raise ValueError("基準日が見つからない")
    d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    t = re.search(
        r"<td>\s*([\d,]+)\s*<span[^>]*>円</span>\s*</td>\s*<td>\s*<span[^>]*>\s*([↑↓]?)\s*([\d,]+)\s*円",
        html,
    )
    if not t:
        raise ValueError("基準価額が見つからない")
    nav = int(t.group(1).replace(",", ""))
    diff = int(t.group(3).replace(",", ""))
    if t.group(2) == "↓":
        diff = -diff
    return d, nav, diff


def parse_yoy(html):
    """トータルリターン(1年)と評価基準日(月末)を返す。"""
    m = re.search(r"評価基準日\s*(\d{4})年(\d{1,2})月(\d{1,2})日", html)
    r = re.search(r"トータルリターン</td>((?:\s*<td>.*?</td>){6})", html, re.S)
    if not m or not r:
        raise ValueError("1年リターンが見つからない")
    cells = [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<td>(.*?)</td>", r.group(1), re.S)]
    v = float(cells[3].replace("%", ""))
    return v, "%d/%d" % (int(m.group(2)), int(m.group(3)))


def month_ago(d):
    y, m = (d.year, d.month - 1) if d.month > 1 else (d.year - 1, 12)
    day = d.day
    while True:
        try:
            return date(y, m, day)
        except ValueError:
            day -= 1


def mom(hist, latest):
    """前月比: 1か月前以前でいちばん近い日(7日以内)。なければ、手持ちで最も古い日(10日以上前)。"""
    target = month_ago(latest)
    days = sorted(date.fromisoformat(k) for k in hist)
    ref = None
    for k in days:
        if k <= target and (target - k).days <= 7:
            ref = k
    if ref is None:
        older = [k for k in days if (latest - k).days >= 10]
        if older:
            ref = older[0]
    if ref is None:
        return None, None
    base = hist[ref.isoformat()]
    return round((hist[latest.isoformat()] / base - 1) * 100, 2), "%d/%d" % (ref.month, ref.day)


def main():
    old = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
    history = old.get("history", {})
    items = []
    for name, code in FUNDS:
        h = history.setdefault(code, {})
        try:
            d, nav, diff = parse(fetch(code))
            h[d.isoformat()] = nav
        except Exception as e:
            print("skip", name, e, file=sys.stderr)
            if not h:
                continue
            d = max(date.fromisoformat(k) for k in h)
            nav = h[d.isoformat()]
            diff = 0
        cutoff = (d - timedelta(days=KEEP_DAYS)).isoformat()
        for k in [k for k in h if k < cutoff]:
            del h[k]
        pct = round(diff / (nav - diff) * 100, 2) if nav != diff else 0.0
        m, ref = mom(h, d)
        yoy, yref = None, None
        try:
            yoy, yref = parse_yoy(fetch(code, RTN_URL))
        except Exception as e:
            print("yoy skip", name, e, file=sys.stderr)
        items.append({"name": name, "code": code, "date": "%d/%d" % (d.month, d.day),
                      "nav": nav, "diff": diff, "pct": pct, "mom": m, "momRef": ref, "yoy": yoy, "yoyRef": yref})
    if not items:
        print("no items", file=sys.stderr)
        sys.exit(1)
    data = {"updated": datetime.now(JST).strftime("%Y-%m-%d %H:%M"), "items": items, "history": history}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
    print("saved", len(items), "funds")


if __name__ == "__main__":
    main()
