import pygame
import os

class AudioManager:
    def __init__(self):
        self.sfx = {}
        self.available_tracks = []
        self.menu_playing = False
        self.music_vol = 0.5
        self.sfx_vol = 0.5
        self.settings_path = os.path.join(os.path.expanduser('~'), 'Documents', 'PolygonRush', 'settings.json')
        self.load_settings()
        
        try:
            pygame.mixer.init()
            self.mixer_active = True
        except Exception:
            self.mixer_active = False

        self.load_sfx()
        self.scan_music()
        self.update_volumes()

    def update_volumes(self):
        if not self.mixer_active: return
        self.music_vol = round(self.music_vol, 2)
        self.sfx_vol = round(self.sfx_vol, 2)
        pygame.mixer.music.set_volume(self.music_vol)
        for sound in self.sfx.values():
            if sound: sound.set_volume(self.sfx_vol)
        self.save_settings()

    def load_settings(self):
        import json
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r') as f:
                    data = json.load(f)
                    self.music_vol = data.get("music_vol", 0.5)
                    self.sfx_vol = data.get("sfx_vol", 0.5)
            except Exception: pass

    def save_settings(self):
        import json
        os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
        try:
            with open(self.settings_path, 'w') as f:
                json.dump({"music_vol": self.music_vol, "sfx_vol": self.sfx_vol}, f)
        except Exception: pass

    def load_sfx(self):
        if not self.mixer_active: return
        for file in ['menu.mp3', 'button.mp3', 'death.mp3', 'win.mp3', 'start.mp3']:
            path = os.path.join("audio", "sfx", file)
            if os.path.exists(path):
                try: self.sfx[file] = pygame.mixer.Sound(path)
                except Exception: self.sfx[file] = None

    def _meta_path(self):
        return os.path.join("audio", "music", "_meta.json")

    def load_track_meta(self):
        import json
        self.track_meta = {}
        path = self._meta_path()
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    self.track_meta = json.load(f)
            except Exception:
                self.track_meta = {}

    def save_track_meta(self):
        import json
        try:
            os.makedirs(os.path.dirname(self._meta_path()), exist_ok=True)
            with open(self._meta_path(), 'w') as f:
                json.dump(self.track_meta, f)
        except Exception: pass

    def set_track_meta(self, filename, title=None, artist=None):
        entry = self.track_meta.get(filename, {})
        if title is not None: entry['title'] = title
        if artist is not None: entry['artist'] = artist
        entry['is_ng'] = filename.startswith('ng_')
        self.track_meta[filename] = entry
        self.save_track_meta()

    def get_track_length(self, filename):
        entry = self.track_meta.get(filename, {})
        if 'length' in entry:
            return entry['length']
        length = 0
        if self.mixer_active:
            path = os.path.join("audio", "music", filename)
            try:
                length = int(round(pygame.mixer.Sound(path).get_length()))
            except Exception:
                length = 0
        entry['length'] = length
        self.track_meta[filename] = entry
        self.save_track_meta()
        return length

    def get_track_display(self, filename):
        """Returns (title, artist, is_ng) for a track, deriving reasonable
        defaults for files with no stored metadata (bundled/official tracks)."""
        entry = self.track_meta.get(filename, {})
        is_ng = entry.get('is_ng', filename.startswith('ng_'))
        title = entry.get('title')
        artist = entry.get('artist')
        if not title:
            name = filename[:-4] if filename.lower().endswith(('.mp3', '.wav')) else filename
            if is_ng:
                # ng_<id>_<slug> fallback if metadata is somehow missing
                parts = name.split('_', 2)
                name = parts[2] if len(parts) == 3 else name
            title = name.replace('_', ' ').strip() or filename
        return title, artist, is_ng

    def delete_track(self, filename):
        """Only ever call this for NG/custom-downloaded tracks -- official
        bundled tracks are never deletable from the UI."""
        path = os.path.join("audio", "music", filename)
        try:
            if os.path.exists(path): os.remove(path)
        except Exception: pass
        self.track_meta.pop(filename, None)
        self.save_track_meta()
        if filename in self.available_tracks:
            self.available_tracks.remove(filename)

    def scan_music(self):
        self.available_tracks = []
        if not hasattr(self, 'track_meta'): self.load_track_meta()
        if not self.mixer_active: return
        path = os.path.join("audio", "music")
        if os.path.exists(path):
            for file in os.listdir(path):
                if file.endswith(".mp3") or file.endswith(".wav"):
                    self.available_tracks.append(file)

    def play_sfx(self, name):
        if not self.mixer_active: return
        sound = self.sfx.get(name)
        if sound: sound.play()

    def play_menu_music(self):
        if not self.mixer_active or self.menu_playing: return
        path = os.path.join("audio", "sfx", "menu.mp3")
        if os.path.exists(path):
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.play(-1)
                self.menu_playing = True
            except Exception: pass

    def preload_music(self, filename):
        if not self.mixer_active or not filename: return False
        path = os.path.join("audio", "music", filename)
        if not os.path.exists(path):
            path = os.path.join("audio", "sfx", filename)
        if os.path.exists(path):
            try:
                pygame.mixer.music.load(path)
                return True
            except Exception: return False
        return False
        
    def play_preloaded_music(self, offset=0.0):
        if not self.mixer_active: return
        try:
            pygame.mixer.music.play(-1, start=offset)
            self.menu_playing = False
        except Exception: pass

    def play_music(self, filename, offset=0.0):
        if self.preload_music(filename):
            length = self.get_track_length(filename)
            if length > 0 and offset >= length:
                offset = offset % length
            self.play_preloaded_music(max(0.0, offset))
        else:
            # Fallback if music not found
            if getattr(self, 'available_tracks', []):
                fallback = self.available_tracks[0]
                if self.preload_music(fallback):
                    self.play_preloaded_music(offset)

    def stop_music(self):
        if self.mixer_active:
            pygame.mixer.music.stop()
            self.menu_playing = False

    def pause_music(self):
        if self.mixer_active:
            pygame.mixer.music.pause()

    def unpause_music(self):
        if self.mixer_active:
            pygame.mixer.music.unpause()