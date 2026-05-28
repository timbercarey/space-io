"""
Mine entity - obstacle that kills ships
"""
import math
import random

from utils import Vector2
from config import Config

class Mine:
    def __init__(self, position, velocity=None, rotation_speed=None):
        """
        Args:
            position: Vector2
            velocity: Vector2 movement velocity in pixels per second
            rotation_speed: float visual spin in degrees per second
        """
        self.position = position
        self.velocity = velocity or self._random_velocity()
        self.angle = random.uniform(0, 360)
        self.rotation_speed = (
            rotation_speed
            if rotation_speed is not None
            else self._random_rotation_speed()
        )
        self.active = True
        self.size = Config.MINE_SIZE
        self.color = Config.MINE_COLOR
        self.outline_color = Config.MINE_OUTLINE_COLOR
        self.crater_color = Config.MINE_CRATER_COLOR
        self.shape_points = self._random_shape_points()
        self.craters = self._random_craters()

    def update(self, dt):
        """Move and spin the mine."""
        if not self.active:
            return

        self.position = self.position + self.velocity * dt
        self.angle = (self.angle + self.rotation_speed * dt) % 360
        self._wrap_position()

    def _wrap_position(self):
        """Wrap around screen edges, with size padding to avoid popping."""
        playfield_width = Config.playfield_width()
        playfield_height = Config.playfield_height()
        half_width = playfield_width / 2
        half_height = playfield_height / 2
        padding = self.size

        if self.position.x < -half_width - padding:
            self.position.x += playfield_width + padding * 2
        elif self.position.x > half_width + padding:
            self.position.x -= playfield_width + padding * 2

        if self.position.y < -half_height - padding:
            self.position.y += playfield_height + padding * 2
        elif self.position.y > half_height + padding:
            self.position.y -= playfield_height + padding * 2

    def _random_velocity(self):
        """Create a random drifting velocity."""
        speed = random.uniform(
            Config.MINE_FLOAT_MIN_SPEED,
            Config.MINE_FLOAT_MAX_SPEED
        )
        return Vector2.from_angle(random.uniform(0, 360)) * speed

    def _random_rotation_speed(self):
        """Create a random clockwise or counter-clockwise spin."""
        speed = random.uniform(
            Config.MINE_ROTATION_MIN_SPEED,
            Config.MINE_ROTATION_MAX_SPEED
        )
        return speed * random.choice((-1, 1))

    def _random_shape_points(self):
        """Create an uneven asteroid silhouette in local coordinates."""
        points = []
        point_count = random.randint(9, 13)

        for i in range(point_count):
            angle = (360 / point_count) * i + random.uniform(-10, 10)
            radius = self.size * random.uniform(0.72, 1.18)
            angle_rad = math.radians(angle)
            points.append(Vector2(
                math.cos(angle_rad) * radius,
                math.sin(angle_rad) * radius
            ))

        return points

    def _random_craters(self):
        """Create small local-space crater marks."""
        craters = []
        for _ in range(random.randint(2, 4)):
            angle_rad = math.radians(random.uniform(0, 360))
            distance = random.uniform(0.15, 0.52) * self.size
            craters.append({
                "offset": Vector2(
                    math.cos(angle_rad) * distance,
                    math.sin(angle_rad) * distance
                ),
                "radius": random.uniform(0.12, 0.24) * self.size
            })

        return craters
    
    def check_collision(self, ship_position, ship_size):
        """
        Check if ship collides with this mine
        
        Args:
            ship_position: Vector2
            ship_size: float (radius)
        
        Returns:
            bool: True if collision detected
        """
        if not self.active:
            return False
        
        distance = self.position.distance_to(ship_position)
        return distance < (self.size + ship_size)
