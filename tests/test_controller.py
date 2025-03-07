"""Tests for game controller."""

from unittest.mock import Mock, patch

import numpy as np
import pytest

from gol.controller import (
    BoundaryCondition,
    ControllerConfig,
    GridConfig,
    handle_viewport_pan,
    initialize_game,
    process_generation,
    resize_game,
)
from gol.grid import create_grid
from gol.renderer import cleanup_terminal
from gol.state import RendererState, ViewportState


@pytest.fixture
def config() -> ControllerConfig:
    """Create test configuration."""
    return ControllerConfig.create(
        width=2,
        height=2,
        density=0.5,
        boundary=BoundaryCondition.FINITE,
        update_interval=100,
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
    config = ControllerConfig.create(
        width=30,
        height=20,
        density=0.3,
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

    config = ControllerConfig.create(
        width=30,
        height=20,
        density=0.3,  # Use valid dimensions
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

    config = ControllerConfig.create(
        width=10,
        height=10,
        density=0.3,  # Use valid dimensions
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


def test_viewport_pan_boundaries() -> None:
    """
    Given: A grid and viewport of known dimensions
    When: Panning the viewport in different directions
    Then: Should stop at grid boundaries
    """
    # Create initial state with viewport smaller than grid
    grid_width, grid_height = 50, 30
    viewport_width, viewport_height = 20, 10
    initial_state = RendererState().with_viewport(
        ViewportState(
            dimensions=(viewport_width, viewport_height),
            offset_x=0,
            offset_y=0,
        )
    )

    # Test panning right to boundary
    max_x_offset = grid_width - viewport_width
    state = initial_state
    for _ in range(max_x_offset + 5):  # Try to pan beyond boundary
        state = handle_viewport_pan(state, 1, 0, grid_width, grid_height)
    assert state.viewport.offset_x == max_x_offset  # Should stop at boundary

    # Test panning down to boundary
    max_y_offset = grid_height - viewport_height
    state = initial_state
    for _ in range(max_y_offset + 5):  # Try to pan beyond boundary
        state = handle_viewport_pan(state, 0, 1, grid_width, grid_height)
    assert state.viewport.offset_y == max_y_offset  # Should stop at boundary

    # Test panning left to boundary
    state = initial_state.with_viewport(
        ViewportState(
            dimensions=(viewport_width, viewport_height),
            offset_x=max_x_offset,
            offset_y=0,
        )
    )
    for _ in range(max_x_offset + 5):  # Try to pan beyond boundary
        state = handle_viewport_pan(state, -1, 0, grid_width, grid_height)
    assert state.viewport.offset_x == 0  # Should stop at boundary

    # Test panning up to boundary
    state = initial_state.with_viewport(
        ViewportState(
            dimensions=(viewport_width, viewport_height),
            offset_x=0,
            offset_y=max_y_offset,
        )
    )
    for _ in range(max_y_offset + 5):  # Try to pan beyond boundary
        state = handle_viewport_pan(state, 0, -1, grid_width, grid_height)
    assert state.viewport.offset_y == 0  # Should stop at boundary


def test_viewport_pan_diagonal_boundaries() -> None:
    """
    Given: A grid and viewport of known dimensions
    When: Panning the viewport diagonally
    Then: Should respect both x and y boundaries independently
    """
    # Create initial state with viewport smaller than grid
    grid_width, grid_height = 50, 30
    viewport_width, viewport_height = 20, 10
    initial_state = RendererState().with_viewport(
        ViewportState(
            dimensions=(viewport_width, viewport_height),
            offset_x=0,
            offset_y=0,
        )
    )

    # Test panning to bottom-right corner
    max_x_offset = grid_width - viewport_width
    max_y_offset = grid_height - viewport_height
    state = initial_state
    for _ in range(max(max_x_offset, max_y_offset) + 5):
        state = handle_viewport_pan(state, 1, 1, grid_width, grid_height)
    assert state.viewport.offset_x == max_x_offset
    assert state.viewport.offset_y == max_y_offset

    # Test panning to top-left corner
    state = initial_state.with_viewport(
        ViewportState(
            dimensions=(viewport_width, viewport_height),
            offset_x=max_x_offset,
            offset_y=max_y_offset,
        )
    )
    for _ in range(max(max_x_offset, max_y_offset) + 5):
        state = handle_viewport_pan(state, -1, -1, grid_width, grid_height)
    assert state.viewport.offset_x == 0
    assert state.viewport.offset_y == 0
