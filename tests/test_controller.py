"""Tests for game controller."""

from unittest.mock import Mock, patch

import numpy as np
import pytest

from gol.controller import (
    ControllerConfig,
    GridConfig,
    RendererConfig,
    initialize_game,
    process_generation,
    resize_game,
)
from gol.grid import BoundaryCondition, create_grid
from gol.renderer import cleanup_terminal


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
    assert isinstance(grid, np.ndarray)  # Grid is now a NumPy array
    assert grid.dtype == np.bool_  # Check correct dtype
    assert grid.shape == (config.grid.height, config.grid.width)  # Check dimensions


def test_resize_game() -> None:
    """Test grid resizing."""
    # Create initial grid and config
    config = GridConfig(width=10, height=10, density=0.3)
    grid = create_grid(config)

    # Test resize to larger dimensions
    new_grid, new_config = resize_game(grid, 20, 15, config)
    assert new_grid.shape == (15, 20)
    assert new_config.width == 20
    assert new_config.height == 15
    assert new_config.density == config.density  # Should preserve density
    assert new_config.boundary == config.boundary  # Should preserve boundary
    assert new_config is not config  # Should be a new instance

    # Test resize to smaller dimensions
    new_grid, new_config = resize_game(grid, 5, 8, config)
    assert new_grid.shape == (8, 5)
    assert new_config.width == 5
    assert new_config.height == 8
    assert new_config.density == config.density  # Should preserve density
    assert new_config.boundary == config.boundary  # Should preserve boundary
    assert new_config is not config  # Should be a new instance


def test_initialize_game_with_dimensions() -> None:
    """Test game initialization with explicit dimensions."""
    config = ControllerConfig(
        grid=GridConfig(width=30, height=20, density=0.3),
        renderer=RendererConfig(),
    )

    terminal, grid = initialize_game(config)
    try:
        assert grid.shape == (20, 30)  # Height, width
    finally:
        cleanup_terminal(terminal)


def create_mock_terminal() -> Mock:
    """Create a mock terminal with proper context manager support."""
    terminal = Mock()
    terminal.width = 80
    terminal.height = 24

    # Create a context manager mock
    cbreak_context = Mock()
    cbreak_context.__enter__ = Mock(return_value=None)
    cbreak_context.__exit__ = Mock(return_value=None)
    terminal.cbreak = Mock(return_value=cbreak_context)

    return terminal


@patch("gol.controller.initialize_terminal")
def test_initialize_game_auto_dimensions(mock_init_terminal: Mock) -> None:
    """Test game initialization with auto dimensions."""
    terminal = create_mock_terminal()
    state = Mock()
    mock_init_terminal.return_value = (terminal, state)

    config = ControllerConfig(
        grid=GridConfig(width=30, height=20, density=0.3),  # Use valid dimensions
        renderer=RendererConfig(),
    )
    grid = initialize_game(config)[1]

    assert grid.shape[1] == 30  # Original width preserved
    assert grid.shape[0] == 20  # Original height preserved


@patch("gol.controller.initialize_terminal")
def test_initialize_game_minimum_dimensions(mock_init_terminal: Mock) -> None:
    """Test game initialization with minimum dimensions."""
    terminal = create_mock_terminal()
    terminal.width = 30  # Minimum width to fit 10 cells (2 chars each) + margins
    terminal.height = 12  # Minimum height to fit 10 cells + status lines
    state = Mock()
    mock_init_terminal.return_value = (terminal, state)

    config = ControllerConfig(
        grid=GridConfig(width=10, height=10, density=0.3),  # Use valid dimensions
        renderer=RendererConfig(),
    )
    grid = initialize_game(config)[1]

    assert grid.shape[1] >= 10
    assert grid.shape[0] >= 10


def test_process_generation(config: ControllerConfig) -> None:
    """
    Given: A grid with known pattern
    When: Processing one generation
    Then: Should apply Game of Life rules correctly
    """
    # Create initial grid with blinker pattern
    grid = np.array(
        [
            [False, True, False],
            [False, True, False],
            [False, True, False],
        ],
        dtype=np.bool_,
    )

    # Process one generation
    new_grid = process_generation(grid, BoundaryCondition.FINITE)

    # Check that blinker oscillates correctly
    assert not new_grid[0, 1]  # Top cell dies
    assert new_grid[1, 0]  # Left cell becomes alive
    assert new_grid[1, 1]  # Center cell survives
    assert new_grid[1, 2]  # Right cell becomes alive
    assert not new_grid[2, 1]  # Bottom cell dies
