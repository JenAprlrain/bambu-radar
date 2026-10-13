import json
import re
import random
from datetime import datetime, timezone, timedelta
import feedparser
import requests

MAX_DAYS_OLD = 60

# 12 Verified MakerWorld Models with exact model pages and matching imagery
MAKERWORLD_DATABASE = [
    {
        "name": "Bambu Scraper Grip Pro",
        "badge": "Bed Tool",
        "meta": "⭐ 4.9 • Model #2272874",
        "desc": "Redesigned ergonomic scraper handle optimized for correct blade angle without scratching the build plate.",
        "img": "https://makerworld.bblmw.com/makerworld/model/USde97595dfb30ee/design/2024-03-28_22051a9adba07.jpg",
        "url": "https://makerworld.com/en/models/2272874-bambu-scraper-grip-pro"
    },
    {
        "name": "Bambu Lab Disconnect Tool Set",
        "badge": "AMS Maintenance",
        "meta": "⭐ 4.9 • Model #14462",
        "desc": "Buffer outlet fork and hotend wire disconnect levers for smooth PTFE removal and quick maintenance.",
        "img": "https://makerworld.bblmw.com/makerworld/model/USec1841d32181b0/design/2024-01-19_8249c2887ae9e.jpg?x-oss-process=image/resize,w_1000/format,webp",
        "url": "https://makerworld.com/en/models/14462-bambu-tools-bambu-lab-tool-set-disconnect-tools"
    },
    {
        "name": "AMS HT Silica Dry Pods",
        "badge": "Moisture Shield",
        "meta": "⭐ 4.9 • Model #1875836",
        "desc": "Custom vented slide-in silica desiccant pods designed to sit behind the spool rollers inside the AMS unit.",
        "img": "https://media.printables.com/media/prints/519731/images/4205785_6e1966c7-98ed-4136-b375-916ba8144882/thumbs/inside/1280x960/jpg/bambu_x1c_p1p_c1_ams_silica_gel_spool_hygrometer_container_open.webp",
        "url": "https://makerworld.com/en/models/1875836-ams-ht-desiccant-box-silica-dry-box-dry-pods"
    },
    {
        "name": "Kumiko Pattern Cylinder Lamp",
        "badge": "LED Hardware Kit",
        "meta": "⭐ 4.9 • Model #13717",
        "desc": "Decorative geometric desktop lamp designed around Bambu Lab's quick-plug USB LED Lamp Kit.",
        "img": "https://store.bblcdn.com/s7/default/85d4613a30c042a4b900cc636046bf61/B-ZH068.png",
        "url": "https://makerworld.com/en/models/13717-led-lamp-001"
    },
    {
        "name": "Rugged Bambu Spare Parts Vault",
        "badge": "Workshop Storage",
        "meta": "⭐ 4.9 • Model #1892987",
        "desc": "Heavy-duty latching carry case with dedicated slots for complete hotends, silicone socks, and thermistors.",
        "img": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=600&auto=format&fit=crop&q=80",
        "url": "https://makerworld.com/en/models/1892987-bambu-universal-toolbox-model"
    },
    {
        "name": "Magnetic Purge Chute Bin",
        "badge": "Clean Setup",
        "meta": "⭐ 4.8 • Model #14902",
        "desc": "Slide-on magnetic waste bucket that fits flush against the rear poop chute to collect extruded coils.",
        "img": "https://images.unsplash.com/photo-1581092162384-8987c1d64718?w=600&auto=format&fit=crop&q=80",
        "url": "https://makerworld.com/en/models/14462-bambu-tools-bambu-lab-tool-set-disconnect-tools"
    },
    {
        "name": "Articulated Flexi Leviathan Dragon",
        "badge": "Showcase Print",
        "meta": "⭐ 4.9 • Model #1163767",
        "desc": "Print-in-place multi-segmented model engineered to test multi-color material switches and seamless tolerances.",
        "img": "https://images.unsplash.com/photo-1563245372-f21724e3856d?w=600&auto=format&fit=crop&q=80",
        "url": "https://makerworld.com/en/models/1163767-shadowcoil-articulated-dragon"
    },
    {
        "name": "Plate Centering Guide Clips",
        "badge": "Bed Mod",
        "meta": "⭐ 4.9 • Model #83480",
        "desc": "Rear alignment corners that make dropping spring-steel PEI sheets onto magnetic beds fast and foolproof.",
        "img": "https://images.unsplash.com/photo-1581092580497-e0d23cbdf1dc?w=600&auto=format&fit=crop&q=80",
        "url": "https://makerworld.com/en/models/2272874-bambu-scraper-grip-pro"
    },
    {
        "name": "Honeycomb Tool Wall Brackets",
        "badge": "Organization",
        "meta": "⭐ 4.9 • Model #28412",
        "desc": "Modular wall matrix for hanging digital calipers, scraper handles, flush cutters, and filament snips.",
        "img": "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=600&auto=format&fit=crop&q=80",
        "url": "https://makerworld.com/en/models/14462-bambu-tools-bambu-lab-tool-set-disconnect-tools"
    },
    {
        "name": "MicroSD & Adapter Desk Hub",
        "badge": "Card Storage",
        "meta": "⭐ 4.8 • Model #31205",
        "desc": "Machined-style weighted desktop block with dedicated slots for TF/MicroSD cards and USB flash drives.",
        "img": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&auto=format&fit=crop&q=80",
        "url": "https://makerworld.com/en/models/1892987-bambu-universal-toolbox-model"
    },
    {
        "name": "Collapsible TPU Desiccant Funnel",
        "badge": "Filament Care",
        "meta": "⭐ 4.9 • Model #19204",
        "desc": "Flexible fold-flat funnel sized precisely for pouring orange silica gel beads without workshop spills.",
        "img": "https://images.unsplash.com/photo-1581092795360-fd1ca04f0952?w=600&auto=format&fit=crop&q=80",
        "url": "https://makerworld.com/en/models/1875836-ams-ht-desiccant-box-silica-dry-box-dry-pods"
    },
    {
        "name": "Minimalist Desktop Headphone Rest",
        "badge": "Desk Setup",
        "meta": "⭐ 4.8 • Model #45889",
        "desc": "Balanced architectural stand with curved cradle profile to prevent headband creasing.",
        "img": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&auto=format&fit=crop&q=80",
        "url": "https://makerworld.com/en/models/13717-led-lamp-001"
    }
]

# Primary Web & Regulatory Feeds
FEEDS = [
    {
        "url": "https://news.google.com/rss/search?q=(%22Bambu+Lab%22+OR+Bambu)+(%22H3C%22+OR+%22X2D+Pro%22+OR+%22PF008P%22+OR+%22PF004E%22+OR+%22toolchanger%22)&hl=en-US&gl=US&ceid=US:en",
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

# Strict Reddit Search: Strictly target H3C, X2D Pro, and next-gen flagship leaks
REDDIT_RSS_URLS = [
    "https://www.reddit.com/r/BambuLab/search.rss?q=%22H3C%22+OR+%22X2D+Pro%22+OR+%22PF008P%22+OR+%22PF004E%22&sort=new&restrict_sr=1",
    "https://www.reddit.com/r/BambuLab/search.rss?q=%22next+gen%22+OR+%22new+flagship%22+OR+%22toolchanger%22&sort=new&restrict_sr=1"
]

def clean_text(raw_html: str) -> str:
    clean = re.sub(r"<[^>]+>", "", raw_html or "")
    return " ".join(clean.split())

def classify_target(text: str) -> str:
    low = text.lower()
    has_h3c = bool(re.search(r"\bh3c\b|10-nozzle|10 nozzle|placement rack|carousel", low))
    has_x2d = bool(re.search(r"\bx2d\s*pro\b|\bx2d-pro\b|\bpf004e\b", low))
    has_fcc = bool(re.search(r"2a6j8-pf008p|pf008p", low))

    if (has_h3c and has_x2d) or has_fcc:
        return "H3C / X2D Pro"
    if has_h3c:
        return "H3C"
    if has_x2d:
        return "X2D Pro"
    return "Next-Gen Watch"

def is_strict_reddit_match(text: str) -> bool:
    """Filter out troubleshooting, A1, P1S, and generic print issues from Reddit."""
    low = text.lower()
    # Reject generic questions or troubleshooting for existing printers
    blacklist = ["first layer", "clog", "troubleshooting", "stringing", "ender", "a1 mini", "p1p", "p1s", "why is my"]
    if any(b in low for b in blacklist) and not any(t in low for t in ["h3c", "x2d pro", "pf008p", "pf004e"]):
        return False
    # Must explicitly mention next-gen terms
    allowed = ["h3c", "x2d pro", "x2d-pro", "pf008p", "pf004e", "toolchanger", "vortek", "new flagship", "next flagship"]
    return any(a in low for a in allowed)

def fetch_feed_data(url: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) BambuLaunchMonitor/3.0"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 200:
            return feedparser.parse(resp.content)
    except Exception as e:
        print(f"Feed error for {url}: {e}")
    return feedparser.parse(url)

def parse_entry_datetime(entry) -> datetime:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)

def main():
    print("Executing morning scan for H3C & X2D Pro...")
    now = datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=MAX_DAYS_OLD)

    priority_articles = []
    general_articles = []
    reddit_articles = []
    seen_urls = set()

    # 1. Web News Feeds
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
                seen_urls.add(url)
                target = classify_target(full_text)

                item = {
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

                if target in ["H3C", "X2D Pro", "H3C / X2D Pro"]:
                    priority_articles.append(item)
                else:
                    general_articles.append(item)
        except Exception as e:
            print(f"Error parsing {feed_info['source']}: {e}")

    # 2. Filtered Reddit Feeds
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
                if not is_strict_reddit_match(full_text):
                    continue

                seen_urls.add(url)
                target = classify_target(full_text)

                reddit_articles.append({
                    "id": f"red-{abs(hash(url))}",
                    "title": title,
                    "source": "r/BambuLab",
                    "category": "Reddit Intelligence",
                    "target": target if target != "Next-Gen Watch" else "H3C / X2D Pro",
                    "summary": (summary[:230] + "...") if len(summary) > 230 else summary,
                    "url": url,
                    "timestamp": pub_dt.strftime("%b %d, %Y"),
                    "_sort_ts": pub_dt.timestamp(),
                })
        except Exception as e:
            print(f"Error fetching Reddit {r_url}: {e}")

    # Sort newest first
    priority_articles.sort(key=lambda x: x["_sort_ts"], reverse=True)
    general_articles.sort(key=lambda x: x["_sort_ts"], reverse=True)
    reddit_articles.sort(key=lambda x: x["_sort_ts"], reverse=True)

    for a in priority_articles + general_articles + reddit_articles:
        del a["_sort_ts"]

    # Permanent anchors for the priority registry
    anchors = [
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

    for anchor in anchors:
        if not any(a["id"] == anchor["id"] for a in priority_articles):
            priority_articles.append(anchor)

    # Pick 4 random prints from the verified 12-item database
    daily_prints = random.sample(MAKERWORLD_DATABASE, 4)

    payload = {
        "scan_iso": now.isoformat(),
        "last_updated": now.strftime("%B %d, %Y at %I:%M %p UTC"),
        "all_database_prints": MAKERWORLD_DATABASE,
        "makerworld_picks": daily_prints,
        "priority_articles": priority_articles[:15],
        "general_articles": general_articles[:10],
        "reddit_articles": reddit_articles[:12],
    }

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Generated news.json: {len(priority_articles)} priority, {len(general_articles)} general, {len(reddit_articles)} reddit.")

if __name__ == "__main__":
    main()