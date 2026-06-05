import requests, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
resp = requests.get('http://localhost:5000/api/servants')
data = resp.json()
print(f'Total: {len(data)}')
mc = sum(1 for s in data if s.get('mooncell_icon'))
print(f'With mooncell_icon: {mc}')
# Test chat endpoint
resp2 = requests.post('http://localhost:5000/api/chat', json={
    'servant_id': 2275,
    'message': '你好，贞德',
    'language': 'cn'
})
print(f'Chat status: {resp2.status_code}')
if resp2.status_code == 200:
    r = resp2.json()
    print(f'Response: {r.get("response", "")[:200]}')
else:
    print(f'Error: {resp2.text[:200]}')
