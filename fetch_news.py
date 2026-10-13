import json
import re
from datetime import datetime, timezone
import feedparser
import requests

FEEDS = [
    # Google News RSS for Bambu Lab new/flagship printer
    {
        "url": "https://news.google.com/rss/search?q=Bambu+Lab+new+printer+OR+flagship+3D+printer&hl=en-US&gl=US&ceid=US:en",
        "source": "Google News",
        "category": "Bambu Leaks",
    },
    # 3D Printing Industry RSS
    {
        "url": "https://3dprintingindustry.com/feed/",
        "source": "3D Printing Industry",
        "category": "Tech & Filament",
    },
]

REDDIT_URL = "https://www.reddit.com/r/BambuLab/search.json?q=new+printer+OR+next+gen+OR+flagship&sort=new&restrict_sr=1&limit=15"

KEYWORDS = [
    "bambu", "flagship", "next gen", "leak", "faster", "h2", "xl",
    "speed", "corexy", "firmware", "announcement", "teaser"
]


def clean_text(raw_html: str) -> str:
    """Strip basic HTML tags and clean whitespace."""
    clean = re.sub(r"<[^>]+>", "", raw_html or "")
    return " ".join(clean.split())


def is_relevant(text: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in KEYWORDS)


def fetch_reddit():
    items = []
    headers = {"User-Agent": "BambuRadarBot/1.0 (morning dashboard tracker)"}
    try:
        resp = requests.get(REDDIT_URL, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            posts = data.get("data", {}).get("children", [])
            for p in posts:
                post = p.get("data", {})
                title = post.get("title", "")
                selftext = post.get("selftext", "")
                if is_relevant(title) or is_relevant(selftext):
                    items.append({
                        "id": f"reddit-{post.get('id')}",
                        "title": title,
                        "source": "r/BambuLab",
                        "category": "Community Speculation",
                        "summary": (selftext[:220] + "...") if len(selftext) > 220 else selftext or "Reddit community discussion.",
                        "url": f"https://reddit.com{post.get('permalink')}",
                        "timestamp": datetime.fromtimestamp(post.get("created_utc", 0), tz=timezone.utc).strftime("%b %d, %Y"),
                    })
    except Exception as e:
        print(f"Error fetching Reddit: {e}")
    return items


def fetch_rss_feeds():
    items = []
    for f in FEEDS:
        try:
            parsed = feedparser.parse(f["url"])
            for entry in parsed.entries[:8]:
                title = entry.get("title", "")
                summary = clean_text(entry.get("summary", ""))

                # Apply keyword filter to general 3D printing news
                if f["source"] != "Google News" and not is_relevant(title + " " + summary):
                    continue

                items.append({
                    "id": f"rss-{abs(hash(entry.get('link', title)))}",
                    "title": title,
                    "source": f["source"],
                    "category": f["category"],
                    "summary": (summary[:220] + "...") if len(summary) > 220 else summary or "Click link to view article.",
                    "url": entry.get("link", "#"),
                    "timestamp": datetime.now(timezone.utc).strftime("%b %d, %Y"),
                })
        except Exception as e:
            print(f"Error parsing feed {f['url']}: {e}")
    return items


def main():
    print("Collecting news entries...")
    entries = fetch_reddit() + fetch_rss_feeds()

    # Deduplicate by URL or title
    seen = set()
    unique_entries = []
    for item in entries:
        key = item["url"].split("?")[0].strip() or item["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique_entries.append(item)

    payload = {
        "last_updated": datetime.now(timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC"),
        "total": len(unique_entries),
        "articles": unique_entries[:20],  # Keep latest 20 items
    }

    with open("news.json", "w", encoding="utf-8") as out:
        json.dump(payload, out, indent=2, ensure_ascii=False)

    print(f"Successfully generated news.json with {len(payload['articles'])} articles.")


if __name__ == "__main__":
    main()