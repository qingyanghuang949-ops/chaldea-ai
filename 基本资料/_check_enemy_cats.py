import requests
BASE_URL = 'https://fgo.wiki/api.php'
HEADERS = {'User-Agent': 'FGO-Wiki-Scraper/1.0'}

# Check 敌方从者 category
resp = requests.get(BASE_URL, params={
    'action': 'query', 'list': 'categorymembers',
    'cmtitle': 'Category:敌方从者', 'cmlimit': '10', 'cmtype': 'page', 'format': 'json'
}, headers=HEADERS, timeout=30)
data = resp.json()
members = data.get('query', {}).get('categorymembers', [])
print('Category:敌方从者 - first 10:')
for m in members:
    print('  %d: %s' % (m['pageid'], m['title']))

# Get total count
resp2 = requests.get(BASE_URL, params={
    'action': 'query', 'titles': 'Category:敌方从者',
    'prop': 'categoryinfo', 'format': 'json'
}, headers=HEADERS, timeout=30)
data2 = resp2.json()
pages = data2.get('query', {}).get('pages', {})
for pid, p in pages.items():
    ci = p.get('categoryinfo', {})
    print('Total pages: %s' % ci.get('size', '?'))

# Also search for other enemy-related categories
for cat in ['敌人', '敌方从者', '敌方角色', '敌方Boss', '怪物']:
    resp3 = requests.get(BASE_URL, params={
        'action': 'query', 'list': 'categorymembers',
        'cmtitle': 'Category:' + cat, 'cmlimit': '5', 'cmtype': 'page', 'format': 'json'
    }, headers=HEADERS, timeout=30)
    data3 = resp3.json()
    m3 = data3.get('query', {}).get('categorymembers', [])
    if m3:
        print('Category:%s found with %d+ pages' % (cat, len(m3)))
    else:
        print('Category:%s - empty or not found' % cat)
