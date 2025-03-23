"""Command handlers for Game of Life user interactions."""

import dataclasses
import sys

import numpy as np
from blessed.keyboard import Keystroke

from gol.controller import (
    ControllerConfig,
    handle_viewport_pan,
    handle_viewport_resize,
    resize_game,
)
from gol.grid import BoundaryCondition, create_grid
from gol.patterns import BUILTIN_PATTERNS, FilePatternStorage, place_pattern
from gol.renderer import RendererConfig, RendererState, TerminalProtocol
from gol.types import CommandType, Grid


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
        # Center cursor in current viewport
        viewport_x = render_state.viewport.offset_x + (render_state.viewport.width // 2)
        viewport_y = render_state.viewport.offset_y + (
            render_state.viewport.height // 2
        )
        new_render_state = new_render_state.with_cursor(viewport_x, viewport_y)
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
    min_interval = config.renderer.min_interval
    max_interval = config.renderer.max_interval
    interval_threshold = config.renderer.interval_threshold
    step = (
        config.renderer.max_interval_step
        if current_interval > interval_threshold
        else config.renderer.min_interval_step
    )
    new_interval = round(
        max(
            min_interval,
            min(
                max_interval,
                current_interval - step if increase else current_interval + step,
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
    """Handle cursor movement within grid bounds."""
    if not render_state.pattern_mode:
        return grid, config, render_state, False

    new_x, new_y = render_state.cursor_x, render_state.cursor_y

    # Handle cursor movement based on boundary condition
    if config.grid.boundary in (BoundaryCondition.FINITE, BoundaryCondition.TOROIDAL):
        # Wrap coordinates for FINITE and TOROIDAL boundaries
        if direction == "left":
            new_x = (render_state.cursor_x - 1) % config.grid.width
        elif direction == "right":
            new_x = (render_state.cursor_x + 1) % config.grid.width
        elif direction == "up":
            new_y = (render_state.cursor_y - 1) % config.grid.height
        elif direction == "down":
            new_y = (render_state.cursor_y + 1) % config.grid.height
    else:  # INFINITE boundary
        # Don't wrap coordinates for INFINITE boundary
        if direction == "left":
            new_x = render_state.cursor_x - 1
        elif direction == "right":
            new_x = render_state.cursor_x + 1
        elif direction == "up":
            new_y = render_state.cursor_y - 1
        elif direction == "down":
            new_y = render_state.cursor_y + 1

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
    new_render_state = render_state.with_previous_grid(None).with_pattern_cells(None)

    # Resize grid and update configs
    new_grid, new_grid_config = resize_game(grid, new_width, new_height, config.grid)
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

    # When switching from INFINITE to FINITE/TOROIDAL, resize grid to match viewport
    if current == BoundaryCondition.INFINITE and new_boundary in (
        BoundaryCondition.FINITE,
        BoundaryCondition.TOROIDAL,
    ):
        new_grid, new_grid_config = resize_game(
            grid,
            render_state.viewport.width,
            render_state.viewport.height,
            config.grid,
        )
        # Update boundary condition after resizing
        new_grid_config = new_grid_config.with_boundary(new_boundary)
    else:
        new_grid = grid
        new_grid_config = config.grid.with_boundary(new_boundary)

    new_renderer_config = dataclasses.replace(
        config.renderer, boundary_condition=new_boundary
    )
    new_config = ControllerConfig(
        dimensions=(new_grid_config.width, new_grid_config.height),
        grid=new_grid_config,
        renderer=new_renderer_config,
    )
    return new_grid, new_config, render_state, False


def handle_viewport_resize_command(
    grid: Grid,
    config: ControllerConfig,
    render_state: RendererState,
    expand: bool,
    terminal: TerminalProtocol,
) -> tuple[Grid, ControllerConfig, RendererState, bool]:
    """Handle viewport resize while preserving content.

    For FINITE and TOROIDAL boundary conditions, the grid is resized to exactly match
    the viewport dimensions. For INFINITE boundary condition, only the viewport is
    resized.
    """
    # First resize the viewport
    new_render_state = handle_viewport_resize(render_state, expand, terminal)

    # Clear screen and handle artifacts
    print(terminal.clear(), end="", flush=True)
    print(terminal.move_xy(0, 0), end="", flush=True)
    for y in range(terminal.height):
        print(terminal.move_xy(0, y) + " " * terminal.width, end="", flush=True)
    sys.stdout.flush()

    # Clear the previous render state to force complete redraw
    new_render_state = new_render_state.with_previous_grid(None).with_pattern_cells(
        None
    )

    # Only resize grid for FINITE and TOROIDAL boundaries
    if config.grid.boundary in (
        BoundaryCondition.FINITE,
        BoundaryCondition.TOROIDAL,
    ):
        # Get new viewport dimensions
        viewport = new_render_state.viewport
        new_width = viewport.width
        new_height = viewport.height

        # Always resize to match viewport exactly
        new_grid, new_grid_config = resize_game(
            grid,
            new_width,
            new_height,
            config.grid,
        )
        new_config = ControllerConfig(
            dimensions=(new_width, new_height),
            grid=new_grid_config,
            renderer=config.renderer,
        )
        return new_grid, new_config, new_render_state, False

    return grid, config, new_render_state, False


def handle_viewport_pan_command(
    grid: Grid,
    config: ControllerConfig,
    render_state: RendererState,
    dx: int,
    dy: int,
) -> tuple[Grid, ControllerConfig, RendererState, bool]:
    """Handle viewport panning."""
    grid_height, grid_width = grid.shape  # (y, x)
    new_render_state = handle_viewport_pan(
        render_state, dx, dy, grid_width, grid_height
    )
    return grid, config, new_render_state, False


def handle_toggle_debug(
    grid: Grid, config: ControllerConfig, render_state: RendererState
) -> tuple[Grid, ControllerConfig, RendererState, bool]:
    """Toggle debug mode."""
    new_render_state = render_state.with_debug_mode(not render_state.debug_mode)
    return grid, config, new_render_state, False


def handle_normal_mode_input(
    key: Keystroke, config: RendererConfig
) -> tuple[CommandType, RendererConfig]:
    """Handle keyboard input when in normal mode."""
    if str(key) == "\x1b" or key.name == "KEY_ESCAPE":
        return "quit", config

    # Grid commands
    match str(key):
        case "c":
            return "clear_grid", config
        case "b":
            return "cycle_boundary", config
        case "+":
            return "resize_larger", config
        case "-":
            return "resize_smaller", config
        case "r":
            return "restart", config
        case "d":
            return "toggle_debug", config
        case _ if str(key) in (" ", "KEY_SPACE"):
            return "toggle_simulation", config

    # Speed control
    match key.name:
        case "KEY_SUP":
            return "speed_up", config.with_decreased_interval()
        case "KEY_SDOWN":
            return "speed_down", config.with_increased_interval()

    # Viewport movement
    match key.name:
        case "KEY_LEFT":
            return "viewport_pan_left", config
        case "KEY_RIGHT":
            return "viewport_pan_right", config
        case "KEY_UP":
            return "viewport_pan_up", config
        case "KEY_DOWN":
            return "viewport_pan_down", config

    return "continue", config
