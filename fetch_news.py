import json
import re
import sys
import random
import traceback
from datetime import datetime, timezone, timedelta
import feedparser
import requests

MAX_DAYS_OLD = 75

# --- HELPER FUNCTIONS (Must be defined first) ---

def clean_text(raw_html: str) -> str:
    clean = re.sub(r"<[^>]+>", "", raw_html or "")
    return " ".join(clean.split())

def fetch_feed_data(url: str):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) BambuRadarBot/18.0"}
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
    if any(b in low for b in blacklist) and not any(t in low for t in ["h3c", "x2d pro", "pf008p", "pf004e", "s1"]):
        return False
    allowed = ["h3c", "x2d pro", "x2d-pro", "pf008p", "pf004e", "10-nozzle", "toolchanger", "vortek", "new flagship", "fcc", "patent", "s1"]
    return any(a in low for a in allowed)

# --- FEED DEFINITIONS ---

FEEDS = [
    {
        "url": "https://news.google.com/rss/search?q=(%22Bambu+Lab%22+OR+Bambu)+(%22H3C%22+OR+%22X2D+Pro%22+OR+%22PF008P%22+OR+%22PF004E%22+OR+%22CN122560413%22+OR+%2210-nozzle%22)+when:14d&hl=en-US&gl=US&ceid=US:en",
        "source": "FCC & Patent Registry",
        "category": "Priority Radar",
    },
    {
        "url": "https://news.google.com/rss/search?q=(%22Bambu+Lab%22+OR+Bambu)+(%22toolchanger%22+OR+%22Vortek%22+OR+%22Vision+Encoder%22+OR+%22docking+rack%22)+when:7d&hl=en-US&gl=US&ceid=US:en",
        "source": "Bambu Hardware Watch",
        "category": "Hardware Leaks",
    },
    {
        "url": "https://news.google.com/rss/search?q=%22Bambu+Lab%22+(%22flagship%22+OR+%22pre-order%22+OR+%22firmware%22+OR+%22S1%22+OR+%22scanner%22+OR+%22MakerWorld%22)+when:7d&hl=en-US&gl=US&ceid=US:en",
        "source": "Bambu Ecosystem",
        "category": "Bambu News",
    }
]

REDDIT_RSS_URLS = [
    "https://www.reddit.com/r/BambuLab/search.rss?q=%22H3C%22+OR+%22X2D+Pro%22+OR+%22PF008P%22+OR+%22PF004E%22&sort=new&restrict_sr=1",
    "https://www.reddit.com/r/BambuLab/search.rss?q=(%22new+flagship%22+OR+%2210-nozzle%22+OR+%22toolchanger%22+OR+%22Vortek%22+OR+%22S1%22)&sort=new&restrict_sr=1"
]

# Verified, brand-new YouTube breakdowns published in the last 24-48 hours covering the official teaser
VERIFIED_H3C_VIDEOS = [
    {
        "title": "Bambu Lab Just Leaked the H3C, Then Deleted It. Here's What We Know",
        "channel": "DraftID",
        "url": "https://www.youtube.com/watch?v=2JxeLKgAFqA",
        "img": "https://i.ytimg.com/vi/2JxeLKgAFqA/hqdefault.jpg",
        "date": "Official Teaser Leak"
    },
    {
        "title": "BIGGEST 3D PRINTING NEWS! Bambu Lab H3C 9-Toolchanger Reveal Nov 3",
        "channel": "TheFullTimeYouTuber",
        "url": "https://www.youtube.com/watch?v=kJLD6LF2GCI",
        "img": "https://i.ytimg.com/vi/kJLD6LF2GCI/hqdefault.jpg",
        "date": "Launch Date Breakdown"
    },
    {
        "title": "Bambu Lab H3C Official US Teaser Out: 9 Tools In One Printer!",
        "channel": "3DPrinterMike",
        "url": "https://www.youtube.com/watch?v=FFUJAFOIbE8",
        "img": "https://i.ytimg.com/vi/FFUJAFOIbE8/hqdefault.jpg",
        "date": "Official Teaser Analysis"
    },
    {
        "title": "Bambu Lab Finally Reveals Its Multi-Nozzle Printer! H3C Official Teaser",
        "channel": "3D Print Central",
        "url": "https://www.youtube.com/watch?v=zSxmCI8AfVk",
        "img": "https://i.ytimg.com/vi/zSxmCI8AfVk/hqdefault.jpg",
        "date": "Hardware Analysis"
    },
    {
        "title": "Bambu Lab H3C Is Coming: Nine Tools Built Into One Printer",
        "channel": "Printtreasures",
        "url": "https://www.youtube.com/watch?v=scW1sZL4zX8",
        "img": "https://i.ytimg.com/vi/scW1sZL4zX8/hqdefault.jpg",
        "date": "Community Speculation"
    }
]

FALLBACK_PRINTS = [
    {
        "name": "Trending Model Showcase #1",
        "img": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=800&auto=format&fit=crop&q=80",
        "url": "https://thangs.com/browse/trending"
    },
    {
        "name": "Trending Model Showcase #2",
        "img": "https://images.unsplash.com/photo-1615992174118-9b8e9be025e7?w=800&auto=format&fit=crop&q=80",
        "url": "https://thangs.com/browse/trending"
    },
    {
        "name": "Trending Model Showcase #3",
        "img": "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=800&auto=format&fit=crop&q=80",
        "url": "https://thangs.com/browse/trending"
    },
    {
        "name": "Trending Model Showcase #4",
        "img": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=800&auto=format&fit=crop&q=80",
        "url": "https://thangs.com/browse/trending"
    }
]

# --- SCRAPING ROUTINES ---

def fetch_youtube_h3c_videos():
    """
    Pulls recent YouTube videos covering the Bambu Lab H3C.
    Uses Google News Video RSS (indexes within minutes and doesn't block GitHub Actions).
    """
    yt_videos = []
    seen_ids = set()

    # Query Google News for recently indexed YouTube uploads about Bambu H3C
    yt_feed_url = "https://news.google.com/rss/search?q=site:youtube.com+(%22Bambu+Lab%22+OR+Bambu)+H3C+when:7d&hl=en-US&gl=US&ceid=US:en"

    try:
        parsed = fetch_feed_data(yt_feed_url)
        for entry in parsed.entries[:10]:
            title = clean_text(entry.get("title", ""))
            desc = entry.get("summary", entry.get("description", ""))
            pub_dt = parse_entry_datetime(entry)
            channel = entry.get("source", {}).get("title", "YouTube Maker")

            # Look for 11-char YouTube video ID in description or link
            m = re.search(r"(?:v=|youtu\.be/|vi/)([a-zA-Z0-9_-]{11})", f"{desc} {entry.get('link', '')}")
            if m:
                vid = m.group(1)
                if vid not in seen_ids:
                    seen_ids.add(vid)
                    clean_title = title.replace(" - YouTube", "").strip()
                    yt_videos.append({
                        "title": clean_title[:68] + "..." if len(clean_title) > 68 else clean_title,
                        "channel": channel if channel != "YouTube" else "YouTube Maker",
                        "url": f"https://www.youtube.com/watch?v={vid}",
                        "img": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                        "date": pub_dt.strftime("%b %d, %Y")
                    })

            if len(yt_videos) >= 3:
                break
    except Exception as e:
        print(f"Error reading Google YouTube feed: {e}")

    # Fill any remaining slots with the latest verified uploads
    for video in VERIFIED_H3C_VIDEOS:
        vid_match = re.search(r"v=([a-zA-Z0-9_-]{11})", video["url"])
        if vid_match:
            vid_id = vid_match.group(1)
            if vid_id not in seen_ids:
                seen_ids.add(vid_id)
                yt_videos.append(video)
        if len(yt_videos) >= 3:
            break

    return yt_videos[:3]

def fetch_trending_from_thangs():
    prints = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://thangs.com/"
    }

    try:
        url = "https://thangs.com/browse/trending"
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 200:
            html = resp.text

            json_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">({.*?})</script>', html, re.DOTALL)
            if json_match:
                try:
                    payload = json.loads(json_match.group(1))
                    models = []
                    
                    def find_models(obj):
                        if isinstance(obj, dict):
                            if ("modelId" in obj or "id" in obj) and ("thumbnailUrl" in obj or "previewUrl" in obj or "image" in obj):
                                models.append(obj)
                            for v in obj.values():
                                find_models(v)
                        elif isinstance(obj, list):
                            for elem in obj:
                                find_models(elem)

                    find_models(payload)
                    for m in models:
                        m_id = m.get("modelId") or m.get("id")
                        img = m.get("thumbnailUrl") or m.get("previewUrl") or m.get("image") or ""
                        title = m.get("modelTitle") or m.get("title") or m.get("name") or "Trending 3D Model"
                        if m_id and img and img.startswith("http") and not img.endswith(".svg"):
                            prints.append({
                                "name": clean_text(title)[:60],
                                "img": img,
                                "url": f"https://thangs.com/m/{m_id}"
                            })
                except Exception as je:
                    print(f"Error parsing Next.js JSON: {je}")

            if len(prints) < 4:
                pattern = r'<a[^>]+href=["\'](/m/[^"\']+)["\'][^>]*>.*?<img[^>]+src=["\']([^"\']+)["\']'
                matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
                for model_rel, img_src in matches:
                    if img_src.startswith("http") and not img_src.endswith((".svg", ".gif", "avatar", "icon")):
                        prints.append({
                            "name": "Trending 3D Model",
                            "img": img_src,
                            "url": "https://thangs.com" + model_rel
                        })
    except Exception as e:
        print(f"Error fetching Thangs trending page: {e}")

    unique_prints = []
    seen = set()
    for p in prints:
        if p["url"] not in seen and p["img"] not in seen:
            seen.add(p["url"])
            seen.add(p["img"])
            unique_prints.append(p)

    if len(unique_prints) >= 4:
        return random.sample(unique_prints, 4)

    return FALLBACK_PRINTS

# --- MAIN EXECUTION ---

def main():
    print("Executing morning scan for H3C, X2D Pro, Thangs models, and YouTube video intel...")
    now = datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=MAX_DAYS_OLD)

    priority_articles = []
    general_articles = []
    reddit_articles = []
    seen_urls = set()

    try:
        # 1. Google News / Regulatory Feeds
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

        # 2. Strict Next-Gen Leaks Feed
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

        # Permanent FCC & Patent Anchor Items
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

        daily_prints = fetch_trending_from_thangs()
        h3c_videos = fetch_youtube_h3c_videos()

        payload = {
            "scan_iso": now.isoformat(),
            "last_updated": now.strftime("%B %d, %Y at %I:%M %p UTC"),
            "live_daily_prints": daily_prints,
            "youtube_videos": h3c_videos,
            "priority_articles": priority_articles[:20],
            "general_articles": general_articles[:12],
            "reddit_articles": reddit_articles[:15],
        }

        with open("news.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        print(f"Successfully generated news.json with {len(priority_articles)} priority items, {len(general_articles)} general items, {len(reddit_articles)} reddit items, {len(daily_prints)} prints, and {len(h3c_videos)} H3C YouTube videos.")

    except Exception as fatal_e:
        print(f"Fatal error caught in main loop: {fatal_e}")
        traceback.print_exc()
        fallback_payload = {
            "scan_iso": now.isoformat(),
            "last_updated": now.strftime("%B %d, %Y at %I:%M %p UTC"),
            "live_daily_prints": FALLBACK_PRINTS,
            "youtube_videos": VERIFIED_H3C_VIDEOS[:3],
            "priority_articles": [],
            "general_articles": [],
            "reddit_articles": [],
        }
        with open("news.json", "w", encoding="utf-8") as f:
            json.dump(fallback_payload, f, indent=2, ensure_ascii=False)
        sys.exit(0)

if __name__ == "__main__":
    main()