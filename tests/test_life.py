"""Tests for pure Game of Life functions."""

import numpy as np
import pytest

from gol.grid import BoundaryCondition, count_live_neighbors, get_neighbors
from gol.life import calculate_next_state, next_generation
from gol.types import Grid, GridPosition, IntArray


def create_grid(data: list[list[bool]]) -> Grid:
    """Create a Grid from a list of boolean lists.

    Args:
        data: List of boolean lists representing the grid

    Returns:
        Grid array with proper type

    Example:
        >>> grid = create_grid([[True, False], [False, True]])
        >>> grid.shape
        (2, 2)
    """
    return np.array(data, dtype=np.bool_)


def create_neighbor_counts(data: list[list[int]]) -> IntArray:
    """Create a neighbor count array from a list of integer lists.

    Args:
        data: List of integer lists representing neighbor counts

    Returns:
        Integer array with proper type

    Example:
        >>> counts = create_neighbor_counts([[2, 3], [1, 0]])
        >>> counts.shape
        (2, 2)
    """
    return np.array(data, dtype=np.int_)


# Test data for cell state transitions
UNDERPOPULATION_CASES = [
    (True, 0, False),  # Dies from underpopulation
    (True, 1, False),  # Dies from underpopulation
]

SURVIVAL_CASES = [
    (True, 2, True),  # Survives with 2 neighbors
    (True, 3, True),  # Survives with 3 neighbors
]

OVERPOPULATION_CASES = [
    (True, 4, False),  # Dies from overpopulation
    (True, 8, False),  # Dies from overpopulation
]

BIRTH_CASES = [
    (False, 0, False),  # Stays dead with no neighbors
    (False, 2, False),  # Stays dead with 2 neighbors
    (False, 3, True),  # Becomes alive with 3 neighbors
    (False, 4, False),  # Stays dead with 4 neighbors
    (False, 8, False),  # Stays dead with 8 neighbors
]


@pytest.mark.parametrize(
    "current_state,live_neighbors,expected",
    [
        *UNDERPOPULATION_CASES,
        *SURVIVAL_CASES,
        *OVERPOPULATION_CASES,
        *BIRTH_CASES,
    ],
)
def test_calculate_next_state(
    current_state: bool,
    live_neighbors: int,
    expected: bool,
) -> None:
    """Test cell state transitions based on Game of Life rules.

    Given: A cell with a specific state and number of live neighbors
    When: Calculating its next state
    Then: Should follow Conway's Game of Life rules

    Args:
        current_state: Whether cell is alive
        live_neighbors: Number of live neighbors
        expected: Expected state after transition
    """
    # Convert inputs to numpy arrays for vectorized operation
    current_array: Grid = create_grid([[current_state]])
    neighbors_array: IntArray = create_neighbor_counts([[live_neighbors]])

    result = calculate_next_state(current_array, neighbors_array)
    assert result[0, 0] == expected


# Common test patterns
CROSS_PATTERN = [
    [False, True, False],
    [True, True, True],
    [False, True, False],
]

BLOCK_PATTERN = [[True, True], [True, True]]

BLINKER_PATTERN = [
    [False, True, False],
    [False, True, False],
    [False, True, False],
]

BLINKER_NEXT = [
    [False, False, False],
    [True, True, True],
    [False, False, False],
]


@pytest.mark.parametrize(
    "grid,pos,boundary,expected_count",
    [
        # Test with finite boundary
        (
            create_grid(CROSS_PATTERN),
            (1, 1),  # Center cell
            BoundaryCondition.FINITE,
            4,  # Should count 4 live neighbors
        ),
        (
            create_grid([[True, True], [True, False]]),
            (0, 0),  # Corner cell
            BoundaryCondition.FINITE,
            2,  # Should count 2 live neighbors
        ),
        # Test with toroidal boundary - simple case
        (
            create_grid([[True, False], [False, True]]),
            (0, 0),  # Corner wraps around
            BoundaryCondition.TOROIDAL,
            4,  # Each live neighbor is counted for each path to it
        ),
        # Test with toroidal boundary - comprehensive case
        (
            create_grid(BLOCK_PATTERN),
            (0, 0),  # Corner position in fully alive 2x2 grid
            BoundaryCondition.TOROIDAL,
            8,  # Should count all 8 neighbors due to wrapping
        ),
        # Test with infinite boundary
        (
            create_grid(BLOCK_PATTERN),
            (0, 0),  # Corner extends infinitely
            BoundaryCondition.INFINITE,
            3,  # Should only count neighbors within grid
        ),
    ],
)
def test_count_live_neighbors(
    grid: Grid,
    pos: GridPosition,
    boundary: BoundaryCondition,
    expected_count: int,
) -> None:
    """Test counting live neighbors with different boundary conditions.

    Given: A grid with a specific pattern and boundary condition
    When: Counting live neighbors for a position
    Then: Should return correct count based on boundary rules

    Args:
        grid: Test grid configuration
        pos: Position to count neighbors for
        boundary: Boundary condition to apply
        expected_count: Expected number of live neighbors
    """
    neighbors = get_neighbors(grid, pos, boundary)
    print(f"\nNeighbors for {pos} with {boundary}:")
    for n in neighbors:
        print(f"  {n}: {grid[n[1], n[0]]}")
    count = count_live_neighbors(grid, neighbors, boundary)
    assert count == expected_count


@pytest.mark.parametrize(
    "input_grid,boundary,expected_grid",
    [
        # Test still life (block)
        (
            create_grid(BLOCK_PATTERN),
            BoundaryCondition.FINITE,
            create_grid(BLOCK_PATTERN),
        ),
        # Test oscillator (blinker)
        (
            create_grid(BLINKER_PATTERN),
            BoundaryCondition.FINITE,
            create_grid(BLINKER_NEXT),
        ),
        # Test death by underpopulation
        (
            create_grid([[True, False], [False, False]]),
            BoundaryCondition.FINITE,
            create_grid([[False, False], [False, False]]),
        ),
        # Test death by overpopulation
        (
            create_grid(
                [
                    [True, True, True],
                    [True, True, True],
                    [True, True, True],
                ]
            ),
            BoundaryCondition.FINITE,
            create_grid(
                [
                    [True, False, True],
                    [False, False, False],
                    [True, False, True],
                ]
            ),
        ),
        # Test toroidal boundary with full grid
        (
            create_grid(BLOCK_PATTERN),
            BoundaryCondition.TOROIDAL,
            create_grid([[False, False], [False, False]]),
            # All cells die from overpopulation due to wrapping
        ),
        # Test toroidal boundary with oscillator
        (
            create_grid([[True, True], [False, False]]),
            BoundaryCondition.TOROIDAL,
            create_grid([[True, True], [False, False]]),
            # Live cells survive (2 neighbors), dead cells stay dead (2 neighbors)
        ),
    ],
)
def test_next_generation(
    input_grid: Grid,
    boundary: BoundaryCondition,
    expected_grid: Grid,
) -> None:
    """Test complete grid state transitions.

    Given: A grid with a specific pattern and boundary condition
    When: Calculating the next generation
    Then: Should evolve according to Game of Life rules

    Args:
        input_grid: Initial grid state
        boundary: Boundary condition to apply
        expected_grid: Expected grid state after one generation
    """
    result = next_generation(input_grid, boundary)
    np.testing.assert_array_equal(result, expected_grid)


def test_analyze_2x2_toroidal() -> None:
    """Analyze neighbor counts for each position in a 2x2 toroidal grid.

    Given: A 2x2 grid with toroidal boundary
    When: Analyzing neighbor counts for each position
    Then: Should correctly identify neighbors and states with wrapping
    """
    grid: Grid = create_grid([[True, True], [False, False]])
    boundary = BoundaryCondition.TOROIDAL

    print("\nAnalyzing 2x2 grid with toroidal boundaries:")
    print("Initial grid:")
    print(grid)
    print("\nNeighbor analysis:")

    # Check each position
    positions: list[GridPosition] = [(0, 0), (1, 0), (0, 1), (1, 1)]

    for pos in positions:
        neighbors = get_neighbors(grid, pos, boundary)
        count = count_live_neighbors(grid, neighbors, boundary)
        print(f"\nPosition {pos}:")
        print(f"Current state: {'ALIVE' if grid[pos[1], pos[0]] else 'DEAD'}")
        print("Neighbors (with wrapping):")
        for n in neighbors:
            print(f"  {n}: {'ALIVE' if grid[n[1], n[0]] else 'DEAD'}")
        print(f"Total live neighbors: {count}")
