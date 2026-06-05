import requests, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
resp = requests.get('http://localhost:5000/api/servants')
data = resp.json()
print(f'Total: {len(data)}')
s = data[0]
print(f'First: {s["name_cn"]} / mooncell_icon: {s.get("mooncell_icon", "none")}')
mc = sum(1 for s in data if s.get('mooncell_icon'))
print(f'With mooncell_icon: {mc}/{len(data)}')
