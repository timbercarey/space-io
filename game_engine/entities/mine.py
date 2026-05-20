"""
Mine entity - obstacle that kills ships
"""
from utils import Vector2
from config import Config

class Mine:
    def __init__(self, position):
        """
        Args:
            position: Vector2
        """
        self.position = position
        self.active = True
        self.size = Config.MINE_SIZE
        self.color = Config.MINE_COLOR
    
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