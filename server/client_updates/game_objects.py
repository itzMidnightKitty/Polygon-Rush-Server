import pygame
import math
import config

def sort_for_draw(objects):
    """Layer 0 draws last (on top); higher layers draw first (further back).
    Stable sort keeps relative insertion order within the same layer."""
    return sorted(objects, key=lambda o: getattr(o, 'layer', 0), reverse=True)

TILEABLE_TYPES = (config.OBJ_BLOCK, config.OBJ_HALF_BLOCK, config.OBJ_BLOCK_FADED, config.OBJ_BLOCK_BRICK,
                   config.OBJ_BLOCK_GRID, config.OBJ_BLOCK_BEVEL, config.OBJ_BLOCK_DOTS, config.OBJ_BLOCK_STRIPES,
                   config.OBJ_BLOCK_CROSS, config.OBJ_BLOCK_CIRCLE,
                   config.OBJ_OUTLINE_LINE, config.OBJ_OUTLINE_CORNER_PIXEL, config.OBJ_OUTLINE_3SIDE,
                   config.OBJ_OUTLINE_OPPOSITE, config.OBJ_OUTLINE_CORNER2)

class GameObject:
    def __init__(self, type, x, y, rotation=0, color_idx=0, flip_x=False, flip_y=False, bpm=60, layer=0, **kwargs):
        self.type = type
        self.x = x
        self.y = y
        self.rotation = rotation
        self.color_idx = color_idx
        self.flip_x = flip_x
        self.flip_y = flip_y
        self.bpm = bpm
        self.layer = max(0, min(config.MAX_LAYERS - 1, layer))

        self.rect = pygame.Rect(self.x, self.y, config.GRID_SIZE, config.GRID_SIZE)
        self.update_rect()

    def is_solid(self):
        # Only Half Block and the outline pieces collide -- the rest of the
        # Blocks category is decorative fill, meant to sit behind an outline
        # piece rather than provide its own collision.
        return self.type in (config.OBJ_HALF_BLOCK, config.OBJ_OUTLINE_LINE, config.OBJ_OUTLINE_CORNER_PIXEL,
                              config.OBJ_OUTLINE_3SIDE, config.OBJ_OUTLINE_OPPOSITE, config.OBJ_OUTLINE_CORNER2)

    def is_deadly(self):
        return self.type in (config.OBJ_SPIKE, config.OBJ_HALF_SPIKE, config.OBJ_GROUND_SPIKE, config.OBJ_SAW, config.OBJ_SAW_2, config.OBJ_SAW_3)

    def to_dict(self):
        d = {"type": self.type, "x": self.x, "y": self.y, "rotation": self.rotation, "color_idx": self.color_idx, "flip_x": self.flip_x, "flip_y": self.flip_y, "bpm": self.bpm, "layer": self.layer}
        return d

    def update_rect(self):
        w, h = config.GRID_SIZE, config.GRID_SIZE
        ox, oy = self.x, self.y

        if self.type == config.OBJ_HALF_BLOCK:
            w, h = config.GRID_SIZE, config.GRID_SIZE // 2
            if self.rotation == 90: ox, oy, w, h = self.x + config.GRID_SIZE//2, self.y, config.GRID_SIZE//2, config.GRID_SIZE
            elif self.rotation == 180: ox, oy, w, h = self.x, self.y, config.GRID_SIZE, config.GRID_SIZE//2
            elif self.rotation == 270: ox, oy, w, h = self.x, self.y, config.GRID_SIZE//2, config.GRID_SIZE
            else: oy = self.y + config.GRID_SIZE // 2
        elif self.type == config.OBJ_OUTLINE_LINE:
            t = 10
            if self.rotation == 90: ox, oy, w, h = self.x + config.GRID_SIZE - t, self.y, t, config.GRID_SIZE
            elif self.rotation == 180: ox, oy, w, h = self.x, self.y + config.GRID_SIZE - t, config.GRID_SIZE, t
            elif self.rotation == 270: ox, oy, w, h = self.x, self.y, t, config.GRID_SIZE
            else: ox, oy, w, h = self.x, self.y, config.GRID_SIZE, t
        elif self.type == config.OBJ_OUTLINE_CORNER_PIXEL:
            t = 10
            if self.rotation == 90: ox, oy, w, h = self.x + config.GRID_SIZE - t, self.y, t, t
            elif self.rotation == 180: ox, oy, w, h = self.x + config.GRID_SIZE - t, self.y + config.GRID_SIZE - t, t, t
            elif self.rotation == 270: ox, oy, w, h = self.x, self.y + config.GRID_SIZE - t, t, t
            else: ox, oy, w, h = self.x, self.y, t, t
        elif self.type == config.OBJ_SPIKE:
            if self.rotation == 0: ox, oy, w, h = self.x + 6, self.y + 10, config.GRID_SIZE - 12, config.GRID_SIZE - 10
            elif self.rotation == 90: ox, oy, w, h = self.x, self.y + 6, config.GRID_SIZE - 10, config.GRID_SIZE - 12
            elif self.rotation == 180: ox, oy, w, h = self.x + 6, self.y, config.GRID_SIZE - 12, config.GRID_SIZE - 10
            elif self.rotation == 270: ox, oy, w, h = self.x + 10, self.y + 6, config.GRID_SIZE - 10, config.GRID_SIZE - 12
        elif self.type == config.OBJ_HALF_SPIKE:
            if self.rotation == 0: ox, oy, w, h = self.x + 6, self.y + config.GRID_SIZE//2 + 4, config.GRID_SIZE - 12, config.GRID_SIZE//2 - 4
            elif self.rotation == 90: ox, oy, w, h = self.x, self.y + 6, config.GRID_SIZE//2 - 4, config.GRID_SIZE - 12
            elif self.rotation == 180: ox, oy, w, h = self.x + 6, self.y, config.GRID_SIZE - 12, config.GRID_SIZE//2 - 4
            elif self.rotation == 270: ox, oy, w, h = self.x + config.GRID_SIZE//2 + 4, self.y + 6, config.GRID_SIZE//2 - 4, config.GRID_SIZE - 12
        elif self.type == config.OBJ_GROUND_SPIKE:
            if self.rotation == 0: ox, oy, w, h = self.x, self.y + config.GRID_SIZE//2, config.GRID_SIZE, config.GRID_SIZE//2
            elif self.rotation == 90: ox, oy, w, h = self.x, self.y, config.GRID_SIZE//2, config.GRID_SIZE
            elif self.rotation == 180: ox, oy, w, h = self.x, self.y, config.GRID_SIZE, config.GRID_SIZE//2
            elif self.rotation == 270: ox, oy, w, h = self.x + config.GRID_SIZE//2, self.y, config.GRID_SIZE//2, config.GRID_SIZE
        elif self.type in (config.OBJ_PORTAL_CUBE, config.OBJ_PORTAL_SHIP, config.OBJ_PORTAL_BALL, config.OBJ_PORTAL_UFO, config.OBJ_PORTAL_WAVE, config.OBJ_PORTAL_GRAV_DOWN, config.OBJ_PORTAL_GRAV_UP):
            ox, oy, w, h = self.x, self.y - config.GRID_SIZE, config.GRID_SIZE, config.GRID_SIZE * 3
        elif self.type in (config.OBJ_PAD_YELLOW, config.OBJ_PAD_BLUE, config.OBJ_PAD_PURPLE):
            if self.rotation == 0: ox, oy, w, h = self.x, self.y + config.GRID_SIZE - 12, config.GRID_SIZE, 12
            elif self.rotation == 90: ox, oy, w, h = self.x, self.y, 12, config.GRID_SIZE
            elif self.rotation == 180: ox, oy, w, h = self.x, self.y, config.GRID_SIZE, 12
            elif self.rotation == 270: ox, oy, w, h = self.x + config.GRID_SIZE - 12, self.y, 12, config.GRID_SIZE
            else: ox, oy, w, h = self.x, self.y + config.GRID_SIZE - 12, config.GRID_SIZE, 12
        elif self.type in (config.OBJ_ORB_YELLOW, config.OBJ_ORB_BLUE, config.OBJ_ORB_PURPLE):
            ox, oy, w, h = self.x - 10, self.y - 10, config.GRID_SIZE + 20, config.GRID_SIZE + 20
        elif self.type == config.OBJ_PULSEROD_1:
            ox, oy, w, h = self.x, self.y, config.GRID_SIZE, config.GRID_SIZE
        elif self.type == config.OBJ_PULSEROD_2:
            ox, oy, w, h = self.x, self.y - config.GRID_SIZE, config.GRID_SIZE, config.GRID_SIZE * 2
        elif self.type == config.OBJ_PULSEROD_3:
            ox, oy, w, h = self.x, self.y - config.GRID_SIZE * 2, config.GRID_SIZE, config.GRID_SIZE * 3
        elif self.type == config.OBJ_SAW:
            rad = config.GRID_SIZE
            ox, oy = (self.x + config.GRID_SIZE//2) - rad, (self.y + config.GRID_SIZE//2) - rad
            self.rect = pygame.Rect(ox + 8, oy + 8, (rad * 2) - 16, (rad * 2) - 16)
            return
        elif self.type == config.OBJ_SAW_2:
            rad = int(config.GRID_SIZE * 0.75)
            ox, oy = (self.x + config.GRID_SIZE//2) - rad, (self.y + config.GRID_SIZE//2) - rad
            self.rect = pygame.Rect(ox + 6, oy + 6, (rad * 2) - 12, (rad * 2) - 12)
            return
        elif self.type == config.OBJ_SAW_3:
            rad = int(config.GRID_SIZE * 1.5)
            ox, oy = (self.x + config.GRID_SIZE//2) - rad, (self.y + config.GRID_SIZE//2) - rad
            self.rect = pygame.Rect(ox + 12, oy + 12, (rad * 2) - 24, (rad * 2) - 24)
            return
        elif self.type == config.OBJ_GEAR_L:
            ox, oy, w, h = self.x, self.y - config.GRID_SIZE, config.GRID_SIZE*2, config.GRID_SIZE*2
        elif self.type == config.OBJ_GEAR_M:
            ox, oy, w, h = self.x, self.y - config.GRID_SIZE//2, int(config.GRID_SIZE*1.5), int(config.GRID_SIZE*1.5)
        elif self.type == config.OBJ_GEAR_S:
            ox, oy, w, h = self.x, self.y, config.GRID_SIZE, config.GRID_SIZE
        elif self.type == config.OBJ_CLOUD_1:
            ox, oy, w, h = self.x, self.y, config.GRID_SIZE*2, config.GRID_SIZE
        elif self.type == config.OBJ_CLOUD_2:
            ox, oy, w, h = self.x, self.y, int(config.GRID_SIZE*1.5), config.GRID_SIZE
        elif self.type == config.OBJ_DECO_CHAIN:
            ox, oy, w, h = self.x, self.y, config.GRID_SIZE, config.GRID_SIZE*2

        self.rect = pygame.Rect(ox, oy, w, h)

    def get_surface(self, zoom=1.0, highlight=False, size_override=None):
        if self.type in (config.OBJ_PORTAL_CUBE, config.OBJ_PORTAL_SHIP, config.OBJ_PORTAL_BALL, config.OBJ_PORTAL_UFO, config.OBJ_PORTAL_WAVE, config.OBJ_PORTAL_GRAV_DOWN, config.OBJ_PORTAL_GRAV_UP):
            sw, sh = config.GRID_SIZE, config.GRID_SIZE * 3
        elif self.type == config.OBJ_PULSEROD_2: sw, sh = config.GRID_SIZE, config.GRID_SIZE * 2
        elif self.type == config.OBJ_PULSEROD_3: sw, sh = config.GRID_SIZE, config.GRID_SIZE * 3
        elif self.type == config.OBJ_DECO_CHAIN: sw, sh = config.GRID_SIZE, config.GRID_SIZE * 2
        elif self.type == config.OBJ_SAW: sw, sh = config.GRID_SIZE * 2, config.GRID_SIZE * 2
        elif self.type == config.OBJ_GEAR_L: sw, sh = config.GRID_SIZE * 2, config.GRID_SIZE * 2
        elif self.type in (config.OBJ_SAW_2, config.OBJ_GEAR_M): sw, sh = int(config.GRID_SIZE * 1.5), int(config.GRID_SIZE * 1.5)
        elif self.type == config.OBJ_SAW_3: sw, sh = int(config.GRID_SIZE * 3), int(config.GRID_SIZE * 3)
        elif self.type == config.OBJ_CLOUD_1: sw, sh = config.GRID_SIZE * 2, config.GRID_SIZE
        elif self.type == config.OBJ_CLOUD_2: sw, sh = int(config.GRID_SIZE * 1.5), config.GRID_SIZE
        else: sw, sh = config.GRID_SIZE, config.GRID_SIZE

        z_scale = zoom * config.get_scale()
        if size_override is not None:
            # Pixel-exact size derived by the caller from neighboring cell boundaries,
            # so adjacent tiles share identical edges with no rounding gap between them.
            w, h = size_override
            gz = w
        else:
            w, h = max(1, int(sw * z_scale)), max(1, int(sh * z_scale))
            gz = int(config.GRID_SIZE * z_scale)
        
        if self.type in (config.OBJ_SAW, config.OBJ_SAW_2, config.OBJ_SAW_3, config.OBJ_GEAR_L, config.OBJ_GEAR_M, config.OBJ_GEAR_S):
            if w % 2 != 0: w += 1
            if h % 2 != 0: h += 1
        
        obj_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        base_color = config.BG_COLORS[self.color_idx] if self.color_idx < len(config.BG_COLORS) else config.GRAY
        
        if self.type in (config.OBJ_BLOCK, config.OBJ_BLOCK_GRID, config.OBJ_BLOCK_BEVEL, config.OBJ_BLOCK_FADED, config.OBJ_BLOCK_BRICK, config.OBJ_HALF_BLOCK, config.OBJ_SPIKE, config.OBJ_HALF_SPIKE,
                         config.OBJ_BLOCK_DOTS, config.OBJ_BLOCK_STRIPES, config.OBJ_BLOCK_CROSS, config.OBJ_BLOCK_CIRCLE):
            base_color = (max(0, base_color[0]-30), max(0, base_color[1]-30), max(0, base_color[2]-30))
            
        outline_color = config.GREEN if highlight else config.WHITE
        lw = max(1, int(2 * z_scale))

        if self.type == config.OBJ_BLOCK:
            pygame.draw.rect(obj_surf, base_color, (0, 0, gz, gz))
        elif self.type == config.OBJ_HALF_BLOCK:
            pygame.draw.rect(obj_surf, base_color, (0, gz//2, gz, gz//2))
            pygame.draw.rect(obj_surf, outline_color, (0, gz//2, gz, gz//2), lw)
        elif self.type == config.OBJ_BLOCK_FADED:  # "Checker Block"
            pygame.draw.rect(obj_surf, base_color, (0, 0, w, h))
            dark_c = (max(0, base_color[0]-45), max(0, base_color[1]-45), max(0, base_color[2]-45))
            n = 4
            cell_w = max(1, gz // n)
            # Index squares by absolute grid position (not local surface coords) so
            # the checker parity carries over exactly between adjacent cells instead
            # of each block restarting its own pattern at the edge.
            col0 = round(self.x / config.GRID_SIZE) * n
            row0 = round(self.y / config.GRID_SIZE) * n
            for i in range(n):
                for j in range(n):
                    if (col0 + i + row0 + j) % 2 == 0:
                        pygame.draw.rect(obj_surf, dark_c, (i*cell_w, j*cell_w, cell_w, cell_w))
        elif self.type == config.OBJ_BLOCK_BRICK:
            pygame.draw.rect(obj_surf, base_color, (0, 0, gz, gz))
            dark_brick = (max(0, base_color[0]-60), max(0, base_color[1]-60), max(0, base_color[2]-60))
            brick_h = gz // 4
            for r in range(1, 4):
                y = r * brick_h
                pygame.draw.line(obj_surf, dark_brick, (0, y), (gz, y), lw)
            brick_w = gz // 2
            for r in range(4):
                offset = (gz // 4) if r % 2 == 1 else 0
                for c in range(3):
                    x = offset + c * brick_w - (brick_w if c==0 and offset>0 else 0)
                    if 0 < x < gz:
                        pygame.draw.line(obj_surf, dark_brick, (x, r*brick_h), (x, r*brick_h + brick_h), lw)
        elif self.type == config.OBJ_BLOCK_GRID:
            pygame.draw.rect(obj_surf, base_color, (0, 0, gz, gz))
            inner_c = (max(0, base_color[0]-40), max(0, base_color[1]-40), max(0, base_color[2]-40))
            step = gz // 3
            for i in range(3):
                for j in range(3):
                    pygame.draw.rect(obj_surf, inner_c, (i*step+lw, j*step+lw, step-lw*2, step-lw*2))
        elif self.type == config.OBJ_BLOCK_BEVEL:
            pygame.draw.rect(obj_surf, base_color, (0, 0, gz, gz))
            c2 = (max(0, base_color[0]-20), max(0, base_color[1]-20), max(0, base_color[2]-20))
            c3 = (max(0, base_color[0]-40), max(0, base_color[1]-40), max(0, base_color[2]-40))
            c4 = (max(0, base_color[0]-60), max(0, base_color[1]-60), max(0, base_color[2]-60))
            pygame.draw.polygon(obj_surf, base_color, [(0,0), (gz,0), (gz//2, gz//2)])
            pygame.draw.polygon(obj_surf, c2, [(gz,0), (gz,gz), (gz//2, gz//2)])
            pygame.draw.polygon(obj_surf, c3, [(0,gz), (gz,gz), (gz//2, gz//2)])
            pygame.draw.polygon(obj_surf, c4, [(0,0), (0,gz), (gz//2, gz//2)])
        elif self.type == config.OBJ_BLOCK_DOTS:
            pygame.draw.rect(obj_surf, base_color, (0, 0, gz, gz))
            dot_c = (max(0, base_color[0]-50), max(0, base_color[1]-50), max(0, base_color[2]-50))
            step = gz // 4
            for i in range(1, 4):
                for j in range(1, 4):
                    pygame.draw.circle(obj_surf, dot_c, (i*step, j*step), max(1, gz//14))
        elif self.type == config.OBJ_BLOCK_STRIPES:  # "Panel Block"
            pygame.draw.rect(obj_surf, base_color, (0, 0, w, h))
            dark_c = (max(0, base_color[0]-45), max(0, base_color[1]-45), max(0, base_color[2]-45))
            n = 4  # even count: alternation naturally continues across a cell boundary, no phase math needed
            band_h = max(1, h // n)
            for i in range(n):
                if i % 2 == 1:
                    pygame.draw.rect(obj_surf, dark_c, (0, i*band_h, w, band_h))
        elif self.type == config.OBJ_BLOCK_CROSS:
            pygame.draw.rect(obj_surf, base_color, (0, 0, gz, gz))
            cross_c = (max(0, base_color[0]-50), max(0, base_color[1]-50), max(0, base_color[2]-50))
            cw = max(2, gz//5)
            pygame.draw.rect(obj_surf, cross_c, (gz//2 - cw//2, 0, cw, gz))
            pygame.draw.rect(obj_surf, cross_c, (0, gz//2 - cw//2, gz, cw))
        elif self.type == config.OBJ_BLOCK_CIRCLE:
            pygame.draw.rect(obj_surf, base_color, (0, 0, gz, gz))
            circ_c = (max(0, base_color[0]-50), max(0, base_color[1]-50), max(0, base_color[2]-50))
            pygame.draw.circle(obj_surf, circ_c, (gz//2, gz//2), int(gz*0.32))
        elif self.type == config.OBJ_OUTLINE_LINE:
            lw2 = max(2, int(5 * z_scale))
            pygame.draw.line(obj_surf, base_color, (0, lw2//2), (gz, lw2//2), lw2)
        elif self.type == config.OBJ_OUTLINE_CORNER_PIXEL:
            lw2 = max(2, int(5 * z_scale))
            pygame.draw.rect(obj_surf, base_color, (0, 0, lw2, lw2))
        elif self.type == config.OBJ_OUTLINE_3SIDE:
            lw2 = max(2, int(5 * z_scale))
            pygame.draw.line(obj_surf, base_color, (0, lw2//2), (gz, lw2//2), lw2)
            pygame.draw.line(obj_surf, base_color, (lw2//2, 0), (lw2//2, gz), lw2)
            pygame.draw.line(obj_surf, base_color, (gz-lw2//2, 0), (gz-lw2//2, gz), lw2)
        elif self.type == config.OBJ_OUTLINE_OPPOSITE:
            lw2 = max(2, int(5 * z_scale))
            pygame.draw.line(obj_surf, base_color, (0, lw2//2), (gz, lw2//2), lw2)
            pygame.draw.line(obj_surf, base_color, (0, gz-lw2//2), (gz, gz-lw2//2), lw2)
        elif self.type == config.OBJ_OUTLINE_CORNER2:
            lw2 = max(2, int(5 * z_scale))
            pygame.draw.line(obj_surf, base_color, (0, lw2//2), (gz, lw2//2), lw2)
            pygame.draw.line(obj_surf, base_color, (lw2//2, 0), (lw2//2, gz), lw2)
        elif self.type == config.OBJ_SPIKE:
            pygame.draw.polygon(obj_surf, base_color, [(0, gz), (gz//2, 0), (gz, gz)])
            pygame.draw.polygon(obj_surf, outline_color, [(0, gz), (gz//2, 0), (gz, gz)], lw)
            pygame.draw.line(obj_surf, outline_color, (0, gz-1), (gz, gz-1), lw)
        elif self.type == config.OBJ_HALF_SPIKE:
            pygame.draw.polygon(obj_surf, base_color, [(0, gz), (gz//2, gz//2), (gz, gz)])
            pygame.draw.polygon(obj_surf, outline_color, [(0, gz), (gz//2, gz//2), (gz, gz)], lw)
            pygame.draw.line(obj_surf, outline_color, (0, gz-1), (gz, gz-1), lw)
        elif self.type == config.OBJ_GROUND_SPIKE:
            pts = [(0, gz), (gz//6, gz//2), (gz//3, gz), (gz//2, gz//2), (2*gz//3, gz), (5*gz//6, gz//2), (gz, gz)]
            pygame.draw.polygon(obj_surf, (20, 20, 20), pts)
            pygame.draw.polygon(obj_surf, outline_color, pts, lw)
            pygame.draw.line(obj_surf, outline_color, (0, gz-1), (gz, gz-1), lw)
        elif self.type in (config.OBJ_DECO_SPIKE_L, config.OBJ_DECO_SPIKE_M):
            d_h = gz if self.type == config.OBJ_DECO_SPIKE_L else gz//2
            pygame.draw.polygon(obj_surf, base_color, [(0, gz), (gz//2, gz - d_h), (gz, gz)])
        elif self.type == config.OBJ_DECO_CHAIN:
            pygame.draw.line(obj_surf, base_color, (w//2, 0), (w//2, h), max(1, int(3*z_scale)))
            for i in range(4):
                pygame.draw.ellipse(obj_surf, config.BLACK, (w//2 - int(4*z_scale), i*(h//4) + int(5*z_scale), int(8*z_scale), int(15*z_scale)))
                pygame.draw.ellipse(obj_surf, base_color, (w//2 - int(4*z_scale), i*(h//4) + int(5*z_scale), int(8*z_scale), int(15*z_scale)), max(1, int(2*z_scale)))
        elif self.type in (config.OBJ_CLOUD_1, config.OBJ_CLOUD_2):
            base_y = h - int(4*z_scale)
            if self.type == config.OBJ_CLOUD_1: circles = [(0.15, 10), (0.35, 15), (0.6, 18), (0.85, 12)]
            else: circles = [(0.2, 10), (0.5, 14), (0.8, 9)]
            for cx_pct, r_base in circles:
                r = int(r_base * z_scale)
                pygame.draw.circle(obj_surf, base_color, (int(w * cx_pct), base_y - r), r)
            pygame.draw.rect(obj_surf, base_color, (int(w*0.1), base_y - int(10*z_scale), int(w*0.8), int(10*z_scale)))
        elif self.type in (config.OBJ_PULSEROD_1, config.OBJ_PULSEROD_2, config.OBJ_PULSEROD_3):
            pw = max(1, int(8 * z_scale))
            px = w//2 - pw//2
            pygame.draw.rect(obj_surf, (20, 20, 25), (px, int(10*z_scale), pw, h - int(10*z_scale)))
            pygame.draw.rect(obj_surf, base_color, (px + int(2*z_scale), int(12*z_scale), pw - int(4*z_scale), h - int(14*z_scale)))
            for i in range(2, h // int(12*z_scale)):
                pygame.draw.line(obj_surf, (10, 10, 15), (px, i*int(12*z_scale)), (px+pw, i*int(12*z_scale)), max(1, int(2*z_scale)))
            
            center = (w//2, int(10*z_scale))
            freq = self.bpm / 60.0
            pulse = math.sin(pygame.time.get_ticks() * 0.001 * math.pi * freq)
            radius = int((8 + pulse * 3) * z_scale)
            
            halo_surf = pygame.Surface((radius*4, radius*4), pygame.SRCALPHA)
            pygame.draw.circle(halo_surf, (*base_color[:3], 100), (radius*2, radius*2), int(radius*1.5))
            obj_surf.blit(halo_surf, (center[0] - radius*2, center[1] - radius*2))
            
            pygame.draw.circle(obj_surf, base_color, center, max(2, int(6*z_scale)))
            pygame.draw.circle(obj_surf, config.WHITE, center, max(1, int(3*z_scale)))
            
        elif self.type in (config.OBJ_PULSE_CIRCLE, config.OBJ_PULSE_HOLLOW, config.OBJ_PULSE_HEART, config.OBJ_PULSE_DIAMOND, config.OBJ_PULSE_STAR, config.OBJ_PULSE_NOTE):
            freq = 1.0
            pulse = math.sin(pygame.time.get_ticks() * 0.001 * math.pi * freq)
            scale = 1.0 + pulse * 0.25
            cx, cy = w//2, h//2
            if self.type == config.OBJ_PULSE_CIRCLE:
                pygame.draw.circle(obj_surf, base_color, (cx, cy), int(12*z_scale*scale))
            elif self.type == config.OBJ_PULSE_HOLLOW:
                pygame.draw.circle(obj_surf, base_color, (cx, cy), int(14*z_scale*scale), max(1, int(4*z_scale)))
            elif self.type == config.OBJ_PULSE_DIAMOND:
                r = int(14 * z_scale * scale)
                pygame.draw.polygon(obj_surf, base_color, [(cx, cy-r), (cx+r, cy), (cx, cy+r), (cx-r, cy)])
            elif self.type == config.OBJ_PULSE_STAR:
                pts = []
                r_out = int(14 * z_scale * scale)
                r_in = int(6 * z_scale * scale)
                for i in range(10):
                    angle = math.pi/2 - i * math.pi/5
                    r = r_out if i % 2 == 0 else r_in
                    pts.append((cx + math.cos(angle)*r, cy - math.sin(angle)*r))
                pygame.draw.polygon(obj_surf, base_color, pts)
            elif self.type == config.OBJ_PULSE_HEART:
                r = int(7 * z_scale * scale)
                pygame.draw.circle(obj_surf, base_color, (cx-r, cy-r//2), r)
                pygame.draw.circle(obj_surf, base_color, (cx+r, cy-r//2), r)
                pygame.draw.polygon(obj_surf, base_color, [(cx-r*2, cy-r//2+1), (cx+r*2, cy-r//2+1), (cx, cy+r*1.5)])
            elif self.type == config.OBJ_PULSE_NOTE:
                s = scale * z_scale
                pygame.draw.circle(obj_surf, base_color, (cx - int(4*s), cy + int(6*s)), int(5*s))
                pygame.draw.line(obj_surf, base_color, (cx + int(1*s), cy + int(6*s)), (cx + int(1*s), cy - int(8*s)), max(1, int(2*z_scale)))
                pygame.draw.line(obj_surf, base_color, (cx + int(1*s), cy - int(8*s)), (cx + int(8*s), cy - int(2*s)), max(1, int(2*z_scale)))
        elif self.type in (config.OBJ_SAW, config.OBJ_SAW_2, config.OBJ_SAW_3, config.OBJ_GEAR_L, config.OBJ_GEAR_M, config.OBJ_GEAR_S):
            cx, cy = w//2, h//2
            num_spikes = 12 if self.type not in (config.OBJ_SAW_3, config.OBJ_GEAR_L) else 16
            points = []
            is_gear = self.type in (config.OBJ_GEAR_L, config.OBJ_GEAR_M, config.OBJ_GEAR_S)
            outer_margin = int(2*z_scale) if not is_gear else int(1*z_scale)
            inner_margin = int(12*z_scale) if not is_gear else int(6*z_scale)
            
            for i in range(num_spikes * 2):
                angle = math.pi * i / num_spikes
                r = (w//2 - outer_margin) if (i % 2 == 0 or is_gear and i%4 < 2) else (w//2 - inner_margin)
                points.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r))
            
            pygame.draw.polygon(obj_surf, base_color, points)
            if not is_gear:
                pygame.draw.polygon(obj_surf, outline_color, points, lw)
                pygame.draw.circle(obj_surf, config.DARK_GRAY, (cx, cy), w//4)
                pygame.draw.circle(obj_surf, outline_color, (cx, cy), w//4, lw)
            else:
                pygame.draw.circle(obj_surf, (0,0,0,0), (cx, cy), w//4) 
                pygame.draw.circle(obj_surf, base_color, (cx, cy), w//4, lw)
        elif self.type in (config.OBJ_PORTAL_CUBE, config.OBJ_PORTAL_SHIP, config.OBJ_PORTAL_BALL, config.OBJ_PORTAL_UFO, config.OBJ_PORTAL_WAVE):
            color = config.GREEN if self.type == config.OBJ_PORTAL_CUBE else config.CYAN if self.type == config.OBJ_PORTAL_WAVE else config.MAGENTA if self.type == config.OBJ_PORTAL_SHIP else config.ORANGE if self.type == config.OBJ_PORTAL_UFO else config.RED
            pygame.draw.ellipse(obj_surf, color, (int(4*z_scale), 0, gz - int(8*z_scale), gz * 3), int(6*z_scale))
            pygame.draw.ellipse(obj_surf, config.WHITE, (int(4*z_scale), 0, gz - int(8*z_scale), gz * 3), lw)
        elif self.type in (config.OBJ_PORTAL_GRAV_DOWN, config.OBJ_PORTAL_GRAV_UP):
            color = config.BLUE if self.type == config.OBJ_PORTAL_GRAV_DOWN else config.YELLOW
            pygame.draw.rect(obj_surf, color, (int(4*z_scale), 0, gz - int(8*z_scale), gz * 3), int(4*z_scale), border_radius=int(8*z_scale))
            cy = gz + gz//2; cx = gz // 2
            dir_y = 1 if self.type == config.OBJ_PORTAL_GRAV_DOWN else -1
            pts = [(cx, cy + dir_y * int(15*z_scale)), (cx - int(10*z_scale), cy - dir_y * int(5*z_scale)), (cx + int(10*z_scale), cy - dir_y * int(5*z_scale))]
            pygame.draw.polygon(obj_surf, config.WHITE, pts)
            pygame.draw.line(obj_surf, config.WHITE, (cx, cy - dir_y * int(5*z_scale)), (cx, cy - dir_y * int(15*z_scale)), int(4*z_scale))
        elif self.type in (config.OBJ_PAD_YELLOW, config.OBJ_PAD_PURPLE, config.OBJ_PAD_BLUE):
            color1 = config.ORANGE if self.type == config.OBJ_PAD_YELLOW else config.MAGENTA if self.type == config.OBJ_PAD_PURPLE else config.BLUE
            color2 = config.YELLOW if self.type == config.OBJ_PAD_YELLOW else config.PURPLE if self.type == config.OBJ_PAD_PURPLE else config.CYAN
            pad_rect = pygame.Rect(0, gz - int(12*z_scale), gz, int(12*z_scale))
            pygame.draw.rect(obj_surf, color1, pad_rect, 0, int(6*z_scale))
            pygame.draw.rect(obj_surf, color2, (int(2*z_scale), gz - int(10*z_scale), gz - int(4*z_scale), int(8*z_scale)), 0, int(4*z_scale))
        elif self.type in (config.OBJ_ORB_YELLOW, config.OBJ_ORB_PURPLE, config.OBJ_ORB_BLUE):
            color1 = config.ORANGE if self.type == config.OBJ_ORB_YELLOW else config.MAGENTA if self.type == config.OBJ_ORB_PURPLE else config.BLUE
            color2 = config.YELLOW if self.type == config.OBJ_ORB_YELLOW else config.PURPLE if self.type == config.OBJ_ORB_PURPLE else config.CYAN
            pygame.draw.circle(obj_surf, color1, (w//2, h//2), int(12*z_scale), int(3*z_scale))
            pygame.draw.circle(obj_surf, color2, (w//2, h//2), int(7*z_scale))
        elif self.type in (config.OBJ_COLOR_TRIGGER, config.OBJ_GROUND_COLOR_TRIGGER):
            trig_color = config.BG_COLORS[self.color_idx]
            label = "T" if self.type == config.OBJ_COLOR_TRIGGER else "G"
            pygame.draw.rect(obj_surf, trig_color, (0, 0, gz, gz), int(3*z_scale))
            font = pygame.font.SysFont("Arial", int(18*z_scale), bold=True)
            obj_surf.blit(font.render(label, True, config.WHITE), (int(11*z_scale), int(8*z_scale)))
        elif self.type == config.OBJ_SPAWN:
            pygame.draw.rect(obj_surf, outline_color, (0, 0, gz, gz), int(3*z_scale))
            font = pygame.font.SysFont("Arial", int(18*z_scale), bold=True)
            obj_surf.blit(font.render("S", True, outline_color), (int(12*z_scale), int(8*z_scale)))
        elif self.type == config.OBJ_END_TRIGGER:
            pygame.draw.rect(obj_surf, config.MAGENTA, (0, 0, gz, gz), int(3*z_scale))
            font = pygame.font.SysFont("Arial", int(18*z_scale), bold=True)
            obj_surf.blit(font.render("E", True, config.MAGENTA), (int(12*z_scale), int(8*z_scale)))
        elif self.type in (config.OBJ_SPEED_05X, config.OBJ_SPEED_1X, config.OBJ_SPEED_2X, config.OBJ_SPEED_3X):
            speed_color = {config.OBJ_SPEED_05X: config.ORANGE, config.OBJ_SPEED_1X: config.BLUE,
                            config.OBJ_SPEED_2X: config.GREEN, config.OBJ_SPEED_3X: config.MAGENTA}[self.type]
            chevron_count = {config.OBJ_SPEED_05X: 1, config.OBJ_SPEED_1X: 1,
                              config.OBJ_SPEED_2X: 2, config.OBJ_SPEED_3X: 3}[self.type]
            ch_h, ch_w = gz * 0.5, gz * 0.32
            spacing = ch_w * 0.62
            total_span = ch_w + (chevron_count - 1) * spacing
            start_cx = gz / 2 - total_span / 2
            cy = gz / 2
            olw = max(1, int(1.1 * z_scale))
            for i in range(chevron_count):
                cx = start_cx + i * spacing
                pts = [
                    (cx, cy - ch_h / 2),
                    (cx + ch_w, cy),
                    (cx, cy + ch_h / 2),
                    (cx + ch_w * 0.35, cy + ch_h / 2),
                    (cx + ch_w * 0.65, cy),
                    (cx + ch_w * 0.35, cy - ch_h / 2),
                ]
                pygame.draw.polygon(obj_surf, speed_color, pts)
                pygame.draw.polygon(obj_surf, config.BLACK, pts, olw)

        if highlight:
            pygame.draw.rect(obj_surf, config.GREEN, (0, 0, w, h), max(1, int(4 * z_scale)))

        if self.flip_x or self.flip_y:
            obj_surf = pygame.transform.flip(obj_surf, self.flip_x, self.flip_y)

        if self.rotation != 0 and self.type not in config.NON_ROTATABLE:
            obj_surf = pygame.transform.rotate(obj_surf, -self.rotation)
            
        return obj_surf

    def draw(self, surface, scroll_x, scroll_y, zoom=1.0, highlight=False, alpha=255):
        dy = self.y
        dx = self.x
        
        if self.type in (config.OBJ_PORTAL_CUBE, config.OBJ_PORTAL_SHIP, config.OBJ_PORTAL_BALL, config.OBJ_PORTAL_UFO, config.OBJ_PORTAL_WAVE, config.OBJ_PORTAL_GRAV_DOWN, config.OBJ_PORTAL_GRAV_UP): dy = self.y - config.GRID_SIZE
        elif self.type == config.OBJ_PULSEROD_2: dy = self.y - config.GRID_SIZE
        elif self.type == config.OBJ_PULSEROD_3: dy = self.y - config.GRID_SIZE * 2
        elif self.type == config.OBJ_SAW: dy = (self.y + config.GRID_SIZE//2) - config.GRID_SIZE; dx = (self.x + config.GRID_SIZE//2) - config.GRID_SIZE
        elif self.type == config.OBJ_SAW_2: dy = (self.y + config.GRID_SIZE//2) - int(config.GRID_SIZE * 0.75); dx = (self.x + config.GRID_SIZE//2) - int(config.GRID_SIZE * 0.75)
        elif self.type == config.OBJ_SAW_3: dy = (self.y + config.GRID_SIZE//2) - int(config.GRID_SIZE * 1.5); dx = (self.x + config.GRID_SIZE//2) - int(config.GRID_SIZE * 1.5)
        elif self.type == config.OBJ_GEAR_L: dy = self.y - config.GRID_SIZE; dx = self.x - config.GRID_SIZE//2
        elif self.type == config.OBJ_GEAR_M: dy = self.y - config.GRID_SIZE//2
            
        draw_x = int((dx - scroll_x) * zoom * config.get_scale())
        draw_y = int((dy - scroll_y) * zoom * config.get_scale())

        if draw_x < -config.S(config.GRID_SIZE * 4 * zoom) or draw_x > config.RENDER_W: return
        if draw_y < -config.S(config.GRID_SIZE * 4 * zoom) or draw_y > config.RENDER_H: return

        size_override = None
        if self.type in TILEABLE_TYPES:
            z = zoom * config.get_scale()
            x1 = int((dx + config.GRID_SIZE - scroll_x) * z)
            y1 = int((dy + config.GRID_SIZE - scroll_y) * z)
            size_override = (max(1, x1 - draw_x), max(1, y1 - draw_y))

        obj_surf = self.get_surface(zoom, highlight, size_override=size_override)
        if alpha < 255:
            obj_surf.set_alpha(alpha)

        if self.type in (config.OBJ_SAW, config.OBJ_SAW_2, config.OBJ_SAW_3, config.OBJ_GEAR_L, config.OBJ_GEAR_M, config.OBJ_GEAR_S):
            time_rot = (pygame.time.get_ticks() / 3.0) % 360
            if self.flip_x: time_rot = -time_rot
            orig_center = (draw_x + obj_surf.get_width()//2, draw_y + obj_surf.get_height()//2)
            rotated_surf = pygame.transform.rotate(obj_surf, -time_rot)
            if alpha < 255:
                rotated_surf.set_alpha(alpha)
            rect = rotated_surf.get_rect(center=orig_center)
            surface.blit(rotated_surf, rect.topleft)
            return

        surface.blit(obj_surf, (draw_x, draw_y))