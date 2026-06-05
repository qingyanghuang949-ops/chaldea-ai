import sqlite3, re, sys, requests, os, time, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = r'D:\fgo ai\fgo_wiki.db'
OUT_DIR = r'D:\fgo ai\基本资料\mooncell头像'
PERSONALITIES_JSON = r'D:\fgo ai\基本资料\personalities.json'
os.makedirs(OUT_DIR, exist_ok=True)

# Stats
stats = {'downloaded': 0, 'failed': 0, 'skipped': 0, 'api_error': 0}
stats_lock = Lock()
counter = {'done': 0}
counter_lock = Lock()
total_count = 0

def get_image_url(filename):
    """Get the actual image URL from Mooncell wiki API"""
    api_url = "https://fgo.wiki/api.php"
    params = {
        "action": "query",
        "titles": f"File:{filename}",
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json"
    }
    try:
        resp = requests.get(api_url, params=params, timeout=15)
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            if "imageinfo" in page:
                return page["imageinfo"][0]["url"]
    except Exception as e:
        return None
    return None

def sanitize_filename(name):
    """Sanitize filename for Windows"""
    # Remove characters not allowed in Windows filenames
    for ch in r'<>:"/\|?*':
        name = name.replace(ch, '_')
    return name

def download_icon(pid, name, icon_filename):
    """Download one icon. Returns (pid, name, saved_path, status)"""
    safe_name = sanitize_filename(name)
    out_file = os.path.join(OUT_DIR, f"{pid}_{safe_name}.png")
    
    # Skip if exists
    if os.path.exists(out_file) and os.path.getsize(out_file) > 0:
        with stats_lock:
            stats['skipped'] += 1
        with counter_lock:
            counter['done'] += 1
            n = counter['done']
        if n % 50 == 0:
            print(f"  Progress: {n}/{total_count} processed "
                  f"(DL:{stats['downloaded']} Skip:{stats['skipped']} Fail:{stats['failed']})")
        return (pid, name, out_file, 'skipped')
    
    # Rate limit
    time.sleep(0.3)
    
    # Get image URL
    url = get_image_url(icon_filename)
    if not url:
        # Retry once
        time.sleep(0.5)
        url = get_image_url(icon_filename)
    
    if not url:
        with stats_lock:
            stats['failed'] += 1
            stats['api_error'] += 1
        with counter_lock:
            counter['done'] += 1
            n = counter['done']
        if n % 50 == 0:
            print(f"  Progress: {n}/{total_count} processed "
                  f"(DL:{stats['downloaded']} Skip:{stats['skipped']} Fail:{stats['failed']})")
        print(f"  ✗ API error for {pid} ({name}): {icon_filename}")
        return (pid, name, None, 'api_error')
    
    # Download image
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            with open(out_file, 'wb') as f:
                f.write(resp.content)
            with stats_lock:
                stats['downloaded'] += 1
            with counter_lock:
                counter['done'] += 1
                n = counter['done']
            if n % 50 == 0:
                print(f"  Progress: {n}/{total_count} processed "
                      f"(DL:{stats['downloaded']} Skip:{stats['skipped']} Fail:{stats['failed']})")
            return (pid, name, out_file, 'ok')
        else:
            with stats_lock:
                stats['failed'] += 1
            with counter_lock:
                counter['done'] += 1
                n = counter['done']
            if n % 50 == 0:
                print(f"  Progress: {n}/{total_count} processed "
                      f"(DL:{stats['downloaded']} Skip:{stats['skipped']} Fail:{stats['failed']})")
            print(f"  ✗ HTTP {resp.status_code} for {pid} ({name})")
            return (pid, name, None, f'http_{resp.status_code}')
    except Exception as e:
        with stats_lock:
            stats['failed'] += 1
        with counter_lock:
            counter['done'] += 1
            n = counter['done']
        if n % 50 == 0:
            print(f"  Progress: {n}/{total_count} processed "
                  f"(DL:{stats['downloaded']} Skip:{stats['skipped']} Fail:{stats['failed']})")
        print(f"  ✗ Download error for {pid} ({name}): {e}")
        return (pid, name, None, 'download_error')


# ── Extract icon data from database ──
print("Extracting servant icon data from database...")
conn = sqlite3.connect(DB)
c = conn.cursor()

icon_pattern = re.compile(r'\{\{再临阶段图标\s*\|(.*?)\}\}', re.DOTALL)
servants = []

c.execute("SELECT page_id, name, wikitext_raw FROM servants")
for row in c:
    pid, name, wt = row
    wt = wt or ""
    m = icon_pattern.search(wt)
    if m:
        content = m.group(1)
        icon_match = re.search(r'图标=(.+?)(?:\n|$)', content)
        if icon_match:
            icons_str = icon_match.group(1).strip()
            icons = [f.strip() for f in icons_str.split(';;') if f.strip()]
            if icons:
                servants.append({
                    'page_id': pid,
                    'name': name,
                    'first_icon': icons[0]
                })

conn.close()
total_count = len(servants)
print(f"Found {total_count} servants with icons.\n")

# ── Download all icons ──
print(f"Downloading icons to: {OUT_DIR}")
print(f"Workers: 10, Delay: 0.3s between API calls\n")

results = {}
with ThreadPoolExecutor(max_workers=10) as pool:
    futures = {
        pool.submit(download_icon, s['page_id'], s['name'], s['first_icon']): s
        for s in servants
    }
    for future in as_completed(futures):
        pid, name, path, status = future.result()
        results[pid] = {
            'name': name,
            'status': status,
            'path': path
        }

# ── Summary ──
print(f"\n{'='*50}")
print(f"Download Complete!")
print(f"  Downloaded: {stats['downloaded']}")
print(f"  Skipped (already existed): {stats['skipped']}")
print(f"  Failed: {stats['failed']}")
print(f"  Total processed: {total_count}")

# ── Update personalities.json ──
print(f"\nUpdating {PERSONALITIES_JSON}...")
# Load existing if present
if os.path.exists(PERSONALITIES_JSON):
    with open(PERSONALITIES_JSON, 'r', encoding='utf-8') as f:
        personalities = json.load(f)
else:
    personalities = {}

# Build a lookup by page_id
for pid, info in results.items():
    pid_str = str(pid)
    if pid_str not in personalities:
        personalities[pid_str] = {}
    personalities[pid_str]['name'] = info['name']
    if info['path']:
        # Store relative path from the 基本资料 directory
        rel_path = os.path.relpath(info['path'], os.path.dirname(PERSONALITIES_JSON))
        personalities[pid_str]['mooncell_icon'] = rel_path.replace('\\', '/')
    elif info['status'] == 'skipped':
        # File exists but wasn't downloaded this run — find it
        safe_name = sanitize_filename(info['name'])
        expected = os.path.join(OUT_DIR, f"{pid}_{safe_name}.png")
        if os.path.exists(expected):
            rel_path = os.path.relpath(expected, os.path.dirname(PERSONALITIES_JSON))
            personalities[pid_str]['mooncell_icon'] = rel_path.replace('\\', '/')

with open(PERSONALITIES_JSON, 'w', encoding='utf-8') as f:
    json.dump(personalities, f, ensure_ascii=False, indent=2)

print(f"Updated {len(personalities)} entries in personalities.json")
print("Done!")
