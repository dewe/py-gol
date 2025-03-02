#!/usr/bin/env python3
"""Game of Life main application."""

import argparse
import signal
import sys
import time
from threading import Event
from typing import Any, List

from blessed import Terminal

from gol.controller import (
    ControllerConfig,
    cleanup_game,
    initialize_game,
    process_generation,
)
from gol.grid import Grid, GridConfig
from gol.renderer import RendererConfig, cleanup_terminal, safe_render_grid


def parse_arguments() -> ControllerConfig:
    """Parse command line arguments.

    Returns:
        ControllerConfig with parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Conway's Game of Life with actor-based concurrency"
    )

    parser.add_argument("grid_size", type=int, help="Size of the grid (N for N×N)")

    parser.add_argument(
        "--interval",
        type=int,
        default=100,
        help="Update interval in milliseconds (default: 100)",
    )

    parser.add_argument(
        "--density",
        type=float,
        default=0.3,
        help="Initial density of live cells (0.0-1.0, default: 0.3)",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.grid_size <= 0:
        parser.error("Grid size must be positive")

    if args.interval <= 0:
        parser.error("Interval must be positive")

    if not 0.0 <= args.density <= 1.0:
        parser.error("Density must be between 0.0 and 1.0")

    # Create configuration
    return ControllerConfig(
        grid=GridConfig(size=args.grid_size, density=args.density),
        renderer=RendererConfig(update_interval=args.interval),
    )


def setup_signal_handlers(terminal: Terminal) -> None:
    """Set up signal handlers for graceful shutdown.

    Args:
        terminal: Terminal instance to clean up on exit
    """

    def signal_handler(sig: int, frame: Any) -> None:
        """Handle signals by cleaning up terminal and exiting."""
        cleanup_terminal(terminal)
        sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def run_game_loop(terminal: Terminal, actors: List, config: ControllerConfig) -> None:
    """Run the main game loop.

    Args:
        terminal: Terminal instance for rendering
        actors: List of cell actors
        config: Controller configuration
    """
    # Create synchronization event
    completion_event = Event()

    # Set up signal handlers
    setup_signal_handlers(terminal)

    try:
        # Main game loop
        with terminal.cbreak():
            while True:
                # Process one generation
                process_generation(actors, completion_event)

                # Extract grid state from actors
                grid_size = config.grid.size
                grid = Grid(
                    [[False for _ in range(grid_size)] for _ in range(grid_size)]
                )

                for actor in actors:
                    x, y = actor.position
                    grid[x][y] = actor.state

                # Render grid
                safe_render_grid(terminal, grid, config.renderer)

                # Check for user input (non-blocking)
                key = terminal.inkey(timeout=0.01)  # Short timeout for responsiveness
                if key:
                    if key.lower() == "q" or key == "\x03":  # q or Ctrl+C
                        break

                # Sleep for the update interval
                time.sleep(config.renderer.update_interval / 1000)

    finally:
        # Clean up resources
        cleanup_game(terminal, actors)


def main() -> None:
    """Main entry point for the application."""
    try:
        # Parse command line arguments
        config = parse_arguments()

        # Initialize game components
        terminal, actors = initialize_game(config)

        # Run game loop
        run_game_loop(terminal, actors, config)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
