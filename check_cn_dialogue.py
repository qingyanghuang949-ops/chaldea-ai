import sqlite3, re, sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conn = sqlite3.connect(r'D:\fgo ai\fgo_wiki.db')
c = conn.cursor()

# Get CN dialogue for key servants
servants_to_check = ['190', '2275', '841', '2662', '2952']  # 玛修, 贞德, 清姬, 刑部姬, 罗宾汉

for pid in servants_to_check:
    # Get servant name
    c.execute("SELECT name FROM servants WHERE page_id=?", (int(pid),))
    row = c.fetchone()
    if not row:
        continue
    name = row[0]
    
    # Find CN dialogue for this servant
    c.execute("""
        SELECT script_text, quest_name FROM story_scripts 
        WHERE region='CN' AND script_text LIKE ?
        LIMIT 3
    """, (f'%{name}%',))
    
    print(f"\n=== {name} ({pid}) ===")
    for row in c:
        text, qname = row
        # Extract dialogue lines
        lines = text.split('\n')
        for line in lines:
            if line.strip().startswith('＠') and name in line:
                # Get the next non-empty line as dialogue
                idx = lines.index(line)
                for next_line in lines[idx+1:idx+3]:
                    next_line = next_line.strip()
                    if next_line and not next_line.startswith('[') and not next_line.startswith('＠'):
                        print(f"  [{qname}] {next_line[:100]}")
                        break
        break  # Just show first script

conn.close()
