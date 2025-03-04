"""Pattern management for Game of Life."""

import json
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Protocol

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
    cells: List[List[bool]]  # Simplified to just booleans
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
            "cells": [[bool(cell) for cell in row] for row in pattern.cells],
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

        # Convert cell data to booleans
        cells = [[bool(cell) for cell in row] for row in data["cells"]]

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
            [False, True, False],
            [False, False, True],
            [True, True, True],
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
        cells=[[True, True, True]],
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
        cells=[[True, True], [True, True]],
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
            [False] * 24 + [True] + [False] * 11,
            # Row 2: 36 cells
            [False] * 22 + [True, False, True] + [False] * 11,
            # Row 3: 36 cells
            [False] * 12
            + [True, True]
            + [False] * 6
            + [True, True]
            + [False] * 12
            + [True, True],
            # Row 4: 36 cells
            [False] * 11
            + [True]
            + [False] * 3
            + [True]
            + [False] * 4
            + [True, True]
            + [False] * 12
            + [True, True],
            # Row 5: 36 cells
            [True, True]
            + [False] * 8
            + [True]
            + [False] * 5
            + [True]
            + [False] * 3
            + [True, True]
            + [False] * 14,
            # Row 6: 36 cells
            [True, True]
            + [False] * 8
            + [True]
            + [False] * 3
            + [True, False, True, True]
            + [False] * 4
            + [True, False, True]
            + [False] * 11,
            # Row 7: 36 cells
            [False] * 10
            + [True]
            + [False] * 5
            + [True]
            + [False] * 7
            + [True]
            + [False] * 11,
            # Row 8: 36 cells
            [False] * 11 + [True] + [False] * 3 + [True] + [False] * 20,
            # Row 9: 36 cells
            [False] * 12 + [True, True] + [False] * 22,
        ],
        width=36,
        height=9,
    ),
}


def extract_pattern(
    grid: Grid, top_left: Position, bottom_right: Position, metadata: PatternMetadata
) -> Pattern:
    """Extract a pattern from a grid section.

    Args:
        grid: Source grid
        top_left: Top-left position of pattern
        bottom_right: Bottom-right position of pattern
        metadata: Pattern metadata

    Returns:
        Extracted pattern
    """
    x1, y1 = top_left
    x2, y2 = bottom_right
    width = x2 - x1 + 1
    height = y2 - y1 + 1

    # Extract pattern cells
    cells = []
    for y in range(y1, y2 + 1):
        row = []
        for x in range(x1, x2 + 1):
            row.append(grid[y][x])
        cells.append(row)

    return Pattern(metadata=metadata, cells=cells, width=width, height=height)


def get_centered_position(pattern: Pattern, cursor_position: Position) -> Position:
    """Calculate centered position for pattern placement.

    Args:
        pattern: Pattern to place
        cursor_position: Cursor position

    Returns:
        Top-left position for centered pattern placement
    """
    x, y = cursor_position
    x_offset = pattern.width // 2
    y_offset = pattern.height // 2
    return Position((x - x_offset, y - y_offset))


def place_pattern(
    grid: Grid,
    pattern: Pattern,
    position: Position,
    rotation: int = 0,
    centered: bool = True,
) -> Grid:
    """Place a pattern on the grid.

    Args:
        grid: Target grid
        pattern: Pattern to place
        position: Position to place pattern at
        rotation: Rotation in degrees (must be multiple of 90)
        centered: Whether to center pattern on position

    Returns:
        New grid with pattern placed
    """
    if rotation % 90 != 0:
        raise ValueError("Rotation must be multiple of 90 degrees")

    # Convert rotation to number of 90-degree turns
    turns = (rotation // 90) % 4

    # Get pattern cells with rotation
    pattern_cells = get_pattern_cells(pattern, turns)

    # Calculate actual position
    pos = get_centered_position(pattern, position) if centered else position

    # Create new grid
    height = len(grid)
    width = len(grid[0])
    new_grid = [[cell for cell in row] for row in grid]

    # Place pattern cells
    for x, y in pattern_cells:
        grid_x = pos[0] + x
        grid_y = pos[1] + y
        if 0 <= grid_x < width and 0 <= grid_y < height:
            new_grid[grid_y][grid_x] = True

    return Grid(new_grid)


def find_pattern(grid: Grid, pattern: Pattern) -> List[Position]:
    """Find all occurrences of a pattern in the grid.

    Args:
        grid: Grid to search in
        pattern: Pattern to find

    Returns:
        List of positions where pattern was found
    """
    height = len(grid)
    width = len(grid[0])
    pattern_height = len(pattern.cells)
    pattern_width = len(pattern.cells[0])
    positions = []

    # Search each possible position
    for y in range(height - pattern_height + 1):
        for x in range(width - pattern_width + 1):
            matches = True
            for py in range(pattern_height):
                for px in range(pattern_width):
                    if pattern.cells[py][px] != grid[y + py][x + px]:
                        matches = False
                        break
                if not matches:
                    break
            if matches:
                positions.append(Position((x, y)))

    return positions


def get_pattern_cells(pattern: Pattern, rotation: int = 0) -> List[tuple[int, int]]:
    """Get list of cell positions in a pattern.

    Args:
        pattern: Source pattern
        rotation: Number of 90-degree clockwise rotations

    Returns:
        List of (x, y) positions of live cells
    """
    cells = []
    for y in range(pattern.height):
        for x in range(pattern.width):
            if pattern.cells[y][x]:
                # Apply rotation
                match rotation:
                    case 0:  # 0 degrees
                        cells.append((x, y))
                    case 1:  # 90 degrees
                        cells.append((pattern.height - 1 - y, x))
                    case 2:  # 180 degrees
                        cells.append((pattern.width - 1 - x, pattern.height - 1 - y))
                    case 3:  # 270 degrees
                        cells.append((y, pattern.width - 1 - x))

    return cells
