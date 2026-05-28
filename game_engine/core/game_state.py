"""
Central game state management
"""
import random
from utils import Vector2
from config import Config
from entities import Spaceship, Star, Mine

class GameState:
    PLAYER_STARTS = Config.PLAYER_STARTS

    def __init__(self, num_players=1, ship_styles=None):
        """
        Args:
            num_players: 1 or 2
        """
        self.num_players = num_players
        self.ship_styles = ship_styles or {1: "x_wing", 2: "tie_fighter"}
        self.difficulty_level = None
        self.hardware_difficulty_switch = None
        self.hardware_player2_enabled = None
        self.hardware_switch_packet_received = False
        self.hardware_pin25_active = None
        self.hardware_pin26_active = None
        self.hardware_pin9_active = None
        self.hardware_switch_change_time = None
        self.hardware_switch_change_message = ""
        self.running = True
        self.paused = False
        self.fps = 60
        
        # Scores
        self.scores = {1: 0, 2: 0}
        self.kills = {1: 0, 2: 0}  # Track kills in PvP
        
        # Create ships
        self.ships = {}
        if num_players >= 1:
            self.add_player(1)
        if num_players >= 2:
            self.add_player(2)
        
        # Create stars and mines
        self.stars = self._spawn_stars()
        self.mines = self._spawn_mines()
        
        # Game state
        self.game_over = False
        self.winner = None
        self.game_over_return_timer = None
        self.round_restart_timer = None
        self.round_number = 1
        self.best_of = Config.BEST_OF_ROUNDS if hasattr(Config, 'BEST_OF_ROUNDS') else 3

        # Round countdown
        self.countdown_active = False
        self.countdown_timer = 0.0
        self.countdown_duration = 3.0  # 3 second countdown

    def add_player(self, player_id):
        """Add a player ship if it is not already in the game."""
        if player_id in self.ships:
            return False

        start_config = self.PLAYER_STARTS.get(player_id)
        if start_config is None:
            return False
        start_position = self._start_position(player_id)
        start_angle = start_config["angle"]
        default_style = start_config["style"]

        self.ships[player_id] = Spaceship(
            player_id=player_id,
            start_position=start_position,
            start_angle=start_angle,
            ship_style=self.ship_styles.get(player_id, default_style)
        )
        self.num_players = max(self.num_players, player_id)
        self.scores.setdefault(player_id, 0)
        self.kills.setdefault(player_id, 0)
        return True

    def remove_player(self, player_id):
        """Remove a player ship from the game."""
        if player_id not in self.ships:
            return False

        del self.ships[player_id]
        self.num_players = 2 if 2 in self.ships else 1
        if self.game_over and player_id == 2:
            self.game_over = False
            self.winner = None
            self.game_over_return_timer = None
            self.round_restart_timer = None
        return True

    def set_player2_enabled(self, enabled):
        """Add or remove player 2 based on the hardware switch."""
        if enabled:
            return self.add_player(2)
        return self.remove_player(2)

    def apply_difficulty(self, difficulty_level):
        """Apply a hardware difficulty profile and respawn asteroids if needed."""
        profiles = Config.DIFFICULTY_PROFILES
        difficulty_level = max(1, min(3, int(difficulty_level)))
        profile = profiles[difficulty_level]

        if self.difficulty_level == difficulty_level:
            return False

        self.difficulty_level = difficulty_level
        Config.MAX_SPEED = profile["max_speed"]
        Config.ACCELERATION = profile["acceleration"]
        Config.NUM_MINES = profile["num_mines"]
        Config.MINE_FLOAT_MIN_SPEED = profile["mine_float_min_speed"]
        Config.MINE_FLOAT_MAX_SPEED = profile["mine_float_max_speed"]
        Config.DAMPING_SPEED_THRESHOLD = Config.MAX_SPEED * 0.8
        self.mines = self._spawn_mines()
        return True
    
    def _spawn_mines(self):
        """Spawn mines at random positions, avoiding player start areas."""
        mines = []
        
        if not Config.SPAWN_SAFE_ZONE_ENABLED:
            # Safe zone disabled, spawn anywhere
            for _ in range(Config.NUM_MINES):
                mines.append(Mine(self._random_position(margin=100)))
            return mines
        
        for _ in range(Config.NUM_MINES):
            # Keep trying until we get a position outside the safe zone
            max_attempts = 100
            for attempt in range(max_attempts):
                pos = self._random_position(margin=100)
                
                if self._is_outside_spawn_safe_zones(pos, Config.MINE_SIZE):
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
        
        for _ in range(Config.NUM_STARS):
            # Keep trying until we get a position outside the safe zone
            max_attempts = 100
            for attempt in range(max_attempts):
                pos = self._random_position(margin=100)
                
                if self._is_outside_spawn_safe_zones(pos, Config.STAR_SIZE):
                    stars.append(Star(pos))
                    break
            else:
                # If we couldn't find a safe position after max attempts,
                # just place it anywhere (shouldn't happen with reasonable settings)
                stars.append(Star(self._random_position(margin=100)))
        
        return stars

    @classmethod
    def get_player_start_positions(cls):
        """Return fresh Vector2 instances for each configured player start."""
        return {
            player_id: Vector2(*start_config["position"])
            for player_id, start_config in cls.PLAYER_STARTS.items()
        }

    @classmethod
    def _start_position(cls, player_id):
        return Vector2(*cls.PLAYER_STARTS[player_id]["position"])

    def _active_player_start_positions(self):
        return [
            self._start_position(player_id)
            for player_id in self.ships
            if player_id in self.PLAYER_STARTS
        ]

    def _is_outside_spawn_safe_zones(self, position, object_radius=0):
        safe_radius = Config.SPAWN_SAFE_ZONE_MARGIN + object_radius
        for start_position in self._active_player_start_positions():
            if position.distance_to(start_position) < safe_radius:
                return False
        return True
    
    def _random_position(self, margin=0):
        """Generate random position within play area"""
        x = random.uniform(
            -Config.playfield_width() / 2 + margin,
            Config.playfield_width() / 2 - margin
        )
        y = random.uniform(
            -Config.playfield_height() / 2 + margin,
            Config.playfield_height() / 2 - margin
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
        self.game_over_return_timer = None
        self.round_restart_timer = None
        
        # Reset ships
        for ship in self.ships.values():
            ship.alive = True
            ship.exploding = False
            ship.explosion_timer = 0.0
            ship.explosion_particles = []
            ship.velocity = Vector2(0, 0)
            ship.trail_segments = []
            ship.current_segment = []
            ship.boost_active = False
            ship.boost_timer = 0.0
            ship.boost_cooldown_timer = 0.0
            ship.asteroid_bounce_cooldown_timer = 0.0
        
        # Reset ship positions
        if 1 in self.ships:
            self.ships[1].position = self._start_position(1)
            self.ships[1].angle = self.PLAYER_STARTS[1]["angle"]
        if 2 in self.ships:
            self.ships[2].position = self._start_position(2)
            self.ships[2].angle = self.PLAYER_STARTS[2]["angle"]
        
        # Respawn stars and mines
        self.stars = self._spawn_stars()
        self.mines = self._spawn_mines()
        
        return True
    
    def reset(self):
        """Reset game state for new game"""
        self.__init__(self.num_players, self.ship_styles)
    
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
