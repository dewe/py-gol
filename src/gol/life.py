"""Pure functional implementation of Conway's Game of Life."""

import numpy as np
from scipy import signal

from gol.types import Grid, IntArray

from .grid import BoundaryCondition, expand_grid, needs_boundary_expansion


def calculate_next_state(current_state: Grid, live_neighbors: IntArray) -> Grid:
    """Calculate next state using vectorized operations for performance.

    Applies Conway's rules using NumPy's logical operations to process
    all cells simultaneously instead of iterating.
    """
    survival = np.logical_and(
        current_state, np.logical_or(live_neighbors == 2, live_neighbors == 3)
    )
    birth = np.logical_and(~current_state, live_neighbors == 3)
    result: Grid = np.logical_or(survival, birth)
    return result


def next_generation(grid: Grid, boundary: BoundaryCondition) -> Grid:
    """Calculate the next generation using optimized convolution operations.

    Uses scipy's convolve2d for efficient neighbor counting, with different
    boundary handling strategies based on the boundary condition.

    For INFINITE boundary:
    - Checks if grid needs expansion before calculating next state
    - Expands grid only when live cells are at boundaries
    - Maintains pattern evolution as if on infinite plane
    - Preserves grid center position during expansion
    """
    kernel = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], dtype=np.int_)

    if boundary == BoundaryCondition.INFINITE:
        # Check if grid needs expansion
        expand_up, expand_right, expand_down, expand_left = needs_boundary_expansion(
            grid
        )
        if any([expand_up, expand_right, expand_down, expand_left]):
            grid = expand_grid(grid, expand_up, expand_right, expand_down, expand_left)

    # Calculate live neighbor counts based on boundary condition
    match boundary:
        case BoundaryCondition.TOROIDAL:
            live_counts = signal.convolve2d(
                grid.astype(np.int_), kernel, mode="same", boundary="wrap"
            )
        case BoundaryCondition.FINITE | BoundaryCondition.INFINITE:
            # Both FINITE and INFINITE treat cells outside grid as dead
            live_counts = signal.convolve2d(
                grid.astype(np.int_), kernel, mode="same", boundary="fill", fillvalue=0
            )

    return calculate_next_state(grid, live_counts)
