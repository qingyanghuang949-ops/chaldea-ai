import requests, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Try to get multiple pages at once
titles = '玛修·基列莱特|贞德|阿尔托莉雅·潘德拉贡'
resp = requests.get('https://zh.moegirl.org.cn/api.php', params={
    'action': 'query',
    'titles': titles,
    'prop': 'extracts',
    'explaintext': True,
    'exintro': False,
    'exlimit': 3,
    'format': 'json'
}, headers=headers, timeout=15)
print(f'Status: {resp.status_code}')
data = resp.json()
pages = data.get('query', {}).get('pages', {})
for pid, page in pages.items():
    title = page.get('title', '?')
    text = page.get('extract', '')
    print(f'{title}: {len(text)} chars')
    if len(text) > 50:
        print(f'  {text[:200]}')
