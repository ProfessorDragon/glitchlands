import math, random, threading
import pygame
from lib import*


## CONSTANTS ##

# objects

OBJTYPE_SPIKE = -3
OBJTYPE_SEMISOLID = -2
OBJTYPE_BEAM = -1
OBJTYPE_BLOCK = 0
OBJTYPE_TEXT = 1
OBJTYPE_DECO = 2
OBJTYPE_TRIGGER = 3
OBJTYPE_UPGRADE = 4
OBJTYPE_FIRETRAP = 5
OBJTYPE_CRUSHER = 6
OBJTYPE_GLITCHZONE = 7
OBJTYPE_FALLINGPLATFORM = 8
OBJTYPE_BUTTON = 9
OBJTYPE_TIMEDGATE = 10
OBJTYPE_CRYSTALBARRIER = 11
OBJTYPE_UPGRADETIP = 12
OBJTYPE_ONEWAYGATE = 13
OBJTYPE_GOO = 14
OBJTYPE_NPC = 15
OBJTYPE_SAWTRAP = 16
OBJTYPE_VINES = 17
OBJTYPE_BAT = 18
OBJTYPE_HITBUTTON = 19
OBJTYPE_VIRUSBOSS = 20

COLLISION_NONE = 0
COLLISION_BLOCK = 1
COLLISION_HAZARD = 2
COLLISION_SHIELDBREAK = 3
COLLISION_PASS = -1

# menus

MENU_MAIN = 0
MENU_IN_GAME = 0

MENU_SLOT_SELECT = 1
SUBMENU_SLOT_SELECT = 0
SUBMENU_SLOT_ACTION = 1
SUBMENU_DIFFICULTY_SELECT = 2
SUBMENU_COPY_SLOT = 3

MENU_SETTINGS = 2
MENU_CREDITS = 3
SUBMENU_SKIP_CREDITS = 0
SUBMENU_NO_SKIP_CREDITS = 1
MENU_PAUSED = 4
MENU_MAP = 5
MENU_COMPLETION = 6


## GENERAL ##

class LevelData:
    def __init__(self, pos):
        self.level_pos = pos
        self.level_pos_left = (pos[0], pos[1]-1, pos[2])
        self.level_pos_right = (pos[0], pos[1]+1, pos[2])
        self.level_pos_top = (pos[0], pos[1], pos[2]-1)
        self.level_pos_bottom = (pos[0], pos[1], pos[2]+1)
        self.fn = self.get_fn(pos)

    def get_fn(self, pos):
        return Assets.get(f"levels/{','.join([str(n) for n in pos])}.json")
    
    def exists(self, pos=None):
        if pos is None:
            return os.path.isfile(self.fn)
        return LevelData(pos).exists()
    
    def load(self):
        with open(self.fn) as f:
            self.json_data = json.load(f)
        self.background = self.json_data.get("background", 0)
        if self.background == -1: self.background = random.randint(0, 6)
        elif self.background == -2: self.background = random.randint(7, 13)
        elif self.background == -3: self.background = random.randint(0, 13)
        self.terrain_style = self.json_data.get("terrain_style", [0, 0, 0])
        self.checkpoint_positions = self.json_data.get("checkpoint_positions", [None, None, None])
        self.scroll_left = self.json_data.get("scroll_left", True)
        self.scroll_right = self.json_data.get("scroll_right", True)
        self.bottom_exit_left = self.json_data.get("bottom_exit_left")
        self.bottom_exit_right = self.json_data.get("bottom_exit_right")
        self.transition = self.json_data.get("transition")
        self.rookie_checkpoints = self.json_data.get("rookie_checkpoints", False)
        if "warp_left" in self.json_data:
            self.warp_left = self.json_data["warp_left"]
            if self.warp_left is None: self.level_pos_left = None
            else: self.level_pos_left = tuple(self.warp_left)
        if "warp_right" in self.json_data:
            self.warp_right = self.json_data["warp_right"]
            if self.warp_right is None: self.level_pos_right = None
            else: self.level_pos_right = tuple(self.warp_right)
        if "warp_top" in self.json_data:
            self.warp_top = self.json_data["warp_top"]
            if self.warp_top is None: self.level_pos_top = None
            else: self.level_pos_top = tuple(self.warp_top)
        if "warp_bottom" in self.json_data:
            self.warp_bottom = self.json_data["warp_bottom"]
            if self.warp_bottom is None: self.level_pos_bottom = None
            else: self.level_pos_bottom = tuple(self.warp_bottom)
        self.objects = self.json_data.get("objects", [])
        self.glitch_zones = self.json_data.get("glitch_zones", [])

class Background:
    def __init__(self, gc, num=0):
        self.gc = gc
        self.num = num
        self.prev_num = num
        self.xofs = 16
        self.yofs = 16
        self.move_speed = .25
        self.rotate_speed = 0
        self.transition_timer = 0
        self.transition_dir = 0
        self.randomize_direction()
        self.generate_image()
        self.still_image = None

    def generate_image(self):
        self.tile = self.gc.assets.backgrounds[self.num]
        self.tilew, self.tileh = self.tile.get_size()
        if self.transition_timer > 0:
            prev_tile = self.gc.assets.backgrounds[self.prev_num].copy()
            transformed = pygame.transform.rotozoom(
                self.tile.convert_alpha(),
                self.transition_timer/9*self.transition_dir,
                min((12-self.transition_timer)/9, 1)
            )
            prev_tile.blit(transformed, transformed.get_rect(center=(self.tilew//2, self.tileh//2)))
        else:
            prev_tile = None
        self.image = Assets.tile_surface_fill(
            prev_tile if prev_tile is not None else self.tile,
            self.gc.game_width+self.tilew,
            self.gc.game_height+self.tilew
        )
        if self.transition_timer == 0: self.generate_glitch_image()

    def generate_glitch_image(self):
        self.glitch_image = self.image.copy()
        self.glitch_image.blit(
            random.choice(self.gc.assets.backgrounds),
            (random.randint(0, self.gc.game_width//self.tilew)*self.tilew,
             random.randint(0, self.gc.game_height//self.tileh)*self.tileh)
            )
        
    def generate_pause_image(self):
        self.still_image = self.gc.screen.copy()
        overlay = Assets.sized_surface(self.gc.game_size)
        pygame.draw.rect(overlay, BLACK, (0, 0, self.gc.game_width, self.gc.game_height))
        overlay.set_alpha(128)
        self.still_image.blit(overlay, (0, 0))

    def randomize_direction(self):
        if self.num < 14:
            self.dir = {
                1: random.choice((-90, 90)),
                3: random.choice((0, 180)),
                4: random.choice((45, 275)),
                6: random.choice((-45, 135))
            }.get(self.num%7, random.randint(0, 3)*90-45)
        else:
            self.dir = random.randint(0, 359)

    def change_to(self, num, side=0, change_dir=True):
        if self.num == num and side == 0 and not change_dir: return
        self.prev_num = self.num
        self.num = num
        self.randomize_direction()
        if Settings.reduce_motion or side == 0:
            self.transition_timer = 0
            self.generate_image()
        else:
            self.transition_timer = 11
            self.transition_dir = 60*(-1 if side > 0 else 1)

    def update(self):
        if self.transition_timer > 0:
            self.transition_timer -= 1
            self.generate_image()
        self.xofs += math.cos(math.radians(self.dir))*self.move_speed
        self.yofs += math.sin(math.radians(self.dir))*self.move_speed
        self.dir += self.rotate_speed
        if self.xofs < 0: self.xofs += self.tilew
        elif self.xofs > self.tilew: self.xofs -= self.tilew
        if self.yofs < 0: self.yofs += self.tileh
        elif self.yofs > self.tileh: self.yofs -= self.tileh
    
    @property
    def use_still_image(self):
        if self.still_image is None:
            return False
        if self.gc.in_game:
            return self.gc.selection.menu != MENU_IN_GAME
        else:
            return self.gc.selection.menu in (MENU_CREDITS, MENU_COMPLETION)

    def draw(self):
        if self.use_still_image:
            return self.gc.screen.blit(self.still_image, (0, 0))
        glitch = self.transition_timer == 0 and \
            self.gc.glitch_chance >= 0 and random.randint(0, self.gc.glitch_chance)//20 == 0
        return self.gc.screen.blit(self.glitch_image if glitch else self.image, (-self.tilew+self.xofs, -self.tileh+self.yofs))


class FullscreenOverlay:
    def __init__(self, gc, fade=(0, 0, 0), color=None, surface=None, shake=0):
        self.gc = gc
        self.image = Assets.sized_surface((gc.game_width+shake*2, gc.game_height+shake*2))
        if color is not None: self.image.fill(color)
        if surface is not None: self.image.blit(pygame.transform.scale(surface, self.gc.game_size), (shake, shake))
        self.fade_in, self.hold, self.fade_out = fade
        self.shake = shake
        self.level_pos = None
        self.timer = 0

    @property
    def completed(self):
        return self.timer >= self.fade_in+self.hold+self.fade_out
    
    @property
    def halfway(self):
        return self.timer >= self.fade_in+self.hold/2
    
    def update(self):
        self.timer += 1

    def draw(self):
        if self.completed: return
        if self.timer >= self.fade_in+self.hold: # fade out
            opacity = 1-(self.timer-self.fade_in-self.hold)/self.fade_out
        elif self.timer >= self.fade_in: # hold
            opacity = 1
        else: # fade in
            opacity = self.timer/self.fade_in
        if not Settings.enable_transparency and opacity < .75: return
        self.image.set_alpha(opacity*255)
        if self.shake != 0:
            pos = (random.randint(-self.shake*2, 0), random.randint(-self.shake*2, 0))
        else:
            pos = (0, 0)
        return self.gc.screen.blit(self.image, pos)


class Checkpoint:
    def __init__(self, level_pos, left=None, right=None, top=None, bottom=None, centerx=None, facing_right=True):
        self.level_pos = level_pos
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom
        self.centerx = centerx
        self.facing_right = facing_right
        self.update_valid()

    def __repr__(self):
        return f"<Checkpoint({self.get_set_sides()})"
    
    def update_valid(self):
        self.valid = self.level_pos is not None and \
            (self.left, self.right, self.centerx).count(None) == 2 and \
            (self.top, self.bottom).count(None) == 1
        
    def get_set_sides(self):
        cp = {}
        if self.left is not None: cp["left"] = self.left
        if self.right is not None: cp["right"] = self.right
        if self.top is not None: cp["top"] = self.top
        if self.bottom is not None: cp["bottom"] = self.bottom
        if self.centerx is not None: cp["centerx"] = self.centerx
        return cp
    
    def to_json(self):
        return {
            "level_pos": self.level_pos,
            "facing_right": self.facing_right,
            **self.get_set_sides()
        }
    
    def load_json(self, json_data):
        self.level_pos = tuple(json_data["level_pos"])
        self.left = json_data.get("left")
        self.right = json_data.get("right")
        self.top = json_data.get("top")
        self.bottom = json_data.get("bottom")
        self.centerx = json_data.get("centerx")
        self.facing_right = json_data.get("facing_right")
        self.update_valid()


class Selection:
    def __init__(self):
        self.idx = self.x, self.y = 0, 0
        self.max = self.xmax, self.ymax = 0, 0
        self.menu = 0
        self.submenu = 0
        self.prev_menu = 0
        self.scrollable = False
        self.button_pressed = False
        self.using_mouse = True
        self.direction_time = 0

    def __repr__(self):
        return f"<Selection(idx={self.idx}, max={self.max}, menu={self.menu}, submenu={self.submenu})>"
    
    def set(self, idx=None, max=None, menu=None, submenu=None):
        if idx is not None: self.idx = self.x, self.y = idx
        if max is not None: self.max = self.xmax, self.ymax = max
        if menu is not None and menu != self.menu:
            self.prev_menu = self.menu
            self.menu = menu
        if submenu is not None: self.submenu = submenu
        self.scrollable = False

    def enable_mouse(self):
        if not self.using_mouse:
            self.using_mouse = True
            Input.show_mouse(True)

    def disable_mouse(self):
        if self.using_mouse:
            self.using_mouse = False
            Input.show_mouse(False)
            
    def increment(self, x, y):
        if self.xmax > 0: self.x = (self.x+x)%self.xmax
        if self.ymax > 0: self.y = (self.y+y)%self.ymax
        self.idx = self.x, self.y


class DialogueState:
    def __init__(self):
        self.slides = []
        self.npc_num = 0
        self.idx = -1
        self.change_frame = 0
        self.finish_handler = None

    def update(self):
        if self.shown:
            self.change_frame += 1

    def show(self, slides, finish_handler=None):
        self.slides = slides
        self.idx = 0
        self.change_frame = 0
        self.finish_handler = finish_handler

    def hide(self):
        self.idx = -1
        if callable(self.finish_handler): self.finish_handler()

    def advance(self):
        self.idx += 1
        self.change_frame = 0
        if self.idx > len(self.slides)-1:
            self.hide()

    @property
    def shown(self):
        return self.idx >= 0

    @property
    def hidden(self):
        return self.idx < 0

    @property
    def current(self):
        return self.slides[self.idx]


class DialogueSlide:
    def __init__(self, owner, content=None, crystals=0):
        self.owner = owner
        self.content = content
        self.crystals = crystals


class GlobalSave(SettingsBase):
    presets = {
        "none": {
            "completed_difficulties": []
        },
        "unlock": {
            "completed_difficulties": [0, 1, 2]
        }
    }
    all = [
        "completed_difficulties"
    ]

    completed_difficulties = []
    unlock_master = False
    unlock_skip = False

    @classmethod
    def update_extras(cls):
        cls.unlock_master = len(GlobalSave.completed_difficulties) > 0
        cls.unlock_skip = len(GlobalSave.completed_difficulties) > 0


class MusicManager:
    def __init__(self):
        self.name = None
        self.loop_num = 0
        self.loop_start = 0
        self.loop_end = None
        self.crossfade_finish = None
        self.fade_time = 0.3

    def play(self, start=0):
        if PYGAME_2: pygame.mixer.music.play(0, start, int(self.fade_time*1000))
        else: pygame.mixer.music.play(0, start)

    def play_queued(self, sync=True):
        def thread():
            pygame.mixer.music.load(Assets.get(f"music/{self.name}.mp3"))
            pygame.mixer.music.set_volume(MUSIC_VOLUME)
            self.play()
        if sync: thread()
        else: threading.Thread(target=thread).start()

    def fade_out(self):
        pygame.mixer.music.fadeout(int(self.fade_time*1000))

    def load(self, name):
        if name == self.name: return
        if name is None:
            self.stop()
            return
        with open(Assets.get("music/loop.json")) as f:
            loop = json.load(f)
        self.loop_start, self.loop_end = loop.get(name, [0, None])
        if self.name is None or self.crossfade_finish is not None or pygame.mixer.music.get_pos() <= self.fade_time:
            self.name = name
            self.play_queued(sync=True)
        else:
            self.crossfade_finish = time.perf_counter()+self.fade_time
            self.fade_out()
        self.name = name
        self.loop_num = 0

    def stop(self):
        if PYGAME_2: pygame.mixer.music.unload()
        else: pygame.mixer.music.stop()
        self.name = None
        self.loop_num = 0
        self.loop_start, self.loop_end = 0, None

    def update(self):
        if self.crossfade_finish is not None:
            if time.perf_counter() >= self.crossfade_finish:
                self.play_queued(sync=False)
                self.crossfade_finish = None
        elif self.loop_end is not None:
            elapsed = pygame.mixer.music.get_pos()
            if self.loop_num > 0: target = (self.loop_end-self.loop_start)*1000
            else: target = self.loop_end*1000
            if elapsed >= target+self.fade_time:
                self.play(self.loop_start)
            elif elapsed >= target:
                self.fade_out()
