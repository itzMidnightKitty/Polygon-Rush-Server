import pygame
import os
import config
from config import S
from level_manager import Level
from player import Player
from game_objects import GameObject, sort_for_draw
from graphics import draw_world_background, draw_world_ground, draw_difficulty_face

class Editor:
    def __init__(self, audio_manager, target_filename=None, folder=None):
        self.audio = audio_manager
        self.ignore_mouse = True
        self.level = Level(filename=target_filename, folder=folder) if folder else (Level(target_filename) if target_filename else Level())
        
        if not self.level.music and self.audio.available_tracks: self.level.music = self.audio.available_tracks[0]

        self.scroll_x = 0
        self.scroll_y = config.GROUND_Y - 480 
        self.zoom = 1.0

        self.mode = "BUILD" 
        self.category_names = list(config.CATEGORIES.keys())
        self.current_cat_idx = 0
        self.current_item_idx = 0
        self.notification_timer = 0
        self.notification_text = ""
        
        self.current_rot = 0
        self.current_flip_x = False
        self.current_color = 8
        self.current_layer = 0
        self.color_picker_active = False

        self.selected_objs = [] 
        self.selection_box_start = None
        self.selection_box_end = None
        self.clipboard = []
        self.clipboard_center = (0, 0)
        
        self.music_idx = 0
        if self.audio.available_tracks and self.level.music in self.audio.available_tracks:
            self.music_idx = self.audio.available_tracks.index(self.level.music)
            
        self.playtesting = False
        self.just_exited_playtest = 0
        self.options_active = False
        self.song_browser_active = False
        self.preview_song = None
        self.music_testing = False
        self.ui_hovered = False
        
        self.can_build = False
        self.dragging_stroke = False
        
        self.unsaved_changes = False
        self.show_confirm_exit = False
        self.ready_to_exit = False
        self.test_player = Player()
        
        self.playtest_trail = []
        self.fade_bg_color = list(config.BG_COLORS[self.level.start_bg_idx])
        self.fade_gnd_color = list(config.BG_COLORS[self.level.start_ground_idx])
        
        self.edit_btns = {
            "UP": pygame.Rect(250, config.BASE_H - 90, 40, 40),
            "DOWN": pygame.Rect(300, config.BASE_H - 90, 40, 40),
            "LEFT": pygame.Rect(350, config.BASE_H - 90, 40, 40),
            "RIGHT": pygame.Rect(400, config.BASE_H - 90, 40, 40),
            "ROT_L": pygame.Rect(250, config.BASE_H - 45, 40, 35),
            "ROT_R": pygame.Rect(300, config.BASE_H - 45, 40, 35),
            "FLIP_X": pygame.Rect(350, config.BASE_H - 45, 40, 35),
            "FLIP_Y": pygame.Rect(400, config.BASE_H - 45, 40, 35),
            "DEL": pygame.Rect(460, config.BASE_H - 70, 50, 40),
            "COPY": pygame.Rect(520, config.BASE_H - 70, 50, 40),
            "PASTE": pygame.Rect(580, config.BASE_H - 70, 55, 40),
            "UNDO": pygame.Rect(config.BASE_W - 150, config.BASE_H - 70, 60, 40),
            "REDO": pygame.Rect(config.BASE_W - 80, config.BASE_H - 70, 60, 40)
        }
        
        self.history = []
        self.redo_stack = []
        self.first_frame = True
        self.hide_ground = False

    def save_state(self):
        self.history.append([o.to_dict() for o in self.level.objects])
        self.redo_stack.clear()
        if len(self.history) > 50:
            self.history.pop(0)

    def undo(self):
        if not self.history: return
        self.redo_stack.append([o.to_dict() for o in self.level.objects])
        last_state = self.history.pop()
        self.level.objects = [GameObject(o['type'], o['x'], o['y'], o.get('rotation',0), o.get('color_idx',0), o.get('flip_x',False), o.get('flip_y',False), layer=o.get('layer',0)) for o in last_state]
        self.selected_objs = []
        self.unsaved_changes = True
        self.show_notification("Undo")

    def redo(self):
        if not self.redo_stack: return
        self.history.append([o.to_dict() for o in self.level.objects])
        next_state = self.redo_stack.pop()
        self.level.objects = [GameObject(o['type'], o['x'], o['y'], o.get('rotation',0), o.get('color_idx',0), o.get('flip_x',False), o.get('flip_y',False), layer=o.get('layer',0)) for o in next_state]
        self.selected_objs = []
        self.unsaved_changes = True
        self.show_notification("Redo")

    def color_swatch_button_rect(self):
        return pygame.Rect(config.BASE_W - 460, config.BASE_H - 95, 55, 34)

    def layer_box_rect(self, i):
        return pygame.Rect(config.BASE_W - 400 + i * 22, config.BASE_H - 55, 20, 20)

    def color_picker_box(self):
        return pygame.Rect(config.BASE_W//2 - 500, 100, 1000, 500)

    def color_picker_swatch_rect(self, idx):
        cols = 20
        col, row = idx % cols, idx // cols
        box = self.color_picker_box()
        return pygame.Rect(box.x + 40 + col * 34, box.y + 70 + row * 34, 28, 28)

    def set_color(self, color_idx):
        if self.mode == "EDIT" and self.selected_objs:
            self.save_state()
            for obj in self.selected_objs: obj.color_idx = color_idx
            self.unsaved_changes = True
        else:
            self.current_color = color_idx

    def set_layer(self, layer):
        if self.mode == "EDIT" and self.selected_objs:
            self.save_state()
            for obj in self.selected_objs: obj.layer = layer
            self.unsaved_changes = True
        else:
            self.current_layer = layer

    def show_notification(self, text):
        self.notification_text = text
        self.notification_timer = 90

    def get_current_bg_color(self, target_x):
        active_color = config.BG_COLORS[self.level.start_bg_idx]
        for obj in self.level.objects:
            if obj.type == config.OBJ_COLOR_TRIGGER and obj.x <= target_x: active_color = config.BG_COLORS[obj.color_idx]
        return active_color

    def get_current_ground_color(self, target_x):
        active_color = config.BG_COLORS[self.level.start_ground_idx]
        for obj in self.level.objects:
            if obj.type == config.OBJ_GROUND_COLOR_TRIGGER and obj.x <= target_x: active_color = config.BG_COLORS[obj.color_idx]
        return active_color

    def get_next_unnamed(self):
        max_idx = 0
        if self.level.folder and os.path.exists(self.level.folder):
            for f in os.listdir(self.level.folder):
                if f.startswith("Unnamed_") and f.endswith(".json"):
                    try:
                        idx = int(f.replace("Unnamed_", "").replace(".json", ""))
                        max_idx = max(max_idx, idx)
                    except: pass
        return f"Unnamed {max_idx + 1}"

    def update(self, keys, logical_mouse, mouse_click, mouse_just_pressed, mouse_scroll_y):
        mouse_click_raw = pygame.mouse.get_pressed()
        
        if getattr(self, 'ignore_mouse', False):
            if not mouse_click_raw[0]:
                self.ignore_mouse = False
            else:
                mouse_click_raw = (False, False, False)
                mouse_click = (False, False, False)
                mouse_just_pressed = False
                
        mouse_click = mouse_click_raw
        
        if self.first_frame:
            self.first_frame = False
            mouse_just_pressed = False
            mouse_click = (False, False, False)
            self.save_state()

        self.ui_hovered = False

        if logical_mouse[1] < 40 or logical_mouse[1] > config.BASE_H - 120: self.ui_hovered = True
        if self.options_active or self.song_browser_active or self.show_confirm_exit or self.color_picker_active: self.ui_hovered = True
        
        if self.just_exited_playtest > 0:
            self.just_exited_playtest -= 1
            self.ui_hovered = True

        if not mouse_click[0]:
            self.can_build = True
            self.dragging_stroke = False
        elif mouse_just_pressed and self.ui_hovered:
            self.can_build = False

        if self.show_confirm_exit:
            if mouse_just_pressed:
                yes_btn = pygame.Rect(config.BASE_W//2 - 120, config.BASE_H//2 + 20, 100, 40)
                no_btn = pygame.Rect(config.BASE_W//2 + 20, config.BASE_H//2 + 20, 100, 40)
                if yes_btn.collidepoint(logical_mouse): self.ready_to_exit = True
                elif no_btn.collidepoint(logical_mouse): self.show_confirm_exit = False
            return
            


        if self.playtesting:
            self.test_player.update(keys, self.level.objects, getattr(self.level, 'speed', getattr(config, 'SCROLL_SPEED', 6)), getattr(self, 'noclip', False))
            self.playtest_trail.append((self.test_player.x + self.test_player.width//2, self.test_player.y + self.test_player.height//2))
            
            has_end_trigger = any(o.type == config.OBJ_END_TRIGGER for o in self.level.objects)
            if self.test_player.dead or keys[pygame.K_ESCAPE] or (has_end_trigger and self.test_player.x > self.level.end_x):
                self.playtesting = False
                self.just_exited_playtest = 15
                self.audio.stop_music()
            return

        if self.options_active:
            if mouse_just_pressed:
                box = pygame.Rect(config.BASE_W//2 - 350, 100, 700, 480)
                if not box.collidepoint(logical_mouse):
                    self.options_active = False; return
                if pygame.Rect(config.BASE_W//2 - 200, 160, 400, 40).collidepoint(logical_mouse):
                    gamemode_cycle = ["cube", "ship", "ball", "wave", "ufo"]
                    idx = gamemode_cycle.index(self.level.start_gamemode) if self.level.start_gamemode in gamemode_cycle else 0
                    self.level.start_gamemode = gamemode_cycle[(idx + 1) % len(gamemode_cycle)]
                    self.unsaved_changes = True
                for i in range(6):
                    if pygame.Rect(config.BASE_W//2 - 270 + i * 90, 250, 70, 70).collidepoint(logical_mouse):
                        self.level.bg_design = i; self.unsaved_changes = True
                if pygame.Rect(config.BASE_W//2 + 280, 265, 40, 40).collidepoint(logical_mouse):
                    self.level.start_bg_idx = (self.level.start_bg_idx + 1) % len(config.BG_COLORS); self.unsaved_changes = True
                for i in range(6):
                    if pygame.Rect(config.BASE_W//2 - 270 + i * 90, 380, 70, 70).collidepoint(logical_mouse):
                        self.level.ground_design = i; self.unsaved_changes = True
                if pygame.Rect(config.BASE_W//2 + 280, 395, 40, 40).collidepoint(logical_mouse):
                    self.level.start_ground_idx = (self.level.start_ground_idx + 1) % len(config.BG_COLORS); self.unsaved_changes = True
                if pygame.Rect(config.BASE_W//2 - 100, 500, 200, 40).collidepoint(logical_mouse):
                    self.options_active = False
            return

        if self.color_picker_active:
            if mouse_just_pressed:
                if not self.color_picker_box().collidepoint(logical_mouse):
                    self.color_picker_active = False; return
                for idx, i in enumerate(config.UI_COLOR_ORDER):
                    if self.color_picker_swatch_rect(idx).collidepoint(logical_mouse):
                        self.set_color(i)
                        self.color_picker_active = False
                        return
            return

        if self.song_browser_active:
            if mouse_just_pressed:
                box = pygame.Rect(config.BASE_W//2 - 300, 100, 600, config.BASE_H - 200)
                if not box.collidepoint(logical_mouse):
                    self.audio.stop_music(); self.preview_song = None; self.song_browser_active = False; return
                for i, song in enumerate(self.audio.available_tracks):
                    play_btn = pygame.Rect(config.BASE_W//2 - 250, 200 + i*40, 40, 30)
                    sel_btn = pygame.Rect(config.BASE_W//2 + 160, 200 + i*40, 90, 30)
                    if play_btn.collidepoint(logical_mouse):
                        if self.preview_song == song:
                            self.audio.stop_music(); self.preview_song = None
                        else:
                            self.audio.play_music(song); self.preview_song = song
                    elif sel_btn.collidepoint(logical_mouse):
                        self.level.music = song; self.unsaved_changes = True; self.audio.stop_music(); self.preview_song = None; self.song_browser_active = False
            return

        if self.music_testing:
            self.scroll_x += getattr(self.level, 'speed', getattr(config, 'SCROLL_SPEED', 6))
            if self.scroll_x + 200 > self.level.end_x:
                self.music_testing = False; self.audio.stop_music()
            return

        if mouse_scroll_y != 0:
            old_zoom = self.zoom
            self.zoom = max(0.3, min(3.0, self.zoom + mouse_scroll_y * 0.1))
            wx = logical_mouse[0] / old_zoom + self.scroll_x
            wy = logical_mouse[1] / old_zoom + self.scroll_y
            self.scroll_x = wx - logical_mouse[0] / self.zoom
            self.scroll_y = wy - logical_mouse[1] / self.zoom

        move_speed = 12 / self.zoom
        if keys[pygame.K_LEFT]: self.scroll_x -= move_speed
        if keys[pygame.K_RIGHT]: self.scroll_x += move_speed
        if keys[pygame.K_UP]: self.scroll_y -= move_speed
        if keys[pygame.K_DOWN]: self.scroll_y += move_speed

        if self.notification_timer > 0: self.notification_timer -= 1

        world_mouse_x = (logical_mouse[0] / self.zoom) + self.scroll_x
        world_mouse_y = (logical_mouse[1] / self.zoom) + self.scroll_y
        grid_x = (world_mouse_x // config.GRID_SIZE) * config.GRID_SIZE
        grid_y = (world_mouse_y // config.GRID_SIZE) * config.GRID_SIZE

        # TOP UI BAR
        if mouse_just_pressed and logical_mouse[1] < 40:
            if 10 < logical_mouse[0] < 310: 
                self.song_browser_active = True; self.options_active = False
            elif 320 < logical_mouse[0] < 470: 
                self.options_active = True; self.song_browser_active = False
            elif config.BASE_W - 220 < logical_mouse[0] < config.BASE_W - 140:
                self.noclip = not getattr(self, 'noclip', False)
            elif config.BASE_W - 350 < logical_mouse[0] < config.BASE_W - 230:
                self.hide_ground = not self.hide_ground
            elif config.BASE_W - 130 < logical_mouse[0] < config.BASE_W - 70:
                if self.unsaved_changes: self.show_confirm_exit = True
                else: self.ready_to_exit = True
            elif config.BASE_W - 60 < logical_mouse[0] < config.BASE_W - 10:
                if not self.level.filename:
                    import random
                    self.level.name = self.get_next_unnamed()
                    self.level.filename = f"{self.level.name.replace(' ', '_')}.json"
                self.level.verified = False
                self.level.save(self.level.filename, self.level.folder)
                self.unsaved_changes = False
                self.show_notification("Level Saved!")
                self.audio.play_sfx('win.mp3')
            return
        # UI INTERCEPTS FOR GLOBAL BUTTONS
        if mouse_just_pressed:
            if self.edit_btns["UNDO"].collidepoint(logical_mouse):
                self.undo(); return
            if self.edit_btns["REDO"].collidepoint(logical_mouse):
                self.redo(); return

        # UI INTERCEPTS FOR SELECTION BUTTONS (EDIT MODE ONLY)
        if self.mode == "EDIT" and self.selected_objs and mouse_just_pressed:
            step = config.GRID_SIZE // 4 if keys[pygame.K_LSHIFT] else config.GRID_SIZE
            for name, rect in self.edit_btns.items():
                if rect.collidepoint(logical_mouse):
                    if name == "DEL":
                        self.save_state()
                        for o in self.selected_objs:
                            if o in self.level.objects: self.level.objects.remove(o)
                        self.selected_objs = []
                        self.unsaved_changes = True
                        return
                    elif name == "COPY":
                        self.clipboard = [o.to_dict() for o in self.selected_objs]
                        cx = sum(o['x'] for o in self.clipboard) / len(self.clipboard)
                        cy = sum(o['y'] for o in self.clipboard) / len(self.clipboard)
                        self.clipboard_center = (cx, cy)
                        self.show_notification(f"Copied {len(self.clipboard)} objects!")
                        return
                    elif name == "PASTE":
                        if hasattr(self, 'clipboard') and self.clipboard:
                            self.save_state()
                            self.unsaved_changes = True
                            new_objs = []
                            wx = (logical_mouse[0] / self.zoom) + self.scroll_x
                            wy = (logical_mouse[1] / self.zoom) + self.scroll_y
                            gx, gy = (wx // config.GRID_SIZE) * config.GRID_SIZE, (wy // config.GRID_SIZE) * config.GRID_SIZE
                            for o_dict in self.clipboard:
                                dx = o_dict['x'] - self.clipboard_center[0]
                                dy = o_dict['y'] - self.clipboard_center[1]
                                nx = gx + round(dx / config.GRID_SIZE) * config.GRID_SIZE
                                ny = gy + round(dy / config.GRID_SIZE) * config.GRID_SIZE
                                if nx < 0: nx = 0
                                new_obj = GameObject(o_dict['type'], nx, ny, o_dict.get('rotation',0), o_dict.get('color_idx',0), o_dict.get('flip_x',False), o_dict.get('flip_y',False), layer=o_dict.get('layer',0))
                                self.level.objects.append(new_obj)
                                new_objs.append(new_obj)
                            self.selected_objs = new_objs
                            self.level.update_end_x()
                            self.show_notification("Pasted!")
                        return
                    
                    self.save_state()
                    self.unsaved_changes = True
                    min_x = min((o.x for o in self.selected_objs), default=0)
                    max_x = max((o.x for o in self.selected_objs), default=0) + config.GRID_SIZE
                    min_y = min((o.y for o in self.selected_objs), default=0)
                    max_y = max((o.y for o in self.selected_objs), default=0) + config.GRID_SIZE
                    for obj in self.selected_objs:
                        if name == "UP": obj.y -= step; obj.base_y = obj.y
                        elif name == "DOWN": obj.y += step; obj.base_y = obj.y
                        elif name == "LEFT": obj.x -= step; obj.base_x = obj.x
                        elif name == "RIGHT": obj.x += step; obj.base_x = obj.x
                        elif name == "ROT_L" and obj.type not in config.NON_ROTATABLE: obj.rotation = (obj.rotation - 90) % 360
                        elif name == "ROT_R" and obj.type not in config.NON_ROTATABLE: obj.rotation = (obj.rotation + 90) % 360
                        elif name == "FLIP_X" and obj.type not in config.NON_ROTATABLE: 
                            obj.flip_x = not obj.flip_x
                            obj.x = min_x + max_x - config.GRID_SIZE - obj.x; obj.base_x = obj.x
                        elif name == "FLIP_Y" and obj.type not in config.NON_ROTATABLE: 
                            obj.flip_y = not obj.flip_y
                            obj.y = min_y + max_y - config.GRID_SIZE - obj.y; obj.base_y = obj.y
                        obj.update_rect()
                    return
            
            if self.color_swatch_button_rect().collidepoint(logical_mouse):
                self.color_picker_active = True
                return
            for i in range(config.MAX_LAYERS):
                if self.layer_box_rect(i).collidepoint(logical_mouse):
                    self.set_layer(i)
                    return

        # LAYER PICKER (DELETE mode, and EDIT mode with nothing selected) -- the
        # EDIT+selection case is already handled above; this covers switching the
        # active layer when there's no selection to also show a color swatch for.
        if (self.mode == "DELETE" or (self.mode == "EDIT" and not self.selected_objs)) and mouse_just_pressed:
            for i in range(config.MAX_LAYERS):
                if self.layer_box_rect(i).collidepoint(logical_mouse):
                    self.set_layer(i)
                    return

        # BOTTOM BAR (Build Mode Selection/Color Panel)
        if self.mode == "BUILD" and logical_mouse[1] > config.BASE_H - 120:
            if mouse_just_pressed:
                cat_name = self.category_names[self.current_cat_idx]
                start_x = 10
                for i, item_id in enumerate(config.CATEGORIES[cat_name]):
                    box_rect = pygame.Rect(start_x + i * 50, config.BASE_H - 70, 40, 40)
                    if box_rect.collidepoint(logical_mouse):
                        self.current_item_idx = i
                        self.show_notification(f"Selected: {config.OBJ_NAMES.get(item_id, 'Item')}")
                        return
                if self.color_swatch_button_rect().collidepoint(logical_mouse):
                    self.color_picker_active = True
                    return
                for i in range(config.MAX_LAYERS):
                    if self.layer_box_rect(i).collidepoint(logical_mouse):
                        self.set_layer(i)
                        return
            return

        # WORLD GRID INTERACTION
        if not self.ui_hovered and self.can_build:
            if self.mode == "BUILD":
                if mouse_click[0] and grid_x >= 0: 
                    cat_name = self.category_names[self.current_cat_idx]
                    obj_type = config.CATEGORIES[cat_name][self.current_item_idx]
                    c_idx = 0 if cat_name == "Gameplay" else self.current_color
                    if grid_x >= 0 and not any(o.x == grid_x and o.y == grid_y and o.type == obj_type for o in self.level.objects):
                        if not self.dragging_stroke: 
                            self.save_state()
                            self.unsaved_changes = True
                            self.dragging_stroke = True
                        new_obj = GameObject(obj_type, grid_x, grid_y, self.current_rot, c_idx, self.current_flip_x, layer=self.current_layer)
                        self.level.objects.append(new_obj)
                        self.selected_objs = [new_obj]
                        self.level.update_end_x()
                    
            elif self.mode == "EDIT":
                if mouse_just_pressed:
                    clicked_objs = [obj for obj in reversed(sort_for_draw(self.level.objects)) if obj.rect.collidepoint(world_mouse_x, world_mouse_y) and obj.layer == self.current_layer]
                    if clicked_objs:
                        if not keys[pygame.K_LSHIFT]:
                            if len(self.selected_objs) == 1 and self.selected_objs[0] in clicked_objs:
                                idx = clicked_objs.index(self.selected_objs[0])
                                next_idx = (idx + 1) % len(clicked_objs)
                                self.selected_objs = [clicked_objs[next_idx]]
                            else:
                                self.selected_objs = [clicked_objs[0]]
                        else:
                            if clicked_objs[0] in self.selected_objs: self.selected_objs.remove(clicked_objs[0])
                            else: self.selected_objs.append(clicked_objs[0])
                        
                        pass
                    else:
                        if not keys[pygame.K_LSHIFT]: self.selected_objs = []
                        self.selection_box_start = (world_mouse_x, world_mouse_y)
                        self.selection_box_end = (world_mouse_x, world_mouse_y)
                elif self.selection_box_start and mouse_click[0]:
                    self.selection_box_end = (world_mouse_x, world_mouse_y)
                elif not mouse_click[0] and self.selection_box_start:
                    x1 = min(self.selection_box_start[0], self.selection_box_end[0])
                    x2 = max(self.selection_box_start[0], self.selection_box_end[0])
                    y1 = min(self.selection_box_start[1], self.selection_box_end[1])
                    y2 = max(self.selection_box_start[1], self.selection_box_end[1])
                    select_rect = pygame.Rect(x1, y1, x2-x1, y2-y1)
                    if select_rect.width > 5 or select_rect.height > 5:
                        new_selection = [obj for obj in self.level.objects if obj.rect.colliderect(select_rect) and obj.layer == self.current_layer]
                        if keys[pygame.K_LSHIFT]:
                            for o in new_selection:
                                if o not in self.selected_objs: self.selected_objs.append(o)
                        else:
                            self.selected_objs = new_selection
                    self.selection_box_start = None
                    self.selection_box_end = None

            elif self.mode == "DELETE":
                if mouse_click[0]:
                    target_objs = [o for o in self.level.objects if o.rect.collidepoint(world_mouse_x, world_mouse_y) and o.layer == self.current_layer]
                    if target_objs:
                        if not self.dragging_stroke: 
                            self.save_state()
                            self.unsaved_changes = True
                            self.dragging_stroke = True
                        for o in target_objs:
                            if o in self.level.objects: self.level.objects.remove(o)
                        self.selected_objs = [o for o in self.selected_objs if o in self.level.objects]

    def handle_event(self, event, logical_mouse):
        if self.show_confirm_exit:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: self.show_confirm_exit = False
            return
            
        if self.options_active or self.song_browser_active or self.color_picker_active:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.options_active = False
                self.song_browser_active = False
                self.color_picker_active = False
                self.audio.stop_music()
            return


        if self.playtesting:
            if event.type == 768 and event.key == 110: # KEYDOWN, K_n
                self.noclip = not getattr(self, 'noclip', False)
            return
        
        if self.music_testing:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_m):
                self.music_testing = False; self.audio.stop_music()
            return

        if event.type == pygame.KEYDOWN:
            mods = pygame.key.get_mods()
            if event.key == pygame.K_1: self.mode = "BUILD"; self.selected_objs = []
            elif event.key == pygame.K_2: self.mode = "EDIT"
            elif event.key == pygame.K_3: self.mode = "DELETE"; self.selected_objs = []
            elif event.key == pygame.K_F5:
                if not self.level.filename:
                    import random
                    self.level.name = self.get_next_unnamed()
                    self.level.filename = f"{self.level.name.replace(' ', '_')}.json"
                self.level.verified = False
                self.level.save(self.level.filename, self.level.folder)
                self.unsaved_changes = False
                self.show_notification("Level Saved!")
                self.audio.play_sfx('win.mp3')

            if self.mode == "BUILD":
                if event.key == pygame.K_TAB:
                    self.current_cat_idx = (self.current_cat_idx + 1) % len(self.category_names); self.current_item_idx = 0
                elif event.key == pygame.K_f:
                    obj_type = config.CATEGORIES[self.category_names[self.current_cat_idx]][self.current_item_idx]
                    if obj_type not in config.NON_ROTATABLE: self.current_flip_x = not self.current_flip_x
                elif event.key in (pygame.K_q, pygame.K_e):
                    obj_type = config.CATEGORIES[self.category_names[self.current_cat_idx]][self.current_item_idx]
                    if obj_type not in config.NON_ROTATABLE:
                        if event.key == pygame.K_q: self.current_rot = (self.current_rot - 90) % 360
                        else: self.current_rot = (self.current_rot + 90) % 360
                elif event.key == pygame.K_LEFTBRACKET:
                    self.current_layer = max(0, self.current_layer - 1)
                elif event.key == pygame.K_RIGHTBRACKET:
                    self.current_layer = min(config.MAX_LAYERS - 1, self.current_layer + 1)

            if self.selected_objs:
                if event.key == pygame.K_f:
                    self.save_state()
                    self.unsaved_changes = True
                    min_x = min((o.x for o in self.selected_objs), default=0)
                    max_x = max((o.x for o in self.selected_objs), default=0) + config.GRID_SIZE
                    for o in self.selected_objs:
                        if o.type not in config.NON_ROTATABLE: 
                            o.flip_x = not o.flip_x
                            o.x = min_x + max_x - config.GRID_SIZE - o.x
                            o.update_rect()
                elif event.key in (pygame.K_q, pygame.K_e):
                    self.save_state()
                    self.unsaved_changes = True
                    for o in self.selected_objs:
                        if o.type not in config.NON_ROTATABLE:
                            if event.key == pygame.K_q: o.rotation = (o.rotation - 90) % 360
                            else: o.rotation = (o.rotation + 90) % 360
                elif event.key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
                    self.save_state()
                    self.unsaved_changes = True
                    delta = -1 if event.key == pygame.K_LEFTBRACKET else 1
                    for o in self.selected_objs:
                        o.layer = max(0, min(config.MAX_LAYERS - 1, o.layer + delta))
                elif event.key == pygame.K_DELETE:
                    self.save_state()
                    for o in self.selected_objs:
                        if o in self.level.objects: self.level.objects.remove(o)
                    self.selected_objs = []
                    self.unsaved_changes = True
                elif event.key == pygame.K_c and mods & pygame.KMOD_CTRL:
                    self.clipboard = [o.to_dict() for o in self.selected_objs]
                    cx = sum(o['x'] for o in self.clipboard) / len(self.clipboard)
                    cy = sum(o['y'] for o in self.clipboard) / len(self.clipboard)
                    self.clipboard_center = (cx, cy)
                    self.show_notification(f"Copied {len(self.clipboard)} objects!")
                else:
                    move_step = config.GRID_SIZE // 4 if mods & pygame.KMOD_SHIFT else config.GRID_SIZE
                    if event.key in (pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d):
                        self.save_state()
                        self.unsaved_changes = True
                        for obj in self.selected_objs:
                            if event.key == pygame.K_w: obj.y -= move_step; obj.base_y = obj.y
                            elif event.key == pygame.K_s: obj.y += move_step; obj.base_y = obj.y
                            elif event.key == pygame.K_a: obj.x -= move_step; obj.base_x = obj.x
                            elif event.key == pygame.K_d: obj.x += move_step; obj.base_x = obj.x
                            obj.update_rect()

            if event.key == pygame.K_v and mods & pygame.KMOD_CTRL:
                if hasattr(self, 'clipboard') and self.clipboard:
                    self.save_state()
                    self.unsaved_changes = True
                    new_objs = []
                    wx = (logical_mouse[0] / self.zoom) + self.scroll_x
                    wy = (logical_mouse[1] / self.zoom) + self.scroll_y
                    gx, gy = (wx // config.GRID_SIZE) * config.GRID_SIZE, (wy // config.GRID_SIZE) * config.GRID_SIZE
                    for o_dict in self.clipboard:
                        dx = o_dict['x'] - self.clipboard_center[0]
                        dy = o_dict['y'] - self.clipboard_center[1]
                        nx = gx + round(dx / config.GRID_SIZE) * config.GRID_SIZE
                        ny = gy + round(dy / config.GRID_SIZE) * config.GRID_SIZE
                        if nx < 0: nx = 0
                        new_obj = GameObject(o_dict['type'], nx, ny, o_dict.get('rotation',0), o_dict.get('color_idx',0), o_dict.get('flip_x',False), o_dict.get('flip_y',False), layer=o_dict.get('layer',0))
                        self.level.objects.append(new_obj)
                        new_objs.append(new_obj)
                    self.selected_objs = new_objs
                    self.level.update_end_x()
                    self.show_notification("Pasted!")
            elif event.key == pygame.K_z and mods & pygame.KMOD_CTRL:
                self.undo()
            elif event.key == pygame.K_y and mods & pygame.KMOD_CTRL:
                self.redo()

            if event.key == pygame.K_m:
                if self.level.music:
                    self.music_testing = True
                    self.scroll_x = max(0, self.level.get_spawn_x() - 200)
                    offset = max(0.0, (self.level.get_spawn_x() - 200) / (getattr(self.level, 'speed', getattr(config, 'SCROLL_SPEED', 6)) * config.FPS))
                    self.audio.play_music(self.level.music, offset=offset)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER): 
                self.playtesting = True
                self.playtest_trail = []
                spawn_x = self.level.get_spawn_x()
                spawn_y = self.level.get_spawn_y()
                self.test_player.reset(start_x=spawn_x, start_y=spawn_y, start_mode=self.level.start_gamemode)
                
                if hasattr(self, 'camera_y'): delattr(self, 'camera_y')
                
                if self.level.music: 
                    offset = max(0.0, (spawn_x - 200) / (getattr(self.level, 'speed', getattr(config, 'SCROLL_SPEED', 6)) * config.FPS))
                    self.audio.play_music(self.level.music, offset=offset)

    def draw_layer_controls(self, surface, font):
        target_objs = self.selected_objs if (self.mode == "EDIT" and self.selected_objs) else None
        surface.blit(font.render("Layer:", True, config.WHITE), (S(config.BASE_W - 460), S(config.BASE_H - 75)))
        if target_objs:
            common_layer = target_objs[0].layer if all(o.layer == target_objs[0].layer for o in target_objs) else None
        else:
            common_layer = self.current_layer
        for i in range(config.MAX_LAYERS):
            r = self.layer_box_rect(i)
            rs = pygame.Rect(S(r.x), S(r.y), S(r.w), S(r.h))
            pygame.draw.rect(surface, config.GREEN if i == common_layer else config.DARK_GRAY, rs)
            pygame.draw.rect(surface, config.WHITE, rs, max(1, S(1)))
            lt = font.render(str(i), True, config.BLACK if i == common_layer else config.WHITE)
            surface.blit(lt, (rs.centerx - lt.get_width()//2, rs.centery - lt.get_height()//2))

    def draw_color_and_layer_controls(self, surface, font):
        target_objs = self.selected_objs if (self.mode == "EDIT" and self.selected_objs) else None

        surface.blit(font.render("Color:", True, config.WHITE), (S(config.BASE_W - 460), S(config.BASE_H - 115)))
        swatch = self.color_swatch_button_rect()
        swatch_s = pygame.Rect(S(swatch.x), S(swatch.y), S(swatch.w), S(swatch.h))
        if target_objs:
            common = target_objs[0].color_idx if all(o.color_idx == target_objs[0].color_idx for o in target_objs) else None
        else:
            common = self.current_color
        pygame.draw.rect(surface, config.BG_COLORS[common] if common is not None else config.GRAY, swatch_s)
        pygame.draw.rect(surface, config.WHITE, swatch_s, max(1, S(2)))
        if common is None:
            mt = font.render("?", True, config.BLACK)
            surface.blit(mt, (swatch_s.centerx - mt.get_width()//2, swatch_s.centery - mt.get_height()//2))

        self.draw_layer_controls(surface, font)

    def draw(self, surface, font, title_font):
        play_zoom = 2.0 
        
        track_x = self.test_player.x if self.playtesting else self.scroll_x + 200
        tgt_bg = self.get_current_bg_color(track_x)
        tgt_gnd = self.get_current_ground_color(track_x)
        
        for i in range(3):
            self.fade_bg_color[i] += (tgt_bg[i] - self.fade_bg_color[i]) * 0.1
            self.fade_gnd_color[i] += (tgt_gnd[i] - self.fade_gnd_color[i]) * 0.1
            
        current_bg = tuple(int(c) for c in self.fade_bg_color)
        current_gnd = tuple(int(c) for c in self.fade_gnd_color)
        
        if self.playtesting:
            test_scroll_x = self.test_player.x - 200
            view_h = config.BASE_H / play_zoom
            
            if self.test_player.mode in ('ship', 'ball', 'wave', 'ufo'):
                corridor_center = (config.GROUND_Y + config.CEILING_Y) // 2
                target_camera_y = corridor_center - view_h // 2
            else:
                base_cam_y = config.GROUND_Y - view_h + (150 / play_zoom)
                threshold_y = config.GROUND_Y - (view_h * 0.66)
                if self.test_player.y < threshold_y:
                    target_camera_y = self.test_player.y - (view_h * 0.33)
                else:
                    target_camera_y = base_cam_y
                
            if not hasattr(self, 'camera_y'): self.camera_y = target_camera_y
            if self.test_player.mode in ('ship', 'ball', 'wave', 'ufo'):
                self.camera_y = target_camera_y
            else:
                self.camera_y += (target_camera_y - self.camera_y) * 0.08
            
            draw_world_background(surface, test_scroll_x, self.camera_y, current_bg, self.level.bg_design)
            for obj in sort_for_draw(self.level.objects): obj.draw(surface, test_scroll_x, self.camera_y, play_zoom)
            if not self.hide_ground:
                draw_world_ground(surface, test_scroll_x, self.camera_y, play_zoom, current_gnd, self.level.ground_design, self.test_player.mode)
            self.test_player.draw(surface, test_scroll_x, self.camera_y, play_zoom, noclip=getattr(self, 'noclip', False))
            
            if getattr(self, 'noclip', False):
                nc_txt = title_font.render("NOCLIP ENABLED", True, (255, 0, 0))
                nc_txt.set_alpha(100)
                surface.blit(nc_txt, (S(config.BASE_W//2 - nc_txt.get_width()//2), S(100)))
            
            overlay = font.render(f"PLAYTESTING - PRESS 'ESC' TO EXIT | NOCLIP: {getattr(self, 'noclip', False)}", True, config.YELLOW)
            surface.blit(overlay, (S(config.BASE_W//2) - overlay.get_width()//2, S(12)))
            return

        draw_world_background(surface, self.scroll_x, self.scroll_y, current_bg, self.level.bg_design)
        
        scaled_grid = config.GRID_SIZE * self.zoom
        if scaled_grid > 4:
            start_k_x = int(self.scroll_x // config.GRID_SIZE)
            world_x = start_k_x * config.GRID_SIZE
            while True:
                screen_x = (world_x - self.scroll_x) * self.zoom
                if screen_x > config.BASE_W: break
                if screen_x >= 0:
                    color = config.GREEN if world_x == 0 else (50, 50, 70)
                    width = max(1, S(3)) if world_x == 0 else max(1, S(1))
                    pygame.draw.line(surface, color, (S(screen_x), 0), (S(screen_x), config.RENDER_H), width)
                world_x += config.GRID_SIZE
                
            start_k_y = int(self.scroll_y // config.GRID_SIZE)
            world_y = start_k_y * config.GRID_SIZE
            while True:
                screen_y = (world_y - self.scroll_y) * self.zoom
                if screen_y > config.BASE_H: break
                if screen_y >= 0:
                    pygame.draw.line(surface, (50, 50, 70), (0, S(screen_y)), (config.RENDER_W, S(screen_y)), max(1, S(1)))
                world_y += config.GRID_SIZE

        if len(self.playtest_trail) > 1:
            pts = []
            for px, py in self.playtest_trail:
                sx = (px - self.scroll_x) * self.zoom * config.get_scale()
                sy = (py - self.scroll_y) * self.zoom * config.get_scale()
                pts.append((sx, sy))
            pygame.draw.lines(surface, config.WHITE, False, pts, max(1, S(2)))

        for obj in sort_for_draw(self.level.objects):
            is_selected = (obj in self.selected_objs)
            alpha = 255 if obj.layer == self.current_layer else 80
            obj.draw(surface, self.scroll_x, self.scroll_y, self.zoom, highlight=is_selected, alpha=alpha)

        if self.selection_box_start and self.selection_box_end:
            x1 = min(self.selection_box_start[0], self.selection_box_end[0])
            y1 = min(self.selection_box_start[1], self.selection_box_end[1])
            w = abs(self.selection_box_end[0] - self.selection_box_start[0])
            h = abs(self.selection_box_end[1] - self.selection_box_start[1])
            sx = int((x1 - self.scroll_x) * self.zoom * config.get_scale())
            sy = int((y1 - self.scroll_y) * self.zoom * config.get_scale())
            sw = int(w * self.zoom * config.get_scale())
            sh = int(h * self.zoom * config.get_scale())
            pygame.draw.rect(surface, config.GREEN, (sx, sy, sw, sh), max(1, S(2)))
            
        if not self.hide_ground:
            draw_world_ground(surface, self.scroll_x, self.scroll_y, self.zoom, current_gnd, self.level.ground_design, self.level.start_gamemode)
        else:
            gy = config.GROUND_Y - self.scroll_y
            screen_gy = int(gy * self.zoom * config.get_scale())
            pygame.draw.line(surface, config.WHITE, (0, screen_gy), (config.RENDER_W, screen_gy), max(1, S(2)))

        if self.music_testing:
            playhead_x = int((self.scroll_x + 200 - self.scroll_x) * self.zoom)
            pygame.draw.line(surface, config.MAGENTA, (S(playhead_x), 0), (S(playhead_x), config.RENDER_H), max(2, S(4*self.zoom)))

        pygame.draw.rect(surface, config.DARK_GRAY, (0, 0, config.RENDER_W, S(40)))
        pygame.draw.line(surface, config.WHITE, (0, S(40)), (config.RENDER_W, S(40)), max(1, S(2)))
        
        obj_count_txt = font.render(f"Objects: {len(self.level.objects)}", True, config.WHITE)
        surface.blit(obj_count_txt, (S(config.BASE_W - 300), S(45)))
        
        def top_btn(text, x, color):
            t = font.render(text, True, color)
            rect = pygame.Rect(S(x), S(10), t.get_width() + S(20), S(20))
            pygame.draw.rect(surface, config.GRAY, rect, max(1, S(1)))
            surface.blit(t, (S(x + 10), S(10)))
            return x + (t.get_width()/config.get_scale()) + 30

        curr_x = 10
        curr_x = top_btn(f"Song: {self.level.music if self.level.music else 'Default'}", curr_x, config.CYAN)
        curr_x = max(curr_x, 320)
        curr_x = top_btn("Level Options", curr_x, config.YELLOW)

        nc_rect = pygame.Rect(S(config.BASE_W - 220), S(10), S(80), S(20))
        pygame.draw.rect(surface, config.GREEN if getattr(self, 'noclip', False) else config.GRAY, nc_rect, 0, S(4))
        nc_t = font.render("NOCLIP", True, config.BLACK if getattr(self, 'noclip', False) else config.WHITE)
        surface.blit(nc_t, (nc_rect.centerx - nc_t.get_width()//2, nc_rect.centery - nc_t.get_height()//2))

        hg_rect = pygame.Rect(S(config.BASE_W - 350), S(10), S(120), S(20))
        pygame.draw.rect(surface, config.GREEN if getattr(self, 'hide_ground', False) else config.GRAY, hg_rect, 0, S(4))
        hg_t = font.render("HIDE GND", True, config.BLACK if getattr(self, 'hide_ground', False) else config.WHITE)
        surface.blit(hg_t, (hg_rect.centerx - hg_t.get_width()//2, hg_rect.centery - hg_t.get_height()//2))

        exit_rect = pygame.Rect(S(config.BASE_W - 130), S(10), S(60), S(20))
        pygame.draw.rect(surface, config.RED, exit_rect, 0, S(4))
        exit_t = font.render("EXIT", True, config.WHITE)
        surface.blit(exit_t, (exit_rect.centerx - exit_t.get_width()//2, exit_rect.centery - exit_t.get_height()//2))

        save_rect = pygame.Rect(S(config.BASE_W - 60), S(10), S(50), S(20))
        pygame.draw.rect(surface, config.GREEN if self.unsaved_changes else config.GRAY, save_rect, 0, S(4))
        save_t = font.render("SAVE", True, config.BLACK)
        surface.blit(save_t, (save_rect.centerx - save_t.get_width()//2, save_rect.centery - save_t.get_height()//2))

        pygame.draw.rect(surface, (20,20,20, 200), (0, S(config.BASE_H - 120), config.RENDER_W, S(120)))
        
        mode_color = config.GREEN if self.mode == "BUILD" else config.YELLOW if self.mode == "EDIT" else config.RED
        surface.blit(font.render(f"MODE: {self.mode}", True, mode_color), (S(10), S(config.BASE_H - 90)))
        
        if self.mode == "BUILD":
            cat_name = self.category_names[self.current_cat_idx]
            surface.blit(font.render(f"Category: {cat_name}", True, config.WHITE), (S(150), S(config.BASE_H - 90)))
            self.draw_color_and_layer_controls(surface, font)

            start_x = 10
            for i, item_id in enumerate(config.CATEGORIES[cat_name]):
                box_rect = pygame.Rect(S(start_x + i * 50), S(config.BASE_H - 70), S(40), S(40))
                if i == self.current_item_idx: pygame.draw.rect(surface, config.GREEN, box_rect, max(1, S(2)))
                else: pygame.draw.rect(surface, config.GRAY, box_rect, max(1, S(1)))

                dummy_obj = GameObject(item_id, 0, 0, self.current_rot, self.current_color, self.current_flip_x)
                dummy_surf = dummy_obj.get_surface(zoom=1.0)
                tw, th = dummy_surf.get_size()
                max_dim = max(tw, th)
                scale_f = S(28) / max_dim
                target_w, target_h = int(tw * scale_f), int(th * scale_f)
                
                scaled = pygame.transform.smoothscale(dummy_surf, (max(1, target_w), max(1, target_h)))
                rect = scaled.get_rect(center=box_rect.center)
                surface.blit(scaled, rect.topleft)
            
            if self.notification_timer > 0:
                notif = title_font.render(self.notification_text, True, config.YELLOW)
                surface.blit(notif, (S(config.BASE_W//2) - notif.get_width()//2, S(config.BASE_H//2)))
            
        if self.mode == "EDIT" and self.selected_objs:
            obj_count = len(self.selected_objs)
            sel_text = font.render(f"Selected: {obj_count} Item(s)", True, config.GREEN)
            surface.blit(sel_text, (S(10), S(config.BASE_H - 60)))
            surface.blit(font.render("Move & Modify:", True, config.WHITE), (S(120), S(config.BASE_H - 70)))
            
            for k, r in self.edit_btns.items():
                if k in ["UNDO", "REDO"]: continue
                sr = pygame.Rect(S(r.x), S(r.y), S(r.w), S(r.h))
                pygame.draw.rect(surface, config.RED if k == "DEL" else config.DARK_GRAY, sr)
                pygame.draw.rect(surface, config.WHITE, sr, max(1, S(1)))
                label = k.replace("ROT_", "R_").replace("FLIP_", "F_")
                t = font.render(label, True, config.WHITE)
                surface.blit(t, (sr.centerx - t.get_width()//2, sr.centery - sr.h//2 + S(2)))

            self.draw_color_and_layer_controls(surface, font)
        elif self.mode == "DELETE" or self.mode == "EDIT":
            self.draw_layer_controls(surface, font)

        for k in ["UNDO", "REDO"]:
            r = self.edit_btns[k]
            sr = pygame.Rect(S(r.x), S(r.y), S(r.w), S(r.h))
            pygame.draw.rect(surface, config.DARK_GRAY, sr)
            pygame.draw.rect(surface, config.WHITE, sr, max(1, S(1)))
            t = font.render(k, True, config.WHITE)
            surface.blit(t, (sr.centerx - t.get_width()//2, sr.centery - t.get_height()//2))

        if self.show_confirm_exit:
            s_mask = pygame.Surface((config.RENDER_W, config.RENDER_H), pygame.SRCALPHA)
            s_mask.fill((0,0,0, 220))
            surface.blit(s_mask, (0,0))
            box = pygame.Rect(S(config.BASE_W//2 - 200), S(config.BASE_H//2 - 80), S(400), S(160))
            pygame.draw.rect(surface, config.DARK_GRAY, box)
            pygame.draw.rect(surface, config.RED, box, max(1, S(3)))
            
            t = title_font.render("Unsaved Changes!", True, config.RED)
            surface.blit(t, (S(config.BASE_W//2) - t.get_width()//2, box.y + S(15)))
            t2 = font.render("Are you sure you want to exit?", True, config.WHITE)
            surface.blit(t2, (S(config.BASE_W//2) - t2.get_width()//2, box.y + S(60)))
            
            yes_btn = pygame.Rect(S(config.BASE_W//2 - 120), S(config.BASE_H//2 + 20), S(100), S(40))
            no_btn = pygame.Rect(S(config.BASE_W//2 + 20), S(config.BASE_H//2 + 20), S(100), S(40))
            pygame.draw.rect(surface, config.GREEN, yes_btn)
            pygame.draw.rect(surface, config.GRAY, no_btn)
            
            yt = font.render("YES", True, config.BLACK)
            nt = font.render("NO", True, config.WHITE)
            surface.blit(yt, (yes_btn.centerx - yt.get_width()//2, yes_btn.centery - yt.get_height()//2))
            surface.blit(nt, (no_btn.centerx - nt.get_width()//2, no_btn.centery - nt.get_height()//2))

        elif self.color_picker_active:
            s_mask = pygame.Surface((config.RENDER_W, config.RENDER_H), pygame.SRCALPHA)
            s_mask.fill((0,0,0, 200))
            surface.blit(s_mask, (0,0))

            box = self.color_picker_box()
            box_s = pygame.Rect(S(box.x), S(box.y), S(box.w), S(box.h))
            pygame.draw.rect(surface, config.DARK_GRAY, box_s, 0, S(10))
            pygame.draw.rect(surface, config.CYAN, box_s, max(1, S(3)), S(10))

            t = title_font.render("COLOR PICKER", True, config.WHITE)
            surface.blit(t, (box_s.centerx - t.get_width()//2, box_s.y + S(15)))

            target_objs = self.selected_objs if (self.mode == "EDIT" and self.selected_objs) else None
            active = None
            if target_objs:
                if all(o.color_idx == target_objs[0].color_idx for o in target_objs):
                    active = target_objs[0].color_idx
            else:
                active = self.current_color

            for idx, i in enumerate(config.UI_COLOR_ORDER):
                r = self.color_picker_swatch_rect(idx)
                rs = pygame.Rect(S(r.x), S(r.y), S(r.w), S(r.h))
                pygame.draw.rect(surface, config.BG_COLORS[i], rs)
                pygame.draw.rect(surface, config.GREEN if i == active else config.WHITE, rs, max(1, S(2) if i == active else S(1)))

            tip = font.render("(Click a color to apply, click outside to close)", True, config.GRAY)
            surface.blit(tip, (box_s.centerx - tip.get_width()//2, box_s.bottom - S(30)))

        elif self.song_browser_active:
            s_mask = pygame.Surface((config.RENDER_W, config.RENDER_H), pygame.SRCALPHA)
            s_mask.fill((0,0,0, 200))
            surface.blit(s_mask, (0,0))

            box = pygame.Rect(S(config.BASE_W//2 - 300), S(100), S(600), S(config.BASE_H - 200))
            pygame.draw.rect(surface, config.DARK_GRAY, box, 0, S(10))
            pygame.draw.rect(surface, config.CYAN, box, max(1, S(3)), S(10))
            
            t = title_font.render("SONG BROWSER", True, config.WHITE)
            surface.blit(t, (S(config.BASE_W//2) - t.get_width()//2, S(110)))
            
            for i, song in enumerate(self.audio.available_tracks):
                play_btn = pygame.Rect(S(config.BASE_W//2 - 250), S(200 + i*40), S(40), S(30))
                pygame.draw.rect(surface, config.YELLOW if self.preview_song == song else config.GRAY, play_btn, 0, S(5))
                pt = font.render("||" if self.preview_song == song else ">", True, config.BLACK if self.preview_song == song else config.WHITE)
                surface.blit(pt, (play_btn.centerx - pt.get_width()//2, play_btn.centery - pt.get_height()//2))
                
                rect = pygame.Rect(S(config.BASE_W//2 - 200), S(200 + i*40), S(350), S(30))
                pygame.draw.rect(surface, config.GRAY, rect, 0, S(5))
                st = font.render(song, True, config.WHITE)
                surface.blit(st, (rect.x + S(10), rect.centery - st.get_height()//2))

                sel_btn = pygame.Rect(S(config.BASE_W//2 + 160), S(200 + i*40), S(90), S(30))
                pygame.draw.rect(surface, config.GREEN, sel_btn, 0, S(5))
                s_t = font.render("SELECT", True, config.BLACK)
                surface.blit(s_t, (sel_btn.centerx - s_t.get_width()//2, sel_btn.centery - s_t.get_height()//2))
            
            tip = font.render("(Click anywhere outside to close)", True, config.GRAY)
            surface.blit(tip, (S(config.BASE_W//2) - tip.get_width()//2, box.bottom - S(30)))

        elif self.options_active:
            s_mask = pygame.Surface((config.RENDER_W, config.RENDER_H), pygame.SRCALPHA)
            s_mask.fill((0,0,0, 200))
            surface.blit(s_mask, (0,0))
            
            box = pygame.Rect(S(config.BASE_W//2 - 350), S(100), S(700), S(480))
            pygame.draw.rect(surface, config.DARK_GRAY, box, 0, S(10))
            pygame.draw.rect(surface, config.CYAN, box, max(1, S(3)), S(10))
            
            t = title_font.render("LEVEL OPTIONS", True, config.WHITE)
            surface.blit(t, (S(config.BASE_W//2) - t.get_width()//2, S(110)))
            
            mode_btn = pygame.Rect(S(config.BASE_W//2 - 200), S(160), S(400), S(40))
            pygame.draw.rect(surface, config.GRAY, mode_btn, 0, S(5))
            pygame.draw.rect(surface, config.WHITE, mode_btn, max(1, S(2)), S(5))
            mt = font.render(f"STARTING GAMEMODE: {self.level.start_gamemode.upper()}", True, config.BLACK)
            surface.blit(mt, (mode_btn.centerx - mt.get_width()//2, mode_btn.centery - mt.get_height()//2))

            surface.blit(font.render("Background Design:", True, config.WHITE), (S(config.BASE_W//2 - 270), S(220)))
            for i in range(6):
                rect = pygame.Rect(S(config.BASE_W//2 - 270 + i * 90), S(250), S(70), S(70))
                sub_surf = pygame.Surface((70, 70))
                draw_world_background(sub_surf, 0, 0, config.BG_COLORS[self.level.start_bg_idx], i)
                scaled_sub = pygame.transform.scale(sub_surf, (S(70), S(70)))
                surface.blit(scaled_sub, rect)
                pygame.draw.rect(surface, config.GREEN if self.level.bg_design == i else config.WHITE, rect, max(1, S(3)) if self.level.bg_design == i else max(1, S(1)))
            
            surface.blit(font.render("BG", True, config.WHITE), (S(config.BASE_W//2 + 280), S(240)))
            cbox = pygame.Rect(S(config.BASE_W//2 + 280), S(265), S(40), S(40))
            pygame.draw.rect(surface, config.BG_COLORS[self.level.start_bg_idx], cbox)
            pygame.draw.rect(surface, config.WHITE, cbox, max(1, S(2)))

            surface.blit(font.render("Ground Design:", True, config.WHITE), (S(config.BASE_W//2 - 270), S(350)))
            for i in range(6):
                rect = pygame.Rect(S(config.BASE_W//2 - 270 + i * 90), S(380), S(70), S(70))
                sub_surf = pygame.Surface((70, 70))
                draw_world_ground(sub_surf, 0, config.GROUND_Y - 35, 1.0, config.BG_COLORS[self.level.start_ground_idx], i, "cube")
                scaled_sub = pygame.transform.scale(sub_surf, (S(70), S(70)))
                surface.blit(scaled_sub, rect)
                pygame.draw.rect(surface, config.GREEN if self.level.ground_design == i else config.WHITE, rect, max(1, S(3)) if self.level.ground_design == i else max(1, S(1)))

            surface.blit(font.render("GND", True, config.WHITE), (S(config.BASE_W//2 + 280), S(370)))
            gbox = pygame.Rect(S(config.BASE_W//2 + 280), S(395), S(40), S(40))
            pygame.draw.rect(surface, config.BG_COLORS[self.level.start_ground_idx], gbox)
            pygame.draw.rect(surface, config.WHITE, gbox, max(1, S(2)))

            hg_btn = pygame.Rect(S(config.BASE_W//2 - 200), S(450), S(190), S(40))
            pygame.draw.rect(surface, config.GREEN if self.hide_ground else config.GRAY, hg_btn, 0, S(5))
            pygame.draw.rect(surface, config.WHITE, hg_btn, max(1, S(2)), S(5))
            hgt = font.render("HIDE GROUND", True, config.BLACK if self.hide_ground else config.WHITE)
            surface.blit(hgt, (hg_btn.centerx - hgt.get_width()//2, hg_btn.centery - hgt.get_height()//2))

            nc_btn = pygame.Rect(config.BASE_W//2 - 120, 240, 100, 40)
            pygame.draw.rect(surface, config.GREEN if getattr(self, 'noclip', False) else config.GRAY, nc_btn, 0, S(5))
            pygame.draw.rect(surface, config.WHITE, nc_btn, max(1, S(2)), S(5))
            nct = font.render("NOCLIP", True, config.BLACK if getattr(self, 'noclip', False) else config.WHITE)
            surface.blit(nct, (nc_btn.centerx - nct.get_width()//2, nc_btn.centery - nct.get_height()//2))

            close_btn = pygame.Rect(S(config.BASE_W//2 - 100), S(500), S(200), S(40))
            pygame.draw.rect(surface, config.RED, close_btn, 0, S(5))
            ct = font.render("CLOSE", True, config.WHITE)
            surface.blit(ct, (close_btn.centerx - ct.get_width()//2, close_btn.centery - ct.get_height()//2))