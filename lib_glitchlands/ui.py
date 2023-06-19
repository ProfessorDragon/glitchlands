import pygame
from lib import*

def create_graphic(gc, *args, **kwargs):
    obj = Graphic(gc, *args, **kwargs)
    gc.ui_objects.append(obj)
    return obj

def create_button(gc, *args, **kwargs):
    obj = Button(gc, *args, **kwargs)
    gc.ui_objects.append(obj)
    return obj

def create_text(gc, text, cx=None, cy=None):
    return create_graphic(gc, gc.assets.font_outlined.render(text), cx=cx, cy=cy)

class Graphic(pygame.sprite.Sprite):
    def __init__(self, gc, frames, cx=None, cy=None, anim_delay=3):
        super().__init__()
        self.gc = gc
        self.update_frames(frames)
        if cx is None: cx = gc.game_width//2
        if cy is None: cy = gc.game_height//2
        self.rect = pygame.Rect(cx-self.width//2, cy-self.height//2, self.width, self.height)
        self.xofs, self.yofs = 0, 0
        self.anim_frame = 0
        self.anim_delay = anim_delay
        self.fixed = False # has fixed position on scrolling menu (such as map ui)
        self.hide_ok = False # whether it should be hidden when jump is pressed (such as map ui)
    def update_frames(self, frames):
        self.frames = [frames] if isinstance(frames, pygame.Surface) else frames
        self.width, self.height = self.frames[0].get_size()
    def update(self):
        self.anim_frame += 1
    @property
    def adjusted_rect(self):
        return pygame.Rect(self.rect.x+self.xofs, self.rect.y+self.yofs, self.rect.w, self.rect.h)
    def draw(self):
        return self.gc.screen.blit(self.frames[(self.anim_frame//self.anim_delay)%len(self.frames)], self.adjusted_rect)

class Button(Graphic):
    def __init__(self, gc, frames, indexes=None, cx=None, cy=None):
        super().__init__(gc, frames, cx=cx, cy=cy)
        if indexes is None: self.indexes = []
        elif type(indexes[0]) == tuple: self.indexes = indexes
        else: self.indexes = [indexes]
    def update_frames(self, frames):
        super().update_frames(frames)
        self.height += 2
        self.image = Assets.sized_surface(self.width, self.height)
        self.image.blit(self.frames[0], (0, 2))
        self.image.blit(self.frames[0], (0, 0))
        self.pressed_image = Assets.sized_surface(self.width, self.height)
        self.pressed_image.blit(self.frames[0], (0, 2))
    def draw(self):
        return self.gc.screen.blit(self.pressed_image if self.gc.selection.idx in self.indexes else self.image, self.adjusted_rect)
