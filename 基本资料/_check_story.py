import sqlite3
conn = sqlite3.connect('fgo_wiki.db')
total = conn.execute('SELECT COUNT(*) FROM story_scripts').fetchone()[0]
regions = conn.execute('SELECT region, COUNT(*) FROM story_scripts GROUP BY region').fetchall()
print('Total:', total)
print('By region:', regions)
old_fmt = conn.execute("SELECT COUNT(*) FROM story_scripts WHERE script_id LIKE '%_%'").fetchone()[0]
print('Underscore format IDs:', old_fmt)
new_fmt = conn.execute("SELECT COUNT(*) FROM story_scripts WHERE script_id NOT LIKE '%_%'").fetchone()[0]
print('Normal format IDs:', new_fmt)
