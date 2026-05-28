"""
Spaceship entity - represents a player's ship
"""
import math
import random
from utils import Vector2
from config import Config

class Spaceship:
    def __init__(self, player_id, start_position, start_angle=0, ship_style=None):
        """
        Args:
            player_id: 1 or 2
            start_position: Vector2
            start_angle: degrees (0 = pointing right)
        """
        self.player_id = player_id
        self.ship_style = ship_style
        self.position = start_position
        self.velocity = Vector2(0, 0)
        self.angle = start_angle  # degrees
        
        self.alive = True
        self.exploding = False
        self.explosion_timer = 0.0
        self.explosion_particles = []
        self.trail_segments = []  # List of trail segments (each segment is a list of Vector2)
        self.current_segment = []  # Current active trail segment
        
        # Boost state
        self.boost_active = False
        self.boost_timer = 0.0
        self.boost_cooldown_timer = 0.0
        self.asteroid_bounce_cooldown_timer = 0.0
        
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

        if self.asteroid_bounce_cooldown_timer > 0:
            self.asteroid_bounce_cooldown_timer -= dt
        
        # Steering - rotate the ship
        turn_amount = steering_input * Config.TURN_RATE * Config.STEERING_SENSITIVITY * dt
        self.angle += turn_amount
        
        # Keep angle in 0-360 range
        self.angle = self.angle % 360
        
        # Throttle - handle acceleration and braking
        if throttle_input > 0:
            # Accelerate forward in the direction ship is facing
            forward_direction = Vector2.from_angle(self.angle)
            acceleration_power = Config.ACCELERATION
            if self.boost_active:
                acceleration_power *= Config.BOOST_ACCELERATION_MULTIPLIER
            acceleration = forward_direction * (throttle_input * acceleration_power * Config.THROTTLE_SENSITIVITY)
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
        playfield_width = Config.playfield_width()
        playfield_height = Config.playfield_height()

        if self.position.x < -playfield_width / 2:
            self.position.x += playfield_width
            wrapped = True
        elif self.position.x > playfield_width / 2:
            self.position.x -= playfield_width
            wrapped = True
        
        if self.position.y < -playfield_height / 2:
            self.position.y += playfield_height
            wrapped = True
        elif self.position.y > playfield_height / 2:
            self.position.y -= playfield_height
            wrapped = True
        
        # Update trail (pass wrapped flag)
        self._update_trail(wrapped)

    def _update_trail(self, wrapped=False):
        """
        Add current exhaust position to trail and maintain trail length
        
        Args:
            wrapped: True if ship just wrapped around screen edge
        """
        trail_position = self.get_trail_origin()

        # If we wrapped, save current segment and start a new one
        if wrapped:
            # Add current exhaust position to the segment before saving it
            if len(self.current_segment) == 0 or trail_position.distance_to(self.current_segment[-1]) >= Config.TRAIL_SEGMENT_SPACING:
                self.current_segment.append(trail_position)
            
            # Save the current segment if it has points
            if len(self.current_segment) > 0:
                self.trail_segments.append(self.current_segment)
                self.current_segment = []
            self._trim_trail()
            return
        
        # Only add to trail if ship has moved enough
        if len(self.current_segment) == 0 or trail_position.distance_to(self.current_segment[-1]) >= Config.TRAIL_SEGMENT_SPACING:
            self.current_segment.append(trail_position)
        
        self._trim_trail()

    def _trail_length_limit(self):
        """Return the active trail point budget."""
        multiplier = (
            Config.BOOST_TRAIL_LENGTH_MULTIPLIER
            if self.boost_active
            else 1.0
        )
        return max(1, int(Config.TRAIL_LENGTH * multiplier))

    def _trim_trail(self):
        """Remove oldest trail points until the active trail budget is met."""
        trail_length_limit = self._trail_length_limit()
        total_points = sum(len(seg) for seg in self.trail_segments) + len(self.current_segment)
        while total_points > trail_length_limit:
            if len(self.trail_segments) == 0:
                if len(self.current_segment) == 0:
                    return
                self.current_segment.pop(0)
                total_points -= 1
                continue

            if len(self.trail_segments[0]) > 0:
                self.trail_segments[0].pop(0)
                total_points -= 1
                if len(self.trail_segments[0]) == 0:
                    self.trail_segments.pop(0)
            else:
                self.trail_segments.pop(0)

    def get_trail_origin(self):
        """Return the rear edge of the ship hitbox, where exhaust begins."""
        rear_direction = Vector2.from_angle(self.angle) * -1
        origin = self.position + rear_direction * Config.SHIP_SIZE
        return Vector2(origin.x, origin.y)
    
    def activate_boost(self):
        """Activate or refresh boost from collecting a star."""
        self.boost_active = True
        self.boost_timer = Config.BOOST_DURATION
        self.boost_cooldown_timer = 0.0
        return True

    def can_bounce_off_asteroid(self):
        """Return whether boost can turn asteroid contact into a bounce."""
        return self.boost_active and self.asteroid_bounce_cooldown_timer <= 0

    def bounce_off_asteroid(self, asteroid):
        """Reflect velocity away from an asteroid and separate from overlap."""
        normal = self.position - asteroid.position
        if normal.length() == 0:
            if self.velocity.length() > 0:
                normal = self.velocity.normalized() * -1
            else:
                normal = Vector2.from_angle(self.angle)
        else:
            normal = normal.normalized()

        contact_distance = Config.SHIP_SIZE + asteroid.size + 1
        self.position = asteroid.position + normal * contact_distance

        relative_velocity = self.velocity - asteroid.velocity
        impact_speed = relative_velocity.dot(normal)
        if impact_speed < 0:
            relative_velocity = relative_velocity - normal * (2 * impact_speed)

        self.velocity = relative_velocity + asteroid.velocity

        away_speed = (self.velocity - asteroid.velocity).dot(normal)
        if away_speed < Config.ASTEROID_BOUNCE_SPEED:
            self.velocity = self.velocity + normal * (Config.ASTEROID_BOUNCE_SPEED - away_speed)

        max_speed = Config.MAX_SPEED * Config.BOOST_SPEED_MULTIPLIER
        if self.velocity.length() > max_speed:
            self.velocity = self.velocity.normalized() * max_speed

        self.asteroid_bounce_cooldown_timer = Config.ASTEROID_BOUNCE_COOLDOWN
        return normal
    
    def kill(self):
        """Kill the ship"""
        self.alive = False
        self.velocity = Vector2(0, 0)

    def start_explosion(self):
        """Start a short visual explosion at the ship position."""
        self.exploding = True
        self.explosion_timer = Config.SHIP_EXPLOSION_DURATION
        self.explosion_particles = []

        for _ in range(Config.SHIP_EXPLOSION_PARTICLES):
            direction = Vector2.from_angle(random.uniform(0, 360))
            self.explosion_particles.append({
                "direction": direction,
                "speed": random.uniform(80, 260),
                "size": random.uniform(2, 5),
                "color": random.choice((
                    (255, 245, 180),
                    (255, 150, 50),
                    (255, 70, 40),
                    (180, 210, 255),
                ))
            })

    def update_explosion(self, dt):
        """Update explosion lifetime."""
        if not self.exploding:
            return

        self.explosion_timer -= dt
        if self.explosion_timer <= 0:
            self.explosion_timer = 0.0
            self.exploding = False
    
    def get_triangle_points(self):
        """Get the three points of the ship triangle for rendering"""
        # Ship is an isoceles triangle pointing in the direction of angle
        size = Config.SHIP_SIZE
        
        # Front point
        front = Vector2.from_angle(self.angle) * size
        
        # Back two points
        back_left = Vector2.from_angle(self.angle + 130) * (size * 0.9)
        back_right = Vector2.from_angle(self.angle - 130) * (size * 0.9)
        
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
