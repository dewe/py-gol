"""Pure functional implementation of Conway's Game of Life."""

import numpy as np
from scipy import signal

from gol.grid import BoundaryCondition
from gol.types import Grid, IntArray


def calculate_next_state(current_state: Grid, live_neighbors: IntArray) -> Grid:
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
    # Define convolution kernel for counting neighbors
    kernel = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], dtype=np.int_)

    # Calculate live neighbors based on boundary condition
    match boundary:
        case BoundaryCondition.TOROIDAL:
            # For toroidal, use periodic boundary
            live_counts = signal.convolve2d(
                grid.astype(np.int_), kernel, mode="same", boundary="wrap"
            )
        case BoundaryCondition.FINITE:
            # For finite, use zero boundary
            live_counts = signal.convolve2d(
                grid.astype(np.int_), kernel, mode="same", boundary="fill", fillvalue=0
            )
        case _:  # INFINITE
            # For infinite, extend with zeros
            live_counts = signal.convolve2d(grid.astype(np.int_), kernel, mode="same")

    return calculate_next_state(grid, live_counts)
