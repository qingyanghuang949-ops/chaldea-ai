import sqlite3, re, sys, requests, os, time
from concurrent.futures import ThreadPoolExecutor
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DB = r'D:\fgo ai\fgo_wiki.db'
OUT_DIR = r'D:\fgo ai\基本资料\mooncell头像'
os.makedirs(OUT_DIR, exist_ok=True)

# Mooncell image URL pattern: https://fgo.wiki/images/{hash_prefix}/{filename}
# We need to use the MediaWiki API to get the actual image URL

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
    except:
        pass
    return None

# Test with one filename
test_url = get_image_url("大公头像1.png")
print(f"Test URL: {test_url}")

# Now extract all icon filenames from wikitext
conn = sqlite3.connect(DB)
c = conn.cursor()

icon_pattern = re.compile(r'\{\{再临阶段图标\s*\|(.*?)\}\}', re.DOTALL)
filenames = {}

c.execute("SELECT page_id, name, wikitext_raw FROM servants")
for row in c:
    pid, name, wt = row
    wt = wt or ""
    m = icon_pattern.search(wt)
    if m:
        content = m.group(1)
        # Extract 图标= line
        icon_match = re.search(r'图标=(.+?)(?:\n|$)', content)
        if icon_match:
            icons_str = icon_match.group(1).strip()
            # Split by ;;
            icons = [f.strip() for f in icons_str.split(';;') if f.strip()]
            if icons:
                filenames[pid] = {
                    'name': name,
                    'icons': icons,
                    'first_icon': icons[0]  # Stage 1 icon
                }

conn.close()

print(f"\nTotal servants with icons: {len(filenames)}")
print(f"Sample icons:")
for pid, info in list(filenames.items())[:5]:
    print(f"  {pid} ({info['name']}): {info['first_icon']}")
