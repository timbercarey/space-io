"""
Star entity - collectible boost pickup
"""
import math
import random

from config import Config

class Star:
    def __init__(self, position):
        """
        Args:
            position: Vector2
        """
        self.position = position
        self.active = True
        self.size = Config.STAR_SIZE
        self.color = Config.STAR_COLOR
        self.core_color = Config.STAR_CORE_COLOR
        self.glow_color = Config.STAR_GLOW_COLOR
        self.phase = random.uniform(0, math.tau)
        self.flicker_phase = random.uniform(0, math.tau)
        self.age = 0.0
        self.visual_size = self.size
        self.brightness = 1.0

    def update(self, dt):
        """Animate subtle twinkle, flicker, and breathing size."""
        if not self.active:
            return

        self.age += dt
        breathe = math.sin(
            self.age * math.tau * Config.STAR_BREATHE_SPEED + self.phase
        )
        flicker = (
            math.sin(self.age * math.tau * Config.STAR_FLICKER_SPEED + self.flicker_phase)
            + 0.45 * math.sin(self.age * math.tau * Config.STAR_FLICKER_SPEED * 1.7 + self.phase)
        )

        self.visual_size = self.size * (1.0 + breathe * Config.STAR_BREATHE_AMOUNT)
        self.brightness = max(
            0.65,
            min(1.25, 1.0 + flicker * Config.STAR_FLICKER_AMOUNT)
        )
    
    def collect(self):
        """Mark star as collected"""
        self.active = False
    
    def check_collision(self, ship_position, ship_size):
        """
        Check if ship collides with this star
        
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
