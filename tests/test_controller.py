"""Tests for game controller."""

import pytest

from gol.controller import (
    ControllerConfig,
    GridConfig,
    initialize_game,
    process_generation,
    resize_game,
)
from gol.grid import BoundaryCondition, Grid
from gol.renderer import RendererConfig


@pytest.fixture
def config() -> ControllerConfig:
    """Create test configuration."""
    return ControllerConfig(
        grid=GridConfig(
            width=2,
            height=2,
            density=0.5,
            boundary=BoundaryCondition.FINITE,
        ),
        renderer=RendererConfig(update_interval=100),
    )


def test_initialize_game(config: ControllerConfig) -> None:
    """
    Given: A valid configuration
    When: Initializing the game
    Then: Should return terminal and grid
    """
    terminal, grid = initialize_game(config)

    assert terminal is not None
    assert isinstance(grid, list)  # Grid is a NewType of list
    assert len(grid) == config.grid.height
    assert len(grid[0]) == config.grid.width


def test_resize_game(config: ControllerConfig) -> None:
    """
    Given: A grid with known pattern
    When: Resizing the grid
    Then: Should preserve pattern within new bounds
    """
    # Create initial grid with known pattern
    grid = Grid([[True, True], [False, False]])

    # Resize to larger dimensions
    new_width = 3
    new_height = 3
    new_grid, new_config = resize_game(grid, new_width, new_height, config.grid)

    # Check dimensions
    assert len(new_grid) == new_height
    assert len(new_grid[0]) == new_width

    # Check pattern preservation
    assert new_grid[0][0] and new_grid[0][1]  # Original pattern preserved
    assert not any(cell for cell in new_grid[2])  # New row dead


def test_process_generation(config: ControllerConfig) -> None:
    """
    Given: A grid with known pattern
    When: Processing one generation
    Then: Should apply Game of Life rules correctly
    """
    # Create initial grid with blinker pattern
    grid = Grid(
        [
            [False, True, False],
            [False, True, False],
            [False, True, False],
        ]
    )

    # Process one generation
    new_grid = process_generation(grid, BoundaryCondition.FINITE)

    # Check that blinker oscillates correctly
    assert not new_grid[0][1]  # Top cell dies
    assert new_grid[1][0]  # Left cell becomes alive
    assert new_grid[1][1]  # Center cell survives
    assert new_grid[1][2]  # Right cell becomes alive
    assert not new_grid[2][1]  # Bottom cell dies
