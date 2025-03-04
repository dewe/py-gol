"""Game of Life controller implementation."""

from dataclasses import dataclass
from typing import Optional, Tuple

from gol.grid import BoundaryCondition, GridConfig, create_grid, resize_grid
from gol.life import next_generation
from gol.patterns import PatternTransform
from gol.renderer import (
    RendererConfig,
    TerminalProtocol,
    cleanup_terminal,
    initialize_terminal,
)
from gol.types import Grid


@dataclass(frozen=True)
class ControllerConfig:
    """Configuration for game controller."""

    grid: GridConfig
    renderer: RendererConfig
    selected_pattern: Optional[str] = None
    pattern_rotation: PatternTransform = PatternTransform.NONE


def initialize_game(
    config: ControllerConfig,
) -> Tuple[TerminalProtocol, Grid]:
    """Initialize game components and handle terminal setup.

    Manages terminal initialization in raw mode for direct keyboard input,
    ensuring proper cleanup on failure.
    """
    terminal, state = initialize_terminal()
    if terminal is None or state is None:
        raise RuntimeError("Failed to initialize terminal")

    try:
        with terminal.cbreak():
            # Handle auto-sizing if dimensions are 0
            if config.grid.width <= 0 or config.grid.height <= 0:
                MIN_WIDTH = 30
                MIN_HEIGHT = 20

                # Calculate dimensions based on terminal size
                width = max(
                    MIN_WIDTH,
                    (
                        (terminal.width - 12) // 2
                        if config.grid.width <= 0
                        else config.grid.width
                    ),
                )
                height = max(
                    MIN_HEIGHT,
                    (
                        terminal.height - 8
                        if config.grid.height <= 0
                        else config.grid.height
                    ),
                )

                # Create new config with calculated dimensions
                new_grid_config = config.grid.with_dimensions(width, height)
                config = ControllerConfig(
                    grid=new_grid_config,
                    renderer=config.renderer,
                )

            grid = create_grid(config.grid)
            return terminal, grid
    except Exception as e:
        cleanup_terminal(terminal)
        raise RuntimeError(f"Failed to initialize game: {str(e)}")


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
    new_config = config.with_dimensions(new_width, new_height)

    return new_grid, new_config


def process_generation(grid: Grid, boundary: BoundaryCondition) -> Grid:
    """Process one generation of cell updates using the Game of Life rules."""
    return next_generation(grid, boundary)


def cleanup_game(terminal: TerminalProtocol) -> None:
    """Restore terminal to its original state and release resources."""
    cleanup_terminal(terminal)
