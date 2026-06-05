import requests, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

resp = requests.get('https://zh.moegirl.org.cn/api.php', params={
    'action': 'query',
    'titles': '玛修·基列莱特',
    'prop': 'revisions',
    'rvprop': 'content',
    'rvslots': 'main',
    'rvlimit': 1,
    'format': 'json'
}, headers=headers, timeout=15)
print(f'Status: {resp.status_code}')
print(f'Response: {resp.text[:1000]}')
