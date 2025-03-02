"""Grid management for Game of Life."""

import random
from dataclasses import dataclass
from typing import NewType

# Type definitions
Position = NewType("Position", tuple[int, int])
Grid = NewType("Grid", list[list[bool]])


@dataclass(frozen=True)
class GridConfig:
    """Grid configuration parameters."""

    width: int
    height: int
    density: float = 0.3
    toroidal: bool = False  # Whether grid wraps around edges


def create_grid(config: GridConfig) -> Grid:
    """Creates initial grid with random cell distribution.

    Args:
        config: Grid configuration parameters

    Returns:
        A new Grid with random live cells based on density
    """
    return Grid(
        [
            [random.random() < config.density for _ in range(config.width)]
            for _ in range(config.height)
        ]
    )


def get_neighbors(grid: Grid, pos: Position, toroidal: bool = False) -> list[Position]:
    """Get valid neighbor positions for a cell.

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
    neighbors = []

    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            new_x = x + dx
            new_y = y + dy

            if toroidal:
                # Wrap around edges
                new_x = new_x % width
                new_y = new_y % height
                neighbors.append(Position((new_x, new_y)))
            else:
                # Only include positions within grid bounds
                if 0 <= new_x < width and 0 <= new_y < height:
                    neighbors.append(Position((new_x, new_y)))

    return neighbors


def count_live_neighbors(grid: Grid, positions: list[Position]) -> int:
    """Count live neighbors from given positions.

    Args:
        grid: Current grid state
        positions: List of positions to check

    Returns:
        Count of live cells in given positions
    """
    return sum(1 for pos in positions if grid[pos[0]][pos[1]])
