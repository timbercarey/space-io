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
        self.throttle_position_pulse_phase = {1: 0.0, 2: 0.0}
        self.mine_hit_steering_vibration_phase = {1: 0.0, 2: 0.0}
        self.asteroid_bounce_steering_vibration_phase = {1: 0.0, 2: 0.0}
        self.axis_velocities = {
            1: {'steering': 0.0, 'throttle': 0.0},
            2: {'steering': 0.0, 'throttle': 0.0}
        }
        self.steering_wall_damping_latched = {1: False, 2: False}
        self.asteroid_bounce_steering_direction = {1: 1.0, 2: 1.0}
        self.velocity_estimator = AxisVelocityEstimator()
        self.using_hardware_velocity = False
        self._latest_position_velocity_snapshot = (
            False,
            {
                1: {'steering': 0.0, 'throttle': 0.0},
                2: {'steering': 0.0, 'throttle': 0.0}
            },
            {
                1: {'steering': 0.0, 'throttle': 0.0},
                2: {'steering': 0.0, 'throttle': 0.0}
            }
        )
        self._lock = threading.RLock()
    
    def update(self, dt, game_state=None, controller=None):
        """Update effect timers"""
        with self._lock:
            for manager in self.effect_managers.values():
                manager.update(dt)

            # Update vibration phase for oscillation
            for player_id in self.vibration_phase:
                self.vibration_phase[player_id] += dt
                self.throttle_position_pulse_phase[player_id] += dt
                self.mine_hit_steering_vibration_phase[player_id] += dt
                self.asteroid_bounce_steering_vibration_phase[player_id] += dt

            if controller:
                self._start_velocity_source(controller)
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
            manager = self.effect_managers[player_id]
            apply_baseline_forces = (
                ship.alive
                or self._is_between_rounds_waiting_for_restart(game_state)
            )

            has_death_effect = manager.has_effect(HapticEffect.MINE_KICKBACK)
            if not apply_baseline_forces and not has_death_effect:
                return (0.0, 0.0)

            # Start with base forces
            steering_force = 0.0
            throttle_force = 0.0

            # 1. Baseline axis forces.
            if controller and apply_baseline_forces:
                has_velocity_snapshot, positions, velocities = (
                    self._get_position_velocity_snapshot(controller)
                )
                if has_velocity_snapshot:
                    velocity_positions = positions.get(player_id, {})
                    velocity_values = velocities.get(player_id, {})
                    steering_position = velocity_positions.get(
                        'steering',
                        controller.get_steering(player_id)
                    )
                    throttle_position = velocity_positions.get(
                        'throttle',
                        controller.get_throttle(player_id)
                    )
                    self.axis_velocities[player_id]['steering'] = velocity_values.get(
                        'steering',
                        self.axis_velocities[player_id]['steering']
                    )
                    self.axis_velocities[player_id]['throttle'] = velocity_values.get(
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
                throttle_force += self._calculate_throttle_position_pulse(
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
                steering_force += self._calculate_mine_hit_steering_vibration(player_id)
                throttle_force += kickback

            # 4. Asteroid bounce impulse while boosted
            if manager.has_effect(HapticEffect.ASTEROID_BOUNCE):
                steering_force += self._calculate_asteroid_bounce_steering_vibration(player_id)
                throttle_force += Config.ASTEROID_BOUNCE_THROTTLE_FORCE

            # 5. Faint forward throttle impulse when a star boost starts
            if manager.has_effect(HapticEffect.STAR_BOOST):
                throttle_force += Config.BOOST_THROTTLE_IMPULSE_FORCE

            # Clamp forces to valid range
            steering_force = max(-1000, min(1000, steering_force))
            throttle_force = max(-1000, min(1000, throttle_force))

            return (steering_force, throttle_force)

    def _is_between_rounds_waiting_for_restart(self, game_state):
        """Return True while a non-final two-player round is resetting."""
        return (
            game_state.num_players == 2
            and game_state.game_over
            and game_state.get_match_winner() is None
        )

    def _calculate_steering_baseline_force(self, ship, player_id, steering_position):
        """Calculate the selected steering force model before event effects."""
        mode = Config.STEERING_HAPTIC_MODE

        if mode == Config.HAPTIC_MODE_OFF:
            return 0.0

        if mode == Config.HAPTIC_MODE_SPRING_ONLY:
            return self._calculate_centering_spring(
                steering_position,
                Config.STEERING_CENTERING_SPRING_STIFFNESS
            )

        if mode == Config.HAPTIC_MODE_DAMPER_ONLY:
            damping = self._calculate_steering_damping_force(
                ship,
                player_id,
                steering_position,
                include_wall_damping=False
            )
            return damping

        if mode == Config.HAPTIC_MODE_SPRING_DAMPER:
            spring = self._calculate_centering_spring(
                steering_position,
                Config.STEERING_CENTERING_SPRING_STIFFNESS
            )
            damping = self._calculate_steering_damping_force(
                ship,
                player_id,
                steering_position,
                include_wall_damping=False
            )
            return spring + damping

        if mode == Config.HAPTIC_MODE_VIRTUAL_WALLS:
            wall = self._calculate_virtual_wall(
                steering_position,
                Config.STEERING_MOTION_RANGE_DEG,
                Config.STEERING_CONTROL_ROTATION_RANGE,
                Config.STEERING_VIRTUAL_WALL_STIFFNESS
            )
            damping = self._calculate_steering_damping_force(
                ship,
                player_id,
                steering_position,
                include_wall_damping=True
            )
            return wall + damping

        if mode == Config.HAPTIC_MODE_SPRING_DAMPER_WITH_WALLS:
            spring = self._calculate_centering_spring(
                steering_position,
                Config.STEERING_CENTERING_SPRING_STIFFNESS
            )
            damping = self._calculate_steering_damping_force(
                ship,
                player_id,
                steering_position,
                include_wall_damping=True
            )
            wall = self._calculate_virtual_wall(
                steering_position,
                Config.STEERING_MOTION_RANGE_DEG,
                Config.STEERING_CONTROL_ROTATION_RANGE,
                Config.STEERING_VIRTUAL_WALL_STIFFNESS
            )
            return spring + damping + wall

        raise ValueError(f"Unknown steering haptic mode: {mode}")

    def _calculate_throttle_baseline_force(self, ship, player_id, throttle_position):
        """Calculate the selected throttle force model before event effects."""
        mode = Config.THROTTLE_HAPTIC_MODE

        if mode == Config.HAPTIC_MODE_OFF:
            return 0.0

        if mode == Config.HAPTIC_MODE_SPRING_ONLY:
            return self._calculate_centering_spring(
                throttle_position,
                Config.THROTTLE_CENTERING_SPRING_STIFFNESS
            )

        if mode == Config.HAPTIC_MODE_DAMPER_ONLY:
            return self._calculate_knob_damping(
                ship,
                player_id,
                'throttle',
                Config.THROTTLE_VELOCITY_DAMPING
            )

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

    def _calculate_throttle_position_pulse(self, player_id, throttle_position):
        """Pulse throttle from the brake wall toward the boosted forward wall."""
        if not Config.THROTTLE_POSITION_PULSE_ENABLED:
            return 0.0

        brake_wall_position, peak_throttle_position = self._get_virtual_wall_limits(
            Config.THROTTLE_MOTION_RANGE_DEG,
            Config.THROTTLE_CONTROL_ROTATION_RANGE,
            forward_extension_deg=Config.BOOST_THROTTLE_FORWARD_EXTENSION_DEG
        )
        start_position = -brake_wall_position + max(
            0.0,
            Config.THROTTLE_POSITION_PULSE_BRAKE_WALL_BUFFER
        )

        if throttle_position <= start_position:
            self.throttle_position_pulse_phase[player_id] = 0.0
            return 0.0

        usable_range = max(0.001, peak_throttle_position - start_position)
        pulse_scale = max(
            0.0,
            min(1.0, (throttle_position - start_position) / usable_range)
        )
        min_interval = max(0.001, Config.THROTTLE_POSITION_PULSE_MIN_INTERVAL_SEC)
        max_interval = max(min_interval, Config.THROTTLE_POSITION_PULSE_MAX_INTERVAL_SEC)
        interval = max_interval - (max_interval - min_interval) * pulse_scale
        width = max(0.001, min(Config.THROTTLE_POSITION_PULSE_WIDTH_SEC, interval))

        phase = self.throttle_position_pulse_phase[player_id] % interval
        if phase >= width:
            return 0.0

        pulse_progress = phase / width
        pulse_envelope = math.sin(math.pi * pulse_progress)
        burst_frequency = max(1.0, Config.THROTTLE_POSITION_PULSE_BURST_FREQ)
        burst_vibration = math.sin(2 * math.pi * burst_frequency * phase)
        min_force = max(0.0, Config.THROTTLE_POSITION_PULSE_MIN_FORCE)
        max_force = max(min_force, Config.THROTTLE_POSITION_PULSE_MAX_FORCE)
        amplitude = min_force + (max_force - min_force) * pulse_scale
        return amplitude * pulse_envelope * burst_vibration

    def _calculate_centering_spring(self, position, stiffness):
        """Calculate a simple spring force toward normalized zero."""
        return -position * stiffness

    def _calculate_steering_wall_damping(self, player_id, steering_position, velocity):
        """Add damping only while steering is moving deeper into a wall."""
        damping_coefficient = Config.STEERING_VIRTUAL_WALL_INTO_WALL_DAMPING
        if damping_coefficient <= 0.0:
            return 0.0

        penetration = self._calculate_virtual_wall_penetration(
            steering_position,
            Config.STEERING_MOTION_RANGE_DEG,
            Config.STEERING_CONTROL_ROTATION_RANGE
        )
        if penetration <= 0.0:
            self.steering_wall_damping_latched[player_id] = False
            return 0.0

        outward_velocity = self._calculate_virtual_wall_outward_velocity(
            steering_position,
            velocity,
            Config.STEERING_MOTION_RANGE_DEG,
            Config.STEERING_CONTROL_ROTATION_RANGE
        )
        if outward_velocity <= 0.0:
            self.steering_wall_damping_latched[player_id] = False
            return 0.0

        if not self._steering_wall_damping_velocity_gate(player_id, outward_velocity):
            return 0.0

        penetration_after_threshold = self._steering_wall_damping_effective_penetration(
            penetration
        )
        if penetration_after_threshold <= 0.0:
            return 0.0

        damping_scale = self._steering_wall_damping_penetration_scale(
            penetration_after_threshold
        )
        return -velocity * damping_coefficient * damping_scale

    def _calculate_steering_damping_force(
        self,
        ship,
        player_id,
        steering_position,
        include_wall_damping
    ):
        """Calculate total steering damping, capped as one combined component."""
        velocity = self._get_steering_damping_velocity(player_id)
        damping = (
            -velocity
            * Config.STEERING_VELOCITY_DAMPING
            * self._calculate_speed_damping_scale(ship)
        )
        if include_wall_damping:
            damping += self._calculate_steering_wall_damping(
                player_id,
                steering_position,
                velocity
            )
        return self._limit_steering_damping_force(damping)

    def _get_steering_damping_velocity(self, player_id):
        """Return steering velocity after optional direct clipping for damping."""
        velocity = self.axis_velocities[player_id]['steering']
        if not Config.STEERING_DAMPING_VELOCITY_CAP_ENABLED:
            return velocity

        limit = Config.STEERING_DAMPING_VELOCITY_LIMIT
        if limit <= 0.0:
            return velocity

        return max(-limit, min(limit, velocity))

    def _steering_wall_damping_velocity_gate(self, player_id, outward_velocity):
        """Gate wall damping with optional outward-velocity hysteresis."""
        if not Config.STEERING_WALL_DAMPING_VELOCITY_HYSTERESIS_ENABLED:
            return True

        enter_threshold = max(0.0, Config.STEERING_WALL_DAMPING_VELOCITY_ENTER_THRESHOLD)
        exit_threshold = max(
            0.0,
            min(enter_threshold, Config.STEERING_WALL_DAMPING_VELOCITY_EXIT_THRESHOLD)
        )
        is_latched = self.steering_wall_damping_latched.get(player_id, False)

        if is_latched:
            if outward_velocity <= exit_threshold:
                self.steering_wall_damping_latched[player_id] = False
                return False
            return True

        if outward_velocity >= enter_threshold:
            self.steering_wall_damping_latched[player_id] = True
            return True

        return False

    def _steering_wall_damping_effective_penetration(self, penetration):
        """Apply optional minimum penetration before wall damping can engage."""
        if not Config.STEERING_WALL_DAMPING_MIN_PENETRATION_ENABLED:
            return penetration

        return penetration - max(0.0, Config.STEERING_WALL_DAMPING_MIN_PENETRATION)

    def _steering_wall_damping_penetration_scale(self, effective_penetration):
        """Fade in extra wall damping over the configured penetration distance."""
        if not Config.STEERING_WALL_DAMPING_PENETRATION_RAMP_ENABLED:
            return 1.0

        ramp_penetration = max(0.0, Config.STEERING_WALL_DAMPING_RAMP_PENETRATION)
        if ramp_penetration <= 0.0:
            return 1.0

        return max(0.0, min(1.0, effective_penetration / ramp_penetration))

    def _limit_steering_damping_force(self, damping_force):
        """Clamp steering damping in motor force units; non-positive disables cap."""
        limit = Config.STEERING_DAMPING_FORCE_LIMIT
        if limit <= 0.0:
            return damping_force

        return max(-limit, min(limit, damping_force))

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

    def _is_moving_deeper_into_virtual_wall(
        self,
        position,
        velocity,
        motion_range_deg,
        control_rotation_range,
        forward_extension_deg=0.0
    ):
        """Return True only when penetration and velocity point farther outward."""
        rear_limit, forward_limit = self._get_virtual_wall_limits(
            motion_range_deg,
            control_rotation_range,
            forward_extension_deg
        )

        return (
            (position > forward_limit and velocity > 0.0)
            or (position < -rear_limit and velocity < 0.0)
        )

    def _calculate_virtual_wall_penetration(
        self,
        position,
        motion_range_deg,
        control_rotation_range,
        forward_extension_deg=0.0
    ):
        """Return positive normalized penetration beyond either virtual wall."""
        rear_limit, forward_limit = self._get_virtual_wall_limits(
            motion_range_deg,
            control_rotation_range,
            forward_extension_deg
        )

        if position > forward_limit:
            return position - forward_limit
        if position < -rear_limit:
            return -rear_limit - position

        return 0.0

    def _calculate_virtual_wall_outward_velocity(
        self,
        position,
        velocity,
        motion_range_deg,
        control_rotation_range,
        forward_extension_deg=0.0
    ):
        """Return positive velocity only when moving farther into a wall."""
        rear_limit, forward_limit = self._get_virtual_wall_limits(
            motion_range_deg,
            control_rotation_range,
            forward_extension_deg
        )

        if position > forward_limit:
            return max(0.0, velocity)
        if position < -rear_limit:
            return max(0.0, -velocity)

        return 0.0

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

    def _start_velocity_source(self, controller):
        """Use hardware velocity when available, otherwise start the host estimator."""
        has_hardware_velocity = (
            hasattr(controller, 'get_position_velocity_snapshot')
            and (
                not hasattr(controller, 'has_hardware_velocity_data')
                or controller.has_hardware_velocity_data()
            )
        )
        if has_hardware_velocity:
            self.using_hardware_velocity = True
            self.velocity_estimator.stop()
            return

        self.using_hardware_velocity = False
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
        """Query the velocity source and copy its thread-safe snapshot."""
        if self.using_hardware_velocity:
            return

        self.axis_velocities = self.velocity_estimator.get_velocities()

    def get_axis_velocity(self, player_id, axis):
        """Return the latest filtered knob velocity from the daemon snapshot."""
        with self._lock:
            return self.axis_velocities.get(player_id, {}).get(axis, 0.0)

    def get_axis_position_velocity_snapshot(self):
        """Return positions and velocities from the active velocity source."""
        if self.using_hardware_velocity:
            return self._latest_position_velocity_snapshot

        return self.velocity_estimator.get_position_velocity_snapshot()

    def _get_position_velocity_snapshot(self, controller):
        """Return hardware or host-estimated position/velocity data."""
        if self.using_hardware_velocity and hasattr(controller, 'get_position_velocity_snapshot'):
            self._latest_position_velocity_snapshot = (
                controller.get_position_velocity_snapshot(refresh=False)
            )
            return self._latest_position_velocity_snapshot

        self._latest_position_velocity_snapshot = (
            self.velocity_estimator.get_position_velocity_snapshot()
        )
        return self._latest_position_velocity_snapshot

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

    def _calculate_mine_hit_steering_vibration(self, player_id):
        """Calculate short steering vibration from hitting an asteroid."""
        phase = self.mine_hit_steering_vibration_phase[player_id]
        frequency = Config.MINE_STEERING_VIBRATION_FREQ
        amplitude = Config.MINE_STEERING_VIBRATION_AMPLITUDE
        return amplitude * math.sin(2 * math.pi * frequency * phase)

    def _calculate_asteroid_bounce_steering_vibration(self, player_id):
        """Calculate short steering vibration from bouncing off an asteroid."""
        phase = self.asteroid_bounce_steering_vibration_phase[player_id]
        frequency = Config.ASTEROID_BOUNCE_STEERING_VIBRATION_FREQ
        amplitude = Config.ASTEROID_BOUNCE_STEERING_FORCE
        direction = self.asteroid_bounce_steering_direction.get(player_id, 1.0)
        return direction * amplitude * math.sin(2 * math.pi * frequency * phase)
    
    def trigger_trail_collision(self, player_id):
        """Trigger trail collision vibration"""
        with self._lock:
            manager = self.effect_managers[player_id]

            if not Config.TRAIL_VIBRATION_ENABLED:
                manager.clear_effects_of_type(HapticEffect.TRAIL_VIBRATION)
                return

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
            manager.clear_effects_of_type(HapticEffect.MINE_KICKBACK)
            self.mine_hit_steering_vibration_phase[player_id] = 0.0
            manager.add_effect(HapticEffect.MINE_KICKBACK, intensity=1.0, 
                              duration=Config.MINE_KICKBACK_DURATION)

    def trigger_star_boost(self, player_id):
        """Trigger a short throttle impulse when collecting a boost star."""
        with self._lock:
            manager = self.effect_managers[player_id]
            manager.clear_effects_of_type(HapticEffect.STAR_BOOST)
            manager.add_effect(
                HapticEffect.STAR_BOOST,
                intensity=1.0,
                duration=Config.BOOST_THROTTLE_IMPULSE_DURATION
            )

    def trigger_asteroid_bounce(self, player_id, steering_direction):
        """Trigger steering and throttle impulse for boosted asteroid bounce."""
        with self._lock:
            manager = self.effect_managers[player_id]
            manager.clear_effects_of_type(HapticEffect.ASTEROID_BOUNCE)
            self.asteroid_bounce_steering_direction[player_id] = steering_direction
            self.asteroid_bounce_steering_vibration_phase[player_id] = 0.0
            manager.add_effect(
                HapticEffect.ASTEROID_BOUNCE,
                intensity=1.0,
                duration=Config.ASTEROID_BOUNCE_FORCE_DURATION
            )
    
    def get_active_effects(self, player_id):
        """Get list of active effects for a player"""
        with self._lock:
            if player_id not in self.effect_managers:
                return []
            return self.effect_managers[player_id].get_effects()
