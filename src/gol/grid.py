"""Grid management for Game of Life."""

from dataclasses import dataclass
from typing import NewType, Tuple

import numpy as np
from numpy.typing import NDArray

# Type definitions
Position = NewType("Position", tuple[int, int])
# Grid now stores tuples of (is_alive: bool, age: int)
Grid = NewType("Grid", list[list[Tuple[bool, int]]])


@dataclass(frozen=True)
class GridConfig:
    """Grid configuration parameters."""

    width: int
    height: int
    density: float = 0.15  # Lower default density for better patterns
    toroidal: bool = False  # Whether grid wraps around edges


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


def get_neighbors(grid: Grid, pos: Position, toroidal: bool = False) -> list[Position]:
    """Get valid neighbor positions for a cell using vectorized operations.

    Args:
        grid: Current grid state
        pos: Position to get neighbors for
        toroidal: Whether to wrap around edges (toroidal grid)

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

    if toroidal:
        # Vectorized modulo operation for wrapping
        new_x = new_x % width
        new_y = new_y % height
        return [Position((int(nx), int(ny))) for nx, ny in zip(new_x, new_y)]
    else:
        # Vectorized bounds checking
        valid_mask = (new_x >= 0) & (new_x < width) & (new_y >= 0) & (new_y < height)
        valid_x = new_x[valid_mask]
        valid_y = new_y[valid_mask]
        return [Position((int(nx), int(ny))) for nx, ny in zip(valid_x, valid_y)]


def count_live_neighbors(grid: Grid, positions: list[Position]) -> int:
    """Count live neighbors using numpy for better performance.

    Args:
        grid: Current grid state
        positions: List of positions to check

    Returns:
        Count of live cells in given positions
    """
    if not positions:
        return 0

    # Convert positions to numpy arrays for vectorized access
    pos_array = np.array([(pos[0], pos[1]) for pos in positions])
    x_coords = pos_array[:, 0]
    y_coords = pos_array[:, 1]

    # Convert grid to numpy array for faster access - extract just alive status
    grid_array = np.array([[cell[0] for cell in row] for row in grid])
    return int(np.sum(grid_array[y_coords, x_coords]))
