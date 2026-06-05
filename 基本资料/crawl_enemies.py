"""
Phase 1c: Crawl enemies (敌方从者) from fgo.wiki
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
                print("  [ERROR] %s" % e)
                return None


def get_all_category_members(category, limit=500, recurse=False):
    """Get all pages in a category, optionally recursing into subcategories"""
    members = []
    subcategories = []
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": "Category:" + category,
        "cmlimit": str(limit),
        "cmtype": "page|subcat",
    }
    while True:
        data = api_get(params)
        if not data or "query" not in data:
            break
        for item in data["query"]["categorymembers"]:
            if item.get("ns") == 14:  # subcategory namespace
                subcategories.append(item["title"].replace("Category:", ""))
            else:
                members.append(item)
        if "continue" in data:
            params["cmcontinue"] = data["continue"]["cmcontinue"]
            time.sleep(REQUEST_DELAY)
        else:
            break

    if recurse:
        for subcat in subcategories:
            print("  Recursing into subcategory: %s" % subcat)
            sub_members = get_all_category_members(subcat, limit, recurse=True)
            members.extend(sub_members)

    return members


def get_page_wikitext(title):
    data = api_get({"action": "parse", "page": title, "prop": "wikitext"})
    if data and "parse" in data:
        return data["parse"]["wikitext"]["*"]
    return None


def parse_enemy(wikitext, page_id, name):
    """Parse enemy page - store basic info + raw wikitext"""
    now = datetime.now().isoformat()

    enemy_name = name
    enemy_class = ""
    enemy_traits = ""

    # Try to extract class from wikitext
    class_patterns = [
        r'职阶[=：]\s*\[\[?([^\]|}\]]+)',
        r'class\s*=\s*([^\]|}\n]+)',
    ]
    for pat in class_patterns:
        m = re.search(pat, wikitext)
        if m:
            enemy_class = m.group(1).strip()
            break

    # Try to extract traits
    trait_match = re.search(r'特性[=：]\s*([^\n]+)', wikitext)
    if trait_match:
        enemy_traits = trait_match.group(1).strip()

    return {
        "page_id": page_id,
        "name": enemy_name,
        "class": enemy_class,
        "traits": enemy_traits,
        "wikitext_raw": wikitext,
        "fetched_at": now,
    }


def main():
    print("Enemies Crawler - %s" % datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")

    # Create table if it doesn't exist
    existing_cols = [r[1] for r in conn.execute("PRAGMA table_info(enemies)").fetchall()]
    if not existing_cols:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS enemies (
                page_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                class TEXT,
                traits TEXT,
                wikitext_raw TEXT,
                fetched_at TEXT
            )
        """)
        conn.commit()

    # Try known enemy categories
    categories_to_try = ["敌方从者", "敌人一览", "敌人"]
    members = []

    for cat in categories_to_try:
        print("Trying Category:%s ..." % cat)
        members = get_all_category_members(cat, recurse=True)
        if members:
            # Deduplicate by page_id
            seen = set()
            unique = []
            for m in members:
                if m["pageid"] not in seen:
                    seen.add(m["pageid"])
                    unique.append(m)
            members = unique
            print("Found %d unique enemy pages" % len(members))
            break

    if not members:
        print("No enemy pages found. Done.")
        conn.close()
        return

    success = 0
    failed = 0
    skipped = 0

    for i, member in enumerate(members):
        page_id = member["pageid"]
        title = member["title"]

        existing = conn.execute(
            "SELECT page_id FROM enemies WHERE page_id=?", (page_id,)
        ).fetchone()
        if existing:
            skipped += 1
            continue

        print("  [%d/%d] %s ..." % (i + 1, len(members), title), end=" ")
        wikitext = get_page_wikitext(title)
        time.sleep(REQUEST_DELAY)

        if not wikitext:
            print("FAILED")
            failed += 1
            continue

        enemy = parse_enemy(wikitext, page_id, title)

        conn.execute("""
            INSERT OR REPLACE INTO enemies
            (page_id, name, class, traits, wikitext_raw, fetched_at)
            VALUES (?,?,?,?,?,?)
        """, (
            enemy["page_id"], enemy["name"], enemy["class"],
            enemy["traits"], enemy["wikitext_raw"], enemy["fetched_at"]
        ))

        conn.execute("""
            INSERT OR REPLACE INTO page_index (page_id, title, category, fetched_at)
            VALUES (?, ?, ?, ?)
        """, (page_id, title, "敌方从者", datetime.now().isoformat()))

        conn.commit()
        print("OK")
        success += 1

    conn.close()
    print("\nEnemies crawl complete: success=%d, skipped=%d, failed=%d, total=%d" % (success, skipped, failed, len(members)))


if __name__ == "__main__":
    main()
