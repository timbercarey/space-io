"""
Generate static plots for haptic force tuning.
"""
import os

os.environ.setdefault(
    "MPLCONFIGDIR",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), ".matplotlib")
)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from config import Config
from .force_calculator import ForceCalculator


def generate_haptic_debug_plots(output_dir=None):
    """Generate haptic force plots and return written file paths."""
    if output_dir is None:
        output_dir = Config.HAPTIC_DEBUG_PLOT_DIR

    os.makedirs(output_dir, exist_ok=True)

    calculator = ForceCalculator()
    paths = [
        _plot_steering_force_vs_angle(calculator, output_dir),
        _plot_steering_force_vs_velocity(output_dir),
        _plot_throttle_force_vs_angle(calculator, output_dir),
        _plot_throttle_force_vs_velocity(output_dir),
        _plot_impulse_effects(output_dir),
    ]

    return paths


def _save(fig, output_dir, filename):
    path = os.path.join(output_dir, filename)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _axis_positions(control_rotation_range, samples=500):
    angle_limit = 360.0 * control_rotation_range
    angles = np.linspace(-angle_limit, angle_limit, samples)
    positions = angles / angle_limit
    return angles, positions


def _wall_limits(motion_range_deg, control_rotation_range, forward_extension_deg=0.0):
    rear = -(motion_range_deg / 2.0)
    forward = (motion_range_deg / 2.0) + forward_extension_deg
    rear_position = rear / (360.0 * control_rotation_range)
    forward_position = forward / (360.0 * control_rotation_range)
    return rear, forward, rear_position, forward_position


def _plot_wall_lines(ax, motion_range_deg, control_rotation_range, forward_extension_deg=0.0):
    rear, forward, _, _ = _wall_limits(
        motion_range_deg,
        control_rotation_range,
        forward_extension_deg
    )
    ax.axvline(rear, color="0.55", linestyle="--", linewidth=1, label="Wall limit")
    ax.axvline(forward, color="0.55", linestyle="--", linewidth=1)


def _plot_steering_force_vs_angle(calculator, output_dir):
    angles, positions = _axis_positions(Config.STEERING_CONTROL_ROTATION_RANGE)
    fig, ax = plt.subplots(figsize=(9, 5))

    if Config.STEERING_HAPTIC_MODE == Config.HAPTIC_MODE_SPRING_DAMPER:
        spring = [
            calculator._calculate_centering_spring(
                pos,
                Config.STEERING_CENTERING_SPRING_STIFFNESS
            )
            for pos in positions
        ]
        ax.plot(angles, spring, label="Steering centering spring")
    else:
        wall = [
            calculator._calculate_virtual_wall(
                pos,
                Config.STEERING_MOTION_RANGE_DEG,
                Config.STEERING_CONTROL_ROTATION_RANGE,
                Config.STEERING_VIRTUAL_WALL_STIFFNESS
            )
            for pos in positions
        ]
        ax.plot(angles, wall, label="Wall spring")
        _plot_wall_lines(ax, Config.STEERING_MOTION_RANGE_DEG, Config.STEERING_CONTROL_ROTATION_RANGE)

    ax.set_title("Steering Force vs. Angle")
    ax.set_xlabel("Steering angle from center (deg)")
    ax.set_ylabel("Force command")
    ax.grid(True, alpha=0.3)
    ax.legend()
    return _save(fig, output_dir, "steering_force_vs_angle.png")


def _plot_steering_force_vs_velocity(output_dir):
    max_velocity = _output_deg_per_sec_to_normalized_per_sec(
        Config.MAX_KNOB_OUTPUT_VELOCITY_DEG_PER_SEC,
        Config.STEERING_CONTROL_ROTATION_RANGE,
        Config.STEERING_TRANSMISSION_RATIO
    )
    velocities = np.linspace(-max_velocity, max_velocity, 500)
    damping = -velocities * Config.STEERING_VELOCITY_DAMPING

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(velocities, damping, label="Steering damping")
    ax.axhline(0, color="0.55", linewidth=1)
    ax.axvline(0, color="0.55", linewidth=1)
    ax.set_title("Steering Force vs. Velocity")
    ax.set_xlabel("Normalized steering velocity / sec")
    ax.set_ylabel("Force command")
    ax.grid(True, alpha=0.3)
    ax.legend()
    return _save(fig, output_dir, "steering_force_vs_velocity.png")


def _plot_throttle_force_vs_angle(calculator, output_dir):
    angles, positions = _axis_positions(Config.THROTTLE_CONTROL_ROTATION_RANGE)
    fig, ax = plt.subplots(figsize=(9, 5))

    if Config.THROTTLE_HAPTIC_MODE == Config.HAPTIC_MODE_SPRING_DAMPER:
        spring = [
            calculator._calculate_centering_spring(
                pos,
                Config.THROTTLE_CENTERING_SPRING_STIFFNESS
            )
            for pos in positions
        ]
        ax.plot(angles, spring, label="Throttle centering spring")
    else:
        spring = [
            calculator._calculate_centering_spring(
                pos,
                Config.THROTTLE_CENTERING_SPRING_STIFFNESS
            )
            for pos in positions
        ]
        wall = [
            calculator._calculate_virtual_wall(
                pos,
                Config.THROTTLE_MOTION_RANGE_DEG,
                Config.THROTTLE_CONTROL_ROTATION_RANGE,
                Config.THROTTLE_VIRTUAL_WALL_STIFFNESS
            )
            for pos in positions
        ]
        boost_wall = [
            calculator._calculate_virtual_wall(
                pos,
                Config.THROTTLE_MOTION_RANGE_DEG,
                Config.THROTTLE_CONTROL_ROTATION_RANGE,
                Config.THROTTLE_VIRTUAL_WALL_STIFFNESS,
                forward_extension_deg=Config.BOOST_THROTTLE_FORWARD_EXTENSION_DEG
            )
            for pos in positions
        ]

        if Config.THROTTLE_HAPTIC_MODE == Config.HAPTIC_MODE_SPRING_DAMPER_WITH_WALLS:
            ax.plot(
                angles,
                [spring_force + wall_force for spring_force, wall_force in zip(spring, wall)],
                label="Throttle spring + wall"
            )
            ax.plot(
                angles,
                [
                    spring_force + wall_force
                    for spring_force, wall_force in zip(spring, boost_wall)
                ],
                label="Throttle spring + wall while boost is active"
            )
        else:
            ax.plot(angles, wall, label="Throttle wall")
            ax.plot(angles, boost_wall, label="Throttle wall while boost is active")

        _plot_wall_lines(ax, Config.THROTTLE_MOTION_RANGE_DEG, Config.THROTTLE_CONTROL_ROTATION_RANGE)
        _plot_wall_lines(
            ax,
            Config.THROTTLE_MOTION_RANGE_DEG,
            Config.THROTTLE_CONTROL_ROTATION_RANGE,
            Config.BOOST_THROTTLE_FORWARD_EXTENSION_DEG
        )

    ax.set_title("Throttle Force vs. Angle")
    ax.set_xlabel("Throttle angle from center (deg)")
    ax.set_ylabel("Force command")
    ax.grid(True, alpha=0.3)
    ax.legend()
    return _save(fig, output_dir, "throttle_force_vs_angle.png")


def _plot_throttle_force_vs_velocity(output_dir):
    max_velocity = _output_deg_per_sec_to_normalized_per_sec(
        Config.MAX_KNOB_OUTPUT_VELOCITY_DEG_PER_SEC,
        Config.THROTTLE_CONTROL_ROTATION_RANGE,
        Config.THROTTLE_TRANSMISSION_RATIO
    )
    velocities = np.linspace(-max_velocity, max_velocity, 500)
    damping = -velocities * Config.THROTTLE_VELOCITY_DAMPING

    fig, ax = plt.subplots(figsize=(9, 5))
    label = "Throttle damping"
    title = "Throttle Damping Force vs. Velocity"
    if Config.THROTTLE_HAPTIC_MODE == Config.HAPTIC_MODE_VIRTUAL_WALLS:
        label = "Throttle wall contact damping"
        title = "Throttle Wall Contact Force vs. Velocity"
    elif Config.THROTTLE_HAPTIC_MODE == Config.HAPTIC_MODE_SPRING_DAMPER_WITH_WALLS:
        label = "Throttle spring-damper damping"
        title = "Throttle Spring-Damper Force vs. Velocity"

    ax.plot(velocities, damping, label=label)
    ax.axhline(0, color="0.55", linewidth=1)
    ax.axvline(0, color="0.55", linewidth=1)
    ax.set_title(title)
    ax.set_xlabel("Normalized throttle velocity / sec")
    ax.set_ylabel("Force command")
    ax.grid(True, alpha=0.3)
    ax.legend()
    return _save(fig, output_dir, "throttle_force_vs_velocity.png")


def _output_deg_per_sec_to_normalized_per_sec(
    output_deg_per_sec,
    control_rotation_range,
    transmission_ratio
):
    encoder_deg_per_sec = output_deg_per_sec * max(0.0, transmission_ratio)
    normalized_denominator = 360.0 * max(0.000001, control_rotation_range)
    return encoder_deg_per_sec / normalized_denominator


def _plot_impulse_effects(output_dir):
    times = np.linspace(0.0, 0.25, 800)
    trail = Config.TRAIL_VIBRATION_AMPLITUDE * np.sin(
        2.0 * np.pi * Config.TRAIL_VIBRATION_FREQ * times
    )
    mine = np.where(times <= Config.MINE_KICKBACK_DURATION, -Config.MINE_KICKBACK_FORCE, 0.0)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(times, trail, label="Trail vibration")
    ax.plot(times, mine, label="Mine kickback")
    ax.axhline(0, color="0.55", linewidth=1)
    ax.set_title("Event Haptic Effects vs. Time")
    ax.set_xlabel("Time (sec)")
    ax.set_ylabel("Force command")
    ax.grid(True, alpha=0.3)
    ax.legend()
    return _save(fig, output_dir, "event_effects_vs_time.png")
