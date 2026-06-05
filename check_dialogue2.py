import sqlite3, re, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = sqlite3.connect(r'D:\fgo ai\fgo_wiki.db')
c = conn.cursor()

# Check more CN scripts to find actual servant dialogue
c.execute("SELECT script_id, script_text FROM story_scripts WHERE region='CN' LIMIT 5")
for row in c:
    sid, text = row
    print(f"\n=== Script {sid} ===")
    lines = text.split('\n')
    for line in lines:
        if '＠' in line and '广播' not in line and '特效' not in line:
            print(f"  {line.strip()[:100]}")

conn.close()
