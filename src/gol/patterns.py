"""Pattern management for Game of Life."""

import json
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Tuple

import numpy as np

from .grid import Grid, Position


class PatternCategory(Enum):
    """Categories for classifying patterns."""

    STILL_LIFE = auto()
    OSCILLATOR = auto()
    SPACESHIP = auto()
    GUN = auto()
    METHUSELAH = auto()
    CUSTOM = auto()


@dataclass(frozen=True)
class PatternMetadata:
    """Immutable metadata for patterns."""

    name: str
    description: str
    category: PatternCategory
    author: Optional[str] = None
    oscillator_period: Optional[int] = None
    discovery_year: Optional[int] = None
    tags: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Pattern:
    """Immutable pattern representation."""

    metadata: PatternMetadata
    cells: List[List[Tuple[bool, int]]]  # [(is_alive, age)]
    width: int
    height: int

    def __post_init__(self) -> None:
        """Validate pattern dimensions."""
        if len(self.cells) != self.height:
            raise ValueError(
                f"Pattern height {len(self.cells)} != declared height {self.height}"
            )
        if any(len(row) != self.width for row in self.cells):
            raise ValueError("Pattern width mismatch with declared width")


class PatternStorage(Protocol):
    """Protocol for pattern storage implementations."""

    def save_pattern(self, pattern: Pattern) -> None:
        """Save pattern to storage."""
        ...

    def load_pattern(self, name: str) -> Optional[Pattern]:
        """Load pattern from storage."""
        ...

    def list_patterns(self) -> List[str]:
        """List available pattern names."""
        ...


@dataclass
class FilePatternStorage:
    """File-based pattern storage implementation."""

    storage_dir: Path = field(default_factory=lambda: Path.home() / ".gol" / "patterns")

    def __post_init__(self) -> None:
        """Create storage directory if it doesn't exist."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_pattern(self, pattern: Pattern) -> None:
        """Save pattern to JSON file."""
        pattern_data = {
            "metadata": {
                "name": pattern.metadata.name,
                "description": pattern.metadata.description,
                "category": pattern.metadata.category.name,
                "author": pattern.metadata.author,
                "oscillator_period": pattern.metadata.oscillator_period,
                "discovery_year": pattern.metadata.discovery_year,
                "tags": pattern.metadata.tags,
            },
            "cells": [
                [(bool(cell[0]), int(cell[1])) for cell in row] for row in pattern.cells
            ],
            "width": pattern.width,
            "height": pattern.height,
        }

        file_path = self.storage_dir / f"{pattern.metadata.name}.json"
        with open(file_path, "w") as f:
            json.dump(pattern_data, f, indent=2)

    def load_pattern(self, name: str) -> Optional[Pattern]:
        """Load pattern from JSON file."""
        file_path = self.storage_dir / f"{name}.json"
        if not file_path.exists():
            return None

        with open(file_path) as f:
            data = json.load(f)

        metadata = PatternMetadata(
            name=data["metadata"]["name"],
            description=data["metadata"]["description"],
            category=PatternCategory[data["metadata"]["category"]],
            author=data["metadata"]["author"],
            oscillator_period=data["metadata"]["oscillator_period"],
            discovery_year=data["metadata"]["discovery_year"],
            tags=data["metadata"]["tags"],
        )

        # Convert cell data back to tuples
        cells = [
            [(bool(cell[0]), int(cell[1])) for cell in row] for row in data["cells"]
        ]

        return Pattern(
            metadata=metadata,
            cells=cells,
            width=data["width"],
            height=data["height"],
        )

    def list_patterns(self) -> List[str]:
        """List available pattern names."""
        return [f.stem for f in self.storage_dir.glob("*.json")]


# Built-in pattern library
BUILTIN_PATTERNS: Dict[str, Pattern] = {
    "glider": Pattern(
        metadata=PatternMetadata(
            name="glider",
            description="Classic glider that moves diagonally",
            category=PatternCategory.SPACESHIP,
            discovery_year=1970,
            tags=["spaceship", "common"],
        ),
        cells=[
            [(False, 0), (True, 1), (False, 0)],
            [(False, 0), (False, 0), (True, 1)],
            [(True, 1), (True, 1), (True, 1)],
        ],
        width=3,
        height=3,
    ),
    "blinker": Pattern(
        metadata=PatternMetadata(
            name="blinker",
            description="Simple period 2 oscillator",
            category=PatternCategory.OSCILLATOR,
            oscillator_period=2,
            tags=["oscillator", "common"],
        ),
        cells=[[(True, 1), (True, 1), (True, 1)]],
        width=3,
        height=1,
    ),
    "block": Pattern(
        metadata=PatternMetadata(
            name="block",
            description="Stable 2x2 block",
            category=PatternCategory.STILL_LIFE,
            tags=["still life", "common"],
        ),
        cells=[[(True, 1), (True, 1)], [(True, 1), (True, 1)]],
        width=2,
        height=2,
    ),
    "gosper_glider_gun": Pattern(
        metadata=PatternMetadata(
            name="gosper_glider_gun",
            description=(
                "First known gun pattern, discovered by Bill Gosper. "
                "Emits a new glider every 30 generations."
            ),
            category=PatternCategory.GUN,
            discovery_year=1970,
            oscillator_period=30,
            author="Bill Gosper",
            tags=["gun", "infinite growth", "historic"],
        ),
        cells=[
            # Row 1: 36 cells
            [(False, 0)] * 24 + [(True, 1)] + [(False, 0)] * 11,
            # Row 2: 36 cells
            [(False, 0)] * 22 + [(True, 1), (False, 0), (True, 1)] + [(False, 0)] * 11,
            # Row 3: 36 cells
            [(False, 0)] * 12
            + [(True, 1), (True, 1)]
            + [(False, 0)] * 6
            + [(True, 1), (True, 1)]
            + [(False, 0)] * 12
            + [(True, 1), (True, 1)],
            # Row 4: 36 cells
            [(False, 0)] * 11
            + [(True, 1)]
            + [(False, 0)] * 3
            + [(True, 1)]
            + [(False, 0)] * 4
            + [(True, 1), (True, 1)]
            + [(False, 0)] * 12
            + [(True, 1), (True, 1)],
            # Row 5: 36 cells
            [(True, 1), (True, 1)]
            + [(False, 0)] * 8
            + [(True, 1)]
            + [(False, 0)] * 5
            + [(True, 1)]
            + [(False, 0)] * 3
            + [(True, 1), (True, 1)]
            + [(False, 0)] * 14,
            # Row 6: 36 cells
            [(True, 1), (True, 1)]
            + [(False, 0)] * 8
            + [(True, 1)]
            + [(False, 0)] * 3
            + [(True, 1), (False, 0), (True, 1), (True, 1)]
            + [(False, 0)] * 4
            + [(True, 1), (False, 0), (True, 1)]
            + [(False, 0)] * 11,
            # Row 7: 36 cells
            [(False, 0)] * 10
            + [(True, 1)]
            + [(False, 0)] * 5
            + [(True, 1)]
            + [(False, 0)] * 7
            + [(True, 1)]
            + [(False, 0)] * 11,
            # Row 8: 36 cells
            [(False, 0)] * 11
            + [(True, 1)]
            + [(False, 0)] * 3
            + [(True, 1)]
            + [(False, 0)] * 20,
            # Row 9: 36 cells
            [(False, 0)] * 12 + [(True, 1), (True, 1)] + [(False, 0)] * 22,
        ],
        width=36,
        height=9,
    ),
}


def extract_pattern(
    grid: Grid, top_left: Position, bottom_right: Position, metadata: PatternMetadata
) -> Pattern:
    """Pure function to extract a pattern from a grid region.

    Args:
        grid: Source grid
        top_left: Top-left position of region
        bottom_right: Bottom-right position of region
        metadata: Pattern metadata

    Returns:
        Extracted pattern
    """
    x1, y1 = top_left
    x2, y2 = bottom_right
    width = x2 - x1 + 1
    height = y2 - y1 + 1

    cells = [[grid[y][x] for x in range(x1, x2 + 1)] for y in range(y1, y2 + 1)]

    return Pattern(metadata=metadata, cells=cells, width=width, height=height)


def get_centered_position(pattern: Pattern, cursor_position: Position) -> Position:
    """Calculate the top-left position for centered pattern placement.

    Args:
        pattern: Pattern to be placed
        cursor_position: Position where the center should be

    Returns:
        Position for the top-left corner of the pattern
    """
    # Use geometric center of the pattern grid
    x_offset = pattern.width // 2
    y_offset = pattern.height // 2

    x, y = cursor_position
    return Position((x - x_offset, y - y_offset))


def place_pattern(
    grid: Grid,
    pattern: Pattern,
    position: Position,
    rotation: int = 0,
    centered: bool = True,
) -> Grid:
    """Pure function to place a pattern on the grid.

    Args:
        grid: Target grid
        pattern: Pattern to place
        position: Position for placement (center position if centered=True,
                 top-left if False)
        rotation: Rotation in degrees (0, 90, 180, 270)
        centered: Whether to center the pattern at the given position

    Returns:
        New grid with pattern placed
    """
    # Calculate actual placement position
    placement_pos = get_centered_position(pattern, position) if centered else position

    # Create numpy arrays for efficient rotation
    pattern_array = np.array(pattern.cells)
    if rotation:
        pattern_array = np.rot90(pattern_array, k=rotation // 90)

    # Create new grid copy
    new_grid = [row[:] for row in grid]
    x, y = placement_pos
    height = len(grid)
    width = len(grid[0])

    # Place pattern with wrapping
    for py in range(pattern_array.shape[0]):
        for px in range(pattern_array.shape[1]):
            grid_y = (y + py) % height
            grid_x = (x + px) % width
            new_grid[grid_y][grid_x] = tuple(pattern_array[py, px].tolist())

    return Grid(new_grid)


def find_pattern(grid: Grid, pattern: Pattern) -> List[Position]:
    """Pure function to find all occurrences of a pattern.

    Args:
        grid: Grid to search in
        pattern: Pattern to find

    Returns:
        List of positions where pattern was found
    """
    # Convert to numpy arrays for efficient comparison
    grid_array = np.array([[cell[0] for cell in row] for row in grid])
    pattern_array = np.array([[cell[0] for cell in row] for row in pattern.cells])

    height = len(grid)
    width = len(grid[0])
    matches = []

    # Slide pattern over grid
    for y in range(height - pattern.height + 1):
        for x in range(width - pattern.width + 1):
            window = grid_array[y : y + pattern.height, x : x + pattern.width]
            if np.array_equal(window, pattern_array):
                matches.append(Position((x, y)))

    return matches


def get_pattern_cells(pattern: Pattern, rotation: int = 0) -> List[Tuple[int, int]]:
    """Extract cell positions from a pattern with rotation support.

    Args:
        pattern: Pattern to extract cells from
        rotation: Rotation in degrees (0, 90, 180, 270)

    Returns:
        List of (x, y) coordinates for live cells in the pattern
    """
    # Create numpy array for efficient rotation
    pattern_array = np.array(
        [[(cell[0], cell[1]) for cell in row] for row in pattern.cells]
    )
    if rotation:
        pattern_array = np.rot90(pattern_array, k=rotation // 90)

    # Extract live cell positions
    height, width = pattern_array.shape[:2]  # Get dimensions from first two axes
    cells = []
    for y in range(height):
        for x in range(width):
            if pattern_array[y, x][0]:  # Check is_alive from the tuple
                cells.append((x, y))

    return cells
