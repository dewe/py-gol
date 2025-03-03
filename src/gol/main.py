#!/usr/bin/env python3
"""Game of Life main application."""

import argparse
import signal
import sys
import time
from typing import Any, Callable, Dict, Literal, Tuple

from gol.controller import (
    ControllerConfig,
    initialize_game,
    process_generation,
    resize_game,
)
from gol.grid import BoundaryCondition, Grid, GridConfig, create_grid
from gol.patterns import BUILTIN_PATTERNS, FilePatternStorage
from gol.renderer import (
    RendererConfig,
    RendererState,
    TerminalProtocol,
    cleanup_terminal,
    handle_user_input,
    safe_render_grid,
)

CommandType = Literal[
    "continue",
    "quit",
    "restart",
    "pattern",
    "move_cursor_left",
    "move_cursor_right",
    "move_cursor_up",
    "move_cursor_down",
    "place_pattern",
    "rotate_pattern",
    "cycle_boundary",
    "resize_larger",
    "resize_smaller",
    "exit_pattern",
]


def parse_arguments() -> ControllerConfig:
    """Parse command line arguments.

    Returns:
        ControllerConfig with parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Conway's Game of Life\n\n"
        "Controls:\n"
        "  - Press 'q' or Ctrl-C to quit the game\n"
        "  - Press 'r' to restart with a new grid\n"
        "  - Press 'p' to enter pattern mode\n"
        "  - Press 'b' to cycle boundary conditions\n"
        "  - Press '+'/'-' to resize grid\n"
        "  - Press '['/']' to rotate pattern\n"
        "  - Press Space to place pattern\n"
        "  - Press Escape to exit pattern mode\n"
        "  - Press ↑ to slow down the simulation\n"
        "  - Press ↓ to speed up the simulation"
    )

    # Use more efficient default values
    parser.add_argument(
        "--width",
        type=int,
        default=0,  # Will be calculated later based on terminal
        help="Width of the grid (auto-sized to terminal width if not specified)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=0,  # Will be calculated later based on terminal
        help="Height of the grid (auto-sized to terminal height if not specified)",
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=100,
        help="Update interval in milliseconds (default: 100).",
    )

    parser.add_argument(
        "--density",
        type=float,
        default=0.3,
        help="Initial density of live cells (0.0-1.0, default: 0.3)",
    )

    parser.add_argument(
        "--boundary",
        type=str,
        choices=["finite", "toroidal", "infinite"],
        default="finite",
        help="Boundary condition (default: finite)",
    )

    args = parser.parse_args()

    # Convert boundary condition string to enum
    boundary = BoundaryCondition[args.boundary.upper()]

    return ControllerConfig(
        grid=GridConfig(
            width=args.width,
            height=args.height,
            density=args.density,
            boundary=boundary,
        ),
        renderer=RendererConfig(update_interval=args.interval),
    )


def adjust_grid_dimensions(
    config: ControllerConfig, terminal: TerminalProtocol
) -> ControllerConfig:
    """Adjust grid dimensions based on terminal size if not specified.

    Args:
        config: Current configuration
        terminal: Terminal instance

    Returns:
        Updated configuration with proper dimensions
    """
    print(f"Terminal dimensions: {terminal.width}x{terminal.height}")

    # Minimum grid dimensions
    MIN_WIDTH = 30
    MIN_HEIGHT = 20

    # Calculate default grid size based on terminal dimensions
    # Each cell takes 2 characters width due to spacing
    width = config.grid.width or max(
        MIN_WIDTH, (terminal.width - 4) // 2
    )  # Leave some margin
    height = config.grid.height or max(
        MIN_HEIGHT, terminal.height - 4
    )  # Leave some margin

    print(f"Calculated grid dimensions: {width}x{height}")

    # Create new config with adjusted dimensions
    return ControllerConfig(
        grid=GridConfig(
            width=width,
            height=height,
            density=config.grid.density,
            boundary=config.grid.boundary,
        ),
        renderer=config.renderer,
        selected_pattern=config.selected_pattern,
        pattern_rotation=config.pattern_rotation,
    )


def setup_signal_handlers(terminal: TerminalProtocol) -> None:
    """Set up signal handlers for graceful shutdown.

    Args:
        terminal: Terminal instance to cleanup on signals
    """

    def signal_handler(sig: int, frame: Any) -> None:
        """Handle signals by cleaning up terminal and exiting."""
        cleanup_terminal(terminal)
        sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def run_game_loop(
    terminal: TerminalProtocol,
    grid: Grid,
    config: ControllerConfig,
    state: RendererState,
) -> None:
    """Main game loop.

    Args:
        terminal: Terminal instance
        grid: Current game grid
        config: Controller configuration
        state: Current renderer state
    """
    # Initialize pattern storage
    pattern_storage = FilePatternStorage()

    # Track timing
    last_frame = time.time()
    last_update = time.time()

    # Track if game is paused
    is_paused = False

    # Command handlers
    def handle_quit() -> tuple[Grid, ControllerConfig, bool]:
        print("Quitting game...")
        return grid, config, True

    def handle_restart() -> tuple[Grid, ControllerConfig, bool]:
        new_grid = create_grid(config.grid)
        state.generation_count = 0  # Reset generation count
        return new_grid, config, False

    def handle_pattern_mode() -> tuple[Grid, ControllerConfig, bool]:
        # Toggle pattern mode and pause state
        state.pattern_mode = not state.pattern_mode
        nonlocal is_paused
        is_paused = state.pattern_mode  # Pause when entering pattern mode

        # Create new config with current settings
        new_config = ControllerConfig(
            grid=config.grid,
            renderer=config.renderer,
            selected_pattern=config.selected_pattern,
            pattern_rotation=config.pattern_rotation,
        )

        if state.pattern_mode:
            # Initialize cursor position to center of grid
            state.cursor_x = config.grid.width // 2
            state.cursor_y = config.grid.height // 2

            # Get available patterns
            patterns = list(BUILTIN_PATTERNS.keys()) + pattern_storage.list_patterns()

            # Display pattern list in status area
            y = terminal.height - 2  # Use second-to-last line
            x = 2  # Leave some margin
            pattern_list = ", ".join(f"{i+1}:{name}" for i, name in enumerate(patterns))
            print(
                terminal.move_xy(x, y)
                + " " * (terminal.width - x)
                + terminal.move_xy(x, y)
                + "Patterns: "
                + pattern_list
            )

        return grid, new_config, False

    def handle_resize(larger: bool) -> tuple[Grid, ControllerConfig, bool]:
        # Calculate new dimensions
        factor = 1.2 if larger else 0.8
        new_width = max(10, int(config.grid.width * factor))
        new_height = max(10, int(config.grid.height * factor))

        # Resize grid and update config
        new_grid, new_config = resize_game(grid, new_width, new_height, config.grid)

        # Create new controller config
        new_controller_config = ControllerConfig(
            grid=new_config,
            renderer=config.renderer,
            selected_pattern=config.selected_pattern,
            pattern_rotation=config.pattern_rotation,
        )

        return new_grid, new_controller_config, False

    # Command map
    command_map: Dict[
        CommandType, Callable[[], Tuple[Grid, ControllerConfig, bool]]
    ] = {
        "quit": handle_quit,
        "restart": handle_restart,
        "pattern": handle_pattern_mode,
        "resize_larger": lambda: handle_resize(True),
        "resize_smaller": lambda: handle_resize(False),
    }

    # Main loop
    should_quit = False
    while not should_quit:
        current_time = time.time()

        # Handle user input
        key = terminal.inkey(timeout=0.001)
        if key:
            command = handle_user_input(terminal, key, config.renderer)
            if command:
                handler = command_map.get(command)
                if handler:
                    grid, config, should_quit = handler()

        # Update game state if not paused
        if (
            not is_paused
            and current_time - last_update >= config.renderer.update_interval / 1000
        ):
            grid = process_generation(grid, config.grid.boundary)
            state.generation_count += 1
            last_update = current_time

        # Render frame if enough time has passed
        if current_time - last_frame >= 1 / 60:  # Cap at 60 FPS
            safe_render_grid(terminal, grid, config.renderer, state)
            last_frame = current_time

        # Small sleep to prevent busy waiting
        time.sleep(0.001)


def main() -> None:
    """Main entry point."""
    try:
        # Parse command line arguments
        config = parse_arguments()

        # Initialize game
        terminal, grid = initialize_game(config)

        # Adjust grid dimensions based on terminal size
        config = adjust_grid_dimensions(config, terminal)

        # Set up signal handlers
        setup_signal_handlers(terminal)

        # Initialize renderer state
        state = RendererState()

        # Run game loop
        run_game_loop(terminal, grid, config, state)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    finally:
        # Clean up
        cleanup_terminal(terminal)


if __name__ == "__main__":
    main()
