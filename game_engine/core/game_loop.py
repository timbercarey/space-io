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
        self.return_to_menu = False
    
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
        return "menu" if self.return_to_menu else "quit"
    
    def _handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.game_state.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game_state.running = False
                elif event.key == pygame.K_SPACE:
                    if self.game_state.game_over:
                        if self._is_round_over_pending_next_round():
                            self.game_state.start_new_round()
                        else:
                            self.return_to_menu = True
                            self.game_state.running = False
                elif event.key == pygame.K_r:
                    self._restart_game()
                elif event.key == pygame.K_n:
                    # Start new round (two-player)
                    if self.game_state.num_players == 2 and self.game_state.game_over:
                        if not self.game_state.start_new_round():
                            # Match is over, full reset
                            self._restart_game()
                elif event.key == pygame.K_h:
                    # Toggle haptic visualization
                    Config.SHOW_HAPTIC_PANEL = not Config.SHOW_HAPTIC_PANEL
                elif event.key == pygame.K_b:
                    # Toggle hitbox display
                    Config.SHOW_HITBOXES = not Config.SHOW_HITBOXES
                elif event.key == pygame.K_z:
                    # Calibrate current throttle position as zero
                    if hasattr(self.controller, 'zero_throttle'):
                        player_ids = list(self.game_state.ships.keys())
                        self.controller.zero_throttle(player_ids)
                        print("Throttle zeroed")

    def _restart_game(self):
        """Restart the current game mode without returning to the menu."""
        self.return_to_menu = False
        self.game_state.reset()
    
    def _update(self, dt):
        """Update game state"""
        
        # Handle countdown
        if self.game_state.countdown_active:
            self.game_state.countdown_timer -= dt
            if self.game_state.countdown_timer <= 0:
                self.game_state.countdown_active = False
            return  # Don't update ships during countdown
        
        # Don't update ships if game is over
        if self.game_state.game_over:
            return
        
        # Update each ship
        for player_id, ship in self.game_state.ships.items():
            if not ship.alive:
                continue
                
            steering = self.controller.get_steering(player_id)
            throttle = self.controller.get_throttle(player_id)
            ship.update(steering, throttle, dt)
    
    def _check_collisions(self):
        """Check all collisions"""
        # Don't check collisions if game is already over
        if self.game_state.game_over:
            return
        
        for player_id, ship in self.game_state.ships.items():
            if not ship.alive:
                continue
            
            # Check star collisions
            for i, star in enumerate(self.game_state.stars):
                if star.check_collision(ship.position, Config.SHIP_SIZE):
                    star.collect()
                    ship.activate_boost()
                    if self.game_state.num_players == 1:
                        self.game_state.scores[player_id] += 100
                    # Respawn star after collection
                    self.game_state.respawn_star(i)
            
            # Check mine collisions
            for mine in self.game_state.mines:
                if mine.check_collision(ship.position, Config.SHIP_SIZE):
                    self._handle_ship_death(player_id, ship)
                    return  # Exit immediately after death
            
            # Check own trail collisions
            all_trail_points = ship.get_all_trail_points()
            
            if len(all_trail_points) > 10:
                for trail_point in all_trail_points[:-10]:
                    if ship.position.distance_to(trail_point) < Config.SHIP_SIZE:
                        self._handle_ship_death(player_id, ship)
                        return  # Exit immediately after death
            
            # TWO-PLAYER: Check opponent trail collisions
            if self.game_state.num_players == 2:
                other_player_id = 2 if player_id == 1 else 1
                if other_player_id in self.game_state.ships:
                    other_ship = self.game_state.ships[other_player_id]
                    other_trail_points = other_ship.get_all_trail_points()
                    
                    # Check collision with opponent's trail
                    for trail_point in other_trail_points:
                        if ship.position.distance_to(trail_point) < Config.SHIP_SIZE:
                            # Dying player loses, other player wins
                            ship.kill()
                            other_ship.kill()  # Freeze winner too
                            self.game_state.declare_winner(other_player_id)
                            
                            # Trigger haptic effect on dying player
                            if self.force_calculator:
                                self.force_calculator.trigger_mine_hit(player_id)
                            
                            return  # Exit immediately after death
            
            # Update trail vibration effect based on proximity to trails
            if self.force_calculator and ship.alive:
                near_trail = self._check_near_trail(ship, player_id)
                if near_trail:
                    self.force_calculator.trigger_trail_collision(player_id)
                else:
                    self.force_calculator.clear_trail_collision(player_id)

    def _handle_ship_death(self, player_id, ship):
        """Handle ship death and end round"""
        ship.kill()
        
        # Trigger haptic effect
        if self.force_calculator:
            self.force_calculator.trigger_mine_hit(player_id)
        
        # In two-player, declare winner and freeze both ships
        if self.game_state.num_players == 2:
            other_player = 2 if player_id == 1 else 1
            self.game_state.declare_winner(other_player)
            
            # Kill other player too to freeze them
            if other_player in self.game_state.ships:
                self.game_state.ships[other_player].kill()
        else:
            # Single player - just game over
            self.game_state.game_over = True

    def _check_near_trail(self, ship, player_id):
        """
        Check if ship is near (but not colliding with) any trail
        Used for warning vibration
        
        Returns:
            bool: True if near trail
        """
        warning_distance = Config.SHIP_SIZE * 2.5
        
        # Check own trail
        all_trail_points = ship.get_all_trail_points()
        if len(all_trail_points) > 10:
            for trail_point in all_trail_points[:-10]:
                distance = ship.position.distance_to(trail_point)
                if Config.SHIP_SIZE < distance < warning_distance:
                    return True
        
        # TWO-PLAYER: Check opponent trail
        if self.game_state.num_players == 2:
            other_player_id = 2 if player_id == 1 else 1
            if other_player_id in self.game_state.ships:
                other_ship = self.game_state.ships[other_player_id]
                other_trail_points = other_ship.get_all_trail_points()
                
                for trail_point in other_trail_points:
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

        # Render safe zone
        # self.renderer.render_safe_zone_debug()  # Uncomment to see safe zone
        
        # Render HUD
        self.renderer.render_hud(self.game_state)
        
        # Send haptic forces to hardware
        if self.force_calculator and hasattr(self.controller, 'send_forces'):
            p1_steer, p1_throttle = self.force_calculator.calculate_forces(
                self.game_state,
                1,
                self.controller
            )
            p2_steer, p2_throttle = 0, 0
            if 2 in self.game_state.ships:
                p2_steer, p2_throttle = self.force_calculator.calculate_forces(
                    self.game_state,
                    2,
                    self.controller
                )
            
            self.controller.send_forces(p1_steer, p1_throttle, p2_steer, p2_throttle)
        
        # Render haptic visualization
        if self.force_visualizer and Config.SHOW_HAPTIC_PANEL:
            self.force_visualizer.render(self.force_calculator, self.controller, self.game_state)
        
        # Show pause message if paused
        if self.game_state.paused:
            self.renderer.render_text("PAUSED", 
                (Config.WINDOW_WIDTH // 2 - 80, Config.WINDOW_HEIGHT // 2),
                (255, 255, 255))
    
        # Show game over message
        if self.game_state.game_over:
            if self._is_round_over_pending_next_round():
                self._render_round_over_message()
            else:
                self._render_game_over_message()
            
        pygame.display.flip()

    def _is_round_over_pending_next_round(self):
        """Check whether 2P game over is only a round break, not match over."""
        return (
            self.game_state.num_players == 2
            and self.game_state.game_over
            and self.game_state.get_match_winner() is None
        )

    def _render_round_over_message(self):
        """Render between-round prompt for two-player mode."""
        font = pygame.font.Font(None, 48)
        small_font = pygame.font.Font(None, 32)

        score_y = Config.WINDOW_HEIGHT // 2 - 55
        self._render_match_score(font, score_y)

        prompt_surface = small_font.render("Press SPACEBAR for next round", True, (220, 220, 220))
        prompt_x = (Config.WINDOW_WIDTH - prompt_surface.get_width()) // 2
        prompt_y = score_y + font.get_height() + 10
        self.renderer.screen.blit(prompt_surface, (prompt_x, prompt_y))

    def _render_game_over_message(self):
        """Render game-over overlay."""
        title_font = pygame.font.Font(None, 96)
        font = pygame.font.Font(None, 42)
        small_font = pygame.font.Font(None, 32)

        title_surface = title_font.render("GAME OVER", True, (255, 60, 60))
        title_x = (Config.WINDOW_WIDTH - title_surface.get_width()) // 2
        title_y = Config.WINDOW_HEIGHT // 2 - 110
        self.renderer.screen.blit(title_surface, (title_x, title_y))

        next_y = title_y + title_surface.get_height() + 8
        if self.game_state.num_players == 2:
            winner = self.game_state.get_match_winner() or self.game_state.winner
            if winner:
                winner_color = Config.SHIP_COLOR_P1 if winner == 1 else Config.SHIP_COLOR_P2
                winner_surface = font.render(f"Player {winner} wins", True, winner_color)
                winner_x = (Config.WINDOW_WIDTH - winner_surface.get_width()) // 2
                self.renderer.screen.blit(winner_surface, (winner_x, next_y))
                next_y += winner_surface.get_height() + 8

        prompt_surface = small_font.render("Press SPACEBAR to return to menu", True, (220, 220, 220))
        prompt_x = (Config.WINDOW_WIDTH - prompt_surface.get_width()) // 2
        self.renderer.screen.blit(prompt_surface, (prompt_x, next_y))

    def _render_match_score(self, font, y):
        """Render 2P round score with player-colored values."""
        parts = [
            ("Score: ", (235, 235, 235)),
            (str(self.game_state.kills[1]), Config.SHIP_COLOR_P1),
            (" - ", (235, 235, 235)),
            (str(self.game_state.kills[2]), Config.SHIP_COLOR_P2),
        ]
        surfaces = [font.render(text, True, color) for text, color in parts]
        total_width = sum(surface.get_width() for surface in surfaces)
        x = (Config.WINDOW_WIDTH - total_width) // 2

        for surface in surfaces:
            self.renderer.screen.blit(surface, (x, y))
            x += surface.get_width()
