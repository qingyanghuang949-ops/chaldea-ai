import sqlite3

conn = sqlite3.connect('fgo_wiki.db')
cursor = conn.cursor()

# Check all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]

for name in tables:
    cursor.execute(f"SELECT COUNT(*) FROM [{name}]")
    count = cursor.fetchone()[0]
    print(f"  {name}: {count}")

# Check story_scripts specifically
if 'story_scripts' in tables:
    cursor.execute("SELECT region, COUNT(*) FROM story_scripts GROUP BY region")
    for row in cursor.fetchall():
        print(f"    {row[0]}: {row[1]} scripts")
    
    cursor.execute("SELECT COUNT(*) FROM story_scripts WHERE script_text IS NOT NULL OR script_text != ''")
    has_text = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM story_scripts")
    total = cursor.fetchone()[0]
    print(f"    With text: {has_text}/{total}")

conn.close()
