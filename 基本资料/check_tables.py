import sqlite3

conn = sqlite3.connect('fgo_wiki.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]
print("Tables:", tables)

for name in tables:
    cursor.execute(f"SELECT COUNT(*) FROM [{name}]")
    print(f"  {name}: {cursor.fetchone()[0]}")

# Check servant wikitext for image URLs
cursor.execute("SELECT page_id, name, wikitext_raw FROM servants LIMIT 1")
row = cursor.fetchone()
if row:
    print(f"\nSample servant: {row[0]} - {row[1]}")
    wt = row[2] or ""
    # Look for image references
    for line in wt.split('\n'):
        if '图' in line or 'img' in line.lower() or '立绘' in line or '画像' in line:
            print(f"  {line.strip()}")

conn.close()
