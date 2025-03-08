"""Tests for grid management."""

import dataclasses
from typing import Callable, Final, TypeAlias

import numpy as np
import pytest

from gol.grid import (
    BoundaryCondition,
    Grid,
    GridConfig,
    GridPosition,
    count_live_neighbors,
    create_grid,
    expand_grid,
    get_grid_section,
    get_neighbors,
    needs_boundary_expansion,
    resize_grid,
)
from gol.types import GridView, IntArray
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

    def test_infinite_section_handles_out_of_bounds(self) -> None:
        """
        Given: A grid with infinite boundary
        When: Getting a section partially outside grid bounds
        Then: Should return section with dead cells for out-of-bounds positions
        """
        # Arrange
        grid = create_test_grid([[True, True], [False, True]])

        # Act
        section: GridView = get_grid_section(
            grid,
            (-1, -1),  # Start outside
            (1, 1),  # End inside
            BoundaryCondition.INFINITE,
        )

        # Assert
        assert section.shape == (3, 3)  # Requested height, width
        assert not section[0][0]  # Outside position is dead
        assert not section[0][1]  # Outside position is dead
        assert not section[0][2]  # Outside position is dead
        assert not section[1][0]  # Outside position is dead
        assert section[1][1]  # Inside position matches grid[0,0]
        assert section[1][2]  # Inside position matches grid[0,1]
        assert not section[2][0]  # Outside position is dead
        assert not section[2][1]  # Inside position matches grid[1,0]
        assert section[2][2]  # Inside position matches grid[1,1]


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

    def test_infinite_boundary_expansion_sequence(self) -> None:
        """
        Given: A grid with live cells at edges (not corners)
        When: Checking expansion needs
        Then: Should identify all directions needing expansion
        And: Should expand grid correctly in sequence
        """
        grid = create_test_grid(
            [
                [False, True, False],  # Top edge (middle)
                [True, False, True],  # Left and right edges
                [False, True, False],  # Bottom edge (middle)
            ]
        )

        # Check expansion needs
        expand_up, expand_right, expand_down, expand_left = needs_boundary_expansion(
            grid
        )
        assert expand_up and expand_down  # Should expand vertically
        assert expand_right and expand_left  # Should expand horizontally

        # Expand grid
        expanded = expand_grid(
            grid, expand_up=True, expand_right=True, expand_down=True, expand_left=True
        )

        # Verify dimensions
        assert expanded.shape == (5, 5)  # Added rows/columns on all sides

        # Verify new rows/columns are dead
        assert not expanded[0].any()  # New top row
        assert not expanded[-1].any()  # New bottom row
        assert not expanded[:, 0].any()  # New left column
        assert not expanded[:, -1].any()  # New right column

        # Verify original pattern preserved in center
        assert_grid_matches_pattern(
            expanded[1:4, 1:4],
            [[False, True, False], [True, False, True], [False, True, False]],
        )


def test_infinite_boundary_expansion() -> None:
    """Test grid expansion with INFINITE boundary condition."""
    config = GridConfig(
        width=5,
        height=5,
        boundary=BoundaryCondition.INFINITE,
        density=0.0,  # Start with all dead cells
    )
    grid = create_grid(config)

    # Place single live cell at top edge
    grid[0, 2] = True

    # Check expansion needed
    expand_up, expand_right, expand_down, expand_left = needs_boundary_expansion(grid)
    assert expand_up  # Should expand up due to live cell at top
    assert not any(
        [expand_right, expand_down, expand_left]
    )  # No expansion needed in other directions

    # Expand grid
    expanded_grid = expand_grid(grid, expand_up=True)
    assert expanded_grid.shape == (6, 5)  # One row added at top
    assert expanded_grid[1, 2]  # Original live cell now at row 1


def test_infinite_boundary_no_expansion() -> None:
    """Test no expansion needed when live cells not at boundary."""
    config = GridConfig(
        width=5,
        height=5,
        boundary=BoundaryCondition.INFINITE,
        density=0.0,  # Start with all dead cells
    )
    grid = create_grid(config)

    # Place single live cell in center
    grid[2, 2] = True

    # Check no expansion needed
    expand_up, expand_right, expand_down, expand_left = needs_boundary_expansion(grid)
    assert not any([expand_up, expand_right, expand_down, expand_left])


def test_infinite_boundary_corner_expansion() -> None:
    """Test corner expansion with INFINITE boundary condition."""
    config = GridConfig(
        width=3,
        height=3,
        boundary=BoundaryCondition.INFINITE,
        density=0.0,  # Start with all dead cells
    )
    grid = create_grid(config)

    # Place live cell at top-right corner
    grid[0, 2] = True

    # Check expansion needed in two directions
    expand_up, expand_right, expand_down, expand_left = needs_boundary_expansion(grid)
    assert expand_up and expand_right  # Should expand up and right due to corner cell
    assert (
        not expand_down and not expand_left
    )  # No expansion needed in other directions

    # Expand grid in both directions
    expanded_grid = expand_grid(grid, expand_up=True, expand_right=True)
    assert expanded_grid.shape == (4, 4)  # Added row at top and column at right
    assert expanded_grid[1, 2]  # Original live cell now at row 1


def test_needs_boundary_expansion_corner() -> None:
    """Test boundary expansion when corner cell is alive."""
    grid = np.array(
        [
            [True, False, False],  # Corner cell alive
            [False, False, False],
            [False, False, False],
        ],
        dtype=np.bool_,
    )

    expand_up, expand_right, expand_down, expand_left = needs_boundary_expansion(grid)
    assert expand_up  # Should expand up due to top row
    assert not expand_right
    assert not expand_down
    assert expand_left  # Should expand left due to first column

    grid = np.array(
        [
            [False, False, True],  # Top-right corner
            [False, False, False],
            [False, False, False],
        ],
        dtype=np.bool_,
    )

    expand_up, expand_right, expand_down, expand_left = needs_boundary_expansion(grid)
    assert expand_up  # Should expand up
    assert expand_right  # Should expand right
    assert not expand_down
    assert not expand_left


def test_needs_boundary_expansion_no_expansion() -> None:
    """Test no expansion needed when live cells not at boundary."""
    # Test center cell
    grid = np.array(
        [
            [False, False, False],
            [False, True, False],  # Live cell in center
            [False, False, False],
        ],
        dtype=np.bool_,
    )

    expand_up, expand_right, expand_down, expand_left = needs_boundary_expansion(grid)
    assert not any([expand_up, expand_right, expand_down, expand_left])

    # Test cells near but not at boundary
    grid = np.array(
        [
            [False, False, False, False],
            [False, True, True, False],  # Live cells one cell away from boundary
            [False, True, False, False],
            [False, False, False, False],
        ],
        dtype=np.bool_,
    )

    expand_up, expand_right, expand_down, expand_left = needs_boundary_expansion(grid)
    assert not any([expand_up, expand_right, expand_down, expand_left])


def test_infinite_boundary_pattern_preservation() -> None:
    """Test pattern preservation during grid expansion.

    Given: A grid with a glider pattern at the edge
    When: Grid expands due to INFINITE boundary
    Then: Pattern should be preserved exactly
    """
    # Arrange - Create a glider pattern at the top edge
    grid = create_test_grid(
        [
            [True, True, True],  # Glider at top
            [False, False, True],
            [False, True, False],
        ]
    )

    # Act - Expand grid upward
    expanded = expand_grid(grid, expand_up=True)

    # Assert - Original pattern should be preserved exactly
    assert expanded.shape == (4, 3)  # Added one row at top
    assert not expanded[0].any()  # New top row is dead
    assert np.array_equal(expanded[1:], grid)  # Original pattern preserved exactly


def test_infinite_boundary_center_maintenance() -> None:
    """Test that grid center position is maintained during expansion.

    Given: A grid with a pattern in the center
    When: Grid expands in all directions
    Then: Pattern should maintain its relative center position
    """
    # Arrange - Create a pattern in the center
    grid = create_test_grid(
        [
            [False, True, False],  # Top edge
            [True, True, True],  # Center pattern
            [False, True, False],  # Bottom edge
        ]
    )

    # Act - Expand in all directions
    expanded = expand_grid(
        grid, expand_up=True, expand_right=True, expand_down=True, expand_left=True
    )

    # Assert
    assert expanded.shape == (5, 5)  # Added rows/columns on all sides
    # Check that pattern maintained its relative center position
    assert np.array_equal(expanded[1:4, 1:4], grid)


def test_infinite_boundary_multiple_expansions() -> None:
    """Test multiple sequential expansions.

    Given: A grid requiring multiple expansions
    When: Processing multiple generations with INFINITE boundary
    Then: Should expand when needed and maintain expanded dimensions
    """
    from gol.life import next_generation

    # Arrange - Create a glider pattern that will move to corner
    grid = create_test_grid(
        [
            [True, True, True],  # Glider at top
            [False, False, True],
            [False, True, False],
        ]
    )
    original_shape = grid.shape

    # Act - Process multiple generations
    gen1 = next_generation(grid, BoundaryCondition.INFINITE)
    gen2 = next_generation(gen1, BoundaryCondition.INFINITE)

    # Assert
    # First generation should expand up due to top pattern
    assert gen1.shape[0] > original_shape[0]
    # Second generation should expand further if needed
    assert gen2.shape[0] >= gen1.shape[0]
    assert gen2.shape[1] >= gen1.shape[1]
    # Pattern should evolve correctly
    assert np.sum(gen2) == 5  # Glider maintains 5 live cells


def test_infinite_boundary_large_grid_performance() -> None:
    """Test performance considerations for large grid expansion.

    Given: A large grid with patterns at edges
    When: Expanding the grid
    Then: Should handle expansion efficiently
    """
    import time

    # Arrange - Create a large grid (100x100) with patterns at edges
    config = GridConfig(width=100, height=100, density=0.0)
    grid = create_grid(config)
    grid[0, :] = True  # Top edge all alive

    # Act - Measure expansion time
    start_time = time.perf_counter()
    expanded = expand_grid(grid, expand_up=True)
    end_time = time.perf_counter()

    # Assert
    expansion_time = end_time - start_time
    assert expansion_time < 0.1  # Should complete quickly
    assert expanded.shape == (101, 100)  # Verify expansion


def test_infinite_boundary_no_shrinking() -> None:
    """Test that grid does not shrink after expansion.

    Given: A grid that has been expanded
    When: Live cells move away from boundaries
    Then: Grid dimensions should remain unchanged
    """
    from gol.life import next_generation

    # Arrange - Create a grid with live cells at boundaries
    grid = create_test_grid(
        [
            [True, False, False],  # Top edge
            [False, False, False],
            [False, False, False],
        ]
    )

    # First expand the grid
    expanded = expand_grid(grid, expand_up=True)
    expanded_shape = expanded.shape

    # Move live cells away from boundaries
    expanded[1:] = False  # Clear all cells
    expanded[2, 1] = True  # Place cell in center

    # Act - Process next generation
    next_gen = next_generation(expanded, BoundaryCondition.INFINITE)

    # Assert - Grid should maintain expanded dimensions
    assert next_gen.shape == expanded_shape
    assert next_gen.shape > grid.shape  # Still larger than original


def test_infinite_boundary_viewport_behavior() -> None:
    """Test viewport behavior during grid expansion.

    Given: A grid with viewport and live cells at boundaries
    When: Grid expands due to INFINITE boundary
    Then: Should maintain viewport constraints:
        1. Viewport size should not change during expansion
        2. Viewport position should not change during expansion
        3. Same grid cells should be visible in viewport after expansion
        4. Expansion happens outside of the viewport with dead cells
    """
    from gol.state import RendererState, ViewportState

    # Arrange - Create a grid with live cells at boundaries
    grid = create_test_grid(
        [
            [True, False, True],  # Top edge
            [False, True, False],  # Center
            [True, False, True],  # Bottom edge
        ]
    )

    # Create viewport showing center of grid
    viewport = ViewportState(dimensions=(2, 2), offset_x=1, offset_y=1)
    state = RendererState().with_viewport(viewport)

    # Record viewport state and visible cells before expansion
    initial_dimensions = state.viewport.dimensions
    initial_offset = state.viewport.offset
    visible_before = grid[1:3, 1:3]  # Center 2x2 region

    # Act - Expand grid in all directions
    expanded = expand_grid(
        grid, expand_up=True, expand_right=True, expand_down=True, expand_left=True
    )

    # Assert - Viewport dimensions and position unchanged
    assert (
        state.viewport.dimensions == initial_dimensions
    ), "Viewport size changed during expansion"
    assert (
        state.viewport.offset == initial_offset
    ), "Viewport position changed during expansion"

    # Assert - Same cells visible after expansion (accounting for expansion offset)
    visible_after = expanded[2:4, 2:4]  # Center shifted by 1 due to expansion
    assert np.array_equal(
        visible_before, visible_after
    ), "Visible cells changed during expansion"

    # Assert - New rows/columns are dead cells
    assert not np.any(expanded[0]), "Top row should be dead cells"
    assert not np.any(expanded[-1]), "Bottom row should be dead cells"
    assert not np.any(expanded[:, 0]), "Left column should be dead cells"
    assert not np.any(expanded[:, -1]), "Right column should be dead cells"
