"""Grid management for Game of Life."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import NewType, Tuple

import numpy as np
from numpy.typing import NDArray

# Type definitions
Position = NewType("Position", tuple[int, int])
# Grid now stores tuples of (is_alive: bool, age: int)
Grid = NewType("Grid", list[list[Tuple[bool, int]]])


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
    density: float = 0.15  # Lower default density for better patterns
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
    grid_list = [
        [(bool(cell), 1 if bool(cell) else 0) for cell in row.tolist()]
        for row in random_grid
    ]
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
    new_grid = [[(False, 0)] * new_width for _ in range(new_height)]

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
    """Get valid neighbor positions using vectorized operations.

    Args:
        grid: Current grid state
        pos: Position to get neighbors for
        boundary: Boundary condition to apply

    Returns:
        List of valid neighbor positions
    """
    x, y = pos
    width = len(grid[0])
    height = len(grid)

    # Generate all possible neighbor offsets using numpy
    dx = np.array([-1, -1, -1, 0, 0, 1, 1, 1])
    dy = np.array([-1, 0, 1, -1, 1, -1, 0, 1])

    # Calculate new positions
    new_x = x + dx
    new_y = y + dy

    match boundary:
        case BoundaryCondition.TOROIDAL:
            # Vectorized modulo operation for wrapping
            new_x = new_x % width
            new_y = new_y % height
            return [Position((int(nx), int(ny))) for nx, ny in zip(new_x, new_y)]

        case BoundaryCondition.INFINITE:
            # All positions are valid in infinite grid
            return [Position((int(nx), int(ny))) for nx, ny in zip(new_x, new_y)]

        case _:  # FINITE
            # Vectorized bounds checking
            valid_mask = (
                (new_x >= 0) & (new_x < width) & (new_y >= 0) & (new_y < height)
            )
            valid_x = new_x[valid_mask]
            valid_y = new_y[valid_mask]
            return [Position((int(nx), int(ny))) for nx, ny in zip(valid_x, valid_y)]


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

    # Convert grid to numpy array for faster access - extract just alive status
    grid_array = np.array([[cell[0] for cell in row] for row in grid])
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
                        row.append((False, 0))
                case _:  # FINITE
                    # Return dead cells for positions outside grid
                    if 0 <= y < height and 0 <= x < width:
                        row.append(grid[y][x])
                    else:
                        row.append((False, 0))
        section.append(row)

    return Grid(section)
