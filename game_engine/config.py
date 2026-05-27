"""
Game configuration and constants
"""

class Config:
    # === Display Settings ===
    WINDOW_WIDTH = 1280
    WINDOW_HEIGHT = 720
    FPS = 60
    BACKGROUND_COLOR = (0, 0, 0)  # Black
    
    # === Physics Settings ===
    CONTROL_LOOP_FREQUENCY_HZ = 1000.0
    MAX_SPEED = 400.0  # pixels per second
    ACCELERATION = 300.0  # pixels per second^2
    BRAKE_POWER = 1.2  # Multiplier for braking (relative to acceleration, 0.5 = half power, 1.0 = same power)
    TURN_RATE = 180.0  # degrees per second
    DRAG_COEFFICIENT = 0.5  # Linear drag
    
    # === Ship Settings ===
    SHIP_SIZE = 15  # pixels (radius)
    SHIP_COLOR_P1 = (0, 200, 255)  # Cyan
    SHIP_COLOR_P2 = (255, 100, 0)  # Orange
    
    # === Trail Settings ===
    TRAIL_LENGTH = 5  # number of segments
    TRAIL_WIDTH = 3  # pixels
    TRAIL_SEGMENT_SPACING = 5  # pixels between trail points
    TRAIL_COLOR_P1 = (0, 150, 200)  # Darker cyan
    TRAIL_COLOR_P2 = (200, 80, 0)  # Darker orange
    
    # === Game Settings ===
    NUM_STARS = 8
    NUM_MINES = 1
    STAR_SIZE = 10
    MINE_SIZE = 10
    STAR_COLOR = (255, 255, 100)  # Yellow
    MINE_COLOR = (255, 50, 50)  # Red

    # === Spawn Settings ===
    SPAWN_SAFE_ZONE_MARGIN = 50  # Pixels of safe zone around starting positions
    SPAWN_SAFE_ZONE_ENABLED = True  # Enable/disable safe zone

    # === Debug Settings ===
    SHOW_HITBOXES = False  # Show ship collision circles

    # === Two-player Settings ===
    BEST_OF_ROUNDS = 3  # Best of 3 rounds
    RESPAWN_DELAY = 1.0  # Seconds before new round starts (future feature)
    
    # === Boost Settings ===
    BOOST_DURATION = 2.0  # seconds
    BOOST_SPEED_MULTIPLIER = 2.0
    BOOST_COOLDOWN = 1.0  # seconds after boost ends
    
    # === Haptics Settings ===
    SERIAL_PORT = '/dev/cu.usbmodem199646501'  # Change to 'COM3' on Windows
    BAUD_RATE = 115200
    SIMULATION_MODE = False  # Set to False when hardware is connected
    SHOW_HAPTIC_PANEL = True  # Set to False to hide haptic visualization panels
    SHOW_KNOB_VELOCITY_PLOT = True
    GENERATE_HAPTIC_DEBUG_PLOTS = False
    HAPTIC_DEBUG_PLOT_DIR = "debug_plots/haptics"

    # === Encoder Settings ===
    STEERING_ENCODER_COUNTS_PER_ROTATION = 4000
    THROTTLE_ENCODER_COUNTS_PER_ROTATION = 25000
    STEERING_ENCODER_DIRECTION = 1
    THROTTLE_ENCODER_DIRECTION = -1
    STEERING_CONTROL_ROTATION_RANGE = 0.5  # +/- rotations maps to normalized +/-1.0
    THROTTLE_CONTROL_ROTATION_RANGE = 1.0  # +/- rotations maps to normalized +/-1.0
    STEERING_TRANSMISSION_RATIO = 1.0
    THROTTLE_TRANSMISSION_RATIO = (
        THROTTLE_ENCODER_COUNTS_PER_ROTATION / STEERING_ENCODER_COUNTS_PER_ROTATION
    )

    # Hardware motor force signs. Flip an axis here if force pushes away from center.
    STEERING_FORCE_DIRECTION = 1
    THROTTLE_FORCE_DIRECTION = -1
    
    # === Force Parameters ===
    # Throttle velocity damping
    THROTTLE_VELOCITY_DAMPING = 120.0
    # Steering velocity damping
    STEERING_VELOCITY_DAMPING = 600.0
    KNOB_VELOCITY_THREAD_FREQUENCY_HZ = 1000.0
    KNOB_VELOCITY_FILTER_ALPHA = 0.45
    KNOB_VELOCITY_MIN_SAMPLE_INTERVAL_SEC = 0.006
    KNOB_VELOCITY_POSITION_NOISE_DEADBAND = 0.0005
    KNOB_VELOCITY_ZERO_DEADBAND = 0.005
    KNOB_VELOCITY_STALE_TIMEOUT_SEC = 0.035
    KNOB_VELOCITY_PLOT_WINDOW_SEC = 5.0
    KNOB_VELOCITY_PLOT_LIMIT_DEG_PER_SEC = 180.0
    STEERING_FORCE_COMPONENT_PLOT_LIMIT = 1000.0
    MAX_KNOB_OUTPUT_VELOCITY_DEG_PER_SEC = 540.0
    MAX_KNOB_ACCELERATION = 0.0  # 0 disables acceleration limiting to avoid damping phase lag

    # Dormant speed scaling for future damping tuning
    SPEED_DAMPING_SCALING_ENABLED = False
    MIN_DAMPING = 50.0
    MAX_DAMPING = 500.0
    DAMPING_SPEED_THRESHOLD = MAX_SPEED * 0.8

    # Virtual walls limit centered knob motion
    HAPTIC_MODE_VIRTUAL_WALLS = "virtual_walls"
    HAPTIC_MODE_SPRING_DAMPER = "spring_damper"
    HAPTIC_MODE_SPRING_DAMPER_WITH_WALLS = "spring_damper_with_walls"
    # Steering
    STEERING_HAPTIC_MODE = HAPTIC_MODE_SPRING_DAMPER
    STEERING_MOTION_RANGE_DEG = 270.0
    STEERING_VIRTUAL_WALL_STIFFNESS = 2500.0
    STEERING_CENTERING_SPRING_STIFFNESS = 300.0
    # Throttle
    THROTTLE_HAPTIC_MODE_VIRTUAL_WALLS = HAPTIC_MODE_VIRTUAL_WALLS
    THROTTLE_HAPTIC_MODE_SPRING_DAMPER = HAPTIC_MODE_SPRING_DAMPER
    THROTTLE_HAPTIC_MODE_SPRING_DAMPER_WITH_WALLS = HAPTIC_MODE_SPRING_DAMPER_WITH_WALLS
    THROTTLE_HAPTIC_MODE = HAPTIC_MODE_SPRING_DAMPER_WITH_WALLS
    THROTTLE_MOTION_RANGE_DEG = 360.0
    BOOST_THROTTLE_FORWARD_EXTENSION_DEG = 120.0
    THROTTLE_VIRTUAL_WALL_STIFFNESS = 4000.0
    THROTTLE_CENTERING_SPRING_STIFFNESS = 150.0
    THROTTLE_BOOST_PUSH_THROUGH_ENABLED = True
    THROTTLE_BOOST_PUSH_THROUGH_WIDTH_DEG = 12.0
    THROTTLE_BOOST_PUSH_THROUGH_STIFFNESS = 2200.0
    
    # Trail collision vibration
    TRAIL_VIBRATION_FREQ = 50  # Hz
    TRAIL_VIBRATION_AMPLITUDE = 300
    
    # Mine collision
    MINE_KICKBACK_FORCE = 800
    MINE_KICKBACK_DURATION = 0.2  # seconds
    
    # === Input Settings ===
    # Keyboard controls for simulation
    # Player 1
    P1_STEER_LEFT = 'a'
    P1_STEER_RIGHT = 'd'
    P1_THROTTLE_UP = 'w'
    P1_THROTTLE_DOWN = 's'
    
    # Player 2
    P2_STEER_LEFT = 'left'
    P2_STEER_RIGHT = 'right'
    P2_THROTTLE_UP = 'up'
    P2_THROTTLE_DOWN = 'down'
    
    # === Control Mapping ===
    # Map normalized input (-1 to 1) to game values
    STEERING_SENSITIVITY = -1.0  # Multiplier for steering input
    THROTTLE_SENSITIVITY = 1.0  # Multiplier for throttle input
