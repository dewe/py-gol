#!/usr/bin/env python3
"""Game of Life main application."""

import argparse
import signal
import sys
import time
from threading import Event
from typing import Any, Callable, Dict

from gol.controller import (
    ControllerConfig,
    initialize_game,
    process_generation,
    resize_game,
    setup_cell_actors,
)
from gol.grid import BoundaryCondition, Grid, GridConfig, Position, create_grid
from gol.patterns import BUILTIN_PATTERNS, FilePatternStorage, place_pattern
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
    # Initialize actors
    actors = setup_cell_actors(grid, config.grid)
    completion_event = Event()

    # Initialize pattern storage
    pattern_storage = FilePatternStorage()

    # Track timing
    last_frame = time.time()
    last_update = time.time()

    # Command handlers
    def handle_quit() -> tuple[Grid, ControllerConfig, bool]:
        print("Quitting game...")
        return grid, config, True

    def handle_restart() -> tuple[Grid, ControllerConfig, bool]:
        new_grid = create_grid(config.grid)
        _ = setup_cell_actors(new_grid, config.grid)  # Ensure actors are set up
        state.generation_count = 0  # Reset generation count
        return new_grid, config, False

    def handle_pattern_mode() -> tuple[Grid, ControllerConfig, bool]:
        # Toggle pattern mode
        state.pattern_mode = not state.pattern_mode
        if state.pattern_mode:
            # Show available patterns
            patterns = list(BUILTIN_PATTERNS.keys()) + pattern_storage.list_patterns()
            print("\nAvailable patterns:")
            for i, name in enumerate(patterns):
                print(f"{i+1}: {name}")
            print("\nEnter pattern number: ", end="", flush=True)
            # Get pattern selection
            while True:
                try:
                    choice = int(terminal.inkey()) - 1
                    if 0 <= choice < len(patterns):
                        new_config = ControllerConfig(
                            grid=config.grid,
                            renderer=config.renderer,
                            selected_pattern=patterns[choice],
                            pattern_rotation=0,
                        )
                        return grid, new_config, False
                except ValueError:
                    pass
        return grid, config, False

    def handle_rotate_pattern() -> tuple[Grid, ControllerConfig, bool]:
        if state.pattern_mode and config.selected_pattern:
            new_config = ControllerConfig(
                grid=config.grid,
                renderer=config.renderer,
                selected_pattern=config.selected_pattern,
                pattern_rotation=(config.pattern_rotation + 90) % 360,
            )
            return grid, new_config, False
        return grid, config, False

    def handle_place_pattern() -> tuple[Grid, ControllerConfig, bool]:
        if state.pattern_mode and config.selected_pattern:
            # Get pattern
            pattern = BUILTIN_PATTERNS.get(
                config.selected_pattern
            ) or pattern_storage.load_pattern(config.selected_pattern)
            if pattern:
                # Place pattern at cursor
                new_grid = place_pattern(
                    grid,
                    pattern,
                    Position((state.cursor_x, state.cursor_y)),
                    config.pattern_rotation,
                )
                # Recreate actors
                _ = setup_cell_actors(new_grid, config.grid)  # Ensure actors are set up
                return new_grid, config, False
        return grid, config, False

    def handle_cycle_boundary() -> tuple[Grid, ControllerConfig, bool]:
        # Cycle through boundary conditions
        current = config.grid.boundary
        next_boundary = {
            BoundaryCondition.FINITE: BoundaryCondition.TOROIDAL,
            BoundaryCondition.TOROIDAL: BoundaryCondition.INFINITE,
            BoundaryCondition.INFINITE: BoundaryCondition.FINITE,
        }[current]
        new_config = ControllerConfig(
            grid=GridConfig(
                width=config.grid.width,
                height=config.grid.height,
                density=config.grid.density,
                boundary=next_boundary,
            ),
            renderer=config.renderer,
            selected_pattern=config.selected_pattern,
            pattern_rotation=config.pattern_rotation,
        )
        # Recreate actors with new boundary
        _ = setup_cell_actors(grid, new_config.grid)  # Ensure actors are set up
        return grid, new_config, False

    def handle_resize_larger() -> tuple[Grid, ControllerConfig, bool]:
        # Increase grid size by 10%
        new_width = int(config.grid.width * 1.1)
        new_height = int(config.grid.height * 1.1)
        new_grid, new_actors = resize_game(
            grid, actors, new_width, new_height, config.grid
        )
        new_config = ControllerConfig(
            grid=GridConfig(
                width=new_width,
                height=new_height,
                density=config.grid.density,
                boundary=config.grid.boundary,
            ),
            renderer=config.renderer,
            selected_pattern=config.selected_pattern,
            pattern_rotation=config.pattern_rotation,
        )
        return new_grid, new_config, False

    def handle_resize_smaller() -> tuple[Grid, ControllerConfig, bool]:
        # Decrease grid size by 10%
        new_width = max(10, int(config.grid.width * 0.9))
        new_height = max(10, int(config.grid.height * 0.9))
        new_grid, new_actors = resize_game(
            grid, actors, new_width, new_height, config.grid
        )
        new_config = ControllerConfig(
            grid=GridConfig(
                width=new_width,
                height=new_height,
                density=config.grid.density,
                boundary=config.grid.boundary,
            ),
            renderer=config.renderer,
            selected_pattern=config.selected_pattern,
            pattern_rotation=config.pattern_rotation,
        )
        return new_grid, new_config, False

    # Command mapping
    command_handlers: Dict[str, Callable[[], tuple[Grid, ControllerConfig, bool]]] = {
        "quit": handle_quit,
        "restart": handle_restart,
        "pattern_mode": handle_pattern_mode,
        "rotate_pattern": handle_rotate_pattern,
        "place_pattern": handle_place_pattern,
        "cycle_boundary": handle_cycle_boundary,
        "resize_larger": handle_resize_larger,
        "resize_smaller": handle_resize_smaller,
    }

    try:
        with terminal.cbreak():
            while True:
                current_time = time.time()

                # Check for user input
                key = terminal.inkey(timeout=0.001)
                if key:
                    command = handle_user_input(terminal, key, config.renderer)
                    if command in command_handlers:
                        grid, config, should_quit = command_handlers[command]()
                        if should_quit:
                            break

                # Process next generation at configured interval
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
                    state.generation_count += 1  # Increment generation count
                    last_update = current_time

                # Render grid at frame rate
                if (
                    current_time - last_frame
                    >= 1.0 / config.renderer.refresh_per_second
                ):
                    safe_render_grid(terminal, grid, config.renderer, state)
                    last_frame = current_time

    except Exception as e:
        print(f"Error in game loop: {e}", file=sys.stderr)
        raise


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

        # Create initial grid
        grid = create_grid(config.grid)

        # Run game loop
        run_game_loop(terminal, grid, config, renderer_state)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if terminal:
            cleanup_terminal(terminal)
        sys.exit(1)
    finally:
        if terminal:
            cleanup_terminal(terminal)


if __name__ == "__main__":
    main()
