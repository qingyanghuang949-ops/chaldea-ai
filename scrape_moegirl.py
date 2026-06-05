#!/usr/bin/env python3
"""Scrape all FGO servant pages from Moegirl Wiki (萌娘百科)."""

import sqlite3
import requests
import time
import re
import json
import urllib.parse
from html.parser import HTMLParser
from datetime import datetime

DB_PATH = r'D:\fgo ai\fgo_wiki.db'

COOKIES = {
    '_gid': 'GA1.3.373479924.1780588731',
    '_ga': 'GA1.1.1688750168.1780588731',
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

class ContentExtractor(HTMLParser):
    """Extract text from main content area of Moegirl wiki page."""
    def __init__(self):
        super().__init__()
        self.in_content = False
        self.skip = False
        self.skip_tags = set()
        self.depth = 0
        self.text_parts = []
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        id_val = attrs_dict.get('id', '')
        class_val = attrs_dict.get('class', '')

        if id_val == 'mw-content-text':
            self.in_content = True
            self.depth = 0

        if self.in_content:
            self.depth += 1
            if tag in ('script', 'style', 'nav', 'footer', 'noscript'):
                self.skip_tags.add(self.depth)
            # Skip edit sections
            if class_val and ('mw-editsection' in class_val or 'navbox' in class_val or 'mw-collapsible' in class_val):
                self.skip_tags.add(self.depth)
            self.current_tag = tag
            if tag in ('br', 'p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr'):
                self.text_parts.append('\n')

    def handle_endtag(self, tag):
        if self.in_content:
            if self.depth in self.skip_tags:
                self.skip_tags.discard(self.depth)
            self.depth -= 1
            if self.depth <= 0:
                self.in_content = False

    def handle_data(self, data):
        if self.in_content and not self.skip_tags:
            text = data.strip()
            if text:
                self.text_parts.append(text)

    def get_text(self):
        raw = '\n'.join(self.text_parts)
        # Clean up multiple newlines
        raw = re.sub(r'\n{3,}', '\n\n', raw)
        return raw.strip()


def fetch_page(url, session):
    """Fetch a page and return (status_code, text) or (None, None) on error."""
    try:
        resp = session.get(url, headers=HEADERS, cookies=COOKIES, timeout=30, allow_redirects=True)
        return resp.status_code, resp.text
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return None, None


def extract_content(html):
    """Extract main text content from HTML."""
    parser = ContentExtractor()
    parser.feed(html)
    return parser.get_text()[:20000]  # Limit to 20000 chars


def clean_name_for_url(name):
    """Clean servant name for URL construction."""
    # Remove special chars that are problematic in URLs
    cleaned = name
    # Remove quotes
    cleaned = cleaned.replace('"', '').replace('"', '').replace('"', '')
    # Remove characters that are not in typical wiki page names
    # Keep alphanumeric, CJK, and common punctuation
    return cleaned.strip()


def try_fetch_moegirl(name, session):
    """Try to fetch Moegirl page for a servant. Returns (title, url, content) or None."""
    clean = clean_name_for_url(name)

    # Strategy 1: name(Fate)
    url1 = f"https://zh.moegirl.org.cn/{urllib.parse.quote(clean, safe='/')}(Fate)"
    code, html = fetch_page(url1, session)
    if code == 200 and html and len(html) > 5000:
        # Check if it's a real content page (not a disambiguation or redirect)
        if 'mw-content-text' in html:
            content = extract_content(html)
            if len(content) > 200:
                return f"{clean}(Fate)", url1, content

    # Strategy 2: name without suffix
    url2 = f"https://zh.moegirl.org.cn/{urllib.parse.quote(clean, safe='/')}"
    code, html = fetch_page(url2, session)
    if code == 200 and html and len(html) > 5000:
        if 'mw-content-text' in html:
            content = extract_content(html)
            if len(content) > 200:
                return clean, url2, content

    # Strategy 3: name(Fate/Grand Order)
    url3 = f"https://zh.moegirl.org.cn/{urllib.parse.quote(clean, safe='/')}(Fate/Grand Order)"
    code, html = fetch_page(url3, session)
    if code == 200 and html and len(html) > 5000:
        if 'mw-content-text' in html:
            content = extract_content(html)
            if len(content) > 200:
                return f"{clean}(Fate/Grand Order)", url3, content

    return None


def main():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create moegirl_wiki table
    c.execute('''CREATE TABLE IF NOT EXISTS moegirl_wiki (
        page_id INTEGER PRIMARY KEY,
        name TEXT,
        moegirl_title TEXT,
        moegirl_url TEXT,
        content TEXT,
        fetched_at TEXT
    )''')
    conn.commit()

    # Get all servants
    c.execute("SELECT page_id, name FROM servants")
    servants = c.fetchall()
    total = len(servants)
    print(f"Total servants to process: {total}")

    # Check which ones are already fetched
    c.execute("SELECT page_id FROM moegirl_wiki")
    already_fetched = set(r[0] for r in c.fetchall())
    print(f"Already fetched: {len(already_fetched)}")

    session = requests.Session()
    success = 0
    failed = 0
    skipped = 0
    consecutive_failures = 0

    for i, (page_id, name) in enumerate(servants):
        if page_id in already_fetched:
            skipped += 1
            continue

        result = try_fetch_moegirl(name, session)

        if result:
            title, url, content = result
            c.execute(
                "INSERT OR REPLACE INTO moegirl_wiki (page_id, name, moegirl_title, moegirl_url, content, fetched_at) VALUES (?, ?, ?, ?, ?, ?)",
                (page_id, name, title, url, content, datetime.now().isoformat())
            )
            conn.commit()
            success += 1
            consecutive_failures = 0
        else:
            # Record that we tried but failed
            c.execute(
                "INSERT OR REPLACE INTO moegirl_wiki (page_id, name, moegirl_title, moegirl_url, content, fetched_at) VALUES (?, ?, ?, ?, ?, ?)",
                (page_id, name, None, None, None, datetime.now().isoformat())
            )
            conn.commit()
            failed += 1
            consecutive_failures += 1

        processed = i + 1 - skipped
        if processed % 20 == 0 or processed == total - skipped:
            print(f"[{processed}/{total - skipped}] OK:{success} FAIL:{failed} SKIP:{skipped} - Last: {name}")

        # Check for cookie expiration (consecutive 403s)
        if consecutive_failures >= 10:
            print(f"\n⚠️ 10 consecutive failures - cookies may have expired!")
            print(f"Stopping early. Progress saved. {success} scraped, {failed} failed so far.")
            break

        # Rate limit
        time.sleep(1)

    print(f"\n=== DONE ===")
    print(f"Total: {total}")
    print(f"Scraped: {success}")
    print(f"Failed: {failed}")
    print(f"Skipped (already done): {skipped}")

    conn.close()


if __name__ == '__main__':
    main()
