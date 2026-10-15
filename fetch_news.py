def fetch_live_prints_from_web():
    """
    Fetches real-time, top daily showcase prints from Reddit's public JSON API.
    Guarantees fresh community creations with valid direct image links.
    """
    prints = []
    # Query top daily showcase & functional prints
    url = "https://www.reddit.com/r/functionalprint/top.json?t=week&limit=15"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) BambuRadarBot/8.0"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            children = data.get("data", {}).get("children", [])
            for child in children:
                pdata = child.get("data", {})
                title = clean_text(pdata.get("title", ""))
                permalink = "https://www.reddit.com" + pdata.get("permalink", "")
                ups = pdata.get("ups", 0)
                
                # Extract the real high-res preview image
                img_url = ""
                if "preview" in pdata and "images" in pdata["preview"] and len(pdata["preview"]["images"]) > 0:
                    img_url = pdata["preview"]["images"][0].get("source", {}).get("url", "").replace("&amp;", "&")
                elif pdata.get("url", "").endswith((".jpg", ".png", ".jpeg", ".webp")):
                    img_url = pdata.get("url", "")

                # Skip posts without an image or stickied mod posts
                if not img_url or pdata.get("stickied", False):
                    continue

                prints.append({
                    "name": title[:65] + "..." if len(title) > 65 else title,
                    "badge": "Community Design",
                    "meta": f"👍 {ups:,} Upvotes • r/functionalprint",
                    "desc": "Trending community project with shared print settings, material choices, and design notes.",
                    "img": img_url,
                    "url": permalink
                })

                if len(prints) >= 4:
                    break
    except Exception as e:
        print(f"Error fetching live Reddit showcase prints: {e}")

    # Fallback to r/3Dprinting if functionalprint had fewer than 4
    if len(prints) < 4:
        try:
            url_alt = "https://www.reddit.com/r/3Dprinting/top.json?t=day&limit=15"
            resp = requests.get(url_alt, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for child in data.get("data", {}).get("children", []):
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
                        "badge": "Daily Showcase",
                        "meta": f"👍 {ups:,} Upvotes • r/3Dprinting",
                        "desc": "Featured community print with slicer settings, layer height, and discussion.",
                        "img": img_url,
                        "url": permalink
                    })

                    if len(prints) >= 4:
                        break
        except Exception as e:
            print(f"Fallback fetch error: {e}")

    return prints[:4]