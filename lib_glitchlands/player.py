import math, random, copy
import pygame

from lib import*
from lib_glitchlands import*
from lib_glitchlands import particles

class Progression:
    def __init__(self):
        self.all = [
            "jump",
            "double_jump",
            "speed_boost",
            "red_glitch",
            "green_glitch",
            "blue_glitch",
            "map",
            "lightbeam",
        ]
        self.jump = True # start with some abilities enabled in world 0
        self.double_jump = True
        self.speed_boost = True
        self.red_glitch = False
        self.green_glitch = False
        self.blue_glitch = False
        self.map = False
        self.lightbeam = False
    def __repr__(self):
        return f"<Progression({self.to_json()})>"
    def get(self, key):
        return getattr(self, key)
    def set(self, key, value):
        setattr(self, key, value)
    def enable(self, key):
        self.set(key, True)
    def set_all(self, val):
        for k in self.all:
            setattr(self, k, val)
    def to_json(self):
        return {k: self.get(k) for k in self.all}
    def load_json(self, json_data):
        for k in self.all:
            self.set(k, json_data.get(k, False))

class Physics:
    def __init__(self):
        self.speed = None
        self.speed_boost_speed = None
        self.jump_power = None
        self.double_jump_power = None
        self.speed_gap = 6.4
        self.speed_boost_gap = 8.3
        self.jump_height = 5.3
        self.double_jump_height = 3.3
        self.speed_decay = .8
        self.gravity = 1.1
        self.gravity_hold_multiplier = -.3
        self.gravity_fall_multiplier = 3
        self.max_jump_buffer = 6
        self.coyote_ticks = 3
        self.terminal_velocity_multiplier = 30
    def copy(self):
        return copy.copy(self)
    def height_to_jump_power(self, height, gt):
        if self.gravity == 0: return 0
        return (gt+math.sqrt(-8*height*-32*gt))/(2*self.gravity)
    def gap_to_speed(self, gap, hland):
        dist = gap*32-(64-13*2+2)
        return dist*(1-self.speed_decay)/(self.speed_decay*math.floor(hland))
    def calculate(self, adjust_jump=True, adjust_speed=True):
        gt = abs(self.gravity+self.gravity*self.gravity_hold_multiplier)
        if adjust_jump or self.jump_power is None:
            self.jump_power = self.height_to_jump_power(self.jump_height, gt)
            self.double_jump_power = self.height_to_jump_power(self.double_jump_height, gt)
        if adjust_speed or self.speed is None:
            hland = -2+2*self.jump_power*self.gravity/gt
            self.speed = self.gap_to_speed(self.speed_gap, hland)
            self.speed_boost_speed = self.gap_to_speed(self.speed_boost_gap, hland)
    def apply_mod(self, config):
        adjust_jump = False
        adjust_speed = False
        if "gravity" in config:
            self.gravity *= config["gravity"]
            adjust_jump = True
        if "jump_height" in config:
            self.jump_height = config["jump_height"]
            adjust_jump = True
        if "double_jump_height" in config:
            self.double_jump_height = config["double_jump_height"]
            adjust_jump = True
        if "speed_decay" in config:
            self.speed_decay = config["speed_decay"]
        if "speed" in config:
            self.speed_gap *= config["speed"]
            self.speed_boost_gap *= config["speed"]
            adjust_speed = True
        self.calculate(adjust_jump=adjust_jump, adjust_speed=adjust_speed)

class Player(pygame.sprite.Sprite):
    def __init__(self, gc):
        super().__init__()
        self.gc = gc
        self.abilities = Progression()
        self.facing_right = True
        self.reset()

    def reset(self):
        self.x, self.y = 64*2, self.gc.game_height-64*2
        self.xv, self.yv = 0, 0
        self.rectw, self.recth = 64, 64
        self.default_physics = Physics()
        self.default_physics.calculate()
        self.physics = self.default_physics.copy()
        self.physics_id = None
        self.fall_frame = 9999
        self.jump_count = 0
        self.upside_down = False
        self.anim = "idle"
        self.anim_delay = 0
        self.anim_frame = 0
        self.jump_buffer = 0
        self.freeze_timer = 0
        self.freeze_anim = False
        self.bottom_exit_timer = 0
        self.bottom_exit_target = None
        self.teleporter_warp = None
        self.fast_teleport = False
        self.attack_cooldown = 0
        self.attack_pressed = False
        self.hurt_timer = 0
    
    def death(self):
        self.freeze_timer = 15
        self.anim = "death"
        self.anim_delay = 4
        self.anim_frame = 0
        self.y += -14 if self.upside_down else 14
        self.gc.death_count += 1
        self.gc.play_sound("death")
    
    def shieldbreak(self):
        if self.hurt_timer > 0: return
        return self.death()
        if self.health > 1:
            self.gc.push_particle(
                particles.ShieldBreakParticle(self.gc, self.hitbox.center, not self.facing_right, 0),
                particles.ShieldBreakParticle(self.gc, self.hitbox.center, not self.facing_right, 1),
                particles.ShieldBreakParticle(self.gc, self.hitbox.center, not self.facing_right, 2)
            )
            self.health -= 1
            self.hurt_timer = 60
            self.gc.play_sound("shieldbreak")
        else:
            self.death()
    
    def revive(self):
        self.freeze_timer = 10
        self.anim = "revive"
        self.anim_delay = 3
        self.anim_frame = 0
    
    def upgrade_collect(self):
        self.freeze_timer = -1
        self.anim = "idle"
        self.anim_frame = 0
        self.freeze_anim = True
        self.xv, self.yv = 0, 0

    def talk_npc(self):
        self.anim = "idle"
        self.xv, self.yv = 0, 0
    
    def teleport_in(self):
        self.fast_teleport = len(self.teleporter_warp) == 2
        self.gc.show_transition(num=5 if self.fast_teleport else 3)
        self.freeze_timer = 10 if self.fast_teleport else 20
        self.freeze_anim = False
        self.anim = "teleport_in"
        self.anim_delay = 3
        self.anim_frame = 0
        self.xv, self.yv = 0, 0
        self.attack_pressed = True
        self.gc.play_sound("teleport")
    
    def equip_shield(self):
        self.gc.push_particle(
            particles.ShieldEquipParticle(self.gc, self.hitbox.center, False),
            particles.ShieldEquipParticle(self.gc, self.hitbox.center, True)
        )
        self.freeze_timer = 18
        self.freeze_anim = True

    def update_hitbox(self):
        self.hitbox = pygame.Rect(round(self.x+13), round(self.y+16), round(self.rectw-13*2), round(self.recth-16))
        if self.upside_down: self.hitbox.y -= 16
    
    def move_hitbox(self, left=None, right=None, top=None, bottom=None, centerx=None, centery=None):
        if left is not None: self.x = left-13
        elif right is not None: self.x = right+13-self.rectw
        elif centerx is not None: self.x = centerx-self.rectw/2
        if top is not None: self.y = top-(0 if self.upside_down else 16)
        elif bottom is not None: self.y = bottom-self.recth+(16 if self.upside_down else 0)
        elif centery is not None: self.y = centery-self.recth/2+(8 if self.upside_down else -8)

    def get_particle_colors(self):
        colors = []
        if self.abilities.red_glitch: colors.append(("circle_red", "square_red"))
        if self.abilities.green_glitch: colors.append(("circle_green", "square_green"))
        if self.abilities.blue_glitch: colors.append(("circle_blue", "square_blue"))
        return colors
    
    def spawn_particles_land(self):
        y = self.hitbox.top+4 if self.upside_down else self.hitbox.bottom-4
        particles.ParticleSpawner(
            self.gc, self.get_particle_colors(),
            [
                {"center": (self.hitbox.centerx-8, y), "xv": -6, "yv": -1.5},
                {"center": (self.hitbox.centerx+8, y), "xv": 6, "yv": -1.5},
            ],
            class_=particles.FadeOutParticle, vflip=self.upside_down
        ).spawn()
    
    def spawn_particles_skid(self):
        side = 1 if self.facing_right else -1
        y = self.hitbox.top+4 if self.upside_down else self.hitbox.bottom-4
        particles.ParticleSpawner(
            self.gc, self.get_particle_colors(),
            [
                {"center": (self.hitbox.centerx-8*side, y), "xv": -7*side, "yv": -2},
            ],
            class_=particles.FadeOutParticle, dirofs=30, vflip=self.upside_down
        ).spawn()

    def collide_bottom(self, y):
        self.move_hitbox(bottom=y)
        if not self.upside_down:
            self.yv = 0
            self.fall_frame = 0
            self.jump_count = 0
        else:
            self.yv *= -.1
        self.update_hitbox()
    
    def collide_top(self, y):
        self.move_hitbox(top=y)
        if not self.upside_down:
            self.yv *= -.1
        else:
            self.yv = 0
            self.fall_frame = 0
            self.jump_count = 0
        self.update_hitbox()

    def collide_left(self, x):
        self.move_hitbox(left=x)
        self.update_hitbox()
        self.xv = 0
        self.skid = False
        
    def collide_right(self, x):
        self.move_hitbox(right=x)
        self.update_hitbox()
        self.xv = 0
        self.skid = False

    def update_physics(self):
        if self.freeze_timer != 0:
            self.update_camera()
            return
        if self.hurt_timer > 0:
            self.hurt_timer -= 1
        if self.bottom_exit_timer > 0:
            self.bottom_exit_timer -= 1
            if self.bottom_exit_timer == 0:
                self.bottom_exit_target = None
        self.update_glitch_zone_collisions()
        self.skid = False
        if self.bottom_exit_target is None:
            lr = Input.right-Input.left
            if lr > 0:
                self.skid = self.xv <= 0 and self.fall_frame == 0
                self.xv += self.physics.speed_boost_speed if self.abilities.speed_boost else self.physics.speed
                if not self.facing_right:
                    self.facing_right = True
                    self.anim_frame = 0
            elif lr < 0:
                self.skid = self.xv >= 0 and self.fall_frame == 0
                self.xv -= self.physics.speed_boost_speed if self.abilities.speed_boost else self.physics.speed
                if self.facing_right:
                    self.facing_right = False
                    self.anim_frame = 0
            if (Input.primary or Input.up) and self.abilities.jump:
                self.jump_buffer += 1
                if (self.fall_frame < self.physics.coyote_ticks and self.jump_count == 0) or \
                    (self.fall_frame >= self.physics.coyote_ticks and self.jump_count > 0):
                    if 0 < self.jump_buffer < self.physics.max_jump_buffer and \
                            self.jump_count < (2 if self.abilities.double_jump else 1):
                        power = self.physics.double_jump_power if self.jump_count > 0 else self.physics.jump_power
                        self.yv = self.physics.gravity*power*(1 if self.upside_down else -1)
                        self.jump_buffer = 9999
                        self.jump_count += 1
                        self.gc.play_sound("jump")
                if (not self.upside_down and self.yv < 0) or (self.upside_down and self.yv > 0):
                    self.yv += self.physics.gravity*self.physics.gravity_hold_multiplier
            else:
                self.jump_buffer = 0
                if (not self.upside_down and self.yv < 0) or (self.upside_down and self.yv > 0):
                    self.yv += self.physics.gravity*self.physics.gravity_fall_multiplier
        else:
            diff = self.bottom_exit_target-self.x
            if self.facing_right:
                if diff > 0:
                    vel = min(diff, self.physics.speed_boost_speed)
                    if diff > self.rectw*2: vel *= 2
                    self.xv += vel
                else: self.xv *= .1
            else:
                if diff < 0:
                    vel = max(diff, -self.physics.speed_boost_speed)
                    if diff < -self.rectw*2: vel *= 2
                    self.xv += vel
                else: self.xv *= .1
            if self.yv < 0:
                self.yv += self.physics.gravity*self.physics.gravity_hold_multiplier
        self.xv *= self.physics.speed_decay
        if abs(self.xv) < self.physics.speed*self.physics.speed_decay: self.xv = 0
        self.yv += self.physics.gravity
        if (not self.upside_down and self.yv > self.physics.gravity*self.physics.terminal_velocity_multiplier) or \
            (self.upside_down and self.yv < self.physics.gravity*self.physics.terminal_velocity_multiplier):
            self.yv = self.physics.gravity*self.physics.terminal_velocity_multiplier
        self.x += self.xv
        self.update_horizontal_collisions(self.xv)
        if self.freeze_timer != 0: return
        self.y += self.yv
        self.update_vertical_collisions(self.yv)
        if self.freeze_timer != 0: return
        self.update_camera(absolute=self.gc.frame == 0)
        if self.skid: self.spawn_particles_skid()
    
    def update_camera(self, absolute=False):
        scroll_left = self.hitbox.left <= self.gc.scroll_bounds+self.gc.xscroll_target or absolute
        scroll_right = self.hitbox.right >= self.gc.game_width-self.gc.scroll_bounds+self.gc.xscroll_target or absolute
        if scroll_left and scroll_right:
            if self.facing_right: scroll_left = False
            else: scroll_right = False
        if scroll_left:
            self.gc.xscroll_target = self.hitbox.left-self.gc.scroll_bounds
        if scroll_right:
            self.gc.xscroll_target = self.hitbox.right-self.gc.game_width+self.gc.scroll_bounds
        if not self.gc.scroll_left: self.gc.xscroll_target = max(self.gc.xscroll_target, 0)
        if not self.gc.scroll_right: self.gc.xscroll_target = min(self.gc.xscroll_target, 0)

    def update_glitch_zone_collisions(self):
        self.update_hitbox()
        warp = None
        physics = None
        physics_id = None
        for i, zone in enumerate(self.gc.glitch_zones):
            if not zone.collides_horizontal(self): continue
            if zone.num == 1:
                if warp is None and zone.warp is not None and Input.secondary and not self.gc.selection.button_pressed:
                    warp = zone.warp
                    zone.pre_warp(self)
            elif zone.num == 2:
                if physics is None and zone.physics is not None and len(zone.physics) > 0:
                    physics = zone.physics
                    physics_id = hash((i, *self.gc.level.level_pos))
        if warp is not None:
            self.teleporter_warp = tuple(warp)
            self.teleport_in()
        if physics_id != self.physics_id:
            self.physics = self.default_physics.copy()
            if physics is not None:
                self.physics.apply_mod(physics)
                self.physics_id = physics_id
            else:
                self.physics_id = None
            if self.physics.gravity > 0 and self.upside_down:
                self.upside_down = False
                self.y -= 16
            elif self.physics.gravity < 0 and not self.upside_down:
                self.upside_down = True
                self.y += 16

    def update_horizontal_collisions(self, dx):
        self.update_hitbox()

        if self.hitbox.left < 0 and self.gc.level_left is None: # left bounds
            self.collide_left(0)
            return
        if self.hitbox.right > self.gc.game_width and self.gc.level_right is None: # right bounds
            self.collide_right(self.gc.game_width)
            return

        if self.hitbox.centerx < 0: # warp left
            self.gc.warp_left()
            self.update_hitbox()
        elif self.hitbox.centerx > self.gc.game_width: # warp right
            self.gc.warp_right()
            self.update_hitbox()
        
        for obj in self.gc.objects_collide:
            if not obj.collides_horizontal(self, dx): continue
            if obj.collides == COLLISION_HAZARD:
                self.death()
                break
            if obj.collides == COLLISION_SHIELDBREAK:
                self.shieldbreak()
            elif obj.collides == COLLISION_BLOCK:
                if dx < 0: self.collide_left(obj.hitbox.right)
                elif dx > 0: self.collide_right(obj.hitbox.left)

    def update_vertical_collisions(self, dy):
        self.fall_frame += 1
        self.update_hitbox()
        
        if self.y+self.recth < 0: # warp up
            self.gc.warp_top()
            self.update_hitbox()
        elif self.y > self.gc.game_height: # warp down
            self.gc.warp_bottom()
            self.update_hitbox()
        
        land = False
        for obj in self.gc.objects_collide:
            if not obj.collides_vertical(self, dy): continue
            if obj.collides == COLLISION_HAZARD:
                # if self.health <= 1 and self.hurt_timer == 0:
                if dy < 0: self.collide_top(obj.hitbox.bottom)
                elif dy > 0: self.collide_bottom(obj.hitbox.top)
                self.death()
                land = False
                break
            if obj.collides == COLLISION_SHIELDBREAK:
                self.shieldbreak()
            elif obj.collides == COLLISION_BLOCK:
                if dy < 0: self.collide_top(obj.hitbox.bottom)
                elif dy > 0: self.collide_bottom(obj.hitbox.top)
                if (not self.upside_down and dy > self.physics.gravity*8) or \
                    (self.upside_down and dy < self.physics.gravity*8):
                    land = True
        if land:
            self.gc.play_sound("land")
            self.spawn_particles_land()
        if self.fall_frame >= self.physics.coyote_ticks:
            self.jump_count = max(self.jump_count, 1)
        
    def update_attacks(self):
        if self.freeze_timer != 0: return
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        elif not self.attack_pressed:
            if Input.secondary and self.abilities.lightbeam:
                self.attack_pressed = True
                self.attack_cooldown = 20
                self.gc.push_player_attack(Lightbeam(self))
                self.gc.play_sound("lightbeam")
        if not Input.secondary:
            self.attack_pressed = False
        
    def update_animations(self):
        if self.freeze_timer == 0:
            self.anim = None
            self.anim_delay = 4
            if not self.upside_down:
                if self.yv > self.physics.gravity*2: self.anim = "fall"
                elif self.yv < -self.physics.gravity*2 or self.fall_frame > 4:
                    self.anim = "double_jump" if self.jump_count > 1 else "jump"
            else:
                if self.yv < self.physics.gravity*2: self.anim = "fall"
                elif self.yv > -self.physics.gravity*2 or self.fall_frame > 4:
                    self.anim = "double_jump" if self.jump_count > 1 else "jump"
            if self.anim is None:
                if self.xv != 0:
                    if self.abilities.speed_boost: self.anim_delay = 3
                    self.anim = "walk"
                elif Input.down:
                    self.anim = "crouch"
                    self.anim_frame = 0
                else: self.anim = "idle"
        else:
            self.freeze_timer -= 1
            if self.anim == "death":
                self.y += -1 if self.upside_down else 1
                if self.freeze_timer == 0:
                    self.gc.restore_checkpoint()
                    return
            elif self.anim == "teleport_in":
                if self.freeze_timer == 0:
                    self.anim = "teleport_out"
                    self.freeze_anim = True
                    self.freeze_timer = 20 if self.fast_teleport else 40
            elif self.anim == "teleport_out":
                if self.freeze_timer == (10 if self.fast_teleport else 20):
                    self.gc.warp_teleporter(self.teleporter_warp)
                    self.update_camera(absolute=True)
                    self.gc.xscroll = self.gc.xscroll_target
                    self.teleporter_warp = None
                    self.fall_frame = 9999
                    self.freeze_anim = False
            if self.freeze_timer == 0 and self.freeze_anim:
                self.freeze_anim = False
        if not self.freeze_anim:
            self.anim_frame += 1
    
    def draw_hitbox(self):
        self.update_hitbox()
        return pygame.draw.rect(self.gc.screen, CYAN, (self.hitbox.x-self.gc.xscroll, self.hitbox.y, self.hitbox.w, self.hitbox.h), 1)
        
    def draw(self):
        sheet = self.gc.assets.player[self.anim]
        im = sheet.get(
            (self.anim_frame//self.anim_delay)%sheet.width,
            hflip=not self.facing_right, vflip=self.upside_down
        ).copy()
        if self.freeze_timer != 0:
            if self.anim == "death": im.set_alpha(self.freeze_timer/15*255)
            elif self.anim == "revive": im.set_alpha((1-self.freeze_timer/7)*255)
            elif self.anim == "teleport_in": im.set_alpha(self.freeze_timer/(10 if self.fast_teleport else 20)*255)
            elif self.anim == "teleport_out": im.set_alpha((1-self.freeze_timer/(10 if self.fast_teleport else 20))*255)
        if self.hurt_timer > 52:
            amount = (self.hurt_timer-52)/8*128
            im.fill((amount, amount, amount, 0), special_flags=pygame.BLEND_RGBA_ADD)
        return self.gc.screen.blit(im, (self.x-self.gc.xscroll, self.y))


class PlayerAttack:
    def __init__(self, player):
        self.gc = player.gc
        self.player = player
        self.facing_right = player.facing_right
        self.rect = None
        self.self_destruct = False
        self.frame = 0
    def update_hitboxes(self):
        self.hitboxes = []
    def spawn_explode_particles(self, center=None):
        particles.ParticleSpawner(
            self.gc, ("circle_white",),
            [
                {"center": self.rect.center if center is None else center, "xv": 8, "yv": 0, "fade_time": 0, "size_change": -0.05}
            ],
            class_=particles.FadeOutParticle, dirofs=360, count=20
        ).spawn()
    def update(self):
        pass
    def kill_if_offscreen(self):
        if self.rect.right-self.gc.xscroll < 0 or self.rect.left-self.gc.xscroll > self.gc.game_width or \
            self.rect.bottom < 0 or self.rect.top > self.gc.game_height:
            self.self_destruct = True
    def blit_rect(self, rect, color, width=0, xofs=0, yofs=0):
        return pygame.draw.rect(self.gc.screen, color, (rect.x-self.gc.xscroll+xofs, rect.y+yofs, rect.w, rect.h), width)
    def blit_image(self, im, rect, xofs=0, yofs=0, area=None):
        return self.gc.screen.blit(im, (rect.x-self.gc.xscroll+xofs, rect.y+yofs), area)
    def draw_hitbox(self):
        if len(self.hitboxes) == 0: return
        rect = self.hitboxes[0]
        for hitbox in self.hitboxes:
            rect.union_ip(self.blit_rect(hitbox, YELLOW, 1))
        return rect
    def draw(self):
        pass


class Lightbeam(PlayerAttack):
    def __init__(self, player):
        super().__init__(player)
        self.rect = pygame.Rect(player.x+player.rectw-10, player.hitbox.y+24, 128, 2)
        if not self.facing_right: self.rect.right = player.x+10
        self.update_hitboxes()
    def update_hitboxes(self):
        self.hitboxes = [pygame.Rect(self.rect.x, self.rect.centery-4, self.rect.w, 8)]
    def spawn_trail_particles(self):
        side = 1 if self.facing_right else -1
        particles.ParticleSpawner(
            self.gc, ("square_white",),
            [
                {"center": (self.rect.left if self.facing_right else self.rect.right, self.rect.centery), 
                 "xv": -7*side, "yv": 0, "fade_time": 0, "size_change": -0.05}
            ],
            class_=particles.FadeOutParticle, dirofs=15, count=random.choice((1, 2, 2, 3))
        ).spawn()
    def update(self):
        self.frame += 1
        for obj in self.gc.objects_collide:
            ok = True
            for hitbox in self.hitboxes:
                if not obj.collides_attack(self, hitbox):
                    ok = False
                    break
            if not ok: continue
            obj.self_destruct = True
            self.spawn_explode_particles(obj.hitbox.center)
        self.rect.w += 64
        if self.facing_right: self.rect.x += 96
        else: self.rect.x -= 96+64
        if self.rect.h < 16:
            self.rect.y -= 1
            self.rect.h += 2
        self.update_hitboxes()
        self.spawn_trail_particles()
        self.kill_if_offscreen()
    def draw(self):
        return self.blit_rect(self.rect, WHITE)
