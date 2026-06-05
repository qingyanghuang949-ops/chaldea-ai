import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open(r'D:\fgo ai\chat_system\index.html', 'r', encoding='utf-8') as f:
    c = f.read()

checks = [
    ('Card click handler on main div', 'class="servant-card" onclick="openChat' in c),
    ('card-click removed', 'card-click' not in c),
    ('Text color improved', '--text:#f0f0f0' in c),
    ('Font size improved', 'font-size:15px' in c),
    ('Font weight improved', 'font-weight:700' in c),
    ('Logo glow improved', 'text-shadow:0 0 30px' in c),
    ('Search input improved', 'rgba(255,255,255,0.08)' in c),
    ('Lightbox exists', 'lightbox' in c),
]

for name, ok in checks:
    print(f"{'OK' if ok else 'FAIL'}: {name}")
