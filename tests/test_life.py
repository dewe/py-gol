"""Tests for pure Game of Life functions."""

import pytest

from gol.grid import BoundaryCondition, Grid, Position, get_neighbors
from gol.life import calculate_next_state, count_live_neighbors, next_generation


@pytest.mark.parametrize(
    "current_state,live_neighbors,expected",
    [
        # Live cell cases
        (True, 0, False),  # Dies from underpopulation
        (True, 1, False),  # Dies from underpopulation
        (True, 2, True),  # Survives with 2 neighbors
        (True, 3, True),  # Survives with 3 neighbors
        (True, 4, False),  # Dies from overpopulation
        (True, 8, False),  # Dies from overpopulation
        # Dead cell cases
        (False, 0, False),  # Stays dead with no neighbors
        (False, 2, False),  # Stays dead with 2 neighbors
        (False, 3, True),  # Becomes alive with 3 neighbors
        (False, 4, False),  # Stays dead with 4 neighbors
        (False, 8, False),  # Stays dead with 8 neighbors
    ],
)
def test_calculate_next_state(
    current_state: bool,
    live_neighbors: int,
    expected: bool,
) -> None:
    """Test cell state transitions based on Game of Life rules.

    Args:
        current_state: Whether cell is alive
        live_neighbors: Number of live neighbors
        expected: Expected state after transition
    """
    result = calculate_next_state(current_state, live_neighbors)
    assert result == expected


@pytest.mark.parametrize(
    "grid,pos,boundary,expected_count",
    [
        # Test with finite boundary
        (
            Grid(
                [
                    [False, True, False],
                    [True, True, True],
                    [False, True, False],
                ]
            ),
            Position((1, 1)),  # Center cell
            BoundaryCondition.FINITE,
            4,  # Should count 4 live neighbors
        ),
        (
            Grid([[True, True], [True, False]]),
            Position((0, 0)),  # Corner cell
            BoundaryCondition.FINITE,
            2,  # Should count 2 live neighbors
        ),
        # Test with toroidal boundary - simple case
        (
            Grid([[True, False], [False, True]]),
            Position((0, 0)),  # Corner wraps around
            BoundaryCondition.TOROIDAL,
            4,  # Each live neighbor is counted for each path to it
        ),
        # Test with toroidal boundary - comprehensive case
        (
            Grid([[True, True], [True, True]]),
            Position((0, 0)),  # Corner position in fully alive 2x2 grid
            BoundaryCondition.TOROIDAL,
            8,  # Should count all 8 neighbors due to wrapping
        ),
        # Test with infinite boundary
        (
            Grid([[True, True], [True, True]]),
            Position((0, 0)),  # Corner extends infinitely
            BoundaryCondition.INFINITE,
            3,  # Should only count neighbors within grid
        ),
    ],
)
def test_count_live_neighbors(
    grid: Grid,
    pos: Position,
    boundary: BoundaryCondition,
    expected_count: int,
) -> None:
    """Test counting live neighbors with different boundary conditions.

    Args:
        grid: Test grid configuration
        pos: Position to count neighbors for
        boundary: Boundary condition to apply
        expected_count: Expected number of live neighbors
    """
    neighbors = get_neighbors(grid, pos, boundary)
    print(f"\nNeighbors for {pos} with {boundary}:")
    for n in neighbors:
        print(f"  {n}: {grid[n[1]][n[0]]}")
    count = count_live_neighbors(grid, pos, boundary)
    assert count == expected_count


@pytest.mark.parametrize(
    "input_grid,boundary,expected_grid",
    [
        # Test still life (block)
        (
            Grid([[True, True], [True, True]]),
            BoundaryCondition.FINITE,
            Grid([[True, True], [True, True]]),
        ),
        # Test oscillator (blinker)
        (
            Grid(
                [
                    [False, True, False],
                    [False, True, False],
                    [False, True, False],
                ]
            ),
            BoundaryCondition.FINITE,
            Grid(
                [
                    [False, False, False],
                    [True, True, True],
                    [False, False, False],
                ]
            ),
        ),
        # Test death by underpopulation
        (
            Grid([[True, False], [False, False]]),
            BoundaryCondition.FINITE,
            Grid([[False, False], [False, False]]),
        ),
        # Test death by overpopulation
        (
            Grid(
                [
                    [True, True, True],
                    [True, True, True],
                    [True, True, True],
                ]
            ),
            BoundaryCondition.FINITE,
            Grid(
                [
                    [True, False, True],
                    [False, False, False],
                    [True, False, True],
                ]
            ),
        ),
        # Test toroidal boundary with full grid
        (
            Grid([[True, True], [True, True]]),
            BoundaryCondition.TOROIDAL,
            Grid(
                [[False, False], [False, False]]
            ),  # All cells die from overpopulation due to wrapping
        ),
        # Test toroidal boundary with oscillator
        (
            Grid([[True, True], [False, False]]),
            BoundaryCondition.TOROIDAL,
            Grid(
                [[True, True], [False, False]]
            ),  # Live cells survive (2 neighbors), dead cells stay dead (2 neighbors)
        ),
    ],
)
def test_next_generation(
    input_grid: Grid,
    boundary: BoundaryCondition,
    expected_grid: Grid,
) -> None:
    """Test complete grid state transitions.

    Args:
        input_grid: Initial grid state
        boundary: Boundary condition to apply
        expected_grid: Expected grid state after one generation
    """
    result = next_generation(input_grid, boundary)

    # Compare dimensions
    assert len(result) == len(expected_grid)
    assert len(result[0]) == len(expected_grid[0])

    # Compare cell states
    for y in range(len(result)):
        for x in range(len(result[0])):
            assert result[y][x] == expected_grid[y][x], (
                f"Mismatch at position ({x}, {y}): "
                f"expected {expected_grid[y][x]}, got {result[y][x]}"
            )


def test_analyze_2x2_toroidal() -> None:
    """Analyze neighbor counts for each position in a 2x2 toroidal grid."""
    grid = Grid([[True, True], [False, False]])
    boundary = BoundaryCondition.TOROIDAL

    print("\nAnalyzing 2x2 grid with toroidal boundaries:")
    print("Initial grid:")
    print("[[True, True]]")
    print("[[False, False]]")
    print("\nNeighbor analysis:")

    # Check each position
    positions = [
        Position((0, 0)),
        Position((1, 0)),
        Position((0, 1)),
        Position((1, 1)),
    ]

    for pos in positions:
        neighbors = get_neighbors(grid, pos, boundary)
        count = count_live_neighbors(grid, pos, boundary)
        print(f"\nPosition {pos}:")
        print(f"Current state: {'ALIVE' if grid[pos[1]][pos[0]] else 'DEAD'}")
        print("Neighbors (with wrapping):")
        for n in neighbors:
            print(f"  {n}: {'ALIVE' if grid[n[1]][n[0]] else 'DEAD'}")
        print(f"Total live neighbors: {count}")
