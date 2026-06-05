import sqlite3, sys, re
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = sqlite3.connect(r'D:\fgo ai\fgo_wiki.db')
c = conn.cursor()

# Extract character names from story scripts
# Format: ＠A：character_name or ＠[color]character_name[-]
char_pattern = re.compile(r'＠(?:\w：)?(?:\[.*?\])?([^\[-\]]+?)(?:\[-\])?$')

servant_dialogues = Counter()
servant_scripts = {}

c.execute("SELECT script_id, script_text FROM story_scripts WHERE region='JP' LIMIT 100")
for row in c:
    sid, text = row
    if not text:
        continue
    for line in text.split('\n'):
        m = char_pattern.match(line.strip())
        if m:
            name = m.group(1).strip()
            if name and not name.startswith('？'):
                servant_dialogues[name] += 1
                if name not in servant_scripts:
                    servant_scripts[name] = []
                servant_scripts[name].append(sid)

print("=== Top 30 dialogue characters ===")
for name, count in servant_dialogues.most_common(30):
    print(f"  {name}: {count} lines")

# Check charaSet to find character IDs
chara_pattern = re.compile(r'\[charaSet\s+\w\s+(\d+)\s+\d+\s+(.+?)\]')
char_ids = {}
c.execute("SELECT script_id, script_text FROM story_scripts WHERE region='JP' LIMIT 200")
for row in c:
    sid, text = row
    if not text:
        continue
    for line in text.split('\n'):
        m = chara_pattern.search(line)
        if m:
            cid, name = m.groups()
            char_ids[name] = cid

print("\n=== Character ID mapping (sample) ===")
for name, cid in list(char_ids.items())[:20]:
    print(f"  {name}: {cid}")

conn.close()
