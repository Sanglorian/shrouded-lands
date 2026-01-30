import json
import time
from pathlib import Path

import requests

# ---------- CONFIG ----------

WIKI_API = "https://shrouded-lands.fandom.com/api.php"

# We'll reuse the same output directory so your image script still works
BASE_DIR = Path("shrouded_test_output")
PAGES_DIR = BASE_DIR / "pages"

USER_AGENT = "ShroudedLandsFullDump/1.0 (your_email@example.com)"  # optional but polite
REQUEST_DELAY = 0.5  # seconds between page-content requests

# Namespaces to dump:
# 0   = main articles
# 10  = Template
# 14  = Category
# (add more namespace numbers here if you want them)
NAMESPACES = [0, 10, 14]


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


def iter_all_pages(namespace: int):
    """
    Yield all pages in a given namespace as dicts with pageid + title.
    Uses the allpages list with pagination via apcontinue.
    """
    apcontinue = None
    print(f"\n=== Listing pages in namespace {namespace} ===")

    while True:
        params = {
            "action": "query",
            "list": "allpages",
            "apnamespace": str(namespace),
            "aplimit": "500",  # max for normal clients
            "format": "json",
        }
        if apcontinue:
            params["apcontinue"] = apcontinue

        data = api_get(params)
        pages = data.get("query", {}).get("allpages", [])
        for p in pages:
            yield p  # { 'pageid': ..., 'title': ... }

        cont = data.get("continue")
        if cont and "apcontinue" in cont:
            apcontinue = cont["apcontinue"]
            time.sleep(REQUEST_DELAY)
        else:
            break


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


def load_page_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    PAGES_DIR.mkdir(parents=True, exist_ok=True)

    # Overwrite index.jsonl with a fresh full index
    index_path = BASE_DIR / "index.jsonl"
    index_file = index_path.open("w", encoding="utf-8")

    for ns in NAMESPACES:
        for p in iter_all_pages(ns):
            pageid = p["pageid"]
            title = p["title"]
            out_path = PAGES_DIR / f"{pageid}.json"

            if out_path.exists():
                # Reuse existing data so reruns are fast/resumable
                print(f"[SKIP] Already have page {pageid}: {title}")
                page_data = load_page_json(out_path)
            else:
                print(f"[PAGE] Fetching {pageid}: {title}")
                page_data = fetch_page_detail(pageid)
                if not page_data:
                    print(f"[WARN] No data for {pageid} ({title})")
                    continue

                with out_path.open("w", encoding="utf-8") as f:
                    json.dump(page_data, f, ensure_ascii=False, indent=2)
                time.sleep(REQUEST_DELAY)

            # Write / rewrite index record
            index_record = {
                "pageid": page_data["pageid"],
                "ns": page_data["ns"],
                "title": page_data["title"],
                "categories": page_data["categories"],
                "fullurl": page_data["fullurl"],
            }
            index_file.write(json.dumps(index_record, ensure_ascii=False) + "\n")

    index_file.close()
    print("\n=== DONE: full page dump complete ===")
    print(f"Index: {index_path}")
    print(f"Pages in: {PAGES_DIR.resolve()}")


if __name__ == "__main__":
    main()
