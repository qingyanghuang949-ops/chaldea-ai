import requests, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

resp = requests.post('http://localhost:5000/api/chat', json={
    'servant_id': 2275,
    'message': '请介绍一下你的故事，你在各个特异点都经历了什么？',
    'language': 'cn'
}, timeout=60)
print(f'Status: {resp.status_code}')
if resp.status_code == 200:
    r = resp.json()
    print(f'Response: {r.get("response", "")[:500]}')
else:
    print(f'Error: {resp.text[:200]}')
