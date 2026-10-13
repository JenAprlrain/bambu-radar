def fetch_live_prints_from_web():
    """
    Pulls live popular/featured community 3D prints from Thingiverse's public explore stream
    and extracts direct CDN image paths.
    """
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
            
            # Extract direct CDN image URLs
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

    # Fallback to Reddit r/3Dprinting showcase with direct preview images if needed
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
                        "desc": "Fresh 3D print project shared by the maker community with settings and design notes.",
                        "img": img_url,
                        "url": link
                    })
                if len(prints) >= 4:
                    break
        except Exception as e:
            print(f"Reddit showcase fetch error: {e}")

    return prints[:4]