"""
Abstract controller interface
"""
from abc import ABC, abstractmethod

class Controller(ABC):
    """Base class for all input controllers"""
    
    @abstractmethod
    def update(self):
        """Update controller state (read inputs)"""
        pass
    
    @abstractmethod
    def get_steering(self, player_id):
        """
        Get steering input for a player
        
        Args:
            player_id: 1 or 2
        
        Returns:
            float: -1.0 to 1.0 (left to right)
        """
        pass
    
    @abstractmethod
    def get_throttle(self, player_id):
        """
        Get throttle input for a player
        
        Args:
            player_id: 1 or 2
        
        Returns:
            float: -1.0 to 1.0 (back to forward)
        """
        pass
    
    @abstractmethod
    def close(self):
        """Cleanup resources"""
        pass