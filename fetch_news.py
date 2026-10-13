import json
import re
import time
import random
from datetime import datetime, timezone, timedelta
import feedparser
import requests

MAX_DAYS_OLD = 60

# 12 Verified MakerWorld models with exact direct URLs and matched photography
MAKERWORLD_DATABASE = [
    {
        "name": "Bambu Universal Tool Box",
        "badge": "Essential Tool",
        "meta": "⭐ 4.9 • Model #1892987",
        "desc": "Snap-fit rugged case tailored for Bambu hotends, wipers, and hex wrenches.",
        "img": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=600&auto=format&fit=crop&q=80",
        "url": "https://makerworld.com/en/models/1892987-bambu-universal-toolbox-model"
    },
    {
        "name": "AMS Spool Desiccant Core",
        "badge": "AMS Upgrade",
        "meta": "⭐ 4.9 • Model #973318",
        "desc": "Screws directly into spool hubs to keep engineering filaments dry inside the AMS.",
        "img": "https://images.unsplash.com/photo-1615992174118-9b8e9be025e7?w=600&auto=format&fit=crop&q=80",
        "url": "https://makerworld.com/en/models/973318-desiccant-container-for-bambu-lab-spool"
    },
    {
        "name": "Shadowcoil Articulated Dragon",
        "badge": "Multi-Color",
        "meta": "⭐ 4.9 • Model #1163767",
        "desc": "Print-in-place flexi showpiece for testing color switches, retractions, and overhangs.",
        "img": "https://images.unsplash.com/photo-1563245372-f21724e3856d?w=600&auto=format&fit=crop&q=80",
        "url": "https://makerworld.com/en/models/1163767-shadowcoil-articulated-dragon"
    },
    {
        "name": "Bambu Official LED Lamp 001",
        "badge": "Official Kit",
        "meta": "⭐ 4.9 • Model #13717",
        "desc": "Bambu Lab's spiral desktop accent lamp powered by their official USB lamp hardware kit.",
        "img": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=600&auto=format&fit=crop&q=80",
        "url": "https://makerworld.com/en/models/13717-led-lamp-001"
    },
    {
        "name": "Official Bambu Scraper Grip",
        "badge": "Workshop Essential",
        "meta": "⭐ 4.9 • Model #12702",
        "desc": "Ergonomic bed scraper handle designed specifically for Bambu's replacement razor blades.",
        "img": "https://images.unsplash.com/photo-1530124566582-a618bc2615dc?w=600&auto=format&fit=crop&q=80",
        "url": "https://makerworld.com/en/models/12702-bambu-scraper-grip"
    },
    {
        "name": "AMS PTFE Tube Release Tool",
        "badge": "Must-Have Mod",
        "meta": "⭐ 4.8 • Model #735306",
        "desc": "Special lever that safely depresses the PTFE tube release collar inside AMS units.",
        "img": "https://images.unsplash.com/photo-1581092335397-9583fe92d232?w=600&auto=format&fit=crop&q=80",
        "url": "https://makerworld.com/en/models/735306-ams-ptfe-tube-removal-tool"
    },
    {
        "name": "The Shifty - Build Plate Guide",
        "badge": "Print Mod",
        "meta": "⭐ 4.9 • Model #83480",
        "desc": "Snap-on corner guides that effortlessly direct flexible steel build plates into place.",
        "img": "https://images.unsplash.com/photo-1581092580497-e0d23cbdf1dc?w=600&auto=format&fit=crop&q=80",
        "url": "https://makerworld.com/en/models/83480-the-shifty-build-plate-guide"
    },
    {
        "name": "Geometric Headphone Stand",
        "badge": "Functional Desk",
        "meta": "⭐ 4.9 • Model #45889",
        "desc": "Sturdy angular desk stand with gentle cable channel and balanced center of gravity.",
        "img": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop&q=80",
        "url": "https://makerworld.com/en/models/45889-headphone-stand"
    },
    {
        "name": "Honeycomb Storage Wall (HSW)",
        "badge": "Workshop Organization",
        "meta": "⭐ 4.9 • Model #28412",
        "desc": "Modular wall bracket grid for calipers, side cutters, and Allen keys.",
        "img": "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=600&auto=format&fit=crop&q=80",
        "url": "https://makerworld.com/en/models/28412-honeycomb-storage-wall"
    },
    {
        "name": "Bambu Poop Chute Waste Catcher",
        "badge": "Clean Setup",
        "meta": "⭐ 4.8 • Model #14902",
        "desc": "Rear-mounted magnetic bucket that catches filament purge coils reliably.",
        "img": "https://images.unsplash.com/photo-1581092162384-8987c1d64718?w=600&auto=format&fit=crop&q=80",
        "url": "https://makerworld.com/en/models/14902-bambu-poop-chute"
    },
    {
        "name": "Micro SD & USB Hub Organizer",
        "badge": "Desk Accessory",
        "meta": "⭐ 4.8 • Model #31205",
        "desc": "Compact desktop organizer with labeled slots for MicroSD cards and USB adapters.",
        "img": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&auto=format&fit=crop&q=80",
        "url": "https://makerworld.com/en/models/31205-sd-card-holder"
    },
    {
        "name": "Collapsible Filament Funnel",
        "badge": "Maintenance",
        "meta": "⭐ 4.9 • Model #19204",
        "desc": "Print-in-place collapsible silicone/TPU funnel for pouring silica gel desiccant beads.",
        "img": "https://images.unsplash.com/photo-1581092795360-fd1ca04f0952?w=600&auto=format&fit=crop&q=80",
        "url": "https://makerworld.com/en/models/19204-collapsible-funnel"
    }
]

FEEDS = [
    {
        "url": "https://news.google.com/rss/search?q=(%22Bambu+Lab%22+OR+Bambu)+(%22H3C%22+OR+%22X2D%22+OR+%22PF008P%22+OR+%22PF004E%22+OR+%22toolchanger%22)&hl=en-US&gl=US&ceid=US:en",
        "source": "Google News",
        "category": "Priority Radar",
    },
    {
        "url": "https://news.google.com/rss/search?q=%22Bambu+Lab%22+(%22patent%22+OR+%22pre-order%22+OR+%22flagship%22+OR+%22Vortek%22)&hl=en-US&gl=US&ceid=US:en",
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
    }
]

REDDIT_RSS_URLS = [
    "https://www.reddit.com/r/BambuLab/search.rss?q=H3C+OR+%22X2D+Pro%22+OR+PF008P+OR+toolchanger&sort=new&restrict_sr=1",
    "https://www.reddit.com/r/3Dprinting/search.rss?q=%22Bambu%22+(H3C+OR+%22X2D+Pro%22+OR+flagship)&sort=new&restrict_sr=1"
]

def clean_text(raw_html: str) -> str:
    clean = re.sub(r"<[^>]+>", "", raw_html or "")
    return " ".join(clean.split())

def is_target_model(text: str) -> bool:
    """Returns True if the text directly relates to H3C or X2D Pro."""
    low = text.lower()
    return bool(re.search(r"\bh3c\b|\bx2d\s*pro\b|\bx2d-pro\b|pf008p|pf004e|10-nozzle|10 nozzle|placement rack", low))

def classify_target(text: str) -> str:
    low = text.lower()
    has_h3c = bool(re.search(r"\bh3c\b|10-nozzle|10 nozzle|placement rack|carousel", low))
    has_x2d = bool(re.search(r"\bx2d\b|\bx2d\s*pro\b|\bpf004e\b", low))
    has_fcc = bool(re.search(r"2a6j8-pf008p|pf008p", low))

    if (has_h3c and has_x2d) or has_fcc:
        return "H3C / X2D Pro"
    if has_h3c:
        return "H3C"
    if has_x2d:
        return "X2D Pro"
    return "General 3D Tech"

def is_relevant_article(text: str) -> bool:
    low = text.lower()
    if any(k in low for k in ["how do i clean my bed", "first layer issue", "clogged extruder"]):
        return False
    keywords = [
        "bambu", "h3c", "x2d", "pf008p", "pf004e", "vortek",
        "toolchanger", "multi-nozzle", "flagship", "patent", "fcc", "ams"
    ]
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
    print("Collecting news and categorizing by target priority...")
    now = datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=MAX_DAYS_OLD)

    priority_articles = []
    general_articles = []
    reddit_articles = []
    seen_urls = set()

    # 1. Web Feeds
    for feed_info in FEEDS:
        try:
            parsed = fetch_feed_data(feed_info["url"])
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
                article_obj = {
                    "id": f"web-{abs(hash(url))}",
                    "title": title,
                    "source": feed_info["source"],
                    "category": feed_info["category"],
                    "target": target,
                    "summary": (summary[:230] + "...") if len(summary) > 230 else summary,
                    "url": url,
                    "timestamp": pub_dt.strftime("%b %d, %Y"),
                    "_sort_ts": pub_dt.timestamp(),
                }

                # Separate priority targets (H3C / X2D Pro) from general 3D printing news
                if is_target_model(full_text) or "toolchanger" in full_text.lower():
                    priority_articles.append(article_obj)
                else:
                    general_articles.append(article_obj)
        except Exception as e:
            print(f"Error reading {feed_info['source']}: {e}")

    # 2. Reddit Feeds
    for r_url in REDDIT_RSS_URLS:
        try:
            parsed = fetch_feed_data(r_url)
            for entry in parsed.entries[:30]:
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

    # Sort each stream chronologically
    priority_articles.sort(key=lambda x: x["_sort_ts"], reverse=True)
    general_articles.sort(key=lambda x: x["_sort_ts"], reverse=True)
    reddit_articles.sort(key=lambda x: x["_sort_ts"], reverse=True)

    for a in priority_articles + general_articles + reddit_articles:
        if "_sort_ts" in a:
            del a["_sort_ts"]

    # Permanent anchors for the priority feed
    anchor_articles = [
        {
            "id": "fcc-pf008p",
            "title": "FCC Registration Confirms Bambu Lab H3C and X2D Pro (ID: 2A6J8-PF008P)",
            "source": "FCC Registry",
            "category": "Regulatory Filing",
            "target": "H3C / X2D Pro",
            "summary": "FCC filings confirm dual releases: the 10-nozzle H3C flagship alongside the industrial-spec X2D Pro combo.",
            "url": "https://forum.bambulab.com/t/h3c-edit-and-x2d-pro-printer-registered-with-fcc/259692",
            "timestamp": "Sept 12, 2026",
        },
        {
            "id": "patent-h3c",
            "title": "Patent Analysis: Inside the H3C Single-Motion 10-Toolhead Docking Rack",
            "source": "Makers101 Patent Breakdown",
            "category": "Hardware Analysis",
            "target": "H3C",
            "summary": "Patent CN 122560413 details how the toolhead couples locking and placement into a single high-speed stroke with magnetic spring retention.",
            "url": "https://makers101.com/bambu-lab-h3c-patent/",
            "timestamp": "Aug 21, 2026",
        }
    ]

    for anchor in anchor_articles:
        if not any(a["id"] == anchor["id"] for a in priority_articles):
            priority_articles.append(anchor)

    # Pick 4 random prints from the database on every run
    daily_prints = random.sample(MAKERWORLD_DATABASE, 4)

    payload = {
        "scan_iso": now.isoformat(),
        "last_updated": now.strftime("%B %d, %Y at %I:%M %p UTC"),
        "makerworld_picks": daily_prints,
        "priority_articles": priority_articles[:12],
        "general_articles": general_articles[:10],
        "reddit_articles": reddit_articles[:12],
    }

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Generated news.json: {len(priority_articles)} priority articles, {len(general_articles)} general, {len(reddit_articles)} reddit.")

if __name__ == "__main__":
    main()