"""
Star entity - collectible boost pickup
"""
from utils import Vector2
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