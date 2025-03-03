"""Tests for grid management."""

from gol.grid import (
    BoundaryCondition,
    Grid,
    GridConfig,
    Position,
    count_live_neighbors,
    create_grid,
    get_grid_section,
    get_neighbors,
    resize_grid,
)


def test_grid_creation() -> None:
    """
    Given: A grid of 10x8 and density of 0.3
    When: Creating a new grid
    Then: Grid should be 10x8
    And: Approximately 30% of cells should be alive (with 20% margin)
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


def test_grid_resizing_smaller() -> None:
    """
    Given: A grid with known pattern
    When: Resizing to smaller dimensions
    Then: Should preserve pattern within new bounds
    """
    grid = Grid(
        [
            [(True, 1), (True, 1), (True, 1)],
            [(False, 0), (False, 0), (False, 0)],
            [(False, 0), (False, 0), (False, 0)],
        ]
    )

    new_grid = resize_grid(grid, new_width=2, new_height=2)

    assert len(new_grid) == 2
    assert len(new_grid[0]) == 2
    assert new_grid[0][0][0] and new_grid[0][1][0]  # Top row preserved
    assert not new_grid[1][0][0] and not new_grid[1][1][0]  # Bottom row preserved


def test_grid_resizing_larger() -> None:
    """
    Given: A grid with known pattern
    When: Resizing to larger dimensions
    Then: Should preserve original pattern and fill new cells with dead state
    """
    grid = Grid([[(True, 1), (True, 1)], [(False, 0), (False, 0)]])

    new_grid = resize_grid(grid, new_width=3, new_height=3)

    assert len(new_grid) == 3
    assert len(new_grid[0]) == 3
    assert new_grid[0][0][0] and new_grid[0][1][0]  # Original pattern preserved
    assert not new_grid[0][2][0]  # New cells dead
    assert not any(cell[0] for cell in new_grid[2])  # New row dead


def test_finite_boundary() -> None:
    """
    Given: A grid with finite boundary
    When: Getting neighbors at edge
    Then: Should only return valid positions within grid
    """
    grid = Grid(
        [
            [(True, 1), (True, 1), (True, 1)],
            [(False, 0), (False, 0), (False, 0)],
            [(False, 0), (False, 0), (False, 0)],
        ]
    )

    corner_pos = Position((0, 0))
    neighbors = get_neighbors(grid, corner_pos, BoundaryCondition.FINITE)

    assert len(neighbors) == 3  # Only 3 valid neighbors for corner
    assert all(0 <= pos[0] < 3 and 0 <= pos[1] < 3 for pos in neighbors)


def test_toroidal_boundary() -> None:
    """
    Given: A grid with toroidal boundary
    When: Getting neighbors at edge
    Then: Should wrap around to opposite edge
    """
    grid = Grid([[(True, 1), (True, 1)], [(False, 0), (False, 0)]])

    corner_pos = Position((0, 0))
    neighbors = get_neighbors(grid, corner_pos, BoundaryCondition.TOROIDAL)

    assert len(neighbors) == 8  # All 8 neighbors valid in toroidal grid
    # Check wrapping
    assert Position((1, 1)) in neighbors  # Bottom-right
    assert Position((1, 0)) in neighbors  # Right
    assert Position((0, 1)) in neighbors  # Bottom
    assert Position((1, 1)) in neighbors  # Bottom-right


def test_infinite_boundary() -> None:
    """
    Given: A grid with infinite boundary
    When: Getting neighbors at edge
    Then: Should return all eight neighbors
    """
    grid = Grid([[(True, 1), (True, 1)], [(False, 0), (False, 0)]])

    corner_pos = Position((0, 0))
    neighbors = get_neighbors(grid, corner_pos, BoundaryCondition.INFINITE)

    assert len(neighbors) == 8  # All 8 neighbors returned
    # Check positions outside grid included
    assert Position((-1, -1)) in neighbors
    assert Position((-1, 0)) in neighbors
    assert Position((-1, 1)) in neighbors


def test_grid_section_finite() -> None:
    """
    Given: A grid with finite boundary
    When: Getting a section partially outside grid
    Then: Should return section with dead cells for outside positions
    """
    grid = Grid([[(True, 1), (True, 1)], [(False, 0), (False, 0)]])

    section = get_grid_section(
        grid,
        Position((1, 1)),  # Start inside
        Position((2, 2)),  # End outside
        BoundaryCondition.FINITE,
    )

    assert len(section) == 2  # Requested height
    assert len(section[0]) == 2  # Requested width
    assert not section[0][1][0]  # Outside position is dead
    assert not section[1][0][0]  # Outside position is dead
    assert not section[1][1][0]  # Outside position is dead


def test_grid_section_toroidal() -> None:
    """
    Given: A grid with toroidal boundary
    When: Getting a section across grid edge
    Then: Should wrap around to opposite edge
    """
    grid = Grid([[(True, 1), (False, 0)], [(False, 0), (True, 1)]])

    section = get_grid_section(
        grid,
        Position((1, 1)),  # Bottom-right
        Position((2, 2)),  # Wraps around
        BoundaryCondition.TOROIDAL,
    )

    assert len(section) == 2
    assert len(section[0]) == 2
    assert section[0][0][0]  # Bottom-right cell is alive
    assert not section[0][1][0]  # Wrapped top-right is dead
    assert not section[1][0][0]  # Wrapped bottom-left is dead
    assert section[1][1][0]  # Wrapped top-left is alive


def test_count_neighbors_infinite() -> None:
    """
    Given: A grid with infinite boundary
    When: Counting neighbors including positions outside grid
    Then: Should only count live cells within actual grid
    """
    grid = Grid([[(True, 1), (True, 1)], [(False, 0), (False, 0)]])

    # Include positions outside grid
    positions = [
        Position((-1, -1)),  # Outside
        Position((0, 0)),  # Inside, alive
        Position((1, 0)),  # Inside, alive
    ]

    count = count_live_neighbors(grid, positions, BoundaryCondition.INFINITE)
    assert count == 2  # Only counts cells within actual grid
