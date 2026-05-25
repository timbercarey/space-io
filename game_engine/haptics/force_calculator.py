"""
Calculate haptic forces based on game state
"""
import math
from config import Config
from .effects import HapticEffect, HapticEffectManager

class ForceCalculator:
    """Calculates haptic forces for motors"""
    
    def __init__(self):
        # Effect managers for each player
        self.effect_managers = {
            1: HapticEffectManager(1),
            2: HapticEffectManager(2)
        }
        
        # Timers for time-based effects
        self.vibration_phase = {1: 0.0, 2: 0.0}
    
    def update(self, dt):
        """Update effect timers"""
        for manager in self.effect_managers.values():
            manager.update(dt)
        
        # Update vibration phase for oscillation
        for player_id in self.vibration_phase:
            self.vibration_phase[player_id] += dt
    
    def calculate_forces(self, game_state, player_id, controller=None):
        """
        Calculate steering and throttle forces for a player
        
        Args:
            game_state: Current game state
            player_id: 1 or 2
            controller: Controller instance for reading current axis positions (optional)
        
        Returns:
            tuple: (steering_force, throttle_force) in range -1000 to 1000
        """
        if player_id not in game_state.ships:
            return (0.0, 0.0)
        
        ship = game_state.ships[player_id]
        
        if not ship.alive:
            return (0.0, 0.0)
        
        manager = self.effect_managers[player_id]
        
        # Start with base forces
        steering_force = 0.0
        throttle_force = 0.0
        
        # 1. Passive centering springs (always active when controller position is available)
        if controller:
            steering_position = controller.get_steering(player_id)
            throttle_position = controller.get_throttle(player_id)

            steering_force += self._calculate_centering_spring(
                steering_position,
                Config.STEERING_CENTERING_STIFFNESS
            )
            throttle_force += self._calculate_centering_spring(
                throttle_position,
                Config.THROTTLE_CENTERING_STIFFNESS
            )
            steering_force += self._calculate_virtual_wall(
                steering_position,
                Config.STEERING_MOTION_RANGE_DEG
            )
            throttle_forward_extension = 0.0
            if ship.boost_active:
                throttle_forward_extension = Config.BOOST_THROTTLE_FORWARD_EXTENSION_DEG

            throttle_force += self._calculate_virtual_wall(
                throttle_position,
                Config.THROTTLE_MOTION_RANGE_DEG,
                forward_extension_deg=throttle_forward_extension
            )

        # 2. Speed-dependent damping (always active)
        steering_damping = self._calculate_speed_damping(ship)
        steering_force += steering_damping

        # 3. Log-modeled throttle damping (always active)
        throttle_damping = self._calculate_throttle_damping(ship)
        throttle_force += throttle_damping
        
        # 4. Trail vibration
        if manager.has_effect(HapticEffect.TRAIL_VIBRATION):
            vibration = self._calculate_trail_vibration(player_id)
            steering_force += vibration
        
        # 5. Mine kickback
        if manager.has_effect(HapticEffect.MINE_KICKBACK):
            kickback = self._calculate_mine_kickback()
            throttle_force += kickback
        
        # Clamp forces to valid range
        steering_force = max(-1000, min(1000, steering_force))
        throttle_force = max(-1000, min(1000, throttle_force))
        
        return (steering_force, throttle_force)

    def _calculate_centering_spring(self, position, stiffness):
        """
        Calculate passive spring force toward zero position.

        Args:
            position: Normalized axis position (-1.0 to 1.0)
            stiffness: Force per normalized position unit

        Returns:
            float: Restoring force
        """
        position = max(-1.0, min(1.0, position))
        return -position * stiffness

    def _calculate_virtual_wall(self, position, motion_range_deg, forward_extension_deg=0.0):
        """
        Calculate a centered virtual wall for an axis.

        Args:
            position: Normalized axis position where +/-1 is CONTROL_ROTATION_RANGE rotations
            motion_range_deg: Total allowed centered motion in degrees
            forward_extension_deg: Extra positive-side motion in degrees

        Returns:
            float: Restoring force when outside the allowed range
        """
        rear_limit_deg = motion_range_deg / 2.0
        forward_limit_deg = (motion_range_deg / 2.0) + forward_extension_deg
        rear_limit = rear_limit_deg / (360.0 * Config.CONTROL_ROTATION_RANGE)
        forward_limit = forward_limit_deg / (360.0 * Config.CONTROL_ROTATION_RANGE)

        if position > forward_limit:
            return -(position - forward_limit) * Config.VIRTUAL_WALL_STIFFNESS
        if position < -rear_limit:
            return -(position + rear_limit) * Config.VIRTUAL_WALL_STIFFNESS

        return 0.0
     
    def _calculate_speed_damping(self, ship):
        """
        Calculate speed-dependent damping for steering
        Higher speed = more damping (harder to turn)
        
        Returns:
            float: Damping force (0 to MAX_DAMPING)
        """
        speed = ship.velocity.length()
        
        # No damping below threshold
        if speed < Config.DAMPING_SPEED_THRESHOLD * 0.3:
            return 0.0
        
        # Linear interpolation from MIN to MAX damping
        damping_ratio = (speed - Config.DAMPING_SPEED_THRESHOLD * 0.3) / (Config.DAMPING_SPEED_THRESHOLD * 0.7)
        damping_ratio = max(0.0, min(1.0, damping_ratio))
        
        damping = Config.MIN_DAMPING + (Config.MAX_DAMPING - Config.MIN_DAMPING) * damping_ratio
        
        return damping

    def _calculate_throttle_damping(self, ship):
        """
        Calculate always-on throttle damping.
        Higher speed increases resistance logarithmically, with a light preload at rest.

        Returns:
            float: Negative damping force (-MAX_THROTTLE_DAMPING to 0)
        """
        speed = ship.velocity.length()
        speed_ratio = max(0.0, min(1.0, speed / Config.MAX_SPEED))

        log_gain = max(0.0, Config.THROTTLE_DAMPING_LOG_GAIN)
        if log_gain == 0.0:
            damping_ratio = speed_ratio
        else:
            damping_ratio = math.log1p(log_gain * speed_ratio) / math.log1p(log_gain)

        damping = (
            Config.MIN_THROTTLE_DAMPING
            + (Config.MAX_THROTTLE_DAMPING - Config.MIN_THROTTLE_DAMPING) * damping_ratio
        )

        return -damping
    
    def _calculate_trail_vibration(self, player_id):
        """
        Calculate vibration force from hitting trail
        
        Returns:
            float: Oscillating force
        """
        phase = self.vibration_phase[player_id]
        frequency = Config.TRAIL_VIBRATION_FREQ
        amplitude = Config.TRAIL_VIBRATION_AMPLITUDE
        
        # Sine wave oscillation
        vibration = amplitude * math.sin(2 * math.pi * frequency * phase)
        
        return vibration
    
    def _calculate_mine_kickback(self):
        """
        Calculate kickback force from hitting mine
        
        Returns:
            float: Negative force (pushes back)
        """
        return -Config.MINE_KICKBACK_FORCE
    
    def trigger_trail_collision(self, player_id):
        """Trigger trail collision vibration"""
        manager = self.effect_managers[player_id]
        
        # Clear any existing trail vibration
        manager.clear_effects_of_type(HapticEffect.TRAIL_VIBRATION)
        
        # Add new vibration effect (continuous until cleared)
        manager.add_effect(HapticEffect.TRAIL_VIBRATION, intensity=1.0, duration=0.0)
        
        # Reset vibration phase for consistent feel
        self.vibration_phase[player_id] = 0.0
    
    def clear_trail_collision(self, player_id):
        """Stop trail collision vibration"""
        manager = self.effect_managers[player_id]
        manager.clear_effects_of_type(HapticEffect.TRAIL_VIBRATION)
    
    def trigger_mine_hit(self, player_id):
        """Trigger mine kickback effect"""
        manager = self.effect_managers[player_id]
        manager.add_effect(HapticEffect.MINE_KICKBACK, intensity=1.0, 
                          duration=Config.MINE_KICKBACK_DURATION)
    
    def get_active_effects(self, player_id):
        """Get list of active effects for a player"""
        if player_id not in self.effect_managers:
            return []
        return self.effect_managers[player_id].get_effects()
