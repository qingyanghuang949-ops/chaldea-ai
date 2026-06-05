import sqlite3, json, re

conn = sqlite3.connect(r'D:\fgo ai\fgo_wiki.db')
c = conn.cursor()

# Check Atlas Academy for asset URLs
# First, look at servant wikitext for image info
c.execute("SELECT page_id, name, wikitext_raw FROM servants LIMIT 3")
for row in c:
    page_id, name, wt = row
    print(f"\n=== {name} (page_id={page_id}) ===")
    wt = wt or ""
    # Look for image-related lines
    for line in wt.split('\n'):
        l = line.strip()
        if any(kw in l for kw in ['立绘', '画像', '图鉴', 'cardimage', 'sprite', 'File:', 'file:', '图片']):
            print(f"  {l[:200]}")
    # Also check for image template params
    if '形象' in wt or '立绘' in wt:
        idx = max(wt.find('形象'), wt.find('立绘'))
        print(f"  [context] ...{wt[max(0,idx-50):idx+300]}...")

conn.close()
