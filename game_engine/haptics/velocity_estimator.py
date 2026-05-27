"""
Threaded velocity estimation for haptic controller axes.
"""
import threading
import time

import numpy as np

from config import Config

try:
    from numba import njit
except ImportError:
    def njit(*args, **kwargs):
        if args and callable(args[0]):
            return args[0]

        def decorator(func):
            return func

        return decorator


PLAYER_IDS = (1, 2)
AXIS_NAMES = ("steering", "throttle")


@njit(cache=True)
def _estimate_axis_velocities(
    previous_positions,
    current_positions,
    previous_velocities,
    previous_position_times,
    sample_time,
    alpha,
    max_velocities,
    max_acceleration,
    min_sample_interval,
    position_noise_deadband,
    velocity_zero_deadband,
    stale_timeout
):
    """Estimate velocity from actual position changes, not repeated samples."""
    delta = current_positions - previous_positions
    velocities = previous_velocities.copy()
    position_times = previous_position_times.copy()

    for player_index in range(current_positions.shape[0]):
        for axis_index in range(current_positions.shape[1]):
            axis_delta = delta[player_index, axis_index]
            previous_time = previous_position_times[player_index, axis_index]
            dt = sample_time - previous_time

            if dt < min_sample_interval:
                continue

            if abs(axis_delta) >= position_noise_deadband and dt > 0.0:
                max_velocity = max_velocities[axis_index]
                raw_velocity = axis_delta / dt
                raw_velocity = min(max(raw_velocity, -max_velocity), max_velocity)

                if max_acceleration > 0.0:
                    max_step = max_acceleration * dt
                    lower = previous_velocities[player_index, axis_index] - max_step
                    upper = previous_velocities[player_index, axis_index] + max_step
                    raw_velocity = min(max(raw_velocity, lower), upper)

                velocities[player_index, axis_index] = (
                    alpha * raw_velocity
                    + (1.0 - alpha) * previous_velocities[player_index, axis_index]
                )
                velocities[player_index, axis_index] = min(
                    max(velocities[player_index, axis_index], -max_velocity),
                    max_velocity
                )
                if abs(velocities[player_index, axis_index]) < velocity_zero_deadband:
                    velocities[player_index, axis_index] = 0.0

                previous_positions[player_index, axis_index] = current_positions[player_index, axis_index]
                position_times[player_index, axis_index] = sample_time
            elif abs(axis_delta) < position_noise_deadband:
                velocities[player_index, axis_index] = 0.0
                previous_positions[player_index, axis_index] = current_positions[player_index, axis_index]
                position_times[player_index, axis_index] = sample_time
            elif sample_time - previous_time >= stale_timeout:
                velocities[player_index, axis_index] = 0.0

    return previous_positions, velocities, position_times


class AxisVelocityEstimator:
    """Sample controller positions in a worker thread and expose safe snapshots."""

    def __init__(self, frequency_hz=None):
        self.frequency_hz = frequency_hz or Config.KNOB_VELOCITY_THREAD_FREQUENCY_HZ
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        self._sample_positions = None
        self._initialized = False
        self._previous_positions = np.zeros((2, 2), dtype=np.float64)
        self._previous_position_times = np.zeros((2, 2), dtype=np.float64)
        self._velocities = np.zeros((2, 2), dtype=np.float64)
        self._latest_snapshot = self._empty_snapshot()

    def start(self, sample_positions):
        """Start the estimator if it is not already running."""
        if self._thread and self._thread.is_alive():
            return

        self._sample_positions = sample_positions
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="haptic-velocity-estimator",
            daemon=True
        )
        self._thread.start()

    def stop(self, timeout=0.5):
        """Stop the estimator thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
            self._thread = None

    def get_velocity(self, player_id, axis):
        """Return one filtered velocity without exposing mutable thread state."""
        with self._lock:
            return self._latest_snapshot.get(player_id, {}).get(axis, 0.0)

    def get_velocities(self):
        """Return a full immutable velocity snapshot."""
        with self._lock:
            return {
                player_id: axes.copy()
                for player_id, axes in self._latest_snapshot.items()
            }

    def get_last_positions(self):
        """Return the last sampled positions as a controller-shaped dict."""
        with self._lock:
            return self._positions_to_dict(self._previous_positions)

    def get_position_velocity_snapshot(self):
        """Return positions and velocities from the same estimator snapshot."""
        with self._lock:
            return (
                self._initialized,
                self._positions_to_dict(self._previous_positions),
                {
                    player_id: axes.copy()
                    for player_id, axes in self._latest_snapshot.items()
                }
            )

    def _run(self):
        interval = 1.0 / max(1.0, float(self.frequency_hz))
        next_sample_time = time.perf_counter()

        while not self._stop_event.is_set():
            now = time.perf_counter()
            if now < next_sample_time:
                time.sleep(min(next_sample_time - now, interval))
                continue

            self._sample()
            next_sample_time += interval

            if next_sample_time < now - interval:
                next_sample_time = now + interval

    def _sample(self):
        try:
            positions = self._positions_to_array(self._sample_positions())
        except Exception:
            return
        sample_time = time.perf_counter()

        if not self._initialized:
            with self._lock:
                self._previous_positions = positions
                self._previous_position_times = np.full((2, 2), sample_time, dtype=np.float64)
                self._initialized = True
            return

        alpha = max(0.0, min(1.0, Config.KNOB_VELOCITY_FILTER_ALPHA))
        max_velocities = self._max_normalized_velocities()
        max_acceleration = max(0.0, Config.MAX_KNOB_ACCELERATION)
        min_sample_interval = max(0.0, Config.KNOB_VELOCITY_MIN_SAMPLE_INTERVAL_SEC)
        noise_deadband = max(0.0, Config.KNOB_VELOCITY_POSITION_NOISE_DEADBAND)
        zero_deadband = max(0.0, Config.KNOB_VELOCITY_ZERO_DEADBAND)
        stale_timeout = max(0.0, Config.KNOB_VELOCITY_STALE_TIMEOUT_SEC)

        previous_positions, velocities, position_times = _estimate_axis_velocities(
            self._previous_positions.copy(),
            positions,
            self._velocities,
            self._previous_position_times,
            sample_time,
            alpha,
            max_velocities,
            max_acceleration,
            min_sample_interval,
            noise_deadband,
            zero_deadband,
            stale_timeout
        )

        snapshot = self._velocities_to_dict(velocities)
        with self._lock:
            self._previous_positions = previous_positions
            self._previous_position_times = position_times
            self._velocities = velocities
            self._latest_snapshot = snapshot

    def _positions_to_array(self, positions):
        values = np.zeros((2, 2), dtype=np.float64)
        for player_index, player_id in enumerate(PLAYER_IDS):
            player_positions = positions.get(player_id, {})
            for axis_index, axis in enumerate(AXIS_NAMES):
                values[player_index, axis_index] = player_positions.get(axis, 0.0)
        return values

    def _max_normalized_velocities(self):
        output_velocity_limit = max(0.0, Config.MAX_KNOB_OUTPUT_VELOCITY_DEG_PER_SEC)
        return np.array([
            self._output_deg_per_sec_to_normalized_per_sec(
                output_velocity_limit,
                Config.STEERING_CONTROL_ROTATION_RANGE,
                Config.STEERING_TRANSMISSION_RATIO
            ),
            self._output_deg_per_sec_to_normalized_per_sec(
                output_velocity_limit,
                Config.THROTTLE_CONTROL_ROTATION_RANGE,
                Config.THROTTLE_TRANSMISSION_RATIO
            )
        ], dtype=np.float64)

    def _output_deg_per_sec_to_normalized_per_sec(
        self,
        output_deg_per_sec,
        control_rotation_range,
        transmission_ratio
    ):
        encoder_deg_per_sec = output_deg_per_sec * max(0.0, transmission_ratio)
        normalized_denominator = 360.0 * max(0.000001, control_rotation_range)
        return encoder_deg_per_sec / normalized_denominator

    def _velocities_to_dict(self, velocities):
        return {
            player_id: {
                axis: float(velocities[player_index, axis_index])
                for axis_index, axis in enumerate(AXIS_NAMES)
            }
            for player_index, player_id in enumerate(PLAYER_IDS)
        }

    def _positions_to_dict(self, positions):
        return {
            player_id: {
                axis: float(positions[player_index, axis_index])
                for axis_index, axis in enumerate(AXIS_NAMES)
            }
            for player_index, player_id in enumerate(PLAYER_IDS)
        }

    def _empty_snapshot(self):
        return {
            player_id: {axis: 0.0 for axis in AXIS_NAMES}
            for player_id in PLAYER_IDS
        }
