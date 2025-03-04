"""Tests for grid management."""

from typing import Callable

import pytest

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
    live_cells = sum(sum(1 for cell in row if cell) for row in grid)
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
            [True, True, True],
            [False, False, False],
            [False, False, False],
        ]
    )

    new_grid = resize_grid(grid, new_width=2, new_height=2)

    assert len(new_grid) == 2
    assert len(new_grid[0]) == 2
    assert new_grid[0][0] and new_grid[0][1]  # Top row preserved
    assert not new_grid[1][0] and not new_grid[1][1]  # Bottom row preserved


def test_grid_resizing_larger() -> None:
    """
    Given: A grid with known pattern
    When: Resizing to larger dimensions
    Then: Should preserve original pattern and fill new cells with dead state
    """
    grid = Grid([[True, True], [False, False]])

    new_grid = resize_grid(grid, new_width=3, new_height=3)

    assert len(new_grid) == 3
    assert len(new_grid[0]) == 3
    assert new_grid[0][0] and new_grid[0][1]  # Original pattern preserved
    assert not new_grid[0][2]  # New cells dead
    assert not any(cell for cell in new_grid[2])  # New row dead


@pytest.mark.parametrize(
    "boundary,grid,pos,expected_neighbors,expected_conditions",
    [
        # Test finite boundary
        (
            BoundaryCondition.FINITE,
            Grid(
                [
                    [True, True, True],
                    [False, False, False],
                    [False, False, False],
                ]
            ),
            Position((0, 0)),  # Corner position
            3,  # Expected number of neighbors
            lambda neighbors: all(  # All positions within grid
                [
                    Position((0, 1)) in neighbors,
                    Position((1, 0)) in neighbors,
                    Position((0, 1)) in neighbors,
                ]
            ),
        ),
        # Test toroidal boundary
        (
            BoundaryCondition.TOROIDAL,
            Grid([[True, True], [False, False]]),
            Position((0, 0)),  # Corner position
            8,  # Expected number of neighbors
            lambda neighbors: all(
                [  # Check wrapping positions
                    Position((1, 1)) in neighbors,  # Bottom-right
                    Position((1, 0)) in neighbors,  # Right
                    Position((0, 1)) in neighbors,  # Bottom
                ]
            ),
        ),
        (
            BoundaryCondition.TOROIDAL,
            Grid(
                [
                    [True, True, True],
                    [False, False, False],
                    [False, False, False],
                ]
            ),
            Position((0, 0)),  # Corner position
            8,  # Expected number of neighbors
            lambda neighbors: all(  # All positions within grid
                [
                    Position((0, 1)) in neighbors,
                    Position((1, 1)) in neighbors,
                    Position((1, 0)) in neighbors,
                    Position((2, 0)) in neighbors,
                    Position((0, 2)) in neighbors,
                    Position((2, 2)) in neighbors,
                    Position((2, 1)) in neighbors,
                    Position((1, 2)) in neighbors,
                ]
            ),
        ),
        # Test infinite boundary
        (
            BoundaryCondition.INFINITE,
            Grid([[True, True], [False, False]]),
            Position((0, 0)),  # Corner position
            8,  # Expected number of neighbors
            # Check positions outside grid boundaries
            lambda n: all(
                [
                    Position((-1, -1)) in n,
                    Position((-1, 0)) in n,
                    Position((-1, 1)) in n,
                ]
            ),
        ),
    ],
)
def test_boundary_conditions(
    boundary: BoundaryCondition,
    grid: Grid,
    pos: Position,
    expected_neighbors: int,
    expected_conditions: Callable[
        [list[Position]],  # Input type: list of positions
        bool,  # Return type: boolean
    ],
) -> None:
    """Test neighbor calculation for different boundary conditions.

    Args:
        boundary: The boundary condition to test
        grid: Test grid configuration
        pos: Position to get neighbors for
        expected_neighbors: Expected number of neighbors
        expected_conditions: Function to verify specific conditions for each
            boundary type
    """
    neighbors = get_neighbors(grid, pos, boundary)

    # Print debug info
    print(f"\nTesting {boundary} boundary:")
    print(f"Position: {pos}")
    print("Neighbors:")
    for n in neighbors:
        print(f"  {n}")

    # Verify number of neighbors
    assert len(neighbors) == expected_neighbors

    # Verify boundary-specific conditions
    assert expected_conditions(neighbors)


def test_grid_section_finite() -> None:
    """
    Given: A grid with finite boundary
    When: Getting a section partially outside grid
    Then: Should return section with dead cells for outside positions
    """
    grid = Grid([[True, True], [False, False]])

    section = get_grid_section(
        grid,
        Position((1, 1)),  # Start inside
        Position((2, 2)),  # End outside
        BoundaryCondition.FINITE,
    )

    assert len(section) == 2  # Requested height
    assert len(section[0]) == 2  # Requested width
    assert not section[0][1]  # Outside position is dead
    assert not section[1][0]  # Outside position is dead
    assert not section[1][1]  # Outside position is dead


def test_grid_section_toroidal() -> None:
    """
    Given: A grid with toroidal boundary
    When: Getting a section across grid edge
    Then: Should wrap around to opposite edge
    """
    grid = Grid([[True, False], [False, True]])

    section = get_grid_section(
        grid,
        Position((1, 1)),  # Bottom-right
        Position((2, 2)),  # Wraps around
        BoundaryCondition.TOROIDAL,
    )

    assert len(section) == 2
    assert len(section[0]) == 2
    assert section[0][0]  # Bottom-right cell is alive
    assert not section[0][1]  # Wrapped top-right is dead
    assert not section[1][0]  # Wrapped bottom-left is dead
    assert section[1][1]  # Wrapped top-left is alive


def test_count_neighbors_infinite() -> None:
    """
    Given: A grid with infinite boundary
    When: Counting neighbors including positions outside grid
    Then: Should only count live cells within actual grid
    """
    grid = Grid([[True, True], [False, False]])

    # Include positions outside grid
    positions = [
        Position((-1, -1)),  # Outside
        Position((0, 0)),  # Inside, alive
        Position((1, 0)),  # Inside, alive
    ]

    count = count_live_neighbors(grid, positions, BoundaryCondition.INFINITE)
    assert count == 2  # Only cells within grid boundaries
