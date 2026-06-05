import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Load data
with open(r'D:\fgo ai\chat_system\personalities.json', 'r', encoding='utf-8') as f:
    personalities = json.load(f)

with open(r'D:\fgo ai\chat_system\servant_stories.json', 'r', encoding='utf-8') as f:
    servant_stories = json.load(f)

# For each servant, create a story memory summary
# Limit to top 20 most relevant stories to keep prompt size manageable
updated = 0
for pid, info in personalities.items():
    stories = servant_stories.get(pid, [])
    if not stories:
        info['story_memory'] = []
        continue
    
    # Get unique quest names and summaries
    seen_quests = set()
    memory_entries = []
    for s in stories:
        qname = s.get('quest_name', '')
        if qname and qname not in seen_quests:
            seen_quests.add(qname)
            summary = s.get('summary', '').strip()
            if summary and len(summary) > 10:
                memory_entries.append({
                    'quest': qname,
                    'summary': summary[:300]
                })
        if len(memory_entries) >= 20:
            break
    
    info['story_memory'] = memory_entries
    updated += 1

# Save updated personalities
with open(r'D:\fgo ai\chat_system\personalities.json', 'w', encoding='utf-8') as f:
    json.dump(personalities, f, ensure_ascii=False, indent=2)

print(f"Updated {updated} servants with story memory")

# Show sample
for pid in ['190', '2275', '841']:
    if pid in personalities:
        name = personalities[pid].get('name_cn', pid)
        mem = personalities[pid].get('story_memory', [])
        print(f"\n{name}: {len(mem)} story memories")
        for m in mem[:3]:
            print(f"  - {m['quest']}: {m['summary'][:80]}...")
