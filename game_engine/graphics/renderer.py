"""
Main rendering system
"""
import pygame
from config import Config
from utils import Vector2

class Renderer:
    def __init__(self, screen):
        """
        Args:
            screen: pygame.Surface to draw on
        """
        self.screen = screen
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
    
    def clear(self):
        """Clear screen"""
        self.screen.fill(Config.BACKGROUND_COLOR)
    
    def render_spaceship(self, ship):
        """Render a spaceship"""
        if not ship.alive:
            return
        
        # Draw ship as triangle
        points = ship.get_triangle_points()
        # Convert to screen coordinates (origin at top-left for pygame)
        screen_points = [self._world_to_screen(p) for p in points]
        pygame.draw.polygon(self.screen, ship.color, screen_points)
        
        # Draw boost indicator if active
        if ship.boost_active:
            center = self._world_to_screen(ship.position.to_tuple())
            pygame.draw.circle(self.screen, (255, 255, 255), center, 
                            int(Config.SHIP_SIZE * 1.5), 2)
        
        # Draw hitbox if enabled
        if Config.SHOW_HITBOXES:
            center = self._world_to_screen(ship.position.to_tuple())
            pygame.draw.circle(self.screen, (255, 255, 255), center, 
                            int(Config.SHIP_SIZE), 1)
    
    def render_trail(self, ship):
        """Render ship trail (may be multiple disconnected segments)"""
        
        def draw_trail_segment(segment):
            """Helper to draw a single trail segment"""
            if len(segment) < 2:
                return
            
            # Build list of connected points (breaking on large gaps)
            current_line = []
            
            for i, point in enumerate(segment):
                screen_point = self._world_to_screen(point.to_tuple())
                
                if len(current_line) == 0:
                    # First point
                    current_line.append(screen_point)
                else:
                    # Check if this point is connected to previous (in world space)
                    prev_world_point = segment[i - 1]
                    world_distance = point.distance_to(prev_world_point)
                    
                    # If distance is reasonable (less than expected spacing * 3), it's connected
                    if world_distance < Config.TRAIL_SEGMENT_SPACING * 3:
                        current_line.append(screen_point)
                    else:
                        # Gap detected - draw current line and start new one
                        if len(current_line) >= 2:
                            pygame.draw.lines(self.screen, ship.trail_color, False, 
                                            current_line, Config.TRAIL_WIDTH)
                        current_line = [screen_point]
            
            # Draw final line segment
            if len(current_line) >= 2:
                pygame.draw.lines(self.screen, ship.trail_color, False, 
                                current_line, Config.TRAIL_WIDTH)
        
        # Render old segments
        for segment in ship.trail_segments:
            draw_trail_segment(segment)
        
        # Render current segment
        draw_trail_segment(ship.current_segment)
    
    def render_star(self, star):
        """Render a star"""
        if not star.active:
            return
        
        center = self._world_to_screen(star.position.to_tuple())
        
        # Draw star as a circle with rays
        pygame.draw.circle(self.screen, star.color, center, star.size)
        
        # Draw 4 rays
        for angle in [0, 90, 180, 270]:
            angle_rad = angle * 3.14159 / 180
            import math
            dx = math.cos(angle_rad) * star.size * 1.5
            dy = math.sin(angle_rad) * star.size * 1.5
            start = (center[0], center[1])
            end = (center[0] + dx, center[1] + dy)
            pygame.draw.line(self.screen, star.color, start, end, 2)
    
    def render_mine(self, mine):
        """Render a mine"""
        if not mine.active:
            return
        
        center = self._world_to_screen(mine.position.to_tuple())
        
        # Draw mine as circle with X
        pygame.draw.circle(self.screen, mine.color, center, mine.size)
        pygame.draw.circle(self.screen, (255, 255, 255), center, mine.size, 2)
        
        # Draw X
        offset = mine.size * 0.6
        pygame.draw.line(self.screen, (255, 255, 255),
                        (center[0] - offset, center[1] - offset),
                        (center[0] + offset, center[1] + offset), 2)
        pygame.draw.line(self.screen, (255, 255, 255),
                        (center[0] + offset, center[1] - offset),
                        (center[0] - offset, center[1] + offset), 2)
    
    def render_text(self, text, position, color=(255, 255, 255), small=False):
        """Render text on screen"""
        font = self.small_font if small else self.font
        text_surface = font.render(text, True, color)
        self.screen.blit(text_surface, position)
    
    def render_hud(self, game_state):
        """Render heads-up display (score, status, etc.)"""
        y_offset = 10
        
        # Player 1 status (top-left)
        p1_text = f"P1 Score: {game_state.scores[1]}"
        if game_state.num_players == 2:
            p1_text += f" | Wins: {game_state.kills[1]}"
        self.render_text(p1_text, (10, y_offset), 
                        Config.SHIP_COLOR_P1, small=True)
        
        if 1 in game_state.ships and game_state.ships[1].boost_active:
            self.render_text("BOOST!", (10, y_offset + 25), 
                        (255, 255, 0), small=True)
        
        # Player 2 status (top-right) - for two-player
        if game_state.num_players == 2:
            p2_text = f"P2 Score: {game_state.scores[2]}"
            p2_text += f" | Wins: {game_state.kills[2]}"
            text_surface = self.small_font.render(p2_text, True, Config.SHIP_COLOR_P2)
            self.screen.blit(text_surface, 
                            (Config.WINDOW_WIDTH - text_surface.get_width() - 10, y_offset))
            
            if 2 in game_state.ships and game_state.ships[2].boost_active:
                boost_surface = self.small_font.render("BOOST!", True, (255, 255, 0))
                self.screen.blit(boost_surface,
                            (Config.WINDOW_WIDTH - boost_surface.get_width() - 10, y_offset + 25))
        
        # Round number (top-center) - for two-player
        if game_state.num_players == 2:
            round_text = f"Round {game_state.round_number} (Best of {game_state.best_of})"
            round_surface = self.small_font.render(round_text, True, (200, 200, 200))
            self.screen.blit(round_surface,
                            ((Config.WINDOW_WIDTH - round_surface.get_width()) // 2, y_offset))
        
        # FPS (top-right corner for single player, or below P2 for two-player)
        fps_text = f"FPS: {int(game_state.fps)}"
        fps_surface = self.small_font.render(fps_text, True, (100, 100, 100))
        if game_state.num_players == 1:
            self.screen.blit(fps_surface, (Config.WINDOW_WIDTH - 100, 10))
        else:
            self.screen.blit(fps_surface, (Config.WINDOW_WIDTH - 100, 60))
    
    def _world_to_screen(self, world_pos):
        """
        Convert world coordinates (origin at center, y-up) to 
        screen coordinates (origin at top-left, y-down)
        
        Args:
            world_pos: tuple (x, y)
        
        Returns:
            tuple: (screen_x, screen_y)
        """
        screen_x = world_pos[0] + Config.WINDOW_WIDTH / 2
        screen_y = Config.WINDOW_HEIGHT / 2 - world_pos[1]
        return (int(screen_x), int(screen_y))
    
    def render_text_centered(self, text, y_position, color=(255, 255, 255), small=False):
        """Render text centered horizontally at given y position"""
        font = self.small_font if small else self.font
        text_surface = font.render(text, True, color)
        x_position = (Config.WINDOW_WIDTH - text_surface.get_width()) // 2
        self.screen.blit(text_surface, (x_position, y_position))

    def render_safe_zone_debug(self):
        """Render safe zone outline for debugging"""
        if not Config.SPAWN_SAFE_ZONE_ENABLED:
            return
        
        margin = Config.SPAWN_SAFE_ZONE_MARGIN
        
        # Calculate safe zone corners in world coordinates
        corners = [
            (-200 - margin, -margin),
            (200 + margin, -margin),
            (200 + margin, margin),
            (-200 - margin, margin)
        ]
        
        # Convert to screen coordinates
        screen_corners = [self._world_to_screen(corner) for corner in corners]
        
        # Draw outline
        pygame.draw.lines(self.screen, (100, 100, 100), True, screen_corners, 2)