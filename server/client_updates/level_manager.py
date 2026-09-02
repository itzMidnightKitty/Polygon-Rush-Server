import json
import os
import config
from game_objects import GameObject

class Level:
    def __init__(self, filename=None, folder="levels/custom"):
        self.objects = []
        self.music = None
        self.ng_song_id = None
        self.ng_song_name = None
        self.song_offset = 0.0
        self.speed = config.SCROLL_SPEED
        self.start_speed = config.SCROLL_SPEED
        self.name = "Unnamed"
        self.creator = "Unknown"
        self.start_gamemode = "cube"
        self.start_bg_idx = 0
        self.start_ground_idx = 7
        self.bg_design = 0
        self.ground_design = 0
        self.difficulty = config.DIFF_NORMAL
        self.normal_best = 0
        self.practice_best = 0
        self.verified = False
        self.noclip = False
        self.end_x = 1200
        self.filename = filename
        self.folder = folder
        if filename:
            self.load(filename, folder)

    def load(self, filename, folder="levels/custom"):
        self.filename = filename
        self.folder = folder
        path = os.path.join(folder, filename)
        if not os.path.exists(path): return
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                self.name = data.get("name", filename.replace(".json",""))
                self.creator = data.get("creator", "Unknown")
                self.music = data.get("music", None)
                self.ng_song_id = data.get("ng_song_id", None)
                self.ng_song_name = data.get("ng_song_name", None)
                self.song_offset = data.get("song_offset", 0.0)
                if "song_data" in data and self.music:
                    audio_path = os.path.join("audio", "music", self.music)
                    if not os.path.exists(audio_path):
                        import base64
                        try:
                            os.makedirs(os.path.dirname(audio_path), exist_ok=True)
                            with open(audio_path, "wb") as af:
                                af.write(base64.b64decode(data["song_data"]))
                        except Exception: pass
                self.speed = data.get("speed", config.SCROLL_SPEED)
                self.start_speed = self.speed  # the configured starting speed, kept
                # separately from self.speed since speed triggers mutate self.speed
                # live during a run -- resetting on replay must go back to THIS, not
                # the global default
                self.start_gamemode = data.get("start_gamemode", "cube")
                self.start_bg_idx = data.get("start_bg_idx", 0)
                self.start_ground_idx = data.get("start_ground_idx", 7)
                self.bg_design = data.get("bg_design", 0)
                self.ground_design = data.get("ground_design", 0)
                self.difficulty = data.get("difficulty", config.DIFF_NORMAL)
                self.normal_best = data.get("normal_best", 0)
                self.practice_best = data.get("practice_best", 0)
                self.verified = data.get("verified", False)
                self.noclip = data.get("noclip", False)
                self.objects = []
                for o in data.get("objects", []):
                    self.objects.append(GameObject(o['type'], o['x'], o['y'], o.get('rotation', 0), o.get('color_idx', 0), o.get('flip_x', False), o.get('flip_y', False), layer=o.get('layer', 0)))
                self.update_end_x()
        except Exception: pass

    def load_from_json(self, json_str):
        try:
            data = json.loads(json_str) if isinstance(json_str, str) else json_str
            self.name = data.get("name", "Online Level")
            self.creator = data.get("creator", "Unknown")
            self.music = data.get("music", None)
            self.ng_song_id = data.get("ng_song_id", None)
            self.ng_song_name = data.get("ng_song_name", None)
            self.song_offset = data.get("song_offset", 0.0)
            if "song_data" in data and self.music:
                audio_path = os.path.join("audio", "music", self.music)
                if not os.path.exists(audio_path):
                    import base64
                    try:
                        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
                        with open(audio_path, "wb") as af:
                            af.write(base64.b64decode(data["song_data"]))
                    except Exception: pass
            self.speed = data.get("speed", config.SCROLL_SPEED)
            self.start_speed = self.speed
            self.start_gamemode = data.get("start_gamemode", "cube")
            self.start_bg_idx = data.get("start_bg_idx", 0)
            self.start_ground_idx = data.get("start_ground_idx", 7)
            self.bg_design = data.get("bg_design", 0)
            self.ground_design = data.get("ground_design", 0)
            self.difficulty = data.get("difficulty", config.DIFF_NORMAL)
            self.normal_best = data.get("normal_best", 0)
            self.practice_best = data.get("practice_best", 0)
            self.verified = data.get("verified", False)
            self.noclip = data.get("noclip", False)
            self.objects = []
            for o in data.get("objects", []):
                self.objects.append(GameObject(o['type'], o['x'], o['y'], o.get('rotation', 0), o.get('color_idx', 0), o.get('flip_x', False), o.get('flip_y', False), layer=o.get('layer', 0)))
            self.update_end_x()
        except Exception: pass

    def save(self, filename=None, folder=None):
        if filename is None: filename = getattr(self, 'filename', None)
        if folder is None: folder = getattr(self, 'folder', "levels/custom")
        
        if not filename:
            import uuid
            filename = f"{self.name.replace(' ', '_').lower()}_{uuid.uuid4().hex[:6]}.json"
            
        if not filename.endswith(".json"): filename += ".json"
        self.filename = filename
        self.folder = folder
        
        if not os.path.exists(folder):
            os.makedirs(folder)
            
        path = os.path.join(folder, filename)
        data = {
            "name": self.name,
            "creator": self.creator,
            "music": self.music,
            "ng_song_id": getattr(self, 'ng_song_id', None),
            "ng_song_name": getattr(self, 'ng_song_name', None),
            "song_offset": getattr(self, 'song_offset', 0.0),
            "speed": self.speed,
            "start_gamemode": self.start_gamemode,
            "start_bg_idx": self.start_bg_idx,
            "start_ground_idx": self.start_ground_idx,
            "bg_design": self.bg_design,
            "ground_design": self.ground_design,
            "difficulty": self.difficulty,
            # normal_best/practice_best deliberately NOT saved here -- this is
            # shared/distributable level content, and progress is per-player.
            # It used to be saved into the level file itself, which meant a
            # creator play-testing their own upload baked their own progress
            # in, and everyone who downloaded it inherited those numbers as
            # if they were their own. Progress now lives in a separate
            # per-account store (see Game.get_progress_store_path in main.py).
            "verified": self.verified,
            "noclip": self.noclip,
            "objects": [o.to_dict() for o in self.objects]
        }
        
        if self.music:
            audio_path = os.path.join("audio", "music", self.music)
            if os.path.exists(audio_path):
                import base64
                try:
                    with open(audio_path, "rb") as af:
                        data["song_data"] = base64.b64encode(af.read()).decode('utf-8')
                except Exception: pass

        try:
            with open(path, 'w') as f: json.dump(data, f)
        except Exception: pass

    def update_end_x(self):
        for obj in self.objects:
            if obj.type == config.OBJ_END_TRIGGER:
                self.end_x = obj.x
                return
        self.end_x = max([obj.x for obj in self.objects] + [1200]) + 400

    def get_spawn_points(self):
        """All spawn points, sorted left-to-right by x. The furthest-right one is
        the default spawn (matches placing later/alternate starts to the left)."""
        pts = [(o.x, o.y) for o in self.objects if o.type == config.OBJ_SPAWN]
        pts.sort(key=lambda p: p[0])
        return pts

    def get_closest_spawn(self, current_x, direction):
        """direction: -1 for left, +1 for right. Returns the closest spawn (x,y)
        strictly in that direction from current_x, wrapping around to the far end
        if already at the edge in that direction (so cycling never just stops
        dead at one end) -- or None if there's nothing to switch to at all."""
        pts = self.get_spawn_points()
        if len(pts) < 2:
            return None
        if direction < 0:
            candidates = [p for p in pts if p[0] < current_x]
            return candidates[-1] if candidates else pts[-1]
        else:
            candidates = [p for p in pts if p[0] > current_x]
            return candidates[0] if candidates else pts[0]

    def get_spawn_x(self):
        pts = self.get_spawn_points()
        return pts[-1][0] if pts else 200

    def get_spawn_y(self):
        pts = self.get_spawn_points()
        return pts[-1][1] if pts else None