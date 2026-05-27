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
        self.velocity_history = {1: [], 2: []}
        self.steering_force_component_history = {1: [], 2: []}
        self.max_velocity_seen = {1: 0.0, 2: 0.0}
    
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
            if Config.SHOW_KNOB_VELOCITY_PLOT:
                self._render_velocity_plot(
                    player_id=1,
                    x=20,
                    y=Config.WINDOW_HEIGHT - 535,
                    force_calculator=force_calculator
                )
                self._render_steering_force_component_plot(
                    player_id=1,
                    x=20,
                    y=Config.WINDOW_HEIGHT - 395,
                    force_calculator=force_calculator,
                    controller=controller,
                    ship=game_state.ships[1]
                )
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
            if Config.SHOW_KNOB_VELOCITY_PLOT:
                self._render_velocity_plot(
                    player_id=2,
                    x=Config.WINDOW_WIDTH - 320,
                    y=Config.WINDOW_HEIGHT - 535,
                    force_calculator=force_calculator
                )
                self._render_steering_force_component_plot(
                    player_id=2,
                    x=Config.WINDOW_WIDTH - 320,
                    y=Config.WINDOW_HEIGHT - 395,
                    force_calculator=force_calculator,
                    controller=controller,
                    ship=game_state.ships[2]
                )
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

        steering_wall_markers = []
        if Config.STEERING_HAPTIC_MODE in (
            Config.HAPTIC_MODE_VIRTUAL_WALLS,
            Config.HAPTIC_MODE_SPRING_DAMPER_WITH_WALLS
        ):
            steering_wall_markers = self._get_wall_markers(
                Config.STEERING_MOTION_RANGE_DEG,
                Config.STEERING_CONTROL_ROTATION_RANGE
            )
        throttle_wall_markers = []
        if Config.THROTTLE_HAPTIC_MODE in (
            Config.HAPTIC_MODE_VIRTUAL_WALLS,
            Config.HAPTIC_MODE_SPRING_DAMPER_WITH_WALLS
        ):
            throttle_wall_markers = self._get_wall_markers(
                Config.THROTTLE_MOTION_RANGE_DEG,
                Config.THROTTLE_CONTROL_ROTATION_RANGE,
                forward_extension_deg=(
                    Config.BOOST_THROTTLE_FORWARD_EXTENSION_DEG
                    if ship.boost_active else 0.0
                )
            )
        
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
            (150, 200, 255),
            steering_wall_markers
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
            (255, 200, 150),
            throttle_wall_markers
        )
        
        current_y += 8  # Reduced spacing
        
        # Render active effects
        self._render_active_effects(x + 10, current_y, force_calculator, player_id)

    def _render_velocity_plot(self, player_id, x, y, force_calculator):
        """Render a rolling steering velocity plot with fixed degree/sec limits."""
        panel_width = 300
        panel_height = 130
        plot_margin_x = 12
        plot_top = y + 34
        plot_height = 82
        plot_width = panel_width - plot_margin_x * 2
        now = pygame.time.get_ticks() / 1000.0
        window_sec = max(0.1, Config.KNOB_VELOCITY_PLOT_WINDOW_SEC)
        deg_per_normalized_unit = 360.0 * Config.STEERING_CONTROL_ROTATION_RANGE
        current_velocity = (
            force_calculator.get_axis_velocity(player_id, 'steering')
            * deg_per_normalized_unit
        )
        self.max_velocity_seen[player_id] = max(
            self.max_velocity_seen.get(player_id, 0.0),
            abs(current_velocity)
        )

        history = self.velocity_history.setdefault(player_id, [])
        history.append((now, current_velocity))
        cutoff = now - window_sec
        while history and history[0][0] < cutoff:
            history.pop(0)

        panel_rect = pygame.Rect(x, y, panel_width, panel_height)
        pygame.draw.rect(self.screen, (24, 24, 24), panel_rect)
        pygame.draw.rect(self.screen, (85, 85, 85), panel_rect, 2)

        color = Config.SHIP_COLOR_P1 if player_id == 1 else Config.SHIP_COLOR_P2
        label = self.font.render(
            f"P{player_id} Steering Velocity {current_velocity:+.1f} deg/s",
            True,
            color
        )
        self.screen.blit(label, (x + 10, y + 7))

        plot_rect = pygame.Rect(x + plot_margin_x, plot_top, plot_width, plot_height)
        pygame.draw.rect(self.screen, (12, 12, 12), plot_rect)
        pygame.draw.rect(self.screen, (70, 70, 70), plot_rect, 1)

        velocity_limit = max(1.0, Config.KNOB_VELOCITY_PLOT_LIMIT_DEG_PER_SEC)

        center_y = plot_rect.centery
        pygame.draw.line(
            self.screen,
            (80, 80, 80),
            (plot_rect.left, center_y),
            (plot_rect.right, center_y),
            1
        )

        points = []
        for sample_time, velocity in history:
            time_fraction = (sample_time - cutoff) / window_sec
            px = plot_rect.left + int(max(0.0, min(1.0, time_fraction)) * plot_rect.width)
            normalized_velocity = max(-1.0, min(1.0, velocity / velocity_limit))
            py = center_y - int(normalized_velocity * (plot_rect.height / 2.0))
            points.append((px, py))

        if len(points) >= 2:
            pygame.draw.lines(self.screen, (120, 210, 255), False, points, 2)
        elif points:
            pygame.draw.circle(self.screen, (120, 210, 255), points[0], 2)

        range_text = self.small_font.render(f"+/- {velocity_limit:.0f} deg/s", True, (150, 150, 150))
        self.screen.blit(range_text, (plot_rect.left, plot_rect.bottom + 2))
        max_text = self.small_font.render(
            f"max {self.max_velocity_seen[player_id]:.1f}",
            True,
            (190, 190, 190)
        )
        self.screen.blit(
            max_text,
            (plot_rect.centerx - max_text.get_width() // 2, plot_rect.bottom + 2)
        )
        time_text = self.small_font.render(f"last {window_sec:g}s", True, (150, 150, 150))
        self.screen.blit(time_text, (plot_rect.right - time_text.get_width(), plot_rect.bottom + 2))

    def _render_steering_force_component_plot(
        self,
        player_id,
        x,
        y,
        force_calculator,
        controller,
        ship
    ):
        """Render rolling steering damping and spring forces on shared axes."""
        panel_width = 300
        panel_height = 130
        plot_margin_x = 12
        plot_top = y + 34
        plot_height = 82
        plot_width = panel_width - plot_margin_x * 2
        now = pygame.time.get_ticks() / 1000.0
        window_sec = max(0.1, Config.KNOB_VELOCITY_PLOT_WINDOW_SEC)
        has_estimator_snapshot, positions, velocities = (
            force_calculator.get_axis_position_velocity_snapshot()
        )
        if has_estimator_snapshot:
            steering_position = positions.get(player_id, {}).get(
                'steering',
                controller.get_steering(player_id)
            )
            steering_velocity = velocities.get(player_id, {}).get('steering', 0.0)
        else:
            steering_position = controller.get_steering(player_id)
            steering_velocity = 0.0
        steering_damping_velocity = force_calculator._get_steering_damping_velocity(
            player_id
        )
        raw_damping_force = (
            -steering_damping_velocity
            * Config.STEERING_VELOCITY_DAMPING
            * force_calculator._calculate_speed_damping_scale(ship)
        )
        raw_wall_damping_force = self._calculate_active_steering_wall_damping_force(
            force_calculator,
            steering_damping_velocity,
            steering_position
        )
        capped_total_damping_force = force_calculator._limit_steering_damping_force(
            raw_damping_force + raw_wall_damping_force
        )
        damping_force = force_calculator._limit_steering_damping_force(
            raw_damping_force
        )
        wall_damping_force = capped_total_damping_force - damping_force
        spring_force = self._calculate_active_steering_spring_force(
            force_calculator,
            steering_position
        )
        wall_force = self._calculate_active_steering_wall_force(
            force_calculator,
            steering_position
        ) + wall_damping_force

        history = self.steering_force_component_history.setdefault(player_id, [])
        history.append((now, damping_force, spring_force, wall_force))
        cutoff = now - window_sec
        while history and history[0][0] < cutoff:
            history.pop(0)

        panel_rect = pygame.Rect(x, y, panel_width, panel_height)
        pygame.draw.rect(self.screen, (24, 24, 24), panel_rect)
        pygame.draw.rect(self.screen, (85, 85, 85), panel_rect, 2)

        color = Config.SHIP_COLOR_P1 if player_id == 1 else Config.SHIP_COLOR_P2
        label = self.font.render(
            f"P{player_id} Steering Forces",
            True,
            color
        )
        self.screen.blit(label, (x + 10, y + 7))

        plot_rect = pygame.Rect(x + plot_margin_x, plot_top, plot_width, plot_height)
        pygame.draw.rect(self.screen, (12, 12, 12), plot_rect)
        pygame.draw.rect(self.screen, (70, 70, 70), plot_rect, 1)

        force_limit = max(1.0, Config.STEERING_FORCE_COMPONENT_PLOT_LIMIT)
        center_y = plot_rect.centery
        pygame.draw.line(
            self.screen,
            (80, 80, 80),
            (plot_rect.left, center_y),
            (plot_rect.right, center_y),
            1
        )

        damping_points = []
        spring_points = []
        wall_points = []
        for sample in history:
            if len(sample) == 3:
                sample_time, sample_damping, sample_spring = sample
                sample_wall = 0.0
            else:
                sample_time, sample_damping, sample_spring, sample_wall = sample
            time_fraction = (sample_time - cutoff) / window_sec
            px = plot_rect.left + int(max(0.0, min(1.0, time_fraction)) * plot_rect.width)
            damping_points.append((
                px,
                self._force_to_plot_y(sample_damping, force_limit, plot_rect)
            ))
            spring_points.append((
                px,
                self._force_to_plot_y(sample_spring, force_limit, plot_rect)
            ))
            wall_points.append((
                px,
                self._force_to_plot_y(sample_wall, force_limit, plot_rect)
            ))

        damping_color = (120, 210, 255)
        spring_color = (255, 210, 100)
        wall_color = (255, 120, 120)
        self._draw_plot_line(damping_points, damping_color)
        self._draw_plot_line(spring_points, spring_color)
        self._draw_plot_line(wall_points, wall_color)

        range_text = self.small_font.render(f"+/- {force_limit:.0f}", True, (150, 150, 150))
        self.screen.blit(range_text, (plot_rect.left, plot_rect.bottom + 2))
        damping_text = self.small_font.render(f"damp {damping_force:+.0f}", True, damping_color)
        self.screen.blit(damping_text, (plot_rect.left + 56, plot_rect.bottom + 2))
        spring_text = self.small_font.render(f"spring {spring_force:+.0f}", True, spring_color)
        self.screen.blit(spring_text, (plot_rect.centerx - 16, plot_rect.bottom + 2))
        wall_text = self.small_font.render(f"wall {wall_force:+.0f}", True, wall_color)
        self.screen.blit(wall_text, (plot_rect.right - wall_text.get_width(), plot_rect.bottom + 2))

    def _calculate_active_steering_spring_force(self, force_calculator, steering_position):
        """Return the steering spring component active in the selected steering mode."""
        if Config.STEERING_HAPTIC_MODE in (
            Config.HAPTIC_MODE_OFF,
            Config.HAPTIC_MODE_DAMPER_ONLY,
            Config.HAPTIC_MODE_VIRTUAL_WALLS
        ):
            return 0.0

        return force_calculator._calculate_centering_spring(
            steering_position,
            Config.STEERING_CENTERING_SPRING_STIFFNESS
        )

    def _calculate_active_steering_wall_force(
        self,
        force_calculator,
        steering_position
    ):
        """Return the elastic steering wall component active in the selected mode."""
        if Config.STEERING_HAPTIC_MODE in (
            Config.HAPTIC_MODE_VIRTUAL_WALLS,
            Config.HAPTIC_MODE_SPRING_DAMPER_WITH_WALLS
        ):
            return force_calculator._calculate_virtual_wall(
                steering_position,
                Config.STEERING_MOTION_RANGE_DEG,
                Config.STEERING_CONTROL_ROTATION_RANGE,
                Config.STEERING_VIRTUAL_WALL_STIFFNESS
            )

        return 0.0

    def _calculate_active_steering_wall_damping_force(
        self,
        force_calculator,
        steering_velocity,
        steering_position
    ):
        """Return raw extra damping from steering-wall entry before global cap."""
        if Config.STEERING_HAPTIC_MODE not in (
            Config.HAPTIC_MODE_VIRTUAL_WALLS,
            Config.HAPTIC_MODE_SPRING_DAMPER_WITH_WALLS
        ):
            return 0.0

        penetration = force_calculator._calculate_virtual_wall_penetration(
            steering_position,
            Config.STEERING_MOTION_RANGE_DEG,
            Config.STEERING_CONTROL_ROTATION_RANGE
        )
        if penetration <= 0.0:
            return 0.0

        outward_velocity = force_calculator._calculate_virtual_wall_outward_velocity(
            steering_position,
            steering_velocity,
            Config.STEERING_MOTION_RANGE_DEG,
            Config.STEERING_CONTROL_ROTATION_RANGE
        )
        if outward_velocity <= 0.0:
            return 0.0

        if Config.STEERING_WALL_DAMPING_VELOCITY_HYSTERESIS_ENABLED:
            enter_threshold = max(
                0.0,
                Config.STEERING_WALL_DAMPING_VELOCITY_ENTER_THRESHOLD
            )
            if outward_velocity < enter_threshold:
                return 0.0

        effective_penetration = (
            force_calculator._steering_wall_damping_effective_penetration(
                penetration
            )
        )
        if effective_penetration <= 0.0:
            return 0.0

        damping_scale = force_calculator._steering_wall_damping_penetration_scale(
            effective_penetration
        )
        return (
            -steering_velocity
            * Config.STEERING_VIRTUAL_WALL_INTO_WALL_DAMPING
            * damping_scale
        )

    def _force_to_plot_y(self, force, force_limit, plot_rect):
        normalized_force = max(-1.0, min(1.0, force / force_limit))
        return plot_rect.centery - int(normalized_force * (plot_rect.height / 2.0))

    def _draw_plot_line(self, points, color):
        if len(points) >= 2:
            pygame.draw.lines(self.screen, color, False, points, 2)
        elif points:
            pygame.draw.circle(self.screen, color, points[0], 2)
    
    def _render_force_bar(self, x, y, label, value, min_val, max_val, color, markers=None):
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
        
        # Wall markers
        if markers:
            for marker in markers:
                marker = max(min_val, min(max_val, marker))
                marker_normalized = (marker - min_val) / (max_val - min_val)
                marker_x = x + int(marker_normalized * bar_width)
                pygame.draw.line(
                    self.screen,
                    (255, 255, 120),
                    (marker_x, bar_y - 2),
                    (marker_x, bar_y + bar_height + 2),
                    2
                )
        
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
    
    def _render_input_bar(self, x, y, label, value, color, wall_markers=None):
        """
        Render input position bar (-1 to 1)
        
        Returns:
            int: Next y position
        """
        markers = None
        if wall_markers:
            markers = [marker * 500 for marker in wall_markers]

        return self._render_force_bar(x, y, label, value * 500, -500, 500, color, markers)

    def _get_wall_markers(self, motion_range_deg, control_rotation_range, forward_extension_deg=0.0):
        """Get normalized rear and forward virtual wall positions."""
        rear_limit_deg = motion_range_deg / 2.0
        forward_limit_deg = (motion_range_deg / 2.0) + forward_extension_deg
        scale = 360.0 * control_rotation_range

        if scale <= 0:
            return []

        return [
            -rear_limit_deg / scale,
            forward_limit_deg / scale
        ]
    
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
