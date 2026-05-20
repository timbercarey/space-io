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
    
    def _spawn_stars(self):
        """Spawn stars at random positions"""
        stars = []
        for _ in range(Config.NUM_STARS):
            pos = self._random_position(margin=100)
            stars.append(Star(pos))
        return stars
    
    def _spawn_mines(self):
        """Spawn mines at random positions"""
        mines = []
        for _ in range(Config.NUM_MINES):
            pos = self._random_position(margin=100)
            mines.append(Mine(pos))
        return mines
    
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
    
    def reset(self):
        """Reset game state for new game"""
        self.__init__(self.num_players)