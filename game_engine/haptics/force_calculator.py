"""
Calculate haptic forces based on game state
"""
import math
import threading

from config import Config
from .effects import HapticEffect, HapticEffectManager
from .velocity_estimator import AxisVelocityEstimator

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
        self.axis_velocities = {
            1: {'steering': 0.0, 'throttle': 0.0},
            2: {'steering': 0.0, 'throttle': 0.0}
        }
        self.velocity_estimator = AxisVelocityEstimator()
        self._lock = threading.RLock()
    
    def update(self, dt, game_state=None, controller=None):
        """Update effect timers"""
        with self._lock:
            for manager in self.effect_managers.values():
                manager.update(dt)

            # Update vibration phase for oscillation
            for player_id in self.vibration_phase:
                self.vibration_phase[player_id] += dt

            if controller:
                self._start_velocity_estimator(controller)
                self._refresh_axis_velocities()

    def close(self):
        """Stop background haptic workers."""
        self.velocity_estimator.stop()
    
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
        with self._lock:
            if player_id not in game_state.ships:
                return (0.0, 0.0)

            ship = game_state.ships[player_id]

            if not ship.alive:
                return (0.0, 0.0)

            manager = self.effect_managers[player_id]

            # Start with base forces
            steering_force = 0.0
            throttle_force = 0.0

            # 1. Baseline axis forces.
            if controller:
                has_estimator_snapshot, positions, velocities = (
                    self.velocity_estimator.get_position_velocity_snapshot()
                )
                if has_estimator_snapshot:
                    estimator_positions = positions.get(player_id, {})
                    estimator_velocities = velocities.get(player_id, {})
                    steering_position = estimator_positions.get(
                        'steering',
                        controller.get_steering(player_id)
                    )
                    throttle_position = estimator_positions.get(
                        'throttle',
                        controller.get_throttle(player_id)
                    )
                    self.axis_velocities[player_id]['steering'] = estimator_velocities.get(
                        'steering',
                        self.axis_velocities[player_id]['steering']
                    )
                    self.axis_velocities[player_id]['throttle'] = estimator_velocities.get(
                        'throttle',
                        self.axis_velocities[player_id]['throttle']
                    )
                else:
                    steering_position = controller.get_steering(player_id)
                    throttle_position = controller.get_throttle(player_id)

                steering_force += self._calculate_steering_baseline_force(
                    ship,
                    player_id,
                    steering_position
                )

                throttle_force += self._calculate_throttle_baseline_force(
                    ship,
                    player_id,
                    throttle_position
                )

            # 2. Trail vibration
            if manager.has_effect(HapticEffect.TRAIL_VIBRATION):
                vibration = self._calculate_trail_vibration(player_id)
                steering_force += vibration

            # 3. Mine kickback
            if manager.has_effect(HapticEffect.MINE_KICKBACK):
                kickback = self._calculate_mine_kickback()
                throttle_force += kickback

            # Clamp forces to valid range
            steering_force = max(-1000, min(1000, steering_force))
            throttle_force = max(-1000, min(1000, throttle_force))

            return (steering_force, throttle_force)

    def _calculate_steering_baseline_force(self, ship, player_id, steering_position):
        """Calculate the selected steering force model before event effects."""
        mode = Config.STEERING_HAPTIC_MODE

        if mode == Config.HAPTIC_MODE_SPRING_DAMPER:
            spring = self._calculate_centering_spring(
                steering_position,
                Config.STEERING_CENTERING_SPRING_STIFFNESS
            )
            damping = self._calculate_knob_damping(
                ship,
                player_id,
                'steering',
                Config.STEERING_VELOCITY_DAMPING
            )
            return spring + damping

        if mode == Config.HAPTIC_MODE_VIRTUAL_WALLS:
            wall = self._calculate_virtual_wall(
                steering_position,
                Config.STEERING_MOTION_RANGE_DEG,
                Config.STEERING_CONTROL_ROTATION_RANGE,
                Config.STEERING_VIRTUAL_WALL_STIFFNESS
            )
            damping = self._calculate_knob_damping(
                ship,
                player_id,
                'steering',
                Config.STEERING_VELOCITY_DAMPING
            )
            return wall + damping

        raise ValueError(f"Unknown steering haptic mode: {mode}")

    def _calculate_throttle_baseline_force(self, ship, player_id, throttle_position):
        """Calculate the selected throttle force model before event effects."""
        mode = Config.THROTTLE_HAPTIC_MODE

        if mode == Config.THROTTLE_HAPTIC_MODE_SPRING_DAMPER:
            return self._calculate_throttle_spring_damper_force(
                ship,
                player_id,
                throttle_position
            )

        if mode == Config.THROTTLE_HAPTIC_MODE_VIRTUAL_WALLS:
            return self._calculate_throttle_virtual_wall_force(
                ship,
                player_id,
                throttle_position,
                damping_only_past_wall=True
            )

        if mode == Config.THROTTLE_HAPTIC_MODE_SPRING_DAMPER_WITH_WALLS:
            return (
                self._calculate_throttle_spring_damper_force(
                    ship,
                    player_id,
                    throttle_position
                )
                + self._calculate_throttle_virtual_wall_force(
                    ship,
                    player_id,
                    throttle_position,
                    damping_only_past_wall=False
                )
                + self._calculate_throttle_boost_push_through_force(
                    ship,
                    throttle_position
                )
            )

        raise ValueError(f"Unknown throttle haptic mode: {mode}")

    def _calculate_throttle_spring_damper_force(self, ship, player_id, throttle_position):
        """Calculate throttle spring plus always-on velocity damping."""
        spring = self._calculate_centering_spring(
            throttle_position,
            Config.THROTTLE_CENTERING_SPRING_STIFFNESS
        )
        damping = self._calculate_knob_damping(
            ship,
            player_id,
            'throttle',
            Config.THROTTLE_VELOCITY_DAMPING
        )
        return spring + damping

    def _calculate_throttle_virtual_wall_force(
        self,
        ship,
        player_id,
        throttle_position,
        damping_only_past_wall
    ):
        """Calculate throttle virtual-wall force, optionally with wall-contact damping."""
        throttle_forward_extension = 0.0
        if ship.boost_active:
            throttle_forward_extension = Config.BOOST_THROTTLE_FORWARD_EXTENSION_DEG

        force = self._calculate_virtual_wall(
            throttle_position,
            Config.THROTTLE_MOTION_RANGE_DEG,
            Config.THROTTLE_CONTROL_ROTATION_RANGE,
            Config.THROTTLE_VIRTUAL_WALL_STIFFNESS,
            forward_extension_deg=throttle_forward_extension
        )

        if damping_only_past_wall:
            if self._is_past_virtual_wall(
                throttle_position,
                Config.THROTTLE_MOTION_RANGE_DEG,
                Config.THROTTLE_CONTROL_ROTATION_RANGE,
                forward_extension_deg=throttle_forward_extension
            ):
                force += self._calculate_knob_damping(
                    ship,
                    player_id,
                    'throttle',
                    Config.THROTTLE_VELOCITY_DAMPING
                )

        return force

    def _calculate_throttle_boost_push_through_force(self, ship, throttle_position):
        """Add a short tactile gate at the original forward throttle wall during boost."""
        if not Config.THROTTLE_BOOST_PUSH_THROUGH_ENABLED or not ship.boost_active:
            return 0.0

        normal_forward_limit = self._get_virtual_wall_limits(
            Config.THROTTLE_MOTION_RANGE_DEG,
            Config.THROTTLE_CONTROL_ROTATION_RANGE
        )[1]
        gate_width = (
            Config.THROTTLE_BOOST_PUSH_THROUGH_WIDTH_DEG
            / (360.0 * Config.THROTTLE_CONTROL_ROTATION_RANGE)
        )

        if gate_width <= 0.0:
            return 0.0

        penetration = throttle_position - normal_forward_limit
        if penetration <= 0.0 or penetration >= gate_width:
            return 0.0

        gate_fade = 1.0 - (penetration / gate_width)
        return -penetration * Config.THROTTLE_BOOST_PUSH_THROUGH_STIFFNESS * gate_fade

    def _calculate_centering_spring(self, position, stiffness):
        """Calculate a simple spring force toward normalized zero."""
        return -position * stiffness

    def _calculate_virtual_wall(
        self,
        position,
        motion_range_deg,
        control_rotation_range,
        stiffness,
        forward_extension_deg=0.0
    ):
        """
        Calculate a centered virtual wall for an axis.

        Args:
            position: Normalized axis position where +/-1 is the axis control rotation range
            motion_range_deg: Total allowed centered motion in degrees
            control_rotation_range: Axis rotations that map to normalized +/-1
            stiffness: Wall stiffness for this axis
            forward_extension_deg: Extra positive-side motion in degrees

        Returns:
            float: Restoring force when outside the allowed range
        """
        rear_limit_deg = motion_range_deg / 2.0
        forward_limit_deg = (motion_range_deg / 2.0) + forward_extension_deg
        rear_limit = rear_limit_deg / (360.0 * control_rotation_range)
        forward_limit = forward_limit_deg / (360.0 * control_rotation_range)

        if position > forward_limit:
            return -(position - forward_limit) * stiffness
        if position < -rear_limit:
            return -(position + rear_limit) * stiffness

        return 0.0

    def _is_past_virtual_wall(
        self,
        position,
        motion_range_deg,
        control_rotation_range,
        forward_extension_deg=0.0
    ):
        """Return True when position is outside the virtual wall limits."""
        rear_limit, forward_limit = self._get_virtual_wall_limits(
            motion_range_deg,
            control_rotation_range,
            forward_extension_deg
        )

        return position > forward_limit or position < -rear_limit

    def _get_virtual_wall_limits(
        self,
        motion_range_deg,
        control_rotation_range,
        forward_extension_deg=0.0
    ):
        """Return normalized rear and forward wall limits."""
        rear_limit_deg = motion_range_deg / 2.0
        forward_limit_deg = (motion_range_deg / 2.0) + forward_extension_deg
        rear_limit = rear_limit_deg / (360.0 * control_rotation_range)
        forward_limit = forward_limit_deg / (360.0 * control_rotation_range)

        return rear_limit, forward_limit

    def _start_velocity_estimator(self, controller):
        """Start the high-rate velocity worker with the best available sampler."""
        if hasattr(controller, 'get_positions_snapshot'):
            self.velocity_estimator.start(
                lambda: controller.get_positions_snapshot(refresh=False)
            )
            return

        self.velocity_estimator.start(
            lambda: {
                player_id: {
                    'steering': controller.get_steering(player_id),
                    'throttle': controller.get_throttle(player_id)
                }
                for player_id in (1, 2)
            }
        )

    def _refresh_axis_velocities(self):
        """Query the velocity thread and copy its thread-safe snapshot."""
        self.axis_velocities = self.velocity_estimator.get_velocities()

    def get_axis_velocity(self, player_id, axis):
        """Return the latest filtered knob velocity from the daemon snapshot."""
        with self._lock:
            return self.axis_velocities.get(player_id, {}).get(axis, 0.0)

    def get_axis_position_velocity_snapshot(self):
        """Return estimator positions and velocities from the same sample."""
        return self.velocity_estimator.get_position_velocity_snapshot()

    def _calculate_knob_damping(self, ship, player_id, axis, damping_coefficient):
        """Calculate damping force from filtered knob velocity."""
        velocity = self.axis_velocities[player_id][axis]
        speed_scale = self._calculate_speed_damping_scale(ship)
        return -velocity * damping_coefficient * speed_scale

    def _calculate_speed_damping_scale(self, ship):
        """Calculate dormant ship-speed scaling for future damping tuning."""
        if not Config.SPEED_DAMPING_SCALING_ENABLED:
            return 1.0

        if Config.MAX_DAMPING <= 0:
            return 1.0

        speed = ship.velocity.length()

        if speed < Config.DAMPING_SPEED_THRESHOLD * 0.3:
            return Config.MIN_DAMPING / Config.MAX_DAMPING

        damping_ratio = (
            (speed - Config.DAMPING_SPEED_THRESHOLD * 0.3)
            / (Config.DAMPING_SPEED_THRESHOLD * 0.7)
        )
        damping_ratio = max(0.0, min(1.0, damping_ratio))
        damping = Config.MIN_DAMPING + (Config.MAX_DAMPING - Config.MIN_DAMPING) * damping_ratio

        return damping / Config.MAX_DAMPING
    
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
        with self._lock:
            manager = self.effect_managers[player_id]

            # Clear any existing trail vibration
            manager.clear_effects_of_type(HapticEffect.TRAIL_VIBRATION)

            # Add new vibration effect (continuous until cleared)
            manager.add_effect(HapticEffect.TRAIL_VIBRATION, intensity=1.0, duration=0.0)

            # Reset vibration phase for consistent feel
            self.vibration_phase[player_id] = 0.0
    
    def clear_trail_collision(self, player_id):
        """Stop trail collision vibration"""
        with self._lock:
            manager = self.effect_managers[player_id]
            manager.clear_effects_of_type(HapticEffect.TRAIL_VIBRATION)
    
    def trigger_mine_hit(self, player_id):
        """Trigger mine kickback effect"""
        with self._lock:
            manager = self.effect_managers[player_id]
            manager.add_effect(HapticEffect.MINE_KICKBACK, intensity=1.0, 
                              duration=Config.MINE_KICKBACK_DURATION)
    
    def get_active_effects(self, player_id):
        """Get list of active effects for a player"""
        with self._lock:
            if player_id not in self.effect_managers:
                return []
            return self.effect_managers[player_id].get_effects()
