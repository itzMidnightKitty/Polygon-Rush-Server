import pygame
import math
import config

# Kept as a no-op target: main.py calls player._icon_cache.clear() when the
# player changes their icon/color selection in the profile screen.
_icon_cache = {}

class Player:
    def __init__(self):
        self.reset()

    def reset(self, start_x=200, start_y=None, start_mode="cube"):
        self.mode = start_mode
        self.width = 24 if self.mode == "wave" else 28 if self.mode == "ship" else 28 if self.mode == "ufo" else config.GRID_SIZE
        self.height = 24 if self.mode == "wave" else 16 if self.mode == "ship" else 28 if self.mode == "ufo" else config.GRID_SIZE
        self.x = start_x
        self.y = start_y if start_y is not None else config.GROUND_Y - self.height
        
        self.vel_y = 0
        self.gravity_dir = 1 
        self.on_ground = False
        self.on_roof = False
        self.dead = False
        self.death_sound_played = False
        self.won = False
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.orb_touched_last_frame = False
        self.jump_held = False
        self.jump_orb_ready = False
        self.rotation = 0
        self.target_rotation = 0

    def update(self, keys, objects, scroll_speed, noclip=False, ignore_mouse=False):
        if self.dead or self.won: return

        if self.mode == "wave":
            if self.width != 24:
                if self.on_ground: self.y += self.height - 24
                elif self.on_roof: pass
                else: self.y += (self.height - 24) / 2
                self.width, self.height = 24, 24
                self.rect.width, self.rect.height = 24, 24
        elif self.mode == "ship":
            if self.width != 28:
                if self.on_ground: self.y += self.height - 16
                elif self.on_roof: pass
                else: self.y += (self.height - 16) / 2
                self.width, self.height = 28, 16
                self.rect.width, self.rect.height = 28, 16
        elif self.mode == "ufo":
            if self.width != 28:
                if self.on_ground: self.y += self.height - 28
                elif self.on_roof: pass
                else: self.y += (self.height - 28) / 2
                self.width, self.height = 28, 28
                self.rect.width, self.rect.height = 28, 28
        else:
            if self.width != config.GRID_SIZE:
                if self.on_ground: self.y -= config.GRID_SIZE - self.height
                elif self.on_roof: pass
                else: self.y -= (config.GRID_SIZE - self.height) / 2
                self.width, self.height = config.GRID_SIZE, config.GRID_SIZE
                self.rect.width, self.rect.height = config.GRID_SIZE, config.GRID_SIZE

        jump_input = keys[pygame.K_SPACE] or (pygame.mouse.get_pressed()[0] and not ignore_mouse) or keys[pygame.K_UP]
        jump_just_pressed = jump_input and not self.jump_held
        self.jump_held = jump_input

        if jump_just_pressed:
            self.jump_orb_ready = True
        elif not jump_input:
            self.jump_orb_ready = False
            
        consume_jump = self.jump_orb_ready
        jump_vel = -14.5 * self.gravity_dir 
        gravity_force = 1.2 * self.gravity_dir 

        if self.mode == "cube":
            self.vel_y += gravity_force
            if getattr(self, 'on_ground', False): self.coyote_timer = 4
            elif getattr(self, 'coyote_timer', 0) > 0: self.coyote_timer -= 1
            
            if (consume_jump or jump_input) and (getattr(self, 'on_ground', False) or getattr(self, 'coyote_timer', 0) > 0):
                self.vel_y = jump_vel
                self.on_ground = False
                self.coyote_timer = 0
                self.jump_orb_ready = False
                self.target_rotation = round(self.rotation / 90) * 90 - 180 * self.gravity_dir

        elif self.mode == "ship":
            if jump_input:
                thrust = -0.45 if self.gravity_dir == 1 else 0.45
                self.vel_y += thrust
            else:
                fall = 0.3 if self.gravity_dir == 1 else -0.3
                self.vel_y += fall
            self.vel_y = max(min(self.vel_y, 7.5), -7.5)
            
        elif self.mode == "ball":
            self.vel_y += gravity_force
            if consume_jump and (self.on_ground or self.on_roof):
                self.gravity_dir *= -1
                self.vel_y = 0
                self.on_ground = False
                self.on_roof = False
                self.jump_orb_ready = False
                
        elif self.mode == "ufo":
            if jump_just_pressed:
                self.vel_y = -10.0 * self.gravity_dir
                self.jump_orb_ready = False
            self.vel_y += gravity_force * 0.5
            self.vel_y = max(min(self.vel_y, 12), -12)
                
        elif self.mode == "wave":
            target_vel = scroll_speed if not jump_input else -scroll_speed
            self.vel_y = target_vel * self.gravity_dir

        prev_y = self.y
        prev_bottom = prev_y + self.height
        prev_top = prev_y

        self.y += self.vel_y
        self.rect.y = int(self.y)
        self.on_ground = False
        self.on_roof = False

        if self.mode in ('ship', 'ball', 'wave', 'ufo') and self.rect.top <= config.CEILING_Y:
            self.rect.top = config.CEILING_Y
            self.y = self.rect.y
            if self.mode in ('ship', 'wave', 'ufo'):
                self.vel_y = max(0, self.vel_y) if self.gravity_dir == 1 else min(0, self.vel_y)
                if self.mode == 'wave' and self.vel_y == 0: self.on_roof = True
            else:
                self.vel_y = 0
                if self.gravity_dir == -1: self.on_roof = True

        if self.rect.bottom >= config.GROUND_Y:
            self.rect.bottom = config.GROUND_Y
            self.y = self.rect.y
            self.vel_y = 0
            if self.gravity_dir == 1 or self.mode in ('ship', 'wave', 'ufo'): self.on_ground = True
            
        if self.mode == 'cube' and self.rect.bottom <= -3000:
            self.die(noclip)

        inner_rect = self.rect.inflate(-20, -20)
        for obj in objects:
            if obj.is_solid() and self.rect.colliderect(obj.rect):
                if self.mode == "wave":
                    self.die(noclip)
                else:
                    # Y-collisions using a slightly narrower hitbox so you slide off edges instead of hovering
                    y_rect = self.rect.inflate(-12, 0)
                    if self.vel_y > 0 and prev_bottom <= obj.rect.top + abs(self.vel_y) + 2: 
                        if y_rect.right > obj.rect.left and y_rect.left < obj.rect.right:
                            self.rect.bottom = obj.rect.top; self.y = self.rect.y; self.vel_y = 0
                            if self.gravity_dir == 1: self.on_ground = True
                            elif self.gravity_dir == -1: self.on_roof = True
                    elif self.vel_y < 0 and prev_top >= obj.rect.bottom - abs(self.vel_y) - 2: 
                        if y_rect.right > obj.rect.left and y_rect.left < obj.rect.right:
                            self.rect.top = obj.rect.bottom; self.y = self.rect.y; self.vel_y = 0
                            if self.gravity_dir == -1: self.on_ground = True
                            elif self.gravity_dir == 1: self.on_roof = True

        if self.mode == "cube":
            if self.on_ground:
                target_rot = round(self.rotation / 90) * 90
                diff = (target_rot - self.rotation)
                while diff > 180: diff -= 360
                while diff < -180: diff += 360
                self.rotation += diff * 0.4
                self.target_rotation = target_rot
            else:
                self.rotation -= 7 * self.gravity_dir
                self.target_rotation = round(self.rotation / 90) * 90
                        
        elif self.mode == "ship":
            target_rot = max(-60, min(60, self.vel_y * -7))
            self.rotation += (target_rot - self.rotation) * 0.35
        elif self.mode == "ball":
            self.rotation -= 10 * (scroll_speed / 9) * self.gravity_dir
        elif self.mode == "wave":
            if self.on_ground or self.on_roof: 
                target_rot = 0
            else: 
                target_rot = 45 if self.vel_y < 0 else -45
            self.rotation += (target_rot - self.rotation) * 0.4

        self.x += scroll_speed
        self.rect.x = int(self.x)

        overlapping_orb = False
        if not hasattr(self, 'active_pads'): self.active_pads = set()
        current_pads = set()
        
        for obj in objects:
            if self.rect.colliderect(obj.rect):
                if obj.type == config.OBJ_PORTAL_CUBE: 
                    if self.mode != "cube": self.rotation = round(self.rotation / 90) * 90
                    self.mode = "cube"
                elif obj.type == config.OBJ_PORTAL_SHIP: 
                    if self.mode != "ship": self.rotation = 0
                    self.mode = "ship"
                elif obj.type == config.OBJ_PORTAL_BALL: 
                    if self.mode != "ball": self.rotation = 0
                    self.mode = "ball"
                elif obj.type == config.OBJ_PORTAL_UFO:
                    if self.mode != "ufo": self.rotation = 0
                    self.mode = "ufo"
                elif obj.type == config.OBJ_PORTAL_WAVE: 
                    self.mode = "wave"
                elif obj.type == config.OBJ_PORTAL_GRAV_DOWN:
                    if self.gravity_dir == -1:
                        self.gravity_dir = 1
                        # Momentum carries through the flip (unlike the blue pad's hard reset),
                        # but damped so it settles into the new gravity quickly instead of
                        # coasting like a gravity orb. Wave mode is a direct function of
                        # gravity_dir each frame rather than accumulated, so it just flips sign.
                        if self.mode == "wave": self.vel_y = -self.vel_y
                        else: self.vel_y *= 0.4
                        self.on_ground = False; self.on_roof = False
                        self.target_rotation = round(self.rotation / 90) * 90 + 180 * self.gravity_dir
                elif obj.type == config.OBJ_PORTAL_GRAV_UP:
                    if self.gravity_dir == 1:
                        self.gravity_dir = -1
                        if self.mode == "wave": self.vel_y = -self.vel_y
                        else: self.vel_y *= 0.4
                        self.on_ground = False; self.on_roof = False
                        self.target_rotation = round(self.rotation / 90) * 90 - 180 * self.gravity_dir
                elif obj.type == config.OBJ_PAD_YELLOW:
                    current_pads.add(id(obj))
                    if id(obj) not in self.active_pads:
                        # Launch direction is purely a function of the pad's own mounting
                        # rotation (0 = floor-mounted, launches up; 180 = ceiling-mounted,
                        # launches down) -- it must NOT also be scaled by gravity_dir, or a
                        # ceiling pad placed for a reversed-gravity section (the standard
                        # way to use one) cancels back out and launches the wrong way.
                        self.vel_y = 20.0 if obj.rotation == 180 else -20.0
                        self.on_ground = False; self.on_roof = False
                        self.target_rotation = round(self.rotation / 90) * 90 - 360 * self.gravity_dir
                elif obj.type == config.OBJ_PAD_PURPLE:
                    current_pads.add(id(obj))
                    if id(obj) not in self.active_pads:
                        self.vel_y = 13.0 if obj.rotation == 180 else -13.0
                        self.on_ground = False; self.on_roof = False
                        self.target_rotation = round(self.rotation / 90) * 90 - 180 * self.gravity_dir
                elif obj.type == config.OBJ_PAD_BLUE:
                    current_pads.add(id(obj))
                    if id(obj) not in self.active_pads:
                        self.gravity_dir *= -1
                        self.vel_y = -self.vel_y if self.vel_y != 0 else -10.0 * self.gravity_dir
                        self.on_ground = False; self.on_roof = False
                        self.target_rotation = round(self.rotation / 90) * 90 - 180 * self.gravity_dir
                elif obj.type == config.OBJ_ORB_YELLOW:
                    overlapping_orb = True
                    if consume_jump and not self.orb_touched_last_frame:
                        self.vel_y = -17.0 * self.gravity_dir; self.on_ground = False; self.orb_touched_last_frame = True; self.jump_orb_ready = False
                        self.target_rotation = round(self.rotation / 90) * 90 - 360 * self.gravity_dir
                elif obj.type == config.OBJ_ORB_PURPLE:
                    overlapping_orb = True
                    if consume_jump and not self.orb_touched_last_frame:
                        self.vel_y = -11.0 * self.gravity_dir; self.on_ground = False; self.orb_touched_last_frame = True; self.jump_orb_ready = False
                        self.target_rotation = round(self.rotation / 90) * 90 - 180 * self.gravity_dir
                elif obj.type == config.OBJ_ORB_BLUE:
                    overlapping_orb = True
                    if consume_jump and not self.orb_touched_last_frame:
                        self.gravity_dir *= -1; self.vel_y = 0; self.on_ground = False; self.orb_touched_last_frame = True; self.jump_orb_ready = False
                        self.target_rotation = round(self.rotation / 90) * 90 - 180 * self.gravity_dir
                elif obj.is_deadly():
                    self.die(noclip)

                if obj.is_solid() and self.mode != "wave" and self.rect.colliderect(obj.rect):
                    if inner_rect.right > obj.rect.left and inner_rect.left < obj.rect.right:
                        margin_y = 2 if self.mode == "ship" else 14
                        if self.rect.bottom > obj.rect.top + margin_y and self.rect.top < obj.rect.bottom - margin_y:
                            self.die(noclip)

        self.active_pads = current_pads
        if not overlapping_orb: self.orb_touched_last_frame = False

    def die(self, noclip=False): 
        if not noclip: self.dead = True

    def _lighten(self, color, amt=0.4):
        return tuple(min(255, int(c + (255 - c) * amt)) for c in color)

    def _darken(self, color, amt=0.35):
        return tuple(max(0, int(c * (1 - amt))) for c in color)

    def _draw_mini_rider(self, surf, cx, cy, size, color, color2):
        """A tiny cube-shaped pilot silhouette riding on top of a ship hull."""
        r = pygame.Rect(0, 0, size, size)
        r.center = (int(cx), int(cy))
        radius = max(1, int(size * 0.22))
        pygame.draw.rect(surf, color, r, border_radius=radius)
        pygame.draw.rect(surf, color2, r, max(1, int(size * 0.14)), border_radius=radius)
        eye_w = max(1, int(size * 0.18))
        eye_h = max(1, int(size * 0.18))
        eye_y = r.centery - int(size * 0.08)
        pygame.draw.rect(surf, config.BLACK, (r.centerx - int(size * 0.32), eye_y, eye_w, eye_h))
        pygame.draw.rect(surf, config.BLACK, (r.centerx + int(size * 0.14), eye_y, eye_w, eye_h))

    def _draw_ship_variant(self, surf, body_pts, dark_pts, light_pts, accents, rider_pos, rider_size, color, color2, light_c, dark_c, border_w):
        pygame.draw.polygon(surf, color, body_pts)
        if dark_pts:
            pygame.draw.polygon(surf, dark_c, dark_pts)
        if light_pts:
            pygame.draw.polygon(surf, light_c, light_pts)
        pygame.draw.polygon(surf, color2, body_pts, border_w)
        for pts, acc_color in accents:
            pygame.draw.polygon(surf, acc_color, pts)
            pygame.draw.polygon(surf, config.BLACK, pts, max(1, border_w - 1))
        if rider_pos:
            self._draw_mini_rider(surf, rider_pos[0], rider_pos[1], rider_size, color, color2)

    def _outline_and_blit(self, surface, shape_surf, center, outline_offset, flip_v=False):
        s = pygame.transform.flip(shape_surf, False, True) if flip_v else shape_surf
        rotated = pygame.transform.rotate(s, self.rotation)
        rect = rotated.get_rect(center=center)
        mask = pygame.mask.from_surface(rotated)
        outline = mask.to_surface(setcolor=config.BLACK, unsetcolor=(0, 0, 0, 0))
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (1,1), (-1,1), (1,-1)]:
            surface.blit(outline, (rect.x + dx*outline_offset, rect.y + dy*outline_offset))
        surface.blit(rotated, rect.topleft)

    def draw(self, surface, scroll_x, scroll_y, zoom=1.0, noclip=False):
        if self.dead: return
        z_scale = zoom * config.get_scale()

        draw_x = int((self.x - scroll_x) * z_scale)
        draw_y = int((self.y - scroll_y) * z_scale)
        w = max(1, int(self.width * z_scale))
        h = max(1, int(self.height * z_scale))

        color = config.P_COLOR
        color2 = getattr(config, 'P_COLOR2', config.WHITE)
        light = self._lighten(color)
        border_w = max(2, int(3 * z_scale))
        outline_offset = max(2, int(3 * z_scale))

        if noclip:
            halo_rect = pygame.Rect(draw_x - int(4*z_scale), draw_y - int(4*z_scale), w + int(8*z_scale), h + int(8*z_scale))
            pygame.draw.rect(surface, (255, 0, 0, 100), halo_rect, border_w, int(5*z_scale))

        if self.mode == "ball":
            center = (draw_x + w//2, draw_y + h//2)
            radius = w//2
            ball_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.circle(ball_surf, color, (w//2, h//2), radius)
            pygame.draw.circle(ball_surf, light, (int(w*0.36), int(h*0.34)), max(2, int(radius*0.26)))
            pygame.draw.circle(ball_surf, color2, (w//2, h//2), radius, border_w)

            if config.P_BALL_IDX == 0:
                pygame.draw.circle(ball_surf, color2, (w//2, h//2), radius//2, border_w)
                pygame.draw.circle(ball_surf, color2, (w//2, h//2), radius//4)
            elif config.P_BALL_IDX == 1:
                for i in range(8):
                    angle = math.pi/4 * i
                    pts = [(w//2 + math.cos(angle - 0.2)*radius//2, h//2 + math.sin(angle - 0.2)*radius//2),
                           (w//2 + math.cos(angle + 0.2)*radius//2, h//2 + math.sin(angle + 0.2)*radius//2),
                           (w//2 + math.cos(angle)*radius, h//2 + math.sin(angle)*radius)]
                    pygame.draw.polygon(ball_surf, color2, pts)
                pygame.draw.circle(ball_surf, config.BLACK, (w//2, h//2), radius//2)
                pygame.draw.circle(ball_surf, color2, (w//2, h//2), radius//3, border_w)
            elif config.P_BALL_IDX == 2:
                # Yin Yang
                pygame.draw.circle(ball_surf, color2, (w//2, h//2), radius)
                pts = [(w//2, h//2)]
                for i in range(181):
                    a = math.pi/2 - math.pi * (i/180)
                    pts.append((w//2 + math.cos(a)*radius, h//2 - math.sin(a)*radius))
                pygame.draw.polygon(ball_surf, color, pts)
                pygame.draw.circle(ball_surf, color, (w//2, h//4), radius//2)
                pygame.draw.circle(ball_surf, color2, (w//2, 3*h//4), radius//2)
                pygame.draw.circle(ball_surf, color2, (w//2, h//4), radius//5)
                pygame.draw.circle(ball_surf, color, (w//2, 3*h//4), radius//5)
                pygame.draw.circle(ball_surf, color2, (w//2, h//2), radius, border_w)
            elif config.P_BALL_IDX == 3:
                pygame.draw.circle(ball_surf, color2, (w//2, h//2), radius*0.8, border_w)
                pygame.draw.circle(ball_surf, config.BLACK, (w//2, h//2), radius*0.5)
                pygame.draw.circle(ball_surf, color2, (w//2, h//2), radius*0.3)
                for i in range(4):
                    angle = math.pi/2 * i
                    pygame.draw.circle(ball_surf, color2, (w//2 + math.cos(angle)*radius*0.6, h//2 + math.sin(angle)*radius*0.6), radius*0.15)
            elif config.P_BALL_IDX == 4:
                for i in range(4):
                    angle = math.pi/2 * i
                    pts = [(w//2, h//2),
                           (w//2 + math.cos(angle - 0.3)*radius, h//2 + math.sin(angle - 0.3)*radius),
                           (w//2 + math.cos(angle + 0.3)*radius*0.5, h//2 + math.sin(angle + 0.3)*radius*0.5)]
                    pygame.draw.polygon(ball_surf, color2, pts)
                pygame.draw.circle(ball_surf, config.BLACK, (w//2, h//2), radius//3)
            elif config.P_BALL_IDX == 5:
                pts = []
                for i in range(10):
                    angle = math.pi/5 * i - math.pi/2
                    r = radius if i % 2 == 0 else radius//2
                    pts.append((w//2 + math.cos(angle)*r, h//2 + math.sin(angle)*r))
                pygame.draw.polygon(ball_surf, color2, pts)
                pygame.draw.circle(ball_surf, config.BLACK, (w//2, h//2), radius//2)
                pygame.draw.circle(ball_surf, color, (w//2, h//2), radius//3)
                pygame.draw.circle(ball_surf, color2, (w//2, h//2), radius//3, border_w)
            elif config.P_BALL_IDX == 6:
                pygame.draw.circle(ball_surf, color2, (w//2, h//2), int(radius*0.7))
                pygame.draw.circle(ball_surf, color, (w//2, h//2), int(radius*0.4))
                for i in range(8):
                    angle = math.pi/4 * i
                    pygame.draw.polygon(ball_surf, color2, [(w//2 + math.cos(angle - 0.2)*radius*0.7, h//2 + math.sin(angle - 0.2)*radius*0.7),
                                                          (w//2 + math.cos(angle + 0.2)*radius*0.7, h//2 + math.sin(angle + 0.2)*radius*0.7),
                                                          (w//2 + math.cos(angle)*radius, h//2 + math.sin(angle)*radius)])
            elif config.P_BALL_IDX == 7:
                pygame.draw.circle(ball_surf, color2, (w//2, h//2), radius)
                pygame.draw.circle(ball_surf, config.BLACK, (w//2, h//2), radius, border_w)
                pygame.draw.arc(ball_surf, config.BLACK, (w*0.1, -h*0.2, w*0.8, h*1.4), math.pi*0.2, math.pi*0.8, max(1, int(3*z_scale)))
                pygame.draw.arc(ball_surf, config.BLACK, (w*0.1, -h*0.2, w*0.8, h*1.4), math.pi*1.2, math.pi*1.8, max(1, int(3*z_scale)))
                pygame.draw.line(ball_surf, config.BLACK, (0, h//2), (w, h//2), max(1, int(3*z_scale)))
                pygame.draw.line(ball_surf, config.BLACK, (w//2, 0), (w//2, h), max(1, int(3*z_scale)))

            self._outline_and_blit(surface, ball_surf, center, outline_offset)

        elif self.mode == "ship":
            w_draw = max(1, int(config.GRID_SIZE * z_scale))
            h_draw = max(1, int(config.GRID_SIZE * z_scale))
            ship_surf = pygame.Surface((w_draw, h_draw), pygame.SRCALPHA)
            
            # All ship variants are drawn in SIDE VIEW (nose points right, +x), built from a
            # faceted hull (dark underbelly / light top panel) plus jagged tail spikes, with
            # a mini cube-shaped pilot riding on top — so the silhouette is never vertically
            # symmetric and flipping for gravity always reads clearly as upside-down.
            dark = self._darken(color)
            ww, hh = w_draw, h_draw

            if config.P_SHIP_IDX == 0:
                body = [(0, hh*0.6), (0, hh*0.4), (ww*0.15, hh*0.36), (ww*0.15, hh*0.28), (ww*0.45, hh*0.28), (ww*0.45, hh*0.36),
                        (ww*0.75, hh*0.4), (ww*0.92, hh*0.5), (ww*0.75, hh*0.6), (ww*0.45, hh*0.64), (ww*0.45, hh*0.72), (ww*0.15, hh*0.72), (ww*0.15, hh*0.64)]
                dark_p = [(ww*0.15, hh*0.5), (ww*0.15, hh*0.72), (ww*0.45, hh*0.72), (ww*0.45, hh*0.64), (ww*0.75, hh*0.6), (ww*0.92, hh*0.5)]
                light_p = [(ww*0.15, hh*0.28), (ww*0.45, hh*0.28), (ww*0.45, hh*0.36), (ww*0.75, hh*0.4), (ww*0.92, hh*0.5), (ww*0.45, hh*0.5), (ww*0.15, hh*0.5)]
                accents = [
                    ([(0, hh*0.4), (ww*0.08, hh*0.3), (ww*0.1, hh*0.4)], color2),
                    ([(0, hh*0.6), (ww*0.08, hh*0.72), (ww*0.1, hh*0.6)], color2),
                ]
                self._draw_ship_variant(ship_surf, body, dark_p, light_p, accents, (ww*0.3, hh*0.2), hh*0.32, color, color2, light, dark, border_w)
            elif config.P_SHIP_IDX == 1:
                body = [(0, hh*0.52), (0, hh*0.44), (ww*0.35, hh*0.36), (ww*0.55, hh*0.28), (ww*0.8, hh*0.36), (ww, hh*0.5),
                        (ww*0.8, hh*0.6), (ww*0.55, hh*0.68), (ww*0.35, hh*0.6)]
                dark_p = [(ww*0.35, hh*0.5), (ww*0.35, hh*0.6), (ww*0.55, hh*0.68), (ww*0.8, hh*0.6), (ww, hh*0.5)]
                light_p = [(ww*0.35, hh*0.36), (ww*0.55, hh*0.28), (ww*0.8, hh*0.36), (ww*0.55, hh*0.44), (ww*0.35, hh*0.44)]
                accents = [
                    ([(0, hh*0.44), (ww*0.12, hh*0.34), (ww*0.14, hh*0.44)], color2),
                    ([(ww*0.14, hh*0.44), (ww*0.22, hh*0.38), (ww*0.24, hh*0.46)], color2),
                ]
                self._draw_ship_variant(ship_surf, body, dark_p, light_p, accents, (ww*0.45, hh*0.2), hh*0.28, color, color2, light, dark, border_w)
            elif config.P_SHIP_IDX == 2:
                body = [(0, hh*0.66), (0, hh*0.34), (ww*0.2, hh*0.2), (ww*0.5, hh*0.16), (ww*0.75, hh*0.28), (ww, hh*0.5),
                        (ww*0.75, hh*0.62), (ww*0.5, hh*0.7), (ww*0.2, hh*0.68)]
                dark_p = [(ww*0.2, hh*0.5), (ww*0.2, hh*0.68), (ww*0.5, hh*0.7), (ww*0.75, hh*0.62), (ww, hh*0.5), (ww*0.5, hh*0.5)]
                light_p = [(ww*0.2, hh*0.2), (ww*0.5, hh*0.16), (ww*0.75, hh*0.28), (ww*0.5, hh*0.42), (ww*0.2, hh*0.4)]
                accents = [
                    ([(0, hh*0.34), (ww*0.1, hh*0.22), (ww*0.14, hh*0.36)], color2),
                    ([(0, hh*0.66), (ww*0.1, hh*0.78), (ww*0.14, hh*0.64)], color2),
                ]
                self._draw_ship_variant(ship_surf, body, dark_p, light_p, accents, (ww*0.4, hh*0.14), hh*0.3, color, color2, light, dark, border_w)
            elif config.P_SHIP_IDX == 3:
                body = [(0, hh*0.58), (0, hh*0.42), (ww*0.2, hh*0.36), (ww*0.55, hh*0.24), (ww, hh*0.5),
                        (ww*0.55, hh*0.6), (ww*0.2, hh*0.62)]
                dark_p = [(ww*0.2, hh*0.5), (ww*0.2, hh*0.62), (ww*0.55, hh*0.6), (ww, hh*0.5), (ww*0.55, hh*0.5)]
                light_p = [(ww*0.2, hh*0.36), (ww*0.55, hh*0.24), (ww, hh*0.5), (ww*0.55, hh*0.42), (ww*0.2, hh*0.44)]
                accents = [
                    ([(0, hh*0.42), (ww*0.1, hh*0.32), (ww*0.13, hh*0.42)], color2),
                    ([(0, hh*0.58), (ww*0.1, hh*0.68), (ww*0.13, hh*0.58)], color2),
                    ([(ww*0.13, hh*0.58), (ww*0.2, hh*0.62), (ww*0.2, hh*0.5)], color2),
                ]
                self._draw_ship_variant(ship_surf, body, dark_p, light_p, accents, (ww*0.35, hh*0.18), hh*0.3, color, color2, light, dark, border_w)
            elif config.P_SHIP_IDX == 4:
                body = [(0, hh*0.54), (0, hh*0.46), (ww*0.35, hh*0.42), (ww, hh*0.5), (ww*0.35, hh*0.58)]
                dark_p = [(ww*0.1, hh*0.5), (ww*0.35, hh*0.58), (ww, hh*0.5), (ww*0.35, hh*0.5)]
                light_p = [(ww*0.1, hh*0.46), (ww*0.35, hh*0.42), (ww, hh*0.5), (ww*0.35, hh*0.5)]
                accents = [
                    ([(0, hh*0.46), (ww*0.1, hh*0.36), (ww*0.13, hh*0.46)], color2),
                    ([(0, hh*0.54), (ww*0.1, hh*0.64), (ww*0.13, hh*0.54)], color2),
                ]
                self._draw_ship_variant(ship_surf, body, dark_p, light_p, accents, None, 0, color, color2, light, dark, border_w)
                pygame.draw.circle(ship_surf, config.CYAN, (int(ww*0.4), int(hh*0.32)), int(ww*0.15))
                pygame.draw.circle(ship_surf, light, (int(ww*0.35), int(hh*0.27)), max(2, int(ww*0.045)))
                pygame.draw.circle(ship_surf, color2, (int(ww*0.4), int(hh*0.32)), int(ww*0.15), border_w)
                self._draw_mini_rider(ship_surf, ww*0.4, hh*0.14, hh*0.22, color, color2)
            elif config.P_SHIP_IDX == 5:
                body = [(0, hh*0.62), (0, hh*0.4), (ww*0.25, hh*0.34), (ww*0.5, hh*0.06), (ww*0.55, hh*0.4), (ww, hh*0.5),
                        (ww*0.55, hh*0.6), (ww*0.25, hh*0.62)]
                dark_p = [(ww*0.25, hh*0.5), (ww*0.25, hh*0.62), (ww*0.55, hh*0.6), (ww, hh*0.5), (ww*0.55, hh*0.5)]
                light_p = [(ww*0.5, hh*0.06), (ww*0.55, hh*0.4), (ww*0.4, hh*0.4)]
                accents = [
                    ([(0, hh*0.4), (ww*0.1, hh*0.3), (ww*0.13, hh*0.4)], color2),
                    ([(0, hh*0.62), (ww*0.1, hh*0.72), (ww*0.13, hh*0.62)], color2),
                ]
                self._draw_ship_variant(ship_surf, body, dark_p, light_p, accents, (ww*0.16, hh*0.24), hh*0.26, color, color2, light, dark, border_w)
            elif config.P_SHIP_IDX == 6:
                body = [(0, hh*0.6), (0, hh*0.4), (ww*0.2, hh*0.32), (ww*0.35, hh*0.36), (ww*0.42, hh*0.24), (ww*0.5, hh*0.36),
                        (ww*0.62, hh*0.36), (ww, hh*0.5), (ww*0.62, hh*0.64), (ww*0.35, hh*0.6), (ww*0.2, hh*0.62)]
                dark_p = [(ww*0.2, hh*0.5), (ww*0.2, hh*0.62), (ww*0.35, hh*0.6), (ww*0.62, hh*0.64), (ww, hh*0.5), (ww*0.5, hh*0.5)]
                light_p = [(ww*0.2, hh*0.32), (ww*0.35, hh*0.36), (ww*0.42, hh*0.24), (ww*0.5, hh*0.36), (ww*0.62, hh*0.36), (ww*0.5, hh*0.46), (ww*0.2, hh*0.46)]
                teeth = [(ww*0.46, hh*0.36), (ww*0.5, hh*0.3), (ww*0.5, hh*0.4)], [(ww*0.55, hh*0.37), (ww*0.59, hh*0.32), (ww*0.59, hh*0.42)]
                accents = [
                    ([(0, hh*0.4), (ww*0.08, hh*0.3), (ww*0.1, hh*0.4)], color2),
                    ([(0, hh*0.6), (ww*0.08, hh*0.7), (ww*0.1, hh*0.6)], color2),
                    (teeth[0], config.WHITE),
                    (teeth[1], config.WHITE),
                ]
                self._draw_ship_variant(ship_surf, body, dark_p, light_p, accents, (ww*0.22, hh*0.18), hh*0.26, color, color2, light, dark, border_w)
            elif config.P_SHIP_IDX == 7:
                body = [(0, hh*0.56), (0, hh*0.44), (ww*0.3, hh*0.4), (ww*0.55, hh*0.44), (ww*0.8, hh*0.4), (ww, hh*0.5),
                        (ww*0.8, hh*0.6), (ww*0.55, hh*0.56), (ww*0.3, hh*0.6)]
                dark_p = [(ww*0.3, hh*0.5), (ww*0.3, hh*0.6), (ww*0.55, hh*0.56), (ww*0.8, hh*0.6), (ww, hh*0.5), (ww*0.8, hh*0.5)]
                light_p = [(ww*0.3, hh*0.4), (ww*0.55, hh*0.44), (ww*0.8, hh*0.4), (ww*0.55, hh*0.48), (ww*0.3, hh*0.48)]
                spikes = [
                    ([(ww*0.32, hh*0.4), (ww*0.38, hh*0.26), (ww*0.42, hh*0.4)], color2),
                    ([(ww*0.5, hh*0.42), (ww*0.56, hh*0.26), (ww*0.6, hh*0.42)], color2),
                    ([(ww*0.68, hh*0.4), (ww*0.74, hh*0.24), (ww*0.78, hh*0.4)], color2),
                    ([(0, hh*0.44), (ww*0.1, hh*0.34), (ww*0.12, hh*0.44)], color2),
                    ([(0, hh*0.56), (ww*0.1, hh*0.66), (ww*0.12, hh*0.56)], color2),
                ]
                self._draw_ship_variant(ship_surf, body, dark_p, light_p, spikes, (ww*0.16, hh*0.26), hh*0.26, color, color2, light, dark, border_w)

            self._outline_and_blit(surface, ship_surf, (draw_x + w//2, draw_y + h//2), outline_offset, flip_v=(self.gravity_dir == -1))

        elif self.mode == "ufo":
            w_draw = max(1, int(32 * z_scale))
            h_draw = max(1, int(24 * z_scale))
            ufo_surf = pygame.Surface((w_draw, h_draw), pygame.SRCALPHA)

            if config.P_UFO_IDX == 1:
                pygame.draw.ellipse(ufo_surf, color, (-w_draw*0.05, h_draw*0.45, w_draw*1.1, h_draw*0.4))
                pygame.draw.ellipse(ufo_surf, light, (w_draw*0.05, h_draw*0.48, w_draw*0.3, h_draw*0.12))
                pygame.draw.ellipse(ufo_surf, color2, (-w_draw*0.05, h_draw*0.45, w_draw*1.1, h_draw*0.4), border_w)
                pygame.draw.ellipse(ufo_surf, config.CYAN, (w_draw*0.32, h_draw*0.08, w_draw*0.36, h_draw*0.42))
                pygame.draw.ellipse(ufo_surf, config.WHITE, (w_draw*0.32, h_draw*0.08, w_draw*0.36, h_draw*0.42), border_w)
                for i in range(5):
                    lx = w_draw * (0.1 + 0.2*i)
                    pygame.draw.circle(ufo_surf, color2, (int(lx), int(h_draw*0.72)), max(1, int(border_w*0.7)))
            elif config.P_UFO_IDX == 2:
                pts = [(w_draw*0.5, h_draw*0.38), (w_draw*0.85, h_draw*0.55), (w_draw*0.5, h_draw*0.85), (w_draw*0.15, h_draw*0.55)]
                pygame.draw.polygon(ufo_surf, color, pts)
                pygame.draw.polygon(ufo_surf, color2, pts, border_w)
                pygame.draw.polygon(ufo_surf, color2, [(0, h_draw*0.55), (w_draw*0.18, h_draw*0.48), (w_draw*0.18, h_draw*0.62)])
                pygame.draw.polygon(ufo_surf, color2, [(w_draw, h_draw*0.55), (w_draw*0.82, h_draw*0.48), (w_draw*0.82, h_draw*0.62)])
                pygame.draw.circle(ufo_surf, config.CYAN, (int(w_draw*0.5), int(h_draw*0.45)), int(w_draw*0.14))
                pygame.draw.circle(ufo_surf, config.WHITE, (int(w_draw*0.5), int(h_draw*0.45)), int(w_draw*0.14), border_w)
            elif config.P_UFO_IDX == 3:
                pygame.draw.ellipse(ufo_surf, color2, (w_draw*0.1, h_draw*0.3, w_draw*0.8, h_draw*0.28))
                pygame.draw.ellipse(ufo_surf, color, (0, h_draw*0.5, w_draw, h_draw*0.42))
                pygame.draw.ellipse(ufo_surf, light, (w_draw*0.1, h_draw*0.54, w_draw*0.24, h_draw*0.12))
                pygame.draw.ellipse(ufo_surf, color2, (0, h_draw*0.5, w_draw, h_draw*0.42), border_w)
                pygame.draw.line(ufo_surf, color2, (w_draw*0.5, h_draw*0.3), (w_draw*0.5, h_draw*0.02), border_w)
                pygame.draw.circle(ufo_surf, config.CYAN, (int(w_draw*0.5), int(h_draw*0.02)), max(2, int(w_draw*0.06)))
            elif config.P_UFO_IDX == 4:
                pygame.draw.ellipse(ufo_surf, color, (w_draw*0.05, h_draw*0.62, w_draw*0.9, h_draw*0.3))
                pygame.draw.ellipse(ufo_surf, color2, (w_draw*0.05, h_draw*0.62, w_draw*0.9, h_draw*0.3), border_w)
                pygame.draw.ellipse(ufo_surf, config.CYAN, (w_draw*0.06, 0, w_draw*0.88, h_draw*0.82))
                pygame.draw.ellipse(ufo_surf, light, (w_draw*0.18, h_draw*0.08, w_draw*0.3, h_draw*0.2))
                pygame.draw.ellipse(ufo_surf, config.WHITE, (w_draw*0.06, 0, w_draw*0.88, h_draw*0.82), border_w)
            elif config.P_UFO_IDX == 5:
                pts = [(0, h_draw*0.6), (w_draw*0.2, h_draw*0.42), (w_draw*0.8, h_draw*0.42), (w_draw, h_draw*0.6), (w_draw*0.8, h_draw*0.78), (w_draw*0.2, h_draw*0.78)]
                pygame.draw.polygon(ufo_surf, color, pts)
                pygame.draw.ellipse(ufo_surf, light, (w_draw*0.14, h_draw*0.46, w_draw*0.22, h_draw*0.1))
                pygame.draw.polygon(ufo_surf, color2, pts, border_w)
                pygame.draw.polygon(ufo_surf, config.CYAN, [(w_draw*0.36, h_draw*0.42), (w_draw*0.64, h_draw*0.42), (w_draw*0.5, h_draw*0.1)])
                pygame.draw.polygon(ufo_surf, config.WHITE, [(w_draw*0.36, h_draw*0.42), (w_draw*0.64, h_draw*0.42), (w_draw*0.5, h_draw*0.1)], border_w)
            elif config.P_UFO_IDX == 6:
                pygame.draw.ellipse(ufo_surf, color, (w_draw*0.15, h_draw*0.4, w_draw*0.7, h_draw*0.4))
                pygame.draw.ellipse(ufo_surf, light, (w_draw*0.2, h_draw*0.44, w_draw*0.2, h_draw*0.12))
                pygame.draw.ellipse(ufo_surf, color2, (w_draw*0.15, h_draw*0.4, w_draw*0.7, h_draw*0.4), border_w)
                pygame.draw.polygon(ufo_surf, color2, [(w_draw*0.15, h_draw*0.5), (0, h_draw*0.35), (0, h_draw*0.65)])
                pygame.draw.polygon(ufo_surf, color2, [(w_draw*0.85, h_draw*0.5), (w_draw, h_draw*0.35), (w_draw, h_draw*0.65)])
                pygame.draw.circle(ufo_surf, config.CYAN, (int(w_draw*0.5), int(h_draw*0.32)), int(w_draw*0.16))
                pygame.draw.circle(ufo_surf, config.WHITE, (int(w_draw*0.5), int(h_draw*0.32)), int(w_draw*0.16), border_w)
            elif config.P_UFO_IDX == 7:
                pygame.draw.ellipse(ufo_surf, color, (0, h_draw*0.5, w_draw, h_draw*0.4))
                pygame.draw.ellipse(ufo_surf, light, (w_draw*0.1, h_draw*0.54, w_draw*0.24, h_draw*0.12))
                pygame.draw.ellipse(ufo_surf, color2, (0, h_draw*0.5, w_draw, h_draw*0.4), border_w)
                pygame.draw.ellipse(ufo_surf, config.CYAN, (w_draw*0.3, h_draw*0.22, w_draw*0.4, h_draw*0.34))
                pygame.draw.ellipse(ufo_surf, config.WHITE, (w_draw*0.3, h_draw*0.22, w_draw*0.4, h_draw*0.34), border_w)
                pygame.draw.line(ufo_surf, color2, (w_draw*0.5, h_draw*0.22), (w_draw*0.5, 0), border_w)
                pygame.draw.circle(ufo_surf, color2, (int(w_draw*0.5), 0), max(2, int(w_draw*0.05)))
            else:
                # Dome (top half)
                pygame.draw.ellipse(ufo_surf, config.CYAN, (w_draw*0.2, 0, w_draw*0.6, h_draw*0.8))
                pygame.draw.ellipse(ufo_surf, config.WHITE, (w_draw*0.2, 0, w_draw*0.6, h_draw*0.8), border_w)

                # Saucer (bottom half)
                pygame.draw.ellipse(ufo_surf, color, (0, h_draw*0.4, w_draw, h_draw*0.6))
                pygame.draw.ellipse(ufo_surf, light, (w_draw*0.08, h_draw*0.44, w_draw*0.28, h_draw*0.16))
                pygame.draw.ellipse(ufo_surf, color2, (0, h_draw*0.4, w_draw, h_draw*0.6), border_w)

                # Details (lights)
                pygame.draw.circle(ufo_surf, color2, (int(w_draw*0.2), int(h_draw*0.7)), border_w)
                pygame.draw.circle(ufo_surf, color2, (int(w_draw*0.5), int(h_draw*0.75)), border_w)
                pygame.draw.circle(ufo_surf, color2, (int(w_draw*0.8), int(h_draw*0.7)), border_w)

            self._outline_and_blit(surface, ufo_surf, (draw_x + w//2, draw_y + h//2), outline_offset, flip_v=(self.gravity_dir == -1))

        elif self.mode == "wave":
            ww = max(1, int(40 * z_scale))
            wh = max(1, int(40 * z_scale))
            wave_surf = pygame.Surface((ww, wh), pygame.SRCALPHA)
            
            if config.P_WAVE_IDX == 0:
                pts = [(0, wh//4), (ww, wh//2), (0, 3*wh//4)]
                pygame.draw.polygon(wave_surf, color, pts)
                pygame.draw.polygon(wave_surf, light, [(ww*0.06, wh*0.36), (ww*0.3, wh*0.44), (ww*0.06, wh*0.5)])
                pygame.draw.polygon(wave_surf, color2, pts, border_w)
                pygame.draw.polygon(wave_surf, config.BLACK, [(ww*0.2, wh*0.4), (ww*0.6, wh//2), (ww*0.2, wh*0.6)])
            elif config.P_WAVE_IDX == 1:
                pts = [(0, wh//5), (ww, wh//2), (0, 4*wh//5), (ww//3, wh//2)]
                pygame.draw.polygon(wave_surf, color, pts)
                pygame.draw.polygon(wave_surf, light, [(ww*0.05, wh*0.28), (ww*0.24, wh*0.4), (ww*0.05, wh*0.46)])
                pygame.draw.polygon(wave_surf, color2, pts, border_w)
            elif config.P_WAVE_IDX == 2:
                pts = [(0, wh//4), (ww//2, wh//2), (0, 3*wh//4)]
                pts2 = [(ww//2, wh//4), (ww, wh//2), (ww//2, 3*wh//4)]
                pygame.draw.polygon(wave_surf, color, pts)
                pygame.draw.polygon(wave_surf, light, [(ww*0.04, wh*0.34), (ww*0.2, wh*0.42), (ww*0.04, wh*0.5)])
                pygame.draw.polygon(wave_surf, color2, pts, border_w)
                pygame.draw.polygon(wave_surf, color2, pts2)
            elif config.P_WAVE_IDX == 3:
                pts = [(ww//4, wh//4), (ww, wh//2), (ww//4, 3*wh//4), (0, wh//2)]
                pygame.draw.polygon(wave_surf, color, pts)
                pygame.draw.polygon(wave_surf, light, [(ww*0.28, wh*0.34), (ww*0.5, wh*0.42), (ww*0.28, wh*0.48)])
                pygame.draw.polygon(wave_surf, color2, pts, border_w)
                pygame.draw.polygon(wave_surf, config.BLACK, [(ww*0.3, wh*0.4), (ww*0.7, wh//2), (ww*0.3, wh*0.6), (ww*0.15, wh//2)])
            elif config.P_WAVE_IDX == 4:
                pts = [(0, 0), (ww, wh//2), (0, wh), (ww//4, wh//2)]
                pygame.draw.polygon(wave_surf, color, pts)
                pygame.draw.polygon(wave_surf, light, [(ww*0.08, wh*0.14), (ww*0.32, wh*0.28), (ww*0.1, wh*0.32)])
                pygame.draw.polygon(wave_surf, color2, pts, border_w)
                pygame.draw.line(wave_surf, config.BLACK, (ww*0.1, wh*0.3), (ww*0.7, wh*0.5), border_w)
                pygame.draw.line(wave_surf, config.BLACK, (ww*0.1, wh*0.7), (ww*0.7, wh*0.5), border_w)
            elif config.P_WAVE_IDX == 5:
                pts = [(0, wh//3), (ww//3, wh//3), (ww, wh//2), (ww//3, 2*wh//3), (0, 2*wh//3)]
                pygame.draw.polygon(wave_surf, color, pts)
                pygame.draw.polygon(wave_surf, light, [(ww*0.06, wh*0.36), (ww*0.26, wh*0.4), (ww*0.06, wh*0.46)])
                pygame.draw.polygon(wave_surf, color2, pts, border_w)
                pygame.draw.rect(wave_surf, config.BLACK, (ww*0.1, wh*0.4, ww*0.1, wh*0.2))
            elif config.P_WAVE_IDX == 6:
                pts = [(0, wh*0.2), (ww*0.6, wh*0.4), (ww*0.4, wh*0.5), (ww, wh*0.5), (ww*0.4, wh*0.6), (ww*0.6, wh*0.7), (0, wh*0.8)]
                pygame.draw.polygon(wave_surf, color, pts)
                pygame.draw.polygon(wave_surf, light, [(ww*0.06, wh*0.3), (ww*0.28, wh*0.4), (ww*0.06, wh*0.46)])
                pygame.draw.polygon(wave_surf, color2, pts, border_w)
                pygame.draw.circle(wave_surf, config.CYAN, (ww//2, wh//2), int(ww*0.1))
            elif config.P_WAVE_IDX == 7:
                pygame.draw.line(wave_surf, color2, (0, wh//2), (ww, wh//2), max(1, int(4*z_scale)))
                pygame.draw.line(wave_surf, color2, (ww*0.5, wh*0.2), (ww*0.8, wh*0.5), max(1, int(4*z_scale)))
                pygame.draw.line(wave_surf, color2, (ww*0.5, wh*0.8), (ww*0.8, wh*0.5), max(1, int(4*z_scale)))
                pygame.draw.polygon(wave_surf, color, [(0, wh*0.4), (ww*0.3, wh//2), (0, wh*0.6)])
                pygame.draw.polygon(wave_surf, light, [(ww*0.04, wh*0.44), (ww*0.14, wh*0.5), (ww*0.04, wh*0.54)])

            center = (draw_x + int(12 * z_scale), draw_y + int(12 * z_scale))
            self._outline_and_blit(surface, wave_surf, center, outline_offset)

        else: # Cube
            cube_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            radius = max(2, int(w * 0.12))
            pygame.draw.rect(cube_surf, color, (0, 0, w, h), border_radius=radius)
            pygame.draw.rect(cube_surf, light, (int(w*0.1), int(h*0.1), int(w*0.32), int(h*0.2)), border_radius=max(1, int(w*0.06)))
            pygame.draw.rect(cube_surf, color2, (0, 0, w, h), border_w, border_radius=radius)

            if config.P_CUBE_IDX == 0:
                eye_y = int(8 * z_scale) if self.gravity_dir == 1 else int(h - int(18 * z_scale))
                pygame.draw.rect(cube_surf, config.BLACK, (int(w*0.25), eye_y, int(w*0.15), int(h*0.15)))
                pygame.draw.rect(cube_surf, config.BLACK, (int(w*0.6), eye_y, int(w*0.15), int(h*0.15)))
                pygame.draw.polygon(cube_surf, color2, [(int(w*0.25), eye_y), (int(w*0.4), eye_y), (int(w*0.32), eye_y + int(h*0.05))])
                pygame.draw.polygon(cube_surf, color2, [(int(w*0.6), eye_y), (int(w*0.75), eye_y), (int(w*0.67), eye_y + int(h*0.05))])
                mouth_y = int(24 * z_scale) if self.gravity_dir == 1 else int(8 * z_scale)
                pygame.draw.rect(cube_surf, config.BLACK, (int(w*0.35), mouth_y, int(w*0.3), int(h*0.05)))
            elif config.P_CUBE_IDX == 1:
                pygame.draw.rect(cube_surf, color2, (int(w*0.2), int(h*0.2), int(w*0.6), int(h*0.6)), max(1, int(3*z_scale)))
                pygame.draw.circle(cube_surf, color2, (w//2, h//2), int(w*0.15))
                pygame.draw.rect(cube_surf, config.BLACK, (int(w*0.4), int(h*0.4), int(w*0.2), int(h*0.2)))
            elif config.P_CUBE_IDX == 2:
                pygame.draw.rect(cube_surf, config.BLACK, (int(w*0.1), int(h*0.1), int(w*0.8), int(h*0.8)))
                eye_y = int(12 * z_scale) if self.gravity_dir == 1 else int(h - int(18 * z_scale))
                pygame.draw.rect(cube_surf, config.CYAN, (int(w*0.25), eye_y, int(w*0.2), int(h*0.1)))
                pygame.draw.rect(cube_surf, config.CYAN, (int(w*0.55), eye_y, int(w*0.2), int(h*0.1)))
                pygame.draw.line(cube_surf, color2, (int(w*0.3), h//2), (int(w*0.7), h//2), border_w)
            elif config.P_CUBE_IDX == 3:
                pygame.draw.rect(cube_surf, config.BLACK, (int(w*0.2), int(h*0.2), int(w*0.6), int(h*0.6)))
                pygame.draw.polygon(cube_surf, color2, [(w//2, int(h*0.25)), (int(w*0.75), h//2), (w//2, int(h*0.75)), (int(w*0.25), h//2)], max(1, int(3*z_scale)))
                pygame.draw.circle(cube_surf, color, (w//2, h//2), int(w*0.1))
            elif config.P_CUBE_IDX == 4:
                pygame.draw.line(cube_surf, color2, (w//2, 0), (w//2, h), max(1, int(4*z_scale)))
                pygame.draw.line(cube_surf, color2, (0, h//2), (w, h//2), max(1, int(4*z_scale)))
                pygame.draw.rect(cube_surf, config.BLACK, (int(w*0.35), int(h*0.35), int(w*0.3), int(h*0.3)))
                pygame.draw.circle(cube_surf, color, (w//2, h//2), int(w*0.08))
            elif config.P_CUBE_IDX == 5:
                pygame.draw.rect(cube_surf, config.BLACK, (0, int(h*0.3), w, int(h*0.4)))
                pygame.draw.circle(cube_surf, color2, (int(w*0.3), h//2), int(w*0.1))
                pygame.draw.circle(cube_surf, color2, (int(w*0.7), h//2), int(w*0.1))
                pygame.draw.circle(cube_surf, config.BLACK, (int(w*0.3), h//2), int(w*0.04))
                pygame.draw.circle(cube_surf, config.BLACK, (int(w*0.7), h//2), int(w*0.04))
            elif config.P_CUBE_IDX == 6:
                eye_y = int(12 * z_scale) if self.gravity_dir == 1 else int(h - int(24 * z_scale))
                pygame.draw.rect(cube_surf, config.BLACK, (int(w*0.2), eye_y, int(w*0.2), int(h*0.1)))
                pygame.draw.rect(cube_surf, config.BLACK, (int(w*0.6), eye_y, int(w*0.2), int(h*0.1)))
                pygame.draw.polygon(cube_surf, color2, [(int(w*0.15), eye_y - int(h*0.1)), (int(w*0.45), eye_y + int(h*0.05)), (int(w*0.15), eye_y)])
                pygame.draw.polygon(cube_surf, color2, [(int(w*0.85), eye_y - int(h*0.1)), (int(w*0.55), eye_y + int(h*0.05)), (int(w*0.85), eye_y)])
                mouth_y = int(24 * z_scale) if self.gravity_dir == 1 else int(12 * z_scale)
                pygame.draw.rect(cube_surf, config.BLACK, (int(w*0.35), mouth_y, int(w*0.3), int(h*0.2)))
                pygame.draw.rect(cube_surf, config.WHITE, (int(w*0.4), mouth_y, int(w*0.08), int(h*0.08)))
                pygame.draw.rect(cube_surf, config.WHITE, (int(w*0.52), mouth_y, int(w*0.08), int(h*0.08)))
            elif config.P_CUBE_IDX == 7:
                pygame.draw.rect(cube_surf, color2, (int(w*0.2), int(h*0.2), int(w*0.6), int(h*0.6)), max(1, int(3*z_scale)))
                pygame.draw.rect(cube_surf, color, (int(w*0.35), int(h*0.35), int(w*0.3), int(h*0.3)))
                pygame.draw.line(cube_surf, color2, (0, 0), (int(w*0.2), int(h*0.2)), max(1, int(3*z_scale)))
                pygame.draw.line(cube_surf, color2, (w, 0), (int(w*0.8), int(h*0.2)), max(1, int(3*z_scale)))
                pygame.draw.line(cube_surf, color2, (0, h), (int(w*0.2), int(h*0.8)), max(1, int(3*z_scale)))
                pygame.draw.line(cube_surf, color2, (w, h), (int(w*0.8), int(h*0.8)), max(1, int(3*z_scale)))

            self._outline_and_blit(surface, cube_surf, (draw_x + w//2, draw_y + h//2), outline_offset)