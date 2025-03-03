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


def place_pattern(
    grid: Grid, pattern: Pattern, position: Position, rotation: int = 0
) -> Grid:
    """Pure function to place a pattern on the grid.

    Args:
        grid: Target grid
        pattern: Pattern to place
        position: Top-left position for placement
        rotation: Rotation in degrees (0, 90, 180, 270)

    Returns:
        New grid with pattern placed
    """
    # Create numpy arrays for efficient rotation
    pattern_array = np.array(pattern.cells)
    if rotation:
        pattern_array = np.rot90(pattern_array, k=rotation // 90)

    # Create new grid copy
    new_grid = [row[:] for row in grid]
    x, y = position
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
