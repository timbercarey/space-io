"""
Space IO - Main Entry Point
"""
import pygame
from config import Config
from core import GameState, GameLoop
from entities import Spaceship
from input import KeyboardController, HapticController
from graphics import Renderer
from audio import AudioManager
from haptics import ForceCalculator, ForceVisualizer
from utils import Vector2


def toggle_fullscreen():
    """Toggle fullscreen and keep Config display dimensions in sync."""
    Config.FULLSCREEN = not Config.FULLSCREEN
    if Config.FULLSCREEN:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode(
            (Config.WINDOWED_WIDTH, Config.WINDOWED_HEIGHT)
        )
    Config.set_display_size(screen.get_size())
    return screen


def run_main_menu(
    screen,
    initial_ship_styles=None,
    initial_difficulty=None,
    audio_manager=None,
    controller=None
):
    """Run the pre-game menu and return selected settings, or None to quit."""
    clock = pygame.time.Clock()
    title_font = pygame.font.Font(None, 72)
    font = pygame.font.Font(None, 36)
    small_font = pygame.font.Font(None, 24)
    preview_renderer = Renderer(screen)
    selected_ship_styles = dict(initial_ship_styles or {1: "x_wing", 2: "tie_fighter"})
    selected_difficulty = initial_difficulty or Config.DEFAULT_DIFFICULTY
    menu_screen = "main"
    ship_style_options = [
        ("x_wing", "X-wing"),
        ("y_wing", "Y-wing"),
        ("tie_fighter", "TIE Fighter"),
        ("falcon", "Falcon"),
        ("death_star", "Death Star"),
        ("classic", "Classic"),
    ]

    button_height = 48
    difficulty_button_width = 170

    def layout_rects():
        center_x = Config.WINDOW_WIDTH // 2
        return center_x, {
            "difficulty": {
                1: pygame.Rect(center_x - 270, 285, difficulty_button_width, button_height),
                2: pygame.Rect(center_x - 85, 285, difficulty_button_width, button_height),
                3: pygame.Rect(center_x + 100, 285, difficulty_button_width, button_height),
            },
            "start": pygame.Rect(center_x - 140, 390, 280, button_height),
            "options": pygame.Rect(center_x - 140, 455, 280, button_height),
            "p1_prev": pygame.Rect(center_x - 300, 275, 64, button_height),
            "p1_next": pygame.Rect(center_x + 236, 275, 64, button_height),
            "p2_prev": pygame.Rect(center_x - 300, 420, 64, button_height),
            "p2_next": pygame.Rect(center_x + 236, 420, 64, button_height),
            "back": pygame.Rect(center_x - 140, 565, 280, button_height),
        }

    if audio_manager:
        audio_manager.play_music()

    def draw_button(rect, text, active=False):
        fill = (45, 70, 85) if active else (35, 35, 35)
        border = (0, 200, 255) if active else (120, 120, 120)
        pygame.draw.rect(screen, fill, rect)
        pygame.draw.rect(screen, border, rect, 2)
        text_surface = font.render(text, True, (235, 235, 235))
        text_pos = (
            rect.centerx - text_surface.get_width() // 2,
            rect.centery - text_surface.get_height() // 2
        )
        screen.blit(text_surface, text_pos)

    def draw_centered_text(text, y, color=(180, 180, 180), use_font=None):
        render_font = use_font or small_font
        surface = render_font.render(text, True, color)
        screen.blit(surface, ((Config.WINDOW_WIDTH - surface.get_width()) // 2, y))

    def sync_difficulty_from_hardware():
        if not controller or not hasattr(controller, 'get_control_switch_snapshot'):
            return

        try:
            controls = controller.get_control_switch_snapshot(refresh=True)
        except TypeError:
            controls = controller.get_control_switch_snapshot()

        if not controls.get('received', False):
            return

        difficulty = controls.get('difficulty')
        if difficulty is not None:
            set_difficulty(difficulty, play_sound=False)

    def style_label(style):
        for value, label in ship_style_options:
            if value == style:
                return label
        return "Classic"

    def cycle_ship_style(player_id, direction):
        current_style = selected_ship_styles.get(player_id, "classic")
        values = [value for value, _label in ship_style_options]
        current_index = values.index(current_style) if current_style in values else 0
        selected_ship_styles[player_id] = values[(current_index + direction) % len(values)]
        if audio_manager:
            audio_manager.play("menu_select")

    def set_difficulty(difficulty_level, play_sound=True):
        nonlocal selected_difficulty
        difficulty_level = max(1, min(3, int(difficulty_level)))
        if selected_difficulty != difficulty_level and play_sound and audio_manager:
            audio_manager.play("menu_select")
        selected_difficulty = difficulty_level

    def draw_ship_selector(player_id, y, angle):
        center_x, rects = layout_rects()
        color = Config.SHIP_COLOR_P1 if player_id == 1 else Config.SHIP_COLOR_P2
        label = font.render(f"Player {player_id}", True, color)
        screen.blit(label, (center_x - label.get_width() // 2, y - 58))

        style = selected_ship_styles.get(player_id, "classic")
        style_surface = font.render(style_label(style), True, (235, 235, 235))
        screen.blit(style_surface, (center_x - style_surface.get_width() // 2, y + 35))

        prev_rect = rects["p1_prev"] if player_id == 1 else rects["p2_prev"]
        next_rect = rects["p1_next"] if player_id == 1 else rects["p2_next"]
        draw_button(prev_rect, "<")
        draw_button(next_rect, ">")

        ship = Spaceship(
            player_id=player_id,
            start_position=Vector2(0, Config.WINDOW_HEIGHT / 2 - y),
            start_angle=angle,
            ship_style=style
        )
        preview_renderer.render_spaceship(ship)

    while True:
        sync_difficulty_from_hardware()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_f:
                    screen = toggle_fullscreen()
                    preview_renderer.screen = screen
                elif event.key == pygame.K_ESCAPE:
                    if menu_screen == "options":
                        menu_screen = "main"
                    else:
                        if audio_manager:
                            audio_manager.play("return_to_menu")
                        return None
                elif menu_screen == "main":
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if audio_manager:
                            audio_manager.play("menu_start")
                        return selected_ship_styles, selected_difficulty
                    elif event.key in (pygame.K_q, pygame.K_MINUS):
                        set_difficulty(selected_difficulty - 1)
                    elif event.key in (pygame.K_e, pygame.K_EQUALS):
                        set_difficulty(selected_difficulty + 1)
                elif menu_screen == "options":
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if audio_manager:
                            audio_manager.play("return_to_menu")
                        menu_screen = "main"
                    elif event.key == pygame.K_a:
                        cycle_ship_style(1, -1)
                    elif event.key == pygame.K_d:
                        cycle_ship_style(1, 1)
                    elif event.key == pygame.K_LEFT:
                        cycle_ship_style(2, -1)
                    elif event.key == pygame.K_RIGHT:
                        cycle_ship_style(2, 1)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = event.pos
                _center_x, rects = layout_rects()
                if menu_screen == "main":
                    if rects["start"].collidepoint(mouse_pos):
                        if audio_manager:
                            audio_manager.play("menu_start")
                        return selected_ship_styles, selected_difficulty
                    clicked_difficulty = False
                    for difficulty_level, rect in rects["difficulty"].items():
                        if rect.collidepoint(mouse_pos):
                            set_difficulty(difficulty_level)
                            clicked_difficulty = True
                            break
                    if clicked_difficulty:
                        continue
                    elif rects["options"].collidepoint(mouse_pos):
                        if audio_manager:
                            audio_manager.play("menu_select")
                        menu_screen = "options"
                elif menu_screen == "options":
                    if rects["p1_prev"].collidepoint(mouse_pos):
                        cycle_ship_style(1, -1)
                    elif rects["p1_next"].collidepoint(mouse_pos):
                        cycle_ship_style(1, 1)
                    elif rects["p2_prev"].collidepoint(mouse_pos):
                        cycle_ship_style(2, -1)
                    elif rects["p2_next"].collidepoint(mouse_pos):
                        cycle_ship_style(2, 1)
                    elif rects["back"].collidepoint(mouse_pos):
                        if audio_manager:
                            audio_manager.play("return_to_menu")
                        menu_screen = "main"

        screen.fill(Config.BACKGROUND_COLOR)
        center_x, rects = layout_rects()

        title = title_font.render("Space IO", True, (235, 245, 255))
        screen.blit(title, ((Config.WINDOW_WIDTH - title.get_width()) // 2, 110))

        if menu_screen == "main":
            draw_centered_text(
                "Difficulty follows the 3-way switch live",
                205
            )
            draw_centered_text(
                "Player 2 is controlled by the hardware 2-way switch",
                226
            )

            difficulty_label = small_font.render("Difficulty", True, (180, 180, 180))
            screen.blit(
                difficulty_label,
                ((Config.WINDOW_WIDTH - difficulty_label.get_width()) // 2, 257)
            )
            for difficulty_level, rect in rects["difficulty"].items():
                profile = Config.DIFFICULTY_PROFILES[difficulty_level]
                draw_button(
                    rect,
                    profile["name"].title(),
                    selected_difficulty == difficulty_level
                )

            draw_button(rects["start"], "Start Game")
            draw_button(rects["options"], "Options")

            how_to_y = 525
            draw_centered_text("How to Play", how_to_y, (235, 245, 255), font)
            if Config.SIMULATION_MODE:
                control_lines = [
                    "P1: W/S throttle, A/D steer",
                    "P2: arrow keys when enabled",
                    "Q/E or click to change difficulty, Enter to start",
                ]
            else:
                control_lines = [
                    "Steer wheel to turn; throttle forward to accelerate",
                    "Pull throttle back to brake; collect stars for boost",
                    "3-way switch selects difficulty, 2-way switch enables P2",
                ]
            for index, line in enumerate(control_lines):
                draw_centered_text(line, how_to_y + 38 + index * 23)
        else:
            heading = font.render("Options", True, (235, 235, 235))
            screen.blit(heading, ((Config.WINDOW_WIDTH - heading.get_width()) // 2, 170))
            draw_ship_selector(1, 300, 0)
            draw_ship_selector(2, 445, 180)
            draw_button(rects["back"], "Back")

        pygame.display.flip()
        clock.tick(Config.FPS)

def main():
    """Main entry point"""
    if Config.GENERATE_HAPTIC_DEBUG_PLOTS:
        from haptics.debug_plots import generate_haptic_debug_plots

        plot_paths = generate_haptic_debug_plots()
        print("Generated haptic debug plots:")
        for path in plot_paths:
            print(f"  {path}")

    # The game starts with player 1; player 2 is added/removed live by hardware.
    num_players = 1
    
    # Initialize pygame
    pygame.init()
    audio_manager = AudioManager()
    
    # Create window
    screen = pygame.display.set_mode((Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT))
    Config.set_display_size(screen.get_size())
    pygame.display.set_caption("Space IO")

    ship_styles = {1: "x_wing", 2: "tie_fighter"}
    difficulty_level = Config.DEFAULT_DIFFICULTY

    while True:
        # The menu reads hardware switches live, so the controller must exist
        # before a game starts.
        if Config.SIMULATION_MODE:
            print("Running in SIMULATION MODE (keyboard input)")
            controller = KeyboardController()
        else:
            print("Running in HARDWARE MODE (haptic input)")
            controller = HapticController()

        selected_settings = run_main_menu(
            screen,
            ship_styles,
            difficulty_level,
            audio_manager,
            controller
        )
        if selected_settings is None:
            controller.close()
            break
        screen = pygame.display.get_surface()

        selected_ship_styles, selected_difficulty = selected_settings
        ship_styles = selected_ship_styles
        difficulty_level = selected_difficulty
        
        # Initialize components
        game_state = GameState(
            num_players=num_players,
            ship_styles=selected_ship_styles
        )
        game_state.apply_difficulty(selected_difficulty)
        renderer = Renderer(screen)

        # Initialize haptics
        force_calculator = ForceCalculator()
        force_visualizer = ForceVisualizer(screen)
        
        # Create and run game loop
        game_loop = GameLoop(game_state, controller, renderer,
                            force_calculator, force_visualizer, audio_manager)
        
        print("=" * 50)
        print("SPACE IO - Controls")
        print("=" * 50)
        if Config.SIMULATION_MODE:
            print("Player 1: W/A/S/D (throttle/steer)")
            print("Player 2: Arrow Keys when enabled by hardware switch")
        else:
            print("Using haptic hardware for input")
        print("\nESC: Quit")
        print("Backspace: Return to main menu")
        print("F: Toggle fullscreen")
        print("R: Restart")
        print("H: Toggle debug overlay and keyboard shortcuts")
        print("B: Toggle hitbox display")
        print("Shift+S: Toggle audio mixer")
        print("M: Toggle music")
        print("N: Toggle sound effects")
        print("T: Switch music track")
        if not Config.SIMULATION_MODE:
            print("Z: Zero throttle")
        print("\nRound over: next round starts automatically")
        print("Single-player game over: new game starts after 4s, SPACEBAR returns to menu")
        print("Two-player match over: SPACEBAR returns to menu")
        print("Haptic visualization: " + ("ON" if Config.SHOW_HAPTIC_PANEL else "OFF"))
        print("Hitbox display: " + ("ON" if Config.SHOW_HITBOXES else "OFF"))
        profile = Config.DIFFICULTY_PROFILES[selected_difficulty]
        print(f"Difficulty: {selected_difficulty} ({profile['name']})")
        print("=" * 50)
        
        if game_loop.run() != "menu":
            break
    
    # Cleanup
    audio_manager.close()
    pygame.quit()

if __name__ == "__main__":
    main()
