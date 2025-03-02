#!/usr/bin/env python3
"""Game of Life main application."""

import argparse
import signal
import sys
import time
from threading import Event
from typing import Any, List

from gol.controller import (
    ControllerConfig,
    cleanup_game,
    initialize_game,
    process_generation,
    setup_cell_actors,
)
from gol.grid import Grid, GridConfig, create_grid
from gol.renderer import (
    RendererConfig,
    RendererState,
    TerminalProtocol,
    cleanup_terminal,
    handle_user_input,
    initialize_terminal,
    safe_render_grid,
)


def parse_arguments() -> ControllerConfig:
    """Parse command line arguments.

    Returns:
        ControllerConfig with parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Conway's Game of Life with actor-based concurrency\n\n"
        "Controls:\n"
        "  - Press 'q' or Ctrl-C to quit the game\n"
        "  - Press 'r' to restart with a new grid\n"
        "  - Press Escape to exit\n"
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
        "--toroidal",
        action="store_true",
        help="Enable toroidal grid (edges wrap around)",
    )

    args = parser.parse_args()

    # Validate non-terminal dependent arguments
    if args.interval <= 0:
        parser.error("Interval must be positive")

    if not 0.0 <= args.density <= 1.0:
        parser.error("Density must be between 0.0 and 1.0")

    # Create configuration with placeholder dimensions
    return ControllerConfig(
        grid=GridConfig(
            width=args.width,
            height=args.height,
            density=args.density,
            toroidal=args.toroidal,
        ),
        renderer=RendererConfig(
            update_interval=args.interval,
        ),
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
    # Calculate default grid size based on terminal dimensions
    # Each cell takes 2 characters width due to spacing
    width = config.grid.width or (terminal.width - 4) // 2  # Leave some margin
    height = config.grid.height or terminal.height - 4  # Leave some margin

    # Validate dimensions
    if width <= 0:
        raise ValueError("Grid width must be positive")
    if height <= 0:
        raise ValueError("Grid height must be positive")

    # Create new config with adjusted dimensions
    return ControllerConfig(
        grid=GridConfig(
            width=width,
            height=height,
            density=config.grid.density,
            toroidal=config.grid.toroidal,
        ),
        renderer=config.renderer,
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
    actors: List,
    config: ControllerConfig,
    renderer_state: RendererState,
) -> None:
    """Run the main game loop.

    Args:
        terminal: Terminal instance for rendering
        actors: List of cell actors
        config: Controller configuration
        renderer_state: State for differential rendering
    """
    # Create synchronization event
    completion_event = Event()

    # Set up signal handlers
    setup_signal_handlers(terminal)

    try:
        # Calculate timing constraints
        min_frame_time = 1.0 / config.renderer.refresh_per_second
        last_render_time = 0.0

        # Main game loop
        with terminal.cbreak():
            while True:
                # Process one generation
                process_generation(actors, completion_event)

                # Check if it's time to render
                current_time = time.time()
                time_since_last_render = current_time - last_render_time

                if time_since_last_render >= min_frame_time:
                    # Extract grid state from actors
                    # Create empty grid with correct dimensions [rows][columns]
                    grid = Grid(
                        [
                            [False for _ in range(config.grid.width)]  # columns
                            for _ in range(config.grid.height)  # rows
                        ]
                    )

                    # Update grid with actor states
                    for actor in actors:
                        x, y = actor.position
                        grid[y][x] = actor.state  # Access as [row][column]

                    # Render grid with differential updates
                    safe_render_grid(terminal, grid, config.renderer, renderer_state)
                    last_render_time = current_time

                # Check for user input
                key = terminal.inkey(timeout=0)
                if key:
                    command = handle_user_input(terminal, key, config.renderer)
                    if command == "quit":
                        break
                    elif command == "restart":
                        # Create new grid and actors
                        grid = create_grid(config.grid)
                        actors.clear()  # Clear old actors
                        actors.extend(setup_cell_actors(grid, config.grid))
                        renderer_state.previous_grid = None  # Force full redraw

                # Sleep for the update interval
                time.sleep(config.renderer.update_interval / 1000)

    finally:
        # Clean up resources
        cleanup_game(terminal, actors)


def main() -> None:
    """Main entry point for the application."""
    terminal = None
    try:
        # Parse command line arguments (without terminal dependency)
        config = parse_arguments()

        # Initialize terminal only when needed
        terminal, renderer_state = initialize_terminal(config.renderer)

        # Adjust grid dimensions based on terminal size
        config = adjust_grid_dimensions(config, terminal)

        # Initialize game components
        terminal, actors = initialize_game(config)

        # Run game loop
        run_game_loop(terminal, actors, config, renderer_state)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if terminal:
            cleanup_terminal(terminal)
        sys.exit(1)


if __name__ == "__main__":
    main()
