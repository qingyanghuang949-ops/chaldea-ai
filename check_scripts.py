import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = sqlite3.connect(r'D:\fgo ai\fgo_wiki.db')
c = conn.cursor()

# Check story script format
c.execute("SELECT script_id, quest_name, script_text FROM story_scripts WHERE region='JP' LIMIT 3")
for row in c:
    sid, qname, text = row
    print(f"\n=== {sid} ({qname}) ===")
    print((text or "")[:800])

# Check how many unique servants we have
c.execute("SELECT COUNT(DISTINCT page_id) FROM servants")
print(f"\nTotal servants: {c.fetchone()[0]}")

# Check servant names
c.execute("SELECT page_id, name FROM servants LIMIT 10")
for row in c:
    print(f"  {row[0]}: {row[1]}")

conn.close()
