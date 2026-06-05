import requests, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

# Try mobileview API
resp = requests.get('https://zh.moegirl.org.cn/api.php', params={
    'action': 'mobileview',
    'page': '玛修·基列莱特',
    'sections': 'all',
    'prop': 'text',
    'format': 'json'
}, headers=headers, timeout=15)
print(f'Status: {resp.status_code}')
if resp.status_code == 200:
    data = resp.json()
    if 'mobileview' in data:
        sections = data['mobileview'].get('sections', [])
        print(f'Sections: {len(sections)}')
        for s in sections[:5]:
            title = s.get('line', '?')
            text = s.get('text', '')
            print(f'  {title}: {len(text)} chars')
    else:
        print(json.dumps(data, ensure_ascii=False)[:500])
