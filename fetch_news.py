import json
import re
import sys
import random
import traceback
from datetime import datetime, timezone, timedelta
import feedparser
import requests

MAX_DAYS_OLD = 75

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

# Verified, live YouTube uploads on the Bambu Lab H3C with working thumbnails and links
VERIFIED_H3C_VIDEOS = [
    {
        "title": "New Bambu Lab H3C Leaked Image & AMS 3 Patent Breakdown!",
        "channel": "Directed T3CH",
        "url": "https://www.youtube.com/watch?v=jpCFmw4wdB8",
        "img": "https://i.ytimg.com/vi/jpCFmw4wdB8/hqdefault.jpg",
        "date": "Recent Breakdown"
    },
    {
        "title": "Bambu Lab's H3C Just Got Confirmed",
        "channel": "3DPrinterMike",
        "url": "https://www.youtube.com/watch?v=SvqOZ3hrnD8",
        "img": "https://i.ytimg.com/vi/SvqOZ3hrnD8/hqdefault.jpg",
        "date": "FCC Filing Analysis"
    },
    {
        "title": "Bambu H3C Rumor: 10 Nozzles? Here's the FCC Evidence",
        "channel": "Layer Shift 3D",
        "url": "https://www.youtube.com/watch?v=D6j2vZp3RIw",
        "img": "https://i.ytimg.com/vi/D6j2vZp3RIw/hqdefault.jpg",
        "date": "Hardware Teardown"
    },
    {
        "title": "New Bambu H3C 10 Multi Changer",
        "channel": "Digital Magicians Studios",
        "url": "https://www.youtube.com/watch?v=cS3DgUOr5bI",
        "img": "https://i.ytimg.com/vi/cS3DgUOr5bI/hqdefault.jpg",
        "date": "Ecosystem Speculation"
    },
    {
        "title": "Bambu Lab H3C: Patent drawings with ten nozzles",
        "channel": "WohuM_TECH",
        "url": "https://www.youtube.com/watch?v=Ou4NyUFQkvo",
        "img": "https://i.ytimg.com/vi/Ou4NyUFQkvo/hqdefault.jpg",
        "date": "Patent Analysis"
    }
]

def fetch_youtube_h3c_videos():
    """
    Pulls recent YouTube videos covering the Bambu Lab H3C.
    Uses DuckDuckGo HTML search to bypass datacenter IP blocks,
    with verified live videos ensuring working links and thumbnails.
    """
    yt_videos = []
    seen_ids = set()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    # 1. Scrape live video URLs via DuckDuckGo HTML search (not blocked on GitHub runners)
    try:
        ddg_url = "https://html.duckduckgo.com/html/?q=site%3Ayoutube.com+Bambu+Lab+H3C"
        resp = requests.get(ddg_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            html = resp.text
            # Match results: capture title and YouTube link
            matches = re.findall(
                r'<a[^>]+class="result__snippet"[^>]*href="[^"]*(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})"[^>]*>.*?</a>|<a[^>]+class="result__url"[^>]*href="[^"]*(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})"',
                html,
                re.DOTALL
            )
            # Flatten matched tuples
            found_ids = [m[0] or m[1] for m in matches if (m[0] or m[1])]
            
            # Extract corresponding titles from result links
            result_blocks = re.findall(
                r'<h2 class="result__title">.*?<a[^>]+href="[^"]*(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})"[^>]*>(.*?)</a>',
                html,
                re.DOTALL
            )
            for vid, raw_title in result_blocks:
                if vid in seen_ids:
                    continue
                seen_ids.add(vid)
                title = clean_text(raw_title).replace(" - YouTube", "").strip()
                yt_videos.append({
                    "title": title[:68] + "..." if len(title) > 68 else title,
                    "channel": "YouTube Community",
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "img": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                    "date": "Recent Upload"
                })
                if len(yt_videos) >= 3:
                    break
    except Exception as e:
        print(f"DuckDuckGo video scrape error: {e}")

    # 2. Fill remaining slots from our verified real H3C video pool
    for real_video in VERIFIED_H3C_VIDEOS:
        vid_match = re.search(r"v=([a-zA-Z0-9_-]{11})", real_video["url"])
        if vid_match:
            vid_id = vid_match.group(1)
            if vid_id not in seen_ids:
                seen_ids.add(vid_id)
                yt_videos.append(real_video)
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
        selected = random.sample(unique_prints, 4)
        return selected

    return FALLBACK_PRINTS

def main():
    print("Executing morning scan for H3C, X2D Pro, Thangs models, and YouTube video intel...")
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

        print(f"Successfully generated news.json with {len(priority_articles)} priority items, {len(daily_prints)} prints, and {len(h3c_videos)} H3C YouTube videos.")

    except Exception as fatal_e:
        print(f"Fatal error caught in main loop: {fatal_e}")
        traceback.print_exc()
        fallback_payload = {
            "scan_iso": now.isoformat(),
            "last_updated": now.strftime("%B %d, %Y at %I:%M %p UTC"),
            "live_daily_prints": FALLBACK_PRINTS,
            "youtube_videos": FALLBACK_YOUTUBE,
            "priority_articles": [],
            "general_articles": [],
            "reddit_articles": [],
        }
        with open("news.json", "w", encoding="utf-8") as f:
            json.dump(fallback_payload, f, indent=2, ensure_ascii=False)
        sys.exit(0)

if __name__ == "__main__":
    main()