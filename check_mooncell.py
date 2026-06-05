import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open(r'D:\fgo ai\基本资料\personalities.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
for i, (k, v) in enumerate(list(data.items())[:3]):
    name = v.get('name', '?')
    icon = v.get('mooncell_icon', 'none')
    print(f'{k}: {name} -> {icon}')
print(f'Total: {len(data)}')
