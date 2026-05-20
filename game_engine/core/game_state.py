"""
Central game state management
"""
import random
from utils import Vector2
from config import Config
from entities import Spaceship, Star, Mine

class GameState:
    def __init__(self, num_players=1):
        """
        Args:
            num_players: 1 or 2
        """
        self.num_players = num_players
        self.running = True
        self.paused = False
        self.fps = 60
        
        # Scores
        self.scores = {1: 0, 2: 0}
        self.kills = {1: 0, 2: 0}  # Track kills in PvP
        
        # Create ships
        self.ships = {}
        if num_players >= 1:
            self.ships[1] = Spaceship(
                player_id=1,
                start_position=Vector2(-200, 0),
                start_angle=0
            )
        if num_players >= 2:
            self.ships[2] = Spaceship(
                player_id=2,
                start_position=Vector2(200, 0),
                start_angle=180
            )
        
        # Create stars and mines
        self.stars = self._spawn_stars()
        self.mines = self._spawn_mines()
        
        # Game state
        self.game_over = False
        self.winner = None
        self.round_number = 1
        self.best_of = Config.BEST_OF_ROUNDS if hasattr(Config, 'BEST_OF_ROUNDS') else 3

        # Round countdown
        self.countdown_active = False
        self.countdown_timer = 0.0
        self.countdown_duration = 3.0  # 3 second countdown
    
    def _spawn_mines(self):
        """Spawn mines at random positions, avoiding spawn area"""
        mines = []
        
        if not Config.SPAWN_SAFE_ZONE_ENABLED:
            # Safe zone disabled, spawn anywhere
            for _ in range(Config.NUM_MINES):
                mines.append(Mine(self._random_position(margin=100)))
            return mines
        
        # Define safe zone (rectangle around both starting positions)
        # P1 starts at (-200, 0), P2 starts at (200, 0)
        safe_zone_margin = Config.SPAWN_SAFE_ZONE_MARGIN
        safe_zone = {
            'min_x': -200 - safe_zone_margin,
            'max_x': 200 + safe_zone_margin,
            'min_y': -safe_zone_margin,
            'max_y': safe_zone_margin
        }
        
        for _ in range(Config.NUM_MINES):
            # Keep trying until we get a position outside the safe zone
            max_attempts = 100
            for attempt in range(max_attempts):
                pos = self._random_position(margin=100)
                
                # Check if position is outside safe zone
                if (pos.x < safe_zone['min_x'] or pos.x > safe_zone['max_x'] or
                    pos.y < safe_zone['min_y'] or pos.y > safe_zone['max_y']):
                    # Position is safe, use it
                    mines.append(Mine(pos))
                    break
            else:
                # If we couldn't find a safe position after max attempts,
                # just place it anywhere (shouldn't happen with reasonable settings)
                mines.append(Mine(self._random_position(margin=100)))
        
        return mines

    def _spawn_stars(self):
        """Spawn stars at random positions, avoiding spawn area"""
        stars = []
        
        if not Config.SPAWN_SAFE_ZONE_ENABLED:
            # Safe zone disabled, spawn anywhere
            for _ in range(Config.NUM_STARS):
                stars.append(Star(self._random_position(margin=100)))
            return stars
        
        # Define safe zone (rectangle around both starting positions)
        safe_zone_margin = Config.SPAWN_SAFE_ZONE_MARGIN
        safe_zone = {
            'min_x': -200 - safe_zone_margin,
            'max_x': 200 + safe_zone_margin,
            'min_y': -safe_zone_margin,
            'max_y': safe_zone_margin
        }
        
        for _ in range(Config.NUM_STARS):
            # Keep trying until we get a position outside the safe zone
            max_attempts = 100
            for attempt in range(max_attempts):
                pos = self._random_position(margin=100)
                
                # Check if position is outside safe zone
                if (pos.x < safe_zone['min_x'] or pos.x > safe_zone['max_x'] or
                    pos.y < safe_zone['min_y'] or pos.y > safe_zone['max_y']):
                    # Position is safe, use it
                    stars.append(Star(pos))
                    break
            else:
                # If we couldn't find a safe position after max attempts,
                # just place it anywhere (shouldn't happen with reasonable settings)
                stars.append(Star(self._random_position(margin=100)))
        
        return stars
    
    def _random_position(self, margin=0):
        """Generate random position within play area"""
        x = random.uniform(
            -Config.WINDOW_WIDTH / 2 + margin,
            Config.WINDOW_WIDTH / 2 - margin
        )
        y = random.uniform(
            -Config.WINDOW_HEIGHT / 2 + margin,
            Config.WINDOW_HEIGHT / 2 - margin
        )
        return Vector2(x, y)
    
    def respawn_star(self, star_index):
        """Respawn a star at new random position"""
        self.stars[star_index] = Star(self._random_position(margin=100))
    
    def declare_winner(self, player_id):
        """Declare a winner"""
        self.winner = player_id
        self.game_over = True
        
        if self.num_players == 2:
            self.kills[player_id] += 1
    
    def start_new_round(self):
        """Start a new round (for two-player)"""
        # Check if someone won the match
        if self.num_players == 2:
            wins_needed = (self.best_of // 2) + 1
            if self.kills[1] >= wins_needed or self.kills[2] >= wins_needed:
                # Match is over
                return False
        
        # Reset for new round
        self.round_number += 1
        self.game_over = False
        self.winner = None
        
        # Reset ships
        for ship in self.ships.values():
            ship.alive = True
            ship.velocity = Vector2(0, 0)
            ship.trail_segments = []
            ship.current_segment = []
            ship.boost_active = False
            ship.boost_timer = 0.0
            ship.boost_cooldown_timer = 0.0
        
        # Reset ship positions
        if 1 in self.ships:
            self.ships[1].position = Vector2(-200, 0)
            self.ships[1].angle = 0
        if 2 in self.ships:
            self.ships[2].position = Vector2(200, 0)
            self.ships[2].angle = 180
        
        # Respawn stars and mines
        self.stars = self._spawn_stars()
        self.mines = self._spawn_mines()
        
        return True
    
    def reset(self):
        """Reset game state for new game"""
        self.__init__(self.num_players)
    
    def get_match_winner(self):
        """Get overall match winner (for two-player)"""
        if self.num_players != 2:
            return None
        
        wins_needed = (self.best_of // 2) + 1
        if self.kills[1] >= wins_needed:
            return 1
        elif self.kills[2] >= wins_needed:
            return 2
        return None