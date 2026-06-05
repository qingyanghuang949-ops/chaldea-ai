import sqlite3

conn = sqlite3.connect(r'D:\fgo ai\fgo_wiki.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print("Tables:", tables)
conn.close()
