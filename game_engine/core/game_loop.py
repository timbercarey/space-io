"""
Main game loop
"""
import copy
import math
import threading
import time

import pygame
from config import Config
from utils import Vector2

class GameLoop:
    def __init__(
        self,
        game_state,
        controller,
        renderer,
        force_calculator=None,
        force_visualizer=None,
        audio_manager=None
    ):
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
        self.audio_manager = audio_manager
        self.clock = pygame.time.Clock()
        self.return_to_menu = False
        self.audio_events = []
        self.help_panel_visible = False
        self.volume_panel_visible = False
        self.dragging_volume_slider = None
        self.state_lock = threading.RLock()
        self.control_stop_event = threading.Event()
        self.control_thread = None
        self.last_hardware_difficulty = None
        self.last_hardware_player2_enabled = None
        self.trail_death_erm_timers = {1: 0.0, 2: 0.0}
    
    def run(self):
        """Main game loop"""
        with self.state_lock:
            self._zero_current_hardware_inputs()
        self._start_control_thread()
        try:
            while self._is_running():
                self.clock.tick(Config.FPS)
                with self.state_lock:
                    self.game_state.fps = self.clock.get_fps()

                # Pygame event handling and rendering stay on the main thread.
                self._handle_events()
                self._render()
        finally:
            self._stop_control_thread()
            if self.force_calculator and hasattr(self.force_calculator, 'close'):
                self.force_calculator.close()
            if self.audio_manager:
                self.audio_manager.stop_engine()
            self.controller.close()

        return "menu" if self.return_to_menu else "quit"

    def _start_control_thread(self):
        """Start the high-rate physics/control worker."""
        if self.control_thread and self.control_thread.is_alive():
            return

        self.control_stop_event.clear()
        self.control_thread = threading.Thread(
            target=self._run_control_loop,
            name="game-control-loop",
            daemon=True
        )
        self.control_thread.start()

    def _stop_control_thread(self):
        """Stop the high-rate physics/control worker."""
        self.control_stop_event.set()
        if self.control_thread:
            self.control_thread.join(timeout=1.0)
            self.control_thread = None
        if hasattr(self.controller, 'stop_forces'):
            self.controller.stop_forces()

    def _run_control_loop(self):
        """Run input, physics, collision checks, haptics, and force output."""
        interval = 1.0 / max(1.0, float(Config.CONTROL_LOOP_FREQUENCY_HZ))
        next_tick = time.perf_counter()
        last_tick = next_tick

        while not self.control_stop_event.is_set():
            now = time.perf_counter()
            if now < next_tick:
                time.sleep(min(next_tick - now, interval))
                continue

            dt = now - last_tick
            last_tick = now

            with self.state_lock:
                if not self.game_state.running:
                    break

                self.controller.update()
                self._sync_hardware_game_switches()
                self._update_trail_death_erm_pulse(dt)
                self._update(dt)
                self._check_collisions()

                if self.force_calculator:
                    self.force_calculator.update(dt, self.game_state, self.controller)

                self._send_haptic_forces()

            next_tick += interval
            if next_tick < now - interval:
                next_tick = now + interval

    def _is_running(self):
        """Read running state safely from the main/render thread."""
        with self.state_lock:
            return self.game_state.running
    
    def _handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if self._handle_volume_panel_event(event):
                continue

            if event.type == pygame.QUIT:
                with self.state_lock:
                    self.game_state.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    with self.state_lock:
                        self.game_state.running = False
                elif event.key == pygame.K_BACKSPACE:
                    with self.state_lock:
                        self._return_to_menu()
                elif event.key == pygame.K_f:
                    self._toggle_fullscreen()
                elif event.key == pygame.K_SPACE:
                    with self.state_lock:
                        if self.game_state.game_over:
                            if self._is_round_over_pending_next_round(self.game_state):
                                continue

                            self._return_to_menu()
                elif event.key == pygame.K_r:
                    with self.state_lock:
                        self._restart_game()
                elif event.key == pygame.K_h:
                    self.help_panel_visible = not self.help_panel_visible
                elif event.key == pygame.K_v:
                    # Toggle haptic visualization
                    Config.SHOW_HAPTIC_PANEL = not Config.SHOW_HAPTIC_PANEL
                elif event.key == pygame.K_b:
                    # Toggle hitbox display
                    Config.SHOW_HITBOXES = not Config.SHOW_HITBOXES
                elif event.key == pygame.K_s and event.mod & pygame.KMOD_SHIFT:
                    self.volume_panel_visible = not self.volume_panel_visible
                elif event.key == pygame.K_m and self.audio_manager:
                    self.audio_manager.toggle_music()
                elif event.key == pygame.K_n and self.audio_manager:
                    self.audio_manager.toggle_sfx()
                elif event.key == pygame.K_t and self.audio_manager:
                    track_name = self.audio_manager.switch_music_track()
                    if track_name:
                        print(f"Music track: {track_name}")
                elif event.key == pygame.K_z:
                    # Calibrate current hardware controller positions as zero.
                    if hasattr(self.controller, 'zero_inputs'):
                        with self.state_lock:
                            self._zero_current_hardware_inputs()
                        print("Hardware inputs zeroed")

    def _toggle_fullscreen(self):
        """Toggle fullscreen and update surfaces used by render helpers."""
        Config.FULLSCREEN = not Config.FULLSCREEN
        if Config.FULLSCREEN:
            screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            screen = pygame.display.set_mode(
                (Config.WINDOWED_WIDTH, Config.WINDOWED_HEIGHT)
            )
        Config.set_display_size(screen.get_size())
        self.renderer.screen = screen
        if self.force_visualizer:
            self.force_visualizer.screen = screen

    def _restart_game(self):
        """Restart the current game mode without returning to the menu."""
        self.return_to_menu = False
        self.trail_death_erm_timers = {1: 0.0, 2: 0.0}
        self.game_state.reset()
        self._zero_current_hardware_inputs()

    def _return_to_menu(self):
        """Return from the active game loop to the main menu."""
        self._queue_audio("return_to_menu")
        self.return_to_menu = True
        self.game_state.running = False

    def _zero_current_hardware_inputs(self):
        """Treat current hardware steering/throttle positions as neutral."""
        if not hasattr(self.controller, 'zero_inputs'):
            return

        player_ids = list(self.game_state.ships.keys())
        self.controller.zero_inputs(player_ids)

    def _sync_hardware_game_switches(self):
        """Apply Teensy game-mode switches to the active game."""
        if not hasattr(self.controller, 'get_control_switch_snapshot'):
            return

        controls = self.controller.get_control_switch_snapshot()
        difficulty = controls.get('difficulty')
        player2_enabled = controls.get('player2_enabled')
        self.game_state.hardware_switch_packet_received = controls.get('received', False)
        self.game_state.hardware_pin25_active = controls.get('pin25_active')
        self.game_state.hardware_pin26_active = controls.get('pin26_active')
        self.game_state.hardware_pin9_active = controls.get('pin9_active')

        if not self.game_state.hardware_switch_packet_received:
            return

        changes = []
        if difficulty is not None:
            self.game_state.hardware_difficulty_switch = difficulty
            if (
                Config.USE_HARDWARE_DIFFICULTY_SWITCH
                and difficulty != self.last_hardware_difficulty
            ):
                self.game_state.apply_difficulty(difficulty)
                changes.append(f"3-way -> {difficulty}")
                self.last_hardware_difficulty = difficulty

        if player2_enabled is not None:
            self.game_state.hardware_player2_enabled = player2_enabled
            if player2_enabled != self.last_hardware_player2_enabled:
                changed = self.game_state.set_player2_enabled(player2_enabled)
                changes.append(
                    "2-way -> enabled"
                    if player2_enabled
                    else "2-way -> disabled"
                )
                self.last_hardware_player2_enabled = player2_enabled
                if changed:
                    self._zero_current_hardware_inputs()

        if changes:
            self.game_state.hardware_switch_change_time = time.perf_counter()
            self.game_state.hardware_switch_change_message = ", ".join(changes)
    
    def _update(self, dt):
        """Update game state"""
        for star in self.game_state.stars:
            star.update(dt)
        self.game_state.update_super_star_system(dt)

        for ship in self.game_state.ships.values():
            ship.update_explosion(dt)
        
        # Handle countdown
        if self.game_state.countdown_active:
            self.game_state.countdown_timer -= dt
            if self.game_state.countdown_timer <= 0:
                self.game_state.countdown_active = False
            return  # Don't update ships during countdown
        
        # Don't update ships if game is over
        if self.game_state.game_over:
            if self._is_round_over_pending_next_round(self.game_state):
                if self.game_state.round_restart_timer is None:
                    self.game_state.round_restart_timer = Config.RESPAWN_DELAY

                self.game_state.round_restart_timer -= dt
                if self.game_state.round_restart_timer <= 0:
                    if not self.game_state.start_new_round():
                        self.game_state.round_restart_timer = None
                return

            if self.game_state.game_over_return_timer is not None:
                self.game_state.game_over_return_timer -= dt
                if self.game_state.game_over_return_timer <= 0:
                    if self.game_state.num_players == 1:
                        self._restart_game()
                    else:
                        self._queue_audio("return_to_menu")
                        self.return_to_menu = True
                        self.game_state.running = False
            return

        for mine in self.game_state.mines:
            mine.update(dt)
        
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
                    self._queue_audio("star_pickup")
                    self._queue_audio("boost")
                    if self.force_calculator:
                        self.force_calculator.trigger_star_boost(player_id)
                    if self.game_state.num_players == 1:
                        self.game_state.scores[player_id] += 100
                    # Respawn star after collection
                    self.game_state.respawn_star(i)

            # Check rare super star collision
            if (
                self.game_state.super_star
                and self.game_state.super_star.check_collision(ship.position, Config.SHIP_SIZE)
            ):
                if self.game_state.collect_super_star(player_id):
                    self._queue_audio("star_pickup")
                    if self.game_state.num_players == 1:
                        self.game_state.scores[player_id] += 250

            # Super blades only kill players who did not spawn them.
            if self.game_state.num_players == 2:
                for blade in self.game_state.super_blades:
                    if blade.check_collision(player_id, ship.position, Config.SHIP_SIZE):
                        self._handle_ship_death(player_id, ship)
                        return
            
            # Check mine collisions
            for mine in self.game_state.mines:
                if mine.check_collision(ship.position, Config.SHIP_SIZE):
                    if ship.can_bounce_off_asteroid():
                        bounce_normal = ship.bounce_off_asteroid(mine)
                        if self.force_calculator:
                            self.force_calculator.trigger_asteroid_bounce(
                                player_id,
                                self._asteroid_bounce_steering_direction(ship, bounce_normal)
                            )
                        self._queue_audio("asteroid_bounce")
                        break

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
                            self._arm_round_restart_if_needed()
                            self._queue_audio("mine_explosion")
                            self._queue_audio("round_win")
                            
                            self._trigger_trail_death_erm_pulse(player_id)
                            if self.force_calculator:
                                self.force_calculator.trigger_trail_death(player_id)
                            
                            return  # Exit immediately after death
            
            # Update trail vibration effect based on proximity to trails
            if self.force_calculator and ship.alive:
                near_trail = self._check_near_trail(ship, player_id)
                if near_trail:
                    self.force_calculator.trigger_trail_collision(player_id)
                else:
                    self.force_calculator.clear_trail_collision(player_id)

                near_super_blade = self._check_near_super_blade(ship)
                if near_super_blade:
                    self.force_calculator.trigger_super_blade_proximity(player_id)
                else:
                    self.force_calculator.clear_super_blade_proximity(player_id)

    def _handle_ship_death(self, player_id, ship):
        """Handle ship death and end round"""
        ship.start_explosion()
        ship.kill()
        self._queue_audio("mine_explosion")
        
        # Trigger haptic effect
        if self.force_calculator:
            self.force_calculator.trigger_mine_hit(player_id)
        
        # In two-player, declare winner and freeze both ships
        if self.game_state.num_players == 2:
            other_player = 2 if player_id == 1 else 1
            self.game_state.declare_winner(other_player)
            self._arm_round_restart_if_needed()
            self._queue_audio("round_win")
            
            # Kill other player too to freeze them
            if other_player in self.game_state.ships:
                self.game_state.ships[other_player].kill()
        else:
            # Single player - just game over
            self.game_state.game_over = True
            self.game_state.game_over_return_timer = Config.SINGLE_PLAYER_RESTART_DELAY

    def _arm_round_restart_if_needed(self):
        """Start the automatic next-round timer after a non-final 2P round."""
        if self._is_round_over_pending_next_round(self.game_state):
            self.game_state.round_restart_timer = Config.RESPAWN_DELAY

    def _trigger_trail_death_erm_pulse(self, player_id):
        """Pulse the ERMs for trail deaths without applying motor kickback."""
        self.trail_death_erm_timers[player_id] = Config.TRAIL_DEATH_ERM_DURATION

    def _update_trail_death_erm_pulse(self, dt):
        """Advance the ERM pulse timer used for opponent-trail deaths."""
        for player_id, timer in self.trail_death_erm_timers.items():
            if timer > 0.0:
                self.trail_death_erm_timers[player_id] = max(0.0, timer - dt)

    def _queue_audio(self, name):
        """Queue an audio event to be played from the render thread."""
        if self.audio_manager:
            self.audio_events.append(name)

    def _handle_volume_panel_event(self, event):
        """Handle mouse interaction for the live volume panel."""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_s and event.mod & pygame.KMOD_SHIFT:
            self.volume_panel_visible = not self.volume_panel_visible
            return True

        if not self.volume_panel_visible or not self.audio_manager:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            slider = self._volume_slider_at(event.pos)
            if slider:
                self.dragging_volume_slider = slider
                self._set_volume_from_mouse(slider, event.pos[0])
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging_volume_slider:
                self.dragging_volume_slider = None
                return True
        elif event.type == pygame.MOUSEMOTION and self.dragging_volume_slider:
            self._set_volume_from_mouse(self.dragging_volume_slider, event.pos[0])
            return True

        return False

    def _check_near_super_blade(self, ship):
        """Return True when a ship is close enough to feel an active super blade."""
        warning_distance = Config.SUPER_BLADE_PROXIMITY_DISTANCE + Config.SHIP_SIZE
        return any(
            blade.is_near(ship.position, warning_distance)
            for blade in self.game_state.super_blades
        )

    def _volume_panel_rects(self):
        panel = pygame.Rect(Config.WINDOW_WIDTH - 400, 90, 340, 225)
        slider_x = panel.x + 110
        slider_width = 150
        return {
            "panel": panel,
            "music": pygame.Rect(slider_x, panel.y + 58, slider_width, 14),
            "sfx": pygame.Rect(slider_x, panel.y + 104, slider_width, 14),
            "engine": pygame.Rect(slider_x, panel.y + 150, slider_width, 14),
        }

    def _volume_slider_at(self, mouse_pos):
        rects = self._volume_panel_rects()
        for name in ("music", "sfx", "engine"):
            hit_rect = rects[name].inflate(16, 24)
            if hit_rect.collidepoint(mouse_pos):
                return name
        return None

    def _set_volume_from_mouse(self, slider_name, mouse_x):
        rect = self._volume_panel_rects()[slider_name]
        value = (mouse_x - rect.x) / rect.width
        value = max(0.0, min(1.0, value))
        if slider_name == "music":
            self.audio_manager.set_music_volume(value)
        elif slider_name == "sfx":
            self.audio_manager.set_sfx_volume(value)
        elif slider_name == "engine":
            self.audio_manager.set_engine_volume(value)

    def _asteroid_bounce_steering_direction(self, ship, bounce_normal):
        """Choose haptic steering impulse direction from contact side."""
        ship_right = Vector2.from_angle(ship.angle - 90)
        return 1.0 if bounce_normal.dot(ship_right) >= 0 else -1.0

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
        with self.state_lock:
            render_state = copy.deepcopy(self.game_state)
            audio_events = self.audio_events
            self.audio_events = []

        self.renderer.clear()
        if self.audio_manager:
            for event_name in audio_events:
                self.audio_manager.play(event_name)
            self.audio_manager.update_engine(render_state)
        
        # Render trails first (so they're behind ships)
        for ship in render_state.ships.values():
            self.renderer.render_trail(ship)

        # Render temporary super blades with the trails.
        for blade in render_state.super_blades:
            self.renderer.render_super_blade(blade)
        
        # Render stars
        for star in render_state.stars:
            self.renderer.render_star(star)
        if render_state.super_star:
            self.renderer.render_star(render_state.super_star)
        
        # Render mines
        for mine in render_state.mines:
            self.renderer.render_mine(mine)
        
        # Render ships
        for ship in render_state.ships.values():
            self.renderer.render_spaceship(ship)

        # Render safe zone
        # self.renderer.render_safe_zone_debug()  # Uncomment to see safe zone

        # Persistent game overlay for physical throttle position and walls.
        self.renderer.render_throttle_overlay(render_state, self.controller)
        
        # Render HUD
        self.renderer.render_hud(render_state)
        
        # Render haptic visualization
        if self.force_visualizer and Config.SHOW_HAPTIC_PANEL:
            self.force_visualizer.render(self.force_calculator, self.controller, render_state)

        if self.volume_panel_visible:
            self._render_volume_panel()

        if self.help_panel_visible:
            self._render_shortcuts_panel()
        
        # Show game over message
        if render_state.game_over:
            if self._is_round_over_pending_next_round(render_state):
                self._render_round_over_message(render_state)
            else:
                self._render_game_over_message(render_state)
            
        pygame.display.flip()

    def _render_volume_panel(self):
        """Render the live audio mixer panel."""
        if not self.audio_manager:
            return

        rects = self._volume_panel_rects()
        panel = rects["panel"]
        font = pygame.font.Font(None, 28)
        small_font = pygame.font.Font(None, 22)

        overlay = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
        overlay.fill((10, 14, 18, 225))
        self.renderer.screen.blit(overlay, panel.topleft)
        pygame.draw.rect(self.renderer.screen, (80, 190, 220), panel, 2)

        title = font.render("Audio Mix", True, (235, 245, 255))
        self.renderer.screen.blit(title, (panel.x + 18, panel.y + 16))

        values = {
            "music": ("Music", Config.MUSIC_VOLUME),
            "sfx": ("SFX", Config.SFX_VOLUME),
            "engine": ("Engine", Config.ENGINE_VOLUME),
        }
        for name, (label, value) in values.items():
            slider = rects[name]
            y = slider.y - 6
            label_surface = small_font.render(label, True, (220, 225, 230))
            value_surface = small_font.render(f"{int(value * 100):3d}%", True, (220, 225, 230))
            self.renderer.screen.blit(label_surface, (panel.x + 18, y - 2))
            self.renderer.screen.blit(value_surface, (slider.right + 12, y - 2))

            pygame.draw.rect(self.renderer.screen, (55, 65, 72), slider)
            fill_rect = pygame.Rect(slider.x, slider.y, int(slider.width * value), slider.height)
            pygame.draw.rect(self.renderer.screen, (0, 200, 255), fill_rect)
            knob_x = slider.x + int(slider.width * value)
            pygame.draw.circle(self.renderer.screen, (245, 250, 255), (knob_x, slider.centery), 8)

        track_text = f"Track: {self.audio_manager.current_music_name()}"
        track_surface = small_font.render(track_text, True, (190, 220, 230))
        self.renderer.screen.blit(track_surface, (panel.x + 18, panel.bottom - 42))

    def _render_shortcuts_panel(self):
        """Render an in-game keyboard shortcut reference."""
        panel_width = 520
        panel_height = 430 if Config.SIMULATION_MODE else 360
        panel = pygame.Rect(
            (Config.WINDOW_WIDTH - panel_width) // 2,
            (Config.WINDOW_HEIGHT - panel_height) // 2,
            panel_width,
            panel_height
        )
        font = pygame.font.Font(None, 34)
        small_font = pygame.font.Font(None, 25)

        overlay = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
        overlay.fill((8, 12, 18, 235))
        self.renderer.screen.blit(overlay, panel.topleft)
        pygame.draw.rect(self.renderer.screen, (80, 190, 220), panel, 2)

        title = font.render("Keyboard Shortcuts", True, (235, 245, 255))
        self.renderer.screen.blit(title, (panel.x + 22, panel.y + 18))

        shortcuts = [
            ("H", "Show or hide this panel"),
            ("Backspace", "Return to main menu"),
            ("ESC", "Quit game"),
            ("R", "Restart current game"),
            ("F", "Toggle fullscreen"),
            ("V", "Toggle haptic visualization"),
            ("B", "Toggle hitboxes"),
            ("Shift+S", "Toggle audio mixer"),
            ("M", "Toggle music"),
            ("N", "Toggle sound effects"),
            ("T", "Switch music track"),
        ]
        if not Config.SIMULATION_MODE:
            shortcuts.append(("Z", "Zero hardware inputs"))
        else:
            shortcuts.extend([
                ("W/S", "Player 1 throttle"),
                ("A/D", "Player 1 steering"),
                ("Arrows", "Player 2 controls"),
            ])

        y = panel.y + 68
        key_width = 120
        for key, description in shortcuts:
            key_surface = small_font.render(key, True, (255, 230, 120))
            desc_surface = small_font.render(description, True, (220, 226, 232))
            self.renderer.screen.blit(key_surface, (panel.x + 28, y))
            self.renderer.screen.blit(desc_surface, (panel.x + 28 + key_width, y))
            y += 25

    def _send_haptic_forces(self):
        """Calculate and send haptic forces from the control thread."""
        if not self.force_calculator or not hasattr(self.controller, 'send_forces'):
            return

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

        p1_erm_pwm, p2_erm_pwm = self._erm_pwms_for_game_state()
        self.controller.send_forces(
            p1_steer,
            p1_throttle,
            p2_steer,
            p2_throttle,
            self._player_led_mask(),
            erm_enable=p1_erm_pwm > 0 or p2_erm_pwm > 0,
            p1_erm_pwm=p1_erm_pwm,
            p2_erm_pwm=p2_erm_pwm
        )

    def _erm_pwms_for_game_state(self):
        """Return independent P1/P2 ERM amplitudes for the current game state."""
        p1_pwm = self._trail_death_erm_pwm(1)
        p2_pwm = self._trail_death_erm_pwm(2)

        if (
            not self.game_state.running
            or self.game_state.paused
            or self.game_state.game_over
        ):
            return p1_pwm, p2_pwm

        normal_forward_wall = (
            (Config.THROTTLE_MOTION_RANGE_DEG / 2.0)
            / (360.0 * Config.THROTTLE_CONTROL_ROTATION_RANGE)
        )
        boosted_forward_wall = (
            ((Config.THROTTLE_MOTION_RANGE_DEG / 2.0)
             + Config.BOOST_THROTTLE_FORWARD_EXTENSION_DEG)
            / (360.0 * Config.THROTTLE_CONTROL_ROTATION_RANGE)
        )
        boost_wall_width = boosted_forward_wall - normal_forward_wall
        if boost_wall_width <= 0.0:
            return p1_pwm, p2_pwm

        for player_id, ship in self.game_state.ships.items():
            if not ship.alive or not ship.boost_active:
                continue

            boost_pwm = self._boost_erm_pwm_for_player(
                player_id,
                normal_forward_wall,
                boost_wall_width
            )
            if player_id == 1:
                p1_pwm = max(p1_pwm, boost_pwm)
            elif player_id == 2:
                p2_pwm = max(p2_pwm, boost_pwm)

        return p1_pwm, p2_pwm

    def _trail_death_erm_pwm(self, player_id):
        """Return the sinusoidal trail-death ERM PWM for one player."""
        remaining = self.trail_death_erm_timers.get(player_id, 0.0)
        if remaining <= 0.0:
            return 0

        duration = max(Config.TRAIL_DEATH_ERM_DURATION, 0.001)
        progress = 1.0 - max(0.0, min(1.0, remaining / duration))
        sweep = 0.5 - 0.5 * math.cos(6.0 * math.pi * progress)
        return round(
            Config.TRAIL_DEATH_ERM_MIN_PWM
            + (Config.TRAIL_DEATH_ERM_MAX_PWM - Config.TRAIL_DEATH_ERM_MIN_PWM) * sweep
        )

    def _boost_erm_pwm_for_player(self, player_id, normal_forward_wall, boost_wall_width):
        """Return boost-wall ERM amplitude for one player's throttle position."""
        throttle_position = self.controller.get_throttle(player_id)
        if throttle_position <= normal_forward_wall:
            return 0

        progress = (throttle_position - normal_forward_wall) / boost_wall_width
        progress = max(0.0, min(1.0, progress))
        return round(
            Config.BOOST_ERM_MIN_PWM
            + (Config.BOOST_ERM_MAX_PWM - Config.BOOST_ERM_MIN_PWM) * progress
        )

    def _player_led_mask(self):
        """Encode player join/boost/death state for the Teensy LED driver."""
        mask = 0

        p1 = self.game_state.ships.get(1)
        if p1 is not None:
            mask |= 1 << 0
            if p1.boost_active:
                mask |= 1 << 1
            if not p1.alive:
                mask |= 1 << 2

        p2 = self.game_state.ships.get(2)
        if p2 is not None:
            mask |= 1 << 3
            if p2.boost_active:
                mask |= 1 << 4
            if not p2.alive:
                mask |= 1 << 5

        return mask

    def _is_round_over_pending_next_round(self, game_state):
        """Check whether 2P game over is only a round break, not match over."""
        return (
            game_state.num_players == 2
            and game_state.game_over
            and game_state.get_match_winner() is None
        )

    def _render_round_over_message(self, game_state):
        """Render between-round countdown for two-player mode."""
        font = pygame.font.Font(None, 48)
        small_font = pygame.font.Font(None, 32)

        score_y = Config.WINDOW_HEIGHT // 2 - 55
        self._render_match_score(font, score_y, game_state)

        remaining = game_state.round_restart_timer
        if remaining is None:
            remaining = Config.RESPAWN_DELAY
        prompt_surface = small_font.render(
            f"Next round in {max(0.0, remaining):.1f}s",
            True,
            (220, 220, 220)
        )
        prompt_x = (Config.WINDOW_WIDTH - prompt_surface.get_width()) // 2
        prompt_y = score_y + font.get_height() + 10
        self.renderer.screen.blit(prompt_surface, (prompt_x, prompt_y))

    def _render_game_over_message(self, game_state):
        """Render game-over overlay."""
        title_font = pygame.font.Font(None, 96)
        font = pygame.font.Font(None, 42)
        small_font = pygame.font.Font(None, 32)

        title_surface = title_font.render("GAME OVER", True, (255, 60, 60))
        title_x = (Config.WINDOW_WIDTH - title_surface.get_width()) // 2
        title_y = Config.WINDOW_HEIGHT // 2 - 110
        self.renderer.screen.blit(title_surface, (title_x, title_y))

        next_y = title_y + title_surface.get_height() + 8
        if game_state.num_players == 2:
            winner = game_state.get_match_winner() or game_state.winner
            if winner:
                winner_color = Config.SHIP_COLOR_P1 if winner == 1 else Config.SHIP_COLOR_P2
                winner_surface = font.render(f"Player {winner} wins", True, winner_color)
                winner_x = (Config.WINDOW_WIDTH - winner_surface.get_width()) // 2
                self.renderer.screen.blit(winner_surface, (winner_x, next_y))
                next_y += winner_surface.get_height() + 8

        if game_state.num_players == 1 and game_state.game_over_return_timer is not None:
            prompt_text = (
                f"New game in {max(0.0, game_state.game_over_return_timer):.1f}s"
                " | SPACEBAR for menu"
            )
        else:
            prompt_text = "Press SPACEBAR to return to menu"
        prompt_surface = small_font.render(prompt_text, True, (220, 220, 220))
        prompt_x = (Config.WINDOW_WIDTH - prompt_surface.get_width()) // 2
        self.renderer.screen.blit(prompt_surface, (prompt_x, next_y))

    def _render_match_score(self, font, y, game_state):
        """Render 2P round score with player-colored values."""
        parts = [
            ("Score: ", (235, 235, 235)),
            (str(game_state.kills[1]), Config.SHIP_COLOR_P1),
            (" - ", (235, 235, 235)),
            (str(game_state.kills[2]), Config.SHIP_COLOR_P2),
        ]
        surfaces = [font.render(text, True, color) for text, color in parts]
        total_width = sum(surface.get_width() for surface in surfaces)
        x = (Config.WINDOW_WIDTH - total_width) // 2

        for surface in surfaces:
            self.renderer.screen.blit(surface, (x, y))
            x += surface.get_width()
