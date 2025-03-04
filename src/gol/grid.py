"""Grid management for Game of Life."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import NewType

import numpy as np
from numpy.typing import NDArray

# Type definitions
Position = NewType("Position", tuple[int, int])
Grid = NewType("Grid", list[list[bool]])  # Simplified to just booleans


class BoundaryCondition(Enum):
    """Available boundary conditions for the grid."""

    FINITE = auto()  # Cells outside grid are dead
    TOROIDAL = auto()  # Grid wraps around edges
    INFINITE = auto()  # Grid extends infinitely


@dataclass(frozen=True)
class GridConfig:
    """Grid configuration parameters."""

    width: int
    height: int
    density: float = 0.3  # Default density matching CLI and docs
    boundary: BoundaryCondition = BoundaryCondition.FINITE


def create_grid(config: GridConfig) -> Grid:
    """Creates initial grid with random cell distribution.

    Args:
        config: Grid configuration parameters

    Returns:
        A new Grid with random live cells based on density
    """
    # Use numpy's optimized random generation
    rng = np.random.default_rng()
    random_grid: NDArray[np.bool_] = (
        rng.random((config.height, config.width)) < config.density
    )
    # Convert numpy array to list[list[bool]] with explicit casting
    grid_list = [[bool(cell) for cell in row.tolist()] for row in random_grid]
    return Grid(grid_list)


def resize_grid(grid: Grid, new_width: int, new_height: int) -> Grid:
    """Pure function to resize grid while preserving pattern positions.

    Args:
        grid: Current grid state
        new_width: New grid width
        new_height: New grid height

    Returns:
        Resized grid with preserved patterns
    """
    old_height = len(grid)
    old_width = len(grid[0])

    # Create empty grid of new size
    new_grid = [[False] * new_width for _ in range(new_height)]

    # Calculate dimensions to copy
    copy_height = min(old_height, new_height)
    copy_width = min(old_width, new_width)

    # Copy existing cells to new grid
    for y in range(copy_height):
        for x in range(copy_width):
            new_grid[y][x] = grid[y][x]

    return Grid(new_grid)


def get_neighbors(
    grid: Grid, pos: Position, boundary: BoundaryCondition
) -> list[Position]:
    """Get valid neighbor positions based on boundary condition.

    Args:
        grid: The game grid
        pos: Position to get neighbors for
        boundary: Boundary condition to apply

    Returns:
        List of valid neighbor positions
    """
    height = len(grid)
    width = len(grid[0])
    x, y = pos

    if boundary == BoundaryCondition.FINITE:
        return [
            Position((new_x, new_y))
            for new_x in range(max(0, x - 1), min(width, x + 2))
            for new_y in range(max(0, y - 1), min(height, y + 2))
            if (new_x, new_y) != (x, y)
        ]
    elif boundary == BoundaryCondition.TOROIDAL:
        # For toroidal boundaries, wrap around edges
        neighbors = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                # Calculate wrapped positions
                new_x = (x + dx) % width
                new_y = (y + dy) % height
                neighbors.append(Position((new_x, new_y)))
        return neighbors
    else:  # INFINITE
        # For infinite boundaries, return all 8 neighbors regardless of grid bounds
        neighbors = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                neighbors.append(Position((x + dx, y + dy)))
        return neighbors


def count_live_neighbors(
    grid: Grid, positions: list[Position], boundary: BoundaryCondition
) -> int:
    """Count live neighbors using numpy for better performance.

    Args:
        grid: Current grid state
        positions: List of positions to check
        boundary: Boundary condition to apply

    Returns:
        Count of live cells in given positions
    """
    if not positions:
        return 0

    width = len(grid[0])
    height = len(grid)

    # Convert positions to numpy arrays for vectorized access
    pos_array = np.array([(pos[0], pos[1]) for pos in positions])
    x_coords = pos_array[:, 0]
    y_coords = pos_array[:, 1]

    match boundary:
        case BoundaryCondition.TOROIDAL:
            # Apply wrapping
            x_coords = x_coords % width
            y_coords = y_coords % height

        case BoundaryCondition.INFINITE:
            # For positions outside grid, create virtual cells
            mask = (
                (x_coords >= 0)
                & (x_coords < width)
                & (y_coords >= 0)
                & (y_coords < height)
            )
            # Count only cells within actual grid
            x_coords = x_coords[mask]
            y_coords = y_coords[mask]

        case _:  # FINITE
            # Filter out invalid positions
            mask = (
                (x_coords >= 0)
                & (x_coords < width)
                & (y_coords >= 0)
                & (y_coords < height)
            )
            x_coords = x_coords[mask]
            y_coords = y_coords[mask]

    if len(x_coords) == 0:
        return 0

    # Convert grid to numpy array for faster access
    grid_array = np.array(grid)
    return int(np.sum(grid_array[y_coords, x_coords]))


def get_grid_section(
    grid: Grid, top_left: Position, bottom_right: Position, boundary: BoundaryCondition
) -> Grid:
    """Pure function to get a section of the grid.

    Args:
        grid: Current grid state
        top_left: Top-left position of section
        bottom_right: Bottom-right position of section
        boundary: Boundary condition to apply

    Returns:
        Grid section with applied boundary conditions
    """
    x1, y1 = top_left
    x2, y2 = bottom_right
    width = len(grid[0])
    height = len(grid)

    section = []
    for y in range(y1, y2 + 1):
        row = []
        for x in range(x1, x2 + 1):
            match boundary:
                case BoundaryCondition.TOROIDAL:
                    # Wrap coordinates
                    grid_y = y % height
                    grid_x = x % width
                    row.append(grid[grid_y][grid_x])
                case BoundaryCondition.INFINITE:
                    # Return dead cells for positions outside grid
                    if 0 <= y < height and 0 <= x < width:
                        row.append(grid[y][x])
                    else:
                        row.append(False)
                case _:  # FINITE
                    # Return dead cells for positions outside grid
                    if 0 <= y < height and 0 <= x < width:
                        row.append(grid[y][x])
                    else:
                        row.append(False)
        section.append(row)

    return Grid(section)
