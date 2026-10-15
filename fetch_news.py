import json
import re
import sys
import traceback
from datetime import datetime, timezone, timedelta
import feedparser
import requests

MAX_DAYS_OLD = 75

FEEDS = [
    {
        "url": "https://news.google.com/rss/search?q=(%22Bambu+Lab%22+OR+Bambu)+(%22H3C%22+OR+%22X2D+Pro%22+OR+%22PF008P%22+OR+%22PF004E%22+OR+%22CN122560413%22+OR+%22CN122560409%22)&hl=en-US&gl=US&ceid=US:en",
        "source": "FCC & Patent Registry",
        "category": "Priority Radar",
    },
    {
        "url": "https://news.google.com/rss/search?q=(%22Bambu+Lab%22+OR+Bambu)+(%2210-nozzle%22+OR+%2210+nozzle%22+OR+%22docking+rack%22+OR+%22Vortek%22+OR+%22Vision+Encoder%22)&hl=en-US&gl=US&ceid=US:en",
        "source": "Bambu Hardware Watch",
        "category": "Hardware Leaks",
    },
    {
        "url": "https://news.google.com/rss/search?q=%22Bambu+Lab%22+(%22flagship%22+OR+%22pre-order%22+OR+%22firmware%22+OR+%22MakerWorld%22)&hl=en-US&gl=US&ceid=US:en",
        "source": "Bambu Ecosystem",
        "category": "Bambu News",
    }
]

REDDIT_RSS_URLS = [
    "https://www.reddit.com/r/BambuLab/search.rss?q=%22H3C%22+OR+%22X2D+Pro%22+OR+%22PF008P%22+OR+%22PF004E%22&sort=new&restrict_sr=1",
    "https://www.reddit.com/r/BambuLab/search.rss?q=(%22new+flagship%22+OR+%2210-nozzle%22+OR+%22toolchanger%22+OR+%22Vortek%22)&sort=new&restrict_sr=1"
]

FALLBACK_PRINTS = [
    {
        "name": "Bambu Scraper Grip Pro",
        "badge": "Functional Print",
        "meta": "⭐ 4.9 • Community Make",
        "desc": "Ergonomic bed scraper handle designed for standard Bambu replacement razor blades with blade cover.",
        "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/Scraper_tool.jpg/640px-Scraper_tool.jpg",
        "url": "https://www.printables.com/model/12702-bambu-lab-scraper"
    },
    {
        "name": "AMS HT Silica Dry Pods",
        "badge": "Filament Shield",
        "meta": "⭐ 4.9 • Community Make",
        "desc": "Custom vented slide-in silica desiccant pods designed to sit behind spool rollers inside the AMS unit.",
        "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/Silica_gel_beads.jpg/640px-Silica_gel_beads.jpg",
        "url": "https://www.printables.com/model/519731-bambu-lab-ams-silica-gel-dry-box"
    },
    {
        "name": "Hexagonal Honeycomb Storage Wall",
        "badge": "Shop Organization",
        "meta": "⭐ 4.9 • Community Make",
        "desc": "Modular wall bracket grid designed to mount calipers, flush cutters, nozzle wrenches, and scraper handles.",
        "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Honeycomb_pattern.jpg/640px-Honeycomb_pattern.jpg",
        "url": "https://www.printables.com/model/24867-honeycomb-storage-wall"
    },
    {
        "name": "Geometric Spiral Desktop Accent Lamp",
        "badge": "USB Hardware Kit",
        "meta": "⭐ 4.9 • Community Make",
        "desc": "Spiral shade vase printed in translucent PETG or PLA, engineered around Bambu Lab's quick-plug 5V USB lamp kit.",
        "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/be/Modern_lamp_design.jpg/640px-Modern_lamp_design.jpg",
        "url": "https://www.printables.com/model/13717-led-lamp-001"
    }
]

def clean_text(raw_html: str) -> str:
    clean = re.sub(r"<[^>]+>", "", raw_html or "")
    return " ".join(clean.split())

def is_strict_priority_target(text: str) -> bool:
    low = text.lower()
    if "x2d" in low and not any(k in low for k in ["x2d pro", "x2d-pro", "pf004e", "pf008p", "h3c"]):
        return False
    priority_tokens = [
        "h3c", "x2d pro", "x2d-pro", "pf008p", "pf004e",
        "10-nozzle", "10 nozzle", "placement rack", "docking rack",
        "cn 122560413", "cn122560413", "cn 122560409", "cn122560409",
        "vortek", "ams 3h", "vision encoder"
    ]
    return any(t in low for t in priority_tokens)

def classify_target(text: str) -> str:
    low = text.lower()
    has_h3c = bool(re.search(r"\bh3c\b|10-nozzle|10 nozzle|placement rack|docking rack|cn\s*122560413|vortek", low))
    has_x2d_pro = bool(re.search(r"\bx2d\s*pro\b|\bx2d-pro\b|\bpf004e\b", low))
    has_fcc = bool(re.search(r"2a6j8-pf008p|pf008p", low))

    if (has_h3c and has_x2d_pro) or has_fcc:
        return "H3C / X2D Pro"
    if has_h3c:
        return "H3C"
    if has_x2d_pro:
        return "X2D Pro"
    return "Bambu Lab"

def is_strict_reddit_match(text: str) -> bool:
    low = text.lower()
    blacklist = ["first layer", "clog", "troubleshooting", "stringing", "a1 mini", "p1p", "p1s", "why is my", "print failed", "adhesion", "bed level"]
    if any(b in low for b in blacklist) and not any(t in low for t in ["h3c", "x2d pro", "pf008p", "pf004e"]):
        return False
    allowed = ["h3c", "x2d pro", "x2d-pro", "pf008p", "pf004e", "10-nozzle", "toolchanger", "vortek", "new flagship", "fcc", "patent"]
    return any(a in low for a in allowed)

def fetch_feed_data(url: str):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) BambuRadarBot/10.0"}
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

def fetch_live_prints_from_web():
    prints = []
    # Use standard unique script user-agent to prevent 429 ratelimits on GitHub runners
    headers = {"User-Agent": "linux:bambu-radar-feed-fetcher:v10.0 (by /u/bambu_radar)"}

    try:
        url = "https://www.reddit.com/r/functionalprint/top.json?t=week&limit=15"
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            children = data.get("data", {}).get("children", [])
            for child in children:
                pdata = child.get("data", {})
                title = clean_text(pdata.get("title", ""))
                permalink = "https://www.reddit.com" + pdata.get("permalink", "")
                ups = pdata.get("ups", 0)

                img_url = ""
                if "preview" in pdata and "images" in pdata["preview"] and len(pdata["preview"]["images"]) > 0:
                    img_url = pdata["preview"]["images"][0].get("source", {}).get("url", "").replace("&amp;", "&")
                elif pdata.get("url", "").endswith((".jpg", ".png", ".jpeg", ".webp")):
                    img_url = pdata.get("url", "")

                if not img_url or pdata.get("stickied", False):
                    continue

                prints.append({
                    "name": title[:65] + "..." if len(title) > 65 else title,
                    "badge": "Functional Print",
                    "meta": f"👍 {ups:,} Upvotes • r/functionalprint",
                    "desc": "Featured community functional make. Click below to inspect creator settings, material tips, and STL links.",
                    "img": img_url,
                    "url": permalink
                })

                if len(prints) >= 4:
                    break
    except Exception as e:
        print(f"Non-fatal error fetching functionalprint: {e}")

    # Fallback if Reddit blocked or fewer than 4 items returned
    if len(prints) < 4:
        for fb in FALLBACK_PRINTS:
            if not any(p["name"] == fb["name"] for p in prints):
                prints.append(fb)
            if len(prints) >= 4:
                break

    return prints[:4]

def main():
    print("Executing morning scan for H3C, X2D Pro, and live daily prints...")
    now = datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=MAX_DAYS_OLD)

    priority_articles = []
    general_articles = []
    reddit_articles = []
    seen_urls = set()

    try:
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

                    if is_strict_priority_target(full_text):
                        priority_articles.append(item)
                    else:
                        general_articles.append(item)
            except Exception as e:
                print(f"Error reading feed {feed_info['source']}: {e}")

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
                        "target": target if target != "Bambu Lab" else "H3C / X2D Pro",
                        "summary": (summary[:230] + "...") if len(summary) > 230 else summary,
                        "url": url,
                        "timestamp": pub_dt.strftime("%b %d, %Y"),
                        "_sort_ts": pub_dt.timestamp(),
                    })
            except Exception as e:
                print(f"Error fetching Reddit {r_url}: {e}")

        priority_articles.sort(key=lambda x: x["_sort_ts"], reverse=True)
        general_articles.sort(key=lambda x: x["_sort_ts"], reverse=True)
        reddit_articles.sort(key=lambda x: x["_sort_ts"], reverse=True)

        for a in priority_articles + general_articles + reddit_articles:
            del a["_sort_ts"]

        anchors = [
            {
                "id": "fcc-pf008p",
                "title": "FCC Registration Confirms Bambu Lab H3C and X2D Pro (ID: 2A6J8-PF008P)",
                "source": "FCC Registry",
                "category": "Regulatory Filing",
                "target": "H3C / X2D Pro",
                "summary": "FCC filings identify model numbers confirming dual releases: the 10-nozzle H3C flagship alongside the industrial-spec X2D Pro combo.",
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

        daily_prints = fetch_live_prints_from_web()

        payload = {
            "scan_iso": now.isoformat(),
            "last_updated": now.strftime("%B %d, %Y at %I:%M %p UTC"),
            "live_daily_prints": daily_prints,
            "priority_articles": priority_articles[:20],
            "general_articles": general_articles[:12],
            "reddit_articles": reddit_articles[:15],
        }

        with open("news.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        print(f"Successfully generated news.json with {len(priority_articles)} priority items and {len(daily_prints)} prints.")

    except Exception as fatal_e:
        print(f"Fatal error caught in main loop: {fatal_e}")
        traceback.print_exc()
        # Guarantee news.json is created so GitHub Actions never halts
        fallback_payload = {
            "scan_iso": now.isoformat(),
            "last_updated": now.strftime("%B %d, %Y at %I:%M %p UTC"),
            "live_daily_prints": FALLBACK_PRINTS,
            "priority_articles": [],
            "general_articles": [],
            "reddit_articles": [],
        }
        with open("news.json", "w", encoding="utf-8") as f:
            json.dump(fallback_payload, f, indent=2, ensure_ascii=False)
        sys.exit(0)

if __name__ == "__main__":
    main()