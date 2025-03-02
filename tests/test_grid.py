"""Tests for grid management."""

from gol.grid import (
    Grid,
    GridConfig,
    Position,
    count_live_neighbors,
    create_grid,
    get_neighbors,
)


def test_grid_creation() -> None:
    """
    Given a grid size of 10 and density of 0.3
    When creating a new grid
    Then grid should be 10x10
    And approximately 30% of cells should be alive (with 15% margin)
    """
    config = GridConfig(size=10, density=0.3)
    grid = create_grid(config)

    # Check grid dimensions
    assert len(grid) == 10
    assert all(len(row) == 10 for row in grid)

    # Check approximate density (with 15% margin to reduce flakiness)
    live_cells = sum(sum(1 for cell in row if cell) for row in grid)
    total_cells = 100
    actual_density = live_cells / total_cells
    assert (
        0.15 <= actual_density <= 0.45
    ), f"Expected density between 15% and 45%, got {actual_density * 100:.1f}%"


def test_neighbor_positions() -> None:
    """
    Given a 3x3 grid
    When getting neighbors for center position
    Then should return all 8 surrounding positions
    """
    grid = Grid([[False] * 3 for _ in range(3)])
    center = Position((1, 1))

    neighbors = get_neighbors(grid, center)  # Non-toroidal by default

    assert len(neighbors) == 8
    expected = {(0, 0), (0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1), (2, 2)}
    assert {(x, y) for x, y in neighbors} == expected


def test_edge_neighbor_positions_non_toroidal() -> None:
    """
    Given a 3x3 grid in non-toroidal mode
    When getting neighbors for corner position (0,0)
    Then should return only 3 valid neighbors
    """
    grid = Grid([[False] * 3 for _ in range(3)])
    corner = Position((0, 0))

    neighbors = get_neighbors(grid, corner, toroidal=False)

    assert len(neighbors) == 3
    expected = {
        (0, 1),  # Right
        (1, 0),  # Bottom
        (1, 1),  # Bottom-right
    }
    assert {(x, y) for x, y in neighbors} == expected


def test_edge_neighbor_positions_toroidal() -> None:
    """
    Given a 3x3 grid in toroidal mode
    When getting neighbors for corner position (0,0)
    Then should return 8 neighbors with wrapping
    """
    grid = Grid([[False] * 3 for _ in range(3)])
    corner = Position((0, 0))

    neighbors = get_neighbors(grid, corner, toroidal=True)

    assert len(neighbors) == 8
    expected = {
        (0, 1),  # Right
        (0, 2),  # Wrapped top
        (1, 0),  # Bottom
        (1, 1),  # Bottom-right
        (1, 2),  # Wrapped bottom-top
        (2, 0),  # Wrapped left
        (2, 1),  # Wrapped left-right
        (2, 2),  # Wrapped left-top
    }
    assert {(x, y) for x, y in neighbors} == expected


def test_toroidal_wrapping() -> None:
    """
    Given a 3x3 grid in toroidal mode
    When getting neighbors for all edge positions
    Then should correctly wrap around to opposite edges
    """
    grid = Grid([[False] * 3 for _ in range(3)])

    # Test right edge wrapping to left
    right_edge = Position((2, 1))
    right_neighbors = get_neighbors(grid, right_edge, toroidal=True)
    assert Position((0, 1)) in right_neighbors  # Wraps to left edge

    # Test bottom edge wrapping to top
    bottom_edge = Position((1, 2))
    bottom_neighbors = get_neighbors(grid, bottom_edge, toroidal=True)
    assert Position((1, 0)) in bottom_neighbors  # Wraps to top edge

    # Test diagonal wrapping
    corner = Position((2, 2))
    corner_neighbors = get_neighbors(grid, corner, toroidal=True)
    assert Position((0, 0)) in corner_neighbors  # Wraps diagonally


def test_count_live_neighbors() -> None:
    """
    Given a grid with known live cells
    When counting neighbors for a position
    Then should return correct number of live neighbors
    """
    grid = Grid([[True, False, False], [False, True, False], [False, False, True]])
    center = Position((1, 1))

    neighbors = get_neighbors(grid, center)
    count = count_live_neighbors(grid, neighbors)

    assert count == 2  # Top-left and bottom-right are alive


def test_high_density_grid_creation() -> None:
    """
    Given a grid size of 10 and high density of 0.9
    When creating a new grid
    Then grid should be 10x10
    And approximately 90% of cells should be alive (with 10% margin)
    """
    config = GridConfig(size=10, density=0.9)
    grid = create_grid(config)

    # Check grid dimensions
    assert len(grid) == 10
    assert all(len(row) == 10 for row in grid)

    # Check approximate density (with 10% margin to reduce flakiness)
    live_cells = sum(sum(1 for cell in row if cell) for row in grid)
    total_cells = 100
    actual_density = live_cells / total_cells
    assert (
        0.8 <= actual_density <= 1.0
    ), f"Expected density between 80% and 100%, got {actual_density * 100:.1f}%"
