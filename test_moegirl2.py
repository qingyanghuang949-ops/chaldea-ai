import requests, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Try different API approaches
# 1. Try extracts with exlimit
resp = requests.get('https://zh.moegirl.org.cn/api.php', params={
    'action': 'query',
    'titles': '玛修·基列莱特',
    'prop': 'extracts',
    'explaintext': True,
    'exintro': False,
    'exlimit': 1,
    'exsectionformat': 'plain',
    'format': 'json'
}, headers=headers, timeout=15)
print(f'Extracts: {resp.status_code}')
data = resp.json()
pages = data.get('query', {}).get('pages', {})
for pid, page in pages.items():
    text = page.get('extract', '')
    print(f'  Page {pid}: {len(text)} chars')
    if len(text) > 100:
        print(text[:300])

# 2. Try with exsentences
resp2 = requests.get('https://zh.moegirl.org.cn/api.php', params={
    'action': 'query',
    'titles': '玛修·基列莱特',
    'prop': 'extracts',
    'explaintext': True,
    'exintro': False,
    'exsentences': 20,
    'format': 'json'
}, headers=headers, timeout=15)
print(f'\nExtracts with exsentences: {resp2.status_code}')
data2 = resp2.json()
pages2 = data2.get('query', {}).get('pages', {})
for pid, page in pages2.items():
    text = page.get('extract', '')
    print(f'  Page {pid}: {len(text)} chars')
    if len(text) > 50:
        print(text[:300])
