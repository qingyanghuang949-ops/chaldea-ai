import sqlite3
conn = sqlite3.connect(r'D:\OpenClaw\workspace\fgo_wiki_scraper\fgo_wiki.db')
conn.execute("DELETE FROM page_index WHERE category='敌人一览'")
conn.commit()
print('Deleted enemy page_index entries')
# Also check item count
count = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
print(f'Items: {count}')
conn.close()
