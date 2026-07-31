#!/usr/bin/env python3
import pygame
import sys
import os
import json
import base64
import config
from config import S
from network import NetworkManager
from ui_elements import TextInput
from audio_manager import AudioManager
from player import Player
from level_manager import Level
from editor import Editor
from graphics import draw_world_background, draw_world_ground, draw_difficulty_face

CLIENT_VERSION = 1.3

def init_folders():
    for folder in ["levels/official", "levels/custom", "audio/music", "audio/sfx"]: 
        os.makedirs(folder, exist_ok=True)

class Game:
    def __init__(self):
        pygame.init()
        self.apply_resolution()
        pygame.display.set_caption("Polygon Rush")
        self.clock = pygame.time.Clock()
        self.audio = AudioManager()
        
        self.state = "MENU"
        self.play_fade = 255
        self.is_practice_mode = False
        self.checkpoints = []
        self.player = Player()
        self.current_level = None
        self.level_files = []
        self.level_creators = []
        self.selected_level_idx = 0
        self.editor = None
        self.max_icons = 8
        
        self.fade_bg_color = [0, 0, 0]
        self.fade_gnd_color = [0, 0, 0]
        
        self.network = NetworkManager()
        
        # Auto-login if credentials exist
        self.saved_accounts = {}
        last_logged_in = None
        try:
            docs = os.path.join(os.path.expanduser('~'), 'Documents', 'PolygonRush')
            last_acc_path = os.path.join(docs, 'last_account.txt')
            if os.path.exists(last_acc_path):
                with open(last_acc_path, 'r', encoding='utf-8') as f:
                    last_logged_in = f.read().strip()
            
            if os.path.exists(docs):
                for user_dir in os.listdir(docs):
                    cred_path = os.path.join(docs, user_dir, 'credentials.json')
                    if os.path.exists(cred_path):
                        with open(cred_path, "r", encoding='utf-8') as f:
                            encoded = f.read().strip()
                        if encoded:
                            try:
                                data_str = base64.b64decode(encoded.encode('utf-8')).decode('utf-8')
                                creds = json.loads(data_str)
                                self.saved_accounts[creds["username"]] = creds["password"]
                            except: pass
        except: pass
        
        def auto_login_cb(res):
            if not res.get("success") and res.get("status_code") == 0:
                import threading, time
                def retry():
                    time.sleep(1)
                    if last_logged_in and last_logged_in in self.saved_accounts:
                        self.network.login(last_logged_in, self.saved_accounts[last_logged_in], auto_login_cb)
                    elif self.saved_accounts:
                        first_user = list(self.saved_accounts.keys())[0]
                        self.network.login(first_user, self.saved_accounts[first_user], auto_login_cb)
                threading.Thread(target=retry, daemon=True).start()

        if last_logged_in and last_logged_in in self.saved_accounts:
            self.network.login(last_logged_in, self.saved_accounts[last_logged_in], auto_login_cb)
        elif self.saved_accounts:
            first_user = list(self.saved_accounts.keys())[0]
            self.network.login(first_user, self.saved_accounts[first_user], auto_login_cb)
        
        self.audio.play_menu_music()

    def get_custom_levels_dir(self):
        username = getattr(self.network, 'username', None)
        if not username:
            username = "guest"
        username = "".join(c for c in username if c.isalnum() or c in ('_', '-'))
        docs = os.path.join(os.path.expanduser('~'), 'Documents')
        path = os.path.join(docs, 'PolygonRush', username, "levels", "custom")
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        return path

    def apply_resolution(self):
        self.screen = pygame.display.set_mode((config.RENDER_W, config.RENDER_H), pygame.RESIZABLE)
        self.font = pygame.font.SysFont("Arial", S(18), bold=True)
        self.title_font = pygame.font.SysFont("Arial", S(36), bold=True)
        self.login_username_input = TextInput(config.BASE_W//2 - 150, config.BASE_H//2 - 60, 300, 40, self.font, "Username")
        self.login_password_input = TextInput(config.BASE_W//2 - 150, config.BASE_H//2, 300, 40, self.font, "Password", is_password=True)
        self.online_levels = getattr(self, "online_levels", [])
        self.online_status_msg = getattr(self, "online_status_msg", "")

    def load_levels_list(self, folder):
        files = []
        self.level_creators = []
        if os.path.exists(folder):
            for f in os.listdir(folder):
                if f.endswith('.json'):
                    try:
                        with open(os.path.join(folder, f), 'r') as fp:
                            data = json.load(fp)
                            diff = data.get("difficulty", config.DIFF_NORMAL)
                            creator = data.get("creator", "Unknown")
                            files.append((f, diff, creator))
                    except: pass
        if folder == "levels/official":
            files.sort(key=lambda x: x[1])
        self.level_files = [f[0] for f in files]
        self.level_creators = [f[2] for f in files]
        self.selected_level_idx = 0

    def get_level_difficulty(self, filename, folder):
        path = os.path.join(folder, filename)
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f).get("difficulty", config.DIFF_NORMAL)
            except: pass
        return config.DIFF_NORMAL

    def play_level(self, filename, folder, is_practice=False, is_verify=False, reset_attempts=True, play_start_sfx=False, online_level=None):
        self.audio.stop_music()
        if online_level:
            self.current_level = online_level
        else:
            self.current_level = Level(filename, folder)
        self.ignore_mouse_jump = True
        self.is_practice_mode = is_practice
        self.checkpoints = []
        self.current_level.speed = getattr(config, 'SCROLL_SPEED', 6)
        for obj in self.current_level.objects: obj.activated = False
        
        if reset_attempts:
            self.attempts = 1
            
        spawn_x = self.current_level.get_spawn_x()
        self.player.reset(start_x=spawn_x, start_y=self.current_level.get_spawn_y(), start_mode=self.current_level.start_gamemode)
        self.state = "PLAY"
        
        if hasattr(self, 'camera_y'): delattr(self, 'camera_y')
        
        self.fade_bg_color = list(config.BG_COLORS[self.current_level.start_bg_idx])
        self.fade_gnd_color = list(config.BG_COLORS[self.current_level.start_ground_idx])
        
        if play_start_sfx: self.audio.play_sfx('start.mp3')
        if is_practice:
            import random
            prac_track = random.choice(["practice1.mp3", "practice2.mp3"])
            self.audio.play_music(prac_track)
        else:
            if not self.current_level.music and self.audio.available_tracks: self.current_level.music = self.audio.available_tracks[0]
            if self.current_level.music: 
                offset = max(0.0, (spawn_x - 200) / (self.current_level.speed * config.FPS))
                self.audio.play_music(self.current_level.music, offset=offset)
        self.player.jump_held = pygame.key.get_pressed()[pygame.K_SPACE] or pygame.mouse.get_pressed()[0] or pygame.key.get_pressed()[pygame.K_UP]

    def get_active_bg_color(self, target_x):
        active_color = config.BG_COLORS[self.current_level.start_bg_idx] if self.current_level else config.BG_COLORS[0]
        if self.current_level:
            for obj in self.current_level.objects:
                if obj.type == config.OBJ_COLOR_TRIGGER and obj.x <= target_x: active_color = config.BG_COLORS[obj.color_idx]
        return active_color

    def get_active_ground_color(self, target_x):
        active_color = config.BG_COLORS[self.current_level.start_ground_idx] if self.current_level else config.DARK_GRAY
        if self.current_level:
            for obj in self.current_level.objects:
                if obj.type == config.OBJ_GROUND_COLOR_TRIGGER and obj.x <= target_x: active_color = config.BG_COLORS[obj.color_idx]
        return active_color

    def draw_volume_setting(self, label, value, y_pos):
        t = self.font.render(label, True, config.WHITE)
        self.screen.blit(t, (S(config.BASE_W//2 - 150), S(y_pos)))
        
        left_rect = pygame.Rect(S(config.BASE_W//2 + 50), S(y_pos - 5), S(30), S(30))
        pygame.draw.rect(self.screen, config.GRAY, left_rect)
        self.screen.blit(self.font.render("<", True, config.WHITE), (left_rect.x + S(8), left_rect.y + S(2)))
        
        val_t = self.font.render(f"{int(value * 100)}%", True, config.WHITE)
        self.screen.blit(val_t, (S(config.BASE_W//2 + 100), S(y_pos)))
        
        right_rect = pygame.Rect(S(config.BASE_W//2 + 160), S(y_pos - 5), S(30), S(30))
        pygame.draw.rect(self.screen, config.GRAY, right_rect)
        self.screen.blit(self.font.render(">", True, config.WHITE), (right_rect.x + S(8), right_rect.y + S(2)))
        
        return pygame.Rect(config.BASE_W//2 + 50, y_pos - 5, 30, 30), pygame.Rect(config.BASE_W//2 + 160, y_pos - 5, 30, 30)

    def draw_dummy_player(self, surface, mode, idx, color, x, y, size):
        temp_player = Player()
        temp_player.mode = mode
        temp_player.rotation = 0
        old_color, old_c_idx, old_s_idx, old_b_idx, old_w_idx = config.P_COLOR, config.P_CUBE_IDX, config.P_SHIP_IDX, config.P_BALL_IDX, config.P_WAVE_IDX
        config.P_COLOR, config.P_CUBE_IDX, config.P_SHIP_IDX, config.P_BALL_IDX, config.P_WAVE_IDX = color, idx, idx, idx, idx
        
        temp_player.width, temp_player.height = size, size
        temp_player.x, temp_player.y = x, y
        temp_player.draw(surface, 0, 0, zoom=1.0)
        
        config.P_COLOR, config.P_CUBE_IDX, config.P_SHIP_IDX, config.P_BALL_IDX, config.P_WAVE_IDX = old_color, old_c_idx, old_s_idx, old_b_idx, old_w_idx

    def draw_icon_selector(self, mode, current_idx, x_pos, y_pos, label):
        lbl = self.font.render(label, True, config.WHITE)
        self.screen.blit(lbl, (S(x_pos) - lbl.get_width()//2, S(y_pos - 70)))
        
        l_btn = pygame.Rect(S(x_pos - 120), S(y_pos - 20), S(40), S(80))
        r_btn = pygame.Rect(S(x_pos + 80), S(y_pos - 20), S(40), S(80))
        pygame.draw.rect(self.screen, config.GRAY, l_btn, 0, S(5))
        pygame.draw.rect(self.screen, config.GRAY, r_btn, 0, S(5))
        self.screen.blit(self.title_font.render("<", True, config.WHITE), (l_btn.x + S(8), l_btn.y + S(18)))
        self.screen.blit(self.title_font.render(">", True, config.WHITE), (r_btn.x + S(8), r_btn.y + S(18)))
        
        self.draw_dummy_player(self.screen, mode, current_idx, config.P_COLOR, x_pos - 30, y_pos - 10, 60)
        
        return l_btn, r_btn


    def load_online_hub(self):
        self.active_popup = None
        self.online_tab = "levels" if self.network.token else "create"
        self.online_status_msg = "Loading..."
        if self.network.token:
            def cb(res):
                if res.get("success"): self.online_levels = res.get("data", [])
                else: self.online_status_msg = "Failed to load levels"
            self.network.get_levels(callback=cb)
            if not getattr(self, 'my_profile_data', None):
                def p_cb(res):
                    if res.get("success"): self.my_profile_data = res.get("data")
                self.network.get_user_profile(self.network.username, p_cb)
        self.load_levels_list(self.get_custom_levels_dir()) # For Drafts tab
        self.users_search_text = ""
        self.users_search_active = False
        self.online_users = []

    def get_credentials_path(self):
        username = getattr(self.network, 'username', None)
        if not username:
            username = "guest"
        username = "".join(c for c in username if c.isalnum() or c in ('_', '-'))
        docs = os.path.join(os.path.expanduser('~'), 'Documents')
        folder = os.path.join(docs, 'PolygonRush', username)
        if not os.path.exists(folder): os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, 'credentials.json')

    def load_profile(self, target_user=None):
        self.profile_user = target_user or self.network.username
        self.profile_data = None
        self.profile_msg = "Loading profile..."
        self.profile_levels = []
        self.editing_icons = False
        
        def cb(res):
            if res.get("success"):
                self.profile_data = res.get("data")
                self.profile_msg = ""
                # If viewing own profile, parse colors
                if self.profile_data["username"] == self.network.username:
                    config.P_CUBE_IDX = self.profile_data["icon_cube"]
                    config.P_SHIP_IDX = self.profile_data["icon_ship"]
                    config.P_BALL_IDX = self.profile_data["icon_ball"]
                    config.P_WAVE_IDX = self.profile_data["icon_wave"]
                    try:
                        r, g, b = map(int, self.profile_data["color1"].split(','))
                        config.P_COLOR = (r, g, b)
                        r2, g2, b2 = map(int, self.profile_data["color2"].split(','))
                        config.P_COLOR2 = (r2, g2, b2)
                    except: pass
            else:
                self.profile_msg = "User not found."
        self.network.get_user_profile(self.profile_user, cb)
    
    def handle_rate_popup_click(self, logical_mouse):
        popup_rect = pygame.Rect(config.BASE_W//2 - 300, config.BASE_H//2 - 150, 600, 300)
        if popup_rect.collidepoint(logical_mouse):
            for i in range(1, 11):
                bx = config.BASE_W//2 - 180 + ((i-1)%5)*70
                by = config.BASE_H//2 - 60 + ((i-1)//5)*60
                if pygame.Rect(bx, by, 60, 40).collidepoint(logical_mouse):
                    def rate_cb(r):
                        if r.get("success"):
                            self.online_status_msg = "Rated successfully!"
                            if hasattr(self, 'selected_level_data') and isinstance(self.selected_level_data, dict):
                                self.selected_level_data['has_rated'] = True
                        else:
                            self.online_status_msg = r.get("data", {}).get("detail", r.get("message", "Rated!"))
                    self.network.rate_level(self.popup_version_id, i, rate_cb)
                    self.active_popup = None
                    self.audio.play_sfx('button.mp3')
                    break
        else:
            self.active_popup = None

    def handle_moderate_popup_click(self, logical_mouse):
        popup_rect = pygame.Rect(config.BASE_W//2 - 300, config.BASE_H//2 - 150, 600, 300)
        if popup_rect.collidepoint(logical_mouse):
            is_admin = getattr(self, 'my_profile_data', {}).get('is_admin')
            if is_admin:
                diffs = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
                for i, d in enumerate(diffs):
                    bx = config.BASE_W//2 - 180 + (i%5)*70
                    by = config.BASE_H//2 - 60 + (i//5)*60
                    if pygame.Rect(bx, by, 60, 40).collidepoint(logical_mouse):
                        self.network.moderate_level(self.popup_version_id, "published", d, lambda r: setattr(self, 'state', 'ONLINE_HUB') or self.load_online_hub())
                        self.active_popup = None
                        self.audio.play_sfx('button.mp3')
                        break
                
                del_btn = pygame.Rect(config.BASE_W//2 - 150, config.BASE_H//2 + 80, 300, 35)
                if del_btn.collidepoint(logical_mouse):
                    self.network.delete_level(self.popup_level_id, lambda r: setattr(self, 'state', 'ONLINE_HUB') or self.load_online_hub())
                    self.active_popup = None
                    self.audio.play_sfx('button.mp3')
            else:
                send_btn = pygame.Rect(config.BASE_W//2 - 140, config.BASE_H//2 - 30, 280, 40)
                rej_btn = pygame.Rect(config.BASE_W//2 - 140, config.BASE_H//2 + 30, 280, 40)
                if send_btn.collidepoint(logical_mouse):
                    self.network.moderate_level(self.popup_version_id, "sent_to_admin", 0, lambda r: setattr(self, 'state', 'ONLINE_HUB') or self.load_online_hub())
                    self.active_popup = None
                    self.audio.play_sfx('button.mp3')
                elif rej_btn.collidepoint(logical_mouse):
                    self.network.moderate_level(self.popup_version_id, "rejected", 0, lambda r: setattr(self, 'state', 'ONLINE_HUB') or self.load_online_hub())
                    self.active_popup = None
                    self.audio.play_sfx('button.mp3')
        else:
            self.active_popup = None

    def _draw_popup(self):
        from graphics import draw_difficulty_face
        if getattr(self, 'active_popup', None):
            if self.active_popup == "exit_confirm":
                return
            s = pygame.Surface((config.RENDER_W, config.RENDER_H), pygame.SRCALPHA)
            s.fill((0, 0, 0, 180))
            self.screen.blit(s, (0,0))
        
            w = 600 if self.active_popup == "upload_confirm" else 400
            h = 360 if self.active_popup == "upload_confirm" else 300
            p_rect = pygame.Rect(S(config.BASE_W//2 - w//2), S(config.BASE_H//2 - h//2), S(w), S(h))
            pygame.draw.rect(self.screen, (30, 30, 40), p_rect, 0, S(10))
            pygame.draw.rect(self.screen, config.CYAN, p_rect, max(1, S(2)), S(10))
        
            if self.active_popup == "rate":
                t = self.title_font.render("Rate Level", True, config.WHITE)
                self.screen.blit(t, (p_rect.centerx - t.get_width()//2, p_rect.y + S(20)))
                for i in range(1, 11):
                    bx = config.BASE_W//2 - 180 + ((i-1)%5)*70
                    by = config.BASE_H//2 - 60 + ((i-1)//5)*60
                    br = pygame.Rect(S(bx), S(by), S(60), S(40))
                    pygame.draw.rect(self.screen, (50, 50, 60), br, 0, S(5))
                    draw_difficulty_face(self.screen, bx + 10, by, 35, i)
                
            elif self.active_popup == "moderate":
                is_admin = getattr(self, 'my_profile_data', {}).get('is_admin')
                
                diff_names = {1:"Easy", 2:"Normal", 3:"Hard", 4:"Harder", 5:"Insane", 6:"Easy Demon", 7:"Medium Demon", 8:"Hard Demon", 9:"Insane Demon", 10:"Extreme Demon"}
                req_stars = getattr(self, 'selected_level_data', {}).get('requested_stars', 0)
                if req_stars:
                    req_t = self.font.render(f"User requested: {diff_names.get(req_stars, 'Unknown')}", True, config.YELLOW)
                    self.screen.blit(req_t, (p_rect.centerx - req_t.get_width()//2, p_rect.y + S(45)))
                if is_admin:
                    t = self.title_font.render("Official Rating", True, config.WHITE)
                    self.screen.blit(t, (p_rect.centerx - t.get_width()//2, p_rect.y + S(20)))
                    diffs = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
                    for i, d in enumerate(diffs):
                        bx = config.BASE_W//2 - 180 + (i%5)*70
                        by = config.BASE_H//2 - 60 + (i//5)*60
                        br = pygame.Rect(S(bx), S(by), S(60), S(40))
                        pygame.draw.rect(self.screen, (50, 50, 60), br, 0, S(5))
                        draw_difficulty_face(self.screen, bx + 10, by, 35, d)
                    
                    del_btn = pygame.Rect(S(config.BASE_W//2 - 150), S(config.BASE_H//2 + 80), S(300), S(35))
                    pygame.draw.rect(self.screen, config.RED, del_btn, 0, S(5))
                    pygame.draw.rect(self.screen, config.WHITE, del_btn, max(1, S(2)), S(5))
                    dt = self.font.render("DELETE LEVEL FROM SERVER", True, config.WHITE)
                    self.screen.blit(dt, (del_btn.centerx - dt.get_width()//2, del_btn.centery - dt.get_height()//2))
                else:
                    t = self.title_font.render("Moderate Level", True, config.WHITE)
                    self.screen.blit(t, (p_rect.centerx - t.get_width()//2, p_rect.y + S(20)))
                
                    send_btn = pygame.Rect(S(config.BASE_W//2 - 140), S(config.BASE_H//2 - 30), S(280), S(40))
                    pygame.draw.rect(self.screen, config.GREEN, send_btn, 0, S(5))
                    pygame.draw.rect(self.screen, config.WHITE, send_btn, max(1, S(2)), S(5))
                    st = self.font.render("SEND TO ADMIN", True, config.BLACK)
                    self.screen.blit(st, (send_btn.centerx - st.get_width()//2, send_btn.centery - st.get_height()//2))
                
                    rej_btn = pygame.Rect(S(config.BASE_W//2 - 140), S(config.BASE_H//2 + 30), S(280), S(40))
                    pygame.draw.rect(self.screen, config.RED, rej_btn, 0, S(5))
                    pygame.draw.rect(self.screen, config.WHITE, rej_btn, max(1, S(2)), S(5))
                    rt = self.font.render("REJECT LEVEL", True, config.WHITE)
                    self.screen.blit(rt, (rej_btn.centerx - rt.get_width()//2, rej_btn.centery - rt.get_height()//2))
            elif self.active_popup == "switch_account":
                t = self.title_font.render("Switch Account", True, config.WHITE)
                self.screen.blit(t, (p_rect.centerx - t.get_width()//2, p_rect.y + S(20)))
                
                if len(self.saved_accounts) > 6:
                    scroll_msg = self.font.render("(Scroll for more)", True, config.GRAY)
                    self.screen.blit(scroll_msg, (p_rect.centerx - scroll_msg.get_width()//2, p_rect.y + S(50)))
                
                mx, my = pygame.mouse.get_pos()
                accounts = list(self.saved_accounts.keys())
                disp_accs = accounts[getattr(self, 'switch_scroll', 0):getattr(self, 'switch_scroll', 0)+6]
                p_rect_y_unscaled = config.BASE_H//2 - h//2
                
                for i, acc in enumerate(disp_accs):
                    y = p_rect_y_unscaled + 70 + i * 50
                    btn = pygame.Rect(S(config.BASE_W//2 - 150), S(y), S(300), S(40))
                    hover = btn.collidepoint((mx, my))
                    is_cur = (acc == self.network.username)
                    
                    pygame.draw.rect(self.screen, config.GREEN if is_cur else (50, 50, 70) if hover else (40, 40, 50), btn, 0, S(5))
                    txt = self.font.render(f"{acc}{' (Current)' if is_cur else ''}", True, config.BLACK if is_cur else config.WHITE)
                    self.screen.blit(txt, (btn.centerx - txt.get_width()//2, btn.centery - txt.get_height()//2))
                    
                add_btn = pygame.Rect(S(config.BASE_W//2 - 100), S(p_rect_y_unscaled + 70 + len(disp_accs) * 50 + 20), S(200), S(40))
                hover = add_btn.collidepoint((mx, my))
                pygame.draw.rect(self.screen, (70, 70, 90) if hover else config.BLUE, add_btn, 0, S(5))
                at = self.font.render("+ Add Account", True, config.WHITE)
                self.screen.blit(at, (add_btn.centerx - at.get_width()//2, add_btn.centery - at.get_height()//2))
                
                esc_msg = self.font.render("Press ESC to Cancel", True, config.GRAY)
                self.screen.blit(esc_msg, (p_rect.centerx - esc_msg.get_width()//2, p_rect.bottom - S(30)))

            elif self.active_popup == "delete_account_confirm":
                t = self.font.render("Are you sure you want to delete your account?", True, config.WHITE)
                self.screen.blit(t, (p_rect.centerx - t.get_width()//2, p_rect.y + S(80)))
            
                y_btn = pygame.Rect(S(config.BASE_W//2 - 100), S(config.BASE_H//2 + 20), S(80), S(35))
                n_btn = pygame.Rect(S(config.BASE_W//2 + 20), S(config.BASE_H//2 + 20), S(80), S(35))
                pygame.draw.rect(self.screen, config.RED, y_btn, 0, S(5))
                pygame.draw.rect(self.screen, config.DARK_GRAY, n_btn, 0, S(5))
                yt = self.font.render("Yes", True, config.WHITE)
                nt = self.font.render("No", True, config.WHITE)
                self.screen.blit(yt, (y_btn.centerx - yt.get_width()//2, y_btn.centery - yt.get_height()//2))
                self.screen.blit(nt, (n_btn.centerx - nt.get_width()//2, n_btn.centery - nt.get_height()//2))
            elif self.active_popup == "upload_confirm":
                t = self.title_font.render("Upload Level", True, config.WHITE)
                self.screen.blit(t, (p_rect.centerx - t.get_width()//2, p_rect.y + S(10)))
            
                name_rect = pygame.Rect(S(config.BASE_W//2 - 280), S(config.BASE_H//2 - 75), S(560), S(40))
                pygame.draw.rect(self.screen, (50, 50, 60), name_rect, 0, S(5))
                c = config.YELLOW if getattr(self, 'upload_input_focus', '') == 'name' else config.WHITE
                pygame.draw.rect(self.screen, c, name_rect, max(1, S(2)), S(5))
            
                name_text = getattr(self, 'upload_level_name', '')
                if getattr(self, 'upload_input_focus', '') == 'name' and pygame.time.get_ticks() % 1000 < 500: name_text += "|"
                nt = self.font.render(name_text, True, config.WHITE)
                self.screen.blit(nt, (name_rect.x + S(10), name_rect.centery - nt.get_height()//2))
            
                self.screen.blit(self.font.render("Select Difficulty:", True, config.GRAY), (S(config.BASE_W//2 - 275), S(config.BASE_H//2)))
            
                if getattr(self, 'upload_demon_selector', False):
                    sub_rect = pygame.Rect(S(config.BASE_W//2 - 190), S(config.BASE_H//2 - 30), S(380), S(100))
                    pygame.draw.rect(self.screen, (30, 30, 40), sub_rect, 0, S(10))
                    pygame.draw.rect(self.screen, config.CYAN, sub_rect, max(1, S(2)), S(10))
                    for i, d in enumerate([6, 7, 8, 9, 10]):
                        rect = pygame.Rect(sub_rect.x + S(15) + i*S(70), sub_rect.y + S(20), S(60), S(60))
                        pygame.draw.rect(self.screen, (50, 50, 60), rect, 0, S(5))
                        if d == getattr(self, 'upload_difficulty', 0): pygame.draw.rect(self.screen, config.GREEN, rect, max(1, S(2)), S(5))
                        draw_difficulty_face(self.screen, config.BASE_W//2 - 175 + i*70 + 5, config.BASE_H//2 - 10 + 5, 50, d)
                else:
                    for i in range(7):
                        rect = pygame.Rect(S(config.BASE_W//2 - 275 + i*70), S(config.BASE_H//2 + 50), S(60), S(60))
                        pygame.draw.rect(self.screen, (50, 50, 60), rect, 0, S(5))
                        if i == getattr(self, 'upload_difficulty', 0) and i != 6: pygame.draw.rect(self.screen, config.GREEN, rect, max(1, S(2)), S(5))
                        face_id = i if i < 6 else getattr(self, 'upload_difficulty', 0) if getattr(self, 'upload_difficulty', 0) >= 6 else 6
                        draw_difficulty_face(self.screen, config.BASE_W//2 - 275 + i*70 + 5, config.BASE_H//2 + 50 + 5, 50, face_id)
            
                save_btn = pygame.Rect(S(config.BASE_W//2 - 100), S(config.BASE_H//2 + 120), S(200), S(40))
                pygame.draw.rect(self.screen, config.GREEN, save_btn, 0, S(5))
                pygame.draw.rect(self.screen, config.WHITE, save_btn, max(1, S(2)), S(5))
                ut = self.font.render("UPLOAD LEVEL", True, config.BLACK)
                self.screen.blit(ut, (save_btn.centerx - ut.get_width()//2, save_btn.centery - ut.get_height()//2))


    def run(self):
        running = True
        while running:
            self.network.update()
            keys = pygame.key.get_pressed()
            raw_mouse_pos = pygame.mouse.get_pos()
            logical_mouse = (raw_mouse_pos[0] / config.get_scale(), raw_mouse_pos[1] / config.get_scale())
            
            scroll_y_dir = 0
            mouse_just_pressed = False 
            mouse_click = pygame.mouse.get_pressed()
            if not mouse_click[0]: self.ignore_mouse_jump = False

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    config.RENDER_W, config.RENDER_H = event.w, event.h
                    config.BASE_W = int(config.BASE_H * (event.w / event.h))
                    self.apply_resolution()
                elif event.type == pygame.MOUSEWHEEL:
                    scroll_y_dir = event.y
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_just_pressed = True

                if getattr(self, 'active_popup', None) == "switch_account":
                    if scroll_y_dir != 0:
                        self.switch_scroll = getattr(self, 'switch_scroll', 0) - scroll_y_dir
                        max_scroll = max(0, len(self.saved_accounts) - 6)
                        self.switch_scroll = max(0, min(max_scroll, self.switch_scroll))
                
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.active_popup = None; self.audio.play_sfx('button.mp3')
                    elif mouse_just_pressed:
                        accounts = list(self.saved_accounts.keys())
                        disp_accs = accounts[getattr(self, 'switch_scroll', 0):getattr(self, 'switch_scroll', 0)+6]
                        h = max(300, min(500, 150 + len(disp_accs) * 50))
                        p_rect_y = config.BASE_H//2 - h//2
                        for i, acc in enumerate(disp_accs):
                            y = p_rect_y + 70 + i * 50
                            btn = pygame.Rect(config.BASE_W//2 - 150, y, 300, 40)
                            if btn.collidepoint(logical_mouse):
                                if acc != self.network.username:
                                    def _switch_cb(r, a=acc):
                                        if r.get('success'):
                                            self.load_profile()
                                        elif r.get('error') == 'Unauthorized' or r.get('status_code') == 401 or 'Incorrect' in str(r):
                                            if a in getattr(self, 'saved_accounts', {}):
                                                del self.saved_accounts[a]
                                                docs_base = os.path.join(os.path.expanduser('~'), 'Documents', 'PolygonRush')
                                                import shutil
                                                p = os.path.join(docs_base, a)
                                                if os.path.exists(p): shutil.rmtree(p)
                                    self.network.login(acc, self.saved_accounts[acc], _switch_cb)
                                    docs = os.path.join(os.path.expanduser('~'), 'Documents', 'PolygonRush')
                                    with open(os.path.join(docs, 'last_account.txt'), "w", encoding="utf-8") as f: f.write(acc)
                                    self.active_popup = None
                                    mouse_just_pressed = False
                                    self.audio.play_sfx('button.mp3')
                        
                        add_btn = pygame.Rect(config.BASE_W//2 - 100, p_rect_y + 70 + len(disp_accs) * 50 + 20, 200, 40)
                        if add_btn.collidepoint(logical_mouse):
                            self.network.logout()
                            self.state = "LOGIN"
                            self.active_popup = None
                            mouse_just_pressed = False
                            self.audio.play_sfx('button.mp3')
                    continue

                if getattr(self, 'active_popup', None) == "delete_account_confirm":
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.active_popup = None; self.audio.play_sfx('button.mp3')
                    elif mouse_just_pressed:
                        y_btn = pygame.Rect(config.BASE_W//2 - 100, config.BASE_H//2 + 20, 80, 35)
                        n_btn = pygame.Rect(config.BASE_W//2 + 20, config.BASE_H//2 + 20, 80, 35)
                        if y_btn.collidepoint(logical_mouse):
                            def cb_delete(r):
                                import shutil
                                docs = os.path.join(os.path.expanduser('~'), 'Documents', 'PolygonRush', self.network.username)
                                if os.path.exists(docs): shutil.rmtree(docs)
                                if self.network.username in getattr(self, 'saved_accounts', {}):
                                    del self.saved_accounts[self.network.username]
                                docs_base = os.path.join(os.path.expanduser('~'), 'Documents', 'PolygonRush')
                                la_path = os.path.join(docs_base, 'last_account.txt')
                                if os.path.exists(la_path): os.remove(la_path)
                                self.network.logout()
                                self.state = "LOGIN"
                            self.network._make_request("DELETE", "/users/me", None, cb_delete)
                            self.active_popup = None
                            mouse_just_pressed = False
                            self.audio.play_sfx('button.mp3')
                        elif n_btn.collidepoint(logical_mouse):
                            self.active_popup = None; self.audio.play_sfx('button.mp3')
                            mouse_just_pressed = False
                    continue

                if self.state == "MENU":
                    if getattr(self, 'active_popup', None) == "exit_confirm":
                        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                            self.active_popup = None; self.audio.play_sfx('button.mp3')
                        elif mouse_just_pressed:
                            y_btn = pygame.Rect(config.BASE_W//2 - 100, config.BASE_H//2 + 20, 80, 35)
                            n_btn = pygame.Rect(config.BASE_W//2 + 20, config.BASE_H//2 + 20, 80, 35)
                            if y_btn.collidepoint(logical_mouse):
                                running = False
                            elif n_btn.collidepoint(logical_mouse):
                                self.active_popup = None; self.audio.play_sfx('button.mp3')
                            mouse_just_pressed = False
                        continue
                    elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.active_popup = "exit_confirm"; self.audio.play_sfx('button.mp3')
                        
                    if mouse_just_pressed:
                        btn_w, btn_h = 400, 50
                        btn_start_y = config.BASE_H // 4 + 80
                        
                        b_play = pygame.Rect(config.BASE_W//2 - btn_w//2, btn_start_y + 0 * 70, btn_w, btn_h)
                        b_online = pygame.Rect(config.BASE_W//2 - btn_w//2, btn_start_y + 1 * 70, btn_w, btn_h)
                        b_prof = pygame.Rect(config.BASE_W//2 - btn_w//2, btn_start_y + 2 * 70, btn_w//2 - 10, btn_h)
                        b_log = pygame.Rect(config.BASE_W//2 + 10, btn_start_y + 2 * 70, btn_w//2 - 10, btn_h)
                        b_set = pygame.Rect(config.BASE_W//2 - btn_w//2, btn_start_y + 3 * 70, btn_w, btn_h)
                        b_exit = pygame.Rect(config.BASE_W//2 - btn_w//2, btn_start_y + 4 * 70, btn_w//2 - 10, btn_h)
                        b_update = pygame.Rect(config.BASE_W//2 + 10, btn_start_y + 4 * 70, btn_w//2 - 10, btn_h)
                        
                        if b_play.collidepoint(logical_mouse):
                            self.load_levels_list("levels/official"); self.state = "MAIN_LEVELS"; self.audio.play_sfx('button.mp3')
                        elif b_online.collidepoint(logical_mouse):
                            self.state = "ONLINE_HUB"; getattr(self, "load_online_hub", lambda: None)(); self.audio.play_sfx('button.mp3')
                        elif b_prof.collidepoint(logical_mouse) and self.network.token:
                            self.profile_back_state = "MENU"
                            self.state = "PROFILE"; getattr(self, "load_profile", lambda: None)(); self.audio.play_sfx('button.mp3')
                        elif b_log.collidepoint(logical_mouse):
                            if self.network.token:
                                cred_path = self.get_credentials_path()
                                self.network.logout()
                                if os.path.exists(cred_path): os.remove(cred_path)
                                self.audio.play_sfx('button.mp3')
                            else:
                                self.state = "LOGIN"; self.audio.play_sfx('button.mp3')
                        elif b_set.collidepoint(logical_mouse):
                            self.state = "SETTINGS"; self.audio.play_sfx('button.mp3')
                        elif b_update.collidepoint(logical_mouse):
                            self.audio.play_sfx('button.mp3')
                            def cb_check(res):
                                if res.get("success"):
                                    v = res.get("data", {}).get("version", 0)
                                    if v > CLIENT_VERSION:
                                        self.update_msg = "Update available! Downloading..."
                                        def cb_dl(dl_res):
                                            if dl_res.get("success"):
                                                with open("main_new.py", "w", encoding="utf-8") as f:
                                                    f.write(dl_res.get("text", ""))
                                                updater_script = "import os, time, sys, subprocess\ntime.sleep(1)\ntry:\n    if os.path.exists('main.py'):\n        os.replace('main_new.py', 'main.py')\n    subprocess.Popen([sys.executable, 'main.py'])\nexcept Exception: pass\n"
                                                with open("updater.py", "w") as f:
                                                    f.write(updater_script)
                                                import subprocess
                                                subprocess.Popen([sys.executable, "updater.py"])
                                                import os; os._exit(0)
                                            else:
                                                self.update_msg = f"Failed: {dl_res.get('error')}"
                                        self.network.download_update(cb_dl)
                                    else:
                                        self.update_msg = "Game is up to date!"
                                else:
                                    self.update_msg = f"Error: {res.get('error')}"
                            self.network.check_update(cb_check)
                        elif b_exit.collidepoint(logical_mouse):
                            self.active_popup = "exit_confirm"; self.audio.play_sfx('button.mp3')

                elif self.state == "LOGIN":
                    self.login_username_input.handle_event(event, logical_mouse)
                    self.login_password_input.handle_event(event, logical_mouse)
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.state = "MENU"; self.audio.play_sfx('button.mp3')
                    elif mouse_just_pressed:
                        login_btn = pygame.Rect(config.BASE_W//2 - 150, config.BASE_H//2 + 60, 140, 40)
                        reg_btn = pygame.Rect(config.BASE_W//2 + 10, config.BASE_H//2 + 60, 140, 40)
                        
                        if login_btn.collidepoint(logical_mouse):
                            self.online_status_msg = "Logging in..."
                            def cb(res):
                                if res.get("success"):
                                    self.state = "MENU"
                                    self.online_status_msg = ""
                                    self.load_levels_list(self.get_custom_levels_dir())
                                    try:
                                        with open(self.get_credentials_path(), "w", encoding="utf-8") as f:
                                            data_str = json.dumps({"username": self.network.username, "password": self.login_password_input.text})
                                            encoded = base64.b64encode(data_str.encode('utf-8')).decode('utf-8')
                                            f.write(encoded)
                                            
                                        self.saved_accounts[self.network.username] = self.login_password_input.text
                                        docs = os.path.join(os.path.expanduser('~'), 'Documents', 'PolygonRush')
                                        if not os.path.exists(docs): os.makedirs(docs, exist_ok=True)
                                        with open(os.path.join(docs, 'last_account.txt'), "w", encoding="utf-8") as f:
                                            f.write(self.network.username)
                                    except Exception as e:
                                        with open("crash_log.txt", "w") as cl: cl.write(str(e))
                                else:
                                    err = res.get('data', {}).get('detail', res.get('error', 'Unknown Error')) if isinstance(res.get('data'), dict) else res.get('error', 'Unknown Error')
                                    self.online_status_msg = f"Login failed: {err}"
                            self.network.login(self.login_username_input.text, self.login_password_input.text, cb)
                            self.audio.play_sfx('button.mp3')
                        elif reg_btn.collidepoint(logical_mouse):
                            self.online_status_msg = "Registering..."
                            def cb(res):
                                    if res.get("success"):
                                        self.online_status_msg = "Registered! Now login."
                                    else:
                                        err = res.get('data', {}).get('detail', res.get('error', 'Unknown Error')) if isinstance(res.get('data'), dict) else res.get('error', 'Unknown Error')
                                        self.online_status_msg = f"Registration failed: {err}"
                            self.network.register(self.login_username_input.text, self.login_password_input.text, cb)
                            self.audio.play_sfx('button.mp3')

                elif self.state == "ONLINE_HUB":
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            if getattr(self, 'active_popup', None):
                                self.active_popup = None; self.audio.play_sfx('button.mp3')
                            else:
                                self.state = "MENU"; self.audio.play_sfx('button.mp3')
                        else:
                            if getattr(self, 'active_popup', None) == "upload_confirm":
                                if event.key == pygame.K_BACKSPACE:
                                    if self.upload_input_focus == "name": self.upload_level_name = self.upload_level_name[:-1]
                                else:
                                    target_str = self.upload_level_name if self.upload_input_focus == "name" else ""
                                    if self.upload_input_focus == "name" and len(target_str) < 20 and (event.unicode.isalnum() or event.unicode in (' ', '_', '-')):
                                        self.upload_level_name += event.unicode
                            elif getattr(self, 'online_tab', '') == "levels" and getattr(self, 'levels_search_active', False):
                                if event.key == pygame.K_BACKSPACE: self.levels_search_text = getattr(self, 'levels_search_text', '')[:-1]
                                elif event.unicode and event.unicode.isprintable(): self.levels_search_text = getattr(self, 'levels_search_text', '') + event.unicode
                            elif getattr(self, 'online_tab', '') == "create" and getattr(self, 'create_search_active', False):
                                if event.key == pygame.K_BACKSPACE: self.create_search_text = getattr(self, 'create_search_text', '')[:-1]
                                elif event.unicode and event.unicode.isprintable(): self.create_search_text = getattr(self, 'create_search_text', '') + event.unicode
                            elif getattr(self, 'online_tab', '') == "users" and getattr(self, 'users_search_active', False):
                                if event.key == pygame.K_BACKSPACE: self.users_search_text = getattr(self, 'users_search_text', '')[:-1]
                                elif event.key == pygame.K_RETURN:
                                    def user_cb(res):
                                        if res.get("success"): self.online_users = res.get("data", [])
                                        else: self.online_status_msg = "Failed to load users"
                                    self.network.get_users(getattr(self, 'users_search_text', ''), user_cb)
                                    self.audio.play_sfx('button.mp3')
                                elif event.unicode and event.unicode.isprintable(): self.users_search_text = getattr(self, 'users_search_text', '') + event.unicode
                    elif mouse_just_pressed:
                        if getattr(self, 'active_popup', None):
                            popup_rect = pygame.Rect(config.BASE_W//2 - 300, config.BASE_H//2 - 150, 600, 300)
                            if popup_rect.collidepoint(logical_mouse):
                                # clicks inside popup
                                if getattr(self, 'active_popup', None) == "rate":
                                    self.handle_rate_popup_click(logical_mouse)
                                elif getattr(self, 'active_popup', None) == "moderate":
                                    self.handle_moderate_popup_click(logical_mouse)
                                elif getattr(self, 'active_popup', None) == "upload_confirm":
                                    if getattr(self, 'upload_demon_selector', False):
                                        for i, d in enumerate([6, 7, 8, 9, 10]):
                                            rect = pygame.Rect(config.BASE_W//2 - 175 + i*70, config.BASE_H//2 - 10, 60, 60)
                                            if rect.collidepoint(logical_mouse):
                                                self.upload_difficulty = d
                                                self.upload_demon_selector = False
                                                self.audio.play_sfx('button.mp3')
                                        self.upload_demon_selector = False
                                    
                                    for i in range(7):
                                        rect = pygame.Rect(config.BASE_W//2 - 245 + i*70, config.BASE_H//2 + 50, 60, 60)
                                        if rect.collidepoint(logical_mouse):
                                            if i == 6: self.upload_demon_selector = True
                                            else: self.upload_difficulty = i
                                            self.audio.play_sfx('button.mp3')
                                            
                                    name_rect = pygame.Rect(config.BASE_W//2 - 280, config.BASE_H//2 - 75, 560, 40)
                                    if name_rect.collidepoint(logical_mouse):
                                        self.upload_input_focus = "name"
                                        self.audio.play_sfx('button.mp3')
                                        
                                    confirm_btn = pygame.Rect(config.BASE_W//2 - 100, config.BASE_H//2 + 120, 200, 40)
                                    if confirm_btn.collidepoint(logical_mouse):
                                        old_path = os.path.join(self.get_custom_levels_dir(), self.upload_level_file)
                                        new_filename = f"{self.upload_level_name.replace(' ', '_')}.json"
                                        new_path = os.path.join(self.get_custom_levels_dir(), new_filename)
                                        if os.path.exists(old_path):
                                            with open(old_path, 'r') as f_in:
                                                data = json.load(f_in)
                                            data['name'] = self.upload_level_name
                                            data['difficulty'] = self.upload_difficulty
                                            with open(new_path, 'w') as f_out:
                                                json.dump(data, f_out)
                                            if old_path != new_path:
                                                os.remove(old_path)
                                        with open(new_path, 'r') as f_final:
                                            data_str = f_final.read()
                                        if hasattr(self, 'network'):
                                            self.online_status_msg = "Uploading level..."
                                            def upload_cb(res):
                                                if res.get("success"):
                                                    self.online_status_msg = "Level uploaded successfully!"
                                                    self.load_levels_list(self.get_custom_levels_dir())
                                                    if hasattr(self, 'network'):
                                                        def cb_lvl(r):
                                                            if r.get("success"): self.online_levels = r.get("data", [])
                                                        self.network.get_levels(callback=cb_lvl)
                                                else:
                                                    self.online_status_msg = "Failed to upload level"
                                            level_id = data.get("level_id") # Future support for level updating
                                            self.network.upload_level(self.upload_level_name, data_str, self.upload_difficulty, level_id=level_id, callback=upload_cb)
                                        self.active_popup = None
                                        self.load_levels_list(self.get_custom_levels_dir())
                                        self.audio.play_sfx('button.mp3')
                            else:
                                self.active_popup = None # click outside closes it
                            continue # skip rest of clicks
                            
                        tabs = ["levels", "create", "users"] if self.network.token else ["create"]
                        for i, t in enumerate(tabs):
                            if len(tabs) == 1:
                                rect = pygame.Rect(config.BASE_W//2 - 90, 80, 180, 40)
                            else:
                                rect = pygame.Rect(config.BASE_W//2 - 300 + i * 200, 80, 180, 40)
                            if rect.collidepoint(logical_mouse):
                                self.online_tab = t; self.audio.play_sfx('button.mp3')
                                self.online_status_msg = ""
                                if t == "levels" and hasattr(self, 'network'):
                                    def cb(res):
                                        if res.get("success"): self.online_levels = res.get("data", [])
                                    self.network.get_levels(callback=cb)
                                elif t == "users" and hasattr(self, 'network'):
                                    def cb(res):
                                        if res.get("success"): self.online_users = res.get("data", [])
                                    self.network.get_users("", callback=cb)
                                elif t == "create":
                                    self.online_status_msg = ""
                                
                        if self.online_tab == "levels":
                            search_box = pygame.Rect(config.BASE_W//2 - 200, 150, 400, 40)
                            self.levels_search_active = search_box.collidepoint(logical_mouse)
                            
                            filtered_levels = getattr(self, 'online_levels', [])
                            s_txt = getattr(self, 'levels_search_text', '').lower()
                            if s_txt:
                                filtered_levels = [l for l in filtered_levels if s_txt in l.get('title','').lower() or s_txt in l.get('level_id','').lower()]
                                
                            for i, lvl in enumerate(filtered_levels):
                                row_rect = pygame.Rect(config.BASE_W//2 - 320, 210 + i * 40 - 5, 640, 35)
                                if row_rect.collidepoint(logical_mouse):
                                    self.state = "LEVEL_INFO"
                                    self.selected_level_data = lvl
                                    self.audio.play_sfx('button.mp3')
                                    break
                        elif self.online_tab == "create":
                            search_box = pygame.Rect(config.BASE_W//2 - 200, 150, 400, 40)
                            self.create_search_active = search_box.collidepoint(logical_mouse)
                            editor_btn = pygame.Rect(config.BASE_W//2 - 300, 210, 150, 40)
                            if editor_btn.collidepoint(logical_mouse):
                                self.ignore_mouse_jump = True
                                self.state = "EDITOR"; self.editor = Editor(self.audio, folder=self.get_custom_levels_dir()); self.audio.stop_music(); self.audio.play_sfx('button.mp3')
                                
                            c_txt = getattr(self, 'create_search_text', '').lower()
                            c_levels = [l for l in self.level_files if not c_txt or c_txt in l.lower()]
                            for i, lvl in enumerate(c_levels):
                                play_btn = pygame.Rect(config.BASE_W//2 - 20, 310 + i * 50, 60, 30)
                                prac_btn = pygame.Rect(config.BASE_W//2 + 45, 310 + i * 50, 80, 30)
                                ed_btn2 = pygame.Rect(config.BASE_W//2 + 130, 310 + i * 50, 60, 30)
                                up_btn = pygame.Rect(config.BASE_W//2 + 195, 310 + i * 50, 75, 30)
                                del_btn = pygame.Rect(config.BASE_W//2 + 275, 310 + i * 50, 70, 30)
                                if play_btn.collidepoint(logical_mouse):
                                    self.audio.stop_music()
                                    self.selected_level_idx = i
                                    self.play_level(lvl, self.get_custom_levels_dir(), is_practice=False, play_start_sfx=True)
                                    break
                                elif prac_btn.collidepoint(logical_mouse):
                                    self.audio.stop_music()
                                    self.selected_level_idx = i
                                    self.play_level(lvl, self.get_custom_levels_dir(), is_practice=True, play_start_sfx=True)
                                    break
                                elif up_btn.collidepoint(logical_mouse):
                                    verified = False
                                    try:
                                        l_obj = Level()
                                        l_obj.load(lvl, self.get_custom_levels_dir())
                                        verified = l_obj.verified
                                    except: pass
                                    if verified:
                                        self.active_popup = "upload_confirm"
                                        self.upload_level_file = lvl
                                        self.upload_level_name = lvl.replace(".json","").replace("_", " ")
                                        self.upload_difficulty = 0
                                        self.upload_input_focus = "name"
                                        self.upload_demon_selector = False
                                elif ed_btn2.collidepoint(logical_mouse):
                                    self.ignore_mouse_jump = True
                                    self.audio.stop_music(); self.state = "EDITOR"; self.editor = Editor(self.audio, lvl, folder=self.get_custom_levels_dir()); self.audio.play_sfx('button.mp3'); break
                                elif del_btn.collidepoint(logical_mouse):
                                    path_to_rem = os.path.join(self.get_custom_levels_dir(), lvl)
                                    if os.path.exists(path_to_rem): os.remove(path_to_rem)
                                    self.load_levels_list(self.get_custom_levels_dir())
                                    self.selected_level_idx = max(0, self.selected_level_idx - 1); break
                                    
                        elif getattr(self, 'online_tab', '') == "users":
                            search_box = pygame.Rect(config.BASE_W//2 - 200, 150, 400, 40)
                            if search_box.collidepoint(logical_mouse):
                                self.users_search_active = True
                            else:
                                self.users_search_active = False
                                
                            if getattr(self, 'online_users', []):
                                for i, u in enumerate(self.online_users):
                                    y = 210 + i * 45
                                    btn = pygame.Rect(config.BASE_W//2 + 200, y, 100, 30)
                                    if btn.collidepoint(logical_mouse):
                                        self.profile_back_state = "ONLINE_HUB"
                                        self.state = "PROFILE"
                                        self.load_profile(u.get('username'))
                                        self.audio.play_sfx('button.mp3')
                                        break

                elif self.state == "LEVEL_INFO":
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.state = "ONLINE_HUB"; self.audio.play_sfx('button.mp3')
                    if getattr(self, 'active_popup', None) == "moderate":
                        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                            self.active_popup = None; self.audio.play_sfx('button.mp3')
                        if mouse_just_pressed:
                            self.handle_moderate_popup_click(logical_mouse)
                        continue
                    if getattr(self, 'active_popup', None) == "rate":
                        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                            self.active_popup = None; self.audio.play_sfx('button.mp3')
                        if mouse_just_pressed:
                            self.handle_rate_popup_click(logical_mouse)
                        continue
                    
                    if mouse_just_pressed:
                        back_btn = pygame.Rect(config.BASE_W//2 - 100, config.BASE_H - 80, 200, 40)
                        if back_btn.collidepoint(logical_mouse):
                            self.state = "ONLINE_HUB"; self.audio.play_sfx('button.mp3')
                            continue
                        
                        p_btn = pygame.Rect(config.BASE_W//2 - 100, 260, 260, 50)
                        prac_btn = pygame.Rect(config.BASE_W//2 - 100, 320, 200, 50)
                        r_btn = pygame.Rect(config.BASE_W//2 - 100, 380, 200, 50)
                        like_btn = pygame.Rect(config.BASE_W//2 - 100, 440, 95, 40)
                        dislike_btn = pygame.Rect(config.BASE_W//2 + 5, 440, 95, 40)
                        del_btn = pygame.Rect(config.BASE_W//2 - 100, 490, 200, 40)
                        mod_btn = pygame.Rect(config.BASE_W//2 - 100, 540, 200, 40)
                        
                        lvl = getattr(self, 'selected_level_data', {})
                        
                        if p_btn.collidepoint(logical_mouse):
                            if getattr(self, "online_status_msg", "").startswith("Downloading"): continue
                            self.online_status_msg = f"Downloading {lvl.get('title')}..."
                            def cb_play(res):
                                if res.get("success"):
                                    data = res.get("data", {})
                                    lvl_obj = Level()
                                    lvl_obj.load_from_json(data.get("data", "{}"))
                                    lvl_obj.filename = data.get("title", "Online Level")
                                    lvl_obj.folder = "online"
                                    lvl_obj.online_version_id = data.get("published_version_id")
                                    self.online_status_msg = ""
                                    self.play_level(None, None, is_practice=False, reset_attempts=True, play_start_sfx=True, online_level=lvl_obj)
                                else:
                                    self.online_status_msg = f"Error: {res.get('error', 'Unknown Error')}"
                            self.network.get_level_data(lvl.get("level_id"), cb_play)
                        elif prac_btn.collidepoint(logical_mouse):
                            if getattr(self, "online_status_msg", "").startswith("Downloading"): continue
                            self.online_status_msg = f"Downloading {lvl.get('title')}..."
                            def cb_prac(res):
                                if res.get("success"):
                                    data = res.get("data", {})
                                    lvl_obj = Level()
                                    lvl_obj.load_from_json(data.get("data", "{}"))
                                    lvl_obj.filename = data.get("title", "Online Level")
                                    lvl_obj.folder = "online"
                                    lvl_obj.online_version_id = data.get("published_version_id")
                                    self.online_status_msg = ""
                                    self.play_level(None, None, is_practice=True, reset_attempts=True, play_start_sfx=True, online_level=lvl_obj)
                                else:
                                    self.online_status_msg = f"Error: {res.get('error', 'Unknown Error')}"
                                    self.audio.stop_music(); self.audio.play_sfx('button.mp3')
                            self.network.get_level_data(lvl.get("level_id"), cb_prac)
                        elif r_btn.collidepoint(logical_mouse):
                            if not lvl.get('has_rated', False):
                                self.active_popup = "rate"
                                self.popup_version_id = lvl.get('published_version_id')
                        elif like_btn.collidepoint(logical_mouse) and lvl.get('has_reacted') is None:
                            def cb_like(res):
                                if res.get("success"): self.selected_level_data['has_reacted'] = 'like'; self.selected_level_data['likes'] += 1
                            self.network.like_level(lvl.get('level_id'), True, cb_like)
                        elif dislike_btn.collidepoint(logical_mouse) and lvl.get('has_reacted') is None:
                            def cb_dislike(res):
                                if res.get("success"): self.selected_level_data['has_reacted'] = 'dislike'; self.selected_level_data['dislikes'] += 1
                            self.network.like_level(lvl.get('level_id'), False, cb_dislike)
                            
                        is_mod_or_admin = getattr(self, 'my_profile_data', {}).get('is_admin') or getattr(self, 'my_profile_data', {}).get('is_moderator')
                        if mod_btn.collidepoint(logical_mouse) and is_mod_or_admin:
                            self.active_popup = "moderate"
                            self.popup_version_id = lvl.get('published_version_id')
                            self.popup_level_id = lvl.get('level_id')
                            
                        is_creator = lvl.get('creator_name') == self.network.username
                        if (is_creator or getattr(self, 'my_profile_data', {}).get('is_admin')) and del_btn.collidepoint(logical_mouse):
                            def cb_del(res):
                                if res.get("success"): self.state = "ONLINE_HUB"; self.load_online_hub()
                            self.network.delete_level(lvl.get('level_id'), cb_del)
                    
                elif self.state == "PROFILE":
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        if getattr(self, 'editing_icons', False):
                            self.editing_icons = False
                            prof = {
                                "icon_cube": config.P_CUBE_IDX,
                                "icon_ship": config.P_SHIP_IDX,
                                "icon_ball": config.P_BALL_IDX,
                                "icon_wave": config.P_WAVE_IDX,
                                "color1": f"{config.P_COLOR[0]},{config.P_COLOR[1]},{config.P_COLOR[2]}",
                                "color2": f"{config.P_COLOR2[0]},{config.P_COLOR2[1]},{config.P_COLOR2[2]}"
                            }
                            self.network.update_icons(prof, lambda r: None)
                        else:
                            self.state = getattr(self, 'profile_back_state', "MENU")
                            if self.state == "ONLINE_HUB":
                                self.online_tab = "users"
                            self.audio.play_sfx('button.mp3')
                            
                    elif mouse_just_pressed:
                        if getattr(self, 'profile_data', None) and self.profile_data.get("username") == self.network.username and not getattr(self, 'editing_icons', False):
                            avatar_rect = pygame.Rect(config.BASE_W//2 - 40, 100, 80, 80)
                            if avatar_rect.collidepoint(logical_mouse):
                                self.editing_icons = True
                                
                        if getattr(self, 'editing_icons', False):
                            icon_changed = False
                            if pygame.Rect(config.BASE_W//2 - 150, 200, 50, 50).collidepoint(logical_mouse): config.P_CUBE_IDX = (config.P_CUBE_IDX + 1) % 5; icon_changed = True
                            if pygame.Rect(config.BASE_W//2 - 50, 200, 50, 50).collidepoint(logical_mouse): config.P_SHIP_IDX = (config.P_SHIP_IDX + 1) % 5; icon_changed = True
                            if pygame.Rect(config.BASE_W//2 + 50, 200, 50, 50).collidepoint(logical_mouse): config.P_BALL_IDX = (config.P_BALL_IDX + 1) % 5; icon_changed = True
                            if pygame.Rect(config.BASE_W//2 + 150, 200, 50, 50).collidepoint(logical_mouse): config.P_WAVE_IDX = (config.P_WAVE_IDX + 1) % 5; icon_changed = True
                            for i, color in enumerate(config.PLAYER_COLORS):
                                row, col = i // 8, i % 8
                                c1_rect = pygame.Rect(config.BASE_W//2 - 400 + col*48, 620 + row*48, 40, 40)
                                c2_rect = pygame.Rect(config.BASE_W//2 + 50 + col*48, 620 + row*48, 40, 40)
                                if c1_rect.collidepoint(logical_mouse): config.P_COLOR = color; icon_changed = True
                                if c2_rect.collidepoint(logical_mouse): config.P_COLOR2 = color; icon_changed = True
                            if icon_changed:
                                prof = {
                                    "icon_cube": config.P_CUBE_IDX, "icon_ship": config.P_SHIP_IDX,
                                    "icon_ball": config.P_BALL_IDX, "icon_wave": config.P_WAVE_IDX,
                                    "color1": f"{config.P_COLOR[0]},{config.P_COLOR[1]},{config.P_COLOR[2]}",
                                    "color2": f"{config.P_COLOR2[0]},{config.P_COLOR2[1]},{config.P_COLOR2[2]}"
                                }
                                self.network.update_icons(prof, lambda r: None)
                                
                        if not getattr(self, 'editing_icons', False) and getattr(self, 'profile_data', None):
                            if self.profile_data.get('username') == self.network.username:
                                switch_btn = pygame.Rect(config.BASE_W//2 - 100, 450, 200, 40)
                                del_btn = pygame.Rect(config.BASE_W//2 - 100, 500, 200, 40)
                                if switch_btn.collidepoint(logical_mouse):
                                    self.active_popup = "switch_account"
                                    self.audio.play_sfx('button.mp3')
                                elif del_btn.collidepoint(logical_mouse):
                                    self.active_popup = "delete_account_confirm"
                                    self.audio.play_sfx('button.mp3')
                            else:
                                is_admin = getattr(self, 'my_profile_data', {}).get('is_admin')
                                if is_admin:
                                    b_btn = pygame.Rect(config.BASE_W//2 - 100, 500, 200, 40)
                                    if b_btn.collidepoint(logical_mouse):
                                        self.network._make_request("POST", f"/admin/users/{self.profile_data.get('username')}/ban", None, lambda r: setattr(self, 'state', 'ONLINE_HUB') or self.load_online_hub())
                                        self.audio.play_sfx('button.mp3')
                                        self.audio.play_sfx('button.mp3')

                elif self.state == "SETTINGS":
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.state = "MENU"; self.audio.play_sfx('button.mp3')
                    elif mouse_just_pressed:
                        k_btn = pygame.Rect(config.BASE_W//2 - 150, config.BASE_H//4 + 220, 300, 35)
                        if k_btn.collidepoint(logical_mouse):
                            self.state = "KEYBINDS"; self.audio.play_sfx('button.mp3')
                            
                        m_y = config.BASE_H//4 + 60
                        if pygame.Rect(config.BASE_W//2 + 50, m_y - 5, 30, 30).collidepoint(logical_mouse):
                            self.audio.music_vol = max(0.0, round(self.audio.music_vol - 0.05, 2)); self.audio.update_volumes(); self.audio.play_sfx('button.mp3')
                        elif pygame.Rect(config.BASE_W//2 + 160, m_y - 5, 30, 30).collidepoint(logical_mouse):
                            self.audio.music_vol = min(1.0, round(self.audio.music_vol + 0.05, 2)); self.audio.update_volumes(); self.audio.play_sfx('button.mp3')
                            
                        s_y = config.BASE_H//4 + 130
                        if pygame.Rect(config.BASE_W//2 + 50, s_y - 5, 30, 30).collidepoint(logical_mouse):
                            self.audio.sfx_vol = max(0.0, round(self.audio.sfx_vol - 0.05, 2)); self.audio.update_volumes(); self.audio.play_sfx('button.mp3')
                        elif pygame.Rect(config.BASE_W//2 + 160, s_y - 5, 30, 30).collidepoint(logical_mouse):
                            self.audio.sfx_vol = min(1.0, round(self.audio.sfx_vol + 0.05, 2)); self.audio.update_volumes(); self.audio.play_sfx('button.mp3')

                elif self.state == "KEYBINDS":
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.state = "SETTINGS"; self.audio.play_sfx('button.mp3')
                        
                elif self.state in ("MAIN_LEVELS", "CUSTOM_LEVELS"):
                    is_main = (self.state == "MAIN_LEVELS")
                    folder = "levels/official" if is_main else self.get_custom_levels_dir()
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE: self.state = "MENU"
                        elif event.key == pygame.K_UP and getattr(self, 'level_files', []):
                            self.selected_level_idx = (self.selected_level_idx - 1) % len(self.level_files); self.audio.play_sfx('button.mp3')
                        elif event.key == pygame.K_DOWN and getattr(self, 'level_files', []):
                            self.selected_level_idx = (self.selected_level_idx + 1) % len(self.level_files); self.audio.play_sfx('button.mp3')
                        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) and getattr(self, 'level_files', []):
                            self.is_practice_mode = False
                            self.play_level(self.level_files[self.selected_level_idx], folder, play_start_sfx=True)
                    elif mouse_just_pressed and getattr(self, 'level_files', []):
                        for i, lvl in enumerate(self.level_files):
                            if i == getattr(self, 'selected_level_idx', 0):
                                play_btn = pygame.Rect(config.BASE_W//2 + 100, 255 + i * 50, 80, 30)
                                prac_btn = pygame.Rect(config.BASE_W//2 + 190, 255 + i * 50, 100, 30)
                                if play_btn.collidepoint(logical_mouse):
                                    self.is_practice_mode = False
                                    self.play_level(self.level_files[i], folder, play_start_sfx=True)
                                elif prac_btn.collidepoint(logical_mouse):
                                    self.is_practice_mode = True
                                    self.play_level(self.level_files[i], folder, is_practice=True, play_start_sfx=True)
                            txt_rect = pygame.Rect(config.BASE_W//2 - 280, 260 + i * 50 - 10, 300, 40)
                            if txt_rect.collidepoint(logical_mouse):
                                self.selected_level_idx = i
                                self.audio.play_sfx('button.mp3')
                            
                elif self.state == "PLAY":
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        if getattr(self.player, 'won', False):
                            self.state = "MAIN_LEVELS" if "official" in getattr(self.current_level, 'folder', '') else "ONLINE_HUB"
                            if self.state == "ONLINE_HUB":
                                self.load_levels_list(self.get_custom_levels_dir())
                            else:
                                self.load_levels_list("levels/official")
                            self.audio.stop_music(); self.audio.play_menu_music()
                        else:
                            self.is_paused = not getattr(self, 'is_paused', False)
                            if self.is_paused: self.audio.pause_music()
                            else: self.audio.unpause_music()
                    elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                        if not getattr(self, 'is_paused', False):
                            self.attempts += 1
                            if getattr(self, 'is_practice_mode', False) and getattr(self, 'checkpoints', []):
                                cp = self.checkpoints[-1]
                                self.player.reset(start_x=cp['x'], start_y=cp['y'], start_mode=cp['mode'])
                                self.player.rotation = cp['rot']
                                self.player.gravity_dir = cp['grav']
                                self.player.vel_y = cp.get('vel_y', 0.0)
                                self.current_level.speed = cp.get('speed', getattr(config, 'SCROLL_SPEED', 6))
                                if hasattr(self, 'camera_y'): delattr(self, 'camera_y')
                                self.death_timer = 0
                                self.player.dead = False
                                self.player.death_sound_played = False
                            else:
                                folder = getattr(self.current_level, 'folder', self.get_custom_levels_dir())
                                self.play_level(getattr(self.current_level, 'filename', "unknown.json"), folder, is_practice=getattr(self, 'is_practice_mode', False), reset_attempts=False)
                                
                elif self.state == "EDITOR":
                    if hasattr(self, 'editor') and self.editor:
                        self.editor.handle_event(event, logical_mouse)
                        if self.editor.ready_to_exit: 
                            self.state = "ONLINE_HUB"; self.online_tab = "create"; self.load_levels_list(self.get_custom_levels_dir()); self.audio.stop_music(); self.audio.play_menu_music()

            # --- RENDER CYCLE ---
            self.screen.fill(config.BLACK)

            if self.state == "MENU":
                self.audio.play_menu_music()
                title = self.title_font.render("POLYGON RUSH", True, config.CYAN)
                self.screen.blit(title, (S(config.BASE_W//2) - title.get_width()//2, S(config.BASE_H//4)))
                
                btn_w, btn_h = 400, 50
                btn_start_y = config.BASE_H // 4 + 80
                
                b_play = pygame.Rect(config.BASE_W//2 - btn_w//2, btn_start_y + 0 * 70, btn_w, btn_h)
                b_online = pygame.Rect(config.BASE_W//2 - btn_w//2, btn_start_y + 1 * 70, btn_w, btn_h)
                b_prof = pygame.Rect(config.BASE_W//2 - btn_w//2, btn_start_y + 2 * 70, btn_w//2 - 10, btn_h)
                b_log = pygame.Rect(config.BASE_W//2 + 10, btn_start_y + 2 * 70, btn_w//2 - 10, btn_h)
                b_set = pygame.Rect(config.BASE_W//2 - btn_w//2, btn_start_y + 3 * 70, btn_w, btn_h)
                b_exit = pygame.Rect(config.BASE_W//2 - btn_w//2, btn_start_y + 4 * 70, btn_w//2 - 10, btn_h)
                b_update = pygame.Rect(config.BASE_W//2 + 10, btn_start_y + 4 * 70, btn_w//2 - 10, btn_h)

                buttons_to_draw = [
                    (b_play, "Play", True),
                    (b_online, "Online", True),
                    (b_prof, "Profile", bool(self.network.token)),
                    (b_log, "Logout" if self.network.token else "Login", True),
                    (b_set, "Settings", True),
                    (b_exit, "Exit", True),
                    (b_update, "Update", True)
                ]
                
                if getattr(self, "update_msg", ""):
                    um = self.font.render(self.update_msg, True, config.YELLOW)
                    self.screen.blit(um, (S(config.BASE_W//2) - um.get_width()//2, S(b_update.bottom + 5)))

                for rect, text, enabled in buttons_to_draw:
                    s_rect = pygame.Rect(S(rect.x), S(rect.y), S(rect.w), S(rect.h))
                    hover = s_rect.collidepoint((logical_mouse[0]*config.get_scale(), logical_mouse[1]*config.get_scale()))
                    pygame.draw.rect(self.screen, (50, 50, 70) if (hover and enabled) else (30, 30, 40), s_rect, 0, S(10))
                    
                    if not enabled:
                        pygame.draw.rect(self.screen, (60, 60, 60), s_rect, max(1, S(2)), S(10))
                        t_surf = self.font.render(text, True, config.DARK_GRAY)
                    else:
                        pygame.draw.rect(self.screen, config.CYAN if hover else config.WHITE, s_rect, max(1, S(2)), S(10))
                        t_surf = self.font.render(text, True, config.WHITE)
                        
                    self.screen.blit(t_surf, (s_rect.centerx - t_surf.get_width()//2, s_rect.centery - t_surf.get_height()//2))
                    
                exit_msg = self.font.render("Press ESC to Exit Desktop Game", True, config.GRAY)
                self.screen.blit(exit_msg, (S(config.BASE_W//2) - exit_msg.get_width()//2, S(config.BASE_H - 40)))
                
                if getattr(self, 'active_popup', None) == "exit_confirm":
                    s = pygame.Surface((config.RENDER_W, config.RENDER_H), pygame.SRCALPHA)
                    s.fill((0, 0, 0, 180))
                    self.screen.blit(s, (0,0))
                    p_rect = pygame.Rect(S(config.BASE_W//2 - 150), S(config.BASE_H//2 - 80), S(300), S(160))
                    pygame.draw.rect(self.screen, (30, 30, 40), p_rect, 0, S(10))
                    pygame.draw.rect(self.screen, config.RED, p_rect, max(1, S(2)), S(10))
                    t = self.title_font.render("Exit Game?", True, config.WHITE)
                    self.screen.blit(t, (p_rect.centerx - t.get_width()//2, p_rect.y + S(20)))
                    
                    y_btn = pygame.Rect(S(config.BASE_W//2 - 100), S(config.BASE_H//2 + 20), S(80), S(35))
                    n_btn = pygame.Rect(S(config.BASE_W//2 + 20), S(config.BASE_H//2 + 20), S(80), S(35))
                    pygame.draw.rect(self.screen, config.RED, y_btn, 0, S(5))
                    pygame.draw.rect(self.screen, config.GRAY, n_btn, 0, S(5))
                    
                    yt = self.font.render("Yes", True, config.WHITE)
                    nt = self.font.render("No", True, config.BLACK)
                    self.screen.blit(yt, (y_btn.centerx - yt.get_width()//2, y_btn.centery - yt.get_height()//2))
                    self.screen.blit(nt, (n_btn.centerx - nt.get_width()//2, n_btn.centery - nt.get_height()//2))

            elif self.state == "LOGIN":
                title = self.title_font.render("LOGIN / REGISTER", True, config.CYAN)
                self.screen.blit(title, (S(config.BASE_W//2) - title.get_width()//2, S(config.BASE_H//4)))
                
                self.login_username_input.draw(self.screen)
                self.login_password_input.draw(self.screen)
                
                login_btn = pygame.Rect(S(config.BASE_W//2 - 150), S(config.BASE_H//2 + 60), S(140), S(40))
                reg_btn = pygame.Rect(S(config.BASE_W//2 + 10), S(config.BASE_H//2 + 60), S(140), S(40))
                
                pygame.draw.rect(self.screen, (30, 30, 40), login_btn, 0, S(5))
                pygame.draw.rect(self.screen, config.CYAN, login_btn, max(1, S(2)), S(5))
                lt = self.font.render("Login", True, config.WHITE)
                self.screen.blit(lt, (login_btn.centerx - lt.get_width()//2, login_btn.centery - lt.get_height()//2))
                
                pygame.draw.rect(self.screen, (30, 30, 40), reg_btn, 0, S(5))
                pygame.draw.rect(self.screen, config.CYAN, reg_btn, max(1, S(2)), S(5))
                rt = self.font.render("Register", True, config.WHITE)
                self.screen.blit(rt, (reg_btn.centerx - rt.get_width()//2, reg_btn.centery - rt.get_height()//2))
                
                if getattr(self, 'online_status_msg', None):
                    msg = self.font.render(self.online_status_msg, True, config.YELLOW)
                    self.screen.blit(msg, (S(config.BASE_W//2) - msg.get_width()//2, S(config.BASE_H//2 + 120)))
                    
                self.screen.blit(self.font.render("Press ESC to Return", True, config.GRAY), (S(config.BASE_W//2 - 80), S(config.BASE_H - 60)))

            elif self.state == "PROFILE":
                if getattr(self, 'editing_icons', False):
                    title = self.title_font.render("PLAYER CUSTOMIZATION", True, config.CYAN)
                    self.screen.blit(title, (S(config.BASE_W//2) - title.get_width()//2, S(30)))
                    self.screen.blit(self.font.render("Click a dummy to change icon. Click a color to set.", True, config.WHITE), (S(config.BASE_W//2 - 200), S(100)))
                    self.draw_dummy_player(self.screen, "cube", config.P_CUBE_IDX, config.P_COLOR, config.BASE_W//2 - 150, 200, 50)
                    self.draw_dummy_player(self.screen, "ship", config.P_SHIP_IDX, config.P_COLOR, config.BASE_W//2 - 50, 200, 50)
                    self.draw_dummy_player(self.screen, "ball", config.P_BALL_IDX, config.P_COLOR, config.BASE_W//2 + 50, 200, 50)
                    self.draw_dummy_player(self.screen, "wave", config.P_WAVE_IDX, config.P_COLOR, config.BASE_W//2 + 150, 200, 50)
                    
                    for i, color in enumerate(config.PLAYER_COLORS):
                        row, col = i // 8, i % 8
                        c1_rect = pygame.Rect(S(config.BASE_W//2 - 400 + col*48), S(620 + row*48), S(40), S(40))
                        pygame.draw.rect(self.screen, color, c1_rect)
                        c2_rect = pygame.Rect(S(config.BASE_W//2 + 50 + col*48), S(620 + row*48), S(40), S(40))
                        pygame.draw.rect(self.screen, color, c2_rect)
                        
                    self.screen.blit(self.font.render("Press ESC to Save & Return", True, config.GRAY), (S(config.BASE_W//2 - 100), S(config.BASE_H - 60)))
                else:
                    title = self.title_font.render("USER PROFILE", True, config.CYAN)
                    self.screen.blit(title, (S(config.BASE_W//2) - title.get_width()//2, S(config.BASE_H//4)))
                    if getattr(self, 'profile_data', None):
                        u_t = self.font.render(f"User: {self.profile_data.get('username','')}", True, config.WHITE)
                        s_t = self.font.render(f"Stars: {self.profile_data.get('stars',0)}", True, config.YELLOW)
                        c_t = self.font.render(f"Creator Points: {self.profile_data.get('creator_points',0)}", True, config.GREEN)
                        self.screen.blit(u_t, (S(config.BASE_W//2) - u_t.get_width()//2, S(config.BASE_H//4 + 80)))
                        self.screen.blit(s_t, (S(config.BASE_W//2) - s_t.get_width()//2, S(config.BASE_H//4 + 120)))
                        self.screen.blit(c_t, (S(config.BASE_W//2) - c_t.get_width()//2, S(config.BASE_H//4 + 160)))
                        
                        if self.profile_data.get('username') == self.network.username:
                            pygame.draw.rect(self.screen, (40, 40, 50), pygame.Rect(S(config.BASE_W//2 - 40), S(100), S(80), S(80)))
                            self.draw_dummy_player(self.screen, "cube", config.P_CUBE_IDX, config.P_COLOR, config.BASE_W//2 - 20, 120, 40)
                            self.screen.blit(self.font.render("Click Avatar to Customize", True, config.GRAY), (S(config.BASE_W//2) - self.font.size("Click Avatar to Customize")[0]//2, S(200)))
                            
                            switch_btn = pygame.Rect(S(config.BASE_W//2 - 100), S(450), S(200), S(40))
                            pygame.draw.rect(self.screen, config.BLUE, switch_btn, 0, S(5))
                            st = self.font.render("SWITCH ACCOUNT", True, config.WHITE)
                            self.screen.blit(st, (switch_btn.centerx - st.get_width()//2, switch_btn.centery - st.get_height()//2))

                            del_btn = pygame.Rect(S(config.BASE_W//2 - 100), S(500), S(200), S(40))
                            pygame.draw.rect(self.screen, config.RED, del_btn, 0, S(5))
                            dt = self.font.render("DELETE ACCOUNT", True, config.WHITE)
                            self.screen.blit(dt, (del_btn.centerx - dt.get_width()//2, del_btn.centery - dt.get_height()//2))
                        else:
                            is_admin = getattr(self, 'my_profile_data', {}).get('is_admin')
                            if is_admin:
                                b_btn = pygame.Rect(S(config.BASE_W//2 - 100), S(500), S(200), S(40))
                                pygame.draw.rect(self.screen, config.ORANGE, b_btn, 0, S(5))
                                bt = self.font.render("BAN USER", True, config.WHITE)
                                self.screen.blit(bt, (b_btn.centerx - bt.get_width()//2, b_btn.centery - bt.get_height()//2))
                    else:
                        self.screen.blit(self.font.render(getattr(self, 'profile_msg', ""), True, config.GRAY), (S(config.BASE_W//2 - 100), S(config.BASE_H//2)))
                    self.screen.blit(self.font.render("Press ESC to Return", True, config.GRAY), (S(config.BASE_W//2 - 80), S(config.BASE_H - 60)))
                    
            elif self.state == "LEVEL_INFO":
                lvl = getattr(self, 'selected_level_data', {})
                title = self.title_font.render(lvl.get('title', 'Unknown Level'), True, config.CYAN)
                self.screen.blit(title, (S(config.BASE_W//2) - title.get_width()//2, S(40)))
                
                c_txt = self.font.render(f"By: {lvl.get('creator_name', 'Unknown')}", True, config.GRAY)
                self.screen.blit(c_txt, (S(config.BASE_W//2) - c_txt.get_width()//2, S(90)))
                
                stars = lvl.get('stars', 0)
                comm_rating = lvl.get('community_rating', 0)
                display_diff = stars
                if stars == 0 and comm_rating > 0:
                    if comm_rating >= 6: display_diff = config.DIFF_INSANE
                    else: display_diff = comm_rating
                
                draw_difficulty_face(self.screen, config.BASE_W//2 - 20, 130, 40, display_diff)
                
                if stars > 0:
                    st = self.font.render(f"{stars}*", True, config.YELLOW)
                    self.screen.blit(st, (S(config.BASE_W//2) - st.get_width()//2, S(180)))
                
                lk_t = self.font.render(f"Likes: {lvl.get('likes', 0)}   Dislikes: {lvl.get('dislikes', 0)}", True, config.WHITE)
                self.screen.blit(lk_t, (S(config.BASE_W//2) - lk_t.get_width()//2, S(210)))
                
                p_btn = pygame.Rect(S(config.BASE_W//2 - 100), S(260), S(200), S(50))
                pygame.draw.rect(self.screen, config.GREEN, p_btn, 0, S(10))
                pt = self.title_font.render("PLAY", True, config.BLACK)
                self.screen.blit(pt, (p_btn.centerx - pt.get_width()//2, p_btn.centery - pt.get_height()//2))
                
                prac_btn = pygame.Rect(S(config.BASE_W//2 - 100), S(320), S(200), S(50))
                pygame.draw.rect(self.screen, config.CYAN, prac_btn, 0, S(10))
                pr_t = self.font.render("PRACTICE", True, config.BLACK)
                self.screen.blit(pr_t, (prac_btn.centerx - pr_t.get_width()//2, prac_btn.centery - pr_t.get_height()//2))

                r_btn = pygame.Rect(S(config.BASE_W//2 - 100), S(380), S(200), S(50))
                has_rated = lvl.get('has_rated', False)
                pygame.draw.rect(self.screen, (100, 100, 100) if has_rated else config.ORANGE, r_btn, 0, S(10))
                rt = self.font.render("RATED" if has_rated else "RATE LEVEL", True, config.WHITE)
                self.screen.blit(rt, (r_btn.centerx - rt.get_width()//2, r_btn.centery - rt.get_height()//2))
                
                has_reacted = lvl.get('has_reacted')
                like_color = config.GREEN if has_reacted == 'like' else (40, 60, 40) if has_reacted == 'dislike' else config.GREEN
                dislike_color = config.RED if has_reacted == 'dislike' else (60, 40, 40) if has_reacted == 'like' else config.RED
                
                like_btn = pygame.Rect(S(config.BASE_W//2 - 100), S(440), S(95), S(40))
                pygame.draw.rect(self.screen, like_color, like_btn, 0, S(5))
                if has_reacted is None: pygame.draw.rect(self.screen, config.WHITE, like_btn, max(1, S(2)), S(5))
                lt = self.font.render("LIKED" if has_reacted == 'like' else "LIKE", True, config.BLACK if has_reacted == 'like' or has_reacted is None else config.GRAY)
                self.screen.blit(lt, (like_btn.centerx - lt.get_width()//2, like_btn.centery - lt.get_height()//2))
                
                dislike_btn = pygame.Rect(S(config.BASE_W//2 + 5), S(440), S(95), S(40))
                pygame.draw.rect(self.screen, dislike_color, dislike_btn, 0, S(5))
                if has_reacted is None: pygame.draw.rect(self.screen, config.WHITE, dislike_btn, max(1, S(2)), S(5))
                dt = self.font.render("DISLIKED" if has_reacted == 'dislike' else "DISLIKE", True, config.BLACK if has_reacted == 'dislike' or has_reacted is None else config.GRAY)
                self.screen.blit(dt, (dislike_btn.centerx - dt.get_width()//2, dislike_btn.centery - dt.get_height()//2))
                
                is_creator = lvl.get('creator_name') == getattr(self.network, 'username', '')
                is_admin = getattr(self, 'my_profile_data', {}).get('is_admin')
                is_mod = getattr(self, 'my_profile_data', {}).get('is_moderator')
                
                if is_creator or is_admin:
                    del_btn = pygame.Rect(S(config.BASE_W//2 - 100), S(490), S(200), S(40))
                    pygame.draw.rect(self.screen, config.RED, del_btn, 0, S(5))
                    dt = self.font.render("DELETE LEVEL", True, config.WHITE)
                    self.screen.blit(dt, (del_btn.centerx - dt.get_width()//2, del_btn.centery - dt.get_height()//2))
                    
                if is_admin or is_mod:
                    mod_btn = pygame.Rect(S(config.BASE_W//2 - 100), S(540), S(200), S(40))
                    pygame.draw.rect(self.screen, config.PURPLE, mod_btn, 0, S(5))
                    mt = self.font.render("MODERATE", True, config.WHITE)
                    self.screen.blit(mt, (mod_btn.centerx - mt.get_width()//2, mod_btn.centery - mt.get_height()//2))

                back_btn = pygame.Rect(S(config.BASE_W//2 - 100), S(config.BASE_H - 80), S(200), S(40))
                bt = self.font.render("Press ESC to Return", True, config.GRAY)
                self.screen.blit(bt, (back_btn.centerx - bt.get_width()//2, back_btn.centery - bt.get_height()//2))
                
                if getattr(self, 'online_status_msg', None):
                    msg = self.font.render(self.online_status_msg, True, config.GREEN)
                    self.screen.blit(msg, (S(config.BASE_W//2) - msg.get_width()//2, S(150)))

            elif self.state == "ONLINE_HUB":
                title = self.title_font.render("ONLINE HUB", True, config.CYAN)
                self.screen.blit(title, (S(config.BASE_W//2) - title.get_width()//2, S(20)))
                
                tabs = ["levels", "create", "users"] if self.network.token else ["create"]
                for i, t in enumerate(tabs):
                    if len(tabs) == 1:
                        btn = pygame.Rect(S(config.BASE_W//2 - 90), S(80), S(180), S(40))
                    else:
                        btn = pygame.Rect(S(config.BASE_W//2 - 300 + i * 200), S(80), S(180), S(40))
                    pygame.draw.rect(self.screen, config.DARK_GRAY if getattr(self, 'online_tab', '') == t else config.GRAY, btn)
                    txt = self.font.render(t.upper(), True, config.WHITE)
                    self.screen.blit(txt, (btn.centerx - txt.get_width()//2, btn.centery - txt.get_height()//2))
                    
                if getattr(self, 'online_tab', '') == "levels":
                    if getattr(self, 'online_levels', []):
                        filtered_levels = getattr(self, 'online_levels', [])
                        s_txt = getattr(self, 'levels_search_text', '').lower()
                        if s_txt:
                            filtered_levels = [l for l in filtered_levels if s_txt in l.get('title','').lower() or s_txt in l.get('level_id','').lower()]
                        
                        search_box = pygame.Rect(S(config.BASE_W//2 - 200), S(150), S(400), S(40))
                        pygame.draw.rect(self.screen, (20,20,20), search_box, 0, S(5))
                        pygame.draw.rect(self.screen, config.CYAN if getattr(self, 'levels_search_active', False) else config.GRAY, search_box, max(1, S(2)), S(5))
                        tt = self.font.render(getattr(self, 'levels_search_text', "") + ("|" if getattr(self, 'levels_search_active', False) and (pygame.time.get_ticks() // 500) % 2 == 0 else ""), True, config.WHITE)
                        self.screen.blit(tt, (search_box.x + S(10), search_box.centery - tt.get_height()//2))

                        for i, lvl in enumerate(filtered_levels):
                            y = 210 + i * 40
                            pygame.draw.rect(self.screen, (40, 40, 50), pygame.Rect(S(config.BASE_W//2 - 320), S(y-5), S(640), S(35)))
                            stars = lvl.get('stars', 0)
                            comm_rating = lvl.get('community_rating', 0)
                            display_diff = stars
                            if stars == 0 and comm_rating > 0:
                                if comm_rating >= 6: display_diff = config.DIFF_INSANE
                                else: display_diff = comm_rating
                                
                            draw_difficulty_face(self.screen, config.BASE_W//2 - 300, y - 5, 35, display_diff)
                            
                            if stars > 0:
                                st = self.font.render(f"{stars}*", True, config.YELLOW)
                                self.screen.blit(st, (S(config.BASE_W//2 - 300) - st.get_width()//2, S(y + 15)))
                            
                            name_t = self.font.render(f"{lvl.get('title', 'Unknown')} (ID: {lvl.get('id', '???')})", True, config.WHITE)
                            self.screen.blit(name_t, (S(config.BASE_W//2 - 260), S(y)))
                            
                            # Likes / Dislikes label
                            lk_t = self.font.render(f"Likes: {lvl.get('likes', 0)}  Dislikes: {lvl.get('dislikes', 0)}", True, config.GRAY)
                            self.screen.blit(lk_t, (S(config.BASE_W//2 - 260), S(y + 18)))
                    else:
                        self.screen.blit(self.font.render("No levels found or loading...", True, config.GRAY), (S(config.BASE_W//2 - 100), S(200)))
                        
                elif getattr(self, 'online_tab', '') == "create":
                    search_box = pygame.Rect(S(config.BASE_W//2 - 200), S(150), S(400), S(40))
                    pygame.draw.rect(self.screen, (20,20,20), search_box, 0, S(5))
                    pygame.draw.rect(self.screen, config.CYAN if getattr(self, 'create_search_active', False) else config.GRAY, search_box, max(1, S(2)), S(5))
                    tt = self.font.render(getattr(self, 'create_search_text', "") + ("|" if getattr(self, 'create_search_active', False) and (pygame.time.get_ticks() // 500) % 2 == 0 else ""), True, config.WHITE)
                    self.screen.blit(tt, (search_box.x + S(10), search_box.centery - tt.get_height()//2))

                    ed_btn = pygame.Rect(S(config.BASE_W//2 - 300), S(210), S(150), S(40))
                    pygame.draw.rect(self.screen, config.CYAN, ed_btn, 0, S(10))
                    et = self.font.render("New Level", True, config.BLACK)
                    self.screen.blit(et, (ed_btn.centerx - et.get_width()//2, ed_btn.centery - et.get_height()//2))
                    
                    mt = self.font.render("My Drafts", True, config.YELLOW)
                    self.screen.blit(mt, (S(config.BASE_W//2 - 300), S(265)))
                    
                    c_txt = getattr(self, 'create_search_text', '').lower()
                    c_levels = [l for l in getattr(self, 'level_files', []) if not c_txt or c_txt in l.replace('.json','').replace('_', ' ').lower()]
                    for i, lvl in enumerate(c_levels):
                        txt = self.font.render(lvl.replace('.json','').replace('_', ' '), True, config.WHITE)
                        self.screen.blit(txt, (S(config.BASE_W//2 - 250), S(315 + i * 50)))
                        
                        play_btn = pygame.Rect(S(config.BASE_W//2 - 20), S(310 + i * 50), S(60), S(30))
                        pygame.draw.rect(self.screen, config.GREEN, play_btn, 0, S(5))
                        
                        prac_btn = pygame.Rect(S(config.BASE_W//2 + 45), S(310 + i * 50), S(80), S(30))
                        pygame.draw.rect(self.screen, config.CYAN, prac_btn, 0, S(5))

                        ed_btn2 = pygame.Rect(S(config.BASE_W//2 + 130), S(310 + i * 50), S(60), S(30))
                        pygame.draw.rect(self.screen, config.ORANGE, ed_btn2, 0, S(5))
                        
                        up_btn = pygame.Rect(S(config.BASE_W//2 + 195), S(310 + i * 50), S(75), S(30))
                        
                        verified = False
                        try:
                            l_obj = Level()
                            l_obj.load(lvl, self.get_custom_levels_dir())
                            verified = l_obj.verified
                        except: pass
                        
                        if verified:
                            pygame.draw.rect(self.screen, config.BLUE, up_btn, 0, S(5))
                            ut = self.font.render("UPLOAD", True, config.WHITE)
                            vt = self.font.render("[ Level Verified ]", True, config.GREEN)
                        else:
                            pygame.draw.rect(self.screen, (50, 50, 70), up_btn, 0, S(5))
                            ut = self.font.render("UPLOAD", True, config.GRAY)
                            vt = self.font.render("[ Level Unverified ]", True, config.RED)
                        
                        self.screen.blit(vt, (S(config.BASE_W//2 + 150), S(295 + i * 50)))
                        
                        del_btn = pygame.Rect(S(config.BASE_W//2 + 275), S(310 + i * 50), S(70), S(30))
                        pygame.draw.rect(self.screen, config.RED, del_btn, 0, S(5))

                        pt = self.font.render("PLAY", True, config.BLACK)
                        prt = self.font.render("PRACTICE", True, config.BLACK)
                        et = self.font.render("EDIT", True, config.WHITE)
                        dt = self.font.render("DELETE", True, config.WHITE)
                        self.screen.blit(pt, (play_btn.centerx - pt.get_width()//2, play_btn.centery - pt.get_height()//2))
                        self.screen.blit(prt, (prac_btn.centerx - prt.get_width()//2, prac_btn.centery - prt.get_height()//2))
                        self.screen.blit(ut, (up_btn.centerx - ut.get_width()//2, up_btn.centery - ut.get_height()//2))
                        self.screen.blit(et, (ed_btn2.centerx - et.get_width()//2, ed_btn2.centery - et.get_height()//2))
                        self.screen.blit(dt, (del_btn.centerx - dt.get_width()//2, del_btn.centery - dt.get_height()//2))
                        
                    if getattr(self, 'online_status_msg', None):
                        msg = self.font.render(self.online_status_msg, True, config.GREEN)
                        self.screen.blit(msg, (S(config.BASE_W//2 - 100), S(135)))
                        
                elif getattr(self, 'online_tab', '') == "users":
                    st = self.font.render("Search User:", True, config.WHITE)
                    self.screen.blit(st, (S(config.BASE_W//2 - 200), S(120)))
                    s_rect = pygame.Rect(S(config.BASE_W//2 - 200), S(150), S(400), S(40))
                    pygame.draw.rect(self.screen, (20,20,20), s_rect, 0, S(5))
                    pygame.draw.rect(self.screen, config.CYAN if getattr(self, 'users_search_active', False) else config.GRAY, s_rect, max(1, S(2)), S(5))
                    tt = self.font.render(getattr(self, 'users_search_text', "") + ("|" if getattr(self, 'users_search_active', False) and (pygame.time.get_ticks() // 500) % 2 == 0 else ""), True, config.WHITE)
                    self.screen.blit(tt, (s_rect.x + S(10), s_rect.centery - tt.get_height()//2))
                    hint = self.font.render("Press Enter to Search", True, config.GRAY)
                    self.screen.blit(hint, (S(config.BASE_W//2) - hint.get_width()//2, S(200)))
                    
                    if getattr(self, 'online_users', []):
                        for i, u in enumerate(self.online_users):
                            y = 210 + i * 45
                            pygame.draw.rect(self.screen, (40, 40, 50), pygame.Rect(S(config.BASE_W//2 - 320), S(y-5), S(640), S(40)))
                            name_t = self.font.render(f"{u.get('username')}", True, config.WHITE)
                            self.screen.blit(name_t, (S(config.BASE_W//2 - 290), S(y + 2)))
                            
                            st_t = self.font.render(f"{u.get('stars')}*", True, config.YELLOW)
                            self.screen.blit(st_t, (S(config.BASE_W//2 - 100), S(y + 2)))
                            
                            cp_t = self.font.render(f"{u.get('creator_points')} CP", True, config.GREEN)
                            self.screen.blit(cp_t, (S(config.BASE_W//2), S(y + 2)))
                            
                            btn = pygame.Rect(S(config.BASE_W//2 + 200), S(y), S(100), S(30))
                            pygame.draw.rect(self.screen, config.CYAN, btn, 0, S(5))
                            pt = self.font.render("PROFILE", True, config.BLACK)
                            self.screen.blit(pt, (btn.centerx - pt.get_width()//2, btn.centery - pt.get_height()//2))
                    if getattr(self, 'online_status_msg', None):
                        msg = self.font.render(self.online_status_msg, True, config.YELLOW)
                        self.screen.blit(msg, (S(config.BASE_W//2) - msg.get_width()//2, S(150)))

                if getattr(self, 'active_popup', None):
                    self._draw_popup()

                self.screen.blit(self.font.render("Press ESC to Return", True, config.GRAY), (S(config.BASE_W//2 - 80), S(config.BASE_H - 60)))

            elif self.state == "SETTINGS":
                title = self.title_font.render("SETTINGS MENU", True, config.CYAN)
                self.screen.blit(title, (S(config.BASE_W//2) - title.get_width()//2, S(config.BASE_H//4)))
                
                self.draw_volume_setting("Music Volume", self.audio.music_vol, config.BASE_H//4 + 60)
                self.draw_volume_setting("SFX Volume", self.audio.sfx_vol, config.BASE_H//4 + 130)

                k_btn = pygame.Rect(S(config.BASE_W//2 - 150), S(config.BASE_H//4 + 220), S(300), S(35))
                k_hover = pygame.Rect(config.BASE_W//2 - 150, config.BASE_H//4 + 220, 300, 35).collidepoint(logical_mouse)
                pygame.draw.rect(self.screen, config.GRAY if k_hover else config.DARK_GRAY, k_btn)
                pygame.draw.rect(self.screen, config.WHITE, k_btn, max(1, S(2)))
                self.screen.blit(self.font.render("View Editor Keybinds", True, config.WHITE), (k_btn.x + S(60), k_btn.y + S(6)))
                
                self.screen.blit(self.font.render("Press ESC to Return", True, config.GRAY), (S(config.BASE_W//2 - 80), S(config.BASE_H - 100)))

            elif self.state == "KEYBINDS":
                title = self.title_font.render("EDITOR CONTROLS", True, config.CYAN)
                self.screen.blit(title, (S(config.BASE_W//2) - title.get_width()//2, S(80)))

                binds_col1 = [
                    ("General", config.YELLOW),
                    ("1/2/3", "Switch Modes"),
                    ("Arrows", "Move Camera"),
                    ("ENTER", "Test Level"),
                    ("F5", "Quick Save"),
                    ("CTRL+C", "Copy Selection"),
                    ("CTRL+Z", "Undo Action"),
                    ("R", "Restart / Checkpoint"),
                    ("ESC", "Exit/Cancel"),
                    ("", ""),
                    ("Build Mode", config.YELLOW),
                    ("TAB", "Change Category"),
                    ("Q/E", "Rotate Item"),
                    ("F", "Flip Item"),
                    ("Left Click", "Place Item")
                ]
                binds_col2 = [
                    ("Edit Mode", config.YELLOW),
                    ("Left Click", "Select"),
                    ("Shift+Click", "Multi-select"),
                    ("Drag Box", "Multi-select"),
                    ("W/A/S/D", "Move Item"),
                    ("Shift+WASD", "Fine Move"),
                    ("Q/E", "Rotate Selected"),
                    ("F", "Flip Selected"),
                    ("DELETE", "Erase Items"),
                    ("", ""),
                    ("Other", config.YELLOW),
                    ("N", "Toggle Noclip"),
                    ("Z/X", "Place/Rem Checkpoint")
                ]
                for c_idx, col_data in enumerate([binds_col1, binds_col2]):
                    for i, item in enumerate(col_data):
                        y = 160 + i * 30
                        x = config.BASE_W//2 - 350 + (c_idx * 400)
                        if item[1] == config.YELLOW:
                            self.screen.blit(self.font.render(item[0], True, config.YELLOW), (S(x), S(y)))
                        elif item[0]:
                            self.screen.blit(self.font.render(f"[{item[0]}]:", True, config.CYAN), (S(x), S(y)))
                            self.screen.blit(self.font.render(item[1], True, config.WHITE), (S(x + 120), S(y)))

                self.screen.blit(self.font.render("Press ESC to Return", True, config.GRAY), (S(config.BASE_W//2 - 80), S(config.BASE_H - 60)))

            elif self.state == "MAIN_LEVELS":
                is_main = True
                folder = "levels/official"
                
                title = self.title_font.render("OFFICIAL LEVELS" if is_main else "CUSTOM LEVELS", True, config.CYAN)
                self.screen.blit(title, (S(config.BASE_W//2) - title.get_width()//2, S(50)))
                
                if not self.level_files:
                    msg = self.font.render("No levels found.", True, config.RED)
                    self.screen.blit(msg, (S(config.BASE_W//2) - msg.get_width()//2, S(220)))
                else:
                    for i, lvl in enumerate(self.level_files):
                        txt = self.font.render(lvl.replace('.json','').replace('_', ' '), True, config.YELLOW if i == getattr(self, 'selected_level_idx', 0) else config.WHITE)
                        self.screen.blit(txt, (S(config.BASE_W//2 - 230), S(260 + i * 50)))
                        
                        try:
                            lvl_obj = Level()
                            lvl_obj.load(lvl, folder)
                            draw_difficulty_face(self.screen, config.BASE_W//2 - 280, 260 + i * 50 - 5, 35, lvl_obj.difficulty)
                        except: pass
                        
                        if i == getattr(self, 'selected_level_idx', 0):
                            play_btn = pygame.Rect(S(config.BASE_W//2 + 100), S(255 + i * 50), S(80), S(30))
                            pygame.draw.rect(self.screen, config.GREEN, play_btn, 0, S(5))
                            pt = self.font.render("PLAY", True, config.BLACK)
                            self.screen.blit(pt, (play_btn.centerx - pt.get_width()//2, play_btn.centery - pt.get_height()//2))
                            
                            prac_btn = pygame.Rect(S(config.BASE_W//2 + 190), S(255 + i * 50), S(100), S(30))
                            pygame.draw.rect(self.screen, config.CYAN, prac_btn, 0, S(5))
                            prt = self.font.render("PRACTICE", True, config.BLACK)
                            self.screen.blit(prt, (prac_btn.centerx - prt.get_width()//2, prac_btn.centery - prt.get_height()//2))

                back_btn = pygame.Rect(S(config.BASE_W//2 - 100), S(config.BASE_H - 80), S(200), S(40))
                bt = self.font.render("Press ESC to Return", True, config.GRAY)
                self.screen.blit(bt, (back_btn.centerx - bt.get_width()//2, back_btn.centery - bt.get_height()//2))
                
                if not is_main:
                    new_btn = pygame.Rect(S(config.BASE_W//2 + 300), S(50), S(100), S(40))
                    pygame.draw.rect(self.screen, config.BLUE, new_btn, 0, S(5))
                    nt = self.font.render("NEW", True, config.WHITE)
                    self.screen.blit(nt, (new_btn.centerx - nt.get_width()//2, new_btn.centery - nt.get_height()//2))

            elif self.state == "PLAY":
                play_zoom = 2.0 
                
                is_paused = getattr(self, 'is_paused', False)
                
                if not self.player.dead and not self.player.won and not is_paused:
                    for obj in self.current_level.objects:
                        t = getattr(obj, 'type', -1)
                        if t in (config.OBJ_SPEED_05X, config.OBJ_SPEED_1X, config.OBJ_SPEED_2X, config.OBJ_SPEED_3X, config.OBJ_SPEED_4X):
                            if not getattr(obj, 'activated', False) and self.player.x >= obj.x:
                                obj.activated = True
                                bs = getattr(config, 'SCROLL_SPEED', 6)
                                if t == config.OBJ_SPEED_05X: self.current_level.speed = bs * 0.7
                                elif t == config.OBJ_SPEED_1X: self.current_level.speed = bs * 1.0
                                elif t == config.OBJ_SPEED_2X: self.current_level.speed = bs * 1.3
                                elif t == config.OBJ_SPEED_3X: self.current_level.speed = bs * 1.6
                                elif t == config.OBJ_SPEED_4X: self.current_level.speed = bs * 2.0
                    self.player.update(keys, self.current_level.objects, self.current_level.speed, ignore_mouse=getattr(self, 'ignore_mouse_jump', False))
                    
                    progress = max(0, min(100, int((self.player.x - 200) / max(1, self.current_level.end_x - 200) * 100)))
                    if self.is_practice_mode:
                        if progress > self.current_level.practice_best:
                            self.current_level.practice_best = progress
                            self.current_level.save(self.current_level.filename, self.current_level.folder)
                    else:
                        if progress > self.current_level.normal_best:
                            self.current_level.normal_best = progress
                            self.current_level.save(self.current_level.filename, self.current_level.folder)
                    
                    if self.player.x > self.current_level.end_x:
                        self.player.won = True; self.audio.stop_music(); self.audio.play_sfx('win.mp3')
                        if getattr(self.current_level, 'folder', '') == 'online' and hasattr(self.current_level, 'online_version_id'):
                            self.network.complete_level_version(self.current_level.online_version_id, lambda r: None)
                        elif not self.is_practice_mode:
                            if getattr(self.current_level, 'folder', '') != 'levels/official':
                                self.current_level.verified = True
                                self.current_level.save(self.current_level.filename, self.current_level.folder)
                
                if self.player.dead and not is_paused:
                    if not hasattr(self, 'death_timer'):
                        self.death_timer = 0
                    self.death_timer += 1
                    
                    if not self.player.death_sound_played:
                        if not self.is_practice_mode:
                            self.audio.stop_music()
                        self.audio.play_sfx('death.mp3')
                        self.player.death_sound_played = True

                    respawn_time = 30 if self.is_practice_mode else 60
                    if self.death_timer >= respawn_time:
                        if self.is_practice_mode:
                            self.attempts += 1
                            if self.checkpoints:
                                c = self.checkpoints[-1]
                                self.player.reset(start_x=c['x'], start_y=c['y'], start_mode=c['mode'])
                                self.player.rotation = c['rot']
                                self.player.gravity_dir = c['grav']
                                self.player.vel_y = c.get('vel_y', 0.0)
                                self.current_level.speed = c.get('speed', getattr(config, 'SCROLL_SPEED', 6))
                            else:
                                self.player.reset(start_x=self.current_level.get_spawn_x(), start_y=self.current_level.get_spawn_y(), start_mode=self.current_level.start_gamemode)
                                self.current_level.speed = getattr(config, 'SCROLL_SPEED', 6)
                            for obj in self.current_level.objects:
                                obj.activated = getattr(obj, 'x', 0) <= self.player.x
                            if hasattr(self, 'camera_y'): delattr(self, 'camera_y')
                            self.death_timer = 0
                        else:
                            self.attempts += 1
                            self.death_timer = 0
                            folder = getattr(self.current_level, 'folder', 'levels/custom')
                            online_lvl = getattr(self, 'current_level', None) if folder == 'online' else None
                            self.play_level(getattr(self.current_level, 'filename', "unknown.json"), folder, is_practice=False, reset_attempts=False, online_level=online_lvl)
                
                if self.is_practice_mode and not is_paused:
                    if not getattr(self, 'z_held', False) and keys[pygame.K_z] and not self.player.dead:
                        self.checkpoints.append({
                            'x': self.player.x, 'y': self.player.y, 'mode': self.player.mode,
                            'rot': self.player.rotation, 'grav': self.player.gravity_dir,
                            'vel_y': getattr(self.player, 'vel_y', 0.0),
                            'speed': getattr(self.current_level, 'speed', getattr(config, 'SCROLL_SPEED', 6))
                        })
                    if not getattr(self, 'x_held', False) and keys[pygame.K_x]:
                        if self.checkpoints: self.checkpoints.pop()
                    self.z_held = keys[pygame.K_z]
                    self.x_held = keys[pygame.K_x]

                camera_x = self.player.x - 200
                view_h = config.BASE_H / play_zoom
                
                if self.player.mode in ('ship', 'ball', 'wave'):
                    corridor_center = (config.GROUND_Y + config.CEILING_Y) // 2
                    target_camera_y = corridor_center - view_h // 2
                else:
                    base_cam_y = config.GROUND_Y - view_h + (150 / play_zoom)
                    target_camera_y = min(base_cam_y, self.player.y - (view_h * 0.33))
                
                if not hasattr(self, 'camera_y'): self.camera_y = target_camera_y
                
                if self.player.mode not in ('ship', 'ball', 'wave'):
                    self.camera_y += (target_camera_y - self.camera_y) * 0.04
                else:
                    self.camera_y += (target_camera_y - self.camera_y) * 0.04

                tgt_bg = self.get_active_bg_color(self.player.x)
                tgt_gnd = self.get_active_ground_color(self.player.x)
                
                for i in range(3):
                    self.fade_bg_color[i] += (tgt_bg[i] - self.fade_bg_color[i]) * 0.1
                    self.fade_gnd_color[i] += (tgt_gnd[i] - self.fade_gnd_color[i]) * 0.1
                    
                current_bg = tuple(int(c) for c in self.fade_bg_color)
                current_gnd = tuple(int(c) for c in self.fade_gnd_color)
                
                draw_world_background(self.screen, camera_x, self.camera_y, current_bg, self.current_level.bg_design)
                for obj in self.current_level.objects:
                    if obj.type not in (config.OBJ_SPAWN, config.OBJ_COLOR_TRIGGER, config.OBJ_GROUND_COLOR_TRIGGER, config.OBJ_END_TRIGGER):
                        obj.draw(self.screen, camera_x, self.camera_y, play_zoom)
                
                if getattr(self.current_level, 'noclip', False):
                    nc_txt = self.title_font.render("NOCLIP ENABLED", True, (255, 0, 0))
                    nc_txt.set_alpha(100)
                    self.screen.blit(nc_txt, (S(config.BASE_W//2) - nc_txt.get_width()//2, S(100)))
                    
                if getattr(self, 'is_practice_mode', False):
                    for cp in self.checkpoints:
                        cx = int((cp['x'] - camera_x) * play_zoom * config.get_scale())
                        cy = int((cp['y'] - self.camera_y) * play_zoom * config.get_scale())
                        s = int(10 * play_zoom * config.get_scale())
                        pts = [(cx, cy-s), (cx+s, cy), (cx, cy+s), (cx-s, cy)]
                        pygame.draw.polygon(self.screen, config.GREEN, pts)
                        pygame.draw.polygon(self.screen, config.WHITE, pts, max(1, int(1*play_zoom*config.get_scale())))
                        
                draw_world_ground(self.screen, camera_x, self.camera_y, play_zoom, current_gnd, self.current_level.ground_design, self.player.mode)
                self.player.draw(self.screen, camera_x, self.camera_y, play_zoom)
                
                live_prog = max(0, min(100, int((self.player.x - 200) / max(1, self.current_level.end_x - 200) * 100)))
                bar_w = S(300)
                bar_rect = pygame.Rect(S(config.BASE_W//2) - bar_w//2, S(15), bar_w, S(15))
                pygame.draw.rect(self.screen, config.DARK_GRAY, bar_rect, 0, S(10))
                pygame.draw.rect(self.screen, config.WHITE, bar_rect, max(1, S(2)), S(10))
                if live_prog > 0:
                    fill_w = int(bar_w * (live_prog / 100.0))
                    pygame.draw.rect(self.screen, config.GREEN if not self.is_practice_mode else config.YELLOW, pygame.Rect(bar_rect.x, bar_rect.y, fill_w, bar_rect.h), 0, S(10))
                prog_txt = self.font.render(f"{live_prog}%", True, config.WHITE)
                self.screen.blit(prog_txt, (bar_rect.right + S(10), bar_rect.centery - prog_txt.get_height()//2))

                att_txt = self.font.render(f"Attempt {getattr(self, 'attempts', 1)}", True, config.WHITE)
                self.screen.blit(att_txt, (S(config.BASE_W//2) - att_txt.get_width()//2, bar_rect.bottom + S(10)))

                if self.player.won:
                    s_mask = pygame.Surface((config.RENDER_W, config.RENDER_H), pygame.SRCALPHA)
                    s_mask.fill((0,0,0, 150))
                    self.screen.blit(s_mask, (0,0))
                    
                    p_box = pygame.Rect(S(config.BASE_W//2 - 250), S(config.BASE_H//2 - 150), S(500), S(300))
                    pygame.draw.rect(self.screen, config.DARK_GRAY, p_box, 0, S(10))
                    pygame.draw.rect(self.screen, config.WHITE, p_box, max(1, S(2)), S(10))
                    
                    t = self.title_font.render("LEVEL COMPLETE!", True, config.GREEN if not self.is_practice_mode else config.YELLOW)
                    self.screen.blit(t, (S(config.BASE_W//2) - t.get_width()//2, p_box.y + S(20)))
                    
                    att = self.font.render(f"Attempts: {getattr(self, 'attempts', 1)}", True, config.WHITE)
                    self.screen.blit(att, (S(config.BASE_W//2) - att.get_width()//2, p_box.y + S(80)))
                    
                    btn_y = p_box.y + S(140)
                    if not self.is_practice_mode:
                        exit_btn = pygame.Rect(S(config.BASE_W//2 - 160), btn_y, S(150), S(50))
                        restart_btn = pygame.Rect(S(config.BASE_W//2 + 10), btn_y, S(150), S(50))
                        
                        pygame.draw.rect(self.screen, config.RED, exit_btn, 0, S(10))
                        ex_txt = self.font.render("Exit", True, config.WHITE)
                        self.screen.blit(ex_txt, (exit_btn.centerx - ex_txt.get_width()//2, exit_btn.centery - ex_txt.get_height()//2))
                        
                        pygame.draw.rect(self.screen, config.GREEN, restart_btn, 0, S(10))
                        re_txt = self.font.render("Restart", True, config.WHITE)
                        self.screen.blit(re_txt, (restart_btn.centerx - re_txt.get_width()//2, restart_btn.centery - re_txt.get_height()//2))
                        
                        if mouse_just_pressed:
                            if exit_btn.collidepoint(logical_mouse):
                                self.player.won = False
                                self.ignore_mouse_jump = True
                                if getattr(self.current_level, 'folder', '') == 'levels/official':
                                    self.state = "MAIN_LEVELS"
                                elif getattr(self.current_level, 'folder', '') == self.get_custom_levels_dir():
                                    self.state = "ONLINE_HUB"; self.online_tab = "create"
                                else:
                                    self.state = "ONLINE_HUB"; self.online_tab = "levels"
                            elif restart_btn.collidepoint(logical_mouse):
                                self.player.won = False
                                self.ignore_mouse_jump = True
                                folder = getattr(self.current_level, 'folder', 'levels/custom')
                                online_lvl = getattr(self, 'current_level', None) if folder == 'online' else None
                                self.play_level(getattr(self.current_level, 'filename', "unknown.json"), folder, is_practice=False, online_level=online_lvl)
                    else:
                        exit_btn = pygame.Rect(S(config.BASE_W//2 - 200), btn_y, S(120), S(50))
                        ckpt_btn = pygame.Rect(S(config.BASE_W//2 - 60), btn_y, S(120), S(50))
                        re_btn = pygame.Rect(S(config.BASE_W//2 + 80), btn_y, S(120), S(50))
                        
                        pygame.draw.rect(self.screen, config.RED, exit_btn, 0, S(10))
                        ex_txt = self.font.render("Exit", True, config.WHITE)
                        self.screen.blit(ex_txt, (exit_btn.centerx - ex_txt.get_width()//2, exit_btn.centery - ex_txt.get_height()//2))
                        
                        pygame.draw.rect(self.screen, config.ORANGE, ckpt_btn, 0, S(10))
                        ck_txt = self.font.render("Checkpoint", True, config.WHITE)
                        self.screen.blit(ck_txt, (ckpt_btn.centerx - ck_txt.get_width()//2, ckpt_btn.centery - ck_txt.get_height()//2))
                        
                        pygame.draw.rect(self.screen, config.GREEN, re_btn, 0, S(10))
                        re_txt = self.font.render("Normal Mode", True, config.WHITE)
                        self.screen.blit(re_txt, (re_btn.centerx - re_txt.get_width()//2, re_btn.centery - re_txt.get_height()//2))
                        
                        if mouse_just_pressed:
                            if exit_btn.collidepoint(logical_mouse):
                                self.player.won = False
                                self.ignore_mouse_jump = True
                                if getattr(self.current_level, 'folder', '') == 'levels/official':
                                    self.state = "MAIN_LEVELS"
                                elif getattr(self.current_level, 'folder', '') == self.get_custom_levels_dir():
                                    self.state = "ONLINE_HUB"; self.online_tab = "create"
                                else:
                                    self.state = "ONLINE_HUB"; self.online_tab = "levels"
                            elif ckpt_btn.collidepoint(logical_mouse):
                                self.player.won = False
                                self.ignore_mouse_jump = True
                                if self.checkpoints:
                                    c = self.checkpoints[-1]
                                    self.player.reset(start_x=c['x'], start_y=c['y'], start_mode=c['mode'])
                                    self.player.rotation = c['rot']
                                    self.player.gravity_dir = c['grav']
                                    self.player.vel_y = c.get('vel_y', 0.0)
                                    self.current_level.speed = c.get('speed', getattr(config, 'SCROLL_SPEED', 6))
                                    import random
                                    self.audio.play_music(random.choice(["practice1.mp3", "practice2.mp3"]))
                                else:
                                    folder = getattr(self.current_level, 'folder', 'levels/custom')
                                    online_lvl = getattr(self, 'current_level', None) if folder == 'online' else None
                                    self.play_level(getattr(self.current_level, 'filename', "unknown.json"), folder, is_practice=True, reset_attempts=False, online_level=online_lvl)
                            elif re_btn.collidepoint(logical_mouse):
                                self.player.won = False
                                self.ignore_mouse_jump = True
                                folder = getattr(self.current_level, 'folder', 'levels/custom')
                                online_lvl = getattr(self, 'current_level', None) if folder == 'online' else None
                                self.play_level(getattr(self.current_level, 'filename', "unknown.json"), folder, is_practice=False, online_level=online_lvl)
                    
                if is_paused:
                    s_mask = pygame.Surface((config.RENDER_W, config.RENDER_H), pygame.SRCALPHA)
                    s_mask.fill((0,0,0, 150))
                    self.screen.blit(s_mask, (0,0))
                    
                    p_box = pygame.Rect(S(config.BASE_W//2 - 300), S(config.BASE_H//2 - 200), S(600), S(450))
                    pygame.draw.rect(self.screen, config.DARK_GRAY, p_box, 0, S(10))
                    pygame.draw.rect(self.screen, config.WHITE, p_box, max(1, S(2)), S(10))
                    
                    t = self.title_font.render("PAUSED", True, config.CYAN)
                    self.screen.blit(t, (S(config.BASE_W//2) - t.get_width()//2, p_box.y + S(20)))
                    
                    lvl_t = self.font.render(f"{self.current_level.filename.replace('.json','')} ({config.DIFF_NAMES[self.current_level.difficulty]})", True, config.YELLOW)
                    self.screen.blit(lvl_t, (S(config.BASE_W//2) - lvl_t.get_width()//2, p_box.y + S(60)))
                    
                    def draw_prog_bar(y_pos, label, value, color):
                        surface = self.screen
                        lbl = self.font.render(label, True, config.WHITE)
                        surface.blit(lbl, (S(config.BASE_W//2 - 230), S(y_pos)))
                        bar = pygame.Rect(S(config.BASE_W//2 - 50), S(y_pos), S(250), S(15))
                        pygame.draw.rect(surface, config.DARK_GRAY, bar, 0, S(5))
                        pygame.draw.rect(surface, config.WHITE, bar, max(1, S(1)), S(5))
                        if value > 0:
                            pygame.draw.rect(surface, color, pygame.Rect(bar.x, bar.y, int(S(250) * (value / 100.0)), bar.h), 0, S(5))
                        vt = self.font.render(f"{value}%", True, config.WHITE)
                        surface.blit(vt, (bar.right + S(10), bar.centery - vt.get_height()//2))

                    draw_prog_bar(p_box.y/config.get_scale() + 110, "Normal Mode Best:", self.current_level.normal_best, config.GREEN)
                    draw_prog_bar(p_box.y/config.get_scale() + 150, "Practice Mode Best:", self.current_level.practice_best, config.YELLOW)
                    
                    m_l, m_r = self.draw_volume_setting("Music", self.audio.music_vol, (p_box.y/config.get_scale()) + 210)
                    s_l, s_r = self.draw_volume_setting("SFX", self.audio.sfx_vol, (p_box.y/config.get_scale()) + 260)
                    if mouse_just_pressed:
                        if m_l.collidepoint(logical_mouse): self.audio.music_vol = max(0.0, round(self.audio.music_vol - 0.05, 2)); self.audio.update_volumes()
                        elif m_r.collidepoint(logical_mouse): self.audio.music_vol = min(1.0, round(self.audio.music_vol + 0.05, 2)); self.audio.update_volumes()
                        elif s_l.collidepoint(logical_mouse): self.audio.sfx_vol = max(0.0, self.audio.sfx_vol - 0.05); self.audio.update_volumes(); self.audio.play_sfx('button.mp3')
                        elif s_r.collidepoint(logical_mouse): self.audio.sfx_vol = min(1.0, self.audio.sfx_vol + 0.05); self.audio.update_volumes(); self.audio.play_sfx('button.mp3')
                    
                    btn_y = (p_box.bottom / config.get_scale()) - 100
                    resume_btn = pygame.Rect(config.BASE_W//2 - 237, btn_y, 100, 40)
                    restart_btn = pygame.Rect(config.BASE_W//2 - 122, btn_y, 100, 40)
                    prac_btn = pygame.Rect(config.BASE_W//2 - 7, btn_y, 130, 40)
                    exit_btn = pygame.Rect(config.BASE_W//2 + 138, btn_y, 100, 40)
                    
                    def draw_pbtn(rect, text, color):
                        pygame.draw.rect(self.screen, color, pygame.Rect(S(rect.x), S(rect.y), S(rect.w), S(rect.h)), 0, S(5))
                        rt = self.font.render(text, True, config.BLACK)
                        self.screen.blit(rt, (S(rect.centerx) - rt.get_width()//2, S(rect.centery) - rt.get_height()//2))
                        
                    draw_pbtn(resume_btn, "RESUME", config.GREEN)
                    draw_pbtn(restart_btn, "RESTART", config.CYAN)
                    draw_pbtn(prac_btn, "NORMAL" if self.is_practice_mode else "PRACTICE", config.YELLOW)
                    draw_pbtn(exit_btn, "EXIT", config.RED)
                    
                    if mouse_just_pressed:
                        if resume_btn.collidepoint(logical_mouse):
                            self.is_paused = False
                            self.ignore_mouse_jump = True
                            self.audio.unpause_music()
                            self.player.jump_held = pygame.key.get_pressed()[pygame.K_SPACE] or pygame.mouse.get_pressed()[0] or pygame.key.get_pressed()[pygame.K_UP]
                        elif restart_btn.collidepoint(logical_mouse):
                            self.is_paused = False
                            self.ignore_mouse_jump = True
                            folder = getattr(self.current_level, 'folder', 'levels/custom')
                            online_lvl = getattr(self, 'current_level', None) if folder == 'online' else None
                            self.play_level(getattr(self.current_level, 'filename', "unknown.json"), folder, is_practice=self.is_practice_mode, online_level=online_lvl)
                        elif prac_btn.collidepoint(logical_mouse):
                            self.is_paused = False
                            self.ignore_mouse_jump = True
                            folder = getattr(self.current_level, 'folder', 'levels/custom')
                            online_lvl = getattr(self, 'current_level', None) if folder == 'online' else None
                            self.play_level(getattr(self.current_level, 'filename', "unknown.json"), folder, is_practice=not self.is_practice_mode, online_level=online_lvl)
                        elif exit_btn.collidepoint(logical_mouse):
                            self.is_paused = False
                            self.state = "MAIN_LEVELS" if "official" in getattr(self.current_level, 'folder', '') else "ONLINE_HUB"
                            if self.state == "ONLINE_HUB":
                                if getattr(self.current_level, 'folder', '') == self.get_custom_levels_dir():
                                    self.online_tab = "create"
                                else:
                                    self.online_tab = "levels"
                                self.load_levels_list(self.get_custom_levels_dir())
                            else:
                                self.load_levels_list("levels/official")
                            self.audio.stop_music(); self.audio.play_menu_music()

            elif self.state == "EDITOR":
                self.editor.update(keys, logical_mouse, mouse_click, mouse_just_pressed, scroll_y_dir)
                self.editor.draw(self.screen, self.font, self.title_font)
            
            if getattr(self, 'active_popup', None):
                self._draw_popup()
                
            pygame.display.flip()
            self.clock.tick(config.FPS)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    init_folders()
    try:
        game = Game()
        game.run()
    except Exception as e:
        import traceback
        with open("crash_log.txt", "w") as f:
            f.write(traceback.format_exc())
        raise