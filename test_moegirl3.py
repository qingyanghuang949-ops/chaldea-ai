import requests, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Try revisions API to get wikitext
resp = requests.get('https://zh.moegirl.org.cn/api.php', params={
    'action': 'query',
    'titles': '玛修·基列莱特',
    'prop': 'revisions',
    'rvprop': 'content',
    'rvslots': 'main',
    'rvlimit': 1,
    'format': 'json'
}, headers=headers, timeout=15)
print(f'Revisions: {resp.status_code}')
data = resp.json()
pages = data.get('query', {}).get('pages', {})
for pid, page in pages.items():
    revisions = page.get('revisions', [])
    if revisions:
        content = revisions[0].get('slots', {}).get('main', {}).get('*', '')
        print(f'  Page {pid}: {len(content)} chars')
        if len(content) > 100:
            print(content[:500])
    else:
        print(f'  Page {pid}: No revisions')
        # Check for error
        if 'missing' in page:
            print('  Page missing')
