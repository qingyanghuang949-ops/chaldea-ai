import sqlite3, re, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = sqlite3.connect(r'D:\fgo ai\fgo_wiki.db')
c = conn.cursor()

# For each servant, extract CN dialogue samples from story scripts
servant_cn_dialogue = {}

c.execute("SELECT page_id, name FROM servants")
servants = c.fetchall()

for pid, name in servants:
    # Find CN scripts where this servant speaks
    c.execute("""
        SELECT script_text, quest_name FROM story_scripts 
        WHERE region='CN' AND script_text LIKE ?
        LIMIT 10
    """, (f'＠%{name}%',))
    
    dialogues = []
    for row in c:
        text, qname = row
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('＠') and name in line:
                # Get the next non-empty line as dialogue
                for j in range(i+1, min(i+4, len(lines))):
                    next_line = lines[j].strip()
                    if next_line and not next_line.startswith('[') and not next_line.startswith('＠') and not next_line.startswith('{'):
                        # Clean up the line
                        next_line = re.sub(r'\[.*?\]', '', next_line)
                        next_line = next_line.replace('[r]', ' ').replace('[line 6]', '……')
                        if len(next_line) > 5 and len(next_line) < 100:
                            dialogues.append(next_line)
                            break
        if len(dialogues) >= 5:
            break
    
    if dialogues:
        servant_cn_dialogue[pid] = dialogues[:5]

conn.close()

print(f"Found CN dialogue for {len(servant_cn_dialogue)} servants")

# Show samples
for pid in [190, 2275, 841, 2662, 2952]:
    if pid in servant_cn_dialogue:
        print(f"\n{pid}: {servant_cn_dialogue[pid][:3]}")

# Save
with open(r'D:\fgo ai\chat_system\cn_dialogues.json', 'w', encoding='utf-8') as f:
    json.dump(servant_cn_dialogue, f, ensure_ascii=False, indent=2)
print(f"\nSaved cn_dialogues.json")
