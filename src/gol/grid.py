"""Grid management for Game of Life."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import NewType

import numpy as np
from numpy.typing import NDArray

# More descriptive type aliases
Coordinate = tuple[int, int]
Position = NewType("Position", Coordinate)
CellGrid = list[list[bool]]
Grid = NewType("Grid", CellGrid)


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
    density: float = 0.3
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
    """Get valid neighbor positions based on boundary condition."""
    height, width = len(grid), len(grid[0])
    x, y = pos

    # Define neighbor offsets once
    offsets = [(dx, dy) for dx in [-1, 0, 1] for dy in [-1, 0, 1] if (dx, dy) != (0, 0)]

    match boundary:
        case BoundaryCondition.FINITE:
            return [
                Position((x + dx, y + dy))
                for dx, dy in offsets
                if 0 <= x + dx < width and 0 <= y + dy < height
            ]
        case BoundaryCondition.TOROIDAL:
            return [
                Position(((x + dx) % width, (y + dy) % height)) for dx, dy in offsets
            ]
        case _:  # INFINITE
            return [Position((x + dx, y + dy)) for dx, dy in offsets]


def count_live_neighbors(
    grid: Grid, positions: list[Position], boundary: BoundaryCondition
) -> int:
    """Count live neighbors using numpy for better performance."""
    if not positions:
        return 0

    width, height = len(grid[0]), len(grid)
    pos_array = np.array([(pos[0], pos[1]) for pos in positions])
    x_coords, y_coords = pos_array[:, 0], pos_array[:, 1]

    def validate_coords(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Filter or wrap coordinates based on boundary condition."""
        match boundary:
            case BoundaryCondition.TOROIDAL:
                return x % width, y % height
            case _:  # FINITE or INFINITE
                mask = (x >= 0) & (x < width) & (y >= 0) & (y < height)
                return x[mask], y[mask]

    x_coords, y_coords = validate_coords(x_coords, y_coords)
    if len(x_coords) == 0:
        return 0

    return int(np.sum(np.array(grid)[y_coords, x_coords]))


def get_grid_section(
    grid: Grid, top_left: Position, bottom_right: Position, boundary: BoundaryCondition
) -> Grid:
    """Get a section of the grid."""
    x1, y1 = top_left
    x2, y2 = bottom_right
    width, height = len(grid[0]), len(grid)

    grid_array = np.array(grid)

    def get_indices(start: int, end: int, size: int) -> np.ndarray:
        """Get valid indices based on boundary condition."""
        match boundary:
            case BoundaryCondition.TOROIDAL:
                return np.arange(start, end + 1) % size
            case _:  # FINITE or INFINITE
                return np.arange(start, end + 1)

    y_indices = get_indices(y1, y2, height)
    x_indices = get_indices(x1, x2, width)

    if boundary in (BoundaryCondition.FINITE, BoundaryCondition.INFINITE):
        # Create mask for valid coordinates
        y_mask = (y_indices >= 0) & (y_indices < height)
        x_mask = (x_indices >= 0) & (x_indices < width)

        # Initialize with dead cells
        section = np.zeros((y2 - y1 + 1, x2 - x1 + 1), dtype=bool)

        # Fill valid positions
        valid_y = y_indices[y_mask]
        valid_x = x_indices[x_mask]
        if len(valid_y) > 0 and len(valid_x) > 0:
            section[y_mask][:, x_mask] = grid_array[valid_y][:, valid_x]
    else:
        section = grid_array[y_indices][:, x_indices]

    return Grid([[bool(cell) for cell in row] for row in section])
