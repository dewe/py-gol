"""Tests for Game of Life rules and transitions."""

import json
from pathlib import Path

import numpy as np
import pytest

from gol.grid import BoundaryCondition, count_live_neighbors, get_neighbors
from gol.life import calculate_next_state, next_generation
from gol.types import Grid, GridPosition, IntArray
from tests.conftest import create_test_grid

# Load test patterns
with open(Path(__file__).parent / "test_data" / "patterns.json") as f:
    TEST_PATTERNS = json.load(f)["test_patterns"]


def create_neighbor_counts(data: list[list[int]]) -> IntArray:
    """Create a neighbor count array from a list of integer lists."""
    return np.array(data, dtype=np.int_)


@pytest.mark.rules
class TestGameRules:
    """Tests for Game of Life rules."""

    @pytest.mark.parametrize(
        "current_state,live_neighbors,expected",
        [
            # Underpopulation
            (True, 0, False),
            (True, 1, False),
            # Survival
            (True, 2, True),
            (True, 3, True),
            # Overpopulation
            (True, 4, False),
            (True, 8, False),
            # Birth
            (False, 3, True),
            # Stay dead
            (False, 0, False),
            (False, 2, False),
            (False, 4, False),
            (False, 8, False),
        ],
    )
    def test_cell_state_transitions(
        self,
        current_state: bool,
        live_neighbors: int,
        expected: bool,
    ) -> None:
        """Test cell state transitions based on Game of Life rules.

        Given: A cell with a specific state and number of live neighbors
        When: Calculating its next state
        Then: Should follow Conway's Game of Life rules
        """
        current_array: Grid = create_test_grid([[current_state]])
        neighbors_array: IntArray = create_neighbor_counts([[live_neighbors]])

        result = calculate_next_state(current_array, neighbors_array)
        assert result[0, 0] == expected


@pytest.mark.patterns
class TestPatternEvolution:
    """Tests for pattern evolution over generations."""

    @pytest.mark.parametrize("pattern_data", TEST_PATTERNS.values())
    def test_pattern_evolution(self, pattern_data: dict) -> None:
        """Test evolution of known patterns.

        Given: A known pattern from test data
        When: Evolving the pattern for one generation
        Then: Should follow expected evolution rules
        """
        pattern = create_test_grid(pattern_data["pattern"])
        next_gen = next_generation(pattern, BoundaryCondition.FINITE)

        # Verify pattern behavior based on category
        category = pattern_data["category"]
        if category == "STILL_LIFE":
            # Still life patterns should not change
            assert np.array_equal(next_gen, pattern)
        elif category == "OSCILLATOR":
            # Oscillator patterns should change but return to original
            second_gen = next_generation(next_gen, BoundaryCondition.FINITE)
            assert not np.array_equal(next_gen, pattern)
            assert np.array_equal(second_gen, pattern)


@pytest.mark.boundaries
class TestBoundaryBehavior:
    """Tests for boundary condition effects."""

    @pytest.mark.parametrize(
        "boundary,grid,pos,expected_count",
        [
            # Finite boundary
            (
                BoundaryCondition.FINITE,
                create_test_grid([[True, True], [True, False]]),
                (0, 0),
                2,
            ),
            # Toroidal boundary
            (
                BoundaryCondition.TOROIDAL,
                create_test_grid([[True, False], [False, True]]),
                (0, 0),
                4,
            ),
            # Infinite boundary
            (
                BoundaryCondition.INFINITE,
                create_test_grid([[True, True], [True, True]]),
                (0, 0),
                3,
            ),
        ],
    )
    def test_boundary_neighbor_counting(
        self,
        boundary: BoundaryCondition,
        grid: Grid,
        pos: GridPosition,
        expected_count: int,
    ) -> None:
        """Test neighbor counting with different boundary conditions.

        Given: A grid with specific boundary condition
        When: Counting neighbors at a position
        Then: Should count correctly based on boundary rules
        """
        neighbors = get_neighbors(grid, pos, boundary)
        count = count_live_neighbors(grid, neighbors, boundary)
        assert count == expected_count

    def test_infinite_boundary_expansion(self) -> None:
        """Test grid expansion in INFINITE mode.

        Given: A grid with live cells at the boundary
        When: Calculating next generation with INFINITE boundary
        Then: Grid should expand to accommodate the pattern
        """
        # Arrange
        grid = create_test_grid(
            [
                [True, True, True],  # Glider at top edge
                [False, False, False],
                [False, False, False],
            ]
        )
        original_height, original_width = grid.shape

        # Act
        next_grid = next_generation(grid, BoundaryCondition.INFINITE)

        # Assert
        assert next_grid.shape[0] > grid.shape[0]  # Grid should expand vertically
        assert (
            next_grid.shape[1] >= grid.shape[1]
        )  # Grid width should be at least the same

    def test_infinite_boundary_no_expansion(self) -> None:
        """Test no expansion when not needed in INFINITE mode.

        Given: A grid with no live cells at boundaries
        When: Calculating next generation with INFINITE boundary
        Then: Grid dimensions should remain unchanged
        """
        # Arrange
        grid = create_test_grid(
            [
                [False, False, False],
                [False, True, False],  # Live cell not at boundary
                [False, False, False],
            ]
        )
        original_shape = grid.shape

        # Act
        next_grid = next_generation(grid, BoundaryCondition.INFINITE)

        # Assert
        assert next_grid.shape == original_shape  # No expansion needed
