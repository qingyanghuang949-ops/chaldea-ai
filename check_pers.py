import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Check chat_system personalities
with open(r'D:\fgo ai\chat_system\personalities.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
first_key = list(data.keys())[0]
print(f'chat_system: {len(data)} entries, has mooncell_icon: {"mooncell_icon" in data[first_key]}')

# Check 基本资料 personalities
with open(r'D:\fgo ai\基本资料\personalities.json', 'r', encoding='utf-8') as f:
    data2 = json.load(f)
first_key2 = list(data2.keys())[0]
print(f'基本资料: {len(data2)} entries, has mooncell_icon: {"mooncell_icon" in data2[first_key2]}')

# Merge mooncell_icon into chat_system personalities
updated = 0
for pid, info in data.items():
    if pid in data2 and 'mooncell_icon' in data2[pid]:
        info['mooncell_icon'] = data2[pid]['mooncell_icon']
        updated += 1

with open(r'D:\fgo ai\chat_system\personalities.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f'Updated {updated} entries with mooncell_icon')
