import requests, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Try with exsentences to get more content
resp = requests.get('https://zh.moegirl.org.cn/api.php', params={
    'action': 'query',
    'titles': '玛修·基列莱特',
    'prop': 'extracts',
    'explaintext': True,
    'exintro': False,
    'exsentences': 50,
    'format': 'json'
}, headers=headers, timeout=15)
print(f'Status: {resp.status_code}')
data = resp.json()
pages = data.get('query', {}).get('pages', {})
for pid, page in pages.items():
    text = page.get('extract', '')
    print(f'Page {pid}: {len(text)} chars')
    print(text[:1000])
