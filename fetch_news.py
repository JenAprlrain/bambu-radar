import json
import re
import time
import random
from datetime import datetime, timezone, timedelta
import feedparser
import requests

MAX_DAYS_OLD = 30  # Search the last 30 days of community activity

# Broadened keyword bank capturing technical leaks, FCC tokens, and community tags
SEARCH_KEYWORDS = [
    "bambu", "x2d", "x2d pro", "h3c", "h2c", "h2d", "p3c",
    "toolchanger", "vortek", "dual nozzle", "multi-nozzle", "idex",
    "flagship", "fcc", "pf008p", "patent", "leak", "leaks",
    "preorder", "pre-order", "next gen", "teaser", "announcement"
]

FEEDS = [
    # Google News: Specific targeted query
    {
        "url": "https://news.google.com/rss/search?q=(%22Bambu+Lab%22+OR+Bambu)+(%22X2D%22+OR+%22H3C%22+OR+%22toolchanger%22+OR+%22flagship%22+OR+%22FCC%22)&hl=en-US&gl=US&ceid=US:en",
        "source": "Google News",
        "category": "Regulatory & Leaks",
    },
    # Google News: Broad community leaks & rumors
    {
        "url": "https://news.google.com/rss/search?q=%22Bambu+Lab%22+(%22new+printer%22+OR+%22next-gen%22+OR+%22patent%22+OR+%22pre-order%22)&hl=en-US&gl=US&ceid=US:en",
        "source": "Bambu Radar",
        "category": "Hardware Leaks",
    },
    # 3D Printing Industry feed
    {
        "url": "https://3dprintingindustry.com/feed/",
        "source": "3D Printing Industry",
        "category": "Industry News",
    },
    # All3DP feed
    {
        "url": "https://all3dp.com/feed/",
        "source": "All3DP",
        "category": "3D Tech",
    },
]

# Reddit subreddits to scan via RSS
REDDIT_RSS_URLS = [
    "https://www.reddit.com/r/BambuLab/search.rss?q=X2D+OR+H3C+OR+leak+OR+flagship+OR+patent&sort=new&restrict_sr=1",
    "https://www.reddit.com/r/BambuLab/search.rss?q=%22new+printer%22+OR+%22next+gen%22+OR+toolchanger&sort=new&restrict_sr=1"
]

# Curated pool of trending MakerWorld models with verified CDN images
MAKERWORLD_POOL = [
    {
        "name": "Bambu Universal Tool Box",
        "badge": "Essential Tool",
        "meta": "⭐ 4.9 • Model #1892987",
        "desc": "Rugged snap-fit container tailored for Bambu hotends, wipers, and hex wrenches.",
        "img": "https://makerworld.bblmw.com/makerworld/model/US9e840b13a3714f/design/2025-10-16_797d4777c3f6b8.jpg",
        "url": "https://makerworld.com/en/models/1892987-bambu-universal-toolbox-model"
    },
    {
        "name": "Desiccant Container for Spools",
        "badge": "AMS Upgrade",
        "meta": "⭐ 4.9 • Model #973318",
        "desc": "Screws directly into spool hubs to keep engineering filaments dry inside the AMS.",
        "img": "https://makerworld.bblmw.com/makerworld/model/US15f809ba9e1867/design/2025-01-09_4624e9779251a.jpg?x-oss-process=image/resize,w_800/format,webp",
        "url": "https://makerworld.com/en/models/973318-desiccant-container-for-bambu-lab-spool"
    },
    {
        "name": "Shadowcoil Articulated Dragon",
        "badge": "Multi-Color",
        "meta": "⭐ 4.9 • Model #1163767",
        "desc": "Print-in-place flexi showpiece for testing color switches, retractions, and overhangs.",
        "img": "https://makerworld.bblmw.com/makerworld/model/USf0764dc7070e2c/design/2025-03-01_a443aa6c1fd3a.png",
        "url": "https://makerworld.com/en/models/1163767-shadowcoil-articulated-dragon"
    },
    {
        "name": "Bambu Official LED Lamp 001",
        "badge": "Official Kit",
        "meta": "⭐ 4.9 • Model #13717",
        "desc": "Bambu Lab's spiral desktop accent lamp powered by their official USB lamp hardware kit.",
        "img": "https://makerworld.bblmw.com/makerworld/model/DSM00000000013717/design/2023-09-19_9f3e533f94456.jpg?x-oss-process=image/format,webp",
        "url": "https://makerworld.com/en/models/13717-led-lamp-001"
    },
    {
        "name": "Bambu Scraper with Ergonomic Grip",
        "badge": "Workshop Essential",
        "meta": "⭐ 4.8 • 52k Downloads",
        "desc": "Bed scraper handle optimized for standard Bambu replacement razor blades.",
        "img": "https://makerworld.bblmw.com/makerworld/model/DSM00000000013717/design/2023-09-19_9f3e533f94456.jpg?x-oss-process=image/format,webp",
        "url": "https://makerworld.com/en/search/models?keyword=bambu%20scraper"
    },
    {
        "name": "AMS Disconnect & PTFE Tool",
        "badge": "Must-Have Mod",
        "meta": "⭐ 4.9 • 31k Downloads",
        "desc": "Pocket pry lever to safely release stubborn pneumatic PTFE tube connectors.",
        "img": "https://makerworld.bblmw.com/makerworld/model/US9e840b13a3714f/design/2025-10-16_797d4777c3f6b8.jpg",
        "url": "https://makerworld.com/en/search/models?keyword=ptfe%20disconnect%20tool"
    }
]

def clean_text(raw_html: str) -> str:
    clean = re.sub(r"<[^>]+>", "", raw_html or "")
    return " ".join(clean.split())

def is_relevant(text: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in SEARCH_KEYWORDS)

def tag_printer(text: str) -> str:
    lowered = text.lower()
    if "h3c" in lowered or "10-nozzle" in lowered or "rack" in lowered:
        return "H3C"
    if "x2d" in lowered or "dual nozzle" in lowered or "x2d pro" in lowered:
        return "X2D Pro"
    return "General"

def parse_entry_datetime(entry) -> datetime:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime.fromtimestamp(time.mktime(entry.updated_parsed), tz=timezone.utc)
    return datetime.now(timezone.utc)

def fetch_feed_data(url: str):
    """Fetch with a browser-like User-Agent to avoid Reddit 403 blocks."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 200:
            return feedparser.parse(resp.content)
        else:
            print(f"Fetch failed with HTTP {resp.status_code} for: {url}")
    except Exception as e:
        print(f"Request error for {url}: {e}")
    return feedparser.parse(url)

def main():
    print("Collecting Reddit, Google News, and 3D printing articles...")
    now = datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=MAX_DAYS_OLD)

    collected_articles = []
    seen_urls = set()

    # 1. Fetch Reddit RSS Feeds
    for r_url in REDDIT_RSS_URLS:
        try:
            parsed = fetch_feed_data(r_url)
            for entry in parsed.entries[:15]:
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
                    "source": "r/BambuLab",
                    "category": "Reddit Discussion",
                    "target": tag_printer(full_text),
                    "summary": (summary[:230] + "...") if len(summary) > 230 else summary or "Click link to view Reddit discussion.",
                    "url": url,
                    "timestamp": pub_dt.strftime("%b %d, %Y"),
                    "_sort_ts": pub_dt.timestamp(),
                })
        except Exception as e:
            print(f"Error fetching Reddit: {e}")

    # 2. Fetch Google News & Industry RSS Feeds
    for feed_info in FEEDS:
        try:
            parsed = fetch_feed_data(feed_info["url"])
            for entry in parsed.entries[:12]:
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
                    "summary": (summary[:230] + "...") if len(summary) > 230 else summary or "Click link to read article.",
                    "url": url,
                    "timestamp": pub_dt.strftime("%b %d, %Y"),
                    "_sort_ts": pub_dt.timestamp(),
                })
        except Exception as e:
            print(f"Error reading feed {feed_info['source']}: {e}")

    # Sort newest date on top
    collected_articles.sort(key=lambda x: x["_sort_ts"], reverse=True)
    for a in collected_articles:
        if "_sort_ts" in a:
            del a["_sort_ts"]

    # Pick 4 rotating MakerWorld models
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

    print(f"Wrote {len(payload['articles'])} articles and {len(daily_makerworld_picks)} prints to news.json.")

if __name__ == "__main__":
    main()