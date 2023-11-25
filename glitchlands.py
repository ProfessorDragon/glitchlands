import os, time, json, random, shutil, webbrowser
from functools import cmp_to_key
from argparse import ArgumentParser

from lib import*
from lib_glitchlands import*
from lib_glitchlands import player, objects, ui, particles

import pygame
pygame.mixer.pre_init(44100, -16, 2, 1024)
pygame.init()
try: from PygameShader import shader
except ImportError: shader = None


class AssetLoader:
    def __init__(self):
        Assets.set_dir("assets_glitchlands")

    def load(self): # load main assets
        self.player = Assets.load_spritesheet_dir("player", (32, 32), (64, 64), hflip=True, vflip=True)
        self.backgrounds = Assets.load_spritesheet("ui/backgrounds.png", (64, 64), (128, 128), alpha=False)
        self.sounds = Assets.load_sound_dir("sounds")
        charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ  %/0123456789.,:?!()+-'"
        self.font = Assets.load_font("ui/font.png", (10, 12), (20, 24), charset=charset)
        self.font.set_char_widths(.5, "'")
        self.font_outlined = Assets.load_font("ui/font_outlined.png", (12, 14), (24, 28), charset=charset)
        self.font_outlined.set_char_widths(.5, ":'")
        self.font_small = Assets.load_font("ui/font_small.png", (8, 10), (16, 20))
        self.font_small.set_char_widths(1.1, "MW")
        self.font_small.set_char_widths(.5, ":'")
        self.font_small.set_char_widths(.4, " ")

        self.ui = Collection()
        self.ui.add("menu_buttons", Assets.load_spritesheet("ui/menu_buttons.png", (96, 16), (192, 32)))
        self.ui.add("menu_buttons_small", Assets.load_spritesheet("ui/menu_buttons_small.png", (18, 14), (36, 28)))
        self.ui.add("menu_icons", Assets.load_spritesheet("ui/menu_icons.png", (9, 9), (18, 18)))
        self.ui.add("slot_buttons", Assets.load_spritesheet("ui/slot_buttons.png", (96, 64), (192, 128)))
        self.ui.add("switch", Assets.load_spritesheet("ui/switch.png", (64, 16), (128, 32)))
        self.ui.add("slider", Assets.load_spritesheet("ui/slider.png", (64, 8), (128, 16)))
        self.ui.add("dialogue_container", Assets.load_image("ui/dialogue_container.png", (784, 160)))
        self.ui.add("crystal_counter", Assets.load_spritesheet("ui/crystal_counter.png", (24, 16), (48, 32)))
        self.ui.add("key_icons", Assets.load_spritesheet("ui/key_icons.png", (12, 12), (24, 24)))
        self.ui.add("credits", Assets.load_text("ui/credits.txt"))

        terrain_image = Assets.load_image("objects/terrain.png")
        self.terrain = [ # terrain[type][style][num]
            Assets.load_terrain(terrain_image, [ # blocks
                (0, 6, 0), (0, 6, 4), (0, 6, 8), (0, 0, 0), (0, 0, 4), (0, 0, 8), (0, 17, 4), (0, 21, 0)
            ], (16, 16), (32, 32)),
            Assets.load_terrain(terrain_image, [ # beams
                (1, 12, 0), (1, 12, 4), (1, 12, 8), (1, 17, 8), (1, 22, 8)
            ], (16, 16), (32, 32)),
            Assets.load_terrain(terrain_image, [ # bridges
                (2, 17, 1),(2, 17, 2), (2, 17, 0)
            ], (16, 16), (32, 32)),
            Assets.load_terrain(terrain_image, [ # spikes
                (3, 0, 3)
            ], (16, 16), (32, 32))
        ]

        self.objects = Collection()
        self.objects.add("upgrade_stand", Assets.load_spritesheet("objects/upgrade_stand.png", (32, 32), (64, 64)))
        self.objects.add("fire_trap", Assets.load_spritesheet("objects/fire_trap.png", (16, 32), (32, 64), vflip=True))
        self.objects.add("saw_trap", Assets.load_spritesheet("objects/saw_trap.png", (38, 38), (76, 76), hflip=True))
        self.objects.add("crusher", Assets.load_spritesheet("objects/crusher.png", (64, 48), (128, 96)))
        self.objects.add("falling_platform", Assets.load_spritesheet("objects/falling_platform.png", (32, 16), (64, 32)))
        self.objects.add("one_way_gate", Assets.load_spritesheet("objects/one_way_gate.png", (48, 48), (96, 96), hflip=True))
        self.objects.add("goo", Assets.load_image("objects/goo.png", (128, 128)))
        self.objects.add("npc", Assets.load_spritesheet("objects/npc.png", (32, 32), (64, 64), hflip=True))
        self.objects.add("bat", Assets.load_spritesheet("objects/bat.png", (46, 28), (92, 56), hflip=True))
        for name in ("upgrades", "button", "dark_spikes", "rgb_spikes", "glitch_crystal"):
            self.objects.add(name, Assets.load_spritesheet(f"objects/{name}.png", (16, 16), (32, 32)))

        self.decoration = Collection()
        self.decoration.add("title", Assets.load_spritesheet("decoration/title.png", (256, 64), (512, 128)))
        self.decoration.add("credit_top", Assets.load_spritesheet("decoration/credit_top.png", (150, 10), (450, 30)))
        self.decoration.add("credit_bottom", Assets.load_spritesheet("decoration/credit_bottom.png", (150, 10), (450, 30)))
        self.decoration.add("meteor", Assets.load_spritesheet("decoration/meteor.png", (44, 56), (44*2, 56*2)))
        self.decoration.add("upgrade_deco_1", self.objects["upgrades"].get(x=0, y=0))
        self.decoration.add("upgrade_deco_2", self.objects["upgrades"].get(x=0, y=1))
        self.decoration.add("upgrade_deco_3", self.objects["upgrades"].get(x=0, y=2))
        self.decoration.add("vines", Assets.load_spritesheet("decoration/vines.png", (48, 48), (96, 96)))
        self.decoration.add("signs", Assets.load_spritesheet("decoration/signs.png", (32, 32), (64, 64)))
        self.decoration.add("virus_transition", Assets.load_image("virus/transition.png", (800, 480), alpha=False))

        self.particles = Collection()
        self.particles.add("spawn", Assets.load_spritesheet("decoration/spawn.png"))
        sil = Assets.load_image("decoration/silhouette.png", (64, 128))
        self.particles.add("silhouette", sil)
        self.particles.add("silhouette_hflip", pygame.transform.flip(sil, True, False))
        self.particles.add("circle_red", self.circle_particle(RED))
        self.particles.add("circle_green", self.circle_particle(GREEN))
        self.particles.add("circle_blue", self.circle_particle(BLUE))
        self.particles.add("circle_white", self.circle_particle(WHITE))
        self.particles.add("circle_black", self.circle_particle(BLACK))
        self.particles.add("square_red", self.square_particle(RED))
        self.particles.add("square_green", self.square_particle(GREEN))
        self.particles.add("square_blue", self.square_particle(BLUE))
        self.particles.add("square_white", self.square_particle(WHITE))
        self.particles.add("square_black", self.square_particle(BLACK))

        self.map = Collection()
        self.map.add("data", Assets.load_text("map/data.json", json_=True))
        self.map.add("icons", Assets.load_spritesheet("map/icons.png", (15, 15), (30, 30)))
    
    def load_virus(self): # load assets only used for the virus bossfight
        if hasattr(self, "virus"):
            return
        self.virus = Collection()
        self.virus.add("idle", Assets.load_spritesheet("virus/idle.png", (200, 104), (800, 416)))
        self.virus.add("mad", Assets.load_spritesheet("virus/mad.png", (200, 104), (800, 416)))
        self.virus.add("side", Assets.load_spritesheet("virus/side.png", (116, 96), (464, 384), hflip=True))
        split_frames = Assets.load_spritesheet("virus/split.png", (24, 48), (96, 192))
        self.virus.add("split_left", split_frames[0])
        self.virus.add("split_right", split_frames[1])
        self.virus.add("tentacle_drill", Assets.load_spritesheet("virus/tentacle_drill.png", (32, 32), (64, 64), vflip=True))
        self.virus.add("hit_button", Assets.load_spritesheet("virus/hit_button.png", (32, 16), (64, 32)))
        self.virus.add("infection", Assets.load_spritesheet("virus/infection.png", (32, 16), (64, 32), hflip=True))
        self.virus.add("crystal_barrier", Assets.load_spritesheet("virus/crystal_barrier.png", (32, 16), (64, 32)))
        self.virus.add("arena_barrier", Assets.load_spritesheet("virus/arena_barrier.png", (32, 16), (64, 32)))
        self.virus.add("tombstone", Assets.load_spritesheet("virus/tombstone.png", (32, 48), (64, 96)))
    
    def unload_virus(self):
        if hasattr(self, "virus"):
            del self.virus

    def load_preload(self): # load specific assets before main assets (such as the game icon)
        if hasattr(self, "preload"):
            return
        self.preload = Collection()
        self.preload.add("icon", pygame.image.load(Assets.get("ui/icon.png")))

    def circle_particle(self, color):
        surface = Assets.sized_surface(8, 8)
        pygame.draw.circle(surface, color, (4, 4), 4)
        return surface
    
    def square_particle(self, color):
        surface = Assets.sized_surface(8, 8)
        surface.fill(color)
        return surface
    
    def save_slot_image(self, slot, fn):
        if fn is not None and os.path.isfile(fn):
            with open(fn) as f:
                save_data = json.load(f)
        else:
            save_data = None
        im = self.ui["slot_buttons"][0 if save_data is None else save_data.get("difficulty", 0)+1].copy()
        cx = im.get_width()//2
        if slot >= 0:
            text = self.font_small.render(f"Slot {slot+1}")
            im.blit(text, (cx-text.get_width()//2, 10))
        if save_data is not None:
            icon = None
            if save_data.get("completed_time") is not None:
                icon = 4 if save_data["completed_time"] == GlobalSave.best_time and GlobalSave.speedrun_mode else 5
            if icon is not None:
                im.blit(self.ui.get("menu_icons")[icon], (im.get_width()-10-18, 10))
            text = self.font_small.render(["Rookie", "Normal", "Master"][save_data.get("difficulty", 0)])
            im.blit(text, (cx-text.get_width()//2, 42))
            if GlobalSave.speedrun_mode and save_data.get("completed_time") is not None: t = save_data["completed_time"]
            else: t = save_data.get("elapsed_time", 0)
            hours, rem = divmod(t, 3600)
            minutes, seconds = divmod(rem, 60)
            text = self.font_small.render("{:0>2}:{:0>2}:{:0>2}".format(int(hours), int(minutes), math.ceil(seconds)))
            im.blit(text, (cx-text.get_width()//2, 64))
            deaths = save_data.get("death_count", 0)
            text = self.font_small.render("1 death" if deaths == 1 else f"{deaths} deaths")
            im.blit(text, (cx-text.get_width()//2, 86))
        elif slot < 0:
            text = self.font_small.render("Saving is\ndisabled")
            im.blit(text, (cx-text.get_width()//2, 42))
        else:
            text = self.font_small.render("Empty")
            im.blit(text, (cx-text.get_width()//2, 64))
        return im

    def shield_static(self, sheet, copies=1, min_alpha=0, max_alpha=128):
        out = Spritesheet(sheet.width*copies, sheet.height*copies, hflip=sheet.hflip, vflip=sheet.vflip)
        for frame in sheet.sprites:
            for _ in range(copies):
                surface = frame.copy()
                for x in range(0, surface.get_width(), 2):
                    for y in range(0, surface.get_height(), 2):
                        if surface.get_at((x, y)) == (69, 69, 69, 255):
                            pygame.draw.rect(surface, (255, 255, 255, random.randint(min_alpha, max_alpha)), (x, y, 2, 2))
                out.add(surface)
        return out


class GameController(GameControllerBase):
    def __init__(self):
        super().__init__()
        self.save_slot = 0
        for drive in ("U",):
            if os.path.exists(drive+":\\"): self.save_base = drive+":\\glitchlands_save"
        GlobalSave.save_file = os.path.join(self.save_base, "glitchlands", "global.json")
        GlobalSave.load()
        Settings.save_file = os.path.join(self.save_base, "settings.json")
        Settings.load_else_preset()
        self.shown_settings = []
        if not RASPBERRY_PI: self.shown_settings.append("windowed")
        self.shown_settings.extend(["show_fps", "show_hitboxes"])
        if PYGAME_2: self.shown_settings.append("vsync")
        self.shown_settings.extend(["low_detail", "reduce_motion"])
        if shader is None:
            if Settings.enable_shaders:
                Settings.enable_shaders = False
                print("PygameShader module is required to enable shaders")
        else:
            self.shown_settings.append("enable_shaders")
        if GlobalSave.unlock_speedrun:
            self.shown_settings.append("speedrun_mode")

    def init_display(self):
        super().init_display()
        pygame.display.set_caption("Glitchlands")
        pygame.display.set_icon(self.assets.preload.get("icon"))

    def init_level(self, begin=True):
        self.in_game = True
        self.frame = 0
        self.load_level_full((0, 0, 0)) # load level data
        self.player = player.Player(self) # create player
        self.background.change_to(self.level.background)
        self.checkpoint = Checkpoint(self.level.level_pos, left=self.player.x, bottom=self.player.y+self.player.recth)
        self.npc_dialogue = DialogueState()
        self.xscroll, self.xscroll_target = 0, 0
        self.scroll_bounds = int(self.game_width*.51)
        self.ambience_timer = None
        self.visited_levels = {self.level.level_pos}
        self.visited_npcs = set()
        self.visited_one_ways = set()
        self.visited_final_world = False
        self.crystal_count, self.max_crystal_count, self.crystal_requirements = 0, 12, [5, 4, 3]
        self.death_count = 0
        self.elapsed_time = 0
        self.completed_time = None
        self.splits = []
        if begin:
            self.disable_pause()
            self.restore_progress()

    def init(self):
        self.assets = AssetLoader()
        self.assets.load_preload()
        self.in_game = False
        self.should_toggle_in_game = False
        self.level = None
        self.xscroll, self.xscroll_target = 0, 0
        self.glitch_chance = -1
        self.difficulty = 1
        self.transition = None
        super().init()
        MusicManager.load_loop_data(Assets.get("music/loop.json"))
        self.assets.load()
        self.background = Background(self, random.randint(0, 6))
        self.set_menu(MENU_MAIN)
    
    def save_progress(self):
        now = time.perf_counter()
        self.elapsed_time += now-self.elapsed_time_start
        self.elapsed_time_start = now
        fn = self.get_save_file()
        if fn is None: return
        save_data = {
            "checkpoint": self.checkpoint.to_json(),
            "abilities": self.player.abilities.to_json(),
            "splits": [[split[0], split[1]] for split in self.splits]
        }
        for attr in ("visited_levels", "visited_npcs", "visited_one_ways"):
            save_data[attr] = list(getattr(self, attr))
        for attr in ("visited_final_world", "crystal_count", "glitch_chance", "difficulty",
                     "death_count", "elapsed_time", "completed_time"):
            save_data[attr] = getattr(self, attr)
        os.makedirs(os.path.dirname(fn), exist_ok=True)
        with open(fn, "w") as f:
            json.dump(save_data, f, separators=(",", ":"))
    
    def restore_progress(self):
        fn = self.get_save_file()
        if fn is None or not os.path.isfile(fn):
            self.create_levels_auto(clear=True)
            self.load_music()
            return
        with open(fn) as f:
            save_data = json.load(f)
        self.checkpoint.load_json(save_data["checkpoint"])
        self.player.abilities.load_json(save_data["abilities"])
        for attr in ("visited_levels", "visited_npcs", "visited_one_ways"):
            setattr(self, attr, set(tuple(pos) for pos in save_data.get(attr, getattr(self, attr))))
        for attr in ("visited_final_world", "crystal_count", "glitch_chance", "difficulty",
                     "death_count", "elapsed_time", "completed_time"):
            setattr(self, attr, save_data.get(attr, getattr(self, attr)))
        self.splits = [(split[0], split[1], self.format_elapsed(split[1])) for split in save_data.get("splits", [])]
        self.restore_checkpoint(initial=True)
    
    def restore_checkpoint(self, cp=None, initial=False):
        if cp is None: cp = self.checkpoint
        assert cp.valid
        if self.level.level_pos != cp.level_pos or initial:
            if self.level.level_pos[0] == cp.level_pos[0] and self.level.level_pos[2] == cp.level_pos[2]:
                self.xscroll += (self.level.level_pos[1]-cp.level_pos[1])*self.game_width
            else:
                self.xscroll = 0
                self.xscroll_target = 0
            self.append_visited(cp.level_pos, only_next=True)
            self.load_level_full(cp.level_pos)
            self.create_levels_auto(clear=True)
            self.load_music()
        self.player.reset()
        self.player.move_hitbox(left=cp.left, right=cp.right, top=cp.top, bottom=cp.bottom, centerx=cp.centerx)
        if initial: self.player.facing_right = cp.facing_right
        self.player.revive()
        self.player.update_hitbox()
        self.push_particle(particles.AnimatedParticle(self, "spawn", self.player.hitbox.center, anim_delay=3))
        self.background.change_to(self.level.background, change_dir=False)
        if not self.scroll_right and self.xscroll > 0: self.xscroll = 0
        elif not self.scroll_left and self.xscroll < 0: self.xscroll = 0
    
    def get_save_file(self, slot=None):
        if slot is None: slot = self.save_slot
        if slot < 0: return None
        return os.path.join(self.save_base, "glitchlands", f"slot{slot}.json")
    
    def skip_intro(self):
        self.player.abilities.set_all(False)
        self.glitch_chance = 3000
        self.checkpoint = Checkpoint((1, 0, 0), centerx=self.game_width//2, top=0, facing_right=False)
        self.restore_checkpoint(initial=True)

    def defeat_virus(self):
        elapsed = self.get_elapsed_time()
        if self.completed_time is None:
            self.completed_time = elapsed
            self.add_split("Game completed")
        unlock = SUBMENU_NO_UNLOCK
        if not self.difficulty in GlobalSave.completed_difficulties:
            GlobalSave.completed_difficulties.append(self.difficulty)
        if GlobalSave.best_time is None or elapsed < GlobalSave.best_time:
            GlobalSave.best_time = elapsed
            if GlobalSave.speedrun_mode:
                unlock = SUBMENU_BEST_TIME
        if not GlobalSave.unlock_speedrun and elapsed < 60*60:
            unlock = SUBMENU_UNLOCK_SPEEDRUN
            GlobalSave.unlock_speedrun = True
            self.shown_settings.append("speedrun_mode")
            if not GlobalSave.unlock_master:
                unlock = SUBMENU_UNLOCK_MASTER_SPEEDRUN
                GlobalSave.unlock_master = True
        elif not GlobalSave.unlock_master:
            unlock = SUBMENU_UNLOCK_MASTER
            GlobalSave.unlock_master = True
        GlobalSave.save()
        self.glitch_chance = -1
        self.save_progress()
        self.in_game = False
        self.level = None
        self.set_menu(MENU_COMPLETION, unlock)

    def load_level_full(self, pos):
        self.level = LevelData(pos)
        self.level.load()
        self.load_level_left()
        self.load_level_right()
        self.load_level_top()
        self.load_level_bottom()
    
    def load_level_left(self):
        self.scroll_left = not Settings.reduce_motion and self.level.scroll_left
        if self.level.level_pos_left is not None and self.level.exists(self.level.level_pos_left):
            self.level_left = LevelData(self.level.level_pos_left)
            self.level_left.load()
        else:
            self.level_left = None
            self.scroll_left = False

    def load_level_right(self):
        self.scroll_right = not Settings.reduce_motion and self.level.scroll_right
        if self.level.level_pos_right is not None and self.level.exists(self.level.level_pos_right):
            self.level_right = LevelData(self.level.level_pos_right)
            self.level_right.load()
        else:
            self.level_right = None
            self.scroll_right = False
    
    def load_level_top(self):
        if self.level.level_pos_top is not None and self.level.exists(self.level.level_pos_top):
            self.level_top = LevelData(self.level.level_pos_top)
            self.level_top.load()
        else:
            self.level_top = None

    def load_level_bottom(self):
        if self.level.level_pos_bottom is not None and self.level.exists(self.level.level_pos_bottom):
            self.level_bottom = LevelData(self.level.level_pos_bottom)
            self.level_bottom.load()
        else:
            self.level_bottom = None
    
    def load_music(self, name=None):
        if Settings.volume_music == 0:
            MusicManager.load(None)
            return
        if name is None: # no name specified, auto-detect
            if self.level is not None:
                name = f"world{self.level.level_pos[0]}"
            elif not self.in_game:
                name = "menu"
        elif name == "none":
            name = None
        MusicManager.load(Assets.get(f"music/{name}.ogg"))

    def play_sound(self, name, volume=1):
        if Settings.volume_sfx == 0: return
        sound = self.assets.sounds.get(name)
        sound.set_volume(Settings.volume_sfx*volume)
        sound.play()
    
    def get_elapsed_time(self):
        if self.selection.menu != MENU_IN_GAME: return self.elapsed_time
        return self.elapsed_time+time.perf_counter()-self.elapsed_time_start
    
    def add_split(self, name=None):
        if name is None: name = "Unknown"
        elapsed = self.get_elapsed_time()
        self.splits.append((name, elapsed, self.format_elapsed(elapsed)))
    
    def format_elapsed(self, elapsed):
        hours, rem = divmod(elapsed, 3600)
        minutes, rem = divmod(rem, 60)
        seconds, milliseconds = divmod(rem, 1)
        formatted = "{:0>2}:{:0>2}.{:0>2}".format(int(minutes), int(seconds), math.ceil(milliseconds*100))
        if hours > 0: formatted = "{:0>2}:".format(int(hours))+formatted
        return formatted

    def get_block_objects(self):
        return self.objects_nocollide+self.objects_collide

    def get_deco_objects(self):
        return self.background_deco+self.foreground_deco+self.glitch_zones

    def get_all_objects(self):
        return self.get_block_objects()+self.get_deco_objects()

    def enable_pause(self, menu=MENU_PAUSED):
        self.save_progress()
        self.background.generate_pause_image()
        self.set_menu(menu)
        if menu in (MENU_PAUSED, MENU_MAP): self.play_sound("pause")
    
    def disable_pause(self):
        if self.selection.menu in (MENU_PAUSED, MENU_MAP): self.play_sound("unpause")
        self.elapsed_time_start = time.perf_counter()
        self.set_menu(MENU_IN_GAME)
    
    def adjust_music_volume(self, prev, cur):
        if cur == 0: MusicManager.stop()
        elif prev == 0: self.load_music()
        else: MusicManager.set_volume(cur)

    def set_menu(self, menu, submenu=0, idx=(0, 0)):
        self.ui_objects = []
        mx = [0, 0]
        scrollable = False
        buttons = self.assets.ui.get("menu_buttons")
        buttons_small = self.assets.ui.get("menu_buttons_small")
        if not self.in_game and menu == MENU_MAIN:
            ui.create_graphic(self, self.assets.decoration.get("title"), cy=160, anim_delay=30)
            nums = [0, 2, 3]
            for i, num in enumerate(nums):
                ui.create_button(self, buttons[num], (0, i), cy=320+i*40)
            ui.create_button(self, buttons_small[0], (0, len(nums)), cx=self.game_width-30, cy=25, hit_inflate=(12, 12))
            mx = [0, len(nums)+1]
            if not RASPBERRY_PI:
                ui.create_button(self, buttons_small[1], (0, len(nums)+1), hit_inflate=(12, 12),
                                 cx=self.game_width-30, cy=self.game_height-25)
                mx[1] += 1
            self.load_music()
        elif self.in_game and menu == MENU_PAUSED:
            nums = [10, 2, 11]
            if GlobalSave.unlock_master and self.level.level_pos[0] == 0 and all(pos[0] == 0 for pos in self.visited_levels):
                nums.insert(-1, 12)
            elif GlobalSave.speedrun_mode:
                nums.insert(-1, 15)
            ui.create_text(self, "Paused", cy=160)
            for i, num in enumerate(nums):
                ui.create_button(self, buttons[num], (0, i), cy=220+i*40)
            mx = [0, len(nums)]
        elif menu == MENU_SLOT_SELECT:
            if submenu in (SUBMENU_SLOT_SELECT, SUBMENU_COPY_SLOT):
                if submenu == SUBMENU_SLOT_SELECT:
                    ui.create_text(self, "Select save file", cy=130)
                else:
                    ui.create_text(self, "Select destination", cy=130)
                nums = range(4) if self.save_slot < 4 else range(4, 8)
                for i, num in enumerate(nums):
                    im = self.assets.save_slot_image(num, self.get_save_file(num))
                    ui.create_button(self, im, (i, 0), cx=self.game_width//2+(-(len(nums)-1)/2+i)*198, cy=250)
                ui.create_button(self, buttons[1], [(0, 1), (1, 1)], cx=self.game_width//2-99, cy=370)
                ui.create_button(self, buttons[19 if self.save_slot < 4 else 18], [(2, 1), (3, 1)],
                                 cx=self.game_width//2+99, cy=370)
                mx = [len(nums), 2]
            elif submenu in (SUBMENU_SLOT_ACTION, SUBMENU_DIFFICULTY_SELECT):
                if submenu == SUBMENU_SLOT_ACTION:
                    nums = [9, 1, 4, 5]
                    ui.create_text(self, "Load file", cy=130)
                else:
                    nums = [6, 1, 7, 8 if GlobalSave.unlock_master else 13]
                    ui.create_text(self, "Select difficulty", cy=130)
                ui.create_graphic(self, self.assets.save_slot_image(self.save_slot, self.get_save_file()))
                ui.create_button(self, buttons[nums[0]], (0, 0), cx=300, cy=360)
                ui.create_button(self, buttons[nums[1]], (0, 1), cx=300, cy=400)
                ui.create_button(self, buttons[nums[2]], (1, 0), cx=500, cy=360)
                ui.create_button(self, buttons[nums[3]], (1, 1), cx=500, cy=400)
                mx = [2, 2]
            elif submenu == SUBMENU_CONFIRM_DELETE:
                ui.create_text(self, f"Delete slot {self.save_slot+1}?", cy=200)
                ui.create_button(self, buttons[17], (0, 0), cx=self.game_width//2-110, cy=270)
                ui.create_button(self, buttons[16], (1, 0), cx=self.game_width//2+110, cy=270)
                mx = [2, 1]
        elif menu == MENU_SETTINGS:
            switch = self.assets.ui.get("switch")
            ui.create_text(self, "Settings", cy=70)
            x, y = self.game_width//2, 130 if len(self.shown_settings) > 7 else 150
            for i, attr in enumerate(self.shown_settings):
                cls = GlobalSave if attr in GlobalSave.all else Settings # i love oop
                text = ui.create_text(self, cls.display_names.get(attr, ""), cy=y)
                text.rect.right = x-20
                obj = ui.create_button(self, switch[1 if cls.get(attr) else 2], (0, i), cy=y)
                obj.rect.left = x
                y += 40
            x += 270
            ui.create_text(self, "Music", cx=x, cy=190)
            ui.create_slider(self, "volume_music", 1 if RASPBERRY_PI else 0.5, [(1, 0), (1, 1), (1, 2), (1, 3)],
                             cx=x, cy=215, callback=self.adjust_music_volume)
            ui.create_text(self, "SFX", cx=x, cy=270)
            ui.create_slider(self, "volume_sfx", 1 if RASPBERRY_PI else 0.5, [(1, 4), (1, 5)],
                             cx=x, cy=295)
            ui.create_button(self, buttons[1], [(1, 6), (1, 7)], cx=x, cy=390)
            mx = [2, len(self.shown_settings)]
        elif menu in (MENU_CREDITS, MENU_COMPLETION):
            self.background.still_image = Assets.sized_surface(self.game_size)
            self.background.still_image.fill((30, 30, 30))
            if menu == MENU_CREDITS:
                ui.create_graphic(self, self.assets.decoration.get("title"), cy=500, anim_delay=30)
                text = ui.create_text(self, self.assets.ui.get("credits"))
                text.rect.top = 700
                ui.create_graphic(self, self.assets.player.get("walk").sprites_hflip, cx=700, cy=850, anim_delay=6)
                ui.create_graphic(self, self.assets.objects.get("crusher")[0], cx=100, cy=1300)
                ui.create_graphic(self, self.assets.objects.get("fire_trap")[:3], cx=700, cy=1700, anim_delay=6)
                scrollable = True
            else:
                ui.create_graphic(self, self.assets.decoration.get("title"), cy=120, anim_delay=30)
                hours, rem = divmod(self.elapsed_time, 3600)
                minutes, seconds = divmod(rem, 60)
                text = "Congratulations!\nYou have beaten the game\non "
                text += ["Rookie", "Normal", "Master"][self.difficulty]
                text += " difficulty.\n\nTime: "
                text += "{:0>2}:{:0>2}:{:0>2}".format(int(hours), int(minutes), int(seconds))
                text += f"  Deaths: {self.death_count}\n\n"
                if submenu == SUBMENU_UNLOCK_MASTER: text += "Master difficulty has\nbeen unlocked"
                elif submenu == SUBMENU_UNLOCK_SPEEDRUN: text += "Speedrun mode has been\nunlocked"
                elif submenu == SUBMENU_UNLOCK_MASTER_SPEEDRUN: text += "Master difficulty and\n speedrun mode have been\nunlocked"
                elif submenu == SUBMENU_BEST_TIME: text += "New personal best!"
                else: text += "Press any button to continue"
                ui.create_text(self, text, cy=340)
            self.selection.disable_mouse()
            self.load_music()
        elif menu == MENU_MAP:
            level_size = (100, 60)
            color_key = [
                (170, 186, 206), # light
                (213, 177, 149),
                (194, 194, 194),
                (147, 197, 150),
                (209, 169, 191),
                (181, 169, 201),
                (213, 204, 158),
                (85, 69, 49), # dark
                (42, 78, 106),
                (61, 61, 61),
                (108, 58, 105),
                (46, 86, 64),
                (74, 86, 54),
                (42, 51, 97),
                (255, 0, 255), # missing
                (136, 0, 136),
            ]
            visited = {self.level.level_pos, *self.visited_levels}
            level_icons = [] # (num, x, y)
            teleporter_lines = [] # (x1, y1, x2, y2)
            visited_levels, total_levels = 0, 0
            for world, world_data in enumerate(self.assets.map.get("data")):
                for pos_string, tile_data in world_data.get("levels", {}).items():
                    total_levels += 1
                    pos = (world,)+tuple(int(n) for n in pos_string.split(","))
                    if pos not in visited and pos != self.level.level_pos: continue
                    visited_levels += 1
                    icon_key = {
                        "upgrade": 2,
                        "lever": 3,
                        "crystal": 6 if pos in [npc[1:] for npc in self.visited_npcs] else 5,
                        "teleporter": 7,
                        "virus": 8
                    }
                    color = tile_data.get("color", 2)
                    if pos == self.level.level_pos: color = self.background.num
                    elif color == -1: color = random.randint(0, 6)
                    elif color == -2: color = random.randint(7, 13)
                    elif color == -3: color = random.randint(0, 13)
                    fill = color_key[color]
                    if color in (7, 8, 9, 10, 11, 12, 13, 15): stroke = tuple(int(n*1.3) for n in fill)
                    else: stroke = tuple(int(n*.8) for n in fill)
                    surface = Assets.sized_surface(level_size)
                    surface.fill(fill)
                    borders = tile_data.get("borders", [])
                    pygame.draw.rect(surface, stroke, (0, 0, level_size[0], level_size[1]), 2)
                    border_w, border_h = math.ceil((level_size[0]-4)/3), math.ceil((level_size[1]-4)/3),
                    level_left = tuple(tile_data["left"]) if "left" in tile_data else (pos[0], pos[1]-1, pos[2])
                    level_top = tuple(tile_data["top"]) if "top" in tile_data else (pos[0], pos[1], pos[2]-1)
                    level_right = tuple(tile_data["right"]) if "right" in tile_data else (pos[0], pos[1]+1, pos[2])
                    level_bottom = tuple(tile_data["bottom"]) if "bottom" in tile_data else (pos[0], pos[1], pos[2]+1)
                    if level_left in visited:
                        if 0 in borders:
                            pygame.draw.rect(surface, fill, (0, level_size[1]-2-border_h, 3, border_h))
                        if 1 in borders:
                            pygame.draw.rect(surface, fill, (0, level_size[1]//2-border_h//2, 3, border_h))
                        if 2 in borders:
                            pygame.draw.rect(surface, fill, (0, 2, 3, border_h))
                    if level_top in visited:
                        if 3 in borders:
                            pygame.draw.rect(surface, fill, (2, 0, border_w, 3))
                        if 4 in borders:
                            pygame.draw.rect(surface, fill, (level_size[0]//2-border_w//2, 0, border_w, 3))
                        if 5 in borders:
                            pygame.draw.rect(surface, fill, (level_size[0]-2-border_w, 0, border_w, 3))
                    if level_right in visited:
                        if 6 in borders:
                            pygame.draw.rect(surface, fill, (level_size[0]-3, 2, 3, border_h))
                        if 7 in borders:
                            pygame.draw.rect(surface, fill, (level_size[0]-3, level_size[1]//2-border_h//2, 3, border_h))
                        if 8 in borders:
                            pygame.draw.rect(surface, fill, (level_size[0]-3, level_size[1]-2-border_h, 3, border_h))
                    if level_bottom in visited:
                        if 9 in borders:
                            pygame.draw.rect(surface, fill, (level_size[0]-2-border_w, level_size[1]-3, border_w, 3))
                        if 10 in borders:
                            pygame.draw.rect(surface, fill, (level_size[0]//2-border_w//2, level_size[1]-3, border_w, 3))
                        if 11 in borders:
                            pygame.draw.rect(surface, fill, (2, level_size[1]-3, border_w, 3))
                    cx = (pos[1]+world_data.get("xofs", 0))*level_size[0]+self.game_width//2
                    cy = (pos[2]+world_data.get("yofs", 0))*level_size[1]+self.game_height//2
                    ui.create_graphic(self, surface, cx=cx, cy=cy)
                    if tile_data.get("icon_name") and (tile_data.get("icon_hide_level") is None or \
                            tuple(tile_data["icon_hide_level"]) not in visited): # level icon
                        icon_pos = tile_data.get("icon_pos", [0, 0])
                        icon_x, icon_y = cx+icon_pos[0]*(level_size[0]//3), cy+icon_pos[1]*(level_size[1]//4)
                        level_icons.append((icon_key[tile_data["icon_name"]], icon_x, icon_y))
                        if tile_data.get("warp_target"):
                            target_pos = tuple(tile_data["warp_target"])
                            if target_pos in visited or target_pos == self.level.level_pos:
                                target_world_data = self.assets.map["data"][target_pos[0]]
                                target_cx = (target_pos[1]+target_world_data.get("xofs", 0))*level_size[0]+self.game_width//2
                                target_cy = (target_pos[2]+target_world_data.get("yofs", 0))*level_size[1]+self.game_height//2
                                target_tile_data = target_world_data.get("levels", {})\
                                                                    .get(",".join([str(n) for n in target_pos[1:]]), {})
                                target_icon_pos = target_tile_data.get("icon_pos", [0, 0])
                                teleporter_lines.append((
                                    icon_x,
                                    icon_y,
                                    target_cx+target_icon_pos[0]*(level_size[0]//3),
                                    target_cy+target_icon_pos[1]*(level_size[1]//4)
                                ))
                    if pos == self.level.level_pos: # player icon
                        level_icons.insert(0, (
                            0 if self.player.facing_right else 1,
                            cx+(self.player.x+self.player.rectw//2-self.game_width//2)/self.game_width*(level_size[0]-30),
                            cy+(self.player.y+self.player.recth//2-self.game_height//2)/self.game_height*(level_size[1]-30)
                        ))
                        idx = (self.game_width//2-cx, self.game_height//2-cy)
            for x1, y1, x2, y2 in teleporter_lines:
                surface = Assets.sized_surface(abs(x2-x1), abs(y2-y1))
                pygame.draw.line(surface, WHITE, (x1-min(x1, x2), y1-min(y1, y2)), (x2-min(x1, x2), y2-min(y1, y2)), 3)
                if Settings.enable_transparency: surface.set_alpha(64)
                line = ui.create_graphic(self, surface, cx=(x1+x2)//2, cy=(y1+y2)//2)
                line.hide_ok = True
            for num, x, y in level_icons[::-1]:
                icon = ui.create_graphic(self, self.assets.map["icons"][num], cx=x, cy=y)
                icon.hide_ok = True
            self.ui_objects[-1].hide_ok = False
            y = 24
            graphic = ui.create_graphic(self, self.assets.ui["key_icons"][1 if RASPBERRY_PI else 0],
                                        cx=24, cy=self.game_height-y)
            graphic.fixed = graphic.hide_ok = True
            text = ui.create_text(self, "Hide UI", cy=self.game_height-y)
            text.rect.left = 44
            text.fixed = text.hide_ok = True
            y += 38
            if self.crystal_count > 0: # crystal count
                graphic = ui.create_graphic(self, self.assets.ui.get("crystal_counter")[1], cx=34, cy=self.game_height-y)
                graphic.fixed = graphic.hide_ok = True
                if self.completed_time is not None: total = self.max_crystal_count
                else: total = self.crystal_requirements[self.difficulty]
                text = ui.create_text(self, f"{self.crystal_count}/{total}", cy=self.game_height-y)
                text.rect.left = 48
                text.fixed = text.hide_ok = True
                y += 38
            if self.completed_time is not None: # map completion
                graphic = ui.create_graphic(self, self.assets.ui.get("crystal_counter")[2], cx=34, cy=self.game_height-y)
                graphic.fixed = graphic.hide_ok = True
                text = ui.create_text(self, str(math.floor(visited_levels/total_levels*100))+"%", cy=self.game_height-y)
                text.rect.left = 48
                text.fixed = text.hide_ok = True
                y += 38
            scrollable = True
        elif menu == MENU_CONFIRM_RESET:
            ui.create_text(self, f"Reset slot {self.save_slot+1}?", cy=200)
            ui.create_button(self, buttons[17], (0, 0), cx=self.game_width//2-110, cy=270)
            ui.create_button(self, buttons[16], (1, 0), cx=self.game_width//2+110, cy=270)
            mx = [2, 1]
        self.selection.set(idx, mx, menu, submenu)
        self.selection.initial = idx
        if scrollable:
            self.selection.scrollable = True
            self.update_scrolling_menu()
        elif self.selection.using_mouse:
            self.update_cursor_selection()

    def launch_selection(self):
        sel = self.selection
        if sel.idx is None and not sel.scrollable: return
        button = None
        for button in self.ui_objects:
            if isinstance(button, ui.Button) and sel.idx in button.indexes:
                break
        sound = None if sel.scrollable else "select"
        reset_transition = True
        if not self.in_game and sel.menu == MENU_MAIN:
            if sel.y == 0: self.set_menu(MENU_SLOT_SELECT)
            elif sel.y == 1: self.set_menu(MENU_SETTINGS)
            elif sel.y == 2: self.set_menu(MENU_CREDITS, SUBMENU_SKIP_CREDITS)
            elif sel.y == 3:
                self.running = False
                sound = None
            elif sel.y == 4:
                webbrowser.open("https://codefizz.itch.io/glitchlands")
        elif self.in_game and sel.menu == MENU_IN_GAME:
            return
        elif sel.menu == MENU_SLOT_SELECT:
            if sel.submenu == SUBMENU_SLOT_SELECT:
                if sel.y == 0: # select slot
                    self.save_slot = sel.x if self.save_slot < 4 else sel.x+4
                    self.set_menu(sel.menu,
                        SUBMENU_SLOT_ACTION if os.path.isfile(self.get_save_file()) else SUBMENU_DIFFICULTY_SELECT
                    )
                elif sel.x in (0, 1): # back
                    self.set_menu(sel.prev_menu)
                    sound = "return"
                elif sel.x in (2, 3): # more slots
                    self.save_slot = (self.save_slot+4)%8
                    self.set_menu(sel.menu, sel.submenu, sel.idx)
            elif sel.submenu in (SUBMENU_SLOT_ACTION, SUBMENU_DIFFICULTY_SELECT):
                if sel.idx == (0, 1): # back
                    self.set_menu(sel.menu, SUBMENU_SLOT_SELECT, (self.save_slot%4, 0))
                    sound = "return"
                elif sel.submenu == SUBMENU_SLOT_ACTION: # existing save
                    if sel.idx == (0, 0): # load
                        self.should_toggle_in_game = True
                        reset_transition = False
                    elif sel.idx == (1, 0): # copy
                        self.copy_slot = self.save_slot
                        self.set_menu(sel.menu, SUBMENU_COPY_SLOT, (self.copy_slot%4, 0))
                    elif sel.idx == (1, 1): # delete
                        self.set_menu(sel.menu, SUBMENU_CONFIRM_DELETE)
                else: # start new game
                    if sel.x == 0: self.difficulty = 0 # rookie
                    elif sel.y == 0: self.difficulty = 1 # normal
                    elif GlobalSave.unlock_master: self.difficulty = 2 # master (if unlocked)
                    else: return # locked
                    self.should_toggle_in_game = True
                    reset_transition = False
            elif sel.submenu == SUBMENU_COPY_SLOT:
                if sel.y == 0:
                    if self.save_slot < 4: target = sel.x
                    else: target = sel.x+4
                    if self.copy_slot != target:
                        shutil.copy(self.get_save_file(self.copy_slot), self.get_save_file(target))
                    self.set_menu(sel.menu, SUBMENU_SLOT_SELECT, sel.idx)
                    del self.copy_slot
                elif sel.x in (0, 1): # back
                    self.set_menu(sel.menu, SUBMENU_SLOT_SELECT, sel.idx)
                    sound = "return"
                elif sel.x in (2, 3): # more slots
                    self.save_slot = (self.save_slot+4)%8
                    self.set_menu(sel.menu, sel.submenu, sel.idx)
            elif sel.submenu == SUBMENU_CONFIRM_DELETE:
                if sel.x == 1:
                    os.remove(self.get_save_file())
                    self.set_menu(sel.menu, SUBMENU_SLOT_SELECT, (self.save_slot%4, 0))
                else:
                    self.set_menu(sel.menu, SUBMENU_SLOT_SELECT, (self.save_slot%4, 0))
                    sound = "return"
        elif sel.menu == MENU_SETTINGS:
            if sel.x == 0:
                attr = self.shown_settings[sel.y]
                cls = GlobalSave if attr in GlobalSave.all else Settings
                enabled = not cls.get(attr)
                cls.set(attr, enabled)
                if attr in ("windowed", "vsync"): self.init_display()
                cls.save()
                if button is not None:
                    button.update_frames(self.assets.ui.get("switch")[1 if enabled else 2])
            elif sel.y == sel.ymax-1 or sel.y == sel.ymax-2:
                self.set_menu(sel.prev_menu)
                sound = "return"
        elif sel.menu == MENU_CREDITS:
            if sel.submenu == SUBMENU_SKIP_CREDITS and (Input.start or Input.escape):
                self.in_game = False
                self.level = None
                self.set_menu(MENU_MAIN)
                sound = "return"
        elif sel.menu == MENU_PAUSED:
            if sel.y == 0: # resume
                self.disable_pause()
                sound = None
            elif sel.y == 1: # settings
                self.set_menu(MENU_SETTINGS)
            elif sel.y == sel.ymax-1: # main menu
                self.in_game = False
                self.level = None
                self.set_menu(MENU_MAIN)
                sound = "return"
            elif sel.y == sel.ymax-2: # skip/reset (if available)
                if GlobalSave.unlock_master and self.level.level_pos[0] == 0 and all(pos[0] == 0 for pos in self.visited_levels):
                    self.disable_pause()
                    self.skip_intro()
                    sound = None
                elif GlobalSave.speedrun_mode:
                    self.set_menu(MENU_CONFIRM_RESET)
        elif sel.menu == MENU_COMPLETION:
            self.set_menu(MENU_CREDITS, SUBMENU_NO_SKIP_CREDITS)
            sound = "select"
        elif sel.menu == MENU_CONFIRM_RESET:
            if sel.x == 1:
                os.remove(self.get_save_file())
                self.disable_pause()
                self.load_music("none")
                self.init_level(begin=False)
                self.restore_checkpoint(initial=True)
                sound = None
            else:
                self.set_menu(MENU_PAUSED)
        if sound is not None:
            self.play_sound(sound)
        if reset_transition:
            self.transition = None

    def update_cursor_selection(self, just_pressed=False, touch_pos=None):
        if self.in_game and self.selection.menu == 0: return
        prev = None if self.selection.idx is None else self.selection.idx[:]
        self.selection.idx = None
        x, y = self.get_cursor_pos(touch_pos)
        for button in self.ui_objects:
            if isinstance(button, ui.Button) and len(button.indexes) > 0 and \
                button.rect.inflate(button.hit_inflate).collidepoint(x, y):
                self.selection.set(button.indexes[0])
                if isinstance(button, ui.Slider) and self.selection.mouse_pressed:
                    button.set_percent((x-button.rect.left-12)/(button.rect.width-24))
                break
        if prev != self.selection.idx and self.selection.idx != None:
            self.play_sound("hover")

    def update_objects(self, objs):
        i = 0
        while i < len(objs):
            objs[i].update()
            if objs[i].self_destruct: objs.pop(i)
            else: i += 1
    
    def update_scrolling_menu(self):
        if self.selection.menu == MENU_MAP:
            self.selection.x = min(max(self.selection.x, 100*-3), 100*15)
            self.selection.y = min(max(self.selection.y, 60*-6), 60*3)
        for obj in self.ui_objects:
            if not obj.fixed:
                obj.xofs = self.selection.x
                obj.yofs = self.selection.y

    def update(self):
        if self.should_toggle_in_game and (self.transition is None or self.transition.halfway):
            if not self.in_game:
                if self.transition is not None and self.transition.halfway:
                    self.should_toggle_in_game = False
                    self.init_level()
                else:
                    self.show_transition(num=2)
            else:
                self.should_toggle_in_game = False
                self.in_game = False
                self.level = None
                self.set_menu(self.selection.menu)

        self.prev_xscroll = self.xscroll
        Input.update(pygame.key.get_pressed())
        perf = time.perf_counter()

        if Input.any_button or Input.any_direction:
            if self.selection.idx is None and not self.selection.scrollable:
                self.selection.set((0, 0))
                if not (Input.escape or Input.start or Input.select or Input.secondary):
                    self.selection.button_pressed = True
                    self.selection.direction_time_x, self.selection.direction_time_y = perf, perf
                    self.selection.direction_delay = 0.2
                self.play_sound("hover")
            self.selection.disable_mouse()

        if self.in_game and self.selection.menu == MENU_IN_GAME:
            self.update_objects(self.glitch_zones)
            self.update_objects(self.player_attacks)
            if self.npc_dialogue.hidden:
                self.player.update_physics()
                self.player.update_animations()
            if not Settings.low_detail and self.glitch_chance >= 0 and random.randint(0, self.glitch_chance//40) == 0:
                if random.randint(0, len(self.get_block_objects())) == 0:
                    self.background.generate_glitch_image()
                else:
                    block = random.choice(self.get_block_objects())
                    if isinstance(block, objects.Block): block.generate_glitch_image()
            if self.ambience_timer is None or self.ambience_timer == 0:
                if self.ambience_timer == 0 and self.level.level_pos[0] > 0:
                    self.play_sound(f"ambience_{random.randint(1, 6)}", 0.8)
                self.ambience_timer = random.randint(10*60, 30*60)
            else:
                self.ambience_timer -= 1
            if not Settings.reduce_motion:
                self.background.update()
            self.update_objects(self.objects_collide)
            self.update_objects(self.background_deco)
            self.update_objects(self.foreground_deco)
            self.update_objects(self.particles)
            if self.xscroll != self.xscroll_target:
                if self.frame == 0: self.xscroll = self.xscroll_target
                else: self.xscroll = self.ease_to(self.xscroll, self.xscroll_target, 8)
            if not self.selection.button_pressed:
                if Input.escape or Input.start:
                    self.enable_pause()
                elif (Input.primary or Input.secondary) and self.npc_dialogue.shown:
                    if self.npc_dialogue.change_frame > 0 and self.npc_dialogue.current.crystals == 0:
                        self.npc_dialogue.advance()
                        if self.npc_dialogue.hidden:
                            self.play_sound("unpause")
                            self.player.attack_pressed = True
                        else:
                            self.play_sound("pause")
                elif Input.select and self.player.abilities.map and self.player.teleporter_warp is None:
                    self.enable_pause(MENU_MAP)
            if self.npc_dialogue.hidden:
                self.player.update_attacks()
            self.npc_dialogue.update()
            self.selection.button_pressed = any([
                Input.escape, Input.start, Input.select, Input.secondary, Input.primary and self.npc_dialogue.shown
            ])
        else:
            Input.update_hardware()
            if not Settings.reduce_motion and not self.in_game:
                self.background.update()
            for obj in self.ui_objects:
                obj.update()
            if self.selection.menu == MENU_CREDITS:
                self.selection.y -= 4 if Input.primary else 2
                if self.selection.y < -740-26*self.assets.ui.get("credits").count("\n"):
                    self.in_game = False
                    self.level = None
                    self.set_menu(MENU_MAIN)
                else:
                    self.update_scrolling_menu()
            elif self.selection.menu == MENU_MAP:
                if Input.select or Input.start:
                    if not self.selection.button_pressed:
                        self.disable_pause()
                elif Input.stick_amount > Input.joystick_deadzone:
                    amount = (8 if Input.primary else 5)/Input.joystick_radius
                    self.selection.x -= amount*math.cos(math.radians(Input.stick_angle))
                    self.selection.y += amount*math.sin(math.radians(Input.stick_angle))
                    self.update_scrolling_menu()
            if not self.selection.button_pressed:
                if Input.escape or Input.secondary:
                    if self.in_game:
                        if self.selection.menu in (MENU_PAUSED, MENU_MAP):
                            self.disable_pause()
                        else:
                            self.set_menu(self.selection.prev_menu)
                            self.play_sound("return")
                    else:
                        if self.selection.menu == MENU_MAIN:
                            if Input.escape:
                                self.running = False
                                return
                        elif self.selection.menu in (MENU_CREDITS, MENU_COMPLETION):
                            self.launch_selection()
                        elif self.selection.menu == MENU_SLOT_SELECT and self.selection.submenu != SUBMENU_SLOT_SELECT:
                            if self.selection.submenu == SUBMENU_COPY_SLOT: idx = self.selection.idx
                            else: idx = (self.save_slot%4, 0)
                            self.set_menu(MENU_SLOT_SELECT, SUBMENU_SLOT_SELECT, idx)
                            self.play_sound("return")
                        else:
                            self.set_menu(self.selection.prev_menu)
                            self.play_sound("return")
                if Input.x:
                    if self.selection.menu == MENU_SLOT_SELECT and \
                            self.selection.submenu in (SUBMENU_SLOT_SELECT, SUBMENU_COPY_SLOT):
                        self.save_slot = (self.save_slot+4)%8
                        self.set_menu(self.selection.menu, self.selection.submenu, self.selection.idx)
                        self.play_sound("select")
                    elif self.selection.menu == MENU_MAP:
                        self.selection.x, self.selection.y = self.selection.initial
                        self.update_scrolling_menu()
                if Input.primary or Input.start:
                    self.launch_selection()
            self.selection.button_pressed = Input.any_button
            if Input.any_direction and not self.selection.scrollable:
                prev_selection = self.selection.idx[:]
                prev_delay = self.selection.direction_delay
                button, indexes = None, None
                for button in self.ui_objects:
                    if isinstance(button, ui.Button) and self.selection.idx in button.indexes:
                        indexes = button.indexes
                        break
                if perf-self.selection.direction_time_x > prev_delay:
                    if Input.left:
                        if isinstance(button, ui.Slider):
                            button.increment(-1)
                            self.selection.direction_delay = 0.1
                        else:
                            self.selection.increment(-1, 0, indexes)
                            self.selection.direction_delay = 0.2
                        self.selection.direction_time_x = perf
                    if Input.right:
                        if isinstance(button, ui.Slider):
                            button.increment(1)
                            self.selection.direction_delay = 0.1
                        else:
                            self.selection.increment(1, 0, indexes)
                            self.selection.direction_delay = 0.2
                        self.selection.direction_time_x = perf
                if perf-self.selection.direction_time_y > prev_delay:
                    if Input.down:
                        self.selection.increment(0, 1, indexes)
                        self.selection.direction_time_y = perf
                        self.selection.direction_delay = 0.2
                    if Input.up:
                        self.selection.increment(0, -1, indexes)
                        self.selection.direction_time_y = perf
                        self.selection.direction_delay = 0.2
                if prev_selection != self.selection.idx: self.play_sound("hover")
            else:
                self.selection.direction_delay = 0
        if self.transition is not None:
            self.transition.update()
        MusicManager.update()

    def draw(self):
        # welcome to my very epic, complicated, and definitely optimized draw code
        # (it's actually not that bad now that fullscreen_refresh is gone)
        self.rects = []
        self.background.draw()
        if self.in_game and self.selection.menu == MENU_IN_GAME: # draw level
            for obj in self.background_deco+self.glitch_zones+self.get_block_objects():
                obj.draw()
                if Settings.show_hitboxes:
                    obj.draw_hitbox()
            self.rects.append(self.player.draw())
            if Settings.show_hitboxes:
                self.rects.append(self.player.draw_hitbox())
            for part in self.particles:
                if not Settings.low_detail or part.show_low_detail:
                    self.rects.append(part.draw())
            for atk in self.player_attacks:
                self.rects.append(atk.draw())
                if Settings.show_hitboxes:
                    self.rects.append(atk.draw_hitbox())
            for deco in self.foreground_deco:
                self.rects.append(deco.draw())
                if Settings.show_hitboxes:
                    self.rects.append(deco.draw_hitbox())
        for obj in self.ui_objects: # draw ui
            if obj.hide_ok and Input.primary:
                continue
            self.rects.append(obj.draw())

    def draw_overlays(self):
        if Settings.enable_shaders:
            if not self.in_game or self.glitch_chance <= 0 or random.randint(0, self.glitch_chance)//2 > 0:
                if self.in_game and self.selection.menu == MENU_IN_GAME:
                    cx, cy = self.game_width//2, self.player.y+self.player.recth//2
                    amount = (4000-self.glitch_chance)/250000 if self.glitch_chance > 0 else 0.008
                    if self.level.level_pos[0] == 0: cy = self.game_height//2
                else:
                    cx, cy = self.game_width//2, self.game_height//2
                    amount = 0.005
                self.screen = shader.chromatic(
                    self.screen,
                    min(max(cx, 0), self.game_width), min(max(cy, 0), self.game_height),
                    .9999, fx=amount
                )
            elif random.randint(0, 1) == 0:
                shader.tv_scan(self.screen, random.randint(5, 20))
        if self.in_game and self.selection.menu == MENU_IN_GAME:
            if self.npc_dialogue.shown and self.npc_dialogue.current.content is not None:
                container = self.assets.ui.get("dialogue_container")
                self.screen.blit(container, (
                    self.game_width//2-container.get_width()//2,
                    self.game_height-container.get_height()-8
                ))
                content = self.assets.font.render(self.npc_dialogue.current.content)
                self.screen.blit(content, (
                    self.game_width//2-content.get_width()//2,
                    self.game_height-80-content.get_height()//2-max(4-self.npc_dialogue.change_frame, 0)
                ))
                owner = self.assets.font.render(self.npc_dialogue.current.owner)
                self.screen.blit(owner, (40, self.game_height-160))
        if self.transition is not None:
            self.rects.append(self.transition.draw())
        y = 0
        overlays = []
        if Settings.show_fps:
            text = Assets.debug_font.render(str(round(self.clock.get_fps(), 2)), False, WHITE)
            overlays.append((text, (3, y+2)))
            y += 16
        if GlobalSave.speedrun_mode and self.in_game:
            text = Assets.debug_font.render(self.format_elapsed(self.get_elapsed_time()), False, WHITE)
            overlays.append((text, (3, y+2)))
            y += 16
            for split in self.splits[-5:]:
                text = Assets.debug_font.render(split[0], False, WHITE)
                overlays.append((text, (3, y+2)))
                text = Assets.debug_font.render(split[2], False, WHITE)
                overlays.append((text, (180-text.get_width()-3, y+2)))
                y += 16
        if not (self.in_game and self.selection.menu == MENU_IN_GAME) and RASPBERRY_PI:
            indicator = Assets.status_indicator()
            overlays.append((indicator, (0, y)))
            y += indicator.get_height()
        if y > 16 and self.in_game:
            shade = Assets.sized_surface(180, y)
            shade.fill((0, 0, 0, 128))
            self.rects.append(self.screen.blit(shade, (0, 0)))
        for args in overlays:
            self.rects.append(self.screen.blit(*args))

    def push_particle(self, *parts):
        self.particles.extend(parts)
    
    def push_player_attack(self, *atks):
        self.player_attacks.extend(atks)

    def push_object(self, *objs):
        for obj in objs:
            if isinstance(obj, objects.GlitchZone):
                if obj.num == 0: self.objects_collide.append(obj)
                else: self.glitch_zones.append(obj)
            elif obj.collides != COLLISION_NONE: self.objects_collide.append(obj)
            elif isinstance(obj, objects.Block): self.objects_nocollide.append(obj)
            elif obj.layer > 0: self.foreground_deco.append(obj)
            else: self.background_deco.append(obj)

    def sort_hazards(self):
        def sort(a, b):
            if a.collides in (COLLISION_HAZARD, COLLISION_SHIELDBREAK): return 1
            if b.collides in (COLLISION_HAZARD, COLLISION_SHIELDBREAK): return -1
            return 0
        self.objects_collide.sort(key=cmp_to_key(sort)) # ensure terrain collision takes priority over spikes

    def sort_layers(self):
        self.objects_collide.sort(key=lambda obj: obj.layer)

    def create_level(self, level, screen_xofs=None, hflip=False):
        if level is None: return
        if screen_xofs is None: screen_xofs = level.level_pos[1]-self.level.level_pos[1]
        for config in level.objects:
            removal_range = config.get("removal_range", (None, None))
            if removal_range[0] is not None and self.difficulty >= removal_range[0]: continue
            if removal_range[1] is not None and self.difficulty <= removal_range[1]: continue
            if hflip:
                config["x"] = self.game_width-config.get("x", 0)-config.get("xrep", 1)*32
                swapkey = {
                    OBJTYPE_BLOCK: {0: 2, 3: 5, 6: 8, 9: 10, 11: 12},
                    OBJTYPE_BEAM: {0: 2, 6: 7, 8: 9},
                    OBJTYPE_SEMISOLID: {0: 2}
                }.get(config.get("type"), {})
                if config.get("num", 0) in swapkey:
                    config["num"] = swapkey[config.get("num", 0)]
                elif config.get("num", 0) in swapkey.values():
                    config["num"] = {v: k for k, v in swapkey.items()}[config.get("num", 0)]
            obj = objects.create_object(self, level, config, screen_xofs=screen_xofs*self.game_width)
            if not obj.self_destruct:
                self.push_object(obj)
        self.sort_hazards()

    def create_levels_auto(self, clear=False, xscroll=False):
        if clear: self.delete_all_objects()
        self.create_level(self.level)
        if self.scroll_left: self.create_level(self.level_left, -1)
        elif xscroll and self.xscroll_target < 0: self.xscroll = 0
        if self.scroll_right: self.create_level(self.level_right, 1)
        elif xscroll and self.xscroll_target > 0: self.xscroll = 0

    def delete_all_objects(self):
        self.objects_collide, self.objects_nocollide = [], []
        self.background_deco, self.foreground_deco = [], []
        self.particles = []
        self.glitch_zones = []
        self.player_attacks = []
        self.ui_objects = []

    def delete_objects_from_level(self, pos):
        filt = lambda arr: list(filter(lambda obj: obj.level.level_pos != pos, arr))
        self.objects_collide = filt(self.objects_collide)
        self.objects_nocollide = filt(self.objects_nocollide)
        self.background_deco = filt(self.background_deco)
        self.foreground_deco = filt(self.foreground_deco)
        self.glitch_zones = filt(self.glitch_zones)

    def set_checkpoint(self, bypass_rookie=False, **kwargs):
        if self.level.rookie_checkpoints and self.difficulty > 0 and not bypass_rookie:
            return
        cp = Checkpoint(self.level.level_pos, facing_right=self.player.facing_right, **kwargs)
        if not cp.valid: return
        self.checkpoint = cp
        self.save_progress()
    
    def show_transition(self, level=None, num=None):
        if level is None and self.level is not None: level = self.level
        if num is None: num = level.transition
        if num == 0:
            self.transition = FullscreenOverlay(self, (0, 0, 40), color=BLACK)
        elif num == 1:
            self.transition = FullscreenOverlay(self, (0, 0, 40), color=WHITE)
        elif num == 2:
            self.transition = FullscreenOverlay(self, (20, 20, 20), color=BLACK)
        elif num == 3:
            self.transition = FullscreenOverlay(self, (20, 20, 20), color=WHITE)
        elif num == 4:
            self.transition = FullscreenOverlay(self, (0, 40, 20), color=(68, 68, 68),
                                surface=self.assets.decoration.get("virus_transition"), shake=4)
            self.play_sound("virus_scream")
        elif num == 5:
            self.transition = FullscreenOverlay(self, (10, 10, 10), color=WHITE)
        if level is not None:
            self.transition.level_pos = level.level_pos
            self.player.freeze_timer = self.transition.fade_in+self.transition.hold+1
            self.player.freeze_anim = True
    
    def show_transition_once(self, level=None):
        if level is None: level = self.level
        if level.transition is None or level.level_pos in self.visited_levels: return False
        if self.transition is None or (self.transition.halfway and self.transition.level_pos != level.level_pos):
            self.show_transition(level)
            return self.transition is not None
        return False
    
    def append_visited(self, next_pos=None, only_next=False):
        if not only_next:
            self.visited_levels.add(self.level.level_pos)
        if next_pos is not None:
            if next_pos[0] <= 0: self.assets.load_virus()
            else: self.assets.unload_virus()

    def shift_all_objects(self, amount):
        self.player.x += amount
        for obj in self.get_all_objects():
            obj.x += amount
            obj.rect.x += amount
            obj.update_hitbox()
        for part in self.particles:
            part.rect.x += amount
        for atk in self.player_attacks:
            atk.rect.x += amount
            atk.update_hitboxes()
        self.xscroll += amount
        self.xscroll_target += amount

    def warp_teleporter(self, pos):
        if pos is None: return
        if len(pos) == 3:
            self.append_visited(pos)
            self.load_level_full(pos)
            if self.show_transition_once(self.level):
                return
            self.create_levels_auto(clear=True, xscroll=True)
            self.load_music()
            target = None
            for obj in self.glitch_zones:
                if obj.num == 1:
                    target = obj
                    break
            self.background.change_to(self.level.background)
            if target is not None:
                self.player.move_hitbox(centerx=target.rect.centerx, bottom=target.rect.bottom)
                self.set_checkpoint(centerx=target.rect.centerx, bottom=target.rect.bottom)
        elif len(pos) == 2:
            self.player.move_hitbox(centerx=pos[0], bottom=pos[1])

    def warp_left(self):
        if self.level_left is None: return
        self.append_visited(self.level_left.level_pos)
        level_loaded = self.scroll_left
        if self.show_transition_once(self.level_left):
            if not level_loaded: self.player.x -= self.player.rectw
            return
        if level_loaded:
            if self.level_right is not None:
                self.delete_objects_from_level(self.level_right.level_pos)
            self.shift_all_objects(self.game_width)
        else:
            self.delete_all_objects()
            if Settings.reduce_motion: self.player.move_hitbox(right=self.game_width)
            else: self.player.move_hitbox(centerx=self.game_width-1)
        self.level_right = self.level
        self.level = self.level_left
        self.load_level_left()
        self.load_level_top()
        self.load_level_bottom()
        self.scroll_right = not Settings.reduce_motion
        if not level_loaded:
            self.create_level(self.level)
            self.scroll_right = False
        if self.scroll_left:
            self.create_level(self.level_left, -1)
        self.load_music()
        if self.background.num != self.level.background:
            self.background.change_to(self.level.background, side=-1 if level_loaded else 0)
        if self.level.checkpoint_positions[2] is not None:
            prev = self.checkpoint.get_any_pos()
            prev = (prev[0]+(self.checkpoint.level_pos[1]-self.level.level_pos[1])*self.game_width, prev[1])
            self.set_checkpoint(bottom=self.level.checkpoint_positions[2], right=self.game_width)
            if self.checkpoint.get_any_pos() != prev:
                self.player.spawn_particles_checkpoint(center=(self.game_width, self.checkpoint.bottom))
    
    def warp_right(self):
        if self.level_right is None: return
        self.append_visited(self.level_right.level_pos)
        level_loaded = self.scroll_right
        if self.show_transition_once(self.level_right):
            if not level_loaded: self.player.x += self.player.rectw
            return
        if level_loaded:
            if self.level_left is not None:
                self.delete_objects_from_level(self.level_left.level_pos)
            self.shift_all_objects(-self.game_width)
        else:
            self.delete_all_objects()
            if Settings.reduce_motion: self.player.move_hitbox(left=0)
            else: self.player.move_hitbox(centerx=1)
        self.level_left = self.level
        self.level = self.level_right
        self.load_level_right()
        self.load_level_top()
        self.load_level_bottom()
        self.scroll_left = not Settings.reduce_motion
        if not level_loaded:
            self.create_level(self.level)
            self.scroll_left = False
        if self.scroll_right:
            self.create_level(self.level_right, 1)
        self.load_music()
        if self.background.num != self.level.background:
            self.background.change_to(self.level.background, side=1 if level_loaded else 0)
        if self.level.checkpoint_positions[0] is not None:
            prev = self.checkpoint.get_any_pos()
            prev = (prev[0]+(self.checkpoint.level_pos[1]-self.level.level_pos[1])*self.game_width, prev[1])
            self.set_checkpoint(bottom=self.level.checkpoint_positions[0], left=0)
            if self.checkpoint.get_any_pos() != prev:
                self.player.spawn_particles_checkpoint(center=(0, self.checkpoint.bottom))
    
    def warp_bottom(self):
        if self.level_bottom is None:
            self.restore_checkpoint()
            return
        self.append_visited(self.level_bottom.level_pos)
        if self.show_transition_once(self.level_bottom):
            return
        self.delete_all_objects()
        self.player.move_hitbox(top=0)
        self.level_top = self.level
        self.level = self.level_bottom
        self.load_level_bottom()
        self.load_level_left()
        self.load_level_right()
        self.create_levels_auto(xscroll=True)
        self.load_music()
        self.background.change_to(self.level.background)
        if self.level.checkpoint_positions[1] is not None:
            prev = self.checkpoint.get_set_sides()
            self.set_checkpoint(centerx=self.level.checkpoint_positions[1], top=0)
            if self.checkpoint.get_set_sides() != prev:
                self.player.spawn_particles_checkpoint(center=(self.player.x+self.player.rectw//2, self.player.hitbox.height))

    def warp_top(self):
        if self.level_top is None: return
        self.append_visited(self.level_top.level_pos)
        if self.show_transition_once(self.level_top):
            return
        self.delete_all_objects()
        self.player.move_hitbox(bottom=self.game_height)
        self.level_bottom = self.level
        self.level = self.level_top
        self.load_level_top()
        self.load_level_left()
        self.load_level_right()
        self.create_levels_auto(xscroll=True)
        self.load_music()
        self.background.change_to(self.level.background)
        left_exit, right_exit = self.level.bottom_exit_left, self.level.bottom_exit_right
        if left_exit is not None and right_exit is not None:
            lr = Input.right-Input.right
            if lr > 0: left_exit = None
            elif lr < 0: right_exit = None
            elif self.player.facing_right: left_exit = None
            else: right_exit = None
        self.player.bottom_exit_target = None
        if left_exit is not None:
            if self.player.x-left_exit+self.player.rectw < self.player.rectw*3:
                self.player.bottom_exit_target = left_exit-self.player.rectw
            self.player.facing_right = False
        elif right_exit is not None:
            if right_exit-self.player.x < self.player.rectw*3:
                self.player.bottom_exit_target = right_exit
            self.player.facing_right = True
        self.player.bottom_exit_timer = 22
        self.player.yv = min(self.player.yv, -12)
        self.player.xv = 0

    def patch_background(self, rect):
        if not self.background.use_still_image:
            self.screen.blit(
                self.background.image, rect,
                (
                    rect.x+self.background.tilew-self.background.xofs, rect.y+self.background.tileh-self.background.yofs,
                    rect.w, rect.h
                )
            )
        else:
            self.screen.blit(self.background.still_image, rect, rect)


if __name__ == "__main__":
    parser = ArgumentParser(prog="Glitchlands")
    parser.add_argument("-s", "--slot", type=int, help="Automatically start with the specified slot index")
    args = parser.parse_args()
    gc = GameController()
    gc.init()
    if args.slot is not None:
        gc.save_slot = args.slot
        gc.init_level()
    gc.mainloop()
