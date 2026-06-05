import sqlite3, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = sqlite3.connect(r'D:\fgo ai\fgo_wiki.db')
c = conn.cursor()

# Check wikitext for face icon patterns
c.execute("SELECT page_id, name, wikitext_raw FROM servants LIMIT 5")
for row in c:
    pid, name, wt = row
    print(f"\n=== {pid}: {name} ===")
    wt = wt or ""
    # Look for 再临阶段图标 template
    m = re.search(r'\{\{再临阶段图标\s*\|(.*?)\}\}', wt, re.DOTALL)
    if m:
        print(f"  Found 再临阶段图标: {m.group(1)[:200]}")
    # Look for any image references
    for line in wt.split('\n'):
        if '头像' in line or 'icon' in line.lower() or 'face' in line.lower():
            print(f"  {line.strip()[:150]}")

conn.close()
