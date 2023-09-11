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

def create_slider(gc, *args, **kwargs):
    obj = Slider(gc, *args, **kwargs)
    gc.ui_objects.append(obj)
    return obj

def create_text(gc, text, cx=None, cy=None, font=None):
    if font is None: font = gc.assets.font_outlined
    return create_graphic(gc, font.render(text), cx=cx, cy=cy)

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
    def __init__(self, gc, frames, indexes=None, cx=None, cy=None, hit_inflate=(4, 4)):
        super().__init__(gc, frames, cx=cx, cy=cy)
        if indexes is None: self.indexes = []
        elif type(indexes[0]) == tuple: self.indexes = indexes
        else: self.indexes = [indexes]
        self.hit_inflate = hit_inflate # used for detecting cursor hovering
    def update_frames(self, frames):
        super().update_frames(frames)
        self.height += 2
        self.unpressed_frames, self.pressed_frames = [], []
        for frame in self.frames:
            im = Assets.sized_surface(self.width, self.height)
            im.blit(frame, (0, 2))
            im.blit(frame, (0, 0))
            self.unpressed_frames.append(im)
            im = Assets.sized_surface(self.width, self.height)
            im.blit(frame, (0, 2))
            if RASPBERRY_PI:
                im.fill((32, 32, 32), special_flags=pygame.BLEND_RGB_ADD)
            self.pressed_frames.append(im)
    def update(self):
        return
    def draw(self):
        return self.gc.screen.blit(
            (self.pressed_frames if self.gc.selection.idx in self.indexes else self.unpressed_frames)[self.anim_frame],
            self.adjusted_rect
        )

class Slider(Button):
    def __init__(self, gc, setting, max_=1, indexes=None, cx=None, cy=None, callback=None):
        super().__init__(gc, gc.assets.ui.get("slider"), indexes, cx=cx, cy=cy, hit_inflate=(16, 8))
        self.setting = setting
        self.callback = callback
        self.max = max_/(len(self.frames)-1)
        self.anim_frame = min(max(int(round(Settings.get(setting)/self.max)), 0), len(self.frames)-1)
    def set(self, frame):
        prev = round(self.anim_frame*self.max, 2)
        self.anim_frame = min(max(frame, 0), len(self.frames)-1)
        cur = round(self.anim_frame*self.max, 2)
        Settings.set(self.setting, cur)
        Settings.save()
        if callable(self.callback) and prev != cur: self.callback(prev, cur)
    def set_percent(self, percent):
        self.set(int(round(percent*(len(self.frames)-1))))
    def increment(self, amount):
        self.set(self.anim_frame+amount)
