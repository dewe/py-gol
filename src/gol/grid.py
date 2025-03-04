"""Grid management for Game of Life."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import cast

import numpy as np

from .types import BoolArray, Grid, GridPosition, IntArray


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
    pad_width = (
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
    height, width = grid.shape
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
        case _:  # INFINITE
            return cast(IntArray, neighbors)


def count_live_neighbors(
    grid: Grid, positions: IntArray, boundary: BoundaryCondition
) -> int:
    """Count live neighbors using vectorized operations.

    Handles different boundary conditions efficiently using NumPy operations
    instead of iterating over positions.
    """
    if positions.size == 0:
        return 0

    height, width = grid.shape
    x_coords, y_coords = positions

    match boundary:
        case BoundaryCondition.TOROIDAL:
            x_coords %= width
            y_coords %= height
            return int(np.sum(grid[y_coords, x_coords]))
        case _:  # FINITE or INFINITE
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
) -> Grid:
    """Get a section of the grid with boundary condition handling.

    For toroidal boundaries, wraps coordinates using modulo.
    For finite/infinite boundaries, pads with dead cells beyond edges.
    """
    x1, y1 = top_left
    x2, y2 = bottom_right

    if boundary == BoundaryCondition.TOROIDAL:
        height, width = grid.shape
        y_indices = np.arange(y1, y2 + 1) % height
        x_indices = np.arange(x1, x2 + 1) % width
        return cast(Grid, grid[np.ix_(y_indices, x_indices)])
    else:
        section = np.zeros((y2 - y1 + 1, x2 - x1 + 1), dtype=np.bool_)

        valid_y = slice(max(0, y1), min(grid.shape[0], y2 + 1))
        valid_x = slice(max(0, x1), min(grid.shape[1], x2 + 1))

        section_y = slice(max(0, -y1), min(section.shape[0], grid.shape[0] - y1))
        section_x = slice(max(0, -x1), min(section.shape[1], grid.shape[1] - x1))

        section[section_y, section_x] = grid[valid_y, valid_x]
        return cast(Grid, section)
