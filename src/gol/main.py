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
    - Esc: Exit pattern mode
  C: Clear grid
  Arrow keys: Move cursor
  Q: Quit game
  W: Toggle wrap mode
  +/-: Resize grid larger/smaller (auto-fits to terminal)
  Up/Down: Adjust speed
  Mouse: Click to toggle cells
"""

import argparse
import dataclasses
import signal
import sys
import time
from typing import Any, Callable, Dict, Literal, Tuple

import numpy as np

from gol.controller import ControllerConfig, process_generation, resize_game
from gol.grid import BoundaryCondition, GridConfig, create_grid
from gol.metrics import create_metrics, update_game_metrics
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
from gol.types import Grid

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


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments and provide sensible defaults.

    Uses efficient default values optimized for typical terminal sizes
    while ensuring minimum playable dimensions.

    Returns:
        Raw argument namespace for flexible dimension handling
    """
    parser = argparse.ArgumentParser(
        description="Conway's Game of Life\n\n"
        "Controls:\n"
        "  - Press 'q' or Ctrl-C to quit the game\n"
        "  - Press 'r' to restart with a new grid\n"
        "  - Press 'p' to enter pattern mode\n"
        "  - Press 'b' to cycle boundary conditions\n"
        "  - Press '+'/'-' to resize grid (auto-fits to terminal with margins)\n"
        "  - Press '['/']' to rotate pattern\n"
        "  - Press Space to place pattern\n"
        "  - Press Escape to exit pattern mode\n"
        "  - Press ↑/↓ to adjust simulation speed"
    )

    # Use more efficient default values
    parser.add_argument(
        "--width",
        type=int,
        default=0,  # Default to auto-size
        help=(
            "Width of the grid (auto-sized to terminal width if not specified "
            "or set to 0, minimum 30)"
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
    initial_state: RendererState,
) -> None:
    """Main game loop implementing Conway's Game of Life rules.

    Manages game state updates, user input handling, and rendering with
    performance optimizations like frame rate limiting and efficient
    terminal updates.
    """
    # Track timing for performance optimization
    last_frame = time.time()
    last_update = time.time()

    # Initialize state and metrics
    state = initial_state
    metrics = create_metrics()

    # Command handlers
    def handle_quit() -> tuple[Grid, ControllerConfig, bool]:
        return grid, config, True

    def handle_restart() -> tuple[Grid, ControllerConfig, bool]:
        new_grid = create_grid(config.grid)
        nonlocal metrics
        metrics = create_metrics()  # Reset metrics on restart
        return new_grid, config, False

    def handle_pattern_mode() -> tuple[Grid, ControllerConfig, bool]:
        """Toggle pattern mode with state preservation.

        Manages mode transitions while preserving pattern selection and
        ensuring proper cursor positioning for pattern placement.
        """
        nonlocal state
        # Toggle pattern mode
        state = state.with_pattern_mode(not state.pattern_mode)

        if state.pattern_mode:
            # Entering pattern mode - keep current pattern if set
            new_renderer = config.renderer.with_pattern(
                config.renderer.selected_pattern
                or "glider"  # Use existing pattern or default to glider
            )
            new_config = ControllerConfig(
                grid=config.grid,
                renderer=new_renderer,
            )
            # Initialize cursor position to center of grid
            state = state.with_cursor_position(
                config.grid.width // 2, config.grid.height // 2
            )
        else:
            # Exiting pattern mode via ESC - unpause and clear pattern
            new_renderer = config.renderer.with_pattern(None)
            new_config = ControllerConfig(
                grid=config.grid,
                renderer=new_renderer,
            )

        return grid, new_config, False

    def handle_cursor_movement(direction: str) -> tuple[Grid, ControllerConfig, bool]:
        """Handle wrapped cursor movement within grid bounds."""
        nonlocal state
        if state.pattern_mode:
            if direction == "left":
                state = state.with_cursor_position(
                    (state.cursor_x - 1) % config.grid.width, state.cursor_y
                )
            elif direction == "right":
                state = state.with_cursor_position(
                    (state.cursor_x + 1) % config.grid.width, state.cursor_y
                )
            elif direction == "up":
                state = state.with_cursor_position(
                    state.cursor_x, (state.cursor_y - 1) % config.grid.height
                )
            elif direction == "down":
                state = state.with_cursor_position(
                    state.cursor_x, (state.cursor_y + 1) % config.grid.height
                )

        return grid, config, False

    def handle_place_pattern() -> tuple[Grid, ControllerConfig, bool]:
        """Handle pattern placement in pattern mode.

        Returns:
            Tuple of (grid, config, should_quit)
        """
        nonlocal state
        if state.pattern_mode and config.renderer.selected_pattern:
            pattern = BUILTIN_PATTERNS.get(
                config.renderer.selected_pattern
            ) or FilePatternStorage().load_pattern(config.renderer.selected_pattern)

            if pattern:
                # Use place_pattern with centering enabled
                new_grid = place_pattern(
                    grid,
                    pattern,
                    (state.cursor_x, state.cursor_y),
                    config.renderer.pattern_rotation,
                    centered=True,
                )
                # Keep pattern mode active and clear selected pattern
                new_renderer = config.renderer.with_pattern(None)
                new_config = ControllerConfig(
                    grid=config.grid,
                    renderer=new_renderer,
                )
                return new_grid, new_config, False

        return grid, config, False

    def handle_rotate_pattern() -> tuple[Grid, ControllerConfig, bool]:
        """Handle pattern rotation in pattern mode.

        Returns:
            Tuple of (grid, config, should_quit)
        """
        # No need to update rotation here since it's already handled in renderer
        return grid, config, False

    def handle_resize(larger: bool) -> tuple[Grid, ControllerConfig, bool]:
        """Resize grid while preserving content and preventing artifacts.

        Implements smooth resize operation with:
        - Terminal dimension constraints
        - Artifact prevention
        - State preservation
        - Proper redraw triggering
        """
        nonlocal state
        # Calculate max dimensions based on terminal size
        # Each cell takes 2 characters width due to spacing
        # Reserve 2 lines at bottom for status/menu
        # Add margin of 4 characters on each side for better display
        margin = 4
        max_width = (
            terminal.width - (2 * margin)
        ) // 2  # Each cell is 2 chars wide with spacing
        max_height = terminal.height - 2  # Reserve bottom lines for status/menu

        # Calculate new dimensions
        factor = 1.2 if larger else 0.8
        requested_width = int(config.grid.width * factor)
        requested_height = int(config.grid.height * factor)

        # Enforce minimum and maximum dimensions
        # If requested size exceeds terminal, force it to fit
        new_width = max(10, min(max_width, requested_width))
        new_height = max(10, min(max_height, requested_height))

        # Only resize if dimensions actually changed
        if new_width != config.grid.width or new_height != config.grid.height:
            # Clear screen before resize to prevent artifacts
            print(terminal.clear(), end="", flush=True)
            print(terminal.move_xy(0, 0), end="", flush=True)

            # Clear any remaining artifacts
            for y in range(terminal.height):
                print(terminal.move_xy(0, y) + " " * terminal.width, end="", flush=True)
            sys.stdout.flush()

            # Force full redraw by clearing renderer state
            state = state.with_previous_grid(None)
            state = state.with_pattern_cells(None)

            # Resize grid and update config
            new_grid, new_grid_config = resize_game(
                grid, new_width, new_height, config.grid
            )

            # Create new controller config
            new_config = ControllerConfig(
                grid=new_grid_config,
                renderer=config.renderer,
            )
            return new_grid, new_config, False

        return grid, config, False

    def handle_cycle_boundary() -> tuple[Grid, ControllerConfig, bool]:
        """Cycle through available boundary conditions."""
        current = config.grid.boundary
        new_boundary = {
            BoundaryCondition.FINITE: BoundaryCondition.TOROIDAL,
            BoundaryCondition.TOROIDAL: BoundaryCondition.INFINITE,
            BoundaryCondition.INFINITE: BoundaryCondition.FINITE,
        }[current]

        new_grid_config = config.grid.with_boundary(new_boundary)
        # Update renderer config with new boundary condition
        new_renderer_config = dataclasses.replace(
            config.renderer, boundary_condition=new_boundary
        )
        new_config = ControllerConfig(
            grid=new_grid_config,
            renderer=new_renderer_config,
        )
        return grid, new_config, False

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
        "cycle_boundary": handle_cycle_boundary,
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
                command, new_renderer = handle_user_input(key, config.renderer, state)
                if command:
                    # Update config with new renderer state if changed
                    if new_renderer is not config.renderer:
                        config = ControllerConfig(
                            grid=config.grid,
                            renderer=new_renderer,
                        )
                    handler = command_map.get(command)
                    if handler:
                        grid, config, should_quit = handler()

            # Update game state if not paused
            if (
                not state.pattern_mode
                and current_time - last_update >= config.renderer.update_interval / 1000
            ):
                grid = process_generation(grid, config.grid.boundary)
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

                state, metrics = safe_render_grid(
                    terminal, grid, renderer_config, state, metrics
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
        terminal, _ = initialize_terminal()
        if terminal is None:
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
        config = ControllerConfig(
            grid=GridConfig(
                width=width,
                height=height,
                density=args.density,
                boundary=BoundaryCondition[args.boundary.upper()],
            ),
            renderer=RendererConfig(
                update_interval=args.interval,
                boundary_condition=BoundaryCondition[args.boundary.upper()],
            ),
        )

        # Initialize game with proper dimensions
        grid = create_grid(config.grid)

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
        if terminal is not None:
            cleanup_terminal(terminal)


if __name__ == "__main__":
    main()
