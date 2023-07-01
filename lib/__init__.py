import math, os, time, json, platform

import pygame
from pygame.locals import*

from lib import ft5406


## CONSTANTS ##

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)

LEFT = "left"
RIGHT = "right"
UP = "up"
DOWN = "down"

PYGAME_2 = pygame.version.vernum.major == 2
RASPBERRY_PI = platform.uname()[4].startswith("arm")
USER_NAME = os.path.expandvars("$USER" if RASPBERRY_PI else "%username%")

if RASPBERRY_PI:
    import warnings
    warnings.filterwarnings("ignore")


## INPUT ##

class Input(object):

    keys = ["left", "right", "up", "down", "stick", "jump", "secondary", "x", "y", "escape", "start", "select", "reset", "any_button", "any_direction"]
    left, right, up, down, stick, jump, secondary, x, y, escape, start, select, reset, any_button, any_direction = [False for _ in range(len(keys))]
    mouse_visible = True
    joystick_center = (32736, 32736)
    joystick_threshold = 8000
    battery_percent = None
    battery_charging = None
    cpu_temp = None
    last_hardware_update = 0
    _mcp = None # mcp.mcp3008 instance (for analogue input)
    _ts = None # ft5406 instance (for touchscreen)
    _gpio = None # rpi.gpio module
    _bus = None # smbus.smbus instance (for i2c)

    @staticmethod
    def init():
        if RASPBERRY_PI:
            try:
                import RPi.GPIO as GPIO
            except ImportError:
                print("Failed to load GPIO")
            else:
                Input._gpio = GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(26, GPIO.IN, pull_up_down=GPIO.PUD_UP) # stick
            try:
                import busio, digitalio, board
                import adafruit_mcp3xxx.mcp3008 as MCP
                from adafruit_mcp3xxx.analog_in import AnalogIn
            except ImportError:
                print("Failed to load SPI")
            else:
                spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
                cs = digitalio.DigitalInOut(board.D5)
                Input._mcp = MCP.MCP3008(spi, cs)
                Input.joystick_x = AnalogIn(Input._mcp, MCP.P0)
                Input.joystick_y = AnalogIn(Input._mcp, MCP.P1)
                Input.joystick_button = AnalogIn(Input._mcp, MCP.P2)
                time.sleep(0.5)
                Input.joystick_center = Input.joystick_x.value, Input.joystick_y.value
            try:
                import smbus
            except ImportError:
                print("Failed to load I2C")
            else:
                Input._bus = smbus.SMBus(1)
            try:
                Input._ts = ft5406.Touchscreen(device="raspberrypi-ts")
            except RuntimeError:
                print("Failed to locate touchscreen")
            else:
                Input._ts.run()

    @staticmethod
    def stop():
        if Input._ts is not None:
            Input._ts.stop()
        if Input._gpio is not None:
            Input._gpio.cleanup()

    @staticmethod
    def get_joystick():
        if Input._mcp is None: return (0, 0)
        return -(Input.joystick_x.value-Input.joystick_center[0]), -(Input.joystick_y.value-Input.joystick_center[1])
    
    @staticmethod
    def set_touch_handlers(press=None, release=None, move=None):
        if Input._ts is None: return
        for touch in Input._ts.touches:
            touch.on_press = press
            touch.on_release = release
            touch.on_move = move
        
    @staticmethod
    def show_mouse(shown):
        Input.mouse_visible = shown
        if hasattr(pygame, "SYSTEM_CURSOR_ARROW"):
            if shown: pygame.mouse.set_cursor(SYSTEM_CURSOR_ARROW)
            else: pygame.mouse.set_cursor((8,8),(0,0),(0,0,0,0,0,0,0,0),(0,0,0,0,0,0,0,0))
        else:
            pygame.mouse.set_visible(shown)

    @staticmethod
    def update(keys):
        jx, jy = Input.get_joystick()
        Input.left = keys[K_LEFT] or keys[K_a] or keys[K_KP4] or jx < -Input.joystick_threshold
        Input.right = keys[K_RIGHT] or keys[K_d] or keys[K_KP6] or jx > Input.joystick_threshold
        Input.up = keys[K_UP] or keys[K_w] or keys[K_KP8] or jy < -Input.joystick_threshold
        Input.down = keys[K_DOWN] or keys[K_s] or keys[K_KP2] or jy > Input.joystick_threshold
        Input.stick = Input._gpio is not None and not Input._gpio.input(26)
        Input.primary = keys[K_k] or keys[K_SPACE] # or btn_a
        Input.secondary = keys[K_l] or keys[K_e] or keys[K_SLASH] or keys[K_KP_PLUS] # or btn_b
        Input.x = keys[K_j] # or btn_x
        Input.y = keys[K_i] # or btn_y
        Input.start = keys[K_RETURN] or keys[K_KP_ENTER] # or btn_start
        Input.select = keys[K_TAB] # or btn_select
        Input.escape = keys[K_ESCAPE]
        Input.reset = keys[K_r]
        Input.any_button = any([Input.primary, Input.secondary, Input.start, Input.select, Input.escape, Input.reset])
        Input.any_direction = any([Input.left, Input.right, Input.up, Input.down])
    
    @staticmethod
    def update_hardware(force=False):
        if not force and time.perf_counter()-Input.last_hardware_update < 0.5:
            return False
        Input.last_hardware_update = time.perf_counter()
        if Input._bus is not None:
            bat = Input._bus.read_byte_data(0x57, 0x2a)
            if Input.battery_percent is None: Input.battery_percent = bat
            else: Input.battery_percent = min(max(bat, Input.battery_percent-2), Input.battery_percent+2)
            Input.battery_charging = Input._bus.read_byte_data(0x57, 0x02) >> 7 & 1 == 1
            Input.cpu_temp = Input._bus.read_byte_data(0x57, 0x04)-40
        return True
    
    @staticmethod
    def get_key_dict():
        return {name: getattr(Input, name) for name in Input.keys}


## SETTINGS ##

class SettingsBase(object):
    save_file = None
    presets = {}
    all = []

    @classmethod
    def get(cls, key):
        return getattr(cls, key)
    
    @classmethod
    def set(cls, key, value):
        setattr(cls, key, value)
        cls.update_extras()
    
    @classmethod
    def update_extras(cls):
        pass
    
    @classmethod
    def apply_preset(cls, name):
        assert name in cls.presets
        for k, v in cls.presets[name].items():
            cls.set(k, v)
        cls.last_preset = name
    
    @classmethod
    def log(cls):
        for k in vars(cls):
            if k not in ("__module__", "all", "presets", "display_names"):
                print(f"{k}: {cls.get(k)}")

    @classmethod
    def save(cls):
        if cls.save_file is None: return False
        os.makedirs(os.path.dirname(cls.save_file), exist_ok=True)
        attrs = {k: cls.get(k) for k in cls.all}
        with open(cls.save_file, "w") as f:
            json.dump(attrs, f, indent=2)
        return True
    
    @classmethod
    def load(cls):
        if cls.save_file is None or not os.path.isfile(cls.save_file): return False
        with open(cls.save_file) as f:
            attrs = json.load(f)
        for k, v in attrs.items():
            cls.set(k, v)
        return True
    
    @classmethod
    def load_else_preset(cls, preset):
        if not cls.load(): cls.apply_preset(preset)


class Settings(SettingsBase):
    presets = {
        "pi": {
            "fullscreen_refresh": True,
            "maintain_fullscreen_ratio": False,
            "low_detail": True,
            "reduce_motion": False,
            "enable_transparency": False,
            "enable_shaders": False,
        },
        "ultra_low": {
            "fullscreen_refresh": False,
            "maintain_fullscreen_ratio": True,
            "low_detail": True,
            "reduce_motion": True,
            "enable_transparency": True,
            "enable_shaders": False,
        },
        "low": {
            "fullscreen_refresh": False,
            "maintain_fullscreen_ratio": False,
            "low_detail": False,
            "reduce_motion": True,
            "enable_transparency": True,
            "enable_shaders": False,
        },
        "medium": {
            "fullscreen_refresh": True,
            "maintain_fullscreen_ratio": False,
            "low_detail": False,
            "reduce_motion": False,
            "enable_transparency": True,
            "enable_shaders": False,
        },
        "high": {
            "fullscreen_refresh": True,
            "maintain_fullscreen_ratio": False,
            "low_detail": False,
            "reduce_motion": False,
            "enable_transparency": True,
            "enable_shaders": True,
        }
    }
    display_names = {
        "windowed": "Windowed",
        "show_fps": "Show FPS",
        "limit_fps": "Limit FPS",
        "vsync": "Vsync",
        "fullscreen_refresh": "Fullscreen refresh",
        "maintain_fullscreen_ratio": "Maintain fullscreen ratio",
        "low_detail": "Low detail",
        "reduce_motion": "Reduce motion",
        "enable_transparency": "Enable transparency",
        "enable_shaders": "Enable shaders",
        "volume_music": "Music volume",
        "volume_sfx": "SFX volume",
        "show_hitboxes": "Show hitboxes",
    }
    all = [
        "windowed",
        "show_fps",
        "limit_fps",
        "vsync",
        "fullscreen_refresh",
        "maintain_fullscreen_ratio",
        "low_detail",
        "reduce_motion",
        "enable_transparency",
        "enable_shaders",
        "volume_music",
        "volume_sfx",
        "show_hitboxes",
    ]

    windowed = False
    show_fps = True
    limit_fps = True
    vsync = False
    fullscreen_refresh = True
    maintain_fullscreen_ratio = False
    low_detail = False
    reduce_motion = False
    enable_transparency = True
    enable_shaders = False
    volume_music = 0.2
    volume_sfx = 0.2
    show_hitboxes = False
    last_preset = None


## ASSETS ##

class Spritesheet:
    def __init__(self, width, height, hflip=False, vflip=False):
        self.width = width # tiles on x axis
        self.height = height # tiles on y axis
        self.hflip = hflip
        self.vflip = vflip
        self.sprites = []
        self.sprites_hflip = []
        self.sprites_vflip = []
        self.sprites_hvflip = []

    def __getitem__(self, key):
        return self.sprites[key]
    
    def __setitem__(self, key, value):
        self.sprites[key] = value

    def __len__(self):
        return len(self.sprites)
    
    def __repr__(self):
        return f"<Spritesheet[{len(self.sprites)}]>"
    
    def add(self, surface):
        self.sprites.append(surface)
        if self.hflip: self.sprites_hflip.append(pygame.transform.flip(surface, True, False))
        if self.vflip: self.sprites_vflip.append(pygame.transform.flip(surface, False, True))
        if self.hflip and self.vflip: self.sprites_hvflip.append(pygame.transform.flip(surface, True, True))

    def get(self, x, y=0, hflip=False, vflip=False):
        index = x+y*self.width
        if hflip and vflip: return self.sprites_hvflip[index]
        if hflip: return self.sprites_hflip[index]
        if vflip: return self.sprites_vflip[index]
        return self.sprites[index]
    
    def add_tile(self, im, x, y, tilesize, destsize=None, alpha=True):
        surface = Assets.sized_surface(tilesize, alpha=alpha)
        surface.blit(im, (0, 0), (x*tilesize[0], y*tilesize[1], tilesize[0], tilesize[1]))
        self.add(Assets.apply_size(surface, destsize))


class Fontsheet:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.sprites = {}
        self.char_widths = {}
        self.set_char_widths(.66, " .,!")

    def __getitem__(self, name):
        return self.sprites[str(name).upper()]
    
    def __setitem__(self, name, surface):
        if len(self.sprites) == 0:
            self.tilew, self.tileh = surface.get_size()
        self.sprites[name] = surface

    def __len__(self):
        return len(self.sprites)
    
    def __repr__(self):
        return f"<Fontsheet[{len(self.sprites)}]>"
    
    def add(self, char, surface):
        self[char] = surface

    def get(self, char):
        return self[char]
    
    def add_tile(self, char, im, x, y, tilesize, destsize=None):
        surface = Assets.sized_surface(tilesize, alpha=True)
        surface.blit(im, (0, 0), (x*tilesize[0], y*tilesize[1], tilesize[0], tilesize[1]))
        self.add(char, Assets.apply_size(surface, destsize))

    def set_char_widths(self, width, chars):
        for char in chars:
            self.char_widths[char] = width

    def get_width(self, text):
        return sum(self.char_widths.get(char, 1)*self.tilew for char in text)
    
    def render(self, text):
        if len(text) == 0: return
        if len(text) == 1: return self.get(text)
        lines = text.split("\n")
        surface = Assets.sized_surface(math.ceil(max(self.get_width(ln) for ln in lines)), len(lines)*self.tileh)
        y = 0
        for ln in lines:
            x = math.floor(surface.get_width()/2-self.get_width(ln)/2)
            for char in ln:
                surface.blit(self.get(char), (x, y))
                x += math.floor(self.get_width(char))
            y += self.tileh
        return surface


class Collection:
    def __init__(self):
        self.items = {}

    def __getitem__(self, name):
        return self.items[str(name)]
    
    def __setitem__(self, name, item):
        self.items[str(name)] = item

    def __len__(self):
        return len(self.items)
    
    def __repr__(self):
        return f"<Collection({self.items})>"
    
    def add(self, name, item):
        self[name] = item

    def get(self, name):
        return self[name]


class Assets(object):
    asset_dir = os.getcwd()+os.pathsep
    debug_font = None
    status_font = None
    status_icons = None

    @staticmethod
    def init():
        asset_dir = Assets.asset_dir
        Assets.set_dir("assets")
        Assets.debug_font = pygame.font.SysFont("Helvetica", 13)
        Assets.status_font = pygame.font.SysFont("Helvetica", 14, bold=True)
        Assets.status_icons = Assets.load_spritesheet("status_icons.png", (9, 9), (18, 18))
        Assets.asset_dir = asset_dir

    @staticmethod
    def set_dir(folder=""):
        Assets.asset_dir = os.path.join(os.getcwd(), folder)

    @staticmethod
    def get(path):
        return os.path.join(Assets.asset_dir, path)

    @staticmethod
    def convert_surface(surface, alpha=True):
        if alpha:
            return surface.convert_alpha()
        return surface.convert()

    @staticmethod
    def sized_surface(*size, alpha=True):
        assert len(size) in (1, 2)
        if len(size) == 1: size = size[0]
        if alpha:
            return pygame.Surface(size, pygame.SRCALPHA, 32)
        return pygame.Surface(size)

    @staticmethod
    def apply_size(surface, size):
        if size is None: return surface
        return pygame.transform.scale(surface, size)

    @staticmethod
    def load_image(path, size=None, alpha=True):
        if isinstance(path, pygame.Surface): im = path.copy()
        else: im = pygame.image.load(Assets.get(path))
        return Assets.apply_size(Assets.convert_surface(im, alpha=alpha), size)

    @staticmethod
    def load_spritesheet(path, tilesize=None, destsize=None, hflip=False, vflip=False, alpha=True):
        im = Assets.load_image(path, alpha=alpha)
        if tilesize is None: tilesize = (min(im.get_size()), min(im.get_size()))
        sheet = Spritesheet(im.get_width()//tilesize[0], im.get_height()//tilesize[1], hflip=hflip, vflip=vflip)
        for y in range(sheet.height):
            for x in range(sheet.width):
                sheet.add_tile(im, x, y, tilesize, destsize, alpha=alpha)
        return sheet

    @staticmethod
    def load_terrain(path, groups, tilesize, destsize=None):
        im = Assets.load_image(path, alpha=True)
        collection = Collection()
        i = 0
        for layout, x, y in groups:
            if layout == 0:
                w, h = 5, 3
                alpha = False
                offsets = [
                    (0, 0), (1, 0), (2, 0),
                    (0, 1), (1, 1), (2, 1),
                    (0, 2), (1, 2), (2, 2),
                    (3, 0), (4, 0), (3, 1), (4, 1),
                    (3, 2)
                ]
            elif layout == 1:
                w, h = 4, 3
                alpha = False
                offsets = [
                    (0, 0), (1, 0), (2, 0),
                    (3, 0), (3, 1), (3, 2),
                    (1, 1), (2, 1), (1, 2), (2, 2),
                    (0, 1)
                ]
            elif layout in (2, 3):
                w, h = 3 if layout == 2 else 4, 1
                alpha = True
                offsets = [(n, 0) for n in range(w)]
            else: continue
            sheet = Spritesheet(w, h)
            for xofs, yofs in offsets:
                sheet.add_tile(im, x+xofs, y+yofs, tilesize, destsize, alpha=alpha)
            collection.add(i, sheet)
            i += 1
        return collection

    @staticmethod
    def load_font(path, tilesize, destsize=None, charset="ABCDEFGHIJKLMNOPQRSTUVWXYZ    0123456789.,:?!()+-'"):
        im = Assets.load_image(path, alpha=True)
        sheet = Fontsheet(im.get_width()//tilesize[0], im.get_height()//tilesize[1])
        for i, char in enumerate(charset):
            sheet.add_tile(char, im, i%sheet.width, i//sheet.width, tilesize, destsize)
        return sheet

    @staticmethod
    def load_sound(path, volume=1):
        sound = pygame.mixer.Sound(Assets.get(path))
        sound.set_volume(volume)
        return sound

    @staticmethod
    def load_text(path, json_=False):
        with open(Assets.get(path)) as f:
            if json_: return json.load(f)
            return f.read()

    @staticmethod
    def recursive_loader(file_func, folder_func, path, *args, filetypes=None, **kwargs):
        collection = Collection()
        for fn in os.listdir(Assets.get(path)):
            absfn = os.path.join(Assets.get(path), fn)
            if os.path.isdir(absfn):
                if folder_func is not None:
                    v = folder_func(os.path.join(path, fn), *args, **kwargs)
            elif filetypes is None or os.path.splitext(absfn)[1][1:].lower() in filetypes:
                if file_func is not None:
                    v = file_func(os.path.join(path, fn), *args, **kwargs)
            else: continue
            collection.add(os.path.splitext(fn)[0], v)
        return collection

    @staticmethod
    def load_image_dir(path, *args, **kwargs):
        return Assets.recursive_loader(
            Assets.load_image, Assets.load_image_dir,
            path, filetypes=("png",), *args, **kwargs
        )

    @staticmethod
    def load_spritesheet_dir(path, *args, **kwargs):
        return Assets.recursive_loader(
            Assets.load_spritesheet, Assets.load_spritesheet_dir,
            path, filetypes=("png",), *args, **kwargs
        )

    @staticmethod
    def load_sound_dir(path, *args, **kwargs):
        return Assets.recursive_loader(
            Assets.load_sound, Assets.load_sound_dir,
            path, filetypes=("mp3", "wav", "ogg"), *args, **kwargs
        )

    @staticmethod
    def tile_surface_repetition(tile, xrep, yrep, alpha=True):
        tilew, tileh = tile.get_size()
        im = Assets.sized_surface(tilew*xrep, tileh*yrep, alpha=alpha)
        for x in range(xrep):
            for y in range(yrep):
                im.blit(tile, (x*tilew, y*tileh))
        return im

    @staticmethod
    def tile_surface_fill(tile, width, height):
        tilew, tileh = tile.get_size()
        im = pygame.Surface((width, height))
        for x in range(im.get_width()//tilew+1):
            for y in range(im.get_height()//tileh+1):
                im.blit(tile, (x*tilew, y*tileh))
        return im
    
    @staticmethod
    def status_indicator(rjust=False):
        surface = Assets.sized_surface(96, 20 if Input.cpu_temp is None else 40)
        x = surface.get_width()-18-4 if rjust else 4
        y = 0
        if Input.battery_percent is not None:
            icon = 4 if Input.battery_charging else 0
            if Input.battery_percent > 30: icon += 1
            if Input.battery_percent > 50: icon += 1
            if Input.battery_percent > 75: icon += 1
            surface.blit(Assets.status_icons[icon], (x, y))
            text = Assets.status_font.render(f"{Input.battery_percent}%", False, WHITE)
            surface.blit(text, (x-text.get_width()-4 if rjust else x+22, y))
            y += 20
        if Input.cpu_temp is not None:
            icon = 8
            if Input.cpu_temp > 25: icon += 1
            if Input.cpu_temp > 45: icon += 1
            surface.blit(Assets.status_icons[icon], (x, y))
            text = Assets.status_font.render(f"{Input.cpu_temp}°C", False, WHITE)
            surface.blit(text, (x-text.get_width()-4 if rjust else x+22, y))
            y += 20
        return surface
