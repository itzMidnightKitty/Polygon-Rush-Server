import main
from level_manager import Level
g = main.Game()
import sys
sys.path.append('server')
from server.database import SessionLocal
import server.models as models
import json

db = SessionLocal()
l = db.query(models.Level).first()
v = db.query(models.LevelVersion).filter(models.LevelVersion.level_id == l.id, models.LevelVersion.is_current_published == True).first()

lvl_obj = Level()
lvl_obj.load_from_json(v.data)
lvl_obj.filename = "Online Level"
lvl_obj.folder = "online"

print("Trying play_level...")
try:
    g.play_level(None, None, is_practice=False, reset_attempts=True, play_start_sfx=False, online_level=lvl_obj)
    print("play_level succeeded! state is:", g.state)
except Exception as e:
    import traceback
    traceback.print_exc()
