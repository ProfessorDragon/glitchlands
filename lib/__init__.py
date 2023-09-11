import sys, math, os, time, json, threading, platform

import pygame
from pygame.locals import*

from . import ft5406
try: from . import profilehooks
except ImportError: profilehooks = None


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
RASPBERRY_PI = platform.machine() == "armv7l"
BASH = sys.platform != "win32"
SWAP_A_B_BUTTONS = True
PROFILE_MAINLOOP = False

if RASPBERRY_PI:
    import warnings
    warnings.filterwarnings("ignore")


## INPUT ##

class Input(object):

    keys = ["left", "right", "up", "down", "stick_button", "primary", "secondary", "x", "y", "l", "r", "l2", "r2", "escape", "start", "select", "reset", "any_button", "any_direction"]
    left, right, up, down, stick_button, primary, secondary, x, y, l, r, l2, r2, escape, start, select, reset, any_button, any_direction = [False for _ in range(len(keys))]
    button_bcm_map = {"primary": 17, "secondary": 22, "x": 4, "y": 27, "l": 19, "r": 24, "l2": 26, "r2": 23, "start": 25, "select": 21, "stick_button": 20}
    button_instances = {}
    stick_position = (0, 0)
    stick_amount = 0
    stick_angle = 0
    mouse_visible = True
    joystick_radius = 0.5
    joystick_deadzone = 0.2*joystick_radius
    battery_percent = None
    battery_charging = None
    cpu_temp = None
    memory_usage = None
    last_hardware_update = 0
    _ts = None # ft5406 instance (for touchscreen)
    _mcp = None # gpiozero.mcp3008 instance (for joystick)
    _bus = None # smbus.smbus instance (for i2c)
    _embpi = None # pyembedded.raspberry_pi_tools.raspberrypi.PI instance (for usage stats)
    _psutil = None # psutil module (substitute for other modules on windows)

    if SWAP_A_B_BUTTONS:
        button_bcm_map["primary"], button_bcm_map["secondary"] = button_bcm_map["secondary"], button_bcm_map["primary"]
        button_bcm_map["x"], button_bcm_map["y"] = button_bcm_map["y"], button_bcm_map["x"]

    @staticmethod
    def init(input_devices=True, hardware_devices=True):
        if RASPBERRY_PI:
            if input_devices:
                # try:
                #     import busio, digitalio, board
                #     import adafruit_mcp3xxx.mcp3008 as MCP
                #     from adafruit_mcp3xxx.analog_in import AnalogIn
                # except ImportError:
                #     print("Failed to load SPI")
                # else:
                #     spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
                #     cs = digitalio.DigitalInOut(board.D22)
                #     mcp = MCP.MCP3008(spi, cs)
                #     Input.joystick_x = AnalogIn(mcp, MCP.P0)
                #     Input.joystick_y = AnalogIn(mcp, MCP.P1)
                try:
                    from gpiozero import Button, MCP3008
                except ImportError:
                    print("Failed to load GPIO")
                else:
                    for k, v in Input.button_bcm_map.items():
                        Input.button_instances[k] = Button(v)
                    Input._mcp = MCP3008
                    Input.joystick_x = MCP3008(0)
                    Input.joystick_y = MCP3008(1)
                try:
                    Input._ts = ft5406.Touchscreen(device="raspberrypi-ts")
                except RuntimeError:
                    print("Failed to locate touchscreen")
                else:
                    Input._ts.run()
            if hardware_devices:
                try:
                    import smbus
                except ImportError:
                    print("Failed to load I2C")
                else:
                    Input._bus = smbus.SMBus(1)
                try:
                    from pyembedded.raspberry_pi_tools.raspberrypi import PI
                except ImportError:
                    print("Memory usage unavailable")
                else:
                    Input._embpi = PI()
        else:
            if hardware_devices:
                try:
                    import psutil
                except ImportError:
                    pass
                else:
                    Input._psutil = psutil

    @staticmethod
    def stop():
        Input.stop_gpio()
        if Input._ts is not None:
            Input._ts.stop()
    
    @staticmethod
    def stop_gpio():
        for device in Input.button_instances.values():
            device.close()

    @staticmethod
    def get_joystick():
        if Input._mcp is None: return (0, 0)
        jx = Input.joystick_y.value-Settings.joystick_calibration[4]
        jy = Input.joystick_x.value-Settings.joystick_calibration[1]
        if jx < 0:
            if Settings.joystick_calibration[3] == Settings.joystick_calibration[4]: jx = 0
            else: jx *= Input.joystick_radius/(Settings.joystick_calibration[4]-Settings.joystick_calibration[3])
        elif jx > 0:
            if Settings.joystick_calibration[5] == Settings.joystick_calibration[4]: jx = 0
            else: jx *= Input.joystick_radius/(Settings.joystick_calibration[5]-Settings.joystick_calibration[4])
        if jy < 0:
            if Settings.joystick_calibration[0] == Settings.joystick_calibration[1]: jy = 0
            else: jy *= Input.joystick_radius/(Settings.joystick_calibration[1]-Settings.joystick_calibration[0])
        elif jy > 0:
            if Settings.joystick_calibration[2] == Settings.joystick_calibration[1]: jy = 0
            else: jy *= Input.joystick_radius/(Settings.joystick_calibration[2]-Settings.joystick_calibration[1])
        return jx, jy
    
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
        Input.left = keys[K_LEFT] or keys[K_a] or keys[K_KP4]
        Input.right = keys[K_RIGHT] or keys[K_d] or keys[K_KP6]
        Input.up = keys[K_UP] or keys[K_w] or keys[K_KP8]
        Input.down = keys[K_DOWN] or keys[K_s] or keys[K_KP2]
        Input.stick_button = keys[K_BACKSLASH]
        Input.primary = keys[K_k] or keys[K_SPACE]
        Input.secondary = keys[K_l] or keys[K_e] or keys[K_SLASH] or keys[K_KP_PLUS]
        Input.x = keys[K_j]
        Input.y = keys[K_i]
        Input.l = keys[K_u]
        Input.r = keys[K_o]
        Input.l2 = False
        Input.r2 = False
        Input.start = keys[K_RETURN] or keys[K_KP_ENTER]
        Input.select = keys[K_TAB]
        Input.escape = keys[K_ESCAPE]
        Input.reset = keys[K_r]
        for name, device in Input.button_instances.items():
            if not getattr(Input, name):
                setattr(Input, name, device.is_pressed)
        if RASPBERRY_PI:
            jx, jy = Input.get_joystick()
            Input.stick_position = (jx, jy)
            Input.stick_amount = math.sqrt(jx*jx+jy*jy)
            Input.stick_angle = math.degrees(math.atan2(jy, jx))
            if Input.stick_angle < 0: Input.stick_angle += 360
            if Input.stick_amount > Input.joystick_deadzone:
                overlap = 60
                if not Input.right and (Input.stick_angle < overlap or Input.stick_angle > 360-overlap): Input.right = True
                if not Input.up and 90-overlap < Input.stick_angle < 90+overlap: Input.up = True
                if not Input.left and 180-overlap < Input.stick_angle < 180+overlap: Input.left = True
                if not Input.down and 270-overlap < Input.stick_angle < 270+overlap: Input.down = True
        else:
            jx, jy = Input.right-Input.left, Input.up-Input.down
            Input.stick_position = (jx*Input.joystick_radius, jy*Input.joystick_radius)
            Input.stick_amount = Input.joystick_radius if jx != 0 or jy != 0 else 0
            Input.stick_angle = math.degrees(math.atan2(jy, jx))
        Input.any_button = any([
            Input.primary, Input.secondary, Input.start, Input.x, Input.y,
            Input.select, Input.escape, Input.reset
        ])
        Input.any_direction = any([Input.left, Input.right, Input.up, Input.down])

    @staticmethod
    def rate_limit(new, old, limit):
        if old is None or limit is None or limit < 0: return new
        return min(max(new, old-limit), old+limit)
    
    @staticmethod
    def update_hardware(rate_limit=1, force=False):
        elapsed = time.perf_counter()-Input.last_hardware_update
        if not force:
            if elapsed < 0.5: return False
            if elapsed > 0.75: rate_limit = None 
        Input.last_hardware_update = time.perf_counter()
        try:
            if Input._bus is not None:
                bat = Input._bus.read_byte_data(0x57, 0x2a)
                Input.battery_percent = Input.rate_limit(bat, Input.battery_percent, rate_limit)
                Input.battery_charging = Input._bus.read_byte_data(0x57, 0x02) >> 7 & 1 == 1
            if Input._embpi is not None:
                Input.cpu_temp = Input._embpi.get_cpu_temp()
                ram = Input._embpi.get_ram_info()
                Input.memory_usage = float(ram[1])/float(ram[0])*100
            if Input._psutil is not None and not RASPBERRY_PI:
                bat = Input._psutil.sensors_battery()
                Input.battery_percent = bat.percent
                Input.battery_charging = bat.power_plugged
                Input.memory_usage = math.ceil(Input._psutil.virtual_memory().percent)
        except OSError:
            pass
        return True
    
    @staticmethod
    def get_key_dict():
        return {name: getattr(Input, name) for name in Input.keys}


## SETTINGS ##

class SettingsBase(object):
    save_file = None
    last_preset = None
    default_preset = None
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
    def load_else_preset(cls, preset=None):
        if preset is None:
            if cls.default_preset is None: return
            preset = cls.default_preset
        if not cls.load():
            cls.apply_preset(preset)


class Settings(SettingsBase):
    presets = {
        "low": {
            "low_detail": True,
            "reduce_motion": True,
            "enable_transparency": True,
            "enable_shaders": False,
        },
        "medium": {
            "low_detail": False,
            "reduce_motion": False,
            "enable_transparency": True,
            "enable_shaders": False,
        },
        "high": {
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
        "low_detail",
        "reduce_motion",
        "enable_transparency",
        "enable_shaders",
        "volume_music",
        "volume_sfx",
        "show_hitboxes",
        "joystick_calibration"
    ]

    windowed = False
    show_fps = True
    limit_fps = True
    vsync = False
    low_detail = False
    reduce_motion = False
    enable_transparency = True
    enable_shaders = False
    volume_music = 1 if RASPBERRY_PI else 0.2
    volume_sfx = 1 if RASPBERRY_PI else 0.2
    show_hitboxes = False
    joystick_calibration = [
        0, Input.joystick_radius, Input.joystick_radius*2, # min x, mid x, max x
        0, Input.joystick_radius, Input.joystick_radius*2  # min y, mid y, max y
    ]
    default_preset = "medium"


## MUSIC ##

class MusicManager:
    name = None
    loop_data = None
    loop_num = 0
    loop_start = 0
    loop_end = None
    crossfade_finish = None
    fade_time = 0.3
    
    @staticmethod
    def load_loop_data(fn):
        with open(fn) as f:
            MusicManager.loop_data = json.load(f)

    @staticmethod
    def play(start=0):
        if PYGAME_2: pygame.mixer.music.play(0, start, int(MusicManager.fade_time*1000))
        else: pygame.mixer.music.play(0, start)

    @staticmethod
    def play_queued(sync=True):
        def thread():
            if Settings.volume_music == 0: return
            while pygame.mixer.get_init() is None: pass
            pygame.mixer.music.load(MusicManager.name)
            pygame.mixer.music.set_volume(Settings.volume_music)
            MusicManager.play()
        if sync: thread()
        else: threading.Thread(target=thread).start()

    @staticmethod
    def fade_out():
        pygame.mixer.music.fadeout(int(MusicManager.fade_time*1000))
    
    @staticmethod
    def set_volume(volume):
        pygame.mixer.music.set_volume(volume)

    @staticmethod
    def load(name):
        if name is not None and not os.path.isfile(name): # prevent file not found error
            name = None
        if name == MusicManager.name:
            return
        if name is None:
            MusicManager.stop()
            return
        stripped = os.path.splitext(os.path.basename(name))[0]
        if MusicManager.loop_data is not None and stripped in MusicManager.loop_data:
            MusicManager.loop_start, MusicManager.loop_end = MusicManager.loop_data[stripped]
        else:
            MusicManager.loop_start, MusicManager.loop_end = 0, None
        if MusicManager.name is None or MusicManager.crossfade_finish is not None or \
            pygame.mixer.music.get_pos() <= MusicManager.fade_time:
            MusicManager.name = name
            MusicManager.play_queued(sync=True)
        else:
            MusicManager.crossfade_finish = time.perf_counter()+MusicManager.fade_time
            MusicManager.fade_out()
        MusicManager.name = name
        MusicManager.loop_num = 0

    @staticmethod
    def stop():
        if PYGAME_2: pygame.mixer.music.unload()
        else: pygame.mixer.music.stop()
        MusicManager.name = None
        MusicManager.loop_num = 0
        MusicManager.loop_start, MusicManager.loop_end = 0, None

    @staticmethod
    def update():
        if MusicManager.crossfade_finish is not None:
            if time.perf_counter() >= MusicManager.crossfade_finish:
                MusicManager.play_queued(sync=False)
                MusicManager.crossfade_finish = None
        elif MusicManager.loop_end is not None:
            elapsed = pygame.mixer.music.get_pos()
            if MusicManager.loop_num > 0: target = (MusicManager.loop_end-MusicManager.loop_start)*1000
            else: target = MusicManager.loop_end*1000
            if elapsed >= target+MusicManager.fade_time:
                MusicManager.play(MusicManager.loop_start)
            elif elapsed >= target:
                MusicManager.fade_out()


## SELECTION ##

class Selection:
    def __init__(self):
        self.idx = self.x, self.y = 0, 0
        self.max = self.xmax, self.ymax = 0, 0
        self.initial = 0, 0
        self.menu = 0
        self.submenu = 0
        self.prev_menu = 0
        self.scrollable = False
        self.button_pressed = False
        self.mouse_pressed = False
        self.using_mouse = True
        self.direction_time_x = 0
        self.direction_time_y = 0
        self.direction_delay = 0
        self.on_change = None

    def __repr__(self):
        return f"<Selection(idx={self.idx}, max={self.max}, menu={self.menu}, submenu={self.submenu})>"
    
    def set(self, idx=None, max=None, menu=None, submenu=None):
        if idx is not None:
            prev = self.idx
            self.idx = self.x, self.y = idx
            if prev != self.idx and callable(self.on_change): self.on_change(prev)
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
            
    def increment(self, x, y, avoid_indexes=None):
        if avoid_indexes is None: avoid_indexes = [self.idx]
        i = 0
        while self.idx in avoid_indexes and i < len(avoid_indexes):
            if self.xmax > 0: self.x = (self.x+x)%self.xmax
            if self.ymax > 0: self.y = (self.y+y)%self.ymax
            prev = self.idx
            self.idx = self.x, self.y
            if prev != self.idx and callable(self.on_change): self.on_change(prev)
            i += 1


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
        self.unknown_char = "?"

    def __getitem__(self, name):
        return self.get(name)
    
    def __setitem__(self, name, surface):
        self.set(name, surface)

    def __len__(self):
        return len(self.sprites)
    
    def __repr__(self):
        return f"<Fontsheet[{len(self.sprites)}]>"
    
    def add(self, char, surface):
        if len(self.sprites) == 0:
            self.tilew, self.tileh = surface.get_size()
        self.sprites[char] = surface

    def get(self, char, upper=True):
        char = str(char)
        if upper: char = char.upper()
        return self.sprites.get(char)
    
    def add_tile(self, char, im, x, y, tilesize, destsize=None):
        surface = Assets.sized_surface(tilesize, alpha=True)
        surface.blit(im, (0, 0), (x*tilesize[0], y*tilesize[1], tilesize[0], tilesize[1]))
        self.add(char, Assets.apply_size(surface, destsize))

    def set_char_widths(self, width, chars):
        for char in chars:
            self.char_widths[char] = width

    def get_width(self, text, upper=True):
        if upper: text = text.upper()
        return sum(math.floor(self.char_widths.get(char, 1)*self.tilew) for char in text)
    
    def render(self, text, **kwargs):
        if len(text) == 0: return Assets.sized_surface(1, self.tileh)
        lines = text.split("\n")
        surface = Assets.sized_surface(math.ceil(max(self.get_width(ln, **kwargs) for ln in lines)), len(lines)*self.tileh)
        y = 0
        for ln in lines:
            x = math.floor(surface.get_width()/2-self.get_width(ln, **kwargs)/2)
            for char in ln:
                render = self.get(char, **kwargs)
                if render is None: render = self.get(self.unknown_char, **kwargs)
                if render is None: continue
                surface.blit(render, (x, y))
                x += self.get_width(char, **kwargs)
            y += self.tileh
        return surface


class Collection:
    def __init__(self, items={}):
        self.items = items.copy()

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

    def get(self, name, df=None):
        return self.items.get(name, df)


class Assets(object):
    asset_dir = os.getcwd()+os.sep
    debug_font = None
    status_font = None
    status_icons = None
    status_modules = ["time", "battery", "cpu"]

    @staticmethod
    def init():
        asset_dir = Assets.asset_dir
        Assets.set_dir("assets")
        Assets.debug_font = pygame.font.Font(Assets.get("Helvetica.ttf"), 13)
        Assets.status_font = pygame.font.Font(Assets.get("Helvetica-Bold.ttf"), 14)
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
        try:
            if alpha:
                return surface.convert_alpha()
            return surface.convert()
        except pygame.error:
            return surface

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
        surface = Assets.sized_surface(96, 20*len(Assets.status_modules))
        iy = 0
        for i, name in enumerate(Assets.status_modules):
            ix = surface.get_width()-18-4 if rjust else 4
            tx, ty = ix-5 if rjust else ix+18+5, iy+3
            icon, text = None, None
            if name == "time":
                text = time.strftime("%H:%M")
            elif name == "battery":
                if Input.battery_percent is None: continue
                icon = 4 if Input.battery_charging else 0
                if Input.battery_percent > 30: icon += 1
                if Input.battery_percent > 50: icon += 1
                if Input.battery_percent > 70: icon += 1
                text = f"{Input.battery_percent}%"
            elif name == "cpu":
                if Input.cpu_temp is None: continue
                icon = 8
                if Input.cpu_temp > 50: icon += 1
                if Input.cpu_temp > 80: icon += 1
                text = f"{math.ceil(Input.cpu_temp)}°C"
            elif name == "memory":
                if Input.memory_usage is None: continue
                icon = 12
                if Input.memory_usage > 40: icon += 1
                if Input.memory_usage > 80: icon += 1
                text = f"{math.ceil(Input.memory_usage)}%"
            if icon is not None:
                icon = Assets.status_icons[icon]
                surface.blit(icon, (ix, iy))
            if text is not None:
                text = Assets.status_font.render(text, False, WHITE)
                if icon is None: tx = ix+18 if rjust else ix
                if rjust: tx -= text.get_width()
                surface.blit(text, (tx, ty))
            iy += 20
        if iy < surface.get_height():
            surface = surface.subsurface(0, 0, surface.get_width(), iy)
        return surface


## GAMECONTROLLER ##

class GameControllerBase:
    def __init__(self):
        self.save_base = os.path.abspath("save")
        self.game_size = self.game_width, self.game_height = 800, 480
        self.screen_info = pygame.display.Info()
        self.screen_size = self.screen_width, self.screen_height = self.screen_info.current_w, self.screen_info.current_h
        self.running = False
        self.buffer_touch_selection = False
        self.frame = 0

    def init_display(self):
        if Settings.windowed:
            outsize = self.game_size
            i = 1
            while outsize[0] <= self.screen_width and outsize[1] <= self.screen_height:
                i += 1
                outsize = (self.game_width*i, self.game_height*i)
            outsize = (self.game_width*(i-1), self.game_height*(i-1))
        else:
            outsize = self.screen_size
        if PYGAME_2:
            flags = pygame.DOUBLEBUF
        else:
            flags = pygame.HWSURFACE | pygame.HWACCEL | pygame.ASYNCBLIT
        main_flags = flags | (pygame.RESIZABLE if Settings.windowed else pygame.FULLSCREEN)
        if PYGAME_2 and not RASPBERRY_PI:
            self.main_surface = pygame.display.set_mode(outsize, main_flags, vsync=Settings.vsync)
        else:
            self.main_surface = pygame.display.set_mode(outsize, main_flags)
        self.output_size = self.output_width, self.output_height = self.main_surface.get_size()
        self.screen = pygame.Surface(self.game_size, flags)
        if not Settings.enable_transparency:
            self.main_surface.set_alpha(None)
            self.screen.set_alpha(None)
    
    def init(self):
        self.init_display()
        Assets.init()
        Input.init()
        Input.set_touch_handlers(
            press=self.handle_touch_event,
            release=self.handle_touch_event,
            move=self.handle_touch_event
        )
        self.selection = Selection()
        if RASPBERRY_PI:
            self.selection.disable_mouse()
            pygame.event.set_blocked(None)
            pygame.event.set_allowed(pygame.QUIT)
        else:
            self.selection.enable_mouse()
        self.hidden = False
    
    def handle_touch_event(self, event, touch):
        if self.hidden or not self.running: return
        if event == ft5406.TS_MOVE: # touch down or move
            self.selection.disable_mouse()
            prev = self.selection.mouse_pressed
            self.selection.mouse_pressed = True
            self.update_cursor_selection(just_pressed=not prev, touch_pos=touch.position)
        elif event == ft5406.TS_RELEASE: # else touch up
            self.buffer_touch_selection = True
    
    def get_cursor_pos(self, touch_pos=None):
        if touch_pos is None:
            x, y = pygame.mouse.get_pos() # between (0, 0) and (output_width, output_height)
            x *= self.game_width/self.output_width # scale to (game_width, game_height)
            y *= self.game_height/self.output_height
        else:
            x, y = touch_pos # between (0, 0) and (screen_width, screen_height)
            x *= self.game_width/self.screen_width # scale to (game_width, game_height)
            y *= self.game_height/self.screen_height
        return int(x), int(y)

    def update_cursor_selection(self, just_pressed=False, touch_pos=None):
        pass

    def launch_selection(self):
        pass

    def update(self):
        pass

    def draw(self):
        pass

    def draw_overlays(self):
        pass

    def patch_background(self, rect):
        pass

    def scale_rect(self, rect, xscale, yscale):
        new = rect.copy()
        new.w = new.w*xscale
        new.h = new.h*yscale
        new.x = new.x*xscale
        new.y = new.y*yscale
        return new
    
    def ease_to(self, value, target, ease=4, snap=2):
        if abs(target-value) < snap: return target
        return value + (target-value)/ease

    def mainloop(self):
        self.clock = pygame.time.Clock()
        self.running = True
        self.rects = []
        self.prev_rects = []

        while self.running:
            self.dt = self.clock.tick(60 if Settings.limit_fps else 0)/1000
            if self.hidden: continue
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                if event.type == pygame.VIDEORESIZE and Settings.windowed:
                    self.output_size = self.output_width, self.output_height = event.dict["size"]
                elif event.type == pygame.MOUSEMOTION:
                    if RASPBERRY_PI:
                        self.selection.disable_mouse()
                    else:
                        self.selection.enable_mouse()
                        self.update_cursor_selection()
                elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP) and not RASPBERRY_PI:
                    if event.button == 1:
                        if event.type == pygame.MOUSEBUTTONDOWN:
                            self.selection.mouse_pressed = True
                            self.update_cursor_selection(just_pressed=True)
                        else:
                            self.launch_selection()
                            self.selection.mouse_pressed = False
            self.update()
            if self.buffer_touch_selection:
                self.launch_selection()
                self.selection.mouse_pressed = False
                self.buffer_touch_selection = False

            self.draw()
            self.draw_overlays()
            if self.hidden: continue
            try:
                if self.output_size == self.game_size:
                    self.main_surface.blit(self.screen, (0, 0))
                else:
                    self.main_surface.blit(pygame.transform.scale(self.screen, self.output_size), (0, 0))
            except pygame.error: continue
            pygame.display.update()
            # self.rects = list(filter(lambda rect: rect is not None, self.rects))
            # xscale, yscale = self.output_width/self.game_width, self.output_height/self.game_height
            # inflated = [self.scale_rect(rect, xscale, yscale).inflate(3, 3) for rect in self.rects+self.prev_rects]
            # pygame.display.update(inflated)
            # for rect in self.rects:
            #     self.patch_background(rect)
            self.prev_rects = self.rects[:]
            self.frame += 1

        Input.stop()
        pygame.quit()
    
    if PROFILE_MAINLOOP and profilehooks is not None: mainloop = profilehooks.profile(mainloop)
