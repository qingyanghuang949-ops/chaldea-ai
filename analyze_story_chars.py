import sqlite3, re, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = sqlite3.connect(r'D:\fgo ai\fgo_wiki.db')
c = conn.cursor()

# Extract character-to-script mapping from story scripts
# Format: [charaSet A 8001000 0 マシュ] or Ａ：character_name
chara_pattern = re.compile(r'\[charaSet\s+\w\s+(\d+)\s+\d+\s+(.+?)\]')
dialogue_pattern = re.compile(r'^＠(?:\w：)?(.+?)$', re.MULTILINE)

# Build character name -> script mapping
char_scripts = {}  # name -> list of (script_id, quest_name, region)

c.execute("SELECT script_id, region, quest_name, script_text FROM story_scripts")
total = c.fetchone()[0] if False else 0
c.execute("SELECT COUNT(*) FROM story_scripts")
total = c.fetchone()[0]
print(f"Total scripts: {total}")

c.execute("SELECT script_id, region, quest_name, script_text FROM story_scripts")
script_count = 0
for row in c:
    sid, region, qname, text = row
    if not text:
        continue
    script_count += 1
    
    # Find characters in charaSet
    chars_in_script = set()
    for m in chara_pattern.finditer(text):
        cid, cname = m.groups()
        chars_in_script.add(cname)
    
    # Find dialogue speakers
    for m in dialogue_pattern.finditer(text):
        name = m.group(1).strip()
        if name and not name.startswith('？') and len(name) < 30:
            chars_in_script.add(name)
    
    for name in chars_in_script:
        if name not in char_scripts:
            char_scripts[name] = []
        char_scripts[name].append({
            'script_id': sid,
            'quest_name': qname,
            'region': region
        })

print(f"Processed {script_count} scripts")
print(f"Unique characters: {len(char_scripts)}")

# Show top 20 characters by script count
sorted_chars = sorted(char_scripts.items(), key=lambda x: len(x[1]), reverse=True)
print("\nTop 20 characters by story appearances:")
for name, scripts in sorted_chars[:20]:
    regions = set(s['region'] for s in scripts)
    print(f"  {name}: {len(scripts)} scripts ({', '.join(regions)})")

# Save the mapping
with open(r'D:\fgo ai\chat_system\char_story_map.json', 'w', encoding='utf-8') as f:
    json.dump(char_scripts, f, ensure_ascii=False, indent=2)
print(f"\nSaved to char_story_map.json")

conn.close()
