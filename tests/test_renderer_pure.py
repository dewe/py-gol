"""Tests for pure renderer functions.

Tests the pure computational functions extracted from the renderer module.
"""

import numpy as np

from gol.metrics import create_metrics
from gol.patterns import PatternTransform
from gol.renderer import calculate_pattern_cells, calculate_render_metrics
from gol.types import RenderGrid


def test_calculate_render_metrics_initial_state() -> None:
    """Given a grid with no previous state
    When calculating render metrics
    Then should return metrics with initial values
    """
    # Given
    grid = np.array([[0, 1, 1], [1, 0, 0]], dtype=bool)  # 2x3 grid with 3 live cells
    metrics = create_metrics()

    # When
    new_metrics = calculate_render_metrics(grid, None, metrics)

    # Then
    assert new_metrics.game.total_cells == 6  # 2x3 grid
    assert new_metrics.game.active_cells == 3  # Three live cells
    assert new_metrics.game.births_this_second == 0  # No births without previous state
    assert new_metrics.game.deaths_this_second == 0  # No deaths without previous state


def test_calculate_render_metrics_with_changes() -> None:
    """Given a grid with previous state
    When calculating render metrics
    Then should detect births and deaths correctly
    """
    # Given
    current_grid = np.array([[0, 1, 1], [1, 1, 0]], dtype=bool)  # 4 live cells
    previous_grid: RenderGrid = {
        (1, 0): True,
        (2, 0): True,
        (0, 1): True,
    }  # 3 live cells
    metrics = create_metrics()

    # When
    new_metrics = calculate_render_metrics(current_grid, previous_grid, metrics)

    # Then
    assert new_metrics.game.total_cells == 6
    assert new_metrics.game.active_cells == 4
    assert new_metrics.game.births_this_second == 1  # One new cell
    assert new_metrics.game.deaths_this_second == 0  # No cells died


def test_calculate_render_metrics_with_births_and_deaths() -> None:
    """Given a grid with both births and deaths
    When calculating render metrics
    Then should track both births and deaths correctly
    """
    # Given
    current_grid = np.array([[1, 0, 1], [0, 1, 0]], dtype=bool)  # 3 live cells
    previous_grid: RenderGrid = {
        (0, 0): False,  # Birth
        (1, 0): True,  # Death
        (2, 0): True,  # No change
        (0, 1): False,  # No change
        (1, 1): False,  # Birth
        (2, 1): True,  # Death
    }
    metrics = create_metrics()

    # When
    new_metrics = calculate_render_metrics(current_grid, previous_grid, metrics)

    # Then
    assert new_metrics.game.total_cells == 6
    assert new_metrics.game.active_cells == 3
    assert new_metrics.game.births_this_second == 2  # Two cells born
    assert new_metrics.game.deaths_this_second == 2  # Two cells died


def test_calculate_render_metrics_frame_tracking() -> None:
    """Given multiple metric updates
    When calculating render metrics
    Then should track frame metrics correctly
    """
    # Given
    grid = np.array([[1, 0], [0, 1]], dtype=bool)
    metrics = create_metrics()

    # When - simulate multiple frames
    for _ in range(5):
        metrics = calculate_render_metrics(grid, None, metrics)

    # Then
    assert metrics.game.total_cells == 4
    assert metrics.game.active_cells == 2
    # Generation count should not increment during rendering
    assert metrics.game.generation_count == 0
    # Frame metrics should be updated
    assert metrics.perf.frames_this_second > 0


def test_calculate_pattern_cells_no_pattern() -> None:
    """Given no selected pattern
    When calculating pattern cells
    Then should return empty set
    """
    # Given
    grid_width, grid_height = 10, 10
    cursor_pos = (5, 5)

    # When
    cells = calculate_pattern_cells(
        grid_width,
        grid_height,
        None,  # No pattern selected
        cursor_pos,
        PatternTransform.NONE,
    )

    # Then
    assert cells == set()


def test_calculate_pattern_cells_with_pattern() -> None:
    """Given a selected pattern
    When calculating pattern cells
    Then should return correct cell positions
    """
    # Given
    grid_width, grid_height = 10, 10
    cursor_pos = (5, 5)
    pattern_name = "block"  # 2x2 block pattern

    # When
    cells = calculate_pattern_cells(
        grid_width,
        grid_height,
        pattern_name,
        cursor_pos,
        PatternTransform.NONE,
    )

    # Then
    # Block pattern should have 4 cells around the cursor
    expected_cells = {(4, 4), (4, 5), (5, 4), (5, 5)}
    assert cells == expected_cells


def test_calculate_pattern_cells_with_rotation() -> None:
    """Given a pattern with rotation
    When calculating pattern cells
    Then should return correctly rotated positions
    """
    # Given
    grid_width, grid_height = 10, 10
    cursor_pos = (5, 5)
    pattern_name = "blinker"  # Horizontal line of 3 cells that becomes vertical

    # When - rotate 90 degrees
    cells = calculate_pattern_cells(
        grid_width,
        grid_height,
        pattern_name,
        cursor_pos,
        PatternTransform.RIGHT,  # 90 degree rotation
    )

    # Then
    assert len(cells) == 3  # Blinker has 3 cells

    # Get sorted coordinates for reliable testing
    sorted_cells = sorted(cells)

    # Check that cells form a vertical line
    # After rotation, cells should share the same x coordinate
    # and have consecutive y coordinates
    x_coord = sorted_cells[0][0]
    assert all(cell[0] == x_coord for cell in sorted_cells)
    y_coords = [cell[1] for cell in sorted_cells]
    assert y_coords == [y_coords[0] + i for i in range(3)]
