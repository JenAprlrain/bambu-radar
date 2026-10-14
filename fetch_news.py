import json
import re
from datetime import datetime, timezone, timedelta
import feedparser
import requests

MAX_DAYS_OLD = 75

# Primary Targeted Bambu Feeds
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

# Strict Reddit Feeds: Next-Gen Hardware & Leaks Only
REDDIT_RSS_URLS = [
    "https://www.reddit.com/r/BambuLab/search.rss?q=%22H3C%22+OR+%22X2D+Pro%22+OR+%22PF008P%22+OR+%22PF004E%22&sort=new&restrict_sr=1",
    "https://www.reddit.com/r/BambuLab/search.rss?q=(%22new+flagship%22+OR+%2210-nozzle%22+OR+%22toolchanger%22+OR+%22Vortek%22)&sort=new&restrict_sr=1"
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
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) BambuRadar/7.0"}
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
    tv_rss = "https://www.thingiverse.com/rss/featured"
    try:
        parsed = fetch_feed_data(tv_rss)
        for entry in parsed.entries[:6]:
            title = clean_text(entry.get("title", ""))
            summary = clean_text(entry.get("summary", entry.get("description", "")))
            link = entry.get("link", "").strip()

            img_url = ""
            raw_content = entry.get("description", "") + " " + str(entry.get("enclosures", []))
            
            cdn_match = re.search(r'https://cdn\.thingiverse\.com/renders/[^"\'\s>]+', raw_content)
            if cdn_match:
                img_url = cdn_match.group(0)
            elif "media_thumbnail" in entry and len(entry["media_thumbnail"]) > 0:
                img_url = entry["media_thumbnail"][0].get("url", "")
            elif "enclosures" in entry and len(entry["enclosures"]) > 0:
                img_url = entry["enclosures"][0].get("href", "")

            if title and link:
                prints.append({
                    "name": title,
                    "badge": "Daily Featured Print",
                    "meta": "⭐ Community Design",
                    "desc": (summary[:180] + "...") if len(summary) > 180 else summary or "Open model to view slicing details, STL files, and print settings.",
                    "img": img_url,
                    "url": link
                })
                if len(prints) >= 4:
                    break
    except Exception as e:
        print(f"Error fetching live print stream: {e}")

    if len(prints) < 4:
        try:
            r_prints = fetch_feed_data("https://www.reddit.com/r/3Dprinting/search.rss?q=flair%3A%22Print%22+OR+flair%3A%22Design%22&sort=hot&restrict_sr=1")
            for entry in r_prints.entries[:8]:
                title = clean_text(entry.get("title", ""))
                link = entry.get("link", "")
                raw_desc = entry.get("description", "")
                m = re.search(r'https://preview\.redd\.it/[^"\'>\s]+', raw_desc)
                img_url = m.group(0).replace("&amp;", "&") if m else ""

                if title and link:
                    prints.append({
                        "name": title,
                        "badge": "Community Project",
                        "meta": "💬 Reddit Showcase",
                        "desc": "Fresh daily 3D print project shared by the maker community with settings and design notes.",
                        "img": img_url,
                        "url": link
                    })
                if len(prints) >= 4:
                    break
        except Exception as e:
            print(f"Reddit showcase fetch error: {e}")

    return prints[:4]

def main():
    print("Executing morning scan for H3C, X2D Pro, and live daily prints...")
    now = datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=MAX_DAYS_OLD)

    priority_articles = []
    general_articles = []
    reddit_articles = []
    seen_urls = set()

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

    print(f"Generated news.json: {len(priority_articles)} priority, {len(general_articles)} Bambu general, {len(reddit_articles)} reddit, {len(daily_prints)} live prints.")

if __name__ == "__main__":
    main()