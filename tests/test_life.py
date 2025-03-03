"""Tests for pure Game of Life functions."""

import pytest

from gol.grid import BoundaryCondition, Grid, Position, get_neighbors
from gol.life import calculate_next_state, count_live_neighbors, next_generation


@pytest.mark.parametrize(
    "current_state,live_neighbors,expected",
    [
        # Live cell cases
        ((True, 1), 0, (False, 0)),  # Dies from underpopulation
        ((True, 1), 1, (False, 0)),  # Dies from underpopulation
        ((True, 1), 2, (True, 2)),  # Survives with 2 neighbors
        ((True, 2), 3, (True, 3)),  # Survives with 3 neighbors
        ((True, 3), 4, (False, 0)),  # Dies from overpopulation
        ((True, 4), 8, (False, 0)),  # Dies from overpopulation
        # Dead cell cases
        ((False, 0), 0, (False, 0)),  # Stays dead with no neighbors
        ((False, 0), 2, (False, 0)),  # Stays dead with 2 neighbors
        ((False, 0), 3, (True, 1)),  # Becomes alive with 3 neighbors
        ((False, 0), 4, (False, 0)),  # Stays dead with 4 neighbors
        ((False, 0), 8, (False, 0)),  # Stays dead with 8 neighbors
    ],
)
def test_calculate_next_state(
    current_state: tuple[bool, int],
    live_neighbors: int,
    expected: tuple[bool, int],
) -> None:
    """Test cell state transitions based on Game of Life rules.

    Args:
        current_state: (is_alive, age) tuple
        live_neighbors: Number of live neighbors
        expected: Expected (is_alive, age) tuple after transition
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
                    [(False, 0), (True, 1), (False, 0)],
                    [(True, 1), (True, 1), (True, 1)],
                    [(False, 0), (True, 1), (False, 0)],
                ]
            ),
            Position((1, 1)),  # Center cell
            BoundaryCondition.FINITE,
            4,  # Should count 4 live neighbors
        ),
        (
            Grid([[(True, 1), (True, 1)], [(True, 1), (False, 0)]]),
            Position((0, 0)),  # Corner cell
            BoundaryCondition.FINITE,
            2,  # Should count 2 live neighbors
        ),
        # Test with toroidal boundary - simple case
        (
            Grid([[(True, 1), (False, 0)], [(False, 0), (True, 1)]]),
            Position((0, 0)),  # Corner wraps around
            BoundaryCondition.TOROIDAL,
            4,  # Each live neighbor is counted for each path to it
        ),
        # Test with toroidal boundary - comprehensive case
        (
            Grid([[(True, 1), (True, 1)], [(True, 1), (True, 1)]]),
            Position((0, 0)),  # Corner position in fully alive 2x2 grid
            BoundaryCondition.TOROIDAL,
            8,  # Should count all 8 neighbors due to wrapping
        ),
        # Test with infinite boundary
        (
            Grid([[(True, 1), (True, 1)], [(True, 1), (True, 1)]]),
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
        print(f"  {n}: {grid[n[1]][n[0]][0]}")
    count = count_live_neighbors(grid, pos, boundary)
    assert count == expected_count


@pytest.mark.parametrize(
    "input_grid,boundary,expected_grid",
    [
        # Test still life (block)
        (
            Grid([[(True, 1), (True, 1)], [(True, 1), (True, 1)]]),
            BoundaryCondition.FINITE,
            Grid([[(True, 2), (True, 2)], [(True, 2), (True, 2)]]),
        ),
        # Test oscillator (blinker)
        (
            Grid(
                [
                    [(False, 0), (True, 1), (False, 0)],
                    [(False, 0), (True, 1), (False, 0)],
                    [(False, 0), (True, 1), (False, 0)],
                ]
            ),
            BoundaryCondition.FINITE,
            Grid(
                [
                    [(False, 0), (False, 0), (False, 0)],
                    [(True, 1), (True, 2), (True, 1)],
                    [(False, 0), (False, 0), (False, 0)],
                ]
            ),
        ),
        # Test death by underpopulation
        (
            Grid([[(True, 1), (False, 0)], [(False, 0), (False, 0)]]),
            BoundaryCondition.FINITE,
            Grid([[(False, 0), (False, 0)], [(False, 0), (False, 0)]]),
        ),
        # Test death by overpopulation
        (
            Grid(
                [
                    [(True, 1), (True, 1), (True, 1)],
                    [(True, 1), (True, 1), (True, 1)],
                    [(True, 1), (True, 1), (True, 1)],
                ]
            ),
            BoundaryCondition.FINITE,
            Grid(
                [
                    [(True, 2), (False, 0), (True, 2)],
                    [(False, 0), (False, 0), (False, 0)],
                    [(True, 2), (False, 0), (True, 2)],
                ]
            ),
        ),
        # Test toroidal boundary with full grid
        (
            Grid([[(True, 1), (True, 1)], [(True, 1), (True, 1)]]),
            BoundaryCondition.TOROIDAL,
            Grid(
                [[(False, 0), (False, 0)], [(False, 0), (False, 0)]]
            ),  # All cells die from overpopulation due to wrapping
        ),
        # Test toroidal boundary with oscillator
        (
            Grid([[(True, 1), (True, 1)], [(False, 0), (False, 0)]]),
            BoundaryCondition.TOROIDAL,
            Grid(
                [[(True, 2), (True, 2)], [(False, 0), (False, 0)]]
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

    # Compare cell states and ages
    for y in range(len(result)):
        for x in range(len(result[0])):
            assert result[y][x] == expected_grid[y][x], (
                f"Mismatch at position ({x}, {y}): "
                f"expected {expected_grid[y][x]}, got {result[y][x]}"
            )


def test_analyze_2x2_toroidal() -> None:
    """Analyze neighbor counts for each position in a 2x2 toroidal grid."""
    grid = Grid([[(True, 1), (True, 1)], [(False, 0), (False, 0)]])
    boundary = BoundaryCondition.TOROIDAL

    print("\nAnalyzing 2x2 grid with toroidal boundaries:")
    print("Initial grid:")
    print("[(True, 1), (True, 1)]")
    print("[(False, 0), (False, 0)]")
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
        print(f"Current state: {'ALIVE' if grid[pos[1]][pos[0]][0] else 'DEAD'}")
        print("Neighbors (with wrapping):")
        for n in neighbors:
            print(f"  {n}: {'ALIVE' if grid[n[1]][n[0]][0] else 'DEAD'}")
        print(f"Total live neighbors: {count}")
