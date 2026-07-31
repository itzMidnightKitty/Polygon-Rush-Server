import sqlite3

conn = sqlite3.connect('../geometrybash_v2.db')
c = conn.cursor()

# Enable foreign keys
c.execute("PRAGMA foreign_keys=off;")

# Create new table with AUTOINCREMENT
c.execute("""
CREATE TABLE levels_new (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, 
	level_id VARCHAR, 
	title VARCHAR, 
	creator_id INTEGER, 
	created_at INTEGER, 
	FOREIGN KEY(creator_id) REFERENCES users (id)
)
""")

# Copy data
c.execute("INSERT INTO levels_new SELECT * FROM levels;")

# Drop old table
c.execute("DROP TABLE levels;")

# Rename new table
c.execute("ALTER TABLE levels_new RENAME TO levels;")

# Recreate indices
c.execute("CREATE UNIQUE INDEX ix_levels_level_id ON levels (level_id);")
c.execute("CREATE INDEX ix_levels_id ON levels (id);")
c.execute("CREATE INDEX ix_levels_title ON levels (title);")

conn.commit()
conn.close()
print("Migrated levels table to use AUTOINCREMENT")
