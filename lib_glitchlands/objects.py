import math, random
from functools import cmp_to_key

import pygame

from lib import*
from lib_glitchlands import*
from lib_glitchlands import player, particles


## FUNCTIONS ##

def create_object(gc, level, config, **kwargs):
    args = [gc, level, config]
    typ = config["type"]
    if typ <= OBJTYPE_BLOCK: return Block(*args, **kwargs)
    return {
        OBJTYPE_TEXT: FontCharacter,
        OBJTYPE_DECO: Decoration,
        OBJTYPE_TRIGGER: AreaTrigger,
        OBJTYPE_UPGRADE: UpgradeBox,
        OBJTYPE_FIRETRAP: FireTrap,
        OBJTYPE_CRUSHER: Crusher,
        OBJTYPE_GLITCHZONE: GlitchZone,
        OBJTYPE_FALLINGPLATFORM: FallingPlatform,
        OBJTYPE_BUTTON: Button,
        OBJTYPE_TIMEDGATE: TimedGate,
        OBJTYPE_CRYSTALBARRIER: CrystalBarrier,
        OBJTYPE_UPGRADETIP: UpgradeTip,
        OBJTYPE_ONEWAYGATE: OneWayGate,
        OBJTYPE_GOO: Goo,
        OBJTYPE_NPC: Npc,
        OBJTYPE_SAWTRAP: SawTrap,
        OBJTYPE_VINES: Vines,
        OBJTYPE_BAT: Bat,
        OBJTYPE_HITBUTTON: HitButton,
        OBJTYPE_VIRUSBOSS: VirusBoss,
    }[typ](*args, **kwargs)

def generate_tip_image(gc, text, *icon_nums):
    icons = gc.assets.ui["key_icons"]
    text_image = gc.assets.font_outlined.render(text)
    if len(icon_nums) == 0:
        return text_image
    icon_image = Assets.sized_surface((icons[0].get_width()+2)*len(icon_nums)-2, icons[0].get_height())
    for i, icon_num in enumerate(icon_nums):
        icon_image.blit(icons.get(x=1 if RASPBERRY_PI else 0, y=icon_num), ((icons[0].get_width()+2)*i, 0))
    surface = Assets.sized_surface(
        max(icon_image.get_width(), text_image.get_width()),
        icon_image.get_height()+4+text_image.get_height()
    )
    surface.blit(
        icon_image,
        (surface.get_width()//2-icon_image.get_width()//2, 0)
    )
    surface.blit(
        text_image,
        (surface.get_width()//2-text_image.get_width()//2, icon_image.get_height()+4)
    )
    return surface


## CLASSES ##

class Object(pygame.sprite.Sprite):
    def __init__(self, gc, level, config=None, screen_xofs=0):
        super().__init__()
        self.gc = gc
        self.level = level
        self.screen_xofs = screen_xofs
        self.tilew, self.tileh = 32, 32
        self.update_config(config or {})
    def update_config(self, config):
        self.config = config
        self.num = config.get("num", 0)
        self.type = config.get("type", 0)
        self.x = config.get("x", 0)+self.screen_xofs
        self.y = config.get("y", 0)
        self.spawn_x, self.spawn_y = self.x, self.y
        self.layer = config.get("layer", 0)
        self.image = None # specify either image or frames if self.draw is not overridden
        self.frames = []
        self.anim = "idle" # only used if self.draw is not overridden
        self.anim_frame = 0
        self.anim_delay = 3
        self.rect = pygame.Rect(self.x, self.y, self.tilew, self.tileh)
        self.hitbox = None
        self.collides = COLLISION_NONE
        self.collide_sound = None # currently only used for blocks when they are stepped on or hit from below
        self.loaded = False
        self.self_destruct = False
    def update_hitbox(self):
        self.hitbox = self.rect.copy()
    def copy(self):
        return self.__class__(self.gc, self.level, self.config)
    def not_loaded(self, x_threshold=False, distance_threshold=False):
        if self.loaded: return False # not loaded previously
        if self.level.level_pos != self.gc.level.level_pos: return True # on the same level
        if distance_threshold and not self.rect.colliderect(
                self.gc.player.hitbox.inflate(int(self.gc.game_width*.7), int(self.gc.game_height*.7))
            ):
            return True
        if x_threshold and not \
                (self.gc.scroll_bounds//2 < self.gc.player.hitbox.centerx < self.gc.game_width-self.gc.scroll_bounds//2):
            return True
        return False
    def kill_if_offscreen(self):
        if self.rect.right-self.gc.xscroll < 0 or self.rect.left-self.gc.xscroll > self.gc.game_width or \
            self.rect.bottom < 0 or self.rect.top > self.gc.game_height:
            self.self_destruct = True
    def collides_horizontal(self, entity, dx=0):
        return self.collides != COLLISION_NONE and self.hitbox.colliderect(entity.hitbox)
    def collides_vertical(self, entity, dy=0):
        return self.collides != COLLISION_NONE and self.hitbox.colliderect(entity.hitbox)
    def collides_attack(self, entity, hitbox):
        return False
    def update(self):
        pass
    def blit_rect(self, rect, color, width=0, xofs=0, yofs=0):
        return pygame.draw.rect(self.gc.screen, color, (rect.x-self.gc.xscroll+xofs, rect.y+yofs, rect.w, rect.h), width)
    def blit_image(self, im, rect, xofs=0, yofs=0, area=None):
        return self.gc.screen.blit(im, (rect.x-self.gc.xscroll+xofs, rect.y+yofs), area)
    def draw_hitbox(self):
        if self.collides == COLLISION_NONE or self.hitbox is None: return
        return self.blit_rect(self.hitbox, {
            COLLISION_BLOCK: GREEN,
            COLLISION_PASS: BLUE,
            COLLISION_HAZARD: RED,
            COLLISION_SHIELDBREAK: MAGENTA,
        }.get(self.collides, GRAY), 1)
    def draw(self):
        if len(self.frames) > 0:
            return self.blit_image(self.frames[self.anim_frame//self.anim_delay%len(self.frames)], self.rect)
        elif self.image is not None:
            return self.blit_image(self.image, self.rect)

class Activateable(Object):
    def update_config(self, config):
        super().update_config(config)
        self.link = config.get("link", 0)
        self.activated = False
    def activate(self):
        self.activated = True
    def deactivate(self):
        self.activated = False

class Block(Object):
    def update_config(self, config):
        super().update_config(config)
        self.xrep = config.get("xrep", 1)
        self.yrep = config.get("yrep", 1)
        if self.xrep <= 0 or self.yrep <= 0:
            self.self_destruct = True
            return
        self.style = config.get("style")
        self.fake = False
        if self.style is None:
            if -self.type < len(self.level.terrain_style): self.style = self.level.terrain_style[-self.type]
            else: self.style = 0
        self.anim_delay = 3
        self.anim_duration = 0
        if self.style >= 0:
            if self.type == OBJTYPE_SPIKE:
                self.image = self.gc.assets.terrain[-self.type][0][self.num]
                self.fake = self.style == 1
                if self.style > 1 and self.level.level_pos not in self.gc.visited_levels:
                    self.frames = self.gc.assets.objects.get({2: "dark_spikes", 3: "rgb_spikes"}[self.style])
                    self.anim_duration = self.frames.width
            else:
                self.image = self.gc.assets.terrain[-self.type][self.style][self.num]
                self.collide_sound = "step_rock"
                if self.type == OBJTYPE_BLOCK:
                    if self.style in (0, 1, 2, 5): self.collide_sound = "step_grass"
                    elif self.style == 4: self.collide_sound = "step_wood"
                elif self.type == OBJTYPE_SEMISOLID:
                    if self.style == 0: self.collide_sound = "step_wood"
            self.image = Assets.tile_surface_repetition(self.image, self.xrep, self.yrep, alpha=self.type <= OBJTYPE_SEMISOLID)
            self.frames = [Assets.tile_surface_repetition(frame, self.xrep, self.yrep, alpha=self.type <= OBJTYPE_SEMISOLID) \
                           for frame in self.frames]
            self.rect = pygame.Rect(self.x, self.y, self.image.get_width(), self.image.get_height())
            self.generate_glitch_image()
        else: # invisible block
            self.image = None
            self.rect = pygame.Rect(self.x, self.y, self.tilew*self.xrep, self.tileh*self.yrep)
        if config.get("collide_sound") is not None:
            self.collide_sound = config["collide_sound"]
        self.update_hitbox()
    def update_hitbox(self):
        self.hitbox = self.rect.copy()
        self.collides = COLLISION_BLOCK
        if self.type == OBJTYPE_SPIKE:
            self.collides = COLLISION_HAZARD
            if self.num == 0:
                self.hitbox = pygame.Rect(self.rect.x, self.rect.y+self.tileh//2+1, self.rect.w, self.rect.h-self.tileh//2-1)
            elif self.num == 1:
                self.hitbox = pygame.Rect(self.rect.x+2, self.rect.y, self.rect.w-4, self.rect.h-self.tileh//2-1)
            elif self.num == 2:
                self.hitbox = pygame.Rect(self.rect.x+7, self.rect.y+10, self.rect.w-14, self.rect.h-10)
            elif self.num == 3:
                self.hitbox = pygame.Rect(self.rect.x+7, self.rect.y, self.rect.w-14, self.rect.h-10)
        elif self.type != OBJTYPE_SEMISOLID:
            yofs, hofs = 0, 0 # extend blocks touching the top or bottom border
            if self.rect.top <= 0:
                yofs -= 8
                hofs += 8
            if self.rect.bottom >= self.gc.game_height:
                hofs += 8
            if yofs != 0 or hofs != 0:
                self.hitbox = pygame.Rect(self.rect.x, self.rect.y+yofs*self.tileh, self.rect.w, self.rect.h+hofs*self.tileh)
        if self.type == 0 and self.num in (4, 9, 10, 11, 12, 13):
            self.collides = COLLISION_NONE
        if self.fake:
            self.collides = COLLISION_NONE
    def generate_glitch_image(self):
        if self.image is None or Settings.low_detail:
            self.glitch_image = None
            return
        self.glitch_image = self.image.copy()
        terrain = self.gc.assets.terrain[-self.type]
        if len(terrain) > 1:
            style = self.style
            while style == self.style: style = random.randint(0, len(terrain)-1)
            self.glitch_image.blit(
                terrain[style][self.num],
                (random.randint(0, self.xrep-1)*self.tilew, random.randint(0, self.yrep-1)*self.tileh)
                )
        else:
            for _ in range(2 if self.fake else 1):
                pygame.draw.rect(
                    self.glitch_image,
                    (0, 0, 0, 0),
                    (random.randint(0, self.xrep-1)*self.tilew, random.randint(0, self.yrep-1)*self.tileh, self.tilew, self.tileh)
                    )
    def collides_horizontal(self, entity, dx=0):
        if self.type == OBJTYPE_SEMISOLID: return False
        return self.hitbox.colliderect(entity.hitbox)
    def collides_vertical(self, entity, dy=0):
        if self.type == OBJTYPE_SEMISOLID:
            return self.hitbox.colliderect(entity.hitbox) and entity.hitbox.bottom-self.hitbox.top < dy*2
        return self.hitbox.colliderect(entity.hitbox)
    def update(self):
        if self.anim_duration > 0:
            if self.not_loaded(): return
            self.loaded = True
            self.anim_frame += 1
    def draw(self):
        if self.image is None or (self.anim_duration > 0 and not self.loaded): return
        if self.anim_frame//self.anim_delay > self.anim_duration-1: im = self.image
        else: im = self.frames[self.anim_frame//self.anim_delay+self.anim_duration*self.num]
        if self.gc.glitch_chance >= 0 and self.glitch_image is not None:
            glitch_reduction = self.xrep*self.yrep
            if self.fake: glitch_reduction *= 20
            if random.randint(0, self.gc.glitch_chance)//glitch_reduction == 0:
                im = self.glitch_image
        return self.blit_image(im, self.rect)

class FontCharacter(Object):
    def update_config(self, config):
        super().update_config(config)
        self.image = self.gc.assets.font_outlined.render(self.num)
        self.rect = pygame.Rect(self.x, self.y, 24, 28)
        self.update_hitbox()
        self.ordering = config.get("ordering", 0)
        self.style = config.get("style", 0)
        self.order_timer = self.ordering*1.5+14
        self.flicker_timer = 0
        self.flicker_stage = 0
    def update(self):
        if self.not_loaded(): return
        self.loaded = True
        if self.style == 1:
            if self.flicker_timer > 0:
                self.flicker_timer -= 1
            else:
                self.flicker_stage += 1
                if self.flicker_stage%2 == 1:
                    self.flicker_timer = random.randint(30, 120)
                else: self.flicker_timer = random.randint(1, 3)
        if self.order_timer > 0:
            self.order_timer -= 1
    def draw(self):
        if self.order_timer > 3: return
        rect = self.rect.copy()
        if self.style == 1:
            if self.flicker_stage%2 == 0:
                return
        elif self.style == 2:
            if random.randint(0, 1) == 0: rect.x += random.randint(-1, 1)
            if random.randint(0, 1) == 0: rect.y += random.randint(1, 1)
        if self.order_timer > 0:
            im = self.image.copy()
            im.set_alpha((1-self.order_timer/3)*255)
            return self.blit_image(im, rect, yofs=-self.order_timer*2)
        return self.blit_image(self.image, rect)

class Decoration(Object):
    def update_deco_data(self):
        self.deco_data = [
            {
                "name": "meteor",
                "anim_delay": 6,
                "xofs": int(self.gc.game_width*.6),
                "yofs": -128,
                "xv": -1.5,
                "yv": 3
            },
            {
                "name": "idle",
                "virus": True,
                "anim_delay": 8,
                "yofs": -99,
                "yv": 11,
                "speed_decay": .9
            },
            {
                "name": "split_left",
                "virus": True,
                "xv": -5,
                "speed_decay": .85
            },
            {
                "name": "split_right",
                "virus": True,
                "xv": 5,
                "speed_decay": .85
            },
            {
                "name": "title",
                "anim_delay": 4,
                "yv": 8,
                "speed_decay": .85,
                "load_once": True
            },
            {
                "name": "credit_top",
                "xofs": -80-450//2,
                "xv": 9,
                "speed_decay": .9,
                "load_once": True
            },
            {
                "name": "credit_bottom",
                "xofs": 80-450//2,
                "xv": -9,
                "speed_decay": .9,
                "load_once": True
            },
            {
                "name": "upgrade_deco_1",
                "yv": 11,
                "speed_decay": .85
            },
            {
                "name": "upgrade_deco_2",
                "yv": 11,
                "speed_decay": .85
            },
            {
                "name": "upgrade_deco_3",
                "yv": 11,
                "speed_decay": .85
            }
        ][self.num]
        self.name = self.deco_data["name"]
        self.virus = self.deco_data.get("virus", False)
        self.anim_delay = self.deco_data.get("anim_delay", 1)
        self.scale = self.deco_data.get("scale", 1)
        self.x = self.spawn_x+self.deco_data.get("xofs", 0)
        self.y = self.spawn_y+self.deco_data.get("yofs", 0)
        self.xv = self.deco_data.get("xv", 0)
        self.yv = self.deco_data.get("yv", 0)
        self.speed_decay = self.deco_data.get("speed_decay", 1)
        if self.deco_data.get("hide_low_detail", False) and Settings.low_detail:
            self.self_destruct = True
        if self.deco_data.get("load_once", False) and self.level.level_pos in self.gc.visited_levels:
            self.self_destruct = True
    def update_config(self, config):
        super().update_config(config)
        self.update_deco_data()
        self.frames = (self.gc.assets.virus if self.virus else self.gc.assets.decoration).get(self.name)
        if isinstance(self.frames, pygame.Surface): self.frames = [self.frames]
        self.rect = pygame.Rect(self.x, self.y, self.frames[0].get_width(), self.frames[0].get_height())
    def update_hitbox(self):
        self.x = self.rect.x
        self.y = self.rect.y
        self.hitbox = self.rect.copy()
    def update(self):
        if self.not_loaded(x_threshold=True): return
        self.loaded = True
        self.xv *= self.speed_decay
        self.yv *= self.speed_decay
        self.x += self.xv
        self.y += self.yv
        self.rect.x = self.x
        self.rect.y = self.y
        self.anim_frame += 1

class AreaTrigger(Activateable):
    def update_config(self, config):
        super().update_config(config)
        self.width, self.height = config.get("xrep", 1)*self.tilew, config.get("yrep", 1)*self.tileh
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.update_hitbox()
        self.collides = COLLISION_PASS
    def update_hitbox(self):
        self.hitbox = self.rect.copy()
        if self.num > 0: self.deactivate() # allow checkpoints to be reused
    def activate(self):
        self.activated = True
        if self.num == 0: # game progression
            if self.level.level_pos in self.gc.visited_levels: return
            if self.level.level_pos[0] == 0:
                self.gc.player.abilities.set_all(False)
                self.gc.glitch_chance = 3000
            elif self.level.level_pos[0] == 2:
                self.gc.glitch_chance = 2000
                self.gc.add_split("World 2")
            elif self.level.level_pos[0] == 3:
                self.gc.glitch_chance = 1000
                self.gc.visited_final_world = True
                self.gc.add_split("World 3")
        elif self.num == 1: # checkpoint
            if self.gc.player.fall_frame == 0:
                prev = self.gc.checkpoint.get_set_sides()
                self.gc.set_checkpoint(bottom=self.rect.bottom, centerx=self.rect.centerx)
                if prev != self.gc.checkpoint.get_set_sides():
                    self.gc.player.spawn_particles_checkpoint()
            else:
                self.activated = False
    def collides_any(self, entity):
        # the trigger cannot have not been activated, it must be in the current level,
        # the entity must be a player, and the trigger must collide with the entity
        if not self.activated and self.level.level_pos == self.gc.level.level_pos and \
            isinstance(entity, player.Player) and self.hitbox.colliderect(entity.hitbox):
            self.activate()
        return False
    def collides_horizontal(self, entity, dx=0):
        return self.collides_any(entity)
    def collides_vertical(self, entity, dy=0):
        return self.collides_any(entity)
    def draw(self):
        return

class UpgradeBox(Object):
    def update_config(self, config):
        super().update_config(config)
        self.frames = self.gc.assets.objects.get("upgrade_stand")
        self.rect = pygame.Rect(self.x, self.y, self.frames[0].get_width(), self.frames[0].get_height())
        self.update_hitbox()
        self.collides = COLLISION_NONE
        self.anim = "open"
        self.upgrade_name = self.gc.player.abilities.all[self.num]
        self.upgrade_sheet = self.gc.assets.objects.get("upgrades")
        if self.gc.player.abilities.get(self.upgrade_name):
            self.anim = "complete"
    def update_hitbox(self):
        self.hitbox = pygame.Rect(self.rect.x+16, self.rect.y+18, self.rect.w-32, 32)
    def update(self):
        if self.not_loaded(distance_threshold=True): return
        self.loaded = True
        self.anim_frame += 1
        if self.anim == "open":
            if self.anim_frame//3 >= len(self.frames)-2:
                self.anim = "idle"
                self.anim_frame = 0
        elif self.anim == "idle":
            if self.hitbox.colliderect(self.gc.player.hitbox) and self.gc.player.fall_frame == 0:
                self.anim = "complete"
                clone = self.copy()
                clone.layer = 1
                clone.anim = "collect"
                clone.anim_frame = 0
                self.gc.push_object(clone)
                self.gc.player.upgrade_collect()
        elif self.anim == "collect":
            if self.anim_frame == 12+16:
                self.self_destruct = True
                self.gc.player.freeze_timer = 0
                self.gc.player.freeze_anim = False
                self.gc.player.abilities.enable(self.upgrade_name)
                self.gc.show_transition(num=1)
                self.gc.play_sound("upgrade")
                if self.upgrade_name != "jump":
                    self.gc.add_split(self.gc.player.abilities.upgrade_names.get(self.upgrade_name))
                self.gc.set_checkpoint(bypass_rookie=True, bottom=self.rect.bottom, centerx=self.rect.centerx)
    def draw(self):
        upgrade_image = self.upgrade_sheet.get(
            x=(self.anim_frame//4)%self.upgrade_sheet.width if 3 <= self.num <= 5 else 0,
            y=self.num).copy()
        if self.anim != "collect":
            glitch = self.gc.glitch_chance >= 0 and random.randint(0, self.gc.glitch_chance)//10 == 0
            if self.anim in ("idle", "complete"): idx = -1 if glitch else -2
            else: idx = min(self.anim_frame//3, len(self.frames)-2)
            rect = self.blit_image(self.frames[idx], self.rect)
            if self.anim == "idle":
                upgrade_image.set_alpha(min(self.anim_frame/10, 1)*255)
                self.blit_image(upgrade_image, self.hitbox, yofs=math.sin(self.anim_frame/10)*1.5)
        else:
            xofs = self.gc.player.x+self.gc.player.rectw//2-self.rect.centerx
            yofs = max(self.anim_frame-12, 0)**1.6-self.tileh*3
            rect = self.blit_image(upgrade_image, self.hitbox, xofs=xofs, yofs=yofs)
        return rect

class FireTrap(Object):
    def update_config(self, config):
        super().update_config(config)
        self.frames = self.gc.assets.objects.get("fire_trap")
        self.upside_down = self.num%2 == 1
        self.rect = pygame.Rect(self.x, self.y, self.frames[0].get_width(), self.frames[0].get_height())
        self.update_hitbox()
        self.collides = COLLISION_SHIELDBREAK
        self.on = False
        self.change_timer = 0
        if self.num in (0, 1):
            self.gc.push_object(
                Block(self.gc, self.level, {
                    "x": self.x,
                    "y": self.y+(0 if self.upside_down else self.tileh),
                    "num": 0,
                    "style": -1,
                    "collide_sound": "step_rock"
                })
            )
    def update_hitbox(self):
        self.hitbox = pygame.Rect(self.rect.x+6, self.rect.y+4, self.rect.w-12, 24)
        if self.upside_down: self.hitbox.y += self.tileh
    def update(self):
        self.anim_frame += 1
        if self.change_timer > 0:
            self.change_timer -= 1
        else:
            self.on = not self.on
            if self.on:
                self.collides = COLLISION_SHIELDBREAK
                self.change_timer = 90
            else:
                self.collides = COLLISION_NONE
                self.change_timer = [80, 70, 60][self.gc.difficulty]
    def draw(self):
        im = self.frames.get(x=(self.anim_frame//self.anim_delay)%3 if self.on else 3, y=self.num//2, vflip=self.upside_down)
        return self.blit_image(im, self.rect)

class Crusher(Object):
    def update_config(self, config):
        super().update_config(config)
        self.frames = self.gc.assets.objects.get("crusher")
        self.x = self.spawn_x+self.tilew//2-self.frames[0].get_width()//2
        self.spiked = self.num == 0 # note: non-spiked collision not implemented
        self.attack_distance = self.config.get("attack_distance", self.tileh*5)+(4 if self.spiked else 16)
        self.rect = pygame.Rect(self.x, self.y, self.frames[0].get_width(), self.frames[0].get_height())
        self.update_hitbox()
        self.collides = COLLISION_HAZARD
        self.anim = "idle"
        self.crushing = 0
        self.yv = 0
        self.randomize_blink_timer()
    def update_hitbox(self):
        if self.spiked: self.hitbox = pygame.Rect(self.rect.x+30, self.rect.y+12, self.rect.w-60, self.rect.h-26)
        else: self.hitbox = pygame.Rect(self.rect.x+32, self.rect.y+16, self.rect.w-64, self.rect.h-32)
        self.trigger = pygame.Rect(self.hitbox.x-self.tilew//2, self.rect.bottom, self.hitbox.w+self.tilew, self.attack_distance)
    def randomize_blink_timer(self):
        self.timer = random.randint(180, 720)
    def update(self):
        self.anim_frame += 1
        if self.crushing == 0:
            if self.timer > 0:
                self.timer -= 1
            else:
                self.anim = "blink"
                self.anim_frame = 0
                self.randomize_blink_timer()
            if self.trigger.colliderect(self.gc.player.hitbox):
                self.crushing = 1
                self.yv = 0
        elif self.crushing == 1:
            self.yv += .6
            self.y += self.yv
            if self.y-self.spawn_y > self.attack_distance:
                self.y = self.spawn_y+self.attack_distance
                self.crushing = -1
                self.anim = "hit"
                self.anim_frame = 0
                self.timer = 18
                self.gc.play_sound("crusher")
        elif self.crushing == -1:
            if self.timer > 0:
                self.timer -= 1
            else:
                self.y -= 2
                if self.y < self.spawn_y:
                    self.y = self.spawn_y
                    self.crushing = 0
                    self.anim = "idle"
                    self.randomize_blink_timer()
        if self.crushing != 0:
            self.rect.y = self.y
            self.update_hitbox()
        if self.anim_frame//3 > 3:
            self.anim = "idle"
    def draw(self):
        if self.anim == "idle": frame = 0
        elif self.anim == "blink": frame = self.anim_frame//3+1
        elif self.anim == "hit": frame = self.anim_frame//3+5
        return self.blit_image(self.frames.get(x=frame, y=self.num), self.rect)

class GlitchZone(Object):
    def update_config(self, config):
        super().update_config(config)
        self.xrep = config.get("xrep", 1)
        self.yrep = config.get("yrep", 1)
        self.appear_delay = config.get("appear_delay")
        self.disappear_delay = config.get("disappear_delay")
        self.inflate_hitbox = config.get("inflate_hitbox", 0)
        self.tip_yofs = config.get("tip_yofs", -self.tileh)
        self.no_collide = False
        self.width = self.xrep*self.tilew
        self.height = self.yrep*self.tileh
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.update_hitbox()
        self.color = [RED, GREEN, BLUE, WHITE, BLACK][self.num]
        self.frames = [self.generate_image() for _ in range(16)]
        self.anim_delay = 4
        self.tip_image = generate_tip_image(self.gc, "Warp", 1)
        self.show_tip = False
        self.tip_frame = 9999
    def update_hitbox(self):
        self.hitbox = self.rect.inflate(self.inflate_hitbox, self.inflate_hitbox)
        self.unlocked = [
            self.gc.player.abilities.red_glitch,
            self.gc.player.abilities.green_glitch,
            self.gc.player.abilities.blue_glitch
        ][self.num]
        self.collides = COLLISION_NONE
        self.warp = None
        self.physics = None
        if self.unlocked and (self.appear_delay is None or self.anim_frame > self.appear_delay):
            self.collides = COLLISION_PASS
            if self.num == 0:
                self.collides = COLLISION_BLOCK
                self.collide_sound = "step_glass"
            elif self.num == 1:
                self.warp = self.config.get("warp", None)
            elif self.num == 2:
                self.physics = self.config.get("physics", {})
    def transparent_rect(self, width, height, opacity):
        im = Assets.sized_surface(width, height)
        im.fill(self.color+(opacity*255,))
        return im
    def generate_image(self):
        im = Assets.sized_surface(self.width, self.height)
        for x in range(self.xrep):
            for y in range(self.yrep):
                opacity = random.random()
                if not Settings.enable_transparency:
                    if opacity < .5: continue
                    opacity = 1
                im.blit(
                    self.transparent_rect(self.tilew, self.tileh, opacity),
                    (x*self.tilew,  y*self.tileh)
                )
        return im
    def pre_warp(self, player):
        self.show_tip = False
        self.tip_frame = 9999
    def update(self):
        self.anim_frame += 1
        self.tip_frame += 1
        if self.appear_delay is not None:
            if self.disappear_delay is not None and self.anim_frame > self.appear_delay+self.disappear_delay:
                self.self_destruct = True
                return
            self.update_hitbox()
            if self.num == 0:
                if self.anim_frame == self.appear_delay+1 and self.hitbox.colliderect(self.gc.player.hitbox):
                    self.no_collide = True
                elif self.no_collide and self.anim_frame > self.appear_delay and not self.hitbox.colliderect(self.gc.player.hitbox):
                    self.no_collide = False
    def collides_any(self, entity):
        if not self.unlocked or self.no_collide or (self.appear_delay is not None and self.anim_frame <= self.appear_delay):
            return False
        if self.num == 1:
            if not isinstance(entity, player.Player):
                return False
            if self.hitbox.contains(entity.hitbox) and entity.fall_frame == 0:
                if not self.show_tip:
                    self.show_tip = True
                    self.tip_frame = 0
                return True
            elif self.show_tip:
                self.show_tip = False
                self.tip_frame = 0
            return False
        return self.hitbox.colliderect(entity.hitbox)
    def collides_horizontal(self, entity, dx=0):
        return self.collides_any(entity)
    def collides_vertical(self, entity, dy=0):
        return self.collides_any(entity)
    def draw(self):
        if self.appear_delay is not None and self.anim_frame <= self.appear_delay:
            return
        im = self.frames[self.anim_frame//self.anim_delay%len(self.frames)]
        if self.appear_delay is not None:
            if self.anim_frame <= self.appear_delay+4:
                im.set_alpha((self.anim_frame-self.appear_delay)/4*255)
            elif self.disappear_delay is not None and self.anim_frame > self.appear_delay+self.disappear_delay-4:
                im.set_alpha((self.appear_delay+self.disappear_delay-4+self.anim_frame)/4*255)
        rect = self.blit_image(im, self.rect)
        if self.tip_yofs is not None and (self.show_tip or self.tip_frame < 5):
            tip = self.tip_image.copy()
            if self.tip_frame < 5:
                tip.set_alpha((self.tip_frame if self.show_tip else 5-self.tip_frame)/5*255)
            rect.union_ip(self.blit_image(
                tip, self.rect,
                xofs=self.rect.width//2-self.tip_image.get_width()//2,
                yofs=-self.tip_image.get_height()+self.tip_yofs
            ))
        return rect

class FallingPlatform(Object):
    def update_config(self, config):
        super().update_config(config)
        self.frames = self.gc.assets.objects.get("falling_platform")
        self.rect = pygame.Rect(self.x, self.y, self.frames[0].get_width(), self.frames[0].get_height())
        self.update_hitbox()
        self.collides = COLLISION_BLOCK
        self.collide_sound = "step_rock"
        self.anim = "idle"
        self.anim_delay = 2
        self.prev_anim_frame = self.anim_frame
        self.drop_timer = 0
        self.accelerate = False
    def update_hitbox(self):
        self.hitbox = pygame.Rect(self.rect.x, self.rect.y, self.rect.w, 10)
    def update(self):
        self.prev_anim_frame = self.anim_frame
        if self.anim == "idle":
            self.accelerate = False
            if self.anim_frame > 0:
                self.anim_frame -= 1
        elif self.anim == "activated":
            if self.drop_timer > 0:
                self.drop_timer -= 2 if self.accelerate else 1
                if self.drop_timer <= 0:
                    self.anim = "drop"
                    self.anim_frame = 0
                    self.drop_timer = 100
                    self.gc.play_sound("falling_platform_drop")
        elif self.anim == "drop":
            self.anim_frame += 1
            if self.drop_timer > 0:
                self.drop_timer -= 2 if self.accelerate else 1
                if self.drop_timer <= 0:
                    self.anim = "idle"
                    self.anim_frame = len(self.frames)*self.anim_delay-1
                    self.gc.play_sound("falling_platform_restore")
    def collides_horizontal(self, entity, dx=0):
        if self.anim == "drop" or not self.hitbox.colliderect(entity.hitbox):
            return False
        if self.anim == "idle" and self.anim_frame > 0: # prevent platform hitbox appearing while colliding with player
            self.anim_frame = min(self.prev_anim_frame, len(self.frames)*2)
            return False
        return True
    def collides_vertical(self, entity, dy=0):
        if self.anim == "drop" or not self.hitbox.colliderect(entity.hitbox):
            return False
        if self.anim == "idle" and self.anim_frame > 0:
            self.anim_frame = min(self.prev_anim_frame, len(self.frames)*self.anim_delay)
            return False
        if self.anim == "idle" and self.anim_frame == 0 and entity.hitbox.bottom-self.hitbox.top < dy*2:
            self.anim = "activated"
            self.drop_timer = [60, 40, 20][self.gc.difficulty]
        return True
    def draw(self):
        return self.blit_image(self.frames[min(self.anim_frame//self.anim_delay, len(self.frames)-1)], self.rect)

class Button(Activateable):
    def update_config(self, config):
        super().update_config(config)
        self.frames = self.gc.assets.objects.get("button")
        self.rect = pygame.Rect(self.x, self.y, self.frames[0].get_width(), self.frames[0].get_height())
        self.update_hitbox()
        self.collides = COLLISION_PASS
        self.timer = 0
        self.timer_duration = [3, 4, 6][self.num]*[80, 70, 60][self.gc.difficulty]
        self.linked_objects = None
    def update_hitbox(self):
        self.hitbox = pygame.Rect(self.rect.x+2, self.y+20, self.rect.w-4, self.rect.h-20)
    def should_trigger(self, obj):
        return isinstance(obj, Activateable) and not isinstance(obj, Button) and \
            obj.link == self.link and obj.level.level_pos == self.level.level_pos
    def get_linked_objects(self):
        if self.linked_objects is not None:
            return self.linked_objects
        self.linked_objects = [obj for obj in self.gc.get_all_objects() if self.should_trigger(obj)]
        return self.linked_objects
    def activate(self):
        self.activated = True
        self.timer = self.timer_duration
        for obj in self.get_linked_objects():
            obj.activate()
        self.gc.play_sound("button_press")
    def deactivate(self):
        self.activated = False
        self.timer = 0
        for obj in self.get_linked_objects():
            obj.deactivate()
        self.gc.play_sound("button_release")
    def update(self):
        if self.timer < 6 and self.anim_frame//2 > 0:
            self.anim_frame -= 1
        elif self.timer > 0 and self.anim_frame//2 < 2:
            self.anim_frame += 1
        if self.timer > 0:
            self.timer -= 1
            if self.timer == 0:
                self.deactivate()
    def collides_vertical(self, entity, dy=0):
        if self.timer == 0 and not self.activated and \
            self.hitbox.colliderect(entity.hitbox) and dy > self.gc.player.physics.gravity*2:
            self.activate()
        return False
    def collides_horizontal(self, entity, dx=0):
        return False
    def draw(self):
        return self.blit_image(self.frames.get(x=self.anim_frame//2, y=self.num), self.rect)

class HitButton(Button):
    def update_config(self, config):
        super().update_config(config)
        self.x -= self.tilew//2
        self.frames = self.gc.assets.virus.get("hit_button")
        self.rect = pygame.Rect(self.x, self.y, self.frames[0].get_width(), self.frames[0].get_height())
        self.update_hitbox()
        self.owner = config.get("owner")
    def update_hitbox(self):
        self.hitbox = pygame.Rect(self.rect.x+4, self.y+18, self.rect.w-8, self.rect.h-18)
    def activate(self):
        self.activated = True
        self.gc.show_transition(num=1)
        self.gc.play_sound("hit_button_press")
        particles.ParticleSpawner(
            self.gc, ("circle_white",),
            [
                {"center": self.rect.center, "xv": 16, "yv": 0, "fade_time": 0, "size_change": -0.02}
            ],
            class_=particles.FadeOutParticle, dirofs=360, count=30
        ).spawn()
        if self.owner is not None: self.owner.next_attack()
    def deactivate(self):
        self.activated = False
    def update(self):
        if self.activated:
            if self.anim_frame//2 < 2: self.anim_frame += 1
            else: self.self_destruct = True

class TimedGate(Activateable):
    def update_config(self, config):
        super().update_config(config)
        self.yrep = config.get("yrep", 1)
        self.style = config.get("style")
        if self.style is None: self.style = self.level.terrain_style[1]
        self.upside_down = self.num%2 == 1
        self.image = Assets.sized_surface(self.tilew, self.yrep*self.tileh)
        body = Assets.tile_surface_repetition(self.gc.assets.terrain[1][self.style][4], 1, self.yrep-1)
        if not self.upside_down:
            self.image.blit(body, (0, self.tileh*1.5))
            self.image.blit(self.gc.assets.terrain[1][self.style][3], (0, self.tileh*.5))
            self.image.blit(self.gc.assets.terrain[3][0][0], (0, self.tileh*-.5))
        else:
            self.image.blit(body, (0, self.tileh*-.5))
            self.image.blit(self.gc.assets.terrain[1][self.style][5], (0, self.tileh*(self.yrep-1.5)))
            self.image.blit(self.gc.assets.terrain[3][0][1], (0, self.tileh*(self.yrep-.5)))
        self.rect = pygame.Rect(self.x, self.y, self.image.get_width(), self.image.get_height())
        self.update_hitbox()
        self.collides = COLLISION_BLOCK
        self.position_activated = False
    def update_hitbox(self):
        self.hitbox = pygame.Rect(self.rect.x, self.y, self.rect.w, self.rect.h)
    def update(self):
        if self.num//2 == 0:
            if self.gc.player.x > self.hitbox.right:
                self.position_activated = self.activated = True
            elif self.position_activated and self.gc.player.x+self.gc.player.rectw < self.hitbox.left:
                self.position_activated = self.activated = False
        elif self.num//2 == 1:
            if self.gc.player.x+self.gc.player.rectw < self.hitbox.left:
                self.position_activated = self.activated = True
            elif self.position_activated and self.gc.player.x > self.hitbox.right:
                self.position_activated = self.activated = False
        elif  self.num//2 == 3:
            if self.gc.player.x+self.gc.player.rectw < self.hitbox.left and self.gc.player.y >= self.spawn_y-self.tileh:
                self.position_activated = self.activated = True
            elif self.position_activated and (self.gc.player.x > self.hitbox.right or self.gc.player.y < self.spawn_y-self.tileh):
                self.position_activated = self.activated = False
        if not self.upside_down:
            if self.activated:
                self.y += 3
                if self.y-self.spawn_y > self.hitbox.height+self.tileh//2:
                    self.y = self.spawn_y+self.hitbox.height+self.tileh//2
            else:
                self.y -= 4
                if self.y < self.spawn_y:
                    self.y = self.spawn_y
        else:
            if self.activated:
                self.y -= 3
                if self.y-self.spawn_y < -self.hitbox.height-self.tileh//2:
                    self.y = self.spawn_y-self.hitbox.height-self.tileh//2
            else:
                self.y += 4
                if self.y > self.spawn_y:
                    self.y = self.spawn_y
        self.update_hitbox()
    def collides_any(self, entity):
        if isinstance(entity, player.Player) and self.hitbox.colliderect(entity.hitbox):
            if (not self.upside_down and entity.hitbox.bottom < self.hitbox.top+self.tileh//2) or \
                (self.upside_down and entity.hitbox.top > self.hitbox.bottom-self.tileh//2):
                self.gc.player.death()
            return True
        return self.hitbox.colliderect(entity.hitbox)
    def collides_horizontal(self, entity, dx=0):
        return self.collides_any(entity)
    def collides_vertical(self, entity, dy=0):
        return self.collides_any(entity)
    def draw(self):
        if self.upside_down:
            return self.blit_image(self.image, self.rect, area=(0, self.spawn_y-self.y, self.rect.w, self.rect.h))
        elif self.rect.h-self.y+self.spawn_y > 0:
            return self.blit_image(self.image, self.hitbox, area=(0, 0, self.rect.w, self.rect.h-self.y+self.spawn_y))

class EndgameLever(Activateable):
    def update_config(self, config):
        super().update_config(config)
        self.frames = self.gc.assets.objects.get("lever")
        self.rect = pygame.Rect(self.x, self.y, self.frames[0].get_width(), self.frames[0].get_height())
        self.update_hitbox()
        self.collides = COLLISION_PASS
        self.anim_delay = 3
        self.lever_id = self.gc.level.level_pos[0]-1
        if self.gc.lever_states[self.lever_id]:
            self.activate()
    def update_hitbox(self):
        self.hitbox = pygame.Rect(self.rect.x+32, self.rect.y+112, self.rect.w-64, self.rect.h-112)
    def activate(self):
        self.activated = True
        if self.gc.lever_states[self.lever_id]:
            self.anim_frame = (self.frames.width-1)*self.anim_delay
        else:
            self.gc.lever_states[self.lever_id] = True
            self.gc.save_progress()
    def deactivate(self):
        self.activated = False
        if not self.gc.lever_states[self.lever_id]:
            self.anim_frame = 0
        else:
            self.gc.lever_states[self.lever_id] = False
            self.gc.save_progress()
    def collides_any(self, entity):
        if not self.activated and isinstance(entity, player.Player) and self.hitbox.colliderect(entity.hitbox):
            self.activate()
        return False
    def collides_horizontal(self, entity, dx=0):
        return self.collides_any(entity)
    def collides_vertical(self, entity, dy=0):
        return self.collides_any(entity)
    def update(self):
        if self.activated and self.anim_frame//self.anim_delay < self.frames.width-1:
            self.anim_frame += 1
    def draw(self):
        return self.blit_image(self.frames.get(x=self.anim_frame//self.anim_delay, y=self.num%2), self.rect)

class CrystalBarrier(Object):
    def update_config(self, config):
        super().update_config(config)
        self.yrep = config.get("yrep", 1)
        layouts = {
            3: [(0, -.4), (-.4, .4), (.4, .4)],
            4: [(-.4, -.5), (.4, -.5), (-.4, .5), (.4, .5)],
            5: [(-.4, -.7), (.4, -.7), (0, 0), (-.4, .7), (.4, .7)],
            7: [(0, -1.4), (-.4, -.7), (.4, -.7), (0, 0), (-.4, .7), (.4, .7), (0, 1.4)]
        }
        self.crystal_positions = layouts[self.gc.crystal_requirements[self.gc.difficulty]]
        for crystals in range(min(self.gc.crystal_count, len(self.crystal_positions))+1):
            im = Assets.sized_surface(self.tilew*2, (self.yrep+1)*self.tileh)
            body = Assets.tile_surface_repetition(self.gc.assets.virus["crystal_barrier"][0], 1, self.yrep)
            im.blit(body, (0, 0))
            im.blit(self.gc.assets.virus["crystal_barrier"][1], (0, self.yrep*self.tileh))
            for i, pos in enumerate(self.crystal_positions):
                crystal = self.gc.assets.objects["glitch_crystal"][0 if crystals > i else -1]
                im.blit(crystal, (
                    im.get_width()//2-crystal.get_width()//2+pos[0]*self.tilew,
                    self.yrep*self.tileh//2-crystal.get_height()//2+pos[1]*self.tileh
                ))
            self.frames.append(im)
        self.rect = pygame.Rect(self.x, self.y, self.frames[0].get_width(), self.frames[0].get_height())
        self.update_hitbox()
        self.collides = COLLISION_BLOCK
        self.collide_sound = "step_rock"
        self.anim_delay = 8
        self.locked = None
    def update_hitbox(self):
        self.hitbox = pygame.Rect(self.rect.x, self.y, self.rect.w, self.rect.h-12)
    def update(self):
        self.anim_frame += 1
        if self.locked is None:
            self.locked = False
            # self.anim_frame = len(self.frames)*self.anim_delay-1
        if not self.locked and self.gc.crystal_count >= len(self.crystal_positions) and \
            self.anim_frame//self.anim_delay > len(self.frames)-1:
            self.y -= 1
            if self.y-self.spawn_y < -self.hitbox.height-self.tileh//2:
                self.y = self.spawn_y-self.hitbox.height-self.tileh//2
            self.update_hitbox()
    def draw(self):
        return self.blit_image(
            self.frames[min(self.anim_frame//self.anim_delay, len(self.frames)-1)],
            self.rect, area=(0, self.spawn_y-self.y, self.rect.w, self.rect.h)
        )

class UpgradeTip(Object):
    def update_config(self, config):
        super().update_config(config)
        self.upgrade_name = self.gc.player.abilities.all[self.num]
        if self.gc.player.abilities.get(self.upgrade_name):
            self.self_destruct = True
            return
        jump_num = 0 if RASPBERRY_PI else 2
        self.tip_data = {
            "jump": ["Jump", jump_num],
            "double_jump": ["Double jump", jump_num, jump_num],
            "speed_boost": ["Movement speed\nincreased"],
            "red_glitch": ["Collide with red\nglitch zones"],
            "green_glitch": ["Teleport with green\nglitch zones"],
            "blue_glitch": ["Interact with blue\nglitch zones"],
            "map": ["View map", 6]
        }.get(self.upgrade_name)
        if self.tip_data is None: return
        self.image = generate_tip_image(self.gc, self.tip_data[0], *self.tip_data[1:])
        self.rect = pygame.Rect(self.x+self.tilew-self.image.get_width()//2, self.y, self.image.get_width(), self.image.get_height())
        self.update_hitbox()
    def draw(self):
        if not self.gc.player.abilities.get(self.upgrade_name): return
        return self.blit_image(self.image, self.rect)

class OneWayGate(Activateable):
    def update_config(self, config):
        super().update_config(config)
        self.frames = self.gc.assets.objects.get("one_way_gate")
        self.rect = pygame.Rect(self.x, self.y, self.frames[0].get_width(), self.frames[0].get_height())
        self.update_hitbox()
        self.collide_sound = "step_rock"
        self.anim_delay = 2
        if self.level.level_pos in self.gc.visited_one_ways:
            self.activate()
    def update_hitbox(self):
        self.collides = COLLISION_BLOCK
        if self.num == 0:
            if self.activated: self.hitbox = pygame.Rect(self.rect.x, self.rect.y+self.tileh*2, self.tilew*2, 10)
            else: self.hitbox = pygame.Rect(self.rect.x+self.tilew*2, self.rect.y, 16, self.tileh*2)
        elif self.num == 1:
            if self.activated: self.hitbox = pygame.Rect(self.rect.x+self.tilew, self.rect.y+self.tileh*2, self.tilew*2, 10)
            else: self.hitbox = pygame.Rect(self.rect.x+self.tilew-16, self.rect.y, 16, self.tileh*2)
        elif self.num == 2:
            self.hitbox = pygame.Rect(self.rect.x, self.rect.y+self.tileh-10, self.tilew*2, 10)
            if self.activated: self.collides = COLLISION_NONE
    def activate(self):
        self.activated = True
        self.update_hitbox()
        if self.level.level_pos in self.gc.visited_one_ways:
            self.anim_frame = (3 if self.num//2 == 1 else 4)*self.anim_delay
        else:
            self.gc.visited_one_ways.add(self.level.level_pos)
            self.gc.save_progress()
            self.gc.play_sound("falling_platform_restore")
    def deactivate(self):
        self.activated = False
        self.update_hitbox()
        if not self.level.level_pos in self.gc.visited_one_ways:
            self.anim_frame = 0
        else:
            self.gc.visited_one_ways.remove(self.level.level_pos)
            self.gc.save_progress()
    def collides_horizontal(self, entity, dx=0):
        if not self.hitbox.colliderect(entity.hitbox): return False
        if not self.activated:
            if (self.num == 0 and dx < 0) or (self.num == 1 and dx > 0):
                self.activate()
                return self.hitbox.colliderect(entity.hitbox)
        elif self.num == 2:
            return False
        return True
    def collides_vertical(self, entity, dy=0):
        if not self.hitbox.colliderect(entity.hitbox): return False
        if self.num == 2:
            if self.activated:
                return False
            if dy > 0:
                self.activate()
                return False
        return True
    def update(self):
        if self.activated and self.anim_frame//self.anim_delay < (3 if self.num//2 == 1 else 4):
            self.anim_frame += 1
    def draw(self):
        return self.blit_image(self.frames.get(x=self.anim_frame//self.anim_delay, y=self.num//2, hflip=self.num%2 == 1), self.rect)

class Goo(Object):
    def update_config(self, config):
        super().update_config(config)
        self.style = config.get("style", 0)
        if not self.gc.visited_final_world:
            self.self_destruct = True
            return
        src = self.gc.assets.objects.get("goo")
        self.image = Assets.sized_surface(self.tilew*config.get("xrep", 1), self.tileh)
        self.image.blit(
            src, (0, 0),
            (
                random.randint(0, (src.get_width()-self.image.get_width())//2)*2,
                random.randint(0, src.get_height()//self.tileh-1)*self.tileh,
                self.image.get_width(),
                self.image.get_height()
            )
        )
        self.rect = pygame.Rect(self.x, self.y, self.image.get_width(), self.image.get_height())
        self.update_hitbox()
        self.collides = COLLISION_NONE if self.style == 1 else COLLISION_PASS
        self.layer += 1
    def update_hitbox(self):
        self.hitbox = pygame.Rect(self.rect.x, self.rect.y-4, self.rect.width, self.tileh//2)
    def collides_any(self, entity):
        if isinstance(entity, player.Player) and self.hitbox.colliderect(entity.hitbox):
            entity.xv *= 0.92
        return False
    def collides_horizontal(self, entity, dx=0):
        return self.collides_any(entity)
    def collides_vertical(self, entity, dx=0):
        return self.collides_any(entity)

class Npc(Activateable):
    def update_config(self, config):
        super().update_config(config)
        self.frames = self.gc.assets.objects.get("npc")
        self.tip_image = generate_tip_image(self.gc, "Talk", 1)
        self.rect = pygame.Rect(self.x, self.y, self.frames[0].get_width(), self.frames[0].get_height())
        self.update_hitbox()
        self.collides = COLLISION_PASS
        self.anim = "idle"
        self.anim_delay = 4
        self.facing_right = False
        self.show_tip = False
        self.tip_frame = 9999
        self.tip_yofs = config.get("tip_yofs", -self.tileh)
        self.gift_idx = 0
        self.xofs, self.yofs = 0, 0
        self.xv, self.yv = 0, 0
    def update_hitbox(self):
        self.hitbox = pygame.Rect(self.rect.x-self.tilew*2, self.rect.bottom-self.tileh, self.rect.width+self.tilew*4, self.tileh)
    def update(self):
        if self.anim != "collect":
            self.tip_frame += 1
            if not self.activated:
                self.anim_frame += 1
                self.facing_right = self.gc.player.x+self.gc.player.rectw//2 > self.rect.x+self.rect.width//2
                if self.anim == "hit" and self.anim_frame//self.anim_delay > 6:
                    self.anim = "idle"
                    self.anim_frame = 0
                    self.anim_delay = 4
            elif self.gc.npc_dialogue.hidden:
                self.deactivate()
            elif self.gc.npc_dialogue.change_frame == 1:
                crystals = self.gc.npc_dialogue.current.crystals
                if crystals > 0:
                    for i in range(crystals):
                        clone = self.copy()
                        clone.layer = 1
                        clone.gift_idx = i
                        clone.anim = "collect"
                        clone.anim_frame = 0
                        clone.rect.x += self.tilew//2
                        clone.xv = (self.gc.player.x+self.gc.player.rectw//2-clone.rect.x-self.tilew//2)/32
                        clone.yv = -9
                        self.gc.push_object(clone)
        else:
            self.anim_frame += 1
            if self.anim_frame > (self.gift_idx+1)*12:
                self.xofs += self.xv
                self.yofs += self.yv
                self.yv += 0.6
            if self.yofs > 0:
                self.self_destruct = True
                self.gc.show_transition(num=1)
                self.gc.play_sound("upgrade")
                if self.gift_idx == self.gc.npc_dialogue.current.crystals-1:
                    self.gc.npc_dialogue.advance()
    def activate(self):
        self.activated = True
        self.show_tip = False
        self.tip_frame = 0
        name = None
        slides = []
        visited_this = False
        visited_count = 0
        for pos in self.gc.visited_npcs:
            if self.num == pos[0]:
                if pos[1:] == self.level.level_pos: visited_this = True
                else: visited_count += 1
        if self.num == 0:
            name = "ninja frog"
            if visited_count == 0:
                if not visited_this:
                    slides = [
                        DialogueSlide(name, "Hello, fellow adventurer."),
                        DialogueSlide(name, "It is comforting to know I'm not the\nonly one out here..."),
                        DialogueSlide(name, "Take these crystals. You will need them\nto access the virus' lair."),
                        DialogueSlide(name, crystals=2)
                    ]
                else:
                    slides = [
                        DialogueSlide(name, "I hope to see you again sometime.")
                    ]
            elif visited_count == 1:
                if not visited_this:
                    slides.extend([
                        DialogueSlide(name, "Hello again. I have acquired\nmore crystals."),
                        DialogueSlide(name, crystals=2)
                    ])
                slides.append(DialogueSlide(name, "Best of luck on your journey."))
            elif visited_count == 2:
                if not visited_this:
                    slides = [
                        DialogueSlide(name, "Hello, adventurer."),
                        DialogueSlide(name, "Take these crystals and venture\nnorth to seek the virus."),
                        DialogueSlide(name, crystals=2)
                    ]
                else:
                    slides = [
                        DialogueSlide(name, "You must go north and destroy\nthe virus.")
                    ]
            elif visited_count == 3:
                if not visited_this:
                    slides = [
                        DialogueSlide(name, "Not many make it this far."),
                        DialogueSlide(name, "Here are my last crystals. I want\nyou to have them."),
                        DialogueSlide(name, crystals=2)
                    ]
                slides.append(DialogueSlide(name, "Farewell and good luck."))
        elif self.num == 1:
            name = "survivor"
            if visited_count == 0:
                if not visited_this:
                    slides = [
                        DialogueSlide(name, "Keep quiet. There are others in hiding."),
                        DialogueSlide(name, "Please, take this. I have no use for it."),
                        DialogueSlide(name, crystals=1)
                    ]
                else:
                    slides = [
                        DialogueSlide(name, "I have nothing more for you.")
                    ]
            elif visited_count == 1:
                if not visited_this:
                    slides = [
                        DialogueSlide(name, "Pleased to see you again. You're\ngetting stronger."),
                        DialogueSlide(name, "I must entrust you with another\ncrystal. The world awaits your success."),
                        DialogueSlide(name, crystals=1)
                    ]
                else:
                    slides = [
                        DialogueSlide(name, "You're nearly there, hero.\nThe world awaits your success.")
                    ]
            elif visited_count == 2:
                if not visited_this:
                    slides = [
                        DialogueSlide(name, "It's a relief to see you're still alive."),
                        DialogueSlide(name, "Take this crystal. The virus will meet\nits downfall soon."),
                        DialogueSlide(name, crystals=1)
                    ]
                else:
                    slides = [
                        DialogueSlide(name, "The virus will meet its downfall soon.")
                    ]
        elif self.num == 2:
            name = "???"
            slides = [
                DialogueSlide(name,
                              "01010100 01101000 01100101 00100000\n"+
                              "01110110 01101001 01110010 01110101\n"+
                              "01110011 00100000 01100011 01101111"
                              ),
                DialogueSlide(name,
                              "01110010 01110010 01110101 01110000\n"+
                              "01110100 01110011 00100000 01100001\n"+
                              "01101100 01101100 00101110 00101110"
                              )
                ]
            if not visited_this:
                slides.append(DialogueSlide(name, crystals=1))
        if len(slides) == 0:
            slides = [DialogueSlide("", "")]
        self.gc.npc_dialogue.show(slides, self.dialogue_finished)
        self.gc.player.facing_right = not self.facing_right
        self.gc.player.talk_npc()
        self.gc.play_sound("pause")
    def dialogue_finished(self):
        self.gc.visited_npcs.add((self.num, *self.level.level_pos))
        crystals = sum(slide.crystals for slide in self.gc.npc_dialogue.slides)
        self.gc.crystal_count += crystals
        if crystals == 1:
            self.gc.add_split(f"Crystal {self.gc.crystal_count}")
        elif crystals == 2:
            self.gc.add_split(f"Crystals {self.gc.crystal_count-1} and {self.gc.crystal_count}")
        elif crystals > 2:
            self.gc.add_split(f"Crystals {', '.join([str(self.gc.crystal_count-crystals+n+1) for n in range(crystals)])}")
    def collides_horizontal(self, entity, dx=0):
        if not isinstance(entity, player.Player):
            return False
        if self.hitbox.colliderect(entity.hitbox) and entity.fall_frame == 0:
            if not self.show_tip:
                self.show_tip = True
                self.tip_frame = 0
            if not self.activated and Input.secondary and not self.gc.selection.button_pressed:
                self.activate()
        elif self.show_tip:
            self.show_tip = False
            self.tip_frame = 0
        return False
    def collides_vertical(self, entity, dy=0):
        return False
    def collides_attack(self, entity, hitbox):
        if self.rect.colliderect(hitbox):
            self.anim = "hit"
            self.anim_frame = 0
            self.anim_delay = 2
        return False
    def draw(self):
        if self.anim != "collect": # draw npc
            rect = self.blit_image(self.frames.get(
                x=self.anim_frame//self.anim_delay%11+(11 if self.anim == "hit" else 0),
                y=self.num,
                hflip=not self.facing_right
            ), self.rect)
            if self.show_tip or self.tip_frame < 5:
                tip = self.tip_image.copy()
                if self.tip_frame < 5:
                    tip.set_alpha((self.tip_frame if self.show_tip else 5-self.tip_frame)/5*255)
                rect.union_ip(self.blit_image(
                    tip, self.rect,
                    xofs=self.rect.width//2-self.tip_image.get_width()//2,
                    yofs=-self.tip_image.get_height()+self.tip_yofs
                ))
            return rect
        else: # glitch crystal animation
            im = self.gc.assets.objects.get("glitch_crystal")[self.anim_frame//4%3]
            return self.blit_image(im, self.rect, xofs=self.xofs, yofs=self.yofs)

class SawTrap(Object):
    def update_config(self, config):
        super().update_config(config)
        self.constrained = config.get("constrained", True)
        self.frames = self.gc.assets.objects.get("saw_trap")
        self.dist = max((config.get("xrep", 1)*self.tilew if self.num%2 == 0 else config.get("yrep", 1)*self.tileh)/2-38, 0)
        if self.constrained:
            if self.num == 0: self.y += self.tileh-self.frames[0].get_height()//2
            elif self.num == 3: self.x += self.tilew-self.frames[0].get_width()//2
        self.rect = pygame.Rect(self.x, self.y, self.frames[0].get_width(), self.frames[0].get_height())
        self.update_hitbox()
        self.collides = COLLISION_SHIELDBREAK
        self.anim_delay = 2
    def update_hitbox(self):
        if not self.constrained: self.hitbox = self.rect.inflate(-32, -32)
        elif self.num%2 == 0: self.hitbox = pygame.Rect(self.rect.x+10, self.rect.y+4, self.rect.w-20, self.rect.h//2-8)
        else: self.hitbox = pygame.Rect(self.rect.x+4, self.rect.y+10, self.rect.w//2-8, self.rect.h-20)
    def update(self):
        self.anim_frame += 1
        if not self.constrained:
            amount = 5
            if self.num == 0:
                self.rect.x += amount
                if self.rect.left-self.gc.xscroll > self.gc.game_width: self.self_destruct = True
            elif self.num == 1:
                self.rect.y -= amount
                if self.rect.bottom < 0: self.self_destruct = True
            elif self.num == 2:
                self.rect.x -= amount
                if self.rect.right-self.gc.xscroll < 0: self.self_destruct = True
            elif self.num == 3:
                self.rect.y += amount
                if self.rect.top > self.gc.game_height: self.self_destruct = True
            self.update_hitbox()
        elif self.dist > 0:
            pos = self.dist+self.dist*math.sin(math.radians(self.anim_frame*self.tilew*.1))
            if self.num%2 == 0: self.rect.x = self.x+pos
            else: self.rect.y = self.y+pos
            self.update_hitbox()
    def draw(self):
        if not self.constrained: area = None
        elif self.num == 0: area = (0, 0, self.rect.w, self.rect.h//2)
        elif self.num == 1: area = (self.rect.w//2, 0, self.rect.w//2, self.rect.h)
        elif self.num == 2: area = (0, self.rect.h//2, self.rect.w, self.rect.h//2)
        elif self.num == 3: area = (0, 0, self.rect.w//2, self.rect.h)
        im = self.frames.get(
            self.anim_frame//self.anim_delay%len(self.frames),
            hflip=self.num in (0, 3) and not self.constrained
        )
        return self.blit_image(im, self.rect, area=area)

class Vines(Object):
    def update_config(self, config):
        super().update_config(config)
        if Settings.low_detail:
            self.self_destruct = True
            return
        if self.num < 0:
            self.image = self.gc.assets.decoration["signs"][-self.num-1]
        else:
            self.image = self.gc.assets.decoration["vines"][self.num]
        self.rect = pygame.Rect(self.x, self.y, self.image.get_width(), self.image.get_height())
        self.collides = COLLISION_NONE

class Bat(Object):
    def update_config(self, config):
        super().update_config(config)
        self.frames = self.gc.assets.objects.get("bat")
        self.x = self.spawn_x+self.tilew//2-self.frames[0].get_width()//2
        self.rect = pygame.Rect(self.x, self.y, self.frames[0].get_width(), self.frames[0].get_height())
        self.anim = "idle"
        self.update_hitbox()
        self.collides = COLLISION_SHIELDBREAK
        self.anim_delay = 4
        self.facing_right = None
        self.target = None
        self.attack_angle = 0
        self.speed_base = config.get("speed_base", 7)
        self.speed = random.uniform(self.speed_base-1, self.speed_base+1)
        self.attack_delay = config.get("attack_delay")
        self.layer += 1
    def update_hitbox(self):
        if self.anim == "fly": self.hitbox = pygame.Rect(self.rect.x+17, self.rect.y+16, 58, 24)
        else: self.hitbox = pygame.Rect(self.rect.x+32, self.rect.y, 32, 48)
    def update(self):
        if self.facing_right is None:
            self.facing_right = self.gc.player.x+self.gc.player.rectw//2 > self.rect.centerx
        self.anim_frame += 1
        if self.anim == "idle" and self.attack_delay is not None and self.anim_frame > self.attack_delay:
            self.target_entity(self.gc.player, transition=False)
            self.gc.play_sound("bat")
        elif self.anim == "transition":
            if self.anim_frame//self.anim_delay > 6:
                self.anim = "fly"
                self.anim_frame = 0
                self.gc.play_sound("bat")
        elif self.anim == "fly":
            self.rect.x += math.cos(self.attack_angle)*-self.speed
            self.rect.y += math.sin(self.attack_angle)*-self.speed
            self.update_hitbox()
            if self.anim_frame > 60 and (self.rect.bottom < 0 or self.rect.top > self.gc.game_height):
                self.self_destruct = True
    def calculate_attack_angle(self):
        return math.atan2(self.hitbox.centery-self.target.hitbox.centery, self.hitbox.centerx-self.target.hitbox.centerx)
    def target_entity(self, entity, transition=True):
        self.target = entity
        self.anim = "transition" if transition else "fly"
        self.anim_frame = 0
        self.facing_right = entity.x+entity.rectw//2 > self.rect.centerx
        self.attack_angle = self.calculate_attack_angle()
    def collides_any(self, entity):
        if self.anim == "fly":
            return self.hitbox.colliderect(entity.hitbox)
        if self.anim == "idle" and self.attack_delay is None and isinstance(entity, player.Player) and \
            (self.hitbox.centerx-entity.hitbox.centerx)**2 + (self.hitbox.centery-entity.hitbox.centery)**2 < (self.tilew*16)**2:
            self.target_entity(entity)
        return False
    def collides_horizontal(self, entity, dx=0):
        return self.collides_any(entity)
    def collides_vertical(self, entity, dx=0):
        return self.collides_any(entity)
    def collides_attack(self, entity, hitbox):
        return self.hitbox.colliderect(hitbox)
    def draw(self):
        return self.blit_image(self.frames.get(
            x=self.anim_frame//self.anim_delay%(12 if self.anim == "idle" else 7),
            y=["idle", "transition", "fly"].index(self.anim),
            hflip=self.facing_right
        ), self.rect)


## BOSS ##

class VirusBoss(Object):
    ATTACK_TOMBSTONE = -4
    ATTACK_DEFEAT = -3
    ATTACK_MAD = -2
    ATTACK_INTRO = -1
    ATTACK_PRE_LEVEL = 0
    ATTACK_LEVEL = 1
    ATTACK_RED_GLITCH_HORIZONTAL = 2
    ATTACK_RED_GLITCH_VERTICAL = 3
    ATTACK_BLUE_GLITCH_HORIZONTAL = 4
    ATTACK_BLUE_GLITCH_VERTICAL = 5
    ATTACK_GREEN_GLITCH_HORIZONTAL = 6
    ATTACK_GREEN_GLITCH_VERTICAL = 7
    ATTACK_SPIKES = 8
    ATTACK_SAWS = 9
    ATTACK_BATS = 10

    def update_config(self, config):
        super().update_config(config)
        self.facing_right = False
        self.switch_direction = False
        self.health = 3
        self.hurt_timer = 0
        self.attack_count = 0
        self.max_attacks = 20
        self.level_order = {}
        levels = list(range(6))
        random.shuffle(levels)
        for i, atk in enumerate((3, 10, self.max_attacks-2)):
            self.level_order[atk] = levels[i]
        self.arena_barrier = None
        self.boss_bar = None
        if self.level.level_pos == self.gc.level.level_pos and not self.level.level_pos in self.gc.visited_levels:
            self.gc.add_split("Final boss")
            self.gc.append_visited()
        self.set_attack(self.ATTACK_INTRO if self.gc.completed_time is None else self.ATTACK_TOMBSTONE)
    
    def spawn_ambient_particles(self):
        particles.ParticleSpawner(
            self.gc, ("circle_black", "square_black"),
            [
                {"center": self.rect.center, "xv": 0, "yv": 0, "fade_time": 12}
            ],
            class_=particles.FadeOutParticle, dirofs=0, count=2, yofs=self.rect.height, xofs=self.rect.width*0.7
        ).spawn()

    def spawn_explode_particles(self):
        particles.ParticleSpawner(
            self.gc, ("circle_black", "circle_black", "circle_black", "circle_red", "circle_green", "circle_blue"),
            [
                {"center": (self.gc.game_width*random.uniform(.1, .9), self.gc.game_height*random.uniform(.1, .9)),
                 "xv": 16, "yv": 0, "fade_time": 20}
            ],
            class_=particles.FadeOutParticle, dirofs=360, count=4
        ).spawn()
    
    def spawn_final_explode_particles(self):
        particles.ParticleSpawner(
            self.gc, ("circle_black", "square_black"),
            [
                {"center": (self.gc.game_width//2, self.gc.game_height//2), "xv": 30, "yv": 0,
                 "fade_time": 0, "size_change": -0.015}
            ],
            class_=particles.FadeOutParticle, dirofs=360, count=30, show_low_detail=True
        ).spawn()

    def create_glitch_zone(self, positions, mirror=True, delay=0, kwargs={}, kwargs2={}):
        min_pos = min([sum(pos) for pos in positions])
        for pos in positions:
            self.gc.push_object(
                GlitchZone(self.gc, self.level, {
                    "x": pos[0]*self.tilew,
                    "y": pos[1]*self.tileh,
                    "appear_delay": (sum(pos)+delay-min_pos)*4,
                    "disappear_delay": 160,
                    **kwargs
                })
            )
            if mirror:
                self.gc.push_object(
                    GlitchZone(self.gc, self.level, {
                        "x": self.gc.game_width-self.tilew-pos[0]*self.tilew,
                        "y": pos[1]*self.tileh,
                        "appear_delay": (sum(pos)+delay-min_pos)*4,
                        "disappear_delay": 160,
                        **kwargs, **kwargs2
                    })
                )
    
    def create_infection(self, delay=0):
        delay += self.gc.game_height//self.tileh*16
        for y in range(self.gc.game_height//self.tileh):
            self.gc.push_object(
                Infection(self.gc, self.level, {
                    "x": self.gc.game_width+delay-y*16 if self.facing_right else -self.tilew*2-delay+y*16,
                    "y": y*self.tileh,
                    "facing_right": not self.facing_right
                })
            )

    def sort_last(self):
        def sort(a, b):
            if self == a: return 1
            if self == b: return -1
            return 0
        self.gc.objects_collide.sort(key=cmp_to_key(sort))

    def create_level_chunk(self, x, y, direction, configs):
        w = max(config.get("x", 0)//self.tilew+config.get("xrep", 1) for config in configs)
        drop_delay = (self.gc.game_width/self.tilew-(x+w if self.facing_right else x))*5+30
        chunk = LevelChunk(self.gc, self.level, {
            "x": self.gc.game_width-(x+w)*self.tilew if self.facing_right else x*self.tilew,
            "y": y*self.tileh,
            "direction": direction,
            "configs": configs,
            "drop_delay": drop_delay,
            "hflip": self.facing_right
        })
        self.gc.push_object(chunk)
    
    def pillar_chunk(self, x, y, w, h, direction):
        x, y = x*self.tilew, y*self.tileh
        if direction == 0:
            return [
                {"num": 3, "type": OBJTYPE_BLOCK, "x": x, "y": y, "yrep": h-1},
                {"num": 4, "type": OBJTYPE_BLOCK, "x": x+self.tilew, "y": y, "xrep": w-2, "yrep": h-1},
                {"num": 5, "type": OBJTYPE_BLOCK, "x": x+(w-1)*self.tilew, "y": y, "yrep": h-1},
                {"num": 6, "type": OBJTYPE_BLOCK, "x": x, "y": y+(h-1)*self.tileh},
                {"num": 7, "type": OBJTYPE_BLOCK, "x": x+self.tilew, "y": y+(h-1)*self.tileh, "xrep": w-2},
                {"num": 8, "type": OBJTYPE_BLOCK, "x": x+(w-1)*self.tilew, "y": y+(h-1)*self.tileh},
            ]
        elif direction == 1:
            return [
                {"num": 0, "type": OBJTYPE_BLOCK, "x": x, "y": y},
                {"num": 1, "type": OBJTYPE_BLOCK, "x": x+self.tilew, "y": y, "xrep": w-2},
                {"num": 2, "type": OBJTYPE_BLOCK, "x": x+(w-1)*self.tilew, "y": y},
                {"num": 3, "type": OBJTYPE_BLOCK, "x": x, "y": y+self.tileh, "yrep": h-1},
                {"num": 4, "type": OBJTYPE_BLOCK, "x": x+self.tilew, "y": y+self.tileh, "xrep": w-2, "yrep": h-1},
                {"num": 5, "type": OBJTYPE_BLOCK, "x": x+(w-1)*self.tilew, "y": y+self.tileh, "yrep": h-1}
            ]

    def spike_pillar_chunk(self, x, y, w, h, direction, big=False):
        x, y = x*self.tilew, y*self.tileh
        if direction == 0:
            return [
                {"num": 3, "type": OBJTYPE_BLOCK, "x": x, "y": y, "yrep": h-2},
                {"num": 4, "type": OBJTYPE_BLOCK, "x": x+self.tilew, "y": y, "xrep": w-2, "yrep": h-2},
                {"num": 5, "type": OBJTYPE_BLOCK, "x": x+(w-1)*self.tilew, "y": y, "yrep": h-2},
                {"num": 6, "type": OBJTYPE_BLOCK, "x": x, "y": y+(h-2)*self.tileh},
                {"num": 7, "type": OBJTYPE_BLOCK, "x": x+self.tilew, "y": y+(h-2)*self.tileh, "xrep": w-2},
                {"num": 8, "type": OBJTYPE_BLOCK, "x": x+(w-1)*self.tilew, "y": y+(h-2)*self.tileh},
                {"num": 3 if big else 1, "type": OBJTYPE_SPIKE, "x": x, "y": y+(h-1)*self.tileh, "xrep": w}
            ]
        elif direction == 1:
            return [
                {"num": 2 if big else 0, "type": OBJTYPE_SPIKE, "x": x, "y": y, "xrep": w},
                {"num": 0, "type": OBJTYPE_BLOCK, "x": x, "y": y+self.tileh},
                {"num": 1, "type": OBJTYPE_BLOCK, "x": x+self.tilew, "y": y+self.tileh, "xrep": w-2},
                {"num": 2, "type": OBJTYPE_BLOCK, "x": x+(w-1)*self.tilew, "y": y+self.tileh},
                {"num": 3, "type": OBJTYPE_BLOCK, "x": x, "y": y+self.tileh*2, "yrep": h-2},
                {"num": 4, "type": OBJTYPE_BLOCK, "x": x+self.tilew, "y": y+self.tileh*2, "xrep": w-2, "yrep": h-2},
                {"num": 5, "type": OBJTYPE_BLOCK, "x": x+(w-1)*self.tilew, "y": y+self.tileh*2, "yrep": h-2}
            ]

    def init_horizontal_attack(self, distance):
        self.frames = self.gc.assets.virus.get("side")
        self.anim_delay = 8
        self.x = self.gc.game_width//2+self.gc.game_width*(-distance if self.facing_right else distance)
        self.y = self.gc.game_height*0.6
        self.switch_direction = True

    def set_attack(self, attack):
        self.attack = attack
        self.attack_timer = -1
        if self.switch_direction: self.facing_right = not self.facing_right
        self.switch_direction = False
        self.anim_frame = 0
        self.frames = None
        self.xv, self.yv = 0, 0
        diff = self.gc.difficulty
        if attack in (self.ATTACK_INTRO, self.ATTACK_MAD):
            self.frames = self.gc.assets.virus.get("mad" if attack == self.ATTACK_MAD else "idle")
            self.anim_delay = 8
            self.facing_right = random.randint(0, 1) == 0
            self.x = self.gc.game_width*(.3 if self.facing_right else .7)
            self.y = self.gc.game_height*1.4
            self.switch_direction = True
        elif attack == self.ATTACK_DEFEAT:
            self.frames = self.gc.assets.virus.get("mad")
            self.anim_delay = 4
            self.facing_right = False
            self.x = self.gc.game_width//2
            self.y = (self.gc.game_height-self.tileh)//2
            self.gc.play_sound("virus_scream")
        elif attack == self.ATTACK_TOMBSTONE:
            self.gc.push_object(
                Tombstone(self.gc, self.level, {
                    "x": self.x,
                    "y": self.y,
                    "owner": self
                })
            )
        elif attack == self.ATTACK_SPIKES:
            gaps = set(random.randint(1, 9) for _ in range(random.randint(1, 3)))
            delays = list(range(11))
            random.shuffle(delays)
            self.attack_timer = 10
            for x, delay in enumerate(delays):
                self.attack_timer += 25-diff*3
                if x in gaps: continue
                self.gc.push_object(
                    VirusTentacle(self.gc, self.level, {
                        "x": self.tilew*1.5+x*self.tilew*2,
                        "direction": 0,
                        "drop_speed": 11,
                        "drop_delay": delay*(21-diff*3)+10,
                        "rise_delay": 50
                    })
                )
        elif attack == self.ATTACK_SAWS:
            gaps = [(3, 4), (3,) if diff > 0 else (2, 3)]
            if random.randint(0, 1) == 0: gaps.append((1, 2))
            else: gaps.append((2, 3))
            if random.randint(0, 1) == 0: gaps.append((5, 2))
            else: gaps.append((1, 2))
            random.shuffle(gaps)
            gaps = gaps[:5]
            self.attack_timer = 0
            for x, remove in enumerate(gaps):
                self.attack_timer += 65-diff*3
                for y in range(6):
                    if y in remove: continue
                    self.gc.push_object(
                        SawTrap(self.gc, self.level, {
                            "x": (-x*self.tilew*(9-diff)-self.tilew*4) if self.facing_right else \
                                (x*self.tilew*(9-diff)+self.gc.game_width+self.tilew*2),
                            "y": y*self.tileh*2.3,
                            "num": 0 if self.facing_right else 2,
                            "constrained": False
                        })
                    )
        elif attack == self.ATTACK_BATS:
            self.attack_timer = 20
            for delay in range(8):
                self.attack_timer += 31-diff*5
                self.gc.push_object(
                    Bat(self.gc, self.level, {
                        "x": self.gc.game_width*random.uniform(.1, .9),
                        "y": -56,
                        "attack_delay": delay*(31-diff*5),
                        "speed_base": 8
                    })
                )
        elif attack in (self.ATTACK_RED_GLITCH_HORIZONTAL, self.ATTACK_RED_GLITCH_VERTICAL):
            positions = [(x+1, y+9) for x in range(5) for y in range(5)]
            self.create_glitch_zone(positions, kwargs={"num": 0})
            self.attack_timer = 180
            if attack == self.ATTACK_RED_GLITCH_HORIZONTAL:
                self.init_horizontal_attack(1.3)
                self.attack_timer += 30
            else:
                for x in range(6):
                    self.gc.push_object(
                        VirusTentacle(self.gc, self.level, {
                            "x": self.tilew*.5+x*self.tilew*2,
                            "direction": 1,
                            "drop_delay": x*10+60,
                            "drop_offset": x*self.tileh*1.5
                        })
                    )
                    self.gc.push_object(
                        VirusTentacle(self.gc, self.level, {
                            "x": self.gc.game_width-self.tilew*2.5-x*self.tilew*2,
                            "direction": 1,
                            "drop_delay": x*10+60,
                            "drop_offset": x*self.tileh*1.5
                        })
                    )
                self.attack_timer += 5*10
        elif attack in (self.ATTACK_BLUE_GLITCH_HORIZONTAL, self.ATTACK_BLUE_GLITCH_VERTICAL):
            positions = [(x+2, y+12) for x in range(5) for y in range(2)]
            self.create_glitch_zone(positions, kwargs={"num": 2, "physics": {"jump_height": 10.5}})
            self.attack_timer = 180
            if attack == self.ATTACK_BLUE_GLITCH_HORIZONTAL:
                self.init_horizontal_attack(1.2)
                self.attack_timer += 20
            else:
                for x in range(6):
                    self.gc.push_object(
                        VirusTentacle(self.gc, self.level, {
                            "x": self.tilew*.5+(5-x)*self.tilew*2,
                            "direction": 1,
                            "drop_delay": x*10+50,
                            "drop_offset": x*self.tileh*1.5,
                        })
                    )
                    self.gc.push_object(
                        VirusTentacle(self.gc, self.level, {
                            "x": self.gc.game_width-self.tilew*2.5-(5-x)*self.tilew*2,
                            "direction": 1,
                            "drop_delay": x*10+50,
                            "drop_offset": x*self.tileh*1.5
                        })
                    )
                self.attack_timer += 5*10
        elif attack in (self.ATTACK_GREEN_GLITCH_HORIZONTAL, self.ATTACK_GREEN_GLITCH_VERTICAL):
            positions = [(x+4, y+11) for x in range(3) for y in range(3) if (x, y) != (1, 1)]
            self.create_glitch_zone(positions, kwargs={"num": 1})
            self.create_glitch_zone([(5, 12)], delay=2,
                kwargs={
                    "num": 1, "warp": [19.5*self.tilew, 14*self.tileh], "inflate_hitbox": self.tilew*2,
                    "tip_yofs": -self.tileh*2
                },
                kwargs2={
                    "warp": [5.5*self.tilew, 14*self.tileh], "inflate_hitbox": self.tilew*2,
                    "tip_yofs": -self.tileh*2
                }
            )
            self.attack_timer = 180
            if attack == self.ATTACK_GREEN_GLITCH_HORIZONTAL:
                self.init_horizontal_attack(1.2)
                self.attack_timer += 10
            else:
                for x in range(11):
                    self.gc.push_object(
                        VirusTentacle(self.gc, self.level, {
                            "x": (self.gc.game_width-self.tilew*2.5-x*self.tilew*2) if self.facing_right else \
                                (self.tilew*.5+x*self.tilew*2),
                            "direction": 1,
                            "drop_delay": x*10+50,
                            "drop_offset": self.tileh*5,
                        })
                    )
                self.attack_timer += 6*10
        elif self.attack == self.ATTACK_PRE_LEVEL:
            for x in range(10):
                self.gc.push_object(
                    VirusTentacle(self.gc, self.level, {
                        "x": (x*self.tilew*2) if self.facing_right else \
                            (self.gc.game_width-self.tilew*2-x*self.tilew*2),
                        "direction": 0,
                        "drop_speed": 20,
                        "drop_delay": x*10+10,
                        "rise_delay": 35
                    })
                )
            self.attack_timer = 10*10-10
            chunk = self.level_order[self.attack_count]
            if chunk == 0:
                self.create_level_chunk(6, 8, 1, self.spike_pillar_chunk(0, 0, 2, 6, 1))
                self.create_level_chunk(8, 13, 1, [{"num": 0, "type": OBJTYPE_SPIKE}])
                self.create_level_chunk(15, 0, 0, (self.spike_pillar_chunk if diff > 0 else self.pillar_chunk)(0, 0, 4, 8, 0))
                self.create_level_chunk(15, 12, 1, self.spike_pillar_chunk(0, 0, 4, 2, 1))
                self.create_level_chunk(20.5, 13, 1, [{"num": 0, "type": OBJTYPE_HITBUTTON, "owner": self}])
            elif chunk == 1:
                self.create_level_chunk(5, 11, 1, [
                    {"num": 0, "type": OBJTYPE_SPIKE, "x": 0, "xrep": 5 if diff > 1 else 4},
                    *self.pillar_chunk(0, 1, 6, 2, 1)
                ])
                self.create_level_chunk(11, 13, 1, [
                    {"num": 0, "type": OBJTYPE_SPIKE, "xrep": 2},
                    {"num": 1, "type": OBJTYPE_BEAM, "x": 0, "y": self.tileh, "xrep": 3}
                ])
                self.create_level_chunk(11, 4, 1, [
                    {"num": 2, "type": OBJTYPE_SPIKE, "x": 5*self.tilew, "y": 0, "xrep": 2},
                    {"num": 0, "type": OBJTYPE_BLOCK, "x": 0, "y": self.tileh},
                    {"num": 1, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": self.tileh, "xrep": 5},
                    {"num": 2, "type": OBJTYPE_BLOCK, "x": 6*self.tilew, "y": self.tileh},
                    {"num": 6, "type": OBJTYPE_BLOCK, "x": 0, "y": 2*self.tileh},
                    {"num": 7, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": 2*self.tileh},
                    {"num": 10, "type": OBJTYPE_BLOCK, "x": 2*self.tilew, "y": 2*self.tileh},
                    {"num": 4, "type": OBJTYPE_BLOCK, "x": 3*self.tilew, "y": 2*self.tileh, "yrep": 8},
                    {"num": 9, "type": OBJTYPE_BLOCK, "x": 4*self.tilew, "y": 2*self.tileh},
                    {"num": 7, "type": OBJTYPE_BLOCK, "x": 5*self.tilew, "y": 2*self.tileh},
                    {"num": 8, "type": OBJTYPE_BLOCK, "x": 6*self.tilew, "y": 2*self.tileh},
                    {"num": 3, "type": OBJTYPE_BLOCK, "x": 2*self.tilew, "y": 3*self.tileh, "yrep": 8},
                    {"num": 5, "type": OBJTYPE_BLOCK, "x": 4*self.tilew, "y": 3*self.tileh, "yrep": 5},
                    {"num": 2, "type": OBJTYPE_SPIKE, "x": 5*self.tilew, "y": 7*self.tileh},
                    {"num": 0, "type": OBJTYPE_HITBUTTON, "x": 6.5*self.tilew, "y": 7*self.tileh, "owner": self},
                    {"num": 2, "type": OBJTYPE_SPIKE, "x": 8*self.tilew, "y": 7*self.tileh},
                    {"num": 11, "type": OBJTYPE_BLOCK, "x": 4*self.tilew, "y": 8*self.tileh},
                    {"num": 1, "type": OBJTYPE_BLOCK, "x": 5*self.tilew, "y": 8*self.tileh, "xrep": 3},
                    {"num": 2, "type": OBJTYPE_BLOCK, "x": 8*self.tilew, "y": 8*self.tileh},
                    {"num": 4, "type": OBJTYPE_BLOCK, "x": 4*self.tilew, "y": 9*self.tileh, "xrep": 4},
                    {"num": 5, "type": OBJTYPE_BLOCK, "x": 8*self.tilew, "y": 9*self.tileh},
                ])
                if diff > 0:
                    self.create_level_chunk(20, 13, 1, [{"num": 0, "type": OBJTYPE_SPIKE, "xrep": 4}])
            elif chunk == 2:
                self.create_level_chunk(5, 13, 1, [{"num": 0, "type": OBJTYPE_SPIKE, "xrep": 2}])
                self.create_level_chunk(7, 9, 1, [
                    {"num": 0, "type": OBJTYPE_BLOCK, "x": 0, "y": 0},
                    {"num": 1, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": 0, "xrep": 2},
                    {"num": 2, "type": OBJTYPE_BLOCK, "x": 3*self.tilew, "y": 0},
                    {"num": 2, "type": OBJTYPE_BEAM, "x": 4*self.tilew, "y": 0, "xrep": 0 if diff > 1 else 1},
                    {"num": 3, "type": OBJTYPE_BLOCK, "x": 0, "y": self.tileh, "yrep": 4},
                    {"num": 4, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": self.tileh, "xrep": 2, "yrep": 4},
                    {"num": 5, "type": OBJTYPE_BLOCK, "x": 3*self.tilew, "y": self.tileh},
                    {"num": 0, "type": OBJTYPE_SPIKE, "x": 4*self.tilew, "y": self.tileh, "xrep": 3},
                    {"num": 11, "type": OBJTYPE_BLOCK, "x": 3*self.tilew, "y": 2*self.tileh},
                    {"num": 1, "type": OBJTYPE_BLOCK, "x": 4*self.tilew, "y": 2*self.tileh, "xrep": 2},
                    {"num": 2, "type": OBJTYPE_BLOCK, "x": 6*self.tilew, "y": 2*self.tileh},
                    {"num": 4, "type": OBJTYPE_BLOCK, "x": 3*self.tilew, "y": 3*self.tileh, "xrep": 3, "yrep": 3},
                    {"num": 5, "type": OBJTYPE_BLOCK, "x": 6*self.tilew, "y": 3*self.tileh, "yrep": 3},
                ])
                self.create_level_chunk(7, 0, 0, self.spike_pillar_chunk(0, 0, 4, 7, 0, big=True))
                self.create_level_chunk(14, 5 if diff > 0 else 4, 0, [
                    {"num": 0, "type": OBJTYPE_SPIKE, "x": 0, "y": 0, "xrep": 4 if diff > 0 else 0},
                    {"num": 0, "type": OBJTYPE_BEAM, "x": 0, "y": self.tileh},
                    {"num": 1, "type": OBJTYPE_BEAM, "x": self.tilew, "y": self.tileh, "xrep": 2},
                    {"num": 2, "type": OBJTYPE_BEAM, "x": 3*self.tilew, "y": self.tileh},
                    {"num": 1, "type": OBJTYPE_SPIKE, "x": 0, "y": 2*self.tileh, "xrep": 4}
                ])
                self.create_level_chunk(18, 6, 1, [
                    {"num": 0, "type": OBJTYPE_BLOCK, "x": 4*self.tilew, "y": 0},
                    {"num": 1, "type": OBJTYPE_BLOCK, "x": 5*self.tilew, "y": 0},
                    {"num": 3, "type": OBJTYPE_BLOCK, "x": 4*self.tilew, "y": self.tileh, "yrep": 6},
                    {"num": 4, "type": OBJTYPE_BLOCK, "x": 5*self.tilew, "y": self.tileh, "yrep": 7},
                    {"num": 0, "type": OBJTYPE_SPIKE, "x": 0, "y": 6*self.tileh, "xrep": 3},
                    {"num": 2, "type": OBJTYPE_SPIKE, "x": 3*self.tilew, "y": 6*self.tileh},
                    {"num": 0, "type": OBJTYPE_BLOCK, "x": 0, "y": 7*self.tileh},
                    {"num": 1, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": 7*self.tileh, "xrep": 3},
                    {"num": 12, "type": OBJTYPE_BLOCK, "x": 4*self.tilew, "y": 7*self.tileh}
                ])
                self.create_level_chunk(15.5, 13, 1, [{"num": 0, "type": OBJTYPE_HITBUTTON, "owner": self}])
            elif chunk == 3:
                self.create_level_chunk(6, -0.5, 0, self.spike_pillar_chunk(0, 0, 3, 8 if diff > 0 else 7, 0))
                self.create_level_chunk(6, 11, 1, self.spike_pillar_chunk(0, 0, 3, 3, 1))
                self.create_level_chunk(14, -0.5, 0, self.spike_pillar_chunk(0, 0, 3, 5, 0))
                self.create_level_chunk(14, 9, 1, self.spike_pillar_chunk(0, 0, 3, 5, 1))
                self.create_level_chunk(22, 11, 1, [
                    {"num": 0, "type": OBJTYPE_HITBUTTON, "x": .5*self.tilew, "y": 0, "owner": self},
                    {"num": 0, "type": OBJTYPE_BLOCK, "x": 0, "y": self.tileh},
                    {"num": 1, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": self.tileh},
                    {"num": 3, "type": OBJTYPE_BLOCK, "x": 0, "y": 2*self.tileh},
                    {"num": 4, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": 2*self.tileh}
                ])
            elif chunk == 4:
                self.create_level_chunk(5, 0, 0, self.pillar_chunk(0, 0, 5 if diff > 1 else 4, 9, 0))
                self.create_level_chunk(5, 13, 1, [{"num": 0, "type": OBJTYPE_SPIKE, "xrep": 5 if diff > 1 else 4}])
                self.create_level_chunk(11, 13, 1, [
                    {"num": 0, "type": OBJTYPE_SPIKE, "x": (1.5 if diff > 1 else 1)*self.tilew, "y": 0},
                    {"num": 1, "type": OBJTYPE_BEAM, "x": 0, "y": self.tileh, "xrep": 3}
                ])
                self.create_level_chunk(16, 4, 1, [
                    {"num": 0, "type": OBJTYPE_HITBUTTON, "x": self.tilew, "y": 0, "owner": self},
                    {"num": 0, "type": OBJTYPE_BLOCK, "x": 0, "y": self.tileh},
                    {"num": 1, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": self.tileh},
                    {"num": 2, "type": OBJTYPE_BLOCK, "x": 2*self.tilew, "y": self.tileh},
                    {"num": 3, "type": OBJTYPE_BLOCK, "x": 0, "y": 2*self.tileh, "yrep": 4},
                    {"num": 4, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": 2*self.tileh, "yrep": 4},
                    {"num": 5, "type": OBJTYPE_BLOCK, "x": 2*self.tilew, "y": 2*self.tileh, "yrep": 3},
                    {"num": 0, "type": OBJTYPE_SPIKE, "x": 3*self.tilew, "y": 4*self.tileh},
                    {"num": 11, "type": OBJTYPE_BLOCK, "x": 2*self.tilew, "y": 5*self.tileh},
                    {"num": 2, "type": OBJTYPE_BLOCK, "x": 3*self.tilew, "y": 5*self.tileh},
                    {"num": 6, "type": OBJTYPE_BLOCK, "x": 0, "y": 6*self.tileh},
                    {"num": 7, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": 6*self.tileh, "xrep": 2},
                    {"num": 8, "type": OBJTYPE_BLOCK, "x": 3*self.tilew, "y": 6*self.tileh}
                ])
                self.create_level_chunk(22, 0, 0, [
                    {"num": 3, "type": OBJTYPE_BLOCK, "x": 0, "y": 0},
                    {"num": 4, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": 0},
                    {"num": 6, "type": OBJTYPE_BLOCK, "x": 0, "y": self.tileh},
                    {"num": 10, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": self.tileh},
                    {"num": 1, "type": OBJTYPE_SPIKE, "x": 0, "y": 2*self.tileh},
                    {"num": 3, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": 2*self.tileh, "yrep": 6},
                    {"num": 6, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": 8*self.tileh},
                    {"num": 3, "type": OBJTYPE_SPIKE, "x": self.tilew, "y": 9*self.tileh, "xrep": 1 if diff > 0 else 0}
                ])
                self.create_level_chunk(23, 12, 1, [
                    {"num": 0, "type": OBJTYPE_BLOCK, "x": 0, "y": 0},
                    {"num": 3, "type": OBJTYPE_BLOCK, "x": 0, "y": self.tileh}
                ])
            elif chunk == 5:
                self.create_level_chunk(5, 0, 0, [
                    {"num": 3, "type": OBJTYPE_BLOCK, "x": 0, "y": 0, "yrep": 8},
                    {"num": 4, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": 0, "xrep": 3, "yrep": 7},
                    {"num": 5, "type": OBJTYPE_BLOCK, "x": 4*self.tilew, "y": 0, "yrep": 7},
                    {"num": 2, "type": OBJTYPE_BEAM, "x": 5*self.tilew, "y": 6*self.tileh},
                    {"num": 4, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": 7*self.tileh, "xrep": 2},
                    {"num": 9, "type": OBJTYPE_BLOCK, "x": 3*self.tilew, "y": 7*self.tileh},
                    {"num": 8, "type": OBJTYPE_BLOCK, "x": 4*self.tilew, "y": 7*self.tileh},
                    {"num": 1, "type": OBJTYPE_SPIKE, "x": 5*self.tilew, "y": 7*self.tileh, "xrep": 1 if diff > 0 else 0},
                    {"num": 6, "type": OBJTYPE_BLOCK, "x": 0, "y": 8*self.tileh},
                    {"num": 10, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": 8*self.tileh},
                    {"num": 4, "type": OBJTYPE_BLOCK, "x": 2*self.tilew, "y": 8*self.tileh, "yrep": 2},
                    {"num": 5, "type": OBJTYPE_BLOCK, "x": 3*self.tilew, "y": 8*self.tileh, "yrep": 2},
                    {"num": 3, "type": OBJTYPE_SPIKE, "x": 4*self.tilew, "y": 8*self.tileh},
                    {"num": 3, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": 9*self.tileh},
                    {"num": 6, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": 10*self.tileh},
                    {"num": 7, "type": OBJTYPE_BLOCK, "x": 2*self.tilew, "y": 10*self.tileh},
                    {"num": 8, "type": OBJTYPE_BLOCK, "x": 3*self.tilew, "y": 10*self.tileh},
                    {"num": 1, "type": OBJTYPE_SPIKE, "x": 2*self.tilew, "y": 11*self.tileh, "xrep": 2}
                ])
                self.create_level_chunk(11, 6, 1, [
                    {"num": 0, "type": OBJTYPE_SPIKE, "x": 3*self.tilew, "y": 0, "xrep": 5},
                    {"num": 0, "type": OBJTYPE_SPIKE, "x": 2*self.tilew, "y": self.tileh},
                    {"num": 0, "type": OBJTYPE_BLOCK, "x": 3*self.tilew, "y": self.tileh},
                    {"num": 1, "type": OBJTYPE_BLOCK, "x": 4*self.tilew, "y": self.tileh, "xrep": 3},
                    {"num": 2, "type": OBJTYPE_BLOCK, "x": 7*self.tilew, "y": self.tileh},
                    {"num": 0, "type": OBJTYPE_BLOCK, "x": 2*self.tilew, "y": 2*self.tileh},
                    {"num": 12, "type": OBJTYPE_BLOCK, "x": 3*self.tilew, "y": 2*self.tileh},
                    {"num": 4, "type": OBJTYPE_BLOCK, "x": 4*self.tilew, "y": 2*self.tileh, "xrep": 3},
                    {"num": 5, "type": OBJTYPE_BLOCK, "x": 7*self.tilew, "y": 2*self.tileh, "yrep": 2},
                    {"num": 3, "type": OBJTYPE_BLOCK, "x": 2*self.tilew, "y": 3*self.tileh, "yrep": 3},
                    {"num": 4, "type": OBJTYPE_BLOCK, "x": 3*self.tilew, "y": 3*self.tileh, "xrep": 4, "yrep": 2},
                    {"num": 0, "type": OBJTYPE_SPIKE, "x": 8*self.tilew, "y": 3*self.tileh},
                    {"num": 11, "type": OBJTYPE_BLOCK, "x": 7*self.tilew, "y": 4*self.tileh},
                    {"num": 2, "type": OBJTYPE_BLOCK, "x": 8*self.tilew, "y": 4*self.tileh},
                    {"num": 0, "type": OBJTYPE_SPIKE, "x": self.tilew, "y": 5*self.tileh},
                    {"num": 4, "type": OBJTYPE_BLOCK, "x": 3*self.tilew, "y": 5*self.tileh, "xrep": 5, "yrep": 2},
                    {"num": 5, "type": OBJTYPE_BLOCK, "x": 8*self.tileh, "y": 5*self.tileh, "yrep": 2},
                    {"num": 0, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": 6*self.tileh},
                    {"num": 12, "type": OBJTYPE_BLOCK, "x": 2*self.tilew, "y": 6*self.tileh},
                    {"num": 2, "type": OBJTYPE_SPIKE, "x": 9*self.tilew, "y": 6*self.tileh},
                    {"num": 0 if diff > 1 else 2, "type": OBJTYPE_SPIKE, "x": 0 if diff > 1 else 2, "y": 7*self.tileh},
                    {"num": 3, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": 7*self.tileh, "yrep": 2},
                    {"num": 4, "type": OBJTYPE_BLOCK, "x": 2*self.tilew, "y": 7*self.tileh, "xrep": 6, "yrep": 2},
                    {"num": 11, "type": OBJTYPE_BLOCK, "x": 8*self.tilew, "y": 7*self.tileh},
                    {"num": 2, "type": OBJTYPE_BLOCK, "x": 9*self.tilew, "y": 7*self.tileh},
                    {"num": 1, "type": OBJTYPE_BEAM, "x": 0, "y": 8*self.tileh}
                ])
                self.create_level_chunk(20, 0, 0, [
                    {"num": 6, "type": OBJTYPE_BLOCK, "x": 0, "y": 0},
                    {"num": 10, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": 0},
                    {"num": 4, "type": OBJTYPE_BLOCK, "x": 2*self.tilew, "y": 0, "xrep": 2},
                    {"num": 6, "type": OBJTYPE_BLOCK, "x": self.tilew, "y": self.tileh},
                    {"num": 10, "type": OBJTYPE_BLOCK, "x": 2*self.tilew, "y": self.tileh},
                    {"num": 4, "type": OBJTYPE_BLOCK, "x": 3*self.tilew, "y": self.tileh, "yrep": 3},
                    {"num": 3, "type": OBJTYPE_SPIKE, "x": self.tilew, "y": 2*self.tileh},
                    {"num": 3, "type": OBJTYPE_BLOCK, "x": 2*self.tilew, "y": 2*self.tileh, "yrep": 2},
                    {"num": 6, "type": OBJTYPE_BLOCK, "x": 2*self.tilew, "y": 4*self.tileh},
                    {"num": 10, "type": OBJTYPE_BLOCK, "x": 3*self.tilew, "y": 4*self.tileh},
                    {"num": 1, "type": OBJTYPE_SPIKE, "x": 2*self.tilew, "y": 5*self.tileh},
                    {"num": 3, "type": OBJTYPE_BLOCK, "x": 3*self.tilew, "y": 5*self.tileh, "yrep": 2},
                    {"num": 6, "type": OBJTYPE_BLOCK, "x": 3*self.tilew, "y": 7*self.tileh},
                    {"num": 1, "type": OBJTYPE_SPIKE, "x": 3*self.tilew, "y": 8*self.tileh}
                ])
                self.create_level_chunk(22, 13, 1, [{"num": 0, "type": OBJTYPE_HITBUTTON, "owner": self}])
            self.sort_last()
            self.gc.sort_hazards()
            self.gc.sort_layers()
        elif attack == self.ATTACK_LEVEL:
            self.create_infection([180, 60, 0][diff])
        if self.frames is not None:
            self.rect = pygame.Rect(
                self.x-self.frames[0].get_width()//2, self.y-self.frames[0].get_height()//2,
                self.frames[0].get_width(), self.frames[0].get_height()
            )
        self.update_hitbox()

    def update_hitbox(self):
        self.hitbox = None
        self.hurtbox = None
        if self.frames is not None:
            if self.attack in (self.ATTACK_INTRO, self.ATTACK_MAD, self.ATTACK_DEFEAT): # background attack
                self.hitbox = self.rect.copy()
                self.collides = COLLISION_PASS
            else: # horizontal attack
                self.hitbox = pygame.Rect(
                    self.rect.x+(48 if self.facing_right else 160), self.rect.y+28,
                    self.rect.w-160-48, self.rect.h-56
                )
                self.hurtbox = pygame.Rect(
                    self.rect.x+(self.rect.w-32-128 if self.facing_right else 32), self.rect.y+self.rect.h//2-60,
                    128, 120
                )
                self.collides = COLLISION_SHIELDBREAK
        elif self.attack == self.ATTACK_TOMBSTONE: self.collides = COLLISION_PASS # tombstone
        else: self.collides = COLLISION_NONE # offscreen
    
    def hurt(self):
        if self.hurt_timer > 0: return
        self.health -= 1
        self.hurt_timer = 8

    def next_attack(self):
        self.attack_count += 1
        if self.attack == self.ATTACK_PRE_LEVEL:
            self.set_attack(self.ATTACK_LEVEL)
        elif self.attack == self.ATTACK_LEVEL:
            self.hurt()
            for obj in self.gc.get_all_objects():
                if isinstance(obj, LevelChunk): obj.rise_delay = 0
                elif isinstance(obj, Infection): obj.self_destruct = True
            self.set_attack(self.ATTACK_MAD if self.health > 0 else self.ATTACK_DEFEAT)
        elif self.attack == self.ATTACK_TOMBSTONE:
            self.attack_count -= 1
            self.set_attack(self.ATTACK_INTRO)
        elif self.attack_count in self.level_order:
            self.set_attack(self.ATTACK_PRE_LEVEL)
        else:
            attacks = [
                self.ATTACK_RED_GLITCH_HORIZONTAL,
                self.ATTACK_BLUE_GLITCH_HORIZONTAL,
                self.ATTACK_GREEN_GLITCH_HORIZONTAL
            ]
            if self.health < 3:
                attacks.extend([
                    self.ATTACK_SPIKES,
                    self.ATTACK_SAWS,
                    self.ATTACK_BATS
                ])
            if self.health < 2:
                attacks.extend([
                    self.ATTACK_RED_GLITCH_VERTICAL,
                    self.ATTACK_BLUE_GLITCH_VERTICAL,
                    self.ATTACK_GREEN_GLITCH_VERTICAL
                ])
            if len(attacks) > 1:
                next_attack = self.attack
                while self.attack == next_attack:
                    next_attack = random.choice(attacks)
            else:
                next_attack = attacks[0]
            self.set_attack(next_attack)

    def update(self):
        self.anim_frame += 1
        if self.hurt_timer > 0:
            self.hurt_timer -= 1
        if self.attack_timer > 0:
            self.attack_timer -= 1
        elif self.attack_timer == 0:
            self.next_attack()
        if self.attack in (self.ATTACK_INTRO, self.ATTACK_MAD):
            self.xv += .15 if self.facing_right else -.15
            if self.rect.bottom < self.gc.game_height*-.5: self.next_attack()
            else: self.yv -= .4
            self.spawn_ambient_particles()
        elif self.attack == self.ATTACK_DEFEAT:
            self.x = self.gc.game_width//2+random.randint(-self.anim_frame, self.anim_frame)
            self.y = (self.gc.game_height-self.tileh)//2+random.randint(-self.anim_frame, self.anim_frame)
            if self.anim_frame%4 == 0 and self.frames is not None:
                self.spawn_explode_particles()
            if self.anim_frame == 120:
                self.frames = None
                self.gc.show_transition(num=0)
                self.gc.load_music("none")
            elif self.anim_frame == 130:
                self.spawn_final_explode_particles()
                self.gc.play_sound("explosion")
            elif self.anim_frame == 260:
                self.self_destruct = True
                self.gc.defeat_virus()
        elif self.attack in (
                self.ATTACK_RED_GLITCH_HORIZONTAL,
                self.ATTACK_BLUE_GLITCH_HORIZONTAL,
                self.ATTACK_GREEN_GLITCH_HORIZONTAL
            ):
            self.xv = 10 if self.facing_right else -10
            self.yv = [0.2, 0.1, 0][self.gc.difficulty]
            self.spawn_ambient_particles()
        self.x += self.xv
        self.y += self.yv
        if self.x != self.rect.centerx or self.y != self.rect.centery:
            self.rect.center = self.x, self.y
            self.update_hitbox()
        if self.attack != self.ATTACK_TOMBSTONE and self.arena_barrier is None:
            obj = ArenaBarrier(self.gc, self.level, {
                "x": self.gc.game_width//2,
                "y": self.gc.game_height-self.tileh
            })
            self.arena_barrier = obj
            self.gc.push_object(obj)
            obj = BossBar(self.gc, self.level, {
                "owner": self
            })
            self.boss_bar = obj
            self.gc.push_object(obj)
            self.gc.load_music("boss")

    def collides_any(self, entity):
        if self.hurtbox is not None and self.hurtbox.colliderect(entity.hitbox): return True
        if self.hitbox is not None and self.hitbox.colliderect(entity.hitbox): return True
        return False
    
    def collides_horizontal(self, entity, dx=0):
        return self.collides_any(entity)
    
    def collides_vertical(self, entity, dy=0):
        return self.collides_any(entity)
    
    def collides_attack(self, entity, hitbox):
        if  self.hurtbox is None or not self.hurtbox.colliderect(hitbox) or \
            self.rect.left > self.gc.game_width or self.rect.right < 0 or \
            self.rect.top > self.gc.game_height or self.rect.bottom < 0:
            return
        self.hurt()

    def draw_hitbox(self):
        hit = super().draw_hitbox()
        if self.hurtbox is None: return hit
        hurt = self.blit_rect(self.hurtbox, MAGENTA, 1)
        if hit is None: return hurt
        return hit.union(hurt)
    
    def draw(self):
        if self.frames is None: return
        im = self.frames.get(
            self.anim_frame//self.anim_delay%len(self.frames),
            hflip=self.facing_right and self.attack not in (self.ATTACK_INTRO, self.ATTACK_MAD)
        ).copy()
        if self.hurt_timer > 4:
            amount = (self.hurt_timer-4)/4*128
            im.fill((amount, amount, amount, 0), special_flags=pygame.BLEND_RGBA_ADD)
        return self.blit_image(im, self.rect)

class BossBar(Object):
    def update_config(self, config):
        super().update_config(config)
        self.owner = config.get("owner")
        if self.owner is None:
            self.self_destruct = True
            return
        self.position = -4
        self.rect = pygame.Rect(32, self.position, self.gc.game_width-64, 8)
        self.image = Assets.sized_surface(self.rect.size)
        color = (33, 31, 48)
        pygame.draw.rect(self.image, BLACK, (2, 2, self.rect.width-4, self.rect.height-4))
        pygame.draw.rect(self.image, color, (0, 2, 2, self.rect.height-4))
        pygame.draw.rect(self.image, color, (self.rect.width-2, 2, 2, self.rect.height-4))
        pygame.draw.rect(self.image, color, (2, 0, self.rect.width-4, 2))
        pygame.draw.rect(self.image, color, (2, self.rect.height-2, self.rect.width-4, 2))
        self.update_hitbox()
        self.color = [(52, 215, 51), (51, 62, 215), (215, 51, 51)][self.gc.difficulty]
        self.layer = 9999
    def update(self):
        self.target_y = 2 if Settings.enable_shaders else 0
        if self.rect.y != self.target_y:
            ofs = (self.target_y-self.rect.y)/8
            self.rect.y += math.floor(ofs) if self.rect.y > self.target_y else math.ceil(ofs)
        target = self.owner.attack_count/self.owner.max_attacks*(self.rect.width-4)
        self.position += (target-self.position)/(8 if self.owner.attack_count == self.owner.max_attacks else 30)
        if abs(target-self.position) < 1: self.position = target
        pygame.draw.rect(self.image, self.color, (2, 2, self.position, self.rect.h-4))

class VirusTentacle(Object):
    def update_config(self, config):
        super().update_config(config)
        self.direction = config.get("direction", 0)
        self.y = -self.gc.game_height-self.tileh*2 if self.direction == 0 else self.gc.game_height
        self.rect = pygame.Rect(self.x, self.y, self.tilew*2, self.gc.game_height+self.tileh*2)
        sheet = self.gc.assets.virus.get("tentacle_drill")
        for x in range(sheet.width):
            surface = Assets.sized_surface(self.rect.size)
            for y in range(self.rect.height//(self.tileh*2)):
                if self.direction == 0: surface.blit(sheet.get(x=x, y=0), (0, surface.get_height()-(y+2)*self.tileh*2))
                else: surface.blit(sheet.get(x=x, y=0, vflip=True), (0, (y+1)*self.tileh*2))
            if self.direction == 0: surface.blit(sheet.get(x=x, y=1), (0, surface.get_height()-self.tileh*2))
            else: surface.blit(sheet.get(x=x, y=1, vflip=True), (0, 0))
            self.frames.append(surface)
        self.update_hitbox()
        self.collides = COLLISION_SHIELDBREAK
        self.anim_delay = 2
        self.drop_delay = config.get("drop_delay", 0)
        self.rise_delay = config.get("rise_delay", 30)
        self.drop_speed = config.get("drop_speed", 15)
        self.rise_speed = config.get("rise_speed", 20)
        if self.direction == 0: self.drop_target = self.gc.game_height+self.tileh*2
        else: self.drop_target = 0
        self.drop_target += config.get("drop_offset", 0)
    def spawn_ambient_particles(self):
        particles.ParticleSpawner(
            self.gc, ("circle_black",),
            [
                {"center": self.rect.center, "xv": 0, "yv": 0, "fade_time": 12}
            ],
            class_=particles.FadeOutParticle, dirofs=0, count=3, yofs=self.rect.height, xofs=self.rect.width
        ).spawn()
    def update_hitbox(self):
        if self.direction in (0, 1):
            self.hitbox = pygame.Rect(self.rect.x+4, self.rect.y, self.rect.w-8, self.rect.h-16)
            if self.direction == 1: self.hitbox.y += 16
    def update(self):
        self.anim_frame += 1
        if self.anim_frame > self.drop_delay+self.rise_delay:
            if self.direction == 0:
                if self.rect.bottom < 0: self.self_destruct = True
                else: self.rect.y -= self.rise_speed
            elif self.direction == 1:
                if self.rect.top > self.gc.game_height: self.self_destruct = True
                else: self.rect.y += self.rise_speed
        elif self.anim_frame > self.drop_delay:
            if self.direction == 0:
                if self.rect.bottom >= self.drop_target-self.drop_speed: self.rect.bottom = self.drop_target
                else: self.rect.y += self.drop_speed
            elif self.direction == 1:
                if self.rect.top <= self.drop_target+self.drop_speed: self.rect.top = self.drop_target
                else: self.rect.y -= self.drop_speed
        self.update_hitbox()
        self.spawn_ambient_particles()

class Infection(Object):
    def update_config(self, config):
        super().update_config(config)
        self.facing_right = config.get("facing_right", True)
        self.frames = self.gc.assets.virus.get("infection")
        self.rect = pygame.Rect(self.x, self.y, self.frames[0].get_width(), self.frames[0].get_height())
        self.update_hitbox()
        self.collides = COLLISION_HAZARD
        self.anim_delay = config.get("anim_delay", 4)
        self.extend = 0
    def update_hitbox(self):
        x = self.rect.left-self.tilew+24 if self.facing_right else self.rect.right-24
        x += (4 if self.facing_right else -4)*(self.anim_frame//self.anim_delay)
        self.hitbox = pygame.Rect(x, self.rect.y, self.tilew, self.rect.h)
    def update(self):
        self.anim_frame += 1
        if self.anim_frame%self.anim_delay == 0:
            self.update_hitbox()
        if self.anim_frame//self.anim_delay == len(self.frames):
            self.extend += 1
            self.rect.x += self.tilew if self.facing_right else -self.tilew
            self.anim_frame = 0
    def draw(self):
        rect = self.blit_image(
            self.frames.get(self.anim_frame//self.anim_delay, hflip=not self.facing_right),
            self.rect
        )
        if self.extend > 0:
            extension = pygame.Rect(self.rect.right, self.rect.y, self.extend*self.tilew, self.rect.h)
            if self.facing_right: extension.right = self.rect.left
            rect.union_ip(self.blit_rect(extension, BLACK))
        return rect

class LevelChunk(Object):
    def update_config(self, config):
        super().update_config(config)
        self.direction = config.get("direction", 0)
        self.drop_delay = config.get("drop_delay", 0)
        self.rise_delay = config.get("rise_delay")
        self.hflip = config.get("hflip", False)
        self.xofs, self.yofs = self.x, self.y
        self.finished_drop = False
        self.chunk_vel = 0
        self.create_objects()
    def create_objects(self):
        configs = self.config.get("configs", [])
        self.width = max(config.get("x", 0)+config.get("xrep", 1)*self.tilew for config in configs)
        self.height = max(config.get("y", 0)+config.get("yrep", 1)*self.tileh for config in configs)
        if self.direction == 0: self.yofs = -self.height
        elif self.direction == 1: self.yofs = self.gc.game_height
        self.objects = []
        for config in configs:
            chunk_x, chunk_y = config.get("x", 0), config.get("y", 0)
            if self.hflip:
                chunk_x = self.width-chunk_x-config.get("xrep", 1)*self.tilew
                swapkey = {
                    OBJTYPE_BLOCK: {0: 2, 3: 5, 6: 8, 9: 10, 11: 12},
                    OBJTYPE_BEAM: {0: 2, 6: 7, 8: 9},
                    OBJTYPE_SEMISOLID: {0: 2}
                }.get(config.get("type"), {})
                if config.get("num", 0) in swapkey:
                    config["num"] = swapkey[config.get("num", 0)]
                elif config.get("num", 0) in swapkey.values():
                    config["num"] = {v: k for k, v in swapkey.items()}[config.get("num", 0)]
            config["x"] = chunk_x+self.xofs
            config["y"] = chunk_y+self.yofs
            obj = create_object(self.gc, self.level, config)
            obj.chunk_x, obj.chunk_y = obj.x-self.xofs, obj.y-self.yofs
            obj.layer -= 1
            if not obj.self_destruct:
                self.objects.append(obj)
                self.gc.push_object(obj)
    def update(self):
        self.anim_frame += 1
        if self.rise_delay is not None and self.anim_frame > self.drop_delay+self.rise_delay:
            if self.chunk_vel == 0: # put chunk hitboxes below the screen to remove its collision
                prev_yofs = self.yofs
                self.yofs = self.gc.game_height*2
                self.shift_objects(update_hitbox=True)
                self.yofs = prev_yofs
            self.chunk_vel += 1
            if self.direction == 0:
                self.yofs -= self.chunk_vel
                self.shift_objects()
                if self.yofs+self.height < 0: self.destroy()
            elif self.direction == 1:
                self.yofs += self.chunk_vel
                self.shift_objects()
                if self.yofs > self.gc.game_height: self.destroy()
        elif self.anim_frame > self.drop_delay:
            if abs(self.y-self.yofs) < 2: amount = self.y-self.yofs
            else: amount = (self.y-self.yofs)/7
            if amount == 0:
                if not self.finished_drop:
                    self.finished_drop = True
                    for obj in self.objects:
                        obj.update_hitbox()
            else:
                self.yofs += amount
                self.shift_objects()
    def shift_objects(self, update_hitbox=False):
        for obj in self.objects:
            obj.x = self.xofs+obj.chunk_x
            obj.y = self.yofs+obj.chunk_y
            obj.rect.x = self.xofs+obj.chunk_x
            obj.rect.y = self.yofs+obj.chunk_y
            if update_hitbox: obj.update_hitbox()
    def destroy(self):
        self.self_destruct = True
        for obj in self.objects:
            obj.self_destruct = True

class ArenaBarrier(Activateable):
    def update_config(self, config):
        super().update_config(config)
        self.frames = self.gc.assets.virus.get("arena_barrier")
        self.rect = pygame.Rect(self.x-self.tilew*1.5, self.y, self.tilew*3, self.tileh)
        self.update_hitbox()
        self.collides = COLLISION_BLOCK
        self.collide_sound = "step_rock"
        self.position = 0
        self.auto_activated = False
        self.no_collide = False
    def update(self):
        self.anim_frame += 1
        if self.activated: self.position = min(self.position+4, 50)
        else: self.position = max(self.position-1, 0)
        if not self.auto_activated:
            self.auto_activated = True
            self.activate()
        if self.activated and self.position == 16 and self.hitbox.colliderect(self.gc.player.hitbox):
            self.no_collide = True
        elif self.no_collide and self.position > 16 and not self.hitbox.colliderect(self.gc.player.hitbox):
            self.no_collide = False
    def collides_any(self, entity):
        if self.position < 16 or self.no_collide: return False
        return self.hitbox.colliderect(entity.hitbox)
    def collides_horizontal(self, entity, dx=0):
        return self.collides_any(entity)
    def collides_vertical(self, entity, dy=0):
        return self.collides_any(entity)
    def draw(self):
        left = self.blit_image(
            self.frames[0],
            pygame.Rect(self.rect.left, self.rect.y, self.rect.w, self.rect.h),
            area=(self.frames[0].get_width()-self.position, 0, self.position, self.rect.h)
        )
        right = self.blit_image(
            self.frames[1],
            pygame.Rect(self.rect.right-self.position, self.rect.y, self.rect.w, self.rect.h),
            area=(0, 0, self.position, self.rect.h)
        )
        return left.union(right)

class Tombstone(Object):
    def update_config(self, config):
        super().update_config(config)
        self.frames = self.gc.assets.virus.get("tombstone")
        self.rect = pygame.Rect(self.x, self.y, self.frames[0].get_width(), self.frames[0].get_height())
        self.update_hitbox()
        self.collides = COLLISION_PASS
        self.tip_image = generate_tip_image(self.gc, "Revive", 1)
        self.show_tip = False
        self.tip_frame = 9999
        self.reviving = False
        self.anim_delay = 4
        self.owner = config.get("owner")
    def update_hitbox(self):
        self.hitbox = pygame.Rect(self.rect.x+12-self.tilew, self.rect.bottom-self.tileh, self.rect.w-24+self.tilew*2, self.tileh)
    def update(self):
        if self.reviving:
            self.anim_frame += 1
            if self.anim_frame//self.anim_delay > len(self.frames)-1:
                self.self_destruct = True
                if self.owner is not None: self.owner.next_attack()
        self.tip_frame += 1
    def collides_horizontal(self, entity, dx=0):
        if self.reviving or not isinstance(entity, player.Player):
            return False
        if self.hitbox.colliderect(entity.hitbox) and entity.fall_frame == 0:
            if not self.show_tip:
                self.show_tip = True
                self.tip_frame = 0
            if Input.secondary and not self.gc.selection.button_pressed:
                self.reviving = True
                self.show_tip = False
                self.tip_frame = 0
                self.gc.play_sound("hit_button_press")
        elif self.show_tip:
            self.show_tip = False
            self.tip_frame = 0
        return False
    def collides_vertical(self, entity, dy=0):
        return False
    def draw(self):
        rect = self.blit_image(self.frames[self.anim_frame//self.anim_delay], self.rect)
        if self.show_tip or self.tip_frame < 5:
            tip = self.tip_image.copy()
            if self.tip_frame < 5:
                tip.set_alpha((self.tip_frame if self.show_tip else 5-self.tip_frame)/5*255)
            rect.union_ip(self.blit_image(
                tip, self.rect,
                xofs=self.rect.width//2-self.tip_image.get_width()//2,
                yofs=-self.tip_image.get_height()
            ))
        return rect
