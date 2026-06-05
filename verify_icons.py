import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open(r'D:\fgo ai\chat_system\index.html', 'r', encoding='utf-8') as f:
    c = f.read()
checks = [
    ('mooncell in grid', 'mooncell' in c and 'servant-card' in c),
    ('icon round style', 'border-radius:50%' in c),
    ('grid auto-fill 90px', 'minmax(90px,1fr)' in c),
    ('mooncell route in app', True),  # checked separately
]
for name, ok in checks:
    status = 'OK' if ok else 'FAIL'
    print(f'{status}: {name}')

with open(r'D:\fgo ai\chat_system\app.py', 'r', encoding='utf-8') as f:
    c = f.read()
checks2 = [
    ('mooncell route', '/assets/mooncell/' in c),
    ('mooncell_icon in API', 'mooncell_icon' in c),
]
for name, ok in checks2:
    status = 'OK' if ok else 'FAIL'
    print(f'{status}: {name}')
