import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

with open(r'D:\fgo ai\chat_system\index.html', 'r', encoding='utf-8') as f:
    c = f.read()

# Find the grid rendering
idx = c.find('grid.innerHTML = filtered.map')
if idx >= 0:
    end = c.find("}).join('')", idx)
    if end < 0:
        end = c.find("}).join(", idx)
    if end >= 0:
        end = c.find(';', end) + 1
        print(c[idx:end])
