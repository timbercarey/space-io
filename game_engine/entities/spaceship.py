"""
Spaceship entity - represents a player's ship
"""
import math
from utils import Vector2
from config import Config

class Spaceship:
    def __init__(self, player_id, start_position, start_angle=0):
        """
        Args:
            player_id: 1 or 2
            start_position: Vector2
            start_angle: degrees (0 = pointing right)
        """
        self.player_id = player_id
        self.position = start_position
        self.velocity = Vector2(0, 0)
        self.angle = start_angle  # degrees
        
        self.alive = True
        self.trail_segments = []  # List of trail segments (each segment is a list of Vector2)
        self.current_segment = []  # Current active trail segment
        
        # Boost state
        self.boost_active = False
        self.boost_timer = 0.0
        self.boost_cooldown_timer = 0.0
        
        # Visual properties
        if player_id == 1:
            self.color = Config.SHIP_COLOR_P1
            self.trail_color = Config.TRAIL_COLOR_P1
        else:
            self.color = Config.SHIP_COLOR_P2
            self.trail_color = Config.TRAIL_COLOR_P2
    
    def update(self, steering_input, throttle_input, dt):
        """
        Update ship physics
        
        Args:
            steering_input: -1 to 1 (left to right)
            throttle_input: -1 to 1 (back to forward, negative = brake)
            dt: delta time in seconds
        """
        if not self.alive:
            return
        
        # Update boost timers
        if self.boost_active:
            self.boost_timer -= dt
            if self.boost_timer <= 0:
                self.boost_active = False
                self.boost_cooldown_timer = Config.BOOST_COOLDOWN
        
        if self.boost_cooldown_timer > 0:
            self.boost_cooldown_timer -= dt
        
        # Steering - rotate the ship
        turn_amount = steering_input * Config.TURN_RATE * Config.STEERING_SENSITIVITY * dt
        self.angle += turn_amount
        
        # Keep angle in 0-360 range
        self.angle = self.angle % 360
        
        # Throttle - handle acceleration and braking
        if throttle_input > 0:
            # Accelerate forward in the direction ship is facing
            forward_direction = Vector2.from_angle(self.angle)
            acceleration = forward_direction * (throttle_input * Config.ACCELERATION * Config.THROTTLE_SENSITIVITY)
            self.velocity = self.velocity + acceleration * dt
        elif throttle_input < 0:
            # Brake - apply opposite force to velocity direction
            if self.velocity.length() > 0:
                brake_force = self.velocity.normalized() * (abs(throttle_input) * Config.ACCELERATION * Config.BRAKE_POWER)
                self.velocity = self.velocity - brake_force * dt
                
                # Stop completely if velocity is very low
                if self.velocity.length() < 10:
                    self.velocity = Vector2(0, 0)
        
        # Apply drag
        drag = self.velocity * Config.DRAG_COEFFICIENT * dt
        self.velocity = self.velocity - drag
        
        # Speed limit (boosted or normal)
        max_speed = Config.MAX_SPEED
        if self.boost_active:
            max_speed *= Config.BOOST_SPEED_MULTIPLIER
        
        if self.velocity.length() > max_speed:
            self.velocity = self.velocity.normalized() * max_speed
        
        # Store old position to detect wrapping
        old_position = Vector2(self.position.x, self.position.y)
        
        # Update position
        self.position = self.position + self.velocity * dt
        
        # Screen wrapping - detect if wrapping occurred
        wrapped = False
        if self.position.x < -Config.WINDOW_WIDTH / 2:
            self.position.x += Config.WINDOW_WIDTH
            wrapped = True
        elif self.position.x > Config.WINDOW_WIDTH / 2:
            self.position.x -= Config.WINDOW_WIDTH
            wrapped = True
        
        if self.position.y < -Config.WINDOW_HEIGHT / 2:
            self.position.y += Config.WINDOW_HEIGHT
            wrapped = True
        elif self.position.y > Config.WINDOW_HEIGHT / 2:
            self.position.y -= Config.WINDOW_HEIGHT
            wrapped = True
        
        # Update trail (pass wrapped flag)
        self._update_trail(wrapped)

    def _update_trail(self, wrapped=False):
        """
        Add current position to trail and maintain trail length
        
        Args:
            wrapped: True if ship just wrapped around screen edge
        """
        # If we wrapped, save current segment and start a new one
        if wrapped:
            # Add current position to the segment before saving it
            if len(self.current_segment) == 0 or self.position.distance_to(self.current_segment[-1]) >= Config.TRAIL_SEGMENT_SPACING:
                self.current_segment.append(Vector2(self.position.x, self.position.y))
            
            # Save the current segment if it has points
            if len(self.current_segment) > 0:
                self.trail_segments.append(self.current_segment)
                self.current_segment = []
            return
        
        # Only add to trail if ship has moved enough
        if len(self.current_segment) == 0 or self.position.distance_to(self.current_segment[-1]) >= Config.TRAIL_SEGMENT_SPACING:
            self.current_segment.append(Vector2(self.position.x, self.position.y))
        
        # Limit current segment length
        if len(self.current_segment) > Config.TRAIL_LENGTH:
            self.current_segment.pop(0)
        
        # Gradually remove points from old segments to make them decay
        total_points = sum(len(seg) for seg in self.trail_segments) + len(self.current_segment)
        while total_points > Config.TRAIL_LENGTH and len(self.trail_segments) > 0:
            # Remove from oldest segment first
            if len(self.trail_segments[0]) > 0:
                self.trail_segments[0].pop(0)
                total_points -= 1
                
                # If segment is empty, remove it completely
                if len(self.trail_segments[0]) == 0:
                    self.trail_segments.pop(0)
            else:
                # Empty segment, just remove it
                self.trail_segments.pop(0)
    
    def activate_boost(self):
        """Activate boost if available"""
        if not self.boost_active and self.boost_cooldown_timer <= 0:
            self.boost_active = True
            self.boost_timer = Config.BOOST_DURATION
            return True
        return False
    
    def kill(self):
        """Kill the ship"""
        self.alive = False
        self.velocity = Vector2(0, 0)
    
    def get_triangle_points(self):
        """Get the three points of the ship triangle for rendering"""
        # Ship is an isoceles triangle pointing in the direction of angle
        size = Config.SHIP_SIZE
        
        # Front point
        front = Vector2.from_angle(self.angle) * size
        
        # Back two points
        back_left = Vector2.from_angle(self.angle + 150) * (size * 0.6)
        back_right = Vector2.from_angle(self.angle - 150) * (size * 0.6)
        
        # Convert to screen coordinates
        points = [
            (self.position + front).to_tuple(),
            (self.position + back_left).to_tuple(),
            (self.position + back_right).to_tuple()
        ]
        
        return points
    
    def get_all_trail_points(self):
        """
        Get all trail points from all segments for collision detection
        
        Returns:
            list: All Vector2 trail points
        """
        all_points = []
        for segment in self.trail_segments:
            all_points.extend(segment)
        all_points.extend(self.current_segment)
        return all_points