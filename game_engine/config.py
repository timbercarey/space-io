"""
Game configuration and constants
"""

class Config:
    # === Display Settings ===
    WINDOWED_WIDTH = 1280
    WINDOWED_HEIGHT = 720
    WINDOW_WIDTH = WINDOWED_WIDTH
    WINDOW_HEIGHT = WINDOWED_HEIGHT
    FULLSCREEN = False
    WORLD_SCALE = 0.85  # screen pixels per world pixel; lower values zoom out
    FPS = 60
    BACKGROUND_COLOR = (0, 0, 0)  # Black

    @classmethod
    def set_display_size(cls, size):
        cls.WINDOW_WIDTH, cls.WINDOW_HEIGHT = size

    @classmethod
    def playfield_width(cls):
        return cls.WINDOW_WIDTH / cls.WORLD_SCALE

    @classmethod
    def playfield_height(cls):
        return cls.WINDOW_HEIGHT / cls.WORLD_SCALE

    # === Audio Settings ===
    AUDIO_ENABLED = True
    MUSIC_VOLUME = 0.35
    SFX_VOLUME = 0.75
    ENGINE_VOLUME = 0.55
    ENGINE_SPEED_BUCKETS = 48
    ENGINE_CROSSFADE_MS = 140
    ENGINE_MIN_SWITCH_INTERVAL = 0.10
    
    # === Physics Settings ===
    CONTROL_LOOP_FREQUENCY_HZ = 1000.0
    MAX_SPEED = 320.0  # pixels per second
    ACCELERATION = 480.0  # pixels per second^2
    BRAKE_POWER = 2.0  # Multiplier for braking (relative to acceleration, 0.5 = half power, 1.0 = same power)
    TURN_RATE = 230.0  # degrees per second
    DRAG_COEFFICIENT = 0.35  # Linear drag
    
    # === Ship Settings ===
    SHIP_SIZE = 15  # pixels (radius)
    SHIP_COLOR_P1 = (0, 200, 255)  # Cyan
    SHIP_COLOR_P2 = (255, 100, 0)  # Orange
    SHIP_EXPLOSION_DURATION = 1.4  # seconds
    SHIP_EXPLOSION_PARTICLES = 18
    GAME_OVER_RETURN_DELAY = 2.8  # seconds before returning to launch screen
    
    # === Trail Settings ===
    TRAIL_LENGTH = 75  # number of segments
    TRAIL_WIDTH = 2  # pixels
    TRAIL_SEGMENT_SPACING = 5  # pixels between trail points
    TRAIL_COLOR_P1 = (0, 150, 200)  # Darker cyan
    TRAIL_COLOR_P2 = (200, 80, 0)  # Darker orange
    
    # === Game Settings ===
    NUM_STARS = 5
    NUM_MINES = 0
    STAR_SIZE = 10
    MINE_SIZE = 16
    STAR_COLOR = (255, 255, 100)  # Yellow
    STAR_CORE_COLOR = (255, 255, 235)
    STAR_GLOW_COLOR = (255, 225, 90)
    STAR_BREATHE_SPEED = 1.2  # cycles per second
    STAR_BREATHE_AMOUNT = 0.22  # fraction of base size
    STAR_FLICKER_SPEED = 6.5  # cycles per second
    STAR_FLICKER_AMOUNT = 0.18  # fraction of brightness
    MINE_COLOR = (120, 116, 108)  # Gray-brown
    MINE_OUTLINE_COLOR = (195, 188, 174)
    MINE_CRATER_COLOR = (70, 67, 63)
    MINE_FLOAT_MIN_SPEED = 35.0  # pixels per second
    MINE_FLOAT_MAX_SPEED = 85.0  # pixels per second
    MINE_ROTATION_MIN_SPEED = 35.0  # degrees per second
    MINE_ROTATION_MAX_SPEED = 120.0  # degrees per second

    # Difficulty profiles. The pre-game menu selects the initial profile; the
    # 3-way hardware switch can override it live while a game is running.
    DEFAULT_DIFFICULTY = 3
    USE_HARDWARE_DIFFICULTY_SWITCH = True
    DIFFICULTY_PROFILES = {
        1: {
            "name": "easy",
            "max_speed": 320.0,
            "acceleration": 620.0,
            "num_mines": 0,
            "mine_float_min_speed": 0.0,
            "mine_float_max_speed": 0.0,
        },
        2: {
            "name": "medium",
            "max_speed": 320.0,
            "acceleration": 620.0,
            "num_mines": 5,
            "mine_float_min_speed": 18.0,
            "mine_float_max_speed": 42.0,
        },
        3: {
            "name": "hard",
            "max_speed": 320.0,
            "acceleration": 800.0,
            "num_mines": 10,
            "mine_float_min_speed": 35.0,
            "mine_float_max_speed": 200.0,
        },
    }

    # === Spawn Settings ===
    PLAYER_STARTS = {
        1: {"position": (-200, 0), "angle": 0, "style": "x_wing"},
        2: {"position": (200, 0), "angle": 180, "style": "tie_fighter"},
    }
    SPAWN_SAFE_ZONE_MARGIN = 140  # Radius in pixels around each starting position
    SPAWN_SAFE_ZONE_ENABLED = True  # Enable/disable safe zone

    # === Debug Settings ===
    SHOW_HITBOXES = False  # Show ship collision circles

    # === Two-player Settings ===
    BEST_OF_ROUNDS = 7  # Best of 7 rounds
    RESPAWN_DELAY = 3.0  # Seconds before the next two-player round starts
    
    # === Boost Settings ===
    BOOST_DURATION = 5.0  # seconds
    BOOST_SPEED_MULTIPLIER = 2.35
    BOOST_ACCELERATION_MULTIPLIER = 2.2
    BOOST_TRAIL_LENGTH_MULTIPLIER = 2.0
    BOOST_COOLDOWN = 1.0  # seconds after boost ends
    BOOST_THROTTLE_IMPULSE_FORCE = 220
    BOOST_THROTTLE_IMPULSE_DURATION = 0.14  # seconds
    
    # === Haptics Settings ===
    SERIAL_PORT = '/dev/cu.usbmodem199646501'  # Change to 'COM3' on Windows
    BAUD_RATE = 1000000
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
    STEERING_VELOCITY_DAMPING = 20.0
    STEERING_DAMPING_FORCE_LIMIT = 500.0
    STEERING_DAMPING_VELOCITY_CAP_ENABLED = False
    STEERING_DAMPING_VELOCITY_LIMIT = 2.0
    KNOB_VELOCITY_THREAD_FREQUENCY_HZ = 1000.0
    KNOB_VELOCITY_FILTER_ALPHA = 0.45
    KNOB_VELOCITY_MIN_SAMPLE_INTERVAL_SEC = 0.006
    KNOB_VELOCITY_POSITION_NOISE_DEADBAND = 0.0005
    KNOB_VELOCITY_ZERO_DEADBAND = 0.005
    KNOB_VELOCITY_STALE_TIMEOUT_SEC = 0.035
    HARDWARE_VELOCITY_STALE_REJECTION_ENABLED = True
    HARDWARE_VELOCITY_STALE_TIMEOUT_SEC = 0.020
    KNOB_VELOCITY_PLOT_WINDOW_SEC = 5.0
    KNOB_VELOCITY_PLOT_LIMIT_DEG_PER_SEC = 180.0
    STEERING_FORCE_COMPONENT_PLOT_LIMIT = 1500.0
    MAX_KNOB_OUTPUT_VELOCITY_DEG_PER_SEC = 540.0
    MAX_KNOB_ACCELERATION = 0.0  # 0 disables acceleration limiting to avoid damping phase lag

    # Dormant speed scaling for future damping tuning
    SPEED_DAMPING_SCALING_ENABLED = False
    MIN_DAMPING = 50.0
    MAX_DAMPING = 500.0
    DAMPING_SPEED_THRESHOLD = MAX_SPEED * 0.8

    # Virtual walls limit centered knob motion
    HAPTIC_MODE_OFF = "off"
    HAPTIC_MODE_SPRING_ONLY = "spring_only"
    HAPTIC_MODE_DAMPER_ONLY = "damper_only"
    HAPTIC_MODE_VIRTUAL_WALLS = "virtual_walls"
    HAPTIC_MODE_SPRING_DAMPER = "spring_damper"
    HAPTIC_MODE_SPRING_DAMPER_WITH_WALLS = "spring_damper_with_walls"
    # Steering
    STEERING_HAPTIC_MODE = HAPTIC_MODE_SPRING_DAMPER
    STEERING_MOTION_RANGE_DEG = 270.0
    STEERING_VIRTUAL_WALL_STIFFNESS = 8000.0
    STEERING_VIRTUAL_WALL_INTO_WALL_DAMPING = 0.0
    STEERING_WALL_DAMPING_VELOCITY_HYSTERESIS_ENABLED = True
    STEERING_WALL_DAMPING_VELOCITY_ENTER_THRESHOLD = 0.04
    STEERING_WALL_DAMPING_VELOCITY_EXIT_THRESHOLD = 0.015
    STEERING_WALL_DAMPING_MIN_PENETRATION_ENABLED = True
    STEERING_WALL_DAMPING_MIN_PENETRATION = 0.005
    STEERING_WALL_DAMPING_PENETRATION_RAMP_ENABLED = True
    STEERING_WALL_DAMPING_RAMP_PENETRATION = 0.035
    STEERING_CENTERING_SPRING_STIFFNESS = 800.0
    # Throttle
    THROTTLE_HAPTIC_MODE_VIRTUAL_WALLS = HAPTIC_MODE_VIRTUAL_WALLS
    THROTTLE_HAPTIC_MODE_SPRING_DAMPER = HAPTIC_MODE_SPRING_DAMPER
    THROTTLE_HAPTIC_MODE_SPRING_DAMPER_WITH_WALLS = HAPTIC_MODE_SPRING_DAMPER_WITH_WALLS
    THROTTLE_HAPTIC_MODE = THROTTLE_HAPTIC_MODE_VIRTUAL_WALLS
    THROTTLE_MOTION_RANGE_DEG = 360.0
    BOOST_THROTTLE_FORWARD_EXTENSION_DEG = 120.0
    THROTTLE_VIRTUAL_WALL_STIFFNESS = 4000.0
    THROTTLE_CENTERING_SPRING_STIFFNESS = 150.0
    THROTTLE_BOOST_PUSH_THROUGH_ENABLED = True
    THROTTLE_BOOST_PUSH_THROUGH_WIDTH_DEG = 12.0
    THROTTLE_BOOST_PUSH_THROUGH_STIFFNESS = 2200.0
    THROTTLE_POSITION_PULSE_ENABLED = True
    THROTTLE_POSITION_PULSE_BRAKE_WALL_BUFFER = 0.04
    THROTTLE_POSITION_PULSE_MIN_FORCE = 80.0
    THROTTLE_POSITION_PULSE_MAX_FORCE = 260.0
    THROTTLE_POSITION_PULSE_BURST_FREQ = 180.0
    THROTTLE_POSITION_PULSE_WIDTH_SEC = 0.040
    THROTTLE_POSITION_PULSE_MIN_INTERVAL_SEC = 0.010
    THROTTLE_POSITION_PULSE_MAX_INTERVAL_SEC = 0.070

    DAMPING_EFFECTS = [
        "Steering baseline damping: always-on viscous steering damping from normalized knob velocity.",
        "Steering damping force cap: clamps total steering damping force without limiting spring or elastic wall force.",
        "Steering damping velocity cap: clips the velocity used by steering damping without adding low-pass phase lag.",
        "Steering into-wall damping: adds damping only while steering is penetrating a wall and moving deeper into it.",
        "Steering wall velocity hysteresis: gates into-wall damping with separate enter/exit outward-speed thresholds.",
        "Steering wall minimum penetration: suppresses extra wall damping until the knob is meaningfully past the wall.",
        "Steering wall penetration ramp: fades extra wall damping in over a configurable penetration distance.",
        "Throttle baseline damping: viscous throttle damping used by throttle damper and wall-contact modes.",
        "Throttle position pulse interval modulation: short throttle pulses become more frequent as throttle position moves farther from neutral.",
    ]

    VELOCITY_PROCESSING_EFFECTS = [
        "Teensy adaptive velocity window: estimates velocity after enough encoder counts or elapsed time accumulate.",
        "Teensy time-constant velocity filter: keeps filter behavior stable under control-loop timing jitter.",
        "Teensy asymmetric velocity filter: responds faster to acceleration and direction changes than to decay.",
        "Teensy zero hysteresis: uses separate enter/exit thresholds to avoid velocity chatter around zero.",
        "Teensy stale velocity decay: smoothly decays held velocity when counts stop changing.",
        "Teensy velocity sample age: sends VEL_AGE_US so the host can reject stale hardware velocity.",
        "Host hardware stale rejection: ignores hardware velocity packets older than the configured timeout.",
        "Host fallback estimator: estimates velocity from normalized position changes when hardware velocity is unavailable.",
    ]
    
    # Trail collision vibration
    TRAIL_VIBRATION_ENABLED = False
    TRAIL_VIBRATION_FREQ = 50  # Hz
    TRAIL_VIBRATION_AMPLITUDE = 300
    
    # Mine collision
    MINE_KICKBACK_FORCE = 800
    MINE_KICKBACK_DURATION = 0.2  # seconds
    MINE_STEERING_VIBRATION_FREQ = 45  # Hz
    MINE_STEERING_VIBRATION_AMPLITUDE = 350
    ASTEROID_BOUNCE_SPEED = 360.0  # minimum pixels per second away from asteroid
    ASTEROID_BOUNCE_COOLDOWN = 0.35  # seconds before same ship can bounce again
    ASTEROID_BOUNCE_STEERING_VIBRATION_FREQ = 45  # Hz
    ASTEROID_BOUNCE_STEERING_FORCE = 500
    ASTEROID_BOUNCE_THROTTLE_FORCE = -700
    ASTEROID_BOUNCE_FORCE_DURATION = 0.16  # seconds
    
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
