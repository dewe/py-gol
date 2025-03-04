"""Pure functional implementation of Conway's Game of Life."""

import numpy as np
from numpy.typing import NDArray

from gol.grid import BoundaryCondition, count_live_neighbors, get_neighbors
from gol.types import Grid


def calculate_next_state(current_state: Grid, live_neighbors: NDArray[np.int_]) -> Grid:
    """Calculate next state of cells using vectorized operations.

    Args:
        current_state: Current state of cells as boolean array
        live_neighbors: Number of live neighboring cells for each cell

    Returns:
        Next state of cells as boolean array
    """
    # Vectorized implementation of Conway's rules
    survival = np.logical_and(
        current_state, np.logical_or(live_neighbors == 2, live_neighbors == 3)
    )
    birth = np.logical_and(~current_state, live_neighbors == 3)
    result: Grid = np.logical_or(survival, birth)
    return result


def next_generation(grid: Grid, boundary: BoundaryCondition) -> Grid:
    """Calculate the next generation of the grid using vectorized operations.

    Args:
        grid: Current grid state
        boundary: Boundary condition to apply

    Returns:
        New grid representing the next generation
    """
    height, width = grid.shape
    live_counts = np.zeros((height, width), dtype=np.int_)

    # Calculate live neighbors for all cells
    for y in range(height):
        for x in range(width):
            pos = (x, y)  # type: tuple[int, int]
            neighbors = get_neighbors(grid, pos, boundary)
            live_counts[y, x] = count_live_neighbors(grid, neighbors, boundary)

    # Calculate next state for all cells at once
    return calculate_next_state(grid, live_counts)
