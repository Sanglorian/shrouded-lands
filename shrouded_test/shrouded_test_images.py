import os
import json
import time
from pathlib import Path

import requests

# ---------- CONFIG ----------

WIKI_API = "https://shrouded-lands.fandom.com/api.php"

BASE_DIR = Path("shrouded_test_output")
INDEX_PATH = BASE_DIR / "index.jsonl"
IMAGES_DIR = BASE_DIR / "images"
IMAGE_INDEX_PATH = BASE_DIR / "image_index.jsonl"
FILE_PAGES_DIR = BASE_DIR / "file_pages"

USER_AGENT = "ShroudedLandsImageTest/0.1 (your_email@example.com)"
REQUEST_DELAY = 0.5  # seconds between API calls


# ---------- HELPERS ----------

def safe_filename(name: str) -> str:
    bad_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for ch in bad_chars:
        name = name.replace(ch, "_")
    return name


def save_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})


def api_get(params):
    """Helper around GET with simple retry."""
    while True:
        try:
            r = session.get(WIKI_API, params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"[ERROR] API request failed: {e}. Retrying in 5s...")
            time.sleep(5)


def get_pages_from_index():
    """
    Read index.jsonl created by shrouded_test.py
    and yield (pageid, title).
    """
    if not INDEX_PATH.exists():
        raise FileNotFoundError(
            f"{INDEX_PATH} not found. Run shrouded_test.py first."
        )

    with INDEX_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            yield rec["pageid"], rec["title"]


def get_images_used_by_page(pageid):
    """
    For a given pageid, return a list of image titles used on that page,
    e.g. ['File:Something.png', 'File:Banner.jpg', ...]
    """
    params = {
        "action": "query",
        "prop": "images",
        "pageids": str(pageid),
        "imlimit": "max",
        "format": "json",
        "formatversion": "2",
    }
    data = api_get(params)
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return []

    page = pages[0]
    imgs = page.get("images", [])
    return [img["title"] for img in imgs]


def fetch_image_info(title):
    """
    Given a file title like 'File:Something.png', fetch:
      - imageinfo       (url, size, mime, etc.)
      - revisions       (file page description text)
      - categories/info (tags, URL)
    """
    params = {
        "action": "query",
        "titles": title,
        "prop": "imageinfo|revisions|categories|info",
        "iiprop": "url|size|mime|sha1|timestamp|user|comment|metadata",
        "rvprop": "ids|timestamp|content",
        "rvslots": "main",
        "cllimit": "max",
        "inprop": "url",
        "format": "json",
        "formatversion": "2",
    }
    data = api_get(params)
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return None
    return pages[0]


def download_image_from_file_page(file_page):
    """
    Given a file page JSON, download the image into IMAGES_DIR.
    Returns a dict (metadata) if successful, else None.
    """
    if not file_page:
        return None

    imageinfo = file_page.get("imageinfo")
    if not imageinfo:
        print(f"[WARN] No imageinfo for {file_page.get('title')}")
        return None

    info = imageinfo[0]
    url = info.get("url")
    if not url:
        print(f"[WARN] No url for {file_page.get('title')}")
        return None

    # Use the wiki file title as the filename, so we keep extension & uniqueness
    raw_title = file_page.get("title", "File:unknown")
    if ":" in raw_title:
        _, base_name = raw_title.split(":", 1)
    else:
        base_name = raw_title
    filename = safe_filename(base_name)

    out_path = IMAGES_DIR / filename
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    if out_path.exists():
        print(f"[SKIP] Image already exists: {filename}")
    else:
        print(f"[IMG] Downloading {filename} from {url}")
        try:
            r = session.get(url, timeout=60)
            r.raise_for_status()
            with out_path.open("wb") as f:
                f.write(r.content)
        except Exception as e:
            print(f"[ERROR] Failed to download image {filename}: {e}")
            return None

    return {
        "title": file_page.get("title"),
        "filename": filename,
        "url": url,
        "size": info.get("size"),
        "mime": info.get("mime"),
        "sha1": info.get("sha1"),
    }


def main():
    if not BASE_DIR.exists():
        raise FileNotFoundError(
            f"{BASE_DIR} not found. Run shrouded_test.py first."
        )

    seen_files = set()  # avoid downloading same File:... twice

    image_index_file = IMAGE_INDEX_PATH.open("w", encoding="utf-8")

    print("Reading pages from index.jsonl...")
    for pageid, title in get_pages_from_index():
        print(f"\n[PAGE] {pageid}: {title}")
        image_titles = get_images_used_by_page(pageid)
        time.sleep(REQUEST_DELAY)

        if not image_titles:
            print("  (no images on this page)")
            continue

        for img_title in image_titles:
            if img_title in seen_files:
                print(f"  [SKIP] Already handled {img_title}")
                continue

            print(f"  [IMG] Found image: {img_title}")
            seen_files.add(img_title)

            # Fetch full file-page info (imageinfo + description + categories + URL)
            file_page = fetch_image_info(img_title)
            time.sleep(REQUEST_DELAY)

            if file_page:
                safe_title = safe_filename(img_title.replace("File:", "").strip())
                file_json_path = FILE_PAGES_DIR / f"{safe_title}.json"
                save_json(file_json_path, file_page)

            # Download the actual binary image
            meta = download_image_from_file_page(file_page)
            time.sleep(REQUEST_DELAY)

            if meta:
                meta_record = {
                    "file_title": img_title,
                    "image": meta,
                    "first_seen_on_pageid": pageid,
                    "first_seen_on_title": title,
                }
                image_index_file.write(
                    json.dumps(meta_record, ensure_ascii=False) + "\n"
                )

    image_index_file.close()
    print("\nDone! Check the 'images' and 'file_pages' folders inside shrouded_test_output.")


if __name__ == "__main__":
    main()
