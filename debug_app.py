import json, sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Check if app.py serves the API correctly
with open(r'D:\fgo ai\chat_system\app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

# Check if the /api/servants endpoint queries the database
if 'SELECT page_id, name, rarity, class, nicknames FROM servants' in app_code:
    print('OK: API query exists')
else:
    print('FAIL: API query missing')

# Check ASSETS_BASE
if "ASSETS_BASE = r'D:\\fgo ai\\基本资料'" in app_code:
    print('OK: ASSETS_BASE correct')
else:
    print('WARN: ASSETS_BASE might be wrong')

# Check if DB exists and has data
import sqlite3
db_path = r'D:\fgo ai\fgo_wiki.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM servants')
    count = c.fetchone()[0]
    print(f'DB servants: {count}')
    c.execute('SELECT page_id, name FROM servants LIMIT 3')
    for row in c:
        print(f'  {row[0]}: {row[1]}')
    conn.close()
else:
    print('FAIL: DB not found')
