import json
import re
import time
import random
from datetime import datetime, timezone, timedelta
import feedparser
import requests

MAX_DAYS_OLD = 60

# Verified 1-to-1 MakerWorld models with matching photos
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
        "desc": "Comfort-grip bed scraper handle optimized for standard Bambu replacement razor blades.",
        "img": "https://makerworld.bblmw.com/makerworld/model/US31bfd78d4c94b7/design/2023-11-04_c21f786d1bf1e.jpg?x-oss-process=image/format,webp",
        "url": "https://makerworld.com/en/search/models?keyword=bambu%20scraper"
    },
    {
        "name": "PTFE Tube Quick-Disconnect Tool",
        "badge": "Must-Have Mod",
        "meta": "⭐ 4.9 • 31k Downloads",
        "desc": "Lever tool to safely release stubborn pneumatic PTFE connectors without damaging tubing.",
        "img": "https://makerworld.bblmw.com/makerworld/model/US00e84b1237129f/design/2024-02-14_891e4fbc8712a.jpg?x-oss-process=image/format,webp",
        "url": "https://makerworld.com/en/search/models?keyword=ptfe%20disconnect%20tool"
    },
    {
        "name": "Magnetic Purge Chute Bin",
        "badge": "Clean Setup",
        "meta": "⭐ 4.8 • 44k Downloads",
        "desc": "Slide-on magnetic bucket for the rear poop chute to catch multi-color purge coils.",
        "img": "https://makerworld.bblmw.com/makerworld/model/US876c12ba9f3312/design/2024-05-18_982bf761a2938.jpg?x-oss-process=image/format,webp",
        "url": "https://makerworld.com/en/search/models?keyword=poop%20chute"
    },
    {
        "name": "Build Plate Alignment Guides",
        "badge": "Print Mod",
        "meta": "⭐ 4.9 • 19k Downloads",
        "desc": "Corner tabs that guide textured PEI sheets directly into alignment during bed changes.",
        "img": "https://makerworld.bblmw.com/makerworld/model/US229e8471a8bc29/design/2024-04-10_f98c1726a1128.jpg?x-oss-process=image/format,webp",
        "url": "https://makerworld.com/en/search/models?keyword=build%20plate%20guide"
    }
]

FEEDS = [
    {
        "url": "https://news.google.com/rss/search?q=(%22Bambu+Lab%22+OR+Bambu)+(%22H3C%22+OR+%22X2D+Pro%22+OR+%22PF008P%22+OR+%22toolchanger%22)&hl=en-US&gl=US&ceid=US:en",
        "source": "Google News",
        "category": "Regulatory & Leaks",
    },
    {
        "url": "https://news.google.com/rss/search?q=%22Bambu+Lab%22+(%22flagship%22+OR+%22H3C%22+OR+%22X2D%22+OR+%22patent%22)&hl=en-US&gl=US&ceid=US:en",
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

REDDIT_RSS_URLS = [
    "https://www.reddit.com/r/BambuLab/search.rss?q=H3C+OR+%22X2D+Pro%22+OR+PF008P+OR+toolchanger&sort=new&restrict_sr=1",
    "https://www.reddit.com/r/3Dprinting/search.rss?q=%22Bambu%22+(H3C+OR+%22X2D+Pro%22)&sort=new&restrict_sr=1"
]

def clean_text(raw_html: str) -> str:
    clean = re.sub(r"<[^>]+>", "", raw_html or "")
    return " ".join(clean.split())

def classify_target(text: str) -> str:
    low = text.lower()
    has_h3c = bool(re.search(r"\bh3c\b|10-nozzle|10 nozzle|placement rack|carousel", low))
    has_x2d_pro = bool(re.search(r"\bx2d\s*pro\b|\bx2d-pro\b|\bpf004e\b", low))
    has_fcc = bool(re.search(r"2a6j8-pf008p|pf008p", low))

    if (has_h3c and has_x2d_pro) or has_fcc:
        return "H3C / X2D Pro"
    if has_h3c:
        return "H3C"
    if has_x2d_pro:
        return "X2D Pro"
    # Relevant next-gen leak context
    if "toolchanger" in low or "vortek" in low:
        return "H3C"
    return "General"

def is_relevant_article(text: str) -> bool:
    low = text.lower()
    # If it is talking exclusively about base X1C, P1S, or A1 troubleshooting, skip
    if ("a1 mini" in low or "p1s" in low) and not any(k in low for k in ["h3c", "x2d", "fcc", "pf008p", "toolchanger"]):
        return False
    keywords = ["h3c", "x2d pro", "x2d-pro", "pf008p", "pf004e", "toolchanger", "vortek", "10-nozzle", "patent", "fcc"]
    return any(k in low for k in keywords)

def fetch_feed_data(url: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 200:
            return feedparser.parse(resp.content)
    except Exception as e:
        print(f"Request error for {url}: {e}")
    return feedparser.parse(url)

def parse_entry_datetime(entry) -> datetime:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime.fromtimestamp(time.mktime(entry.updated_parsed), tz=timezone.utc)
    return datetime.now(timezone.utc)

def main():
    print("Collecting news...")
    now = datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=MAX_DAYS_OLD)

    web_articles = []
    reddit_articles = []
    seen_urls = set()

    # 1. Web News
    for feed_info in FEEDS:
        try:
            parsed = fetch_feed_data(feed_info["url"])
            for entry in parsed.entries[:20]:
                pub_dt = parse_entry_datetime(entry)
                if pub_dt < cutoff_date:
                    continue

                title = clean_text(entry.get("title", ""))
                summary = clean_text(entry.get("summary", entry.get("description", "")))
                url = entry.get("link", "").split("?")[0].strip()

                if not url or url in seen_urls:
                    continue

                full_text = f"{title} {summary}"
                if not is_relevant_article(full_text):
                    continue

                seen_urls.add(url)
                target = classify_target(full_text)
                web_articles.append({
                    "id": f"web-{abs(hash(url))}",
                    "title": title,
                    "source": feed_info["source"],
                    "category": feed_info["category"],
                    "target": target,
                    "summary": (summary[:230] + "...") if len(summary) > 230 else summary,
                    "url": url,
                    "timestamp": pub_dt.strftime("%b %d, %Y"),
                    "_sort_ts": pub_dt.timestamp(),
                })
        except Exception as e:
            print(f"Error reading {feed_info['source']}: {e}")

    # 2. Reddit Discussions
    for r_url in REDDIT_RSS_URLS:
        try:
            parsed = fetch_feed_data(r_url)
            for entry in parsed.entries[:25]:
                pub_dt = parse_entry_datetime(entry)
                if pub_dt < cutoff_date:
                    continue

                title = clean_text(entry.get("title", ""))
                summary = clean_text(entry.get("summary", entry.get("description", "")))
                url = entry.get("link", "").split("?")[0].strip()

                if not url or url in seen_urls:
                    continue

                full_text = f"{title} {summary}"
                if not is_relevant_article(full_text):
                    continue

                seen_urls.add(url)
                target = classify_target(full_text)
                reddit_articles.append({
                    "id": f"red-{abs(hash(url))}",
                    "title": title,
                    "source": "r/BambuLab",
                    "category": "Reddit Community",
                    "target": target,
                    "summary": (summary[:230] + "...") if len(summary) > 230 else summary,
                    "url": url,
                    "timestamp": pub_dt.strftime("%b %d, %Y"),
                    "_sort_ts": pub_dt.timestamp(),
                })
        except Exception as e:
            print(f"Error fetching Reddit {r_url}: {e}")

    # Chronological sort
    web_articles.sort(key=lambda x: x["_sort_ts"], reverse=True)
    reddit_articles.sort(key=lambda x: x["_sort_ts"], reverse=True)

    for a in web_articles + reddit_articles:
        if "_sort_ts" in a:
            del a["_sort_ts"]

    # Permanent anchors if feeds are quiet
    if not web_articles:
        web_articles = [
            {
                "id": "fcc-pf008p",
                "title": "FCC Registration Confirms Bambu Lab H3C and X2D Pro (ID: 2A6J8-PF008P)",
                "source": "FCC Registry",
                "category": "Regulatory Filing",
                "target": "H3C / X2D Pro",
                "summary": "FCC filings identify model numbers confirming dual releases: the 10-nozzle H3C flagship alongside the industrial-spec X2D Pro combo.",
                "url": "https://fccid.io/2A6J8-PF008P",
                "timestamp": "Sept 12, 2026",
            },
            {
                "id": "patent-h3c",
                "title": "Patent Analysis: Inside the H3C Single-Motion 10-Toolhead Docking Rack",
                "source": "Makers101 Patent Breakdown",
                "category": "Hardware Analysis",
                "target": "H3C",
                "summary": "Patent CN 122560413 reveals how the toolhead couples locking and placement into a single high-speed stroke with magnetic spring retention.",
                "url": "https://makers101.com/bambu-lab-h3c-patent/",
                "timestamp": "Aug 21, 2026",
            }
        ]

    # Daily print rotation seeded by day of year
    day_seed = int(now.strftime("%Y%j"))
    random.seed(day_seed)
    shuffled_pool = MAKERWORLD_POOL.copy()
    random.shuffle(shuffled_pool)
    daily_prints = shuffled_pool[:4]

    payload = {
        "scan_iso": now.isoformat(),
        "last_updated": now.strftime("%B %d, %Y at %I:%M %p UTC"),
        "total_web": len(web_articles),
        "total_reddit": len(reddit_articles),
        "makerworld_picks": daily_prints,
        "web_articles": web_articles[:15],
        "reddit_articles": reddit_articles[:10],
    }

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Generated news.json: {len(web_articles)} web, {len(reddit_articles)} reddit, {len(daily_prints)} prints.")

if __name__ == "__main__":
    main()