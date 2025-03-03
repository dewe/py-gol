"""Game of Life controller implementation."""

from dataclasses import dataclass
from typing import Optional, Tuple

from gol.grid import BoundaryCondition, Grid, GridConfig, create_grid, resize_grid
from gol.life import next_generation
from gol.renderer import (
    RendererConfig,
    TerminalProtocol,
    cleanup_terminal,
    initialize_terminal,
)


@dataclass(frozen=True)
class ControllerConfig:
    """Configuration for game controller."""

    grid: GridConfig
    renderer: RendererConfig
    selected_pattern: Optional[str] = None
    pattern_rotation: int = 0


def initialize_game(config: ControllerConfig) -> Tuple[TerminalProtocol, Grid]:
    """Initialize game components.

    Args:
        config: Controller configuration parameters

    Returns:
        Tuple of (terminal, grid)

    Raises:
        RuntimeError: If terminal initialization fails
    """
    # Initialize terminal
    terminal, _ = initialize_terminal(config.renderer)
    if terminal is None:
        raise RuntimeError("Failed to initialize terminal")

    # Create initial grid
    grid = create_grid(config.grid)

    return terminal, grid


def resize_game(
    grid: Grid,
    new_width: int,
    new_height: int,
    config: GridConfig,
) -> Tuple[Grid, GridConfig]:
    """Resize the game grid.

    Args:
        grid: Current grid state
        new_width: New grid width
        new_height: New grid height
        config: Grid configuration

    Returns:
        Tuple of (new grid, new config)
    """
    # Create new grid with preserved pattern
    new_grid = resize_grid(grid, new_width, new_height)

    # Create new configuration
    new_config = GridConfig(
        width=new_width,
        height=new_height,
        density=config.density,
        boundary=config.boundary,
    )

    return new_grid, new_config


def process_generation(grid: Grid, boundary: BoundaryCondition) -> Grid:
    """Process one generation of cell updates.

    Args:
        grid: Current grid state
        boundary: Boundary condition to apply

    Returns:
        New grid state for next generation
    """
    return next_generation(grid, boundary)


def cleanup_game(terminal: TerminalProtocol) -> None:
    """Clean up game resources.

    Args:
        terminal: Terminal instance to cleanup
    """
    # Restore terminal state using proper cleanup sequence
    cleanup_terminal(terminal)
