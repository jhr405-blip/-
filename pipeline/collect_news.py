#!/usr/bin/env python3
"""1단계: 뉴스 수집.

크립토/거시 뉴스 RSS 피드를 돌면서 최근 기사를 모아 JSON으로 저장한다.
표준 라이브러리만 사용하므로 어디서든 바로 실행 가능.

사용법:
    python3 pipeline/collect_news.py                # 최근 24시간 기사 수집
    python3 pipeline/collect_news.py --hours 48     # 최근 48시간
    python3 pipeline/collect_news.py -o news.json   # 출력 경로 지정
"""

import argparse
import json
import re
import ssl
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

# 소스 목록 — 새벽에온주호 같은 채널이 쓰는 것과 동일한 공개 소스들.
# 1차 소스(연준)와 크립토 전문 매체를 섞어서 수집한다.
FEEDS = {
    "coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "cointelegraph": "https://cointelegraph.com/rss",
    "decrypt": "https://decrypt.co/feed",
    "theblock": "https://www.theblock.co/rss.xml",
    "bitcoinmagazine": "https://bitcoinmagazine.com/feed",
    "federalreserve": "https://www.federalreserve.gov/feeds/press_all.xml",
}

ATOM_NS = "{http://www.w3.org/2005/Atom}"


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def parse_date(text: str):
    if not text:
        return None
    try:
        return parsedate_to_datetime(text)  # RFC 822 (RSS)
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))  # ISO (Atom)
    except ValueError:
        return None


def fetch_feed(name: str, url: str) -> list[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (news-collector)"})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
        root = ElementTree.fromstring(resp.read())

    items = []
    # RSS 2.0
    for item in root.iter("item"):
        items.append({
            "source": name,
            "title": strip_html(item.findtext("title", "")),
            "link": (item.findtext("link") or "").strip(),
            "summary": strip_html(item.findtext("description", ""))[:500],
            "published": item.findtext("pubDate") or item.findtext(
                "{http://purl.org/dc/elements/1.1/}date", ""),
        })
    # Atom
    for entry in root.iter(f"{ATOM_NS}entry"):
        link_el = entry.find(f"{ATOM_NS}link")
        items.append({
            "source": name,
            "title": strip_html(entry.findtext(f"{ATOM_NS}title", "")),
            "link": link_el.get("href", "") if link_el is not None else "",
            "summary": strip_html(entry.findtext(f"{ATOM_NS}summary", ""))[:500],
            "published": entry.findtext(f"{ATOM_NS}updated", ""),
        })
    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=24, help="최근 N시간 기사만 수집 (기본 24)")
    ap.add_argument("-o", "--output", default="news_today.json")
    args = ap.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)
    collected = []

    for name, url in FEEDS.items():
        try:
            items = fetch_feed(name, url)
        except Exception as e:  # 피드 하나가 죽어도 나머지는 계속
            print(f"  [skip] {name}: {e}", file=sys.stderr)
            continue
        fresh = []
        for it in items:
            dt = parse_date(it["published"])
            if dt is None or dt < cutoff:
                continue
            it["published"] = dt.isoformat()
            fresh.append(it)
        print(f"  [ok] {name}: {len(fresh)}건")
        collected.extend(fresh)

    collected.sort(key=lambda x: x["published"], reverse=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"collected_at": datetime.now(timezone.utc).isoformat(),
                   "window_hours": args.hours,
                   "count": len(collected),
                   "articles": collected}, f, ensure_ascii=False, indent=2)
    print(f"총 {len(collected)}건 → {args.output}")


if __name__ == "__main__":
    main()
