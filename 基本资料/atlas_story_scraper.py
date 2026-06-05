"""
Phase 2: Download ALL FGO story scripts from Atlas Academy API.
Concurrent download with incremental DB writes (small batches).
"""

import requests
import sqlite3
import json
import time
import os
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

DB_PATH = os.path.join(os.path.dirname(__file__), "fgo_wiki.db")
HEADERS = {"User-Agent": "FGO-Story-Scraper/1.0 (Personal Use)"}
MAX_WORKERS = 20
FLUSH_EVERY = 100  # Write to DB every N downloads


def download_war_json(region):
    url = "https://api.atlasacademy.io/export/%s/nice_war.json" % region
    print("Downloading %s war data..." % region)
    resp = requests.get(url, headers=HEADERS, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    print("  %d wars for %s" % (len(data), region))
    return data


def extract_script_urls(wars, region):
    scripts = {}
    for war in wars:
        war_id = war.get("id", 0)
        for spot in war.get("spots", []):
            for quest in spot.get("quests", []):
                quest_id = quest.get("id", 0)
                quest_name = quest.get("name", "")
                for phase in quest.get("phaseScripts", []):
                    for entry in phase.get("scripts", []):
                        url = entry.get("script", "") or entry.get("scriptUrl", "")
                        if url and url not in scripts:
                            scripts[url] = {
                                "war_id": war_id,
                                "quest_id": quest_id,
                                "quest_name": quest_name,
                                "region": region,
                            }
    return scripts


def extract_script_id(url):
    filename = url.rsplit("/", 1)[-1] if "/" in url else url
    return filename.replace(".txt", "")


def fetch_script(args):
    url, info = args
    script_id = extract_script_id(url)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return (script_id, info, url, resp.text, None)
    except Exception as e:
        return (script_id, info, url, None, str(e))


def db_write_batch(conn, rows, retries=5):
    """Write a batch of rows to DB with retry on lock."""
    for attempt in range(retries):
        try:
            conn.executemany("""
                INSERT OR IGNORE INTO story_scripts
                (script_id, region, war_id, quest_id, quest_name, script_url, script_text, fetched_at)
                VALUES (?,?,?,?,?,?,?,?)
            """, rows)
            conn.commit()
            return True
        except sqlite3.OperationalError as e:
            if "locked" in str(e) and attempt < retries - 1:
                time.sleep(2)
            else:
                print("  DB write error: %s" % e)
                return False
    return False


def main():
    start = datetime.now()
    print("Atlas Academy Story Scraper - %s" % start.strftime('%Y-%m-%d %H:%M:%S'))
    print("Workers: %d, Flush every: %d\n" % (MAX_WORKERS, FLUSH_EVERY))

    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS story_scripts (
            script_id TEXT,
            region TEXT,
            war_id INTEGER,
            quest_id INTEGER,
            quest_name TEXT,
            script_url TEXT,
            script_text TEXT,
            fetched_at TEXT,
            PRIMARY KEY (script_id, region)
        )
    """)
    conn.commit()

    existing_ids = set((r[0], r[1]) for r in conn.execute("SELECT script_id, region FROM story_scripts").fetchall())
    print("Existing scripts in DB: %d" % len(existing_ids))

    grand_downloaded = 0
    grand_skipped = 0
    grand_failed = 0
    all_failures = []

    for region in ["CN"]:
        print("\n" + "=" * 60)
        print("Region: %s" % region)
        print("=" * 60)

        try:
            wars = download_war_json(region)
        except Exception as e:
            print("ERROR: %s" % e)
            continue

        scripts = extract_script_urls(wars, region)
        print("Unique script URLs: %d" % len(scripts))

        to_download = []
        skipped = 0
        for url, info in scripts.items():
            sid = extract_script_id(url)
            if (sid, info["region"]) in existing_ids:
                skipped += 1
            else:
                to_download.append((url, info))

        print("Skip: %d, Download: %d" % (skipped, len(to_download)))
        grand_skipped += skipped

        if not to_download:
            continue

        print("Downloading with %d workers..." % MAX_WORKERS)
        buffer = []
        downloaded = 0
        failed = 0
        done = 0

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            for result in pool.map(fetch_script, to_download, chunksize=20):
                done += 1
                script_id, info, url, text, error = result

                if error:
                    failed += 1
                    all_failures.append((url, error))
                else:
                    buffer.append((
                        script_id, info["region"], info["war_id"],
                        info["quest_id"], info["quest_name"], url, text,
                        datetime.now().isoformat()
                    ))
                    downloaded += 1
                    existing_ids.add((script_id, info["region"]))

                # Flush buffer periodically
                if len(buffer) >= FLUSH_EVERY:
                    db_write_batch(conn, buffer)
                    buffer = []

                if done % 500 == 0:
                    print("  [%d/%d] OK: %d, Fail: %d" % (
                        done, len(to_download), downloaded, failed))

        # Final flush
        if buffer:
            db_write_batch(conn, buffer)

        grand_downloaded += downloaded
        grand_failed += failed
        print("  Region done: %d downloaded, %d failed" % (downloaded, failed))

    # Summary
    elapsed = (datetime.now() - start).total_seconds()
    count = conn.execute("SELECT COUNT(*) FROM story_scripts").fetchone()[0]
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("Downloaded: %d" % grand_downloaded)
    print("Skipped: %d" % grand_skipped)
    print("Failed: %d" % grand_failed)
    print("Total in DB: %d" % count)
    for row in conn.execute("SELECT region, COUNT(*) FROM story_scripts GROUP BY region"):
        print("  %s: %d" % (row[0], row[1]))
    print("Time: %.1fs" % elapsed)

    if all_failures:
        print("\nFailed (%d):" % len(all_failures))
        for url, err in all_failures[:20]:
            print("  %s: %s" % (url, err))

    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
