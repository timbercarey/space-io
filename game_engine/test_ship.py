"""
Simple test of spaceship mechanics
"""
from entities.spaceship import Spaceship
from utils import Vector2
from config import Config

def test_ship():
    # Create a ship
    ship = Spaceship(player_id=1, start_position=Vector2(0, 0), start_angle=0)
    
    print(f"Initial position: {ship.position}")
    print(f"Initial angle: {ship.angle}")
    
    # Simulate some movement
    dt = 1.0 / 60.0  # 60 FPS
    
    # Turn right and accelerate for 1 second
    for i in range(60):
        ship.update(steering_input=0.5, throttle_input=1.0, dt=dt)
    
    print(f"\nAfter 1 second of right turn + full throttle:")
    print(f"Position: {ship.position}")
    print(f"Velocity: {ship.velocity}")
    print(f"Angle: {ship.angle}")
    print(f"Trail length: {len(ship.trail)}")
    
    # Test boost
    ship.activate_boost()
    print(f"\nBoost active: {ship.boost_active}")
    
    # Run for another second with boost
    for i in range(60):
        ship.update(steering_input=0, throttle_input=1.0, dt=dt)
    
    print(f"\nAfter 1 second of boost:")
    print(f"Speed: {ship.velocity.length():.2f}")
    print(f"Boost still active: {ship.boost_active}")

if __name__ == "__main__":
    test_ship()