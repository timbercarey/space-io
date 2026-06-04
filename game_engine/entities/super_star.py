"""
Rare purple super star and its temporary rotating tail blade.
"""
import math
import random

from config import Config
from utils import Vector2


class SuperStar:
    def __init__(self, position):
        self.position = position
        self.active = True
        self.size = Config.SUPER_STAR_SIZE
        self.color = Config.SUPER_STAR_COLOR
        self.core_color = Config.SUPER_STAR_CORE_COLOR
        self.glow_color = Config.SUPER_STAR_GLOW_COLOR
        self.phase = random.uniform(0, math.tau)
        self.flicker_phase = random.uniform(0, math.tau)
        self.age = 0.0
        self.visual_size = self.size
        self.brightness = 1.0

    def update(self, dt):
        if not self.active:
            return

        self.age += dt
        breathe = math.sin(
            self.age * math.tau * Config.STAR_BREATHE_SPEED + self.phase
        )
        flicker = (
            math.sin(self.age * math.tau * Config.STAR_FLICKER_SPEED + self.flicker_phase)
            + 0.65 * math.sin(self.age * math.tau * Config.STAR_FLICKER_SPEED * 1.9 + self.phase)
        )

        self.visual_size = self.size * (1.0 + breathe * Config.STAR_BREATHE_AMOUNT * 1.25)
        self.brightness = max(
            0.7,
            min(1.35, 1.0 + flicker * Config.STAR_FLICKER_AMOUNT * 1.2)
        )

    def collect(self):
        self.active = False

    def check_collision(self, ship_position, ship_size):
        if not self.active:
            return False

        return self.position.distance_to(ship_position) < (self.size + ship_size)


class SuperBlade:
    def __init__(self, position, color, owner_player_id):
        self.position = Vector2(position.x, position.y)
        self.velocity = Vector2.from_angle(random.uniform(0, 360)) * Config.SUPER_BLADE_SPEED
        self.angle = random.uniform(0, 360)
        self.rotation_speed = Config.SUPER_BLADE_ROTATION_SPEED * random.choice((-1, 1))
        self.timer = Config.SUPER_BLADE_DURATION
        self.active = True
        self.color = color
        self.owner_player_id = owner_player_id

    def update(self, dt):
        if not self.active:
            return

        self.timer -= dt
        if self.timer <= 0.0:
            self.active = False
            return

        self.position = self.position + self.velocity * dt
        self.angle = (self.angle + self.rotation_speed * dt) % 360
        self._wrap_position()

    def blade_segments(self):
        half_length = Config.SUPER_BLADE_LENGTH / 2.0
        segment_specs = (
            (0, 1.0),
            (30, 0.62),
            (60, 0.82),
            (90, 0.48),
            (120, 0.82),
            (150, 0.62),
        )

        segments = []
        for angle_offset, length_scale in segment_specs:
            direction = Vector2.from_angle(self.angle + angle_offset)
            scaled_half_length = half_length * length_scale
            segments.append((
                self.position - direction * scaled_half_length,
                self.position + direction * scaled_half_length,
            ))
        return segments

    def is_near(self, position, distance):
        if not self.active:
            return False

        for start, end in self.blade_segments():
            if self._distance_to_segment(position, start, end) <= distance:
                return True
        return False

    def can_kill(self, player_id):
        return self.active and player_id != self.owner_player_id

    def check_collision(self, player_id, ship_position, ship_size):
        if not self.can_kill(player_id):
            return False

        hit_distance = ship_size + (Config.SUPER_BLADE_WIDTH / 2.0)
        return self.is_near(ship_position, hit_distance)

    def _wrap_position(self):
        playfield_width = Config.playfield_width()
        playfield_height = Config.playfield_height()
        half_width = playfield_width / 2
        half_height = playfield_height / 2
        padding = Config.SUPER_BLADE_LENGTH / 2

        if self.position.x < -half_width - padding:
            self.position.x += playfield_width + padding * 2
        elif self.position.x > half_width + padding:
            self.position.x -= playfield_width + padding * 2

        if self.position.y < -half_height - padding:
            self.position.y += playfield_height + padding * 2
        elif self.position.y > half_height + padding:
            self.position.y -= playfield_height + padding * 2

    def _distance_to_segment(self, point, start, end):
        segment = end - start
        segment_length_squared = segment.length_squared()
        if segment_length_squared == 0.0:
            return point.distance_to(start)

        t = (point - start).dot(segment) / segment_length_squared
        t = max(0.0, min(1.0, t))
        closest = start + segment * t
        return point.distance_to(closest)
