"""
Main rendering system
"""
import math
import time

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
        if ship.exploding:
            self.render_ship_explosion(ship)
            return

        if not ship.alive:
            return

        ship_style = ship.ship_style or ("x_wing" if ship.player_id == 1 else "tie_fighter")

        if ship_style == "x_wing":
            self._render_x_wing_ship(ship)
        elif ship_style == "tie_fighter":
            self._render_tie_fighter_ship(ship)
        elif ship_style == "falcon":
            self._render_falcon_ship(ship)
        else:
            size = Config.SHIP_SIZE
            self._render_engine_plumes(ship, [(-0.72 * size, 0, 0.92, 0.18)])
            points = ship.get_triangle_points()
            screen_points = [self._world_to_screen(p) for p in points]
            pygame.draw.polygon(self.screen, ship.color, screen_points)
        
        if ship.boost_active:
            self._render_boost_orb(ship)
        
        # Draw hitbox if enabled
        if Config.SHOW_HITBOXES:
            center = self._world_to_screen(ship.position.to_tuple())
            pygame.draw.circle(self.screen, (255, 255, 255), center, 
                            self._world_length_to_screen(Config.SHIP_SIZE), 1)

    def _ship_point(self, ship, forward_offset, side_offset):
        """Convert ship-local offsets to screen coordinates."""
        forward = Vector2.from_angle(ship.angle)
        left = Vector2.from_angle(ship.angle + 90)
        point = ship.position + forward * forward_offset + left * side_offset
        return self._world_to_screen(point.to_tuple())

    def _ship_polygon(self, ship, points):
        return [self._ship_point(ship, x, y) for x, y in points]

    def _blend_color(self, color_a, color_b, amount):
        amount = max(0.0, min(1.0, amount))
        inverse = 1.0 - amount
        return tuple(
            max(0, min(255, int(color_a[index] * inverse + color_b[index] * amount)))
            for index in range(3)
        )

    def _draw_glowing_line(self, surface, start, end, color, width, alpha):
        if width <= 0 or alpha <= 0:
            return

        pygame.draw.line(surface, (*color, alpha), start, end, width)
        radius = max(1, width // 2)
        pygame.draw.circle(surface, (*color, alpha), start, radius)
        pygame.draw.circle(surface, (*color, alpha), end, radius)

    def _render_engine_plumes(self, ship, outlets):
        """Render short tapered rocket flames at engine outlets."""
        plume_surface = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        size = Config.SHIP_SIZE
        forward = Vector2.from_angle(ship.angle)
        left = Vector2.from_angle(ship.angle + 90)

        for forward_offset, side_offset, length_scale, width_scale in outlets:
            base_world = ship.position + forward * forward_offset + left * side_offset
            length = size * length_scale
            half_width = size * width_scale
            tip_world = base_world - forward * length

            base_left = base_world + left * half_width
            base_right = base_world - left * half_width
            mid_left = base_world - forward * (length * 0.48) + left * (half_width * 0.42)
            mid_right = base_world - forward * (length * 0.48) - left * (half_width * 0.42)

            outer = [
                self._world_to_screen(base_left.to_tuple()),
                self._world_to_screen(mid_left.to_tuple()),
                self._world_to_screen(tip_world.to_tuple()),
                self._world_to_screen(mid_right.to_tuple()),
                self._world_to_screen(base_right.to_tuple()),
            ]
            inner_base_left = base_world + left * (half_width * 0.48)
            inner_base_right = base_world - left * (half_width * 0.48)
            inner_tip = base_world - forward * (length * 0.72)
            inner = [
                self._world_to_screen(inner_base_left.to_tuple()),
                self._world_to_screen(inner_tip.to_tuple()),
                self._world_to_screen(inner_base_right.to_tuple()),
            ]

            glow_color = self._blend_color(ship.color, (255, 175, 70), 0.28)
            pygame.draw.polygon(plume_surface, (*glow_color, 92), outer)
            pygame.draw.polygon(plume_surface, (255, 214, 96, 150), outer[1:4])
            pygame.draw.polygon(plume_surface, (245, 252, 255, 215), inner)

        self.screen.blit(plume_surface, (0, 0))

    def _render_boost_orb(self, ship):
        """Render a flickering translucent energy orb around a boosted ship."""
        center = self._world_to_screen(ship.position.to_tuple())
        flicker_time = ship.boost_timer * 17.0
        flicker = (
            0.58
            + 0.24 * math.sin(flicker_time)
            + 0.18 * math.sin(flicker_time * 2.37 + ship.player_id)
        )
        flicker = max(0.25, min(1.0, flicker))

        base_radius = Config.SHIP_SIZE * 2.05
        radius = self._world_length_to_screen(
            base_radius + Config.SHIP_SIZE * 0.22 * flicker
        )
        surface_size = radius * 2 + 12
        orb_surface = pygame.Surface((surface_size, surface_size), pygame.SRCALPHA)
        orb_center = (surface_size // 2, surface_size // 2)

        color = ship.color
        fill_alpha = int(28 + 32 * flicker)
        inner_alpha = int(18 + 20 * flicker)
        ring_alpha = int(80 + 90 * flicker)
        spark_alpha = int(45 + 80 * flicker)

        pygame.draw.circle(orb_surface, (*color, fill_alpha), orb_center, radius)
        pygame.draw.circle(orb_surface, (255, 255, 255, inner_alpha), orb_center, int(radius * 0.72))
        pygame.draw.circle(orb_surface, (*color, ring_alpha), orb_center, radius, 2)
        pygame.draw.circle(orb_surface, (255, 255, 255, int(ring_alpha * 0.65)), orb_center, int(radius * 0.86), 1)

        for index in range(8):
            angle = flicker_time * 0.42 + index * math.pi / 4
            spark_radius = radius * (0.72 + 0.18 * math.sin(flicker_time * 1.4 + index))
            spark_pos = (
                int(orb_center[0] + math.cos(angle) * spark_radius),
                int(orb_center[1] + math.sin(angle) * spark_radius)
            )
            pygame.draw.circle(orb_surface, (255, 255, 255, spark_alpha), spark_pos, 1)

        self.screen.blit(
            orb_surface,
            (center[0] - orb_center[0], center[1] - orb_center[1])
        )

    def _render_x_wing_ship(self, ship):
        """Render an X-wing-inspired top-down fighter silhouette."""
        size = Config.SHIP_SIZE
        hull_color = (214, 214, 196)
        panel_color = (170, 170, 150)
        shadow_color = (88, 92, 86)
        canopy_color = (78, 132, 150)
        canopy_glint = (178, 226, 232)
        accent_color = ship.color
        red_marking = (175, 24, 34)
        engine_color = (142, 142, 122)
        engine_dark = (64, 67, 62)
        blaster_color = (222, 222, 198)
        laser_tip_color = (255, 75, 65)

        self._render_engine_plumes(
            ship,
            [
                (-1.12 * size, -0.52 * size, 0.90, 0.16),
                (-1.12 * size, 0.52 * size, 0.90, 0.16),
            ]
        )

        left_wing = [
            (-0.70 * size, 0.30 * size),
            (-0.96 * size, 1.36 * size),
            (-2.38 * size, 1.36 * size),
            (-2.38 * size, 0.70 * size),
            (-0.80 * size, 0.18 * size),
        ]
        right_wing = [(x, -y) for x, y in left_wing]
        for wing in (left_wing, right_wing):
            pygame.draw.polygon(self.screen, hull_color, self._ship_polygon(ship, wing))
            pygame.draw.lines(self.screen, shadow_color, True, self._ship_polygon(ship, wing), 1)

        for side in (-1, 1):
            stripe = [
                (-1.16 * size, side * 0.76 * size),
                (-2.20 * size, side * 0.92 * size),
                (-2.20 * size, side * 1.16 * size),
                (-1.10 * size, side * 1.00 * size),
            ]
            pygame.draw.polygon(self.screen, red_marking, self._ship_polygon(ship, stripe))

            blaster_base = self._ship_point(ship, -2.38 * size, side * 1.18 * size)
            blaster_tip = self._ship_point(ship, -2.86 * size, side * 1.18 * size)
            pygame.draw.line(self.screen, blaster_color, blaster_base, blaster_tip, 3)
            pygame.draw.circle(self.screen, laser_tip_color, blaster_tip, self._world_length_to_screen(size * 0.10, 2))

        for side in (-1, 1):
            engine_center = self._ship_point(ship, -0.88 * size, side * 0.52 * size)
            engine_radius = self._world_length_to_screen(size * 0.24, 4)
            pygame.draw.circle(self.screen, engine_color, engine_center, engine_radius)
            pygame.draw.circle(self.screen, shadow_color, engine_center, engine_radius, 1)
            exhaust = self._ship_point(ship, -1.12 * size, side * 0.52 * size)
            pygame.draw.circle(self.screen, engine_dark, exhaust, self._world_length_to_screen(size * 0.13, 2))

        nose = [
            (1.98 * size, 0),
            (1.30 * size, 0.22 * size),
            (0.55 * size, 0.20 * size),
            (0.18 * size, 0.12 * size),
            (0.18 * size, -0.12 * size),
            (0.55 * size, -0.20 * size),
            (1.30 * size, -0.22 * size),
        ]
        rear_body = [
            (0.30 * size, 0.24 * size),
            (-1.08 * size, 0.30 * size),
            (-1.32 * size, 0.18 * size),
            (-1.44 * size, 0),
            (-1.32 * size, -0.18 * size),
            (-1.08 * size, -0.30 * size),
            (0.30 * size, -0.24 * size),
        ]
        body = [
            (1.72 * size, 0),
            (0.34 * size, 0.28 * size),
            (-1.48 * size, 0.25 * size),
            (-1.70 * size, 0),
            (-1.48 * size, -0.25 * size),
            (0.34 * size, -0.28 * size),
        ]
        pygame.draw.polygon(self.screen, panel_color, self._ship_polygon(ship, rear_body))
        pygame.draw.lines(self.screen, shadow_color, True, self._ship_polygon(ship, rear_body), 1)
        pygame.draw.polygon(self.screen, hull_color, self._ship_polygon(ship, body))
        pygame.draw.lines(self.screen, shadow_color, True, self._ship_polygon(ship, body), 2)
        pygame.draw.polygon(self.screen, hull_color, self._ship_polygon(ship, nose))
        pygame.draw.lines(self.screen, shadow_color, True, self._ship_polygon(ship, nose), 1)

        for side in (-1, 1):
            pygame.draw.line(
                self.screen,
                red_marking,
                self._ship_point(ship, 1.12 * size, side * 0.15 * size),
                self._ship_point(ship, 0.38 * size, side * 0.16 * size),
                2
            )

        canopy = self._ship_polygon(ship, [
            (0.54 * size, 0),
            (0.16 * size, 0.18 * size),
            (-0.42 * size, 0.15 * size),
            (-0.62 * size, 0),
            (-0.42 * size, -0.15 * size),
            (0.16 * size, -0.18 * size),
        ])
        pygame.draw.polygon(self.screen, canopy_color, canopy)
        pygame.draw.line(
            self.screen,
            canopy_glint,
            self._ship_point(ship, 0.34 * size, 0.03 * size),
            self._ship_point(ship, -0.40 * size, 0.06 * size),
            1
        )
        pygame.draw.line(
            self.screen,
            accent_color,
            self._ship_point(ship, -1.50 * size, 0),
            self._ship_point(ship, -1.18 * size, 0),
            2
        )

    def _render_tie_fighter_ship(self, ship):
        """Render player 2 as a TIE-fighter-inspired silhouette."""
        size = Config.SHIP_SIZE
        panel_color = (62, 72, 82)
        panel_line_color = (150, 160, 170)
        hull_color = (190, 195, 198)
        window_color = (18, 24, 30)
        accent_color = ship.color

        self._render_engine_plumes(ship, [(-0.62 * size, 0, 1.05, 0.22)])

        for side in (-1, 1):
            panel = [
                (-0.54 * size, side * 0.72 * size),
                (0.54 * size, side * 0.72 * size),
                (0.70 * size, side * 1.02 * size),
                (0.54 * size, side * 1.42 * size),
                (-0.54 * size, side * 1.42 * size),
                (-0.70 * size, side * 1.02 * size),
            ]
            pygame.draw.polygon(self.screen, panel_color, self._ship_polygon(ship, panel))
            pygame.draw.lines(self.screen, panel_line_color, True, self._ship_polygon(ship, panel), 2)
            pygame.draw.line(
                self.screen,
                panel_line_color,
                self._ship_point(ship, 0, side * 0.78 * size),
                self._ship_point(ship, 0, side * 1.35 * size),
                1
            )
            pygame.draw.line(
                self.screen,
                panel_line_color,
                self._ship_point(ship, -0.48 * size, side * 1.02 * size),
                self._ship_point(ship, 0.48 * size, side * 1.02 * size),
                1
            )

        pygame.draw.line(
            self.screen,
            hull_color,
            self._ship_point(ship, 0, -0.78 * size),
            self._ship_point(ship, 0, 0.78 * size),
            self._world_length_to_screen(size * 0.22, 3)
        )

        center = self._world_to_screen(ship.position.to_tuple())
        pygame.draw.circle(self.screen, hull_color, center, self._world_length_to_screen(size * 0.62))
        pygame.draw.circle(self.screen, panel_line_color, center, self._world_length_to_screen(size * 0.62), 2)
        pygame.draw.circle(self.screen, window_color, center, self._world_length_to_screen(size * 0.34))

        for spoke_angle in range(0, 360, 60):
            spoke = math.radians(ship.angle + spoke_angle)
            end = (
                int(center[0] + math.cos(spoke) * size * 0.31 * Config.WORLD_SCALE),
                int(center[1] - math.sin(spoke) * size * 0.31 * Config.WORLD_SCALE)
            )
            pygame.draw.line(self.screen, accent_color, center, end, 1)

    def _render_falcon_ship(self, ship):
        """Render a Millennium-Falcon-inspired top-down freighter silhouette."""
        size = Config.SHIP_SIZE
        hull_color = (184, 188, 178)
        panel_color = (126, 132, 126)
        shadow_color = (52, 56, 54)
        dark_detail = (26, 30, 30)
        cockpit_color = (104, 142, 154)
        accent_color = ship.color

        self._render_engine_plumes(
            ship,
            [
                (-1.30 * size, -0.52 * size, 0.72, 0.13),
                (-1.34 * size, 0, 0.78, 0.16),
                (-1.30 * size, 0.52 * size, 0.72, 0.13),
            ]
        )

        center = self._world_to_screen(ship.position.to_tuple())
        body_radius = self._world_length_to_screen(size * 1.32)

        pygame.draw.circle(self.screen, hull_color, center, body_radius)
        pygame.draw.circle(self.screen, shadow_color, center, body_radius, 2)

        mandible_left = [
            (0.20 * size, 0.28 * size),
            (1.24 * size, 0.52 * size),
            (1.82 * size, 1.18 * size),
            (1.42 * size, 1.40 * size),
            (0.50 * size, 0.72 * size),
        ]
        mandible_right = [(x, -y) for x, y in mandible_left]
        for mandible in (mandible_left, mandible_right):
            pygame.draw.polygon(self.screen, hull_color, self._ship_polygon(ship, mandible))
            pygame.draw.lines(self.screen, shadow_color, False, self._ship_polygon(ship, mandible), 2)

        notch = [
            (1.28 * size, 0.34 * size),
            (1.74 * size, 0.86 * size),
            (1.58 * size, 0.22 * size),
        ]
        for side in (-1, 1):
            pygame.draw.polygon(
                self.screen,
                Config.BACKGROUND_COLOR,
                self._ship_polygon(ship, [(x, side * y) for x, y in notch])
            )

        cockpit_tube = [
            (0.00 * size, -0.86 * size),
            (0.74 * size, -1.58 * size),
            (1.20 * size, -1.62 * size),
            (1.10 * size, -1.34 * size),
            (0.18 * size, -0.68 * size),
        ]
        pygame.draw.polygon(self.screen, hull_color, self._ship_polygon(ship, cockpit_tube))
        pygame.draw.lines(self.screen, shadow_color, False, self._ship_polygon(ship, cockpit_tube), 2)
        pygame.draw.circle(self.screen, cockpit_color, self._ship_point(ship, 1.22 * size, -1.58 * size), self._world_length_to_screen(size * 0.25, 4))
        pygame.draw.circle(self.screen, shadow_color, self._ship_point(ship, 1.22 * size, -1.58 * size), self._world_length_to_screen(size * 0.25, 4), 1)

        pygame.draw.circle(self.screen, panel_color, center, self._world_length_to_screen(size * 0.50))
        pygame.draw.circle(self.screen, shadow_color, center, self._world_length_to_screen(size * 0.50), 2)
        pygame.draw.circle(self.screen, dark_detail, center, self._world_length_to_screen(size * 0.18))

        for angle_offset in range(0, 360, 45):
            angle = math.radians(ship.angle + angle_offset)
            inner = self._world_length_to_screen(size * 0.54)
            outer = self._world_length_to_screen(size * 1.16)
            start = (int(center[0] + math.cos(angle) * inner), int(center[1] - math.sin(angle) * inner))
            end = (int(center[0] + math.cos(angle) * outer), int(center[1] - math.sin(angle) * outer))
            pygame.draw.line(self.screen, panel_color, start, end, 1)

        for x, y in ((-0.42, 0.58), (-0.58, -0.52), (-0.88, 0.08), (0.40, 0.76), (0.42, -0.76)):
            detail_center = self._ship_point(ship, x * size, y * size)
            pygame.draw.circle(self.screen, shadow_color, detail_center, self._world_length_to_screen(size * 0.13, 2), 1)

        for side in (-1, 1):
            pygame.draw.line(
                self.screen,
                dark_detail,
                self._ship_point(ship, -0.78 * size, side * 0.72 * size),
                self._ship_point(ship, -1.18 * size, side * 0.46 * size),
                2
            )
            pygame.draw.line(
                self.screen,
                accent_color,
                self._ship_point(ship, 0.54 * size, side * 0.40 * size),
                self._ship_point(ship, 1.08 * size, side * 0.74 * size),
                1
            )

        engine_points = []
        for index in range(9):
            side = -1.0 + index * 0.25
            engine_points.append(self._ship_point(ship, -1.26 * size, side * 0.76 * size))
        if len(engine_points) >= 2:
            pygame.draw.lines(self.screen, (116, 206, 255), False, engine_points, 2)

    def render_ship_explosion(self, ship):
        """Render ship explosion particles."""
        progress = 1.0 - (ship.explosion_timer / Config.SHIP_EXPLOSION_DURATION)
        progress = max(0.0, min(1.0, progress))
        fade = 1.0 - progress
        center = self._world_to_screen(ship.position.to_tuple())

        shock_radius = self._world_length_to_screen(
            Config.SHIP_SIZE * (1.2 + progress * 3.0)
        )
        shock_alpha = int(120 * fade)
        if shock_alpha > 0:
            shock_surface = pygame.Surface((shock_radius * 2 + 4, shock_radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(
                shock_surface,
                (255, 220, 120, shock_alpha),
                (shock_radius + 2, shock_radius + 2),
                shock_radius,
                2
            )
            self.screen.blit(shock_surface, (center[0] - shock_radius - 2, center[1] - shock_radius - 2))

        for particle in ship.explosion_particles:
            distance = particle["speed"] * progress * Config.SHIP_EXPLOSION_DURATION
            particle_pos = ship.position + particle["direction"] * distance
            screen_pos = self._world_to_screen(particle_pos.to_tuple())
            radius = self._world_length_to_screen(particle["size"] * fade)
            color = self._scale_color(particle["color"], 0.45 + fade * 0.9)
            pygame.draw.circle(self.screen, color, screen_pos, radius)
    
    def render_trail(self, ship):
        """Render ship trail (may be multiple disconnected segments)"""
        current_segment = list(ship.current_segment)
        if ship.alive:
            trail_origin = ship.get_trail_origin()
            if len(current_segment) == 0 or trail_origin.distance_to(current_segment[-1]) > 1:
                current_segment.append(trail_origin)

        total_points = sum(len(segment) for segment in ship.trail_segments) + len(current_segment)
        if total_points < 2:
            return

        trail_surface = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        point_index = 0
        
        def draw_trail_segment(segment):
            """Helper to draw a single trail segment"""
            nonlocal point_index
            if len(segment) < 2:
                point_index += len(segment)
                return
            
            # Build list of connected points (breaking on large gaps)
            current_line = []
            current_indices = []
            
            for i, point in enumerate(segment):
                screen_point = self._world_to_screen(point.to_tuple())
                
                if len(current_line) == 0:
                    # First point
                    current_line.append(screen_point)
                    current_indices.append(point_index)
                else:
                    # Check if this point is connected to previous (in world space)
                    prev_world_point = segment[i - 1]
                    world_distance = point.distance_to(prev_world_point)
                    
                    # If distance is reasonable (less than expected spacing * 3), it's connected
                    if world_distance < Config.TRAIL_SEGMENT_SPACING * 3:
                        current_line.append(screen_point)
                        current_indices.append(point_index)
                    else:
                        # Gap detected - draw current line and start new one
                        if len(current_line) >= 2:
                            draw_connected_line(current_line, current_indices)
                        current_line = [screen_point]
                        current_indices = [point_index]
                point_index += 1
            
            # Draw final line segment
            if len(current_line) >= 2:
                draw_connected_line(current_line, current_indices)

        def draw_connected_line(points, indices):
            for i in range(1, len(points)):
                freshness = indices[i] / max(1, total_points - 1)
                shaped_freshness = freshness ** 1.35

                core_width = self._world_length_to_screen(
                    1 + shaped_freshness * (Config.TRAIL_WIDTH + 3)
                )
                glow_width = max(core_width + 3, int(core_width * 3.2))
                hot_width = max(1, int(core_width * 0.38))

                edge_color = self._blend_color(ship.trail_color, ship.color, 0.45 + 0.35 * shaped_freshness)
                warm_color = self._blend_color(edge_color, (255, 190, 70), 0.22 * shaped_freshness)
                core_color = self._blend_color(warm_color, (245, 252, 255), 0.58 * shaped_freshness)

                glow_alpha = int(16 + shaped_freshness * 76)
                edge_alpha = int(75 + shaped_freshness * 130)
                core_alpha = int(100 + shaped_freshness * 125)

                self._draw_glowing_line(trail_surface, points[i - 1], points[i], warm_color, glow_width, glow_alpha)
                self._draw_glowing_line(trail_surface, points[i - 1], points[i], edge_color, core_width, edge_alpha)
                self._draw_glowing_line(trail_surface, points[i - 1], points[i], core_color, hot_width, core_alpha)
        
        # Render old segments
        for segment in ship.trail_segments:
            draw_trail_segment(segment)
        
        # Render current segment
        draw_trail_segment(current_segment)

        self.screen.blit(trail_surface, (0, 0))
    
    def render_star(self, star):
        """Render a star"""
        if not star.active:
            return
        
        center = self._world_to_screen(star.position.to_tuple())
        size = self._world_length_to_screen(star.visual_size, 3)
        brightness = star.brightness

        glow_radius = int(size * 3.2)
        glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        glow_center = (glow_radius, glow_radius)

        for i, alpha in enumerate((34, 24, 14)):
            radius = int(glow_radius * (1.0 - i * 0.25))
            glow_alpha = min(80, int(alpha * brightness))
            pygame.draw.circle(
                glow_surface,
                (*star.glow_color, glow_alpha),
                glow_center,
                radius
            )

        self.screen.blit(glow_surface, (center[0] - glow_radius, center[1] - glow_radius))

        points = []
        for i in range(16):
            angle = -math.pi / 2 + i * math.pi / 8
            if i % 2 == 0:
                radius = size * (1.55 if i % 4 == 0 else 1.18)
            else:
                radius = size * 0.48
            points.append((
                center[0] + math.cos(angle) * radius,
                center[1] + math.sin(angle) * radius
            ))

        star_color = self._scale_color(star.color, brightness)
        core_color = self._scale_color(star.core_color, brightness)
        pygame.draw.polygon(self.screen, star_color, points)
        pygame.draw.circle(self.screen, core_color, center, max(2, int(size * 0.45)))

    def render_super_blade(self, blade):
        """Render a temporary rotating blade made from ship-tail energy."""
        if not blade.active:
            return

        blade_surface = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        life_fraction = max(0.0, min(1.0, blade.timer / Config.SUPER_BLADE_DURATION))
        pulse = 0.75 + 0.25 * math.sin(time.perf_counter() * 18.0)
        core_width = self._world_length_to_screen(Config.SUPER_BLADE_WIDTH, 2)
        glow_width = max(core_width + 8, int(core_width * 5.8))
        hot_width = max(1, int(core_width * 0.34))

        edge_color = self._blend_color(blade.color, (80, 205, 255), 0.25)
        core_color = self._blend_color(edge_color, (245, 252, 255), 0.72)
        glow_alpha = int((20 + 18 * pulse) * life_fraction)
        edge_alpha = int((68 + 28 * pulse) * life_fraction)
        core_alpha = int((118 + 32 * pulse) * life_fraction)
        center = self._world_to_screen(blade.position.to_tuple())
        center_radius = self._world_length_to_screen(Config.SUPER_BLADE_WIDTH * 3.0, 3)
        pygame.draw.circle(
            blade_surface,
            (*edge_color, int(54 * life_fraction)),
            center,
            center_radius
        )
        pygame.draw.circle(
            blade_surface,
            (*core_color, int(132 * life_fraction)),
            center,
            max(2, center_radius // 3)
        )

        for index, (start, end) in enumerate(blade.blade_segments()):
            screen_start = self._world_to_screen(start.to_tuple())
            screen_end = self._world_to_screen(end.to_tuple())
            spoke_scale = 1.0 if index == 0 else 0.78 if index in (2, 4) else 0.58
            self._draw_glowing_line(
                blade_surface,
                screen_start,
                screen_end,
                edge_color,
                max(1, int(glow_width * spoke_scale)),
                glow_alpha
            )
            self._draw_glowing_line(
                blade_surface,
                screen_start,
                screen_end,
                blade.color,
                max(1, int(core_width * spoke_scale)),
                edge_alpha
            )
            self._draw_glowing_line(
                blade_surface,
                screen_start,
                screen_end,
                core_color,
                hot_width,
                int(core_alpha * spoke_scale)
            )

        self.screen.blit(blade_surface, (0, 0))
    
    def render_mine(self, mine):
        """Render a mine"""
        if not mine.active:
            return
        
        center = self._world_to_screen(mine.position.to_tuple())
        angle = math.radians(mine.angle)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        def rotate_point(point):
            return (
                center[0] + (point.x * cos_a - point.y * sin_a) * Config.WORLD_SCALE,
                center[1] + (point.x * sin_a + point.y * cos_a) * Config.WORLD_SCALE
            )

        points = [rotate_point(point) for point in mine.shape_points]
        pygame.draw.polygon(self.screen, mine.color, points)
        pygame.draw.lines(self.screen, mine.outline_color, True, points, 2)

        for crater in mine.craters:
            crater_center = rotate_point(crater["offset"])
            crater_radius = self._world_length_to_screen(crater["radius"], 2)
            pygame.draw.circle(self.screen, mine.crater_color, crater_center, crater_radius)
            pygame.draw.circle(self.screen, mine.outline_color, crater_center, crater_radius, 1)
    
    def render_text(self, text, position, color=(255, 255, 255), small=False):
        """Render text on screen"""
        font = self.small_font if small else self.font
        text_surface = font.render(text, True, color)
        self.screen.blit(text_surface, position)

    def _scale_color(self, color, brightness):
        """Scale RGB color brightness while clamping to display range."""
        return tuple(max(0, min(255, int(component * brightness))) for component in color)

    def _format_boost_timer(self, ship):
        """Format active boost remaining time for HUD."""
        return f"BOOST {max(0.0, ship.boost_timer):.1f}s"
    
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
            boost_text = self._format_boost_timer(game_state.ships[1])
            self.render_text(boost_text, (10, y_offset + 25),
                             (255, 255, 0), small=True)
        
        # Player 2 status (top-right) - for two-player
        if game_state.num_players == 2:
            p2_text = f"P2 Score: {game_state.scores[2]}"
            p2_text += f" | Wins: {game_state.kills[2]}"
            text_surface = self.small_font.render(p2_text, True, Config.SHIP_COLOR_P2)
            self.screen.blit(text_surface, 
                            (Config.WINDOW_WIDTH - text_surface.get_width() - 10, y_offset))
            
            if 2 in game_state.ships and game_state.ships[2].boost_active:
                boost_text = self._format_boost_timer(game_state.ships[2])
                boost_surface = self.small_font.render(boost_text, True, (255, 255, 0))
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

        self._render_switch_debug(game_state)

    def render_throttle_overlay(self, game_state, controller):
        """Render persistent side throttle strips with virtual wall markers."""
        if not Config.SHOW_THROTTLE_OVERLAY or controller is None:
            return

        active_players = [
            player_id for player_id in (1, 2)
            if player_id in game_state.ships
        ]
        for player_id in active_players:
            throttle = controller.get_throttle(player_id)
            self._render_player_throttle_strip(
                player_id,
                game_state.ships[player_id],
                throttle
            )

    def _render_player_throttle_strip(self, player_id, ship, throttle):
        """Render one player's translucent throttle strip on the matching screen edge."""
        width = max(12, int(Config.THROTTLE_OVERLAY_WIDTH))
        margin_y = max(16, int(Config.THROTTLE_OVERLAY_MARGIN_Y))
        height = max(80, Config.WINDOW_HEIGHT - margin_y * 2)
        x = 0 if player_id == 1 else Config.WINDOW_WIDTH - width
        y = margin_y

        player_color = Config.SHIP_COLOR_P1 if player_id == 1 else Config.SHIP_COLOR_P2
        strip = pygame.Surface((width, height), pygame.SRCALPHA)
        strip.fill((*player_color, Config.THROTTLE_OVERLAY_ALPHA))

        rear_wall, normal_forward_wall = self._get_throttle_wall_markers()
        forward_extension = (
            Config.BOOST_THROTTLE_FORWARD_EXTENSION_DEG
            if ship.boost_active
            else 0.0
        )
        _boost_rear_wall, active_forward_wall = self._get_throttle_wall_markers(
            forward_extension
        )
        _unused_rear_wall, max_forward_wall = self._get_throttle_wall_markers(
            Config.BOOST_THROTTLE_FORWARD_EXTENSION_DEG
        )

        center_y = self._throttle_value_to_strip_y(
            0.0,
            height,
            rear_wall,
            max_forward_wall
        )
        pygame.draw.line(
            strip,
            (235, 245, 255, Config.THROTTLE_OVERLAY_CENTER_LINE_ALPHA),
            (4, center_y),
            (width - 4, center_y),
            1
        )

        clamped_throttle = max(rear_wall, min(active_forward_wall, throttle))
        throttle_y = self._throttle_value_to_strip_y(
            clamped_throttle,
            height,
            rear_wall,
            max_forward_wall
        )
        marker_radius = 5
        forward_wall_y = self._throttle_value_to_strip_y(
            active_forward_wall,
            height,
            rear_wall,
            max_forward_wall
        )
        throttle_y = max(forward_wall_y + marker_radius + 1, throttle_y)
        fill_top = min(center_y, throttle_y)
        fill_height = max(3, abs(center_y - throttle_y))
        fill_color = self._blend_color(player_color, (255, 255, 255), 0.24)
        pygame.draw.rect(
            strip,
            (*fill_color, 150),
            pygame.Rect(5, fill_top, width - 10, fill_height),
            border_radius=3
        )
        pygame.draw.circle(
            strip,
            (245, 250, 255, 230),
            (width // 2, throttle_y),
            marker_radius
        )

        if ship.boost_active:
            self._draw_open_throttle_wall(
                strip,
                normal_forward_wall,
                ship.boost_timer,
                rear_wall,
                max_forward_wall
            )
            self._draw_throttle_wall(
                strip,
                active_forward_wall,
                Config.STAR_COLOR,
                rear_wall,
                max_forward_wall
            )
        else:
            self._draw_throttle_wall(
                strip,
                normal_forward_wall,
                (245, 245, 245),
                rear_wall,
                max_forward_wall
            )

        self.screen.blit(strip, (x, y))

    def _get_throttle_wall_markers(self, forward_extension_deg=0.0):
        """Return normalized rear and forward throttle wall positions."""
        scale = 360.0 * Config.THROTTLE_CONTROL_ROTATION_RANGE
        if scale <= 0:
            return (-1.0, 1.0)

        rear_limit = (Config.THROTTLE_MOTION_RANGE_DEG / 2.0) / scale
        forward_limit = (
            (Config.THROTTLE_MOTION_RANGE_DEG / 2.0) + forward_extension_deg
        ) / scale
        return (-rear_limit, forward_limit)

    def _throttle_value_to_strip_y(self, value, height, rear_limit, max_forward_limit):
        """Map throttle to fixed reverse and forward display ranges."""
        center_y = height // 2
        if value <= 0.0:
            reverse_span = max(0.001, abs(rear_limit))
            clamped_value = max(rear_limit, min(0.0, value))
            reverse_fraction = abs(clamped_value) / reverse_span
            return int(center_y + reverse_fraction * ((height - 1) - center_y))

        forward_span = max(0.001, max_forward_limit)
        clamped_value = max(0.0, min(max_forward_limit, value))
        forward_fraction = clamped_value / forward_span
        return int(center_y - forward_fraction * center_y)

    def _draw_throttle_wall(self, strip, value, color, rear_limit, forward_limit):
        y = self._throttle_value_to_strip_y(
            value,
            strip.get_height(),
            rear_limit,
            forward_limit
        )
        alpha = Config.THROTTLE_OVERLAY_WALL_ALPHA
        pygame.draw.line(strip, (*color, alpha), (2, y), (strip.get_width() - 3, y), 2)
        point = [(strip.get_width() // 2, y - 5), (7, y), (strip.get_width() - 7, y)]
        pygame.draw.polygon(strip, (*color, min(230, alpha + 35)), point)

    def _draw_open_throttle_wall(self, strip, value, boost_timer, rear_limit, forward_limit):
        y = self._throttle_value_to_strip_y(
            value,
            strip.get_height(),
            rear_limit,
            forward_limit
        )
        pulse = 0.55 + 0.45 * math.sin(max(0.0, boost_timer) * 16.0)
        alpha = int(42 + 62 * pulse)
        color = Config.STAR_COLOR
        gap = max(5, strip.get_width() // 4)
        mid = strip.get_width() // 2
        pygame.draw.line(strip, (*color, alpha), (2, y), (mid - gap, y), 2)
        pygame.draw.line(strip, (*color, alpha), (mid + gap, y), (strip.get_width() - 3, y), 2)

    def _render_switch_debug(self, game_state):
        """Render latest Teensy switch values for hardware verification."""
        difficulty = getattr(game_state, 'hardware_difficulty_switch', None)
        p2_enabled = getattr(game_state, 'hardware_player2_enabled', None)
        pin25_active = getattr(game_state, 'hardware_pin25_active', None)
        pin26_active = getattr(game_state, 'hardware_pin26_active', None)
        pin9_active = getattr(game_state, 'hardware_pin9_active', None)

        if difficulty is None and p2_enabled is None:
            return

        profile = Config.DIFFICULTY_PROFILES.get(difficulty, {})
        difficulty_name = profile.get("name", "unknown")
        difficulty_text = (
            f"Primary 3-way switch: {difficulty} ({difficulty_name})"
            if difficulty is not None
            else "Primary 3-way switch: --"
        )
        p2_text = (
            f"Optional 2-way switch: {'enabled' if p2_enabled else 'disabled'}"
            if p2_enabled is not None
            else "Optional 2-way switch: --"
        )
        state_text = (
            f"{difficulty_text} | {p2_text} | "
            f"Players: {game_state.num_players} | Asteroids: {len(game_state.mines)}"
        )

        surface = self.small_font.render(state_text, True, (180, 220, 230))
        x = (Config.WINDOW_WIDTH - surface.get_width()) // 2
        y = 36 if game_state.num_players == 1 else 34
        self.screen.blit(surface, (x, y))

        if pin25_active is not None or pin26_active is not None or pin9_active is not None:
            raw_text = (
                f"Active pins: 25={1 if pin25_active else 0} | "
                f"26={1 if pin26_active else 0} | 9={1 if pin9_active else 0}"
            )
            raw_surface = self.small_font.render(raw_text, True, (220, 220, 120))
            raw_x = (Config.WINDOW_WIDTH - raw_surface.get_width()) // 2
            self.screen.blit(raw_surface, (raw_x, y + 18))

        change_time = getattr(game_state, 'hardware_switch_change_time', None)
        change_message = getattr(game_state, 'hardware_switch_change_message', "")
        if change_time is None:
            return

        age = time.perf_counter() - change_time
        if age > 2.0:
            return

        alpha = max(80, int(255 * (1.0 - age / 2.0)))
        banner_text = f"SWITCH CHANGE DETECTED: {change_message}"
        banner_surface = self.small_font.render(banner_text, True, (255, 255, 255))
        padding_x = 12
        padding_y = 5
        banner_rect = pygame.Rect(
            (Config.WINDOW_WIDTH - banner_surface.get_width()) // 2 - padding_x,
            y + 24,
            banner_surface.get_width() + padding_x * 2,
            banner_surface.get_height() + padding_y * 2
        )
        fill = pygame.Surface(banner_rect.size, pygame.SRCALPHA)
        fill.fill((20, 140, 80, alpha))
        self.screen.blit(fill, banner_rect.topleft)
        pygame.draw.rect(self.screen, (120, 255, 170), banner_rect, 2)
        self.screen.blit(
            banner_surface,
            (banner_rect.x + padding_x, banner_rect.y + padding_y)
        )
    
    def _world_to_screen(self, world_pos):
        """
        Convert world coordinates (origin at center, y-up) to 
        screen coordinates (origin at top-left, y-down)
        
        Args:
            world_pos: tuple (x, y)
        
        Returns:
            tuple: (screen_x, screen_y)
        """
        screen_x = world_pos[0] * Config.WORLD_SCALE + Config.WINDOW_WIDTH / 2
        screen_y = Config.WINDOW_HEIGHT / 2 - world_pos[1] * Config.WORLD_SCALE
        return (int(screen_x), int(screen_y))

    def _world_length_to_screen(self, world_length, minimum=1):
        """Convert a world-space length to screen pixels using the current zoom."""
        return max(minimum, int(round(world_length * Config.WORLD_SCALE)))
    
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
        
        radius = self._world_length_to_screen(Config.SPAWN_SAFE_ZONE_MARGIN)
        for start_config in Config.PLAYER_STARTS.values():
            center = self._world_to_screen(start_config["position"])
            pygame.draw.circle(self.screen, (100, 100, 100), center, radius, 2)
