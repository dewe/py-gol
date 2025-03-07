"""Tests for grid management."""

import dataclasses
from typing import Callable, Final, TypeAlias

import numpy as np
import pytest

from gol.grid import (
    BoundaryCondition,
    GridConfig,
    count_live_neighbors,
    create_grid,
    expand_grid,
    get_grid_section,
    get_neighbors,
    needs_boundary_expansion,
    resize_grid,
)
from gol.types import Grid, GridPosition, GridView, IntArray
from tests.conftest import create_test_grid  # Add import from conftest

# Type Aliases
NeighborValidator: TypeAlias = Callable[[IntArray], bool]
GridPattern: TypeAlias = list[list[bool]]

# Test Constants
STANDARD_GRID: Final[Grid] = np.array(
    [
        [True, True, True],
        [False, False, False],
        [False, False, False],
    ],
    dtype=np.bool_,
)

SMALL_GRID: Final[Grid] = np.array(
    [[True, True], [False, False]],
    dtype=np.bool_,
)

CORNER_POSITION: Final[GridPosition] = (0, 0)


# Helper Functions
def count_live_cells(grid: Grid) -> int:
    """Counts number of live cells in grid."""
    return int(np.sum(grid))


def assert_grid_matches_pattern(grid: Grid, pattern: GridPattern) -> None:
    """Asserts that grid matches expected pattern."""
    expected: Grid = create_test_grid(pattern)
    np.testing.assert_array_equal(grid, expected)


class TestGridCreation:
    """Tests for grid creation and resizing operations."""

    def test_grid_creation(self) -> None:
        """
        Given: A grid of 10x8 and density of 0.3
        When: Creating a new grid
        Then: Grid should be 10x8
        And: Approximately 30% of cells should be alive (with 20% margin)
        """
        config = GridConfig(width=10, height=8, density=0.3)
        grid: Grid = create_grid(config)

        # Check grid dimensions
        assert grid.shape == (8, 10)  # height, width

        # Check approximate density (with 20% margin to reduce flakiness)
        live_cells = count_live_cells(grid)
        total_cells = 80  # 10x8
        actual_density = live_cells / total_cells
        assert (
            0.1 <= actual_density <= 0.5
        ), f"Expected density between 10% and 50%, got {actual_density * 100:.1f}%"

    def test_grid_resizing_smaller(self) -> None:
        """
        Given: A grid with known pattern
        When: Resizing to smaller dimensions
        Then: Should preserve pattern within new bounds
        """
        # Arrange
        grid: Grid = STANDARD_GRID.copy()

        # Act
        new_grid: Grid = resize_grid(grid, new_width=2, new_height=2)

        # Assert
        assert new_grid.shape == (2, 2)
        assert new_grid[0][0] and new_grid[0][1]  # Top row preserved
        assert not new_grid[1][0] and not new_grid[1][1]  # Bottom row preserved

    def test_grid_resizing_larger(self) -> None:
        """
        Given: A grid with known pattern
        When: Resizing to larger dimensions
        Then: Should preserve original pattern and fill new cells with dead state
        """
        # Arrange
        grid: Grid = SMALL_GRID.copy()

        # Act
        new_grid: Grid = resize_grid(grid, new_width=3, new_height=3)

        # Assert
        assert new_grid.shape == (3, 3)
        assert new_grid[0][0] and new_grid[0][1]  # Original pattern preserved
        assert not new_grid[0][2]  # New cells dead
        assert not any(cell for cell in new_grid[2])  # New row dead


class TestBoundaryConditions:
    """Tests for different boundary condition behaviors."""

    @pytest.mark.parametrize(
        "boundary,grid,pos,expected_neighbors,expected_conditions",
        [
            # Test finite boundary
            (
                BoundaryCondition.FINITE,
                STANDARD_GRID,
                CORNER_POSITION,
                3,  # Expected number of neighbors
                lambda neighbors: all(  # All positions within grid
                    [
                        (0, 1) in zip(neighbors[0], neighbors[1]),
                        (1, 0) in zip(neighbors[0], neighbors[1]),
                        (1, 1) in zip(neighbors[0], neighbors[1]),
                    ]
                ),
            ),
            # Test toroidal boundary
            (
                BoundaryCondition.TOROIDAL,
                SMALL_GRID,
                CORNER_POSITION,
                8,  # Expected number of neighbors
                lambda neighbors: all(
                    [  # Check wrapping positions
                        (1, 1) in zip(neighbors[0], neighbors[1]),  # Bottom-right
                        (1, 0) in zip(neighbors[0], neighbors[1]),  # Right
                        (0, 1) in zip(neighbors[0], neighbors[1]),  # Bottom
                    ]
                ),
            ),
            # Test infinite boundary
            (
                BoundaryCondition.INFINITE,
                SMALL_GRID,
                CORNER_POSITION,
                8,  # Expected number of neighbors
                # Check positions outside grid boundaries
                lambda n: all(
                    [
                        (-1, -1) in zip(n[0], n[1]),
                        (-1, 0) in zip(n[0], n[1]),
                        (-1, 1) in zip(n[0], n[1]),
                    ]
                ),
            ),
        ],
    )
    def test_boundary_conditions(
        self,
        boundary: BoundaryCondition,
        grid: Grid,
        pos: GridPosition,
        expected_neighbors: int,
        expected_conditions: NeighborValidator,
    ) -> None:
        """Test neighbor calculation for different boundary conditions."""
        # Act
        neighbors: IntArray = get_neighbors(grid, pos, boundary)

        # Debug info
        print(f"\nTesting {boundary} boundary:")
        print(f"Position: {pos}")
        print("Neighbors:")
        for x, y in zip(neighbors[0], neighbors[1]):
            print(f"  ({x}, {y})")

        # Assert
        assert neighbors.shape[1] == expected_neighbors
        assert expected_conditions(neighbors)


class TestGridSections:
    """Tests for grid section operations."""

    SECTION_GRID: Final[Grid] = create_test_grid([[True, True], [False, False]])

    WRAP_GRID: Final[Grid] = create_test_grid([[True, False], [False, True]])

    def test_finite_section_handles_out_of_bounds(self) -> None:
        """
        Given: A grid with finite boundary
        When: Getting a section partially outside grid bounds
        Then: Should return section with dead cells for out-of-bounds positions
        """
        # Act
        section: GridView = get_grid_section(
            self.SECTION_GRID,
            (1, 1),  # Start inside
            (2, 2),  # End outside
            BoundaryCondition.FINITE,
        )

        # Assert
        assert section.shape == (2, 2)  # Requested height, width
        assert not section[0][1]  # Outside position is dead
        assert not section[1][0]  # Outside position is dead
        assert not section[1][1]  # Outside position is dead

    def test_toroidal_section_wraps_around_edges(self) -> None:
        """
        Given: A grid with toroidal boundary
        When: Getting a section across grid edge
        Then: Should wrap around to opposite edge
        """
        # Act
        section: GridView = get_grid_section(
            self.WRAP_GRID,
            (1, 1),  # Bottom-right
            (2, 2),  # Wraps around
            BoundaryCondition.TOROIDAL,
        )

        # Assert
        assert section.shape == (2, 2)
        assert section[0][0]  # Bottom-right cell is alive
        assert not section[0][1]  # Wrapped top-right is dead
        assert not section[1][0]  # Wrapped bottom-left is dead
        assert section[1][1]  # Wrapped top-left is alive


class TestNeighborCounting:
    """Tests for neighbor counting operations."""

    def test_count_neighbors_infinite_boundary(self) -> None:
        """
        Given: A grid with infinite boundary
        When: Counting neighbors including positions outside grid
        Then: Should only count live cells within actual grid
        """
        # Arrange
        grid: Grid = SMALL_GRID.copy()
        positions: IntArray = np.array(
            [
                [-1, 0, 1],  # x coordinates
                [-1, 0, 0],  # y coordinates
            ],
            dtype=np.int_,
        )

        # Act
        count = count_live_neighbors(grid, positions, BoundaryCondition.INFINITE)

        # Assert
        assert count == 2  # Only cells within grid boundaries


def test_grid_config_immutability() -> None:
    """Test that GridConfig is immutable."""
    config = GridConfig(width=10, height=10)

    # Verify that attempting to modify attributes raises FrozenInstanceError
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.width = 20  # type: ignore

    # Verify original values remain unchanged
    assert config.width == 10
    assert config.height == 10


def test_grid_config_dimension_updates() -> None:
    """Test that dimension updates return new instances."""
    config = GridConfig(width=10, height=10)

    # Test dimension update
    new_config = config.with_dimensions(20, 30)
    assert new_config is not config
    assert new_config.width == 20
    assert new_config.height == 30
    assert config.width == 10  # Original unchanged
    assert config.height == 10  # Original unchanged

    # Test invalid dimensions
    with pytest.raises(ValueError):
        config.with_dimensions(0, 10)
    with pytest.raises(ValueError):
        config.with_dimensions(10, 0)


def test_grid_config_density_updates() -> None:
    """Test that density updates return new instances."""
    config = GridConfig(width=10, height=10, density=0.3)

    # Test density update
    new_config = config.with_density(0.5)
    assert new_config is not config
    assert new_config.density == 0.5
    assert config.density == 0.3  # Original unchanged

    # Test invalid density
    with pytest.raises(ValueError):
        config.with_density(-0.1)
    with pytest.raises(ValueError):
        config.with_density(1.1)


def test_grid_config_boundary_updates() -> None:
    """Test that boundary updates return new instances."""
    config = GridConfig(width=10, height=10)
    assert config.boundary == BoundaryCondition.FINITE

    # Test boundary update
    new_config = config.with_boundary(BoundaryCondition.TOROIDAL)
    assert new_config is not config
    assert new_config.boundary == BoundaryCondition.TOROIDAL
    assert config.boundary == BoundaryCondition.FINITE  # Original unchanged


class TestInfiniteBoundary:
    """Tests for infinite boundary behavior."""

    def test_detect_boundary_expansion_needed(self) -> None:
        """Test detection of when grid expansion is needed."""
        # Arrange
        grid = create_test_grid(
            [
                [False, True, False],  # Live cell at top edge
                [False, False, False],
                [False, False, False],
            ]
        )

        # Act
        needs_expansion = needs_boundary_expansion(grid)

        # Assert
        assert needs_expansion == (True, False, False, False)  # (up, right, down, left)

    def test_expand_grid_up(self) -> None:
        """Test grid expansion upward."""
        # Arrange
        grid = create_test_grid(
            [
                [True, False, False],  # Live cell at top edge
                [False, False, False],
            ]
        )
        original_height, original_width = grid.shape

        # Act
        expanded = expand_grid(grid, expand_up=True)

        # Assert
        assert expanded.shape == (original_height + 1, original_width)
        assert not expanded[0].any()  # New row is empty
        assert np.array_equal(expanded[1:], grid)  # Original content preserved

    def test_expand_grid_multiple_directions(self) -> None:
        """Test grid expansion in multiple directions."""
        # Arrange
        grid = create_test_grid(
            [
                [True, False],  # Top edge
                [False, True],  # Right edge
            ]
        )
        original_height, original_width = grid.shape

        # Act
        expanded = expand_grid(grid, expand_up=True, expand_right=True)

        # Assert
        assert expanded.shape == (original_height + 1, original_width + 1)
        assert not expanded[0, 1:].any()  # New top row is empty (except copied cell)
        assert not expanded[1:, -1].any()  # New right column is empty
        assert np.array_equal(expanded[1:, :-1], grid)  # Original content preserved

    def test_no_expansion_needed(self) -> None:
        """Test when no expansion is needed."""
        # Arrange
        grid = create_test_grid(
            [
                [False, False, False],
                [False, True, False],  # Live cell not at edge
                [False, False, False],
            ]
        )

        # Act
        needs_expansion = needs_boundary_expansion(grid)

        # Assert
        assert needs_expansion == (False, False, False, False)
