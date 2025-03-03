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
    Given a grid of 10x8 and density of 0.3
    When creating a new grid
    Then grid should be 10x8
    And approximately 30% of cells should be alive (with 20% margin)
    """
    config = GridConfig(width=10, height=8, density=0.3)
    grid = create_grid(config)

    # Check grid dimensions
    assert len(grid) == 8  # height
    assert all(len(row) == 10 for row in grid)  # width

    # Check approximate density (with 20% margin to reduce flakiness)
    live_cells = sum(sum(1 for cell in row if cell[0]) for row in grid)
    total_cells = 80  # 10x8
    actual_density = live_cells / total_cells
    assert (
        0.1 <= actual_density <= 0.5
    ), f"Expected density between 10% and 50%, got {actual_density * 100:.1f}%"


def test_neighbor_positions() -> None:
    """
    Given a grid and a center position
    When getting neighbor positions
    Then should return all valid neighbor positions
    """
    grid = Grid([[(False, 0) for _ in range(3)] for _ in range(3)])
    center = Position((1, 1))

    neighbors = get_neighbors(grid, center)

    # Center position should have all 8 neighbors
    assert len(neighbors) == 8, f"Expected 8 neighbors, got {len(neighbors)}"

    # Check that all neighbors are within one step of center
    for pos in neighbors:
        x_diff = abs(pos[0] - center[0])
        y_diff = abs(pos[1] - center[1])
        assert x_diff <= 1 and y_diff <= 1, f"Invalid neighbor position: {pos}"
        assert not (
            x_diff == 0 and y_diff == 0
        ), "Center position included in neighbors"


def test_edge_neighbor_positions_non_toroidal() -> None:
    """
    Given a grid and an edge position
    When getting neighbor positions with toroidal=False
    Then should only return valid neighbors within grid bounds
    """
    grid = Grid([[(False, 0) for _ in range(3)] for _ in range(3)])
    corner = Position((0, 0))

    neighbors = get_neighbors(grid, corner, toroidal=False)

    # Corner should have only 3 neighbors
    assert len(neighbors) == 3, f"Expected 3 neighbors for corner, got {len(neighbors)}"

    # All positions should be within grid bounds
    for pos in neighbors:
        assert 0 <= pos[0] < 3 and 0 <= pos[1] < 3, f"Position out of bounds: {pos}"


def test_edge_neighbor_positions_toroidal() -> None:
    """
    Given a grid and an edge position
    When getting neighbor positions with toroidal=True
    Then should wrap around grid edges
    """
    grid = Grid([[(False, 0) for _ in range(3)] for _ in range(3)])
    corner = Position((0, 0))

    neighbors = get_neighbors(grid, corner, toroidal=True)

    # Corner should have all 8 neighbors in toroidal mode
    assert len(neighbors) == 8, f"Expected 8 neighbors for corner, got {len(neighbors)}"


def test_toroidal_wrapping() -> None:
    """
    Given a grid and a corner position
    When getting neighbors with toroidal=True
    Then should correctly wrap around grid edges
    """
    grid = Grid([[(False, 0) for _ in range(3)] for _ in range(3)])
    corner = Position((0, 0))

    neighbors = get_neighbors(grid, corner, toroidal=True)

    # Check that wrapping works correctly
    expected_positions = {
        (0, 1),  # Right
        (1, 0),  # Bottom
        (1, 1),  # Bottom-right
        (0, 2),  # Top (wrapped)
        (1, 2),  # Top-right (wrapped)
        (2, 0),  # Bottom-left (wrapped)
        (2, 1),  # Left (wrapped)
        (2, 2),  # Top-left (wrapped)
    }

    neighbor_set = {(pos[0], pos[1]) for pos in neighbors}
    assert (
        neighbor_set == expected_positions
    ), f"Unexpected neighbor positions: {neighbor_set}"


def test_count_live_neighbors() -> None:
    """
    Given a grid with known live cells
    When counting neighbors for a position
    Then should return correct number of live neighbors
    """
    grid = Grid(
        [
            [(True, 1), (False, 0), (False, 0)],
            [(False, 0), (True, 1), (False, 0)],
            [(False, 0), (False, 0), (True, 1)],
        ]
    )
    center = Position((1, 1))

    neighbors = get_neighbors(grid, center)
    count = count_live_neighbors(grid, neighbors)

    # Center cell has 2 live neighbors (top-left and bottom-right)
    assert count == 2, f"Expected 2 live neighbors, got {count}"


def test_high_density_grid_creation() -> None:
    """
    Given a grid configuration with high density
    When creating a new grid
    Then should have approximately the specified density of live cells
    """
    config = GridConfig(width=20, height=20, density=0.8)
    grid = create_grid(config)

    live_cells = sum(sum(1 for cell in row if cell[0]) for row in grid)
    total_cells = 400  # 20x20
    actual_density = live_cells / total_cells

    # Allow 20% margin to reduce test flakiness
    assert (
        0.6 <= actual_density <= 1.0
    ), f"Expected density between 60% and 100%, got {actual_density * 100:.1f}%"
