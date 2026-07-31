import sys
sys.path.append('server')
from server.database import SessionLocal
import server.models as models

db = SessionLocal()
level = db.query(models.Level).filter(models.Level.id == 15).first()
if not level: print("No level")
else:
    version = db.query(models.LevelVersion).filter(
        models.LevelVersion.level_id == level.id,
        models.LevelVersion.is_current_published == True
    ).first()
    if not version: print("No version")
    else: print("Version exists:", len(version.data))
