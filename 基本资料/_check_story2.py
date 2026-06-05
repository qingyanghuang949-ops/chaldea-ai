import sqlite3
conn = sqlite3.connect('fgo_wiki.db')
total = conn.execute('SELECT COUNT(*) FROM story_scripts').fetchone()[0]
regions = conn.execute('SELECT region, COUNT(*) FROM story_scripts GROUP BY region').fetchall()
print('Total:', total)
print('By region:', regions)
