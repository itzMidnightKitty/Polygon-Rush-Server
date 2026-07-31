import sqlite3
conn = sqlite3.connect('../geometrybash_v2.db')
c = conn.cursor()
c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='levels'")
print(c.fetchone()[0])
