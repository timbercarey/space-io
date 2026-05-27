"""
Space IO - Main Entry Point
"""
import sys
import pygame
from config import Config
from core import GameState, GameLoop
from input import KeyboardController, HapticController
from graphics import Renderer
from haptics import ForceCalculator, ForceVisualizer

def run_main_menu(screen, initial_num_players=1):
    """Run the pre-game menu and return selected player count, or None to quit."""
    clock = pygame.time.Clock()
    title_font = pygame.font.Font(None, 72)
    font = pygame.font.Font(None, 36)
    small_font = pygame.font.Font(None, 24)
    selected_players = initial_num_players
    menu_screen = "main"

    button_width = 220
    button_height = 48
    center_x = Config.WINDOW_WIDTH // 2

    one_player_rect = pygame.Rect(center_x - 230, 250, button_width, button_height)
    two_player_rect = pygame.Rect(center_x + 10, 250, button_width, button_height)
    start_rect = pygame.Rect(center_x - 140, 330, 280, button_height)
    options_rect = pygame.Rect(center_x - 140, 395, 280, button_height)
    back_rect = pygame.Rect(center_x - 140, 395, 280, button_height)

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

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if menu_screen == "options":
                        menu_screen = "main"
                    else:
                        return None
                elif menu_screen == "main":
                    if event.key == pygame.K_1:
                        selected_players = 1
                    elif event.key == pygame.K_2:
                        selected_players = 2
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        return selected_players
                elif menu_screen == "options" and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    menu_screen = "main"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = event.pos
                if menu_screen == "main":
                    if one_player_rect.collidepoint(mouse_pos):
                        selected_players = 1
                    elif two_player_rect.collidepoint(mouse_pos):
                        selected_players = 2
                    elif start_rect.collidepoint(mouse_pos):
                        return selected_players
                    elif options_rect.collidepoint(mouse_pos):
                        menu_screen = "options"
                elif menu_screen == "options" and back_rect.collidepoint(mouse_pos):
                    menu_screen = "main"

        screen.fill(Config.BACKGROUND_COLOR)

        title = title_font.render("Space IO", True, (235, 245, 255))
        screen.blit(title, ((Config.WINDOW_WIDTH - title.get_width()) // 2, 110))

        if menu_screen == "main":
            subtitle = small_font.render("Players", True, (180, 180, 180))
            screen.blit(subtitle, ((Config.WINDOW_WIDTH - subtitle.get_width()) // 2, 220))

            draw_button(one_player_rect, "1 Player", selected_players == 1)
            draw_button(two_player_rect, "2 Player", selected_players == 2)
            draw_button(start_rect, "Start Game")
            draw_button(options_rect, "Options")
        else:
            heading = font.render("Options", True, (235, 235, 235))
            screen.blit(heading, ((Config.WINDOW_WIDTH - heading.get_width()) // 2, 260))
            draw_button(back_rect, "Back")

        pygame.display.flip()
        clock.tick(Config.FPS)

def main():
    """Main entry point"""
    # Parse command line arguments
    num_players = 1  # Start with single player
    
    if len(sys.argv) > 1:
        try:
            num_players = int(sys.argv[1])
            if num_players not in [1, 2]:
                print("Number of players must be 1 or 2")
                sys.exit(1)
        except ValueError:
            print("Usage: python3 main.py [num_players]")
            sys.exit(1)
    
    # Initialize pygame
    pygame.init()
    
    # Create window
    screen = pygame.display.set_mode((Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT))
    pygame.display.set_caption("Space IO")

    while True:
        selected_players = run_main_menu(screen, num_players)
        if selected_players is None:
            break

        num_players = selected_players

        # Initialize components
        game_state = GameState(num_players=selected_players)
        renderer = Renderer(screen)

        # Choose controller based on simulation mode
        if Config.SIMULATION_MODE:
            print("Running in SIMULATION MODE (keyboard input)")
            controller = KeyboardController()
        else:
            print("Running in HARDWARE MODE (haptic input)")
            controller = HapticController()

        # Initialize haptics
        force_calculator = ForceCalculator()
        force_visualizer = ForceVisualizer(screen)

        # Create and run game loop
        game_loop = GameLoop(game_state, controller, renderer,
                             force_calculator, force_visualizer)

        print("=" * 50)
        print("SPACE IO - Controls")
        print("=" * 50)
        if Config.SIMULATION_MODE:
            print("Player 1: W/A/S/D (throttle/steer)")
            if selected_players == 2:
                print("Player 2: Arrow Keys")
        else:
            print("Using haptic hardware for input")
        print("\nESC: Quit")
        print("R: Restart")
        if selected_players == 2:
            print("N: Next round (when round ends)")
        print("H: Toggle haptic visualization")
        print("B: Toggle hitbox display")
        if not Config.SIMULATION_MODE:
            print("Z: Zero throttle")
        print("\nRound over: SPACEBAR for next round")
        print("Game over: SPACEBAR to return to menu")
        print("Haptic visualization: " + ("ON" if Config.SHOW_HAPTIC_PANEL else "OFF"))
        print("Hitbox display: " + ("ON" if Config.SHOW_HITBOXES else "OFF"))
        print("=" * 50)

        if game_loop.run() != "menu":
            break

    # Cleanup
    pygame.quit()

if __name__ == "__main__":
    main()
