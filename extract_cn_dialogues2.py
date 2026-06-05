import sqlite3, re, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = sqlite3.connect(r'D:\fgo ai\fgo_wiki.db')
c = conn.cursor()

# Get all servant names for matching
c.execute("SELECT page_id, name FROM servants")
servant_names = {row[1]: row[0] for row in c.fetchall()}

# Extract CN dialogue for each servant
servant_cn_dialogue = {}

c.execute("SELECT script_id, script_text FROM story_scripts WHERE region='CN'")
script_count = 0
for row in c:
    sid, text = row
    if not text:
        continue
    script_count += 1
    
    lines = text.split('\n')
    for i, line in enumerate(lines):
        # Match speaker pattern: ＠name or ＠X：name
        m = re.match(r'＠(?:\w：)?(.+?)$', line.strip())
        if not m:
            continue
        speaker = m.group(1).strip()
        # Skip system/unknown speakers
        if speaker.startswith('？') or speaker.startswith('[') or speaker.startswith('%'):
            continue
        if '广播' in speaker or '特效' in speaker or '效果' in speaker:
            continue
        
        # Check if this speaker is a servant
        pid = servant_names.get(speaker)
        if not pid:
            continue
        
        # Get the next non-empty line as dialogue
        for j in range(i+1, min(i+4, len(lines))):
            next_line = lines[j].strip()
            if not next_line or next_line.startswith('＠') or next_line.startswith('['):
                continue
            # Clean up
            next_line = re.sub(r'\[.*?\]', '', next_line)
            next_line = next_line.replace('[r]', ' ').replace('[line 6]', '……')
            next_line = next_line.strip()
            if len(next_line) > 3 and len(next_line) < 150:
                if pid not in servant_cn_dialogue:
                    servant_cn_dialogue[pid] = []
                if len(servant_cn_dialogue[pid]) < 10:
                    servant_cn_dialogue[pid].append(next_line)
                break
    
    if script_count % 2000 == 0:
        print(f"Processed {script_count} scripts...")

conn.close()

print(f"\nProcessed {script_count} CN scripts")
print(f"Found CN dialogue for {len(servant_cn_dialogue)} servants")

# Show samples
for pid in [190, 2275, 841, 2662, 2952]:
    if pid in servant_cn_dialogue:
        name = [k for k, v in servant_names.items() if v == pid][0] if pid in servant_names.values() else str(pid)
        print(f"\n{name} ({pid}):")
        for d in servant_cn_dialogue[pid][:3]:
            print(f"  - {d}")

# Save
with open(r'D:\fgo ai\chat_system\cn_dialogues.json', 'w', encoding='utf-8') as f:
    json.dump(servant_cn_dialogue, f, ensure_ascii=False, indent=2)
print(f"\nSaved cn_dialogues.json")
