"""
Phase 1b: Crawl items (道具) from fgo.wiki
Run after main scraper completes.
"""

import sys
import os
import time
import json
import re
import sqlite3
import requests
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_URL = "https://fgo.wiki/api.php"
DB_PATH = os.path.join(os.path.dirname(__file__), "fgo_wiki.db")
HEADERS = {"User-Agent": "FGO-Wiki-Scraper/1.0 (Personal Use)"}
REQUEST_DELAY = 0.5


def api_get(params, retries=3):
    params["format"] = "json"
    for attempt in range(retries):
        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                print(f"  [ERROR] {e}")
                return None


def get_all_category_members(category, limit=500):
    members = []
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": str(limit),
        "cmtype": "page",
    }
    while True:
        data = api_get(params)
        if not data or "query" not in data:
            break
        members.extend(data["query"]["categorymembers"])
        if "continue" in data:
            params["cmcontinue"] = data["continue"]["cmcontinue"]
            time.sleep(REQUEST_DELAY)
        else:
            break
    return members


def get_page_wikitext(title):
    data = api_get({"action": "parse", "page": title, "prop": "wikitext"})
    if data and "parse" in data:
        return data["parse"]["wikitext"]["*"]
    return None


def parse_template_params(wikitext, template_name):
    pattern = r'\{\{' + re.escape(template_name) + r'\s*\|([\s\S]*?)\}\}'
    matches = re.findall(pattern, wikitext)
    results = []
    for match in matches:
        params = {}
        parts = []
        depth = 0
        current = ""
        for ch in match:
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
            elif ch == '|' and depth == 0:
                parts.append(current.strip())
                current = ""
                continue
            current += ch
        if current.strip():
            parts.append(current.strip())
        for part in parts:
            if '=' in part:
                key, _, value = part.partition('=')
                params[key.strip()] = value.strip()
        results.append(params)
    return results


def parse_item(wikitext, page_id, name):
    """Parse item page using {{道具信息}} template"""
    now = datetime.now().isoformat()
    item_data = parse_template_params(wikitext, "道具信息")
    if not item_data:
        return None

    d = item_data[0]
    return {
        "page_id": page_id,
        "name": d.get("中文名称", name),
        "description": d.get("中文详细信息", ""),
        "item_type": d.get("分类", ""),
        "wikitext_raw": wikitext,
        "fetched_at": now,
    }


def main():
    print(f"Items Crawler - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")

    # Ensure table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            page_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            item_type TEXT,
            wikitext_raw TEXT,
            fetched_at TEXT
        )
    """)
    conn.commit()

    print("Fetching 道具 category members...")
    members = get_all_category_members("道具")
    print(f"Found {len(members)} item pages")

    success = 0
    failed = 0
    skipped = 0

    for i, member in enumerate(members):
        page_id = member["pageid"]
        title = member["title"]

        existing = conn.execute(
            "SELECT page_id FROM items WHERE page_id=?", (page_id,)
        ).fetchone()
        if existing:
            skipped += 1
            continue

        print(f"  [{i+1}/{len(members)}] {title} ...", end=" ")
        wikitext = get_page_wikitext(title)
        time.sleep(REQUEST_DELAY)

        if not wikitext:
            print("FAILED")
            failed += 1
            continue

        item = parse_item(wikitext, page_id, title)
        if not item:
            # Store raw even if template not found
            item = {
                "page_id": page_id,
                "name": title,
                "description": "",
                "item_type": "",
                "wikitext_raw": wikitext,
                "fetched_at": datetime.now().isoformat(),
            }

        conn.execute("""
            INSERT OR REPLACE INTO items
            (page_id, name, description, item_type, wikitext_raw, fetched_at)
            VALUES (?,?,?,?,?,?)
        """, (
            item["page_id"], item["name"], item["description"],
            item["item_type"], item["wikitext_raw"], item["fetched_at"]
        ))

        conn.execute("""
            INSERT OR REPLACE INTO page_index (page_id, title, category, fetched_at)
            VALUES (?, ?, ?, ?)
        """, (page_id, title, "道具", datetime.now().isoformat()))

        conn.commit()
        print("OK")
        success += 1

    conn.close()
    print(f"\nItems crawl complete: success={success}, skipped={skipped}, failed={failed}, total={len(members)}")


if __name__ == "__main__":
    main()
