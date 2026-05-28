"""
Haptic effect definitions and parameters
"""
from enum import Enum
from config import Config

class HapticEffect(Enum):
    """Types of haptic effects"""
    NONE = 0
    TRAIL_VIBRATION = 1
    MINE_KICKBACK = 2
    SPEED_DAMPING = 3
    ASTEROID_BOUNCE = 4
    STAR_BOOST = 5

class EffectState:
    """State of a haptic effect"""
    def __init__(self, effect_type, intensity=1.0, duration=0.0):
        """
        Args:
            effect_type: HapticEffect enum
            intensity: 0.0 to 1.0
            duration: How long effect lasts (0 = continuous)
        """
        self.effect_type = effect_type
        self.intensity = intensity
        self.duration = duration
        self.timer = duration
    
    def update(self, dt):
        """Update effect timer"""
        if self.duration > 0:
            self.timer -= dt
            return self.timer > 0
        return True  # Continuous effects never expire
    
    def is_active(self):
        """Check if effect is still active"""
        if self.duration == 0:
            return True
        return self.timer > 0

class HapticEffectManager:
    """Manages active haptic effects for a player"""
    def __init__(self, player_id):
        self.player_id = player_id
        self.active_effects = []
    
    def add_effect(self, effect_type, intensity=1.0, duration=0.0):
        """Add a new effect"""
        effect = EffectState(effect_type, intensity, duration)
        self.active_effects.append(effect)
    
    def update(self, dt):
        """Update all effects, remove expired ones"""
        self.active_effects = [e for e in self.active_effects if e.update(dt)]
    
    def clear_effects_of_type(self, effect_type):
        """Remove all effects of a specific type"""
        self.active_effects = [e for e in self.active_effects 
                              if e.effect_type != effect_type]
    
    def has_effect(self, effect_type):
        """Check if an effect type is active"""
        return any(e.effect_type == effect_type for e in self.active_effects)
    
    def get_effects(self):
        """Get list of active effect types"""
        return [e.effect_type for e in self.active_effects]
    
    def clear_all(self):
        """Clear all effects"""
        self.active_effects.clear()
