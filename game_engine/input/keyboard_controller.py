"""
Keyboard controller for simulation mode
"""
import pygame
from .controller import Controller
from config import Config

class KeyboardController(Controller):
    def __init__(self):
        """Initialize keyboard controller"""
        self.steering = {1: 0.0, 2: 0.0}
        self.throttle = {1: 0.0, 2: 0.0}
    
    def update(self):
        """Read keyboard state and update inputs"""
        keys = pygame.key.get_pressed()
        
        # Player 1 controls
        p1_steer = 0.0
        if keys[pygame.K_a]:
            p1_steer -= 1.0
        if keys[pygame.K_d]:
            p1_steer += 1.0
        self.steering[1] = p1_steer
        
        p1_throttle = 0.0
        if keys[pygame.K_w]:
            p1_throttle += 1.0
        if keys[pygame.K_s]:
            p1_throttle -= 1.0
        self.throttle[1] = p1_throttle
        
        # Player 2 controls
        p2_steer = 0.0
        if keys[pygame.K_LEFT]:
            p2_steer -= 1.0
        if keys[pygame.K_RIGHT]:
            p2_steer += 1.0
        self.steering[2] = p2_steer
        
        p2_throttle = 0.0
        if keys[pygame.K_UP]:
            p2_throttle += 1.0
        if keys[pygame.K_DOWN]:
            p2_throttle -= 1.0
        self.throttle[2] = p2_throttle
    
    def get_steering(self, player_id):
        """Get steering input for player"""
        return self.steering.get(player_id, 0.0)
    
    def get_throttle(self, player_id):
        """Get throttle input for player"""
        return self.throttle.get(player_id, 0.0)
    
    def close(self):
        """No cleanup needed for keyboard"""
        pass