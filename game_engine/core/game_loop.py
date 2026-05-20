"""
Main game loop
"""
import pygame
from config import Config

class GameLoop:
    def __init__(self, game_state, controller, renderer, force_calculator=None, force_visualizer=None):
        """
        Args:
            game_state: GameState instance
            controller: Controller instance
            renderer: Renderer instance
            force_calculator: ForceCalculator instance (optional)
            force_visualizer: ForceVisualizer instance (optional)
        """
        self.game_state = game_state
        self.controller = controller
        self.renderer = renderer
        self.force_calculator = force_calculator
        self.force_visualizer = force_visualizer
        self.clock = pygame.time.Clock()
    
    def run(self):
        """Main game loop"""
        while self.game_state.running:
            # Calculate delta time
            dt = self.clock.tick(Config.FPS) / 1000.0  # Convert to seconds
            self.game_state.fps = self.clock.get_fps()
            
            # Handle events
            self._handle_events()
            
            if not self.game_state.paused:
                # Update input
                self.controller.update()
                
                # Update game state
                self._update(dt)
                
                # Check collisions
                self._check_collisions()
                
                # Update haptics
                if self.force_calculator:
                    self.force_calculator.update(dt)
            
            # Render
            self._render()
        
        # Cleanup
        self.controller.close()
    
    def _handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.game_state.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game_state.running = False
                elif event.key == pygame.K_SPACE:
                    self.game_state.paused = not self.game_state.paused
                elif event.key == pygame.K_r:
                    self.game_state.reset()
    
    def _update(self, dt):
        """Update game state"""
        # Update each ship
        for player_id, ship in self.game_state.ships.items():
            steering = self.controller.get_steering(player_id)
            throttle = self.controller.get_throttle(player_id)
            ship.update(steering, throttle, dt)
    
    def _check_collisions(self):
        """Check all collisions"""
        for player_id, ship in self.game_state.ships.items():
            if not ship.alive:
                continue
            
            # Check star collisions
            for i, star in enumerate(self.game_state.stars):
                if star.check_collision(ship.position, Config.SHIP_SIZE):
                    star.collect()
                    ship.activate_boost()
                    self.game_state.scores[player_id] += 100
                    # Respawn star after collection
                    self.game_state.respawn_star(i)
            
            # Check mine collisions
            for mine in self.game_state.mines:
                if mine.check_collision(ship.position, Config.SHIP_SIZE):
                    ship.kill()
                    self.game_state.game_over = True
                    
                    # Trigger haptic effect
                    if self.force_calculator:
                        self.force_calculator.trigger_mine_hit(player_id)
            
            # Check trail collisions (with own trail for now)
            # Get all trail points
            all_trail_points = ship.get_all_trail_points()
            
            # Check if ship hits its own trail (not the most recent segments)
            trail_collision = False
            if len(all_trail_points) > 10:
                for trail_point in all_trail_points[:-10]:
                    if ship.position.distance_to(trail_point) < Config.SHIP_SIZE:
                        ship.kill()
                        self.game_state.game_over = True
                        trail_collision = True
                        
                        # Trigger haptic effect
                        if self.force_calculator:
                            self.force_calculator.trigger_mine_hit(player_id)
                        break
            
            # Update trail vibration effect based on proximity to trails
            if self.force_calculator:
                near_trail = self._check_near_trail(ship, all_trail_points)
                if near_trail and not trail_collision:
                    self.force_calculator.trigger_trail_collision(player_id)
                else:
                    self.force_calculator.clear_trail_collision(player_id)
    
    def _check_near_trail(self, ship, trail_points):
        """
        Check if ship is near (but not colliding with) trail
        Used for warning vibration
        
        Returns:
            bool: True if near trail
        """
        warning_distance = Config.SHIP_SIZE * 2.5
        
        if len(trail_points) > 10:
            for trail_point in trail_points[:-10]:
                distance = ship.position.distance_to(trail_point)
                if Config.SHIP_SIZE < distance < warning_distance:
                    return True
        return False
    
    def _render(self):
        """Render everything"""
        self.renderer.clear()
        
        # Render trails first (so they're behind ships)
        for ship in self.game_state.ships.values():
            self.renderer.render_trail(ship)
        
        # Render stars
        for star in self.game_state.stars:
            self.renderer.render_star(star)
        
        # Render mines
        for mine in self.game_state.mines:
            self.renderer.render_mine(mine)
        
        # Render ships
        for ship in self.game_state.ships.values():
            self.renderer.render_spaceship(ship)
        
        # Render HUD
        self.renderer.render_hud(self.game_state)
        
        # Send haptic forces to hardware
        if self.force_calculator and hasattr(self.controller, 'send_forces'):
            p1_steer, p1_throttle = self.force_calculator.calculate_forces(self.game_state, 1)
            p2_steer, p2_throttle = 0, 0
            if 2 in self.game_state.ships:
                p2_steer, p2_throttle = self.force_calculator.calculate_forces(self.game_state, 2)
            
            self.controller.send_forces(p1_steer, p1_throttle, p2_steer, p2_throttle)
        
        # Render haptic visualization
        if self.force_visualizer:
            self.force_visualizer.render(self.force_calculator, self.controller, self.game_state)
        
        # Show pause message if paused
        if self.game_state.paused:
            self.renderer.render_text("PAUSED", 
                (Config.WINDOW_WIDTH // 2 - 80, Config.WINDOW_HEIGHT // 2),
                (255, 255, 255))
        
        # Show game over message
        if self.game_state.game_over:
            self.renderer.render_text("GAME OVER - Press R to restart", 
                (Config.WINDOW_WIDTH // 2 - 250, Config.WINDOW_HEIGHT // 2),
                (255, 0, 0))
        
        pygame.display.flip()