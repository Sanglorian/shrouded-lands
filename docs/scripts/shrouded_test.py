import json
import time
from pathlib import Path

import requests

# ---------- CONFIG ----------

WIKI_API = "https://shrouded-lands.fandom.com/api.php"

BASE_DIR = Path("shrouded_test_output")
PAGES_DIR = BASE_DIR / "pages"

USER_AGENT = "ShroudedLandsTest/0.1 (your_email@example.com)"  # optional but polite
REQUEST_DELAY = 0.5  # seconds between page-content requests
NUM_PAGES = 10       # how many pages to fetch


# ---------- SETUP ----------

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})


def api_get(params):
    """Small helper around GET with basic error handling."""
    while True:
        try:
            r = session.get(WIKI_API, params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"[ERROR] API request failed: {e}. Retrying in 5s...")
            time.sleep(5)


def get_sample_pages(limit=10):
    """
    Get up to `limit` pages from the main namespace (articles).
    Returns a list of dicts: [{pageid, title}, ...]
    """
    params = {
        "action": "query",
            "list": "allpages",
            "apnamespace": "0",  # main article namespace
            "aplimit": str(limit),
            "format": "json",
    }
    data = api_get(params)
    pages = data.get("query", {}).get("allpages", [])
    return pages[:limit]


def fetch_page_detail(pageid):
    """
    Fetch wikitext + basic metadata for a single pageid.
    """
    params = {
        "action": "query",
        "prop": "revisions|categories|info",
        "rvprop": "ids|timestamp|content",
        "rvslots": "main",
        "cllimit": "max",
        "inprop": "url",
        "pageids": str(pageid),
        "format": "json",
        "formatversion": "2",
    }
    data = api_get(params)
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return {}

    page = pages[0]

    content = ""
    rev_meta = None
    revisions = page.get("revisions")
    if revisions:
        rev = revisions[0]
        rev_meta = {
            "revid": rev.get("revid"),
            "parentid": rev.get("parentid"),
            "timestamp": rev.get("timestamp"),
        }
        slots = rev.get("slots", {})
        main_slot = slots.get("main", {})
        content = main_slot.get("content", "")

    cats = [c["title"] for c in page.get("categories", [])]
    fullurl = page.get("fullurl")

    return {
        "pageid": page.get("pageid"),
        "ns": page.get("ns"),
        "title": page.get("title"),
        "content": content,
        "revision": rev_meta,
        "categories": cats,
        "fullurl": fullurl,
    }


def main():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    PAGES_DIR.mkdir(parents=True, exist_ok=True)

    index_path = BASE_DIR / "index.jsonl"
    index_file = index_path.open("w", encoding="utf-8")

    print(f"Requesting a sample of {NUM_PAGES} pages from Shrouded Lands...")
    sample_pages = get_sample_pages(NUM_PAGES)

    for p in sample_pages:
        pageid = p["pageid"]
        title = p["title"]
        print(f"[PAGE] Fetching {pageid}: {title}")

        page_data = fetch_page_detail(pageid)
        if not page_data:
            print(f"[WARN] No data for {pageid} ({title})")
            continue

        # Save one JSON per page
        out_path = PAGES_DIR / f"{pageid}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(page_data, f, ensure_ascii=False, indent=2)

        # Also write a small record to index.jsonl
        index_record = {
            "pageid": page_data["pageid"],
            "ns": page_data["ns"],
            "title": page_data["title"],
            "categories": page_data["categories"],
            "fullurl": page_data["fullurl"],
        }
        index_file.write(json.dumps(index_record, ensure_ascii=False) + "\n")

        time.sleep(REQUEST_DELAY)

    index_file.close()
    print("\nDone! Check the 'shrouded_test_output' folder.")


if __name__ == "__main__":
    main()
