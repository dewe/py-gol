"""Pure functional implementation of Conway's Game of Life."""

from typing import List, Tuple

from gol.grid import BoundaryCondition, Grid, Position, get_neighbors

CellState = Tuple[bool, int]  # (is_alive, age)


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
        and grid[neighbor_pos[1]][neighbor_pos[0]][0]
    )


def calculate_next_state(
    current_state: Tuple[bool, int], live_neighbors: int
) -> Tuple[bool, int]:
    """Calculate next state and age of a cell.

    Args:
        current_state: Current (is_alive, age) state of the cell
        live_neighbors: Number of live neighboring cells

    Returns:
        Next (is_alive, age) state of the cell
    """
    is_alive, age = current_state

    if is_alive:
        if live_neighbors in (2, 3):  # Survives
            return True, age + 1
        else:  # Dies
            return False, 0
    else:
        if live_neighbors == 3:  # Becomes alive
            return True, 1
        else:  # Stays dead
            return False, 0


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
    new_grid: List[List[Tuple[bool, int]]] = []

    # Calculate next state for each cell
    for y in range(height):
        row: List[Tuple[bool, int]] = []
        for x in range(width):
            pos = Position((x, y))
            live_count = count_live_neighbors(grid, pos, boundary)
            current_state = grid[y][x]
            next_state = calculate_next_state(current_state, live_count)
            row.append(next_state)
        new_grid.append(row)

    return Grid(new_grid)
