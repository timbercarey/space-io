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
    MAX_SPEED = 400.0  # pixels per second
    ACCELERATION = 300.0  # pixels per second^2
    BRAKE_POWER = 0.8  # Multiplier for braking (relative to acceleration, 0.5 = half power, 1.0 = same power)
    TURN_RATE = 180.0  # degrees per second
    DRAG_COEFFICIENT = 0.5  # Linear drag
    
    # === Ship Settings ===
    SHIP_SIZE = 20  # pixels (radius)
    SHIP_COLOR_P1 = (0, 200, 255)  # Cyan
    SHIP_COLOR_P2 = (255, 100, 0)  # Orange
    
    # === Trail Settings ===
    TRAIL_LENGTH = 100  # number of segments
    TRAIL_WIDTH = 3  # pixels
    TRAIL_SEGMENT_SPACING = 5  # pixels between trail points
    TRAIL_COLOR_P1 = (0, 150, 200)  # Darker cyan
    TRAIL_COLOR_P2 = (200, 80, 0)  # Darker orange
    
    # === Game Objects ===
    NUM_STARS = 5
    NUM_MINES = 8
    STAR_SIZE = 15
    MINE_SIZE = 12
    STAR_COLOR = (255, 255, 100)  # Yellow
    MINE_COLOR = (255, 50, 50)  # Red
    
    # === Boost Settings ===
    BOOST_DURATION = 2.0  # seconds
    BOOST_SPEED_MULTIPLIER = 2.0
    BOOST_COOLDOWN = 1.0  # seconds after boost ends
    
    # === Haptics Settings ===
    SERIAL_PORT = '/dev/ttyUSB0'  # Change to 'COM3' on Windows
    BAUD_RATE = 115200
    SIMULATION_MODE = True  # Set to False when hardware is connected
    
    # === Force Parameters ===
    # Damping increases with speed
    MIN_DAMPING = 0.0
    MAX_DAMPING = 500.0
    DAMPING_SPEED_THRESHOLD = MAX_SPEED * 0.8
    
    # Trail collision vibration
    TRAIL_VIBRATION_FREQ = 50  # Hz
    TRAIL_VIBRATION_AMPLITUDE = 300
    
    # Mine collision
    MINE_KICKBACK_FORCE = 800
    MINE_KICKBACK_DURATION = 0.2  # seconds
    
    # Boost activation
    BOOST_WALL_STIFFNESS = 500
    BOOST_WALL_POSITION = 0.8  # Normalized (0 to 1)
    
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