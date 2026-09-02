import pygame
import config
from config import S

class TextInput:
    def __init__(self, x, y, w, h, font, placeholder="", is_password=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.logical_rect = pygame.Rect(x, y, w, h)
        self.font = font
        self.text = ""
        self.placeholder = placeholder
        self.is_password = is_password
        self.active = False
        
    def handle_event(self, event, logical_mouse):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.logical_rect.collidepoint(logical_mouse):
                self.active = True
            else:
                self.active = False
                
        if event.type == pygame.KEYDOWN and self.active:
            ctrl = pygame.key.get_mods() & pygame.KMOD_CTRL
            if event.key == pygame.K_TAB:
                return "tab"
            elif event.key == pygame.K_RETURN:
                return "submit"
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif ctrl and event.key == pygame.K_v:
                self.text = (self.text + self._get_clipboard_text())[:40]
            elif ctrl and event.key == pygame.K_c:
                self._set_clipboard_text(self.text)
            elif ctrl and event.key == pygame.K_x:
                self._set_clipboard_text(self.text)
                self.text = ""
            elif ctrl and event.key == pygame.K_a:
                pass  # no selection model to select-all into; harmless no-op
            else:
                if len(self.text) < 40 and event.unicode and event.unicode.isprintable() and event.unicode != ' ':
                    self.text += event.unicode
        return None

    def _get_clipboard_text(self):
        try:
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            raw = pygame.scrap.get(pygame.SCRAP_TEXT)
            if not raw:
                return ""
            text = raw.decode('utf-8', errors='ignore').rstrip('\x00').strip()
            return ''.join(c for c in text if c.isprintable() and c != ' ')
        except Exception:
            return ""

    def _set_clipboard_text(self, text):
        try:
            if not pygame.scrap.get_init():
                pygame.scrap.init()
            pygame.scrap.put(pygame.SCRAP_TEXT, text.encode('utf-8'))
        except Exception:
            pass
                    
    def draw(self, surface):
        s_rect = pygame.Rect(S(self.logical_rect.x), S(self.logical_rect.y), S(self.logical_rect.w), S(self.logical_rect.h))
        color = config.CYAN if self.active else config.GRAY
        pygame.draw.rect(surface, (30, 30, 40), s_rect, 0, S(5))
        pygame.draw.rect(surface, color, s_rect, max(1, S(2)), S(5))
        
        display_text = self.text
        if self.is_password:
            display_text = "*" * len(self.text)
            
        if not self.text and not self.active:
            t_surf = self.font.render(self.placeholder, True, config.GRAY)
        else:
            t_surf = self.font.render(display_text, True, config.WHITE)
            
        surface.blit(t_surf, (s_rect.x + S(10), s_rect.centery - t_surf.get_height()//2))
