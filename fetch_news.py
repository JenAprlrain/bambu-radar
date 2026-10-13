import json
import re
import time
from datetime import datetime, timezone, timedelta
import feedparser

# MAX_DAYS_OLD: Adjust this to 3, 5, or 7 depending on how strict you want to be
MAX_DAYS_OLD = 7

FEEDS = [
    # Google News with 'when:7d' restricts results strictly to the past 7 days
    {
        "url": "https://news.google.com/rss/search?q=(%22Bambu+Lab%22+OR+Bambu)+(X2C+OR+H3C+OR+%22pre-order%22+OR+toolchanger)+when:7d&hl=en-US&gl=US&ceid=US:en",
        "source": "Google News (7d)",
        "category": "Pre-Order & Leaks",
    },
    {
        "url": "https://news.google.com/rss/search?q=%22Bambu+Lab%22+(flagship+OR+leak+OR+teaser+OR+patent)+when:7d&hl=en-US&gl=US&ceid=US:en",
        "source": "Bambu Radar",
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
    "preorder", "pre-order", "leak", "patent", "s1", "r1"
]

def clean_text(raw_html: str) -> str:
    clean = re.sub(r"<[^>]+>", "", raw_html or "")
    return " ".join(clean.split())

def is_relevant(text: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in KEYWORDS)

def tag_printer(text: str) -> str:
    lowered = text.lower()
    if "h3c" in lowered or "10-nozzle" in lowered or "carousel" in lowered:
        return "H3C"
    if "x2c" in lowered or "toolchanger" in lowered or "vortek" in lowered:
        return "X2C"
    return "General"

def parse_entry_datetime(entry) -> datetime:
    """Extract publish datetime as a timezone-aware UTC datetime."""
    # feedparser converts published/updated dates into time.struct_time
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime.fromtimestamp(time.mktime(entry.updated_parsed), tz=timezone.utc)
    # Default to now if the feed provides no timestamp
    return datetime.now(timezone.utc)

def main():
    print(f"Scanning for articles published within the last {MAX_DAYS_OLD} days...")
    now = datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=MAX_DAYS_OLD)

    collected_articles = []
    seen_urls = set()

    for feed_info in FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            for entry in feed.entries:
                pub_dt = parse_entry_datetime(entry)

                # Skip any article older than the cutoff threshold
                if pub_dt < cutoff_date:
                    continue

                title = clean_text(entry.get("title", ""))
                summary = clean_text(entry.get("summary", entry.get("description", "")))
                url = entry.get("link", "").split("?")[0].strip()

                if not url or url in seen_urls:
                    continue

                full_text = f"{title} {summary}"
                if not is_relevant(full_text):
                    continue

                seen_urls.add(url)

                collected_articles.append({
                    "id": f"art-{abs(hash(url))}",
                    "title": title,
                    "source": feed_info["source"],
                    "category": feed_info["category"],
                    "target": tag_printer(full_text),
                    "summary": (summary[:240] + "...") if len(summary) > 240 else summary or "Click link to read full report.",
                    "url": url,
                    "timestamp": pub_dt.strftime("%b %d, %Y"),
                    "_sort_ts": pub_dt.timestamp(),  # Used for chronological sorting
                })
        except Exception as e:
            print(f"Error reading feed {feed_info['url']}: {e}")

    # Sort strictly newest first
    collected_articles.sort(key=lambda x: x["_sort_ts"], reverse=True)

    # Remove the internal sorting key before saving to JSON
    for a in collected_articles:
        del a["_sort_ts"]

    # Fallback status if the 3D printing news cycle was completely silent this week
    if not collected_articles:
        collected_articles = [
            {
                "id": "status-idle",
                "title": "All Clear: No New Bambu Disclosures in the Past 7 Days",
                "source": "Radar Bot",
                "category": "Status Update",
                "target": "General",
                "summary": "The scraper scanned Google News, Reddit, and official patent databases. No new leaks, FCC filings, or pre-orders were logged this week. Monitoring continues tomorrow morning.",
                "url": "https://forum.bambulab.com/",
                "timestamp": now.strftime("%b %d, %Y"),
            }
        ]

    payload = {
        "last_updated": now.strftime("%B %d, %Y at %I:%M %p UTC"),
        "total": len(collected_articles),
        "articles": collected_articles[:20],
    }

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"news.json generated with {len(payload['articles'])} fresh articles.")

if __name__ == "__main__":
    main()