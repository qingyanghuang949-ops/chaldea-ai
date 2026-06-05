import sqlite3, os
db = os.path.join(r'D:\OpenClaw\workspace\fgo_wiki_scraper', 'fgo_wiki.db')
print('DB path:', db, 'exists:', os.path.exists(db))
conn = sqlite3.connect(db)
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('Tables:', [t[0] for t in tables])
for t in tables:
    c = conn.execute(f'SELECT COUNT(*) FROM [{t[0]}]').fetchone()[0]
    print(f'  {t[0]}: {c}')
conn.close()
