import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open(r'D:\fgo ai\chat_system\personalities.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f'Total servants in personalities: {len(data)}')

for i, (k, v) in enumerate(list(data.items())[:3]):
    print(f'  {k}: {v.get("name_cn", "?")} / {v.get("name_jp", "?")}')
    print(f'    artwork: {v.get("artwork_file", "none")}')
    print(f'    icon: {v.get("icon_file", "none")}')
