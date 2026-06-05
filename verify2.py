import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open(r'D:\fgo ai\chat_system\index.html', 'r', encoding='utf-8') as f:
    c = f.read()
checks = [
    ('renderGrid function', 'function renderGrid()' in c),
    ('openChat function', 'function openChat(pid)' in c),
    ('init function', 'async function init()' in c),
    ('sendMessage function', 'async function sendMessage()' in c),
    ('Lightbox', 'function openLightbox' in c),
    ('Grid 2 columns', 'grid-template-columns:repeat(2,1fr)' in c),
    ('onclick on card', 'onclick="openChat(' in c),
]
for name, ok in checks:
    status = 'OK' if ok else 'FAIL'
    print(f'{status}: {name}')
