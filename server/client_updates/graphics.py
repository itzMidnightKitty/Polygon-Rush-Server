import pygame
import math
from config import S
import config
import random

def draw_world_background(surface, scroll_x, scroll_y, bg_color, design_idx):
    bg_tuple = (int(bg_color[0]), int(bg_color[1]), int(bg_color[2]))
    surface.fill(bg_tuple)
    px_factor, py_factor = 0.3, 0.3
    offset_x = (scroll_x * px_factor)
    offset_y = (scroll_y * py_factor)
    lighter_bg = (min(255, bg_tuple[0]+30), min(255, bg_tuple[1]+30), min(255, bg_tuple[2]+30))
    
    if design_idx == 0:
        random.seed(42)
        for _ in range(250):
            sz = random.randint(S(10), S(40))
            x = (random.randint(0, config.BASE_W * 2) - offset_x) % (config.BASE_W + sz)
            y = (random.randint(0, config.BASE_H * 2) - offset_y) % (config.BASE_H + sz)
            pygame.draw.rect(surface, lighter_bg, (x, y, sz, sz), max(1, S(2)))
    elif design_idx == 1:
        random.seed(42)
        for _ in range(150):
            r = random.randint(S(15), S(50))
            x = (random.randint(0, config.BASE_W * 2) - offset_x) % (config.BASE_W + r*2)
            y = (random.randint(0, config.BASE_H * 2) - offset_y) % (config.BASE_H + r*2)
            pygame.draw.circle(surface, lighter_bg, (int(x), int(y)), r, max(1, S(3)))
    elif design_idx == 2:
        random.seed(42)
        for _ in range(200):
            sz = random.randint(S(20), S(60))
            x = (random.randint(0, config.BASE_W * 2) - offset_x) % (config.BASE_W + sz)
            y = (random.randint(0, config.BASE_H * 2) - offset_y) % (config.BASE_H + sz)
            pygame.draw.polygon(surface, lighter_bg, [(x, y-sz//2), (x+sz//2, y), (x, y+sz//2), (x-sz//2, y)], max(1, S(2)))
    elif design_idx == 3:
        random.seed(42)
        for _ in range(100):
            w = random.randint(S(50), S(200))
            h = random.randint(S(10), S(30))
            x = (random.randint(0, config.BASE_W * 2) - offset_x) % (config.BASE_W + w)
            y = (random.randint(0, config.BASE_H * 2) - offset_y) % (config.BASE_H + h)
            pygame.draw.rect(surface, lighter_bg, (x, y, w, h), max(1, S(3)), border_radius=S(5))

def draw_world_ground(surface, scroll_x, scroll_y, zoom, ground_color, design_idx, gamemode):
    gy = config.GROUND_Y - scroll_y
    cy = config.CEILING_Y - scroll_y
    gnd_tuple = (int(ground_color[0]), int(ground_color[1]), int(ground_color[2]))

    if gamemode in ('ship', 'ball', 'wave', 'ufo') and cy > 0:
        screen_cy = S(cy * zoom)
        ceiling_rect = pygame.Rect(0, 0, config.RENDER_W, screen_cy)
        surface.set_clip(ceiling_rect)
        pygame.draw.rect(surface, gnd_tuple, ceiling_rect)
        pygame.draw.line(surface, config.WHITE, (0, screen_cy), (config.RENDER_W, screen_cy), max(1, S(3)))
        
        offset = (scroll_x * zoom) % (100 * zoom)
        y = cy * zoom
        size = 100 * zoom
        size_scaled = S(size)
        if size_scaled > 2:
            for i in range(-1, int(config.RENDER_W / size_scaled) + 2):
                x = (i * size) - offset
                if design_idx == 0:
                    pygame.draw.rect(surface, config.BLACK, (S(x + size*0.1), S(y - size*0.9), S(size*0.8), S(size*0.8)), S(2))
                elif design_idx == 1:
                    pygame.draw.circle(surface, config.BLACK, (S(x + size*0.5), S(y - size*0.5)), S(size*0.4), S(2))
                elif design_idx == 2:
                    pygame.draw.line(surface, config.BLACK, (S(x + size*0.1), S(y - size*0.1)), (S(x + size*0.9), S(y - size*0.9)), S(2))
                elif design_idx == 3:
                    pygame.draw.polygon(surface, config.BLACK, [(S(x + size*0.5), S(y - size*0.1)), (S(x + size*0.9), S(y - size*0.5)), (S(x + size*0.5), S(y - size*0.9)), (S(x + size*0.1), S(y - size*0.5))], S(2))
        
        surface.set_clip(None)

    if gy * zoom < config.BASE_H:
        screen_gy = S(gy * zoom)
        ground_rect = pygame.Rect(0, screen_gy, config.RENDER_W, config.RENDER_H - screen_gy)
        surface.set_clip(ground_rect)
        pygame.draw.rect(surface, gnd_tuple, ground_rect)
        pygame.draw.line(surface, config.WHITE, (0, screen_gy), (config.RENDER_W, screen_gy), max(1, S(3)))
        
        offset = (scroll_x * zoom) % (100 * zoom)
        y = gy * zoom
        size = 100 * zoom
        size_scaled = S(size)
        
        if size_scaled > 2:
            for i in range(-1, int(config.RENDER_W / size_scaled) + 2):
                x = (i * size) - offset
                if design_idx == 0:
                    pygame.draw.rect(surface, config.BLACK, (S(x + size*0.1), S(y + size*0.1), S(size*0.8), S(size*0.8)), S(2))
                elif design_idx == 1:
                    pygame.draw.circle(surface, config.BLACK, (S(x + size*0.5), S(y + size*0.5)), S(size*0.4), S(2))
                elif design_idx == 2:
                    pygame.draw.line(surface, config.BLACK, (S(x + size*0.1), S(y + size*0.9)), (S(x + size*0.9), S(y + size*0.1)), S(2))
                elif design_idx == 3:
                    pygame.draw.polygon(surface, config.BLACK, [(S(x + size*0.5), S(y + size*0.9)), (S(x + size*0.9), S(y + size*0.5)), (S(x + size*0.5), S(y + size*0.1)), (S(x + size*0.1), S(y + size*0.5))], S(2))
        
        surface.set_clip(None)

def draw_difficulty_face(surface, x, y, size, difficulty):
    center = (S(x + size//2), S(y + size//2))
    radius = S(size // 2)
    
    colors = {
        config.DIFF_AUTO: (150, 150, 150),
        config.DIFF_EASY: (50, 150, 255),
        config.DIFF_NORMAL: (50, 255, 50),
        config.DIFF_HARD: (255, 200, 50),
        config.DIFF_HARDER: (255, 100, 50),
        config.DIFF_INSANE: (200, 50, 200),
        config.DIFF_DEMON_EASY: (100, 50, 200), # Purple
        config.DIFF_DEMON_MEDIUM: (200, 50, 150), # Pinkish purple
        config.DIFF_DEMON_HARD: (220, 0, 0), # Red
        config.DIFF_DEMON_INSANE: (150, 0, 0), # Dark Red
        config.DIFF_DEMON_EXTREME: (80, 0, 0) # Very Dark Red
    }
    
    color = colors.get(difficulty, config.WHITE)
    
    # Horns for Demon
    if difficulty in (config.DIFF_DEMON_EASY, config.DIFF_DEMON_MEDIUM, config.DIFF_DEMON_HARD, config.DIFF_DEMON_INSANE, config.DIFF_DEMON_EXTREME):
        horn_color = config.WHITE
        if difficulty == config.DIFF_DEMON_EXTREME: horn_color = (200, 200, 200)
        
        pygame.draw.polygon(surface, horn_color, [
            (S(x + size*0.15), S(y + size*0.3)),
            (S(x - size*0.1), S(y - size*0.1)),
            (S(x + size*0.35), S(y + size*0.15))
        ])
        pygame.draw.polygon(surface, horn_color, [
            (S(x + size*0.85), S(y + size*0.3)),
            (S(x + size*1.1), S(y - size*0.1)),
            (S(x + size*0.65), S(y + size*0.15))
        ])
        pygame.draw.polygon(surface, config.BLACK, [
            (S(x + size*0.15), S(y + size*0.3)),
            (S(x - size*0.1), S(y - size*0.1)),
            (S(x + size*0.35), S(y + size*0.15))
        ], max(1, S(2)))
        pygame.draw.polygon(surface, config.BLACK, [
            (S(x + size*0.85), S(y + size*0.3)),
            (S(x + size*1.1), S(y - size*0.1)),
            (S(x + size*0.65), S(y + size*0.15))
        ], max(1, S(2)))
        
        if difficulty == config.DIFF_DEMON_EXTREME:
            pygame.draw.polygon(surface, horn_color, [
                (S(x + size*0.05), S(y + size*0.4)),
                (S(x - size*0.15), S(y + size*0.2)),
                (S(x + size*0.25), S(y + size*0.3))
            ])
            pygame.draw.polygon(surface, config.BLACK, [
                (S(x + size*0.05), S(y + size*0.4)),
                (S(x - size*0.15), S(y + size*0.2)),
                (S(x + size*0.25), S(y + size*0.3))
            ], max(1, S(2)))
            pygame.draw.polygon(surface, horn_color, [
                (S(x + size*0.95), S(y + size*0.4)),
                (S(x + size*1.15), S(y + size*0.2)),
                (S(x + size*0.75), S(y + size*0.3))
            ])
            pygame.draw.polygon(surface, config.BLACK, [
                (S(x + size*0.95), S(y + size*0.4)),
                (S(x + size*1.15), S(y + size*0.2)),
                (S(x + size*0.75), S(y + size*0.3))
            ], max(1, S(2)))
    
    # Face background
    pygame.draw.circle(surface, color, center, radius)
    pygame.draw.circle(surface, config.BLACK, center, radius, max(1, S(3)))
    
    eye_y = S(y + size * 0.4)
    left_eye = (S(x + size * 0.3), eye_y)
    right_eye = (S(x + size * 0.7), eye_y)
    eye_r = S(size*0.12)
    pupil_r = S(size*0.05)
    
    # NA / Unrated
    if difficulty == config.DIFF_AUTO:
        pygame.draw.circle(surface, config.BLACK, left_eye, eye_r)
        pygame.draw.circle(surface, config.BLACK, right_eye, eye_r)
        pygame.draw.circle(surface, config.WHITE, (left_eye[0] + S(1), left_eye[1] - S(1)), pupil_r)
        pygame.draw.circle(surface, config.WHITE, (right_eye[0] + S(1), right_eye[1] - S(1)), pupil_r)
        
    # Easy
    elif difficulty == config.DIFF_EASY:
        pygame.draw.circle(surface, config.BLACK, left_eye, eye_r)
        pygame.draw.circle(surface, config.BLACK, right_eye, eye_r)
        pygame.draw.circle(surface, config.WHITE, (left_eye[0] + S(1), left_eye[1] - S(1)), pupil_r)
        pygame.draw.circle(surface, config.WHITE, (right_eye[0] + S(1), right_eye[1] - S(1)), pupil_r)
        # Open smile
        pygame.draw.polygon(surface, config.BLACK, [
            (S(x + size*0.2), S(y + size*0.55)), 
            (S(x + size*0.8), S(y + size*0.55)), 
            (S(x + size*0.5), S(y + size*0.85))
        ])
        
    # Normal
    elif difficulty == config.DIFF_NORMAL:
        pygame.draw.circle(surface, config.BLACK, left_eye, eye_r)
        pygame.draw.circle(surface, config.BLACK, right_eye, eye_r)
        pygame.draw.circle(surface, config.WHITE, (left_eye[0] + S(1), left_eye[1] - S(1)), pupil_r)
        pygame.draw.circle(surface, config.WHITE, (right_eye[0] + S(1), right_eye[1] - S(1)), pupil_r)
        # Simple curve smile
        rect = pygame.Rect(S(x + size*0.2), S(y + size*0.35), S(size*0.6), S(size*0.4))
        pygame.draw.arc(surface, config.BLACK, rect, 3.14, 0, max(1, S(3)))
        
    # Hard
    elif difficulty == config.DIFF_HARD:
        pygame.draw.circle(surface, config.BLACK, left_eye, eye_r)
        pygame.draw.circle(surface, config.BLACK, right_eye, eye_r)
        pygame.draw.circle(surface, config.WHITE, (left_eye[0] + S(1), left_eye[1] - S(1)), pupil_r)
        pygame.draw.circle(surface, config.WHITE, (right_eye[0] + S(1), right_eye[1] - S(1)), pupil_r)
        # Straight mouth
        pygame.draw.rect(surface, config.BLACK, (S(x + size*0.35), S(y + size*0.65), S(size*0.3), S(size*0.08)))
        # Slight sad eyebrows
        pygame.draw.line(surface, config.BLACK, (left_eye[0]-S(4), eye_y-S(7)), (left_eye[0]+S(6), eye_y-S(5)), max(1, S(3)))
        pygame.draw.line(surface, config.BLACK, (right_eye[0]+S(6), eye_y-S(7)), (right_eye[0]-S(4), eye_y-S(5)), max(1, S(3)))
        
    # Harder
    elif difficulty == config.DIFF_HARDER:
        pygame.draw.circle(surface, config.BLACK, left_eye, eye_r)
        pygame.draw.circle(surface, config.BLACK, right_eye, eye_r)
        pygame.draw.circle(surface, config.WHITE, (left_eye[0] + S(1), left_eye[1] - S(1)), pupil_r)
        pygame.draw.circle(surface, config.WHITE, (right_eye[0] + S(1), right_eye[1] - S(1)), pupil_r)
        # Angry eyebrows
        pygame.draw.line(surface, config.BLACK, (left_eye[0]-S(6), eye_y-S(10)), (left_eye[0]+S(8), eye_y-S(3)), max(1, S(4)))
        pygame.draw.line(surface, config.BLACK, (right_eye[0]+S(6), eye_y-S(10)), (right_eye[0]-S(8), eye_y-S(3)), max(1, S(4)))
        # Frown
        rect = pygame.Rect(S(x + size*0.3), S(y + size*0.65), S(size*0.4), S(size*0.3))
        pygame.draw.arc(surface, config.BLACK, rect, 0, 3.14, max(1, S(3)))
        
    # Insane
    elif difficulty == config.DIFF_INSANE:
        pygame.draw.circle(surface, config.BLACK, left_eye, eye_r)
        pygame.draw.circle(surface, config.BLACK, right_eye, eye_r)
        pygame.draw.circle(surface, config.WHITE, (left_eye[0] + S(1), left_eye[1] - S(1)), pupil_r)
        pygame.draw.circle(surface, config.WHITE, (right_eye[0] + S(1), right_eye[1] - S(1)), pupil_r)
        # Very angry eyebrows
        pygame.draw.line(surface, config.BLACK, (left_eye[0]-S(8), eye_y-S(12)), (left_eye[0]+S(10), eye_y-S(2)), max(1, S(5)))
        pygame.draw.line(surface, config.BLACK, (right_eye[0]+S(8), eye_y-S(12)), (right_eye[0]-S(10), eye_y-S(2)), max(1, S(5)))
        # Open mouth
        pygame.draw.polygon(surface, config.BLACK, [
            (S(x + size*0.3), S(y + size*0.75)), 
            (S(x + size*0.7), S(y + size*0.75)), 
            (S(x + size*0.5), S(y + size*0.6))
        ])
        
    # Demon
    elif difficulty in (config.DIFF_DEMON_EASY, config.DIFF_DEMON_MEDIUM, config.DIFF_DEMON_HARD, config.DIFF_DEMON_INSANE, config.DIFF_DEMON_EXTREME):
        # Green glowing eyes
        pygame.draw.circle(surface, (0, 255, 0), left_eye, eye_r)
        pygame.draw.circle(surface, (0, 255, 0), right_eye, eye_r)
        pygame.draw.circle(surface, config.WHITE, (left_eye[0] + S(1), left_eye[1] - S(1)), pupil_r)
        pygame.draw.circle(surface, config.WHITE, (right_eye[0] + S(1), right_eye[1] - S(1)), pupil_r)
        # Demonic angry eyebrows
        pygame.draw.line(surface, config.BLACK, (left_eye[0]-S(8), eye_y-S(10)), (left_eye[0]+S(12), eye_y), max(1, S(6)))
        pygame.draw.line(surface, config.BLACK, (right_eye[0]+S(8), eye_y-S(10)), (right_eye[0]-S(12), eye_y), max(1, S(6)))
        # Sharp teeth mouth (zigzag)
        m_y = y + size*0.65
        pygame.draw.polygon(surface, config.BLACK, [
            (S(x + size*0.2), S(m_y)),
            (S(x + size*0.35), S(m_y + size*0.15)),
            (S(x + size*0.5), S(m_y)),
            (S(x + size*0.65), S(m_y + size*0.15)),
            (S(x + size*0.8), S(m_y)),
            (S(x + size*0.7), S(m_y + size*0.25)),
            (S(x + size*0.3), S(m_y + size*0.25))
        ])
        pygame.draw.polygon(surface, config.WHITE, [
            (S(x + size*0.25), S(m_y + size*0.05)),
            (S(x + size*0.35), S(m_y + size*0.12)),
            (S(x + size*0.5), S(m_y + size*0.05)),
            (S(x + size*0.65), S(m_y + size*0.12)),
            (S(x + size*0.75), S(m_y + size*0.05)),
            (S(x + size*0.65), S(m_y + size*0.2)),
            (S(x + size*0.35), S(m_y + size*0.2))
        ])