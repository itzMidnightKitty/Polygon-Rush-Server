import sys
sys.path.append('server')
from server.database import SessionLocal
import server.models as models
import json

db = SessionLocal()
lvls = db.query(models.Level).all()
print(f"Found {len(lvls)} levels")
for l in lvls:
    v = db.query(models.LevelVersion).filter(models.LevelVersion.level_id == l.id, models.LevelVersion.is_current_published == True).first()
    if v:
        print(f"Level {l.id} - '{l.title}' data type: {type(v.data)}")
        try:
            d = json.loads(v.data)
            print(f"  Parsed JSON dict! Keys: {list(d.keys())}")
        except Exception as e:
            print(f"  Failed to parse JSON: {e}")
            print(f"  First 50 chars: {repr(v.data[:50])}")
