#!/usr/bin/env python3
"""
Conway's Game of Life - Terminal Implementation

A functional implementation of Conway's Game of Life using Python and curses.
Features include:
- Pure functional core with immutable state transitions
- Side effects isolated to terminal I/O and file operations
- Pattern management with built-in and custom patterns
- Multiple boundary conditions (wrap, dead, reflect)
- Pattern preview and rotation
- Configurable grid size and speed
- Dynamic grid resizing (automatically fits terminal dimensions)

Architecture:
- Pure Functions: Grid operations, life rules, state transitions
- Side Effects: Terminal I/O, file operations, signal handling
- State Management: Immutable data structures, functional patterns

Controls:
  Space: Start/Stop simulation
  P: Enter pattern mode
    - Number keys (1-9): Select pattern
    - R: Rotate pattern
    - Space: Place pattern
    - P: Exit pattern mode
  C: Clear grid
  Arrow keys: Pan viewport
  Q, Esc: Quit game
  R: Restart with new grid
  B: Cycle boundary conditions
  +/-: Resize grid
  Shift+Up/Down: Adjust simulation speed
"""

import argparse
import dataclasses
import signal
import sys
import time
from typing import Any, Callable, Dict, Tuple

import numpy as np

from gol.controller import (
    ControllerConfig,
    handle_viewport_pan,
    handle_viewport_resize,
    process_next_generation,
    resize_game,
)
from gol.grid import BoundaryCondition, GridConfig, create_grid
from gol.metrics import create_metrics, update_game_metrics
from gol.patterns import BUILTIN_PATTERNS, FilePatternStorage, place_pattern
from gol.renderer import (
    RendererState,
    TerminalProtocol,
    apply_initialization,
    cleanup_terminal,
    handle_user_input,
    initialize_render_state,
    initialize_terminal,
    safe_render_grid,
)
from gol.types import CommandType, Grid


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments and provide sensible defaults.

    Uses efficient default values optimized for typical terminal sizes
    while ensuring minimum playable dimensions.

    Returns:
        Raw argument namespace for flexible dimension handling
    """
    parser = argparse.ArgumentParser(
        description="Conway's Game of Life - Terminal Implementation\n\n"
        "A functional implementation with pattern management and dynamic resizing.\n\n"
        "Normal Mode Controls:\n"
        "  Space       - Start/Stop simulation\n"
        "  P           - Enter pattern mode\n"
        "  C           - Clear grid\n"
        "  R           - Restart with new grid\n"
        "  B           - Cycle boundary conditions\n"
        "  +           - Resize grid larger\n"
        "  -           - Resize grid smaller\n"
        "  Arrow keys  - Pan viewport\n"
        "  Shift+Up    - Increase simulation speed\n"
        "  Shift+Down  - Decrease simulation speed\n"
        "  Q, Esc      - Quit game\n\n"
        "Pattern Mode Controls:\n"
        "  1-9         - Select pattern\n"
        "  R           - Rotate pattern\n"
        "  Space       - Place pattern\n"
        "  Arrow keys  - Move cursor\n"
        "  P, Esc      - Exit pattern mode\n"
        "  Q           - Quit game\n\n"
        "Speed Control:\n"
        "  - Maximum speed: 10 generations/second\n"
        "  - Minimum speed: 0.5 generations/second\n"
        "  - Speed changes adapt to current speed\n"
        "  - Default: 5 generations/second\n"
    )

    # Use more efficient default values
    parser.add_argument(
        "--width",
        type=int,
        default=0,  # Default to auto-size
        help=(
            "Width of the grid (auto-sized to terminal width if not specified "
            "or set to 0, minimum 10)"
        ),
    )
    parser.add_argument(
        "--height",
        type=int,
        default=0,  # Default to auto-size
        help=(
            "Height of the grid (auto-sized to terminal height if not specified "
            "or set to 0, minimum 20)"
        ),
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

    return parser.parse_args()


def adjust_grid_dimensions(
    config: ControllerConfig, terminal: TerminalProtocol
) -> ControllerConfig:
    """Adjust grid dimensions to fit terminal while maintaining playability.

    Ensures grid fits within terminal bounds with proper margins for UI elements
    while respecting minimum dimensions for gameplay.
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
        dimensions=(width, height),
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
    """Set up signal handlers for graceful terminal restoration on exit."""

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
    render_state: RendererState,
) -> None:
    """Main game loop implementing Conway's Game of Life rules.

    Manages game state updates, user input handling, and rendering with
    performance optimizations like frame rate limiting and efficient
    terminal updates.
    """
    last_frame = time.time()
    last_update = time.time()
    metrics = create_metrics()

    # Command handlers
    def handle_quit(
        grid: Grid, config: ControllerConfig, render_state: RendererState
    ) -> tuple[Grid, ControllerConfig, RendererState, bool]:
        return grid, config, render_state, True

    def handle_restart(
        _: Grid,
        config: ControllerConfig,
        render_state: RendererState,
    ) -> tuple[Grid, ControllerConfig, RendererState, bool]:
        new_grid = create_grid(config.grid)
        nonlocal metrics
        metrics = create_metrics()  # Create new metrics instead of modifying
        return new_grid, config, render_state, False

    def handle_pattern_mode(
        grid: Grid, config: ControllerConfig, render_state: RendererState
    ) -> tuple[Grid, ControllerConfig, RendererState, bool]:
        """Toggle pattern mode with state preservation."""
        new_render_state = render_state.with_pattern_mode(not render_state.pattern_mode)

        if new_render_state.pattern_mode:
            new_renderer = config.renderer.with_pattern(
                config.renderer.selected_pattern or "glider"
            )
            new_config = ControllerConfig(
                dimensions=config.dimensions,
                grid=config.grid,
                renderer=new_renderer,
            )
            new_render_state = new_render_state.with_cursor(
                config.grid.width // 2, config.grid.height // 2
            )
        else:
            new_renderer = config.renderer.with_pattern(None)
            new_config = ControllerConfig(
                dimensions=config.dimensions,
                grid=config.grid,
                renderer=new_renderer,
            )

        return grid, new_config, new_render_state, False

    def handle_clear_grid(
        grid: Grid, config: ControllerConfig, render_state: RendererState
    ) -> tuple[Grid, ControllerConfig, RendererState, bool]:
        """Clear the grid by creating a new empty grid."""
        new_grid = np.zeros_like(grid)
        return new_grid, config, render_state, False

    def handle_toggle_simulation(
        grid: Grid, config: ControllerConfig, render_state: RendererState
    ) -> tuple[Grid, ControllerConfig, RendererState, bool]:
        """Toggle simulation pause state."""
        new_render_state = render_state.with_paused(not render_state.paused)
        return grid, config, new_render_state, False

    def handle_speed_adjustment(
        grid: Grid,
        config: ControllerConfig,
        render_state: RendererState,
        increase: bool,
    ) -> tuple[Grid, ControllerConfig, RendererState, bool]:
        """Adjust simulation speed."""
        current_interval = config.renderer.update_interval
        delta = max(current_interval * 0.2, 50)
        new_interval = round(
            max(
                50,
                min(
                    2000,
                    current_interval - delta if increase else current_interval + delta,
                ),
            )
        )

        new_renderer = config.renderer.with_update_interval(new_interval)
        new_config = ControllerConfig(
            dimensions=config.dimensions,
            grid=config.grid,
            renderer=new_renderer,
        )
        return grid, new_config, render_state, False

    def handle_cursor_movement(
        grid: Grid,
        config: ControllerConfig,
        render_state: RendererState,
        direction: str,
    ) -> tuple[Grid, ControllerConfig, RendererState, bool]:
        """Handle wrapped cursor movement within grid bounds."""
        if not render_state.pattern_mode:
            return grid, config, render_state, False

        new_x, new_y = render_state.cursor_x, render_state.cursor_y
        if direction == "left":
            new_x = (render_state.cursor_x - 1) % config.grid.width
        elif direction == "right":
            new_x = (render_state.cursor_x + 1) % config.grid.width
        elif direction == "up":
            new_y = (render_state.cursor_y - 1) % config.grid.height
        elif direction == "down":
            new_y = (render_state.cursor_y + 1) % config.grid.height

        new_render_state = render_state.with_cursor(new_x, new_y)
        return grid, config, new_render_state, False

    def handle_place_pattern(
        grid: Grid, config: ControllerConfig, render_state: RendererState
    ) -> tuple[Grid, ControllerConfig, RendererState, bool]:
        """Handle pattern placement in pattern mode."""
        if not (render_state.pattern_mode and config.renderer.selected_pattern):
            return grid, config, render_state, False

        pattern = BUILTIN_PATTERNS.get(
            config.renderer.selected_pattern
        ) or FilePatternStorage().load_pattern(config.renderer.selected_pattern)

        if not pattern:
            return grid, config, render_state, False

        new_grid = place_pattern(
            grid,
            pattern,
            (render_state.cursor_x, render_state.cursor_y),
            config.renderer.pattern_rotation,
            centered=True,
        )
        new_renderer = config.renderer.with_pattern(None)
        new_config = ControllerConfig(
            dimensions=config.dimensions,
            grid=config.grid,
            renderer=new_renderer,
        )
        return new_grid, new_config, render_state, False

    def handle_rotate_pattern(
        grid: Grid, config: ControllerConfig, render_state: RendererState
    ) -> tuple[Grid, ControllerConfig, RendererState, bool]:
        """Handle pattern rotation in pattern mode."""
        return grid, config, render_state, False

    def handle_resize(
        grid: Grid,
        config: ControllerConfig,
        render_state: RendererState,
        terminal: TerminalProtocol,
        larger: bool,
    ) -> tuple[Grid, ControllerConfig, RendererState, bool]:
        """Resize grid while preserving content."""
        margin = 4
        max_width = (terminal.width - (2 * margin)) // 2
        max_height = terminal.height - 2

        factor = 1.2 if larger else 0.8
        requested_width = int(config.grid.width * factor)
        requested_height = int(config.grid.height * factor)

        new_width = max(10, min(max_width, requested_width))
        new_height = max(10, min(max_height, requested_height))

        if new_width == config.grid.width and new_height == config.grid.height:
            return grid, config, render_state, False

        # Clear screen and handle artifacts
        print(terminal.clear(), end="", flush=True)
        print(terminal.move_xy(0, 0), end="", flush=True)
        for y in range(terminal.height):
            print(terminal.move_xy(0, y) + " " * terminal.width, end="", flush=True)
        sys.stdout.flush()

        # Create new render state with cleared caches
        new_render_state = render_state.with_previous_grid(None).with_pattern_cells(
            None
        )

        # Resize grid and update configs
        new_grid, new_grid_config = resize_game(
            grid, new_width, new_height, config.grid
        )
        new_config = ControllerConfig(
            dimensions=(new_width, new_height),
            grid=new_grid_config,
            renderer=config.renderer,
        )
        return new_grid, new_config, new_render_state, False

    def handle_cycle_boundary(
        grid: Grid, config: ControllerConfig, render_state: RendererState
    ) -> tuple[Grid, ControllerConfig, RendererState, bool]:
        """Cycle through available boundary conditions."""
        current = config.grid.boundary
        new_boundary = {
            BoundaryCondition.FINITE: BoundaryCondition.TOROIDAL,
            BoundaryCondition.TOROIDAL: BoundaryCondition.INFINITE,
            BoundaryCondition.INFINITE: BoundaryCondition.FINITE,
        }[current]

        new_grid_config = config.grid.with_boundary(new_boundary)
        new_renderer_config = dataclasses.replace(
            config.renderer, boundary_condition=new_boundary
        )
        new_config = ControllerConfig(
            dimensions=config.dimensions,
            grid=new_grid_config,
            renderer=new_renderer_config,
        )
        return grid, new_config, render_state, False

    def handle_viewport_resize_command(
        grid: Grid, config: ControllerConfig, render_state: RendererState, expand: bool
    ) -> tuple[Grid, ControllerConfig, RendererState, bool]:
        """Handle viewport resize while preserving content."""
        new_render_state = handle_viewport_resize(render_state, expand)
        return grid, config, new_render_state, False

    def handle_viewport_pan_command(
        grid: Grid,
        config: ControllerConfig,
        render_state: RendererState,
        dx: int,
        dy: int,
    ) -> tuple[Grid, ControllerConfig, RendererState, bool]:
        """Handle viewport panning."""
        new_render_state = handle_viewport_pan(render_state, dx, dy)
        return grid, config, new_render_state, False

    # Command map type definition
    CommandHandler = Callable[
        [Grid, ControllerConfig, RendererState],
        Tuple[Grid, ControllerConfig, RendererState, bool],
    ]

    # Command map with proper handler signatures
    command_map: Dict[CommandType, CommandHandler] = {
        "quit": handle_quit,
        "restart": lambda g, c, r: handle_restart(g, c, r),  # Pass metrics from closure
        "pattern": handle_pattern_mode,
        "select_pattern": lambda g, c, r: (g, c, r, False),  # Simple pass-through
        "move_cursor_left": lambda g, c, r: handle_cursor_movement(g, c, r, "left"),
        "move_cursor_right": lambda g, c, r: handle_cursor_movement(g, c, r, "right"),
        "move_cursor_up": lambda g, c, r: handle_cursor_movement(g, c, r, "up"),
        "move_cursor_down": lambda g, c, r: handle_cursor_movement(g, c, r, "down"),
        "place_pattern": handle_place_pattern,
        "rotate_pattern": handle_rotate_pattern,
        "cycle_boundary": handle_cycle_boundary,
        "resize_larger": lambda g, c, r: handle_resize(
            g, c, r, terminal, True
        ),  # Pass terminal from closure
        "resize_smaller": lambda g, c, r: handle_resize(g, c, r, terminal, False),
        "exit_pattern": handle_pattern_mode,  # Reuse pattern mode handler
        "viewport_expand": lambda g, c, r: handle_viewport_resize_command(
            g, c, r, True
        ),
        "viewport_shrink": lambda g, c, r: handle_viewport_resize_command(
            g, c, r, False
        ),
        "viewport_pan_left": lambda g, c, r: handle_viewport_pan_command(
            g, c, r, -1, 0
        ),
        "viewport_pan_right": lambda g, c, r: handle_viewport_pan_command(
            g, c, r, 1, 0
        ),
        "viewport_pan_up": lambda g, c, r: handle_viewport_pan_command(g, c, r, 0, -1),
        "viewport_pan_down": lambda g, c, r: handle_viewport_pan_command(g, c, r, 0, 1),
        "clear_grid": handle_clear_grid,
        "toggle_simulation": handle_toggle_simulation,
        "speed_up": lambda g, c, r: handle_speed_adjustment(g, c, r, True),
        "speed_down": lambda g, c, r: handle_speed_adjustment(g, c, r, False),
    }

    # Main loop with terminal in raw mode
    should_quit = False
    with terminal.cbreak():
        while not should_quit:
            current_time = time.time()

            # Handle user input
            key = terminal.inkey(timeout=0.001)
            if key:
                command, new_renderer = handle_user_input(
                    key, config.renderer, render_state
                )
                if command:
                    # Update config with new renderer state if changed
                    if new_renderer is not config.renderer:
                        config = ControllerConfig(
                            dimensions=config.dimensions,
                            grid=config.grid,
                            renderer=new_renderer,
                        )
                    handler = command_map.get(command)
                    if handler:
                        grid, config, render_state, should_quit = handler(
                            grid, config, render_state
                        )

            # Update game state if not paused
            if (
                not render_state.pattern_mode
                and not render_state.paused
                and current_time - last_update >= config.renderer.update_interval / 1000
            ):
                grid, render_state = process_next_generation(
                    grid, config.grid.boundary, render_state
                )
                metrics = update_game_metrics(
                    metrics,
                    total_cells=grid.size,
                    active_cells=np.count_nonzero(grid),
                    births=0,  # Will be updated in render_grid
                    deaths=0,  # Will be updated in render_grid
                )
                last_update = current_time

            # Render frame if enough time has passed
            if current_time - last_frame >= 1 / 60:  # Cap at 60 FPS
                # Update renderer config with current boundary condition
                renderer_config = config.renderer
                if renderer_config.boundary_condition != config.grid.boundary:
                    renderer_config = dataclasses.replace(
                        renderer_config, boundary_condition=config.grid.boundary
                    )

                render_state, metrics = safe_render_grid(
                    terminal, grid, renderer_config, render_state, metrics
                )
                last_frame = current_time

            # Small sleep to prevent busy waiting
            time.sleep(0.001)


def main() -> None:
    """Main entry point with error handling and cleanup guarantees."""
    terminal: TerminalProtocol | None = None
    try:
        # Parse command line arguments first (without grid config)
        args = parse_arguments()

        # Initialize terminal to get dimensions
        terminal, state = initialize_terminal()
        if terminal is None or state is None:
            raise RuntimeError("Failed to initialize terminal")

        # Calculate grid dimensions based on terminal size
        # Each cell takes 2 characters width due to spacing
        # Leave more margin around the grid (6 chars on each side, 4 lines top/bottom)
        MIN_WIDTH = 30
        MIN_HEIGHT = 20

        width = max(
            MIN_WIDTH,
            args.width if args.width > 0 else (terminal.width - 12) // 2,
        )
        height = max(
            MIN_HEIGHT,
            args.height if args.height > 0 else terminal.height - 8,
        )

        # Create config with calculated dimensions
        config = ControllerConfig.create(
            width=width,
            height=height,
            density=args.density,
            boundary=BoundaryCondition[args.boundary.upper()],
            update_interval=args.interval,
        )

        # Initialize game with proper dimensions
        grid = create_grid(config.grid)

        # Set up signal handlers
        setup_signal_handlers(terminal)

        # Initialize renderer state and apply initialization
        state = RendererState.create(dimensions=config.dimensions)
        init_data, state = initialize_render_state(terminal, grid, state)
        apply_initialization(terminal, init_data)

        # Run game loop
        run_game_loop(terminal, grid, config, state)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        # Clean up
        if terminal is not None:
            cleanup_terminal(terminal)


if __name__ == "__main__":
    main()
