"""Grid management for Game of Life."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import cast

import numpy as np

from .types import (
    BoolArray,
    ExpansionFlags,
    Grid,
    GridDimensions,
    GridPadding,
    GridPosition,
    GridShape,
    GridSlice,
    GridView,
    IntArray,
    ViewportOffset,
)


class BoundaryCondition(Enum):
    """Available boundary conditions for grid evolution."""

    FINITE = auto()  # Dead cells beyond edges
    TOROIDAL = auto()  # Wraps around edges
    INFINITE = auto()  # Extends infinitely


@dataclass(frozen=True)
class GridConfig:
    """Grid configuration with validation.

    This class is immutable. All modifications return new instances.
    """

    width: int
    height: int
    density: float = 0.3
    boundary: BoundaryCondition = BoundaryCondition.FINITE

    @property
    def dimensions(self) -> GridDimensions:
        """Get grid dimensions as (width, height)."""
        return (self.width, self.height)

    def __post_init__(self) -> None:
        """Validate grid dimensions and density."""
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Grid dimensions must be positive")
        if not 0 <= self.density <= 1:
            raise ValueError("Density must be between 0 and 1")

    def with_dimensions(self, width: int, height: int) -> "GridConfig":
        """Return new config with updated dimensions.

        Args:
            width: New grid width
            height: New grid height

        Returns:
            New GridConfig instance with updated dimensions

        Raises:
            ValueError: If dimensions are invalid
        """
        from dataclasses import replace

        return replace(self, width=width, height=height)

    def with_density(self, density: float) -> "GridConfig":
        """Return new config with updated density.

        Args:
            density: New grid density (0.0 to 1.0)

        Returns:
            New GridConfig instance with updated density

        Raises:
            ValueError: If density is invalid
        """
        from dataclasses import replace

        return replace(self, density=density)

    def with_boundary(self, boundary: BoundaryCondition) -> "GridConfig":
        """Return new config with updated boundary condition.

        Args:
            boundary: New boundary condition

        Returns:
            New GridConfig instance with updated boundary condition
        """
        from dataclasses import replace

        return replace(self, boundary=boundary)


def create_grid(config: GridConfig) -> Grid:
    """Creates initial grid with random cell distribution.

    Uses numpy's random generator for efficient array initialization
    based on the configured density.
    """
    rng = np.random.default_rng()
    array: BoolArray = rng.random((config.height, config.width)) < config.density
    return cast(Grid, array)


def resize_grid(grid: Grid, new_width: int, new_height: int) -> Grid:
    """Pure function to resize grid while preserving pattern positions.

    Args:
        grid: Current grid state
        new_width: New grid width
        new_height: New grid height

    Returns:
        Resized grid with preserved patterns
    """
    # Create the padding configuration
    pad_width: GridPadding = (
        (0, max(0, new_height - grid.shape[0])),
        (0, max(0, new_width - grid.shape[1])),
    )

    # Perform padding and slicing
    resized: BoolArray = np.pad(
        grid, pad_width, mode="constant", constant_values=False
    )[:new_height, :new_width]

    return cast(Grid, resized)


def get_neighbors(
    grid: Grid, pos: GridPosition, boundary: BoundaryCondition
) -> IntArray:
    """Get valid neighbor positions as a 2xN array of coordinates."""
    height, width = cast(GridShape, grid.shape)
    x, y = pos

    # Create all neighbor offsets as a 2x8 array with explicit dtype
    offsets = np.array(
        [[-1, -1, -1, 0, 0, 1, 1, 1], [-1, 0, 1, -1, 1, -1, 0, 1]], dtype=np.int_
    )

    # Add position to get neighbor coordinates
    neighbors = np.array([[x], [y]], dtype=np.int_) + offsets

    match boundary:
        case BoundaryCondition.FINITE:
            # Create mask for valid coordinates
            valid = (
                (neighbors[0] >= 0)
                & (neighbors[0] < width)
                & (neighbors[1] >= 0)
                & (neighbors[1] < height)
            )
            return cast(IntArray, neighbors[:, valid])
        case BoundaryCondition.TOROIDAL:
            # Apply modulo for wrapping
            neighbors[0] %= width
            neighbors[1] %= height
            return cast(IntArray, neighbors)
        case BoundaryCondition.INFINITE:
            # Return all neighbors, validity checked during counting
            return cast(IntArray, neighbors)


def count_live_neighbors(
    grid: Grid, positions: IntArray, boundary: BoundaryCondition
) -> int:
    """Count live neighbors using vectorized operations."""
    if positions.size == 0:
        return 0

    height, width = cast(GridShape, grid.shape)
    x_coords, y_coords = positions

    match boundary:
        case BoundaryCondition.TOROIDAL:
            x_coords %= width
            y_coords %= height
            return int(np.sum(grid[y_coords, x_coords]))
        case BoundaryCondition.INFINITE | BoundaryCondition.FINITE:
            # For both FINITE and INFINITE, cells outside grid are dead
            mask = (
                (x_coords >= 0)
                & (x_coords < width)
                & (y_coords >= 0)
                & (y_coords < height)
            )
            return int(np.sum(grid[y_coords[mask], x_coords[mask]]))


def get_grid_section(
    grid: Grid,
    top_left: GridPosition,
    bottom_right: GridPosition,
    boundary: BoundaryCondition,
) -> GridView:
    """Get a section of the grid with boundary condition handling."""
    x1, y1 = top_left
    x2, y2 = bottom_right

    if boundary == BoundaryCondition.TOROIDAL:
        height, width = cast(GridShape, grid.shape)
        y_indices = np.arange(y1, y2 + 1) % height
        x_indices = np.arange(x1, x2 + 1) % width
        return cast(GridView, grid[np.ix_(y_indices, x_indices)])
    else:  # FINITE or INFINITE
        section = np.zeros((y2 - y1 + 1, x2 - x1 + 1), dtype=np.bool_)

        # Calculate valid grid coordinates
        valid_y: GridSlice = slice(max(0, y1), min(grid.shape[0], y2 + 1))
        valid_x: GridSlice = slice(max(0, x1), min(grid.shape[1], x2 + 1))

        # Calculate corresponding section coordinates
        section_y: GridSlice = slice(
            max(0, -y1), min(section.shape[0], grid.shape[0] - y1)
        )
        section_x: GridSlice = slice(
            max(0, -x1), min(section.shape[1], grid.shape[1] - x1)
        )

        # Copy valid grid region to section
        section[section_y, section_x] = grid[valid_y, valid_x]
        return cast(GridView, section)


def needs_boundary_expansion(grid: Grid) -> ExpansionFlags:
    """Check if grid needs to expand in any direction.

    Returns:
        Tuple of booleans (expand_up, expand_right, expand_down, expand_left)
        indicating which directions need expansion.
    """

    # Check each edge for live cells and convert to Python bool
    expand_up = bool(np.any(grid[0]))  # Top row
    expand_right = bool(np.any(grid[:, -1]))  # Rightmost column
    expand_down = bool(np.any(grid[-1]))  # Bottom row
    expand_left = bool(np.any(grid[:, 0]))  # Leftmost column

    return (expand_up, expand_right, expand_down, expand_left)


def expand_grid(
    grid: Grid,
    expand_up: bool = False,
    expand_right: bool = False,
    expand_down: bool = False,
    expand_left: bool = False,
) -> tuple[Grid, ViewportOffset]:
    """Expand grid in specified directions by one cell.

    Args:
        grid: Current grid state
        expand_up: Add row at top
        expand_right: Add column at right
        expand_down: Add row at bottom
        expand_left: Add column at left

    Returns:
        Tuple of:
        - New grid with expanded dimensions. New rows/columns are always dead cells.
          Original grid content is preserved in its new position.
        - Viewport offset adjustments (dx, dy) needed to maintain view position
    """
    height, width = cast(GridShape, grid.shape)
    new_height = height + (1 if expand_up else 0) + (1 if expand_down else 0)
    new_width = width + (1 if expand_left else 0) + (1 if expand_right else 0)

    # Create new grid with expanded dimensions (all cells dead)
    new_grid = np.zeros((new_height, new_width), dtype=np.bool_)

    # Calculate offsets for original grid placement
    y_offset = 1 if expand_up else 0
    x_offset = 1 if expand_left else 0

    # Copy original grid content to new position
    new_grid[y_offset : y_offset + height, x_offset : x_offset + width] = grid

    # Calculate viewport offset adjustments needed
    dx = 1 if expand_left else 0
    dy = 1 if expand_up else 0

    return cast(Grid, new_grid), (dx, dy)
