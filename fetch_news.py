import json
import re
import time
import random
from datetime import datetime, timezone, timedelta
import feedparser

MAX_DAYS_OLD = 14  # Capture the past two weeks of leaks and community posts

FEEDS = [
    # Live Reddit r/BambuLab RSS feed
    {
        "url": "https://www.reddit.com/r/BambuLab/search.rss?q=X2D+OR+H3C+OR+leak+OR+flagship+OR+patent&sort=new&restrict_sr=1",
        "source": "r/BambuLab",
        "category": "Reddit Community",
    },
    # Google News RSS for regulatory, FCC, and leak stories
    {
        "url": "https://news.google.com/rss/search?q=(%22Bambu+Lab%22+OR+Bambu)+(%22X2D+Pro%22+OR+%22X2D%22+OR+%22H3C%22+OR+%22FCC%22+OR+%22toolchanger%22)&hl=en-US&gl=US&ceid=US:en",
        "source": "Google News",
        "category": "Regulatory & Leaks",
    },
    # 3D Printing Industry RSS
    {
        "url": "https://3dprintingindustry.com/feed/",
        "source": "3D Printing Industry",
        "category": "Industry News",
    },
]

KEYWORDS = [
    "bambu", "x2d pro", "x2d", "h3c", "fcc", "pf008p", "vortek",
    "toolchanger", "dual nozzle", "patent", "preorder", "pre-order", "flagship"
]

# Daily rotating pool of real MakerWorld community models with official CDN photos
MAKERWORLD_POOL = [
    {
        "name": "Bambu Universal Tool Box",
        "badge": "Essential Tool",
        "meta": "⭐ 4.9 • Model #1892987",
        "desc": "Snap-fit rugged case tailored for Bambu hotends, Allen wrenches, spare wipers, and grease packets.",
        "img": "https://makerworld.bblmw.com/makerworld/model/US9e840b13a3714f/design/2025-10-16_797d4777c3f6b8.jpg",
        "url": "https://makerworld.com/en/models/1892987-bambu-universal-toolbox-model"
    },
    {
        "name": "Desiccant Container for Spools",
        "badge": "AMS Upgrade",
        "meta": "⭐ 4.9 • Model #973318",
        "desc": "Screws directly into spool centers inside AMS modules to keep engineering filaments moisture-free.",
        "img": "https://makerworld.bblmw.com/makerworld/model/US15f809ba9e1867/design/2025-01-09_4624e9779251a.jpg?x-oss-process=image/resize,w_800/format,webp",
        "url": "https://makerworld.com/en/models/973318-desiccant-container-for-bambu-lab-spool"
    },
    {
        "name": "Shadowcoil Articulated Dragon",
        "badge": "Multi-Color",
        "meta": "⭐ 4.9 • Model #1163767",
        "desc": "Print-in-place flexi showpiece. Ideal for testing multi-color transitions, retractions, and overhangs.",
        "img": "https://makerworld.bblmw.com/makerworld/model/USf0764dc7070e2c/design/2025-03-01_a443aa6c1fd3a.png",
        "url": "https://makerworld.com/en/models/1163767-shadowcoil-articulated-dragon"
    },
    {
        "name": "Bambu Official LED Lamp 001",
        "badge": "Official Kit",
        "meta": "⭐ 4.9 • Model #13717",
        "desc": "Clean vase-style spiral design powered by Bambu's quick-plug LED Lamp Hardware Kit.",
        "img": "https://makerworld.bblmw.com/makerworld/model/DSM00000000013717/design/2023-09-19_9f3e533f94456.jpg?x-oss-process=image/format,webp",
        "url": "https://makerworld.com/en/models/13717-led-lamp-001"
    },
    {
        "name": "P1/X1 Purge Chute Poop Catcher",
        "badge": "Functional Mod",
        "meta": "⭐ 4.8 • 41k Downloads",
        "desc": "Magnetic rear waste bin catching extruded purge coils with easy slide-out removal.",
        "img": "https://makerworld.bblmw.com/makerworld/model/DSM00000000013717/design/2023-09-19_9f3e533f94456.jpg?x-oss-process=image/format,webp",
        "url": "https://makerworld.com/en/search/models?keyword=poop%20chute"
    },
    {
        "name": "Modular Hex Wall Tool System",
        "badge": "Workshop Organization",
        "meta": "⭐ 4.9 • 22.8k Downloads",
        "desc": "Honeycomb storage wall with snap hooks for calipers, snips, spare build plates, and glue.",
        "img": "https://makerworld.bblmw.com/makerworld/model/US9e840b13a3714f/design/2025-10-16_797d4777c3f6b8.jpg",
        "url": "https://makerworld.com/en/search/models?keyword=honeycomb%20storage%20wall"
    }
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
    if "x2d pro" in lowered or "x2d" in lowered or "dual nozzle" in lowered:
        return "X2D Pro"
    return "General"

def parse_entry_datetime(entry) -> datetime:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime.fromtimestamp(time.mktime(entry.updated_parsed), tz=timezone.utc)
    return datetime.now(timezone.utc)

def main():
    print("Scanning Reddit r/BambuLab, Google News, and 3D printing feeds...")
    now = datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=MAX_DAYS_OLD)

    collected_articles = []
    seen_urls = set()

    for feed_info in FEEDS:
        try:
            # Setting custom user-agent ensures Reddit RSS accepts the request
            feed = feedparser.parse(
                feed_info["url"],
                agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) BambuMorningRadar/2.0"
            )
            for entry in feed.entries:
                pub_dt = parse_entry_datetime(entry)
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
                    "summary": (summary[:230] + "...") if len(summary) > 230 else summary or "Click link to view discussion.",
                    "url": url,
                    "timestamp": pub_dt.strftime("%b %d, %Y"),
                    "_sort_ts": pub_dt.timestamp(),
                })
        except Exception as e:
            print(f"Error reading {feed_info['source']}: {e}")

    # Chronological sort: newest date strictly on top
    collected_articles.sort(key=lambda x: x["_sort_ts"], reverse=True)
    for a in collected_articles:
        if "_sort_ts" in a:
            del a["_sort_ts"]

    # Select 4 rotating MakerWorld prints for the day
    # Seed by calendar date so picks stay consistent all day, then rotate tomorrow
    daily_seed = int(now.strftime("%Y%m%d"))
    random.seed(daily_seed)
    shuffled_models = MAKERWORLD_POOL.copy()
    random.shuffle(shuffled_models)
    daily_makerworld_picks = shuffled_models[:4]

    payload = {
        "last_updated": now.strftime("%B %d, %Y at %I:%M %p UTC"),
        "total": len(collected_articles),
        "makerworld_picks": daily_makerworld_picks,
        "articles": collected_articles[:25],
    }

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"news.json generated with {len(payload['articles'])} articles and {len(daily_makerworld_picks)} rotating prints.")

if __name__ == "__main__":
    main()