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
)
from gol.grid import Grid, GridConfig
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
        "  - Press Escape to exit"
    )

    parser.add_argument("width", type=int, help="Width of the grid")
    parser.add_argument("height", type=int, help="Height of the grid")

    parser.add_argument(
        "--interval",
        type=int,
        default=100,
        help="Update interval in milliseconds (default: 100). "
        "The refresh rate is automatically set to 1000/interval updates per second.",
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

    # Validate arguments
    if args.width <= 0:
        parser.error("Grid width must be positive")

    if args.height <= 0:
        parser.error("Grid height must be positive")

    if args.interval <= 0:
        parser.error("Interval must be positive")

    if not 0.0 <= args.density <= 1.0:
        parser.error("Density must be between 0.0 and 1.0")

    # Create configuration
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

                # Check for user input (non-blocking)
                try:
                    key = terminal.inkey(
                        timeout=0.01
                    )  # Short timeout for responsiveness
                    if key:  # Only process if we got a key
                        if handle_user_input(terminal, key) == "quit":
                            break
                except Exception:
                    # If there's any error reading input, ignore it and continue
                    pass

                # Sleep for the update interval
                time.sleep(config.renderer.update_interval / 1000)

    finally:
        # Clean up resources
        cleanup_game(terminal, actors)


def main() -> None:
    """Main entry point for the application."""
    terminal = None
    try:
        # Parse command line arguments
        config = parse_arguments()

        # Initialize game components
        terminal, renderer_state = initialize_terminal(config.renderer)
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
