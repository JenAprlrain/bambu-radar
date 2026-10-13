import json
import re
from datetime import datetime, timezone
import feedparser
import requests

FEEDS = [
    # Targeted queries for the two specific printers & pre-order announcements
    {
        "url": "https://news.google.com/rss/search?q=Bambu+Lab+X2C+OR+H3C+OR+%22pre-order%22&hl=en-US&gl=US&ceid=US:en",
        "source": "Google News",
        "category": "Pre-Order & Leaks",
    },
    {
        "url": "https://news.google.com/rss/search?q=%22Bambu+Lab%22+toolchanger+OR+Vortek+OR+%22multi-nozzle%22&hl=en-US&gl=US&ceid=US:en",
        "source": "Tech Radar",
        "category": "Hardware Leaks",
    },
    {
        "url": "https://3dprintingindustry.com/feed/",
        "source": "3D Printing Industry",
        "category": "Industry News",
    },
    {
        "url": "https://all3dp.com/feed/",
        "source": "All3DP",
        "category": "3D Tech",
    },
]

KEYWORDS = [
    "bambu", "x2c", "h3c", "vortek", "toolchanger", "flagship",
    "preorder", "pre-order", "leak", "faster", "patent", "s1", "r1"
]

def clean_text(raw_html: str) -> str:
    clean = re.sub(r"<[^>]+>", "", raw_html or "")
    return " ".join(clean.split())

def is_relevant(text: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in KEYWORDS)

def tag_printer(text: str) -> str:
    lowered = text.lower()
    if "h3c" in lowered or "10-nozzle" in lowered or "rack" in lowered:
        return "H3C"
    if "x2c" in lowered or "toolchanger" in lowered or "vortek" in lowered:
        return "X2C"
    return "General"

def main():
    print("Scanning news feeds for X2C, H3C, and Bambu announcements...")
    unique_articles = []
    seen_urls = set()

    for feed_info in FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            for entry in feed.entries[:12]:
                title = clean_text(entry.get("title", ""))
                summary = clean_text(entry.get("summary", entry.get("description", "")))
                url = entry.get("link", "").split("?")[0].strip()

                if not url or url in seen_urls:
                    continue

                full_text = f"{title} {summary}"
                if not is_relevant(full_text):
                    continue

                seen_urls.add(url)

                pub_date = entry.get("published", "")
                if not pub_date:
                    pub_date = datetime.now(timezone.utc).strftime("%b %d, %Y")
                else:
                    pub_date = pub_date[:16]

                unique_articles.append({
                    "id": f"art-{abs(hash(url))}",
                    "title": title,
                    "source": feed_info["source"],
                    "category": feed_info["category"],
                    "target": tag_printer(full_text),
                    "summary": (summary[:240] + "...") if len(summary) > 240 else summary or "Click link to read full report.",
                    "url": url,
                    "timestamp": pub_date,
                })
        except Exception as e:
            print(f"Error reading feed {feed_info['url']}: {e}")

    # Fallback cards if feeds are temporarily quiet
    if not unique_articles:
        unique_articles = [
            {
                "id": "init-x2c",
                "title": "Bambu Lab X2C Compact Toolchanger: Patent Filings & Production Window",
                "source": "Bambu Radar Bot",
                "category": "Hardware Leaks",
                "target": "X2C",
                "summary": "Community patent breakdowns indicate compact Vortek toolchanger heads targeting sub-5s swaps with zero filament waste on standard desktop footprints.",
                "url": "https://forum.bambulab.com/",
                "timestamp": datetime.now(timezone.utc).strftime("%b %d, %Y"),
            },
            {
                "id": "init-h3c",
                "title": "Bambu Lab H3C 10-Nozzle Flagship: Industrial Pick-and-Place Carousel",
                "source": "3D Printing Speculation",
                "category": "Hardware Leaks",
                "target": "H3C",
                "summary": "High-volume carousel toolchanger patent disclosures show up to 10 active nozzles with high-temp chamber capabilities aimed at commercial multi-material workflows.",
                "url": "https://forum.bambulab.com/",
                "timestamp": datetime.now(timezone.utc).strftime("%b %d, %Y"),
            },
        ]

    payload = {
        "last_updated": datetime.now(timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC"),
        "total": len(unique_articles),
        "articles": unique_articles[:20],
    }

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"news.json successfully generated with {len(payload['articles'])} articles.")

if __name__ == "__main__":
    main()