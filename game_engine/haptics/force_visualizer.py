"""
Visualize haptic forces on screen for debugging/simulation
"""
import pygame
from config import Config
from .effects import HapticEffect

class ForceVisualizer:
    """Renders force feedback visualization overlay"""
    
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
    
    def render(self, force_calculator, controller, game_state):
        """
        Render force visualization for all players
        
        Args:
            force_calculator: ForceCalculator instance
            controller: Controller instance
            game_state: GameState instance
        """
        # Player 1 on left side
        if 1 in game_state.ships:
            self._render_player_forces(
                player_id=1,
                x=20,
                y=Config.WINDOW_HEIGHT - 250,  # Increased from 220
                force_calculator=force_calculator,
                controller=controller,
                game_state=game_state
            )
        
        # Player 2 on right side (when implemented)
        if 2 in game_state.ships:
            self._render_player_forces(
                player_id=2,
                x=Config.WINDOW_WIDTH - 320,
                y=Config.WINDOW_HEIGHT - 250,  # Increased from 220
                force_calculator=force_calculator,
                controller=controller,
                game_state=game_state
            )
    
    def _render_player_forces(self, player_id, x, y, force_calculator, controller, game_state):
        """Render force display for one player"""
        ship = game_state.ships[player_id]
        
        # Background panel - taller to fit active effects
        panel_width = 300
        panel_height = 240  # Increased from 200
        panel_rect = pygame.Rect(x, y, panel_width, panel_height)
        pygame.draw.rect(self.screen, (30, 30, 30), panel_rect)
        pygame.draw.rect(self.screen, (100, 100, 100), panel_rect, 2)
        
        # Player label
        color = Config.SHIP_COLOR_P1 if player_id == 1 else Config.SHIP_COLOR_P2
        label = self.font.render(f"Player {player_id} Haptics", True, color)
        self.screen.blit(label, (x + 10, y + 5))
        
        current_y = y + 35
        
        # Get forces
        steering_force, throttle_force = force_calculator.calculate_forces(
            game_state,
            player_id,
            controller
        )
        
        # Get controller inputs
        steering_input = controller.get_steering(player_id)
        throttle_input = controller.get_throttle(player_id)
        
        # Render steering
        current_y = self._render_force_bar(
            x + 10, current_y,
            "Steering Force",
            steering_force,
            -1000, 1000,
            (100, 150, 255)
        )
        
        current_y = self._render_input_bar(
            x + 10, current_y,
            "Steering Input",
            steering_input,
            (150, 200, 255)
        )
        
        current_y += 5  # Reduced spacing
        
        # Render throttle
        current_y = self._render_force_bar(
            x + 10, current_y,
            "Throttle Force",
            throttle_force,
            -1000, 1000,
            (255, 150, 100)
        )
        
        current_y = self._render_input_bar(
            x + 10, current_y,
            "Throttle Input",
            throttle_input,
            (255, 200, 150)
        )
        
        current_y += 8  # Reduced spacing
        
        # Render active effects
        self._render_active_effects(x + 10, current_y, force_calculator, player_id)
    
    def _render_force_bar(self, x, y, label, value, min_val, max_val, color):
        """
        Render a horizontal bar showing force value
        
        Returns:
            int: Next y position
        """
        # Label
        text = self.small_font.render(f"{label}: {int(value)}", True, (200, 200, 200))
        self.screen.blit(text, (x, y))
        
        # Bar background
        bar_y = y + 18  # Reduced from 20
        bar_width = 280
        bar_height = 12  # Reduced from 15
        pygame.draw.rect(self.screen, (50, 50, 50), 
                        (x, bar_y, bar_width, bar_height))
        
        # Center line
        center_x = x + bar_width // 2
        pygame.draw.line(self.screen, (100, 100, 100),
                        (center_x, bar_y), (center_x, bar_y + bar_height), 1)
        
        # Value bar
        normalized = (value - min_val) / (max_val - min_val)
        normalized = max(0.0, min(1.0, normalized))
        
        if value >= 0:
            # Positive force - draw from center to right
            bar_start = center_x
            bar_length = int((normalized - 0.5) * bar_width)
        else:
            # Negative force - draw from left to center
            bar_length = int((0.5 - normalized) * bar_width)
            bar_start = center_x - bar_length
        
        if abs(bar_length) > 2:
            pygame.draw.rect(self.screen, color,
                           (bar_start, bar_y, abs(bar_length), bar_height))
        
        return bar_y + bar_height + 3  # Reduced spacing
    
    def _render_input_bar(self, x, y, label, value, color):
        """
        Render input position bar (-1 to 1)
        
        Returns:
            int: Next y position
        """
        return self._render_force_bar(x, y, label, value * 500, -500, 500, color)
    
    def _render_active_effects(self, x, y, force_calculator, player_id):
        """Render list of active haptic effects"""
        effects = force_calculator.get_active_effects(player_id)
        
        text = self.small_font.render("Active Effects:", True, (200, 200, 200))
        self.screen.blit(text, (x, y))
        
        y += 18  # Reduced from 20
        
        if len(effects) == 0:
            text = self.small_font.render("  None", True, (150, 150, 150))
            self.screen.blit(text, (x, y))
        else:
            for effect in effects:
                effect_name = self._get_effect_name(effect)
                text = self.small_font.render(f"  • {effect_name}", True, (255, 255, 100))
                self.screen.blit(text, (x, y))
                y += 16  # Reduced from 18
        
        return y
    
    def _get_effect_name(self, effect):
        """Get human-readable name for effect"""
        names = {
            HapticEffect.NONE: "None",
            HapticEffect.TRAIL_VIBRATION: "Trail Vibration",
            HapticEffect.MINE_KICKBACK: "Mine Kickback",
            HapticEffect.SPEED_DAMPING: "Speed Damping"
        }
        return names.get(effect, "Unknown")
