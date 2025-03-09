"""Command handlers for Game of Life user interactions."""

import dataclasses
import sys

import numpy as np

from gol.controller import (
    ControllerConfig,
    handle_viewport_pan,
    handle_viewport_resize,
    resize_game,
)
from gol.grid import BoundaryCondition, create_grid
from gol.patterns import BUILTIN_PATTERNS, FilePatternStorage, place_pattern
from gol.renderer import RendererState, TerminalProtocol
from gol.types import Grid


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
