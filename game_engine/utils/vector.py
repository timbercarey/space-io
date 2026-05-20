"""
2D Vector math utilities
"""
import math

class Vector2:
    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)
    
    def __add__(self, other):
        return Vector2(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other):
        return Vector2(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar):
        return Vector2(self.x * scalar, self.y * scalar)
    
    def __truediv__(self, scalar):
        return Vector2(self.x / scalar, self.y / scalar)
    
    def __repr__(self):
        return f"Vector2({self.x:.2f}, {self.y:.2f})"
    
    def length(self):
        return math.sqrt(self.x ** 2 + self.y ** 2)
    
    def length_squared(self):
        return self.x ** 2 + self.y ** 2
    
    def normalized(self):
        length = self.length()
        if length == 0:
            return Vector2(0, 0)
        return Vector2(self.x / length, self.y / length)
    
    def dot(self, other):
        return self.x * other.x + self.y * other.y
    
    def distance_to(self, other):
        return (self - other).length()
    
    def rotate(self, angle_degrees):
        """Rotate vector by angle in degrees"""
        angle_rad = math.radians(angle_degrees)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        return Vector2(
            self.x * cos_a - self.y * sin_a,
            self.x * sin_a + self.y * cos_a
        )
    
    def to_tuple(self):
        """Convert to tuple for pygame"""
        return (self.x, self.y)
    
    @staticmethod
    def from_angle(angle_degrees):
        """Create unit vector from angle"""
        angle_rad = math.radians(angle_degrees)
        return Vector2(math.cos(angle_rad), math.sin(angle_rad))