import sqlite3
import os

db_path = 'geometrybash_v2.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("UPDATE users SET is_admin = 1, is_moderator = 1 WHERE username LIKE 'Midnight%'")
    conn.commit()
    print(f'Updated {c.rowcount} rows')
    conn.close()
else:
    print('Database not found!')
