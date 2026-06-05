import requests, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

cookies = {
    '_gid': 'GA1.3.373479924.1780588731',
    '_ga': 'GA1.1.1688750168.1780588731',
}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

# Try to get a page with cookies
resp = requests.get('https://zh.moegirl.org.cn/贞德', cookies=cookies, headers=headers, timeout=15)
print(f'Status: {resp.status_code}')
print(f'Content length: {len(resp.text)}')
if resp.status_code == 200:
    # Check if it's actual content
    if '贞德' in resp.text and 'Fate' in resp.text:
        print('Got actual content!')
        # Extract text
        from html.parser import HTMLParser
        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
                self.skip = False
            def handle_starttag(self, tag, attrs):
                if tag in ('script', 'style', 'noscript'):
                    self.skip = True
            def handle_endtag(self, tag):
                if tag in ('script', 'style', 'noscript'):
                    self.skip = False
            def handle_data(self, data):
                if not self.skip:
                    self.text.append(data.strip())
        parser = TextExtractor()
        parser.feed(resp.text)
        full_text = ' '.join(t for t in parser.text if t)
        print(f'Extracted text: {len(full_text)} chars')
        print(full_text[:500])
    elif '403' in resp.text[:200] or 'cloudflare' in resp.text.lower():
        print('Cloudflare blocked')
    else:
        print('Unknown response')
        print(resp.text[:300])
