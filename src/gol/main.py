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
from gol.grid import BoundaryCondition, Grid, GridConfig, Position, create_grid
from gol.patterns import BUILTIN_PATTERNS, FilePatternStorage, place_pattern
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
        default=30,  # Default to minimum width
        help="Width of the grid (default: 30, auto-sized to terminal width if 0)",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=20,  # Default to minimum height
        help="Height of the grid (default: 20, auto-sized to terminal height if 0)",
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=200,
        help="Update interval in milliseconds (default: 200).",
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
    # Minimum grid dimensions
    MIN_WIDTH = 30
    MIN_HEIGHT = 20

    # If dimensions are already set and above minimums, use them
    if config.grid.width >= MIN_WIDTH and config.grid.height >= MIN_HEIGHT:
        return config

    try:
        # Calculate default grid size based on terminal dimensions
        # Each cell takes 2 characters width due to spacing
        # Leave more margin around the grid (6 chars on each side, 4 lines top/bottom)
        width = max(
            MIN_WIDTH,
            config.grid.width if config.grid.width > 0 else (terminal.width - 12) // 2,
        )
        height = max(
            MIN_HEIGHT,
            config.grid.height if config.grid.height > 0 else terminal.height - 8,
        )
    except (AttributeError, TypeError):
        # If terminal dimensions are not available, use minimum dimensions
        width = max(
            MIN_WIDTH, config.grid.width if config.grid.width > 0 else MIN_WIDTH
        )
        height = max(
            MIN_HEIGHT, config.grid.height if config.grid.height > 0 else MIN_HEIGHT
        )

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
    # Track timing
    last_frame = time.time()
    last_update = time.time()

    # Track if game is paused
    is_paused = False

    # Command handlers
    def handle_quit() -> tuple[Grid, ControllerConfig, bool]:
        return grid, config, True

    def handle_restart() -> tuple[Grid, ControllerConfig, bool]:
        new_grid = create_grid(config.grid)
        state.generation_count = 0  # Reset generation count
        return new_grid, config, False

    def handle_pattern_mode() -> tuple[Grid, ControllerConfig, bool]:
        """Handle entering/exiting pattern mode."""
        # Toggle pattern mode and pause state
        state.pattern_mode = not state.pattern_mode
        nonlocal is_paused

        if state.pattern_mode:
            # Entering pattern mode - pause and keep current pattern if set
            is_paused = True
            new_config = ControllerConfig(
                grid=config.grid,
                renderer=config.renderer,
                selected_pattern=config.renderer.selected_pattern
                or "glider",  # Use existing pattern or default to glider
                pattern_rotation=config.renderer.pattern_rotation,
            )
            # Initialize cursor position to center of grid
            state.cursor_x = config.grid.width // 2
            state.cursor_y = config.grid.height // 2
        else:
            # Exiting pattern mode via ESC - unpause and clear pattern
            is_paused = False
            new_config = ControllerConfig(
                grid=config.grid,
                renderer=config.renderer,
                selected_pattern=None,
                pattern_rotation=0,
            )

        return grid, new_config, False

    def handle_cursor_movement(direction: str) -> tuple[Grid, ControllerConfig, bool]:
        """Handle cursor movement in pattern mode.

        Args:
            direction: Direction to move cursor ('left', 'right', 'up', 'down')

        Returns:
            Tuple of (grid, config, should_quit)
        """
        if state.pattern_mode:
            if direction == "left":
                state.cursor_x = (state.cursor_x - 1) % config.grid.width
            elif direction == "right":
                state.cursor_x = (state.cursor_x + 1) % config.grid.width
            elif direction == "up":
                state.cursor_y = (state.cursor_y - 1) % config.grid.height
            elif direction == "down":
                state.cursor_y = (state.cursor_y + 1) % config.grid.height

        return grid, config, False

    def handle_place_pattern() -> tuple[Grid, ControllerConfig, bool]:
        """Handle pattern placement in pattern mode.

        Returns:
            Tuple of (grid, config, should_quit)
        """
        if state.pattern_mode and config.renderer.selected_pattern:
            pattern = BUILTIN_PATTERNS.get(
                config.renderer.selected_pattern
            ) or FilePatternStorage().load_pattern(config.renderer.selected_pattern)

            if pattern:
                # Use place_pattern with centering enabled
                new_grid = place_pattern(
                    grid,
                    pattern,
                    Position((state.cursor_x, state.cursor_y)),
                    config.renderer.pattern_rotation,
                    centered=True,
                )
                # Keep pattern mode active and clear selected pattern
                config.renderer.set_pattern(None)
                return new_grid, config, False

        return grid, config, False

    def handle_rotate_pattern() -> tuple[Grid, ControllerConfig, bool]:
        """Handle pattern rotation in pattern mode.

        Returns:
            Tuple of (grid, config, should_quit)
        """
        if state.pattern_mode:
            # Update renderer config's pattern rotation
            config.renderer.set_pattern(
                config.renderer.selected_pattern,
                (config.renderer.pattern_rotation + 90) % 360,
            )
        return grid, config, False

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
        "move_cursor_left": lambda: handle_cursor_movement("left"),
        "move_cursor_right": lambda: handle_cursor_movement("right"),
        "move_cursor_up": lambda: handle_cursor_movement("up"),
        "move_cursor_down": lambda: handle_cursor_movement("down"),
        "place_pattern": handle_place_pattern,
        "rotate_pattern": handle_rotate_pattern,
        "resize_larger": lambda: handle_resize(True),
        "resize_smaller": lambda: handle_resize(False),
        "exit_pattern": handle_pattern_mode,  # Reuse pattern mode handler to exit
    }

    # Main loop with terminal in raw mode
    should_quit = False
    with terminal.cbreak():
        while not should_quit:
            current_time = time.time()

            # Handle user input
            key = terminal.inkey(timeout=0.001)
            if key:
                command = handle_user_input(terminal, key, config.renderer, state)
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
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        # Clean up
        cleanup_terminal(terminal)


if __name__ == "__main__":
    main()
