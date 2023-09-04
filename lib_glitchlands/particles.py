import math, random
import pygame

class Particle:
    def __init__(self, gc, name, center):
        self.gc = gc
        if name is not None:
            self.frames = self.gc.assets.particles[name]
            if isinstance(self.frames, pygame.Surface): self.frames = [self.frames]
            self.rect = pygame.Rect(
                center[0]-self.frames[0].get_width()//2,
                center[1]-self.frames[0].get_height()//2,
                self.frames[0].get_width(),
                self.frames[0].get_height()
            )
        self.anim_delay = 3
        self.anim_frame = 0
        self.xv = 0
        self.yv = 0
        self.size = 1
        self.x_speed_decay = 1
        self.y_speed_decay = 1
        self.opacity = 1
        self.show_low_detail = False
        self.self_destruct = False

    def update(self):
        self.xv *= self.x_speed_decay
        self.yv *= self.y_speed_decay
        self.rect.x += self.xv
        self.rect.y += self.yv
        self.anim_frame += 1

    def draw(self):
        im = self.frames[(self.anim_frame//self.anim_delay)%len(self.frames)].copy()
        x, y = self.rect.x-self.gc.xscroll, self.rect.y
        if self.opacity < 1:
            im.set_alpha(self.opacity*255)
        if self.size != 1:
            im = pygame.transform.scale(im, (int(self.rect.w*self.size), int(self.rect.h*self.size)))
            x += (self.rect.w-self.rect.w*self.size)//2
            y += (self.rect.h-self.rect.h*self.size)//2
        return self.gc.screen.blit(im, (x, y))

class AnimatedParticle(Particle):
    def __init__(self, gc, name, center, anim_delay=3):
        super().__init__(gc, name, center)
        self.anim_delay = anim_delay

    def update(self):
        super().update()
        if self.anim_frame//self.anim_delay >= len(self.frames):
            self.self_destruct = True

class FadeOutParticle(Particle):
    def __init__(self, gc, name, center, fade_time=12, xv=0, yv=0, x_speed_decay=.85, y_speed_decay=.85, size_change=0):
        super().__init__(gc, name, center)
        self.xv = xv
        self.yv = yv
        self.x_speed_decay = x_speed_decay
        self.y_speed_decay = y_speed_decay
        self.size_change = size_change
        self.fade_time = fade_time

    def update(self):
        super().update()
        if self.fade_time != 0: self.opacity -= 1/self.fade_time
        self.size += self.size_change
        if self.opacity <= 0 or self.size <= 0: self.self_destruct = True

class ShieldEquipParticle(Particle):
    def __init__(self, gc, center, hflip):
        super().__init__(gc, "shield_equip", center)
        self.frames = (self.frames.sprites_hflip if hflip else self.frames.sprites)[::-1]
        self.magic_number = len(self.frames)*self.anim_delay-1
        self.xv = -1 if hflip else 1
        self.yv = -1
        self.rect.x -= self.magic_number*self.xv
        self.rect.y -= self.magic_number*self.yv+1
    def update(self):
        if self.anim_frame < self.magic_number: super().update()
        self.opacity -= 1/(self.magic_number*2)
        if self.opacity <= 0: self.self_destruct = True

class ShieldBreakParticle(Particle):
    def __init__(self, gc, center, hflip, part):
        super().__init__(gc, "shield_break", center)
        self.frames = (self.frames.sprites_hflip if hflip else self.frames.sprites)[part*8+8:part*8+16]
        self.x_speed_decay = .88
        self.y_speed_decay = .88
        if part == 0: self.xv, self.yv = -4, -1
        elif part == 1: self.xv, self.yv = 3, -3
        elif part == 2: self.xv, self.yv = 1, 4
        if hflip: self.xv *= -1
    def update(self):
        super().update()
        self.opacity -= 0.1
        if self.opacity <= 0: self.self_destruct = True

class ParticleSpawner:
    def __init__(self, gc, names, configs, class_=Particle, count=1, xofs=4, yofs=4, velofs=2, dirofs=15,
                 hflip=False, vflip=False, show_low_detail=False):
        self.gc = gc
        self.particles = []
        if count < 1 or len(names) < 1 or len(configs) < 1: return
        self.names = list(names[:])
        random.shuffle(self.names)
        if hflip != vflip: dirofs *= -1
        for _ in range(count):
            for config in configs:
                for name in self.names:
                    if type(name) in (list, tuple): name = random.choice(name)
                    part = class_(gc, name, **config)
                    part.rect.x += random.random()*xofs-xofs/2
                    part.rect.y += random.random()*yofs-yofs/2
                    velmag = math.sqrt(part.xv**2+part.yv**2)
                    velmag += random.random()*velofs-velofs/2
                    veldir = math.degrees(math.atan2(part.yv, part.xv))
                    veldir += random.random()*dirofs-dirofs/2
                    part.xv = velmag*math.cos(math.radians(veldir))
                    part.yv = velmag*math.sin(math.radians(veldir))
                    if hflip: part.xv *= -1
                    if vflip: part.yv *= -1
                    part.show_low_detail = show_low_detail
                    self.particles.append(part)
                    
    def spawn(self):
        self.gc.push_particle(*self.particles)
