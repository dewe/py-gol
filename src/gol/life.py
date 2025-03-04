"""Pure functional implementation of Conway's Game of Life."""

from typing import List

from gol.grid import BoundaryCondition, Grid, Position, get_neighbors


def count_live_neighbors(grid: Grid, pos: Position, boundary: BoundaryCondition) -> int:
    """Count live neighbors for a cell.

    Args:
        grid: Current grid state
        pos: Position to count neighbors for
        boundary: Boundary condition to apply

    Returns:
        Number of live neighbors
    """
    neighbors = get_neighbors(grid, pos, boundary)
    height = len(grid)
    width = len(grid[0])

    # For all boundary conditions, count cells within grid
    return sum(
        1
        for neighbor_pos in neighbors
        if 0 <= neighbor_pos[1] < height
        and 0 <= neighbor_pos[0] < width
        and grid[neighbor_pos[1]][neighbor_pos[0]]
    )


def calculate_next_state(current_state: bool, live_neighbors: int) -> bool:
    """Calculate next state of a cell.

    Args:
        current_state: Current state of the cell
        live_neighbors: Number of live neighboring cells

    Returns:
        Next state of the cell
    """
    if current_state:
        return live_neighbors in (2, 3)  # Survives
    return live_neighbors == 3  # Becomes alive


def next_generation(grid: Grid, boundary: BoundaryCondition) -> Grid:
    """Calculate the next generation of the grid.

    Args:
        grid: Current grid state
        boundary: Boundary condition to apply

    Returns:
        New grid representing the next generation
    """
    height = len(grid)
    width = len(grid[0])

    # Create new grid with same dimensions
    new_grid: List[List[bool]] = []

    # Calculate next state for each cell
    for y in range(height):
        row: List[bool] = []
        for x in range(width):
            pos = Position((x, y))
            live_count = count_live_neighbors(grid, pos, boundary)
            current_state = grid[y][x]
            next_state = calculate_next_state(current_state, live_count)
            row.append(next_state)
        new_grid.append(row)

    return Grid(new_grid)
