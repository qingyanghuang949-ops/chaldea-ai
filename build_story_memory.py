import sqlite3, re, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = sqlite3.connect(r'D:\fgo ai\fgo_wiki.db')
c = conn.cursor()

# Step 1: Build JP<->CN character name mapping
# We can get this from the servants table and the story scripts
# First, get all servant names
servant_names = {}  # page_id -> {cn, jp}
c.execute("SELECT page_id, name FROM servants")
for row in c:
    pid, name = row
    servant_names[pid] = {'cn': name, 'jp': name}  # Default to same

# Now load personalities to get JP names
with open(r'D:\fgo ai\chat_system\personalities.json', 'r', encoding='utf-8') as f:
    personalities = json.load(f)

for pid, info in personalities.items():
    if int(pid) in servant_names:
        servant_names[int(pid)]['cn'] = info.get('name_cn', servant_names[int(pid)]['cn'])
        servant_names[int(pid)]['jp'] = info.get('name_jp', servant_names[int(pid)]['jp'])

# Step 2: Build charaSet name -> servant page_id mapping
# From story scripts, charaSet format: [charaSet A 8001000 0 マシュ]
chara_pattern = re.compile(r'\[charaSet\s+\w\s+(\d+)\s+\d+\s+(.+?)\]')

# Build atlas_id -> page_id mapping
atlas_to_pid = {}
for pid, names in servant_names.items():
    atlas_to_pid[names['jp']] = pid
    atlas_to_pid[names['cn']] = pid

# Also map common character names
name_aliases = {
    'マシュ': 190, '玛修': 190, 'マシュ・キリエライト': 190,
    'Dr.ロ曼': None, 'Dr.罗曼': None,  # NPC
    'ダ・ヴィンチ': None, '达·芬奇': None,  # NPC
    'フォウ': None, '芙芙': None,  # NPC
    'ゴルドルフ': None, '戈尔德鲁夫': None,  # NPC
    'ホームズ': None, '福尔摩斯': None,  # NPC
    'エフェクト用': None, '特效用': None,  # System
    'エフェクト用ダミー': None, '特效用dummy': None,  # System
    'エフェクト用1': None, 'エフェクト用2': None,  # System
    '特效用1': None, '特效用2': None,  # System
}

# Step 3: Extract story summaries per servant
# For each script, extract key plot points
def extract_script_summary(text, max_len=500):
    """Extract a brief summary from a story script"""
    if not text:
        return ""
    lines = text.split('\n')
    dialogue_lines = []
    for line in lines:
        line = line.strip()
        # Skip commands
        if line.startswith('[') or line.startswith('＄') or line.startswith('？'):
            continue
        # Get dialogue lines (＠name: text)
        if line.startswith('＠'):
            # Extract just the text after the speaker
            parts = line.split('：', 1)
            if len(parts) > 1:
                dialogue_lines.append(parts[1].strip())
        elif line and not line.startswith('{') and not line.startswith('#'):
            # Regular text
            if len(line) > 5 and len(line) < 200:
                dialogue_lines.append(line)
    
    summary = ' '.join(dialogue_lines[:10])  # First 10 lines
    return summary[:max_len]

# Step 4: Build servant story memory
print("Building servant story memory...")
servant_stories = {}  # page_id -> list of {quest_name, region, summary, script_id}

c.execute("SELECT script_id, region, quest_name, script_text FROM story_scripts WHERE region='CN'")
script_count = 0
for row in c:
    sid, region, qname, text = row
    if not text:
        continue
    script_count += 1
    
    # Find all characters in this script
    chars = set()
    for m in chara_pattern.finditer(text):
        cid, cname = m.groups()
        # Try to map to page_id
        pid = name_aliases.get(cname) or atlas_to_pid.get(cname)
        if pid:
            chars.add(pid)
    
    # Also check dialogue speakers
    for line in text.split('\n'):
        if line.strip().startswith('＠'):
            parts = line.strip().split('：', 1)
            if len(parts) > 1:
                speaker = parts[0].replace('＠', '').strip()
                # Remove color codes
                speaker = re.sub(r'\[.*?\]', '', speaker).strip()
                pid = name_aliases.get(speaker) or atlas_to_pid.get(speaker)
                if pid:
                    chars.add(pid)
    
    # For each character found, add this story to their memory
    if chars:
        summary = extract_script_summary(text)
        for pid in chars:
            if pid not in servant_stories:
                servant_stories[pid] = []
            servant_stories[pid].append({
                'script_id': sid,
                'quest_name': qname,
                'region': region,
                'summary': summary
            })
    
    if script_count % 2000 == 0:
        print(f"  Processed {script_count} scripts...")

print(f"Processed {script_count} CN scripts")
print(f"Servants with story memory: {len(servant_stories)}")

# Show top 10
sorted_servants = sorted(servant_stories.items(), key=lambda x: len(x[1]), reverse=True)
print("\nTop 10 servants by story appearances:")
for pid, stories in sorted_servants[:10]:
    name = servant_names.get(pid, {}).get('cn', str(pid))
    print(f"  {name} ({pid}): {len(stories)} stories")

# Save
with open(r'D:\fgo ai\chat_system\servant_stories.json', 'w', encoding='utf-8') as f:
    json.dump(servant_stories, f, ensure_ascii=False, indent=2)
print(f"\nSaved servant_stories.json")

conn.close()
