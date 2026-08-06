import pygame

# --- LOGICAL RESOLUTION ENGINE ---
BASE_W, BASE_H = 1920, 1080
RENDER_W, RENDER_H = 1920, 1080 

def get_scale():
    return RENDER_H / BASE_H

def S(val):
    return int(val * get_scale())

# --- CONFIGURATION & CONSTANTS ---
FPS = 60
GRID_SIZE = 40
SCROLL_SPEED = 7.8 
GROUND_Y = BASE_H - 120 
CEILING_Y = GROUND_Y - (12 * GRID_SIZE) 

# Player Preferences
P_CUBE_IDX = 0
P_SHIP_IDX = 0
P_BALL_IDX = 0
P_WAVE_IDX = 0
P_UFO_IDX = 0
P_COLOR = (0, 255, 128) 
P_COLOR2 = (0, 255, 255)

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 60, 60)
GREEN = (60, 255, 60)
BLUE = (60, 180, 255)
MAGENTA = (255, 60, 255)
YELLOW = (255, 255, 60)
ORANGE = (255, 140, 0)
CYAN = (0, 255, 255)
PURPLE = (180, 40, 255)
GRAY = (120, 120, 120)
DARK_GRAY = (40, 40, 45)
LIGHT_GRAY = (190, 190, 190)

# Colors for levels / blocks (Index 8 is Pure White for default Deco).
# The original 24 keep their indices forever -- saved levels reference colors
# by index, so existing entries must never move or change. New colors are
# only ever appended after them; display order (see UI_COLOR_ORDER) is a
# separate concern from storage index.
import colorsys

BG_COLORS = [
    (40, 100, 255), (255, 50, 100), (50, 220, 100), (150, 50, 255),
    (255, 150, 20), (20, 200, 200), (255, 220, 40), (45, 45, 50),
    (255, 255, 255), (15, 15, 15), (128, 0, 0), (0, 128, 0),
    (0, 0, 128), (128, 128, 0), (128, 0, 128), (0, 128, 128),
    (255, 100, 100), (100, 255, 100), (100, 100, 255), (255, 255, 100),
    (255, 100, 255), (100, 255, 255), (255, 150, 150), (150, 255, 150)
]

def _hue_wheel(n_hues, s, v):
    out = []
    for i in range(n_hues):
        r, g, b = colorsys.hsv_to_rgb(i / n_hues, s, v)
        out.append((int(r * 255), int(g * 255), int(b * 255)))
    return out

# 24 hues x 3 tiers (vivid / pastel / deep) = 72 more colors, plus a 9-step
# grayscale ramp, for 105 total -- well over the old 24-color cap.
BG_COLORS += _hue_wheel(24, 1.0, 1.0)
BG_COLORS += _hue_wheel(24, 0.45, 1.0)
BG_COLORS += _hue_wheel(24, 1.0, 0.55)
BG_COLORS += [(v, v, v) for v in (0, 32, 64, 96, 128, 160, 192, 224, 255)]

def _color_sort_key(idx):
    r, g, b = BG_COLORS[idx]
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if s < 0.08:
        return (1, v)  # group grayscale colors after the chromatic wheel, dark to light
    return (0, h, v)

UI_COLOR_ORDER = sorted(range(len(BG_COLORS)), key=_color_sort_key)

PLAYER_COLORS = [
    (255, 255, 255), (190, 190, 190), (120, 120, 120), (45, 45, 50), (15, 15, 15),
    (255, 60, 60), (180, 0, 0), (255, 140, 0), (255, 180, 50),
    (255, 255, 60), (255, 255, 150),
    (60, 255, 60), (0, 128, 0), (50, 220, 100), (150, 255, 150),
    (0, 255, 255), (0, 128, 128), (60, 180, 255), (0, 100, 255), (0, 0, 128),
    (150, 50, 255), (180, 40, 255), (255, 60, 255), (255, 150, 200)
]

# Difficulties
DIFF_AUTO = 0
DIFF_EASY = 1
DIFF_NORMAL = 2
DIFF_HARD = 3
DIFF_HARDER = 4
DIFF_INSANE = 5
DIFF_DEMON_EASY = 6
DIFF_DEMON_MEDIUM = 7
DIFF_DEMON_HARD = 8
DIFF_DEMON_INSANE = 9
DIFF_DEMON_EXTREME = 10

DIFF_NAMES = {
    DIFF_AUTO: "N/A",
    DIFF_EASY: "Easy",
    DIFF_NORMAL: "Normal",
    DIFF_HARD: "Hard",
    DIFF_HARDER: "Harder",
    DIFF_INSANE: "Insane",
    DIFF_DEMON_EASY: "Easy Demon",
    DIFF_DEMON_MEDIUM: "Medium Demon",
    DIFF_DEMON_HARD: "Hard Demon",
    DIFF_DEMON_INSANE: "Insane Demon",
    DIFF_DEMON_EXTREME: "Extreme Demon"
}

# Object Types
OBJ_BLOCK, OBJ_HALF_BLOCK, OBJ_SPIKE, OBJ_HALF_SPIKE = 1, 2, 3, 4
OBJ_PORTAL_CUBE, OBJ_PORTAL_SHIP, OBJ_PAD_YELLOW, OBJ_ORB_YELLOW = 5, 6, 7, 8
OBJ_PAD_BLUE, OBJ_ORB_BLUE, OBJ_SPAWN, OBJ_COLOR_TRIGGER = 9, 10, 11, 12
OBJ_SAW, OBJ_PORTAL_UFO, OBJ_PORTAL_BALL, OBJ_PORTAL_WAVE = 13, 14, 15, 16
OBJ_END_TRIGGER, OBJ_PAD_PURPLE, OBJ_ORB_PURPLE = 18, 19, 20
OBJ_GROUND_COLOR_TRIGGER, OBJ_SAW_2, OBJ_SAW_3 = 21, 22, 23
OBJ_BLOCK_FADED, OBJ_BLOCK_BRICK, OBJ_BLOCK_BEVEL, OBJ_BLOCK_GRID = 24, 25, 26, 27
OBJ_GROUND_SPIKE = 28
OBJ_PULSEROD_1, OBJ_PULSEROD_2, OBJ_PULSEROD_3 = 29, 30, 31
OBJ_PORTAL_GRAV_DOWN, OBJ_PORTAL_GRAV_UP = 32, 33
OBJ_GEAR_L, OBJ_GEAR_M, OBJ_GEAR_S = 34, 35, 36
OBJ_DECO_SPIKE_L, OBJ_DECO_SPIKE_M = 37, 38 
OBJ_DECO_CHAIN = 40
OBJ_CLOUD_1, OBJ_CLOUD_2 = 41, 42
OBJ_PULSE_CIRCLE, OBJ_PULSE_HOLLOW, OBJ_PULSE_HEART, OBJ_PULSE_DIAMOND, OBJ_PULSE_STAR, OBJ_PULSE_NOTE = 43, 44, 45, 46, 47, 48
OBJ_SPEED_05X, OBJ_SPEED_1X, OBJ_SPEED_2X, OBJ_SPEED_3X, OBJ_SPEED_4X = 49, 50, 51, 52, 53

# Outline blocks: thin border pieces meant to be layered over a detail block
# (usually a contrasting color) to fake a bordered-block look. Rotatable --
# rotation picks which edge/corner the piece occupies.
OBJ_OUTLINE_LINE, OBJ_OUTLINE_CORNER_PIXEL, OBJ_OUTLINE_3SIDE, OBJ_OUTLINE_OPPOSITE, OBJ_OUTLINE_CORNER2 = 54, 55, 56, 57, 58

# More detail block variants (solid, no border, textured fill)
OBJ_BLOCK_DOTS, OBJ_BLOCK_STRIPES, OBJ_BLOCK_CROSS, OBJ_BLOCK_CIRCLE = 59, 60, 61, 62


OBJ_NAMES = {
    OBJ_BLOCK: "Solid Block", OBJ_HALF_BLOCK: "Half Block", OBJ_SPIKE: "Spike", OBJ_HALF_SPIKE: "Half Spike",
    OBJ_PORTAL_CUBE: "Cube Portal", OBJ_PORTAL_SHIP: "Ship Portal", OBJ_PAD_YELLOW: "Yellow Pad",
    OBJ_ORB_YELLOW: "Yellow Orb", OBJ_PAD_BLUE: "Blue Pad", OBJ_ORB_BLUE: "Blue Orb",
    OBJ_SPAWN: "Spawn Point", OBJ_COLOR_TRIGGER: "BG Color Trigger", OBJ_SAW: "Sawblade 2x2",
    OBJ_PORTAL_BALL: "Ball Portal", OBJ_PORTAL_UFO: "UFO Portal", OBJ_PORTAL_WAVE: "Wave Portal", OBJ_END_TRIGGER: "End Trigger", 
    OBJ_PAD_PURPLE: "Purple Pad", OBJ_ORB_PURPLE: "Purple Orb", OBJ_GROUND_COLOR_TRIGGER: "Ground Color Trigger", 
    OBJ_SAW_2: "Sawblade 1.5x", OBJ_SAW_3: "Sawblade 3x3",
    OBJ_BLOCK_FADED: "Checker Block", OBJ_BLOCK_BRICK: "Brick Block", 
    OBJ_BLOCK_BEVEL: "Bevel Block", OBJ_BLOCK_GRID: "Grid Block",
    OBJ_GROUND_SPIKE: "Ground Spike", 
    OBJ_PULSEROD_1: "Pulserod (1x)", OBJ_PULSEROD_2: "Pulserod (2x)", OBJ_PULSEROD_3: "Pulserod (3x)",
    OBJ_PORTAL_GRAV_DOWN: "Gravity Normal Portal", OBJ_PORTAL_GRAV_UP: "Gravity Reverse Portal",
    OBJ_GEAR_L: "Large Gear", OBJ_GEAR_M: "Medium Gear", OBJ_GEAR_S: "Small Gear",
    OBJ_DECO_SPIKE_L: "Deco Spike (L)", OBJ_DECO_SPIKE_M: "Deco Spike (M)",
    OBJ_DECO_CHAIN: "Deco Chain", OBJ_CLOUD_1: "Cloud 1", OBJ_CLOUD_2: "Cloud 2",
    OBJ_PULSE_CIRCLE: "Pulse Circle", OBJ_PULSE_HOLLOW: "Pulse Ring", OBJ_PULSE_HEART: "Pulse Heart",
    OBJ_PULSE_DIAMOND: "Pulse Diamond", OBJ_PULSE_STAR: "Pulse Star", OBJ_PULSE_NOTE: "Pulse Note",
    OBJ_SPEED_05X: "Speed 0.5x", OBJ_SPEED_1X: "Speed 1x", OBJ_SPEED_2X: "Speed 2x",
    OBJ_SPEED_3X: "Speed 3x", OBJ_SPEED_4X: "Speed 4x",
    OBJ_OUTLINE_LINE: "Outline: Line", OBJ_OUTLINE_CORNER_PIXEL: "Outline: Corner Pixel",
    OBJ_OUTLINE_3SIDE: "Outline: 3 Sides", OBJ_OUTLINE_OPPOSITE: "Outline: Opposite Sides",
    OBJ_OUTLINE_CORNER2: "Outline: Corner Two",
    OBJ_BLOCK_DOTS: "Dotted Block", OBJ_BLOCK_STRIPES: "Panel Block",
    OBJ_BLOCK_CROSS: "Cross Block", OBJ_BLOCK_CIRCLE: "Circle Block",
}

CATEGORIES = {
    "Blocks": [OBJ_BLOCK, OBJ_HALF_BLOCK, OBJ_BLOCK_FADED, OBJ_BLOCK_BRICK, OBJ_BLOCK_BEVEL, OBJ_BLOCK_GRID,
               OBJ_BLOCK_DOTS, OBJ_BLOCK_STRIPES, OBJ_BLOCK_CROSS, OBJ_BLOCK_CIRCLE,
               OBJ_OUTLINE_LINE, OBJ_OUTLINE_CORNER_PIXEL, OBJ_OUTLINE_3SIDE, OBJ_OUTLINE_OPPOSITE, OBJ_OUTLINE_CORNER2],
    "Dangers": [OBJ_SPIKE, OBJ_HALF_SPIKE, OBJ_GROUND_SPIKE, OBJ_SAW_2, OBJ_SAW, OBJ_SAW_3],
    "Gameplay": [OBJ_PORTAL_CUBE, OBJ_PORTAL_SHIP, OBJ_PORTAL_BALL, OBJ_PORTAL_UFO, OBJ_PORTAL_WAVE, OBJ_PORTAL_GRAV_DOWN, OBJ_PORTAL_GRAV_UP, OBJ_PAD_YELLOW, OBJ_ORB_YELLOW, OBJ_PAD_PURPLE, OBJ_ORB_PURPLE, OBJ_PAD_BLUE, OBJ_ORB_BLUE, OBJ_SPAWN, OBJ_COLOR_TRIGGER, OBJ_GROUND_COLOR_TRIGGER, OBJ_END_TRIGGER,
                 OBJ_SPEED_05X, OBJ_SPEED_1X, OBJ_SPEED_2X, OBJ_SPEED_3X],
    "Decor": [OBJ_GEAR_L, OBJ_GEAR_M, OBJ_GEAR_S, OBJ_DECO_SPIKE_L, OBJ_DECO_SPIKE_M, OBJ_DECO_CHAIN, OBJ_CLOUD_1, OBJ_CLOUD_2, OBJ_PULSEROD_1, OBJ_PULSEROD_2, OBJ_PULSEROD_3],
    "Pulse": [OBJ_PULSE_CIRCLE, OBJ_PULSE_HOLLOW, OBJ_PULSE_HEART, OBJ_PULSE_DIAMOND, OBJ_PULSE_STAR, OBJ_PULSE_NOTE]
}

NON_ROTATABLE = [OBJ_COLOR_TRIGGER, OBJ_GROUND_COLOR_TRIGGER, OBJ_END_TRIGGER, OBJ_BLOCK, OBJ_BLOCK_FADED, OBJ_BLOCK_BRICK, OBJ_ORB_YELLOW, OBJ_ORB_PURPLE, OBJ_ORB_BLUE, OBJ_SPAWN, OBJ_SAW, OBJ_SAW_2, OBJ_SAW_3, OBJ_CLOUD_1, OBJ_CLOUD_2, OBJ_PULSE_CIRCLE, OBJ_PULSE_HOLLOW, OBJ_PULSE_HEART, OBJ_PULSE_DIAMOND, OBJ_PULSE_STAR, OBJ_PULSE_NOTE, OBJ_SPEED_05X, OBJ_SPEED_1X, OBJ_SPEED_2X, OBJ_SPEED_3X, OBJ_SPEED_4X]

# Layering: layer 0 draws last (on top), layer MAX_LAYERS-1 draws first (furthest back)
MAX_LAYERS = 10

SPEED_TRIGGER_TYPES = (OBJ_SPEED_05X, OBJ_SPEED_1X, OBJ_SPEED_2X, OBJ_SPEED_3X)
_SPEED_TRIGGER_BLOCKS_PER_SEC = {OBJ_SPEED_05X: 8.41, OBJ_SPEED_1X: 10.42, OBJ_SPEED_2X: 12.95, OBJ_SPEED_3X: 15.62}

def speed_for_trigger(obj_type):
    """World units/frame for a speed-trigger object type, or None if not one."""
    bps = _SPEED_TRIGGER_BLOCKS_PER_SEC.get(obj_type)
    return None if bps is None else bps * GRID_SIZE / FPS

def apply_speed_triggers(objects, x, level):
    """Activate any not-yet-activated speed trigger at or behind x, updating level.speed."""
    for obj in objects:
        if obj.type in SPEED_TRIGGER_TYPES and not getattr(obj, 'activated', False) and x >= obj.x:
            obj.activated = True
            level.speed = speed_for_trigger(obj.type)