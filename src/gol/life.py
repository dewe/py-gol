"""Pure functional implementation of Conway's Game of Life."""

from typing import Optional, cast

import numpy as np
from scipy import signal

from gol.state import ViewportState
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


def next_generation(
    grid: Grid,
    boundary: BoundaryCondition,
    viewport_state: Optional[ViewportState] = None,
) -> tuple[Grid, Optional[ViewportState]]:
    """Calculate the next generation using optimized convolution operations.

    Uses scipy's convolve2d for efficient neighbor counting, with different
    boundary handling strategies based on the boundary condition.

    For INFINITE boundary:
    - Checks if grid needs expansion before calculating next state
    - Expands grid only when live cells are at boundaries
    - Maintains pattern evolution as if on infinite plane
    - Preserves grid center position during expansion
    - Adjusts viewport offset if needed to maintain view position

    Args:
        grid: Current grid state
        boundary: Boundary condition to apply
        viewport_state: Optional viewport state to adjust during expansion

    Returns:
        Tuple of:
        - Next generation grid state
        - Updated viewport state if provided and modified, None otherwise
    """
    kernel = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], dtype=np.int_)

    if boundary == BoundaryCondition.INFINITE:
        # Check if grid needs expansion
        expand_up, expand_right, expand_down, expand_left = needs_boundary_expansion(
            grid
        )
        if any([expand_up, expand_right, expand_down, expand_left]):
            grid, (dx, dy) = expand_grid(
                grid, expand_up, expand_right, expand_down, expand_left
            )
            # Adjust viewport offset if provided
            # Only adjust for expansions that affect viewport position
            if viewport_state is not None:
                # Only adjust for left/up expansions as they shift the grid content
                dx_adjust = dx if expand_left else 0
                dy_adjust = dy if expand_up else 0
                viewport_state = viewport_state.with_adjusted_offset(
                    dx_adjust, dy_adjust
                )

    # Calculate live neighbor counts based on boundary condition
    match boundary:
        case BoundaryCondition.TOROIDAL:
            live_counts = signal.convolve2d(grid, kernel, mode="same", boundary="wrap")
        case BoundaryCondition.INFINITE:
            live_counts = signal.convolve2d(
                grid, kernel, mode="same", boundary="fill", fillvalue=0
            )
        case _:  # FINITE
            live_counts = signal.convolve2d(
                grid, kernel, mode="same", boundary="fill", fillvalue=0
            )

    # Apply Game of Life rules using vectorized operations
    new_grid = np.where(
        grid,  # For live cells
        (live_counts == 2) | (live_counts == 3),  # Survival rule
        live_counts == 3,  # Birth rule
    )

    return cast(Grid, new_grid), viewport_state
