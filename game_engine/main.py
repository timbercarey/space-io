"""
Space IO - Main Entry Point
"""
import sys
import pygame
from config import Config
from core import GameState, GameLoop
from input import KeyboardController
from graphics import Renderer
from haptics import ForceCalculator, ForceVisualizer

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
    
    # Initialize components
    game_state = GameState(num_players=num_players)
    controller = KeyboardController()
    renderer = Renderer(screen)
    
    # Initialize haptics (simulation mode)
    force_calculator = ForceCalculator()
    force_visualizer = ForceVisualizer(screen)
    
    # Create and run game loop
    game_loop = GameLoop(game_state, controller, renderer, 
                         force_calculator, force_visualizer)
    
    print("=" * 50)
    print("SPACE IO - Controls")
    print("=" * 50)
    print("Player 1: W/A/S/D (throttle/steer)")
    if num_players == 2:
        print("Player 2: Arrow Keys")
    print("\nESC: Quit")
    print("SPACE: Pause")
    print("R: Restart")
    print("\nHaptic visualization enabled (bottom left)")
    print("=" * 50)
    
    game_loop.run()
    
    # Cleanup
    pygame.quit()

if __name__ == "__main__":
    main()