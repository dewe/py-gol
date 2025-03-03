#!/usr/bin/env python3
"""Game of Life main application."""

import argparse
import signal
import sys
import time
from threading import Event
from typing import Any, List, Tuple

from gol.controller import (
    ControllerConfig,
    cleanup_game,
    initialize_game,
    process_generation,
    setup_cell_actors,
)
from gol.grid import (
    Grid,
    GridConfig,
    Position,
    count_live_neighbors,
    create_grid,
    get_neighbors,
)
from gol.renderer import (
    RendererConfig,
    RendererState,
    TerminalProtocol,
    cleanup_terminal,
    handle_resize_event,
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


def update_cell(
    grid: Grid, pos: Position, neighbors: List[Position], config: GridConfig
) -> Tuple[bool, int]:
    """Determines new cell state based on neighbors.

    Args:
        grid: Current grid state
        pos: Position to update
        neighbors: List of neighbor positions
        config: Grid configuration

    Returns:
        Tuple of (new_state, new_age) for the cell
    """
    x, y = pos
    is_alive, age = grid[y][x]
    live_count = count_live_neighbors(grid, neighbors)

    # Apply Conway's rules with aging
    if is_alive:
        # Cell survives
        if live_count in (2, 3):
            return True, age + 1
        # Cell dies
        return False, 0
    else:
        # Cell becomes alive
        if live_count == 3:
            return True, 1
        # Cell stays dead
        return False, 0


def update_grid(grid: Grid, config: GridConfig) -> Grid:
    """Updates entire grid based on Game of Life rules.

    Args:
        grid: Current grid state
        config: Grid configuration

    Returns:
        New grid state
    """
    width = len(grid[0])
    height = len(grid)
    new_grid = []

    for y in range(height):
        new_row = []
        for x in range(width):
            pos = Position((x, y))
            neighbors = get_neighbors(grid, pos, config.toroidal)
            new_state = update_cell(grid, pos, neighbors, config)
            new_row.append(new_state)
        new_grid.append(new_row)

    return Grid(new_grid)


def run_game_loop(
    terminal: TerminalProtocol,
    grid: Grid,
    config: ControllerConfig,
    state: RendererState,
) -> None:
    """Main game loop.

    Args:
        terminal: Terminal instance
        grid: Initial grid state
        config: Game configuration
        state: Renderer state
    """
    # Initialize timing variables
    last_update = time.time()
    last_frame = last_update

    # Event for synchronizing cell updates
    completion_event = Event()

    # Create and connect cell actors
    actors = setup_cell_actors(grid, config.grid)

    try:
        with terminal.cbreak():
            while True:
                # Handle input with proper timeout
                try:
                    key = terminal.inkey(timeout=0.001)
                    if key:
                        command = handle_user_input(terminal, key, config.renderer)
                        if command == "quit":
                            print("\nQuitting game...")
                            return  # Exit cleanly
                        elif command == "restart":
                            grid = create_grid(config.grid)
                            actors = setup_cell_actors(grid, config.grid)
                            state.previous_grid = None  # Force full redraw
                            continue
                except KeyboardInterrupt:
                    print("\nGame interrupted by user")
                    return  # Exit cleanly

                # Check for resize events
                if (
                    terminal.width != state.terminal_width
                    or terminal.height != state.terminal_height
                ):
                    handle_resize_event(terminal, state)
                    state.terminal_width = terminal.width
                    state.terminal_height = terminal.height

                # Update game state at fixed interval
                current_time = time.time()
                if (
                    current_time - last_update
                    >= config.renderer.update_interval / 1000.0
                ):
                    process_generation(actors, completion_event)
                    # Update grid state from actors
                    grid = Grid(
                        [
                            [
                                (actor.state, actor.age)
                                for actor in actors[y : y + config.grid.width]
                            ]
                            for y in range(0, len(actors), config.grid.width)
                        ]
                    )
                    last_update = current_time

                # Render at maximum frame rate
                if current_time - last_frame >= 1.0 / 60:  # Cap at 60 FPS
                    safe_render_grid(terminal, grid, config.renderer, state)
                    last_frame = current_time

    finally:
        cleanup_game(terminal, actors)


def main() -> None:
    """Main entry point for the application."""
    terminal = None
    try:
        print("Starting Game of Life...")
        # Parse command line arguments (without terminal dependency)
        config = parse_arguments()
        print("Arguments parsed successfully")

        # Initialize terminal only when needed
        print("Initializing terminal...")
        terminal, renderer_state = initialize_terminal(config.renderer)
        print("Terminal initialized")

        # Adjust grid dimensions based on terminal size
        config = adjust_grid_dimensions(config, terminal)
        print(f"Grid dimensions adjusted: {config.grid.width}x{config.grid.height}")

        # Initialize game components
        print("Initializing game components...")
        terminal, actors = initialize_game(config)
        print("Game components initialized")

        # Create initial grid
        grid = create_grid(config.grid)
        print("Initial grid created")

        # Run game loop
        print("Starting game loop...")
        run_game_loop(terminal, grid, config, renderer_state)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if terminal:
            cleanup_terminal(terminal)
        sys.exit(1)


if __name__ == "__main__":
    main()
