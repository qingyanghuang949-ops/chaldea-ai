import sqlite3
conn = sqlite3.connect('fgo_wiki.db')
for table in ['servants','noble_phantasms','skills','craft_essences','items','enemies','page_index']:
    try:
        c = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
        print(f'{table}: {c}')
    except Exception as e:
        print(f'{table}: ERROR - {e}')
conn.close()
