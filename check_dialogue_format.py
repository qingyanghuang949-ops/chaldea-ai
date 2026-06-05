import sqlite3, re, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = sqlite3.connect(r'D:\fgo ai\fgo_wiki.db')
c = conn.cursor()

# Check what the dialogue format actually looks like in CN scripts
c.execute("SELECT script_text FROM story_scripts WHERE region='CN' LIMIT 1")
row = c.fetchone()
if row:
    text = row[0]
    lines = text.split('\n')
    for line in lines[:50]:
        if '＠' in line:
            print(repr(line))

print("\n---")

# Also check with different encoding
c.execute("SELECT script_text FROM story_scripts WHERE region='CN' LIMIT 1")
row = c.fetchone()
if row:
    text = row[0]
    # Check for dialogue pattern
    matches = re.findall(r'＠(.+?)$', text, re.MULTILINE)
    for m in matches[:10]:
        print(f"Speaker: {repr(m)}")

conn.close()
