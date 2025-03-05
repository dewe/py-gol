"""Pattern management for Game of Life."""

import json
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Protocol, cast

import numpy as np

from .types import Grid, GridPosition, PatternGrid  # Add these from types.py


class PatternTransform(Enum):
    """Pattern rotation behavior.

    Represents and manages pattern rotations in 90-degree increments.
    Provides methods for cycling through rotations and converting to numpy turns.
    """

    NONE = 0
    RIGHT = 90
    FLIP = 180
    LEFT = 270

    def next_rotation(self) -> "PatternTransform":
        """Get next rotation (90 degrees clockwise)."""
        rotations = list(PatternTransform)
        current_idx = rotations.index(self)
        return rotations[(current_idx + 1) % len(rotations)]

    def to_turns(self) -> int:
        """Convert rotation to number of 90-degree turns."""
        return self.value // 90


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
    """Immutable pattern representation using NumPy arrays."""

    metadata: PatternMetadata
    cells: PatternGrid

    def __post_init__(self) -> None:
        """Validate pattern dimensions and convert to NumPy array if needed."""
        if not isinstance(self.cells, np.ndarray) or self.cells.dtype != np.bool_:
            # Convert to PatternGrid type with correct dtype
            object.__setattr__(self, "cells", np.array(self.cells, dtype=np.bool_))

    @property
    def width(self) -> int:
        """Get pattern width."""
        return self.cells.shape[1]

    @property
    def height(self) -> int:
        """Get pattern height."""
        return self.cells.shape[0]


class PatternStorage(Protocol):
    """Protocol for pattern storage implementations."""

    def save_pattern(self, pattern: Pattern) -> None:
        """Save pattern to storage."""
        pass

    def load_pattern(self, name: str) -> Optional[Pattern]:
        """Load pattern from storage."""
        pass

    def list_patterns(self) -> List[str]:
        """List available pattern names."""
        pass


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
            "cells": pattern.cells.tolist(),  # Convert NumPy array to list for JSON
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

        # Convert list to NumPy array
        cells = np.array(data["cells"], dtype=np.bool_)

        return Pattern(metadata=metadata, cells=cells)

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
        cells=cast(
            PatternGrid,
            np.array(
                [[False, True, False], [False, False, True], [True, True, True]],
                dtype=np.bool_,
            ),
        ),
    ),
    "blinker": Pattern(
        metadata=PatternMetadata(
            name="blinker",
            description="Simple period 2 oscillator",
            category=PatternCategory.OSCILLATOR,
            oscillator_period=2,
            tags=["oscillator", "common"],
        ),
        cells=np.array([[True, True, True]], dtype=np.bool_),
    ),
    "block": Pattern(
        metadata=PatternMetadata(
            name="block",
            description="Stable 2x2 block",
            category=PatternCategory.STILL_LIFE,
            tags=["still life", "common"],
        ),
        cells=np.array([[True, True], [True, True]], dtype=np.bool_),
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
        cells=np.array(
            [
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
            dtype=np.bool_,
        ),
    ),
}


def extract_pattern(
    grid: Grid,
    top_left: GridPosition,
    bottom_right: GridPosition,
    metadata: PatternMetadata,
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

    # Cast the extracted cells to PatternGrid
    cells = cast(PatternGrid, grid[y1 : y2 + 1, x1 : x2 + 1].copy())
    return Pattern(metadata=metadata, cells=cells)


def get_centered_position(
    pattern: Pattern,
    cursor_position: GridPosition,
    rotation: PatternTransform = PatternTransform.NONE,
) -> GridPosition:
    """Calculate centered position for pattern placement.

    Args:
        pattern: Pattern to place
        cursor_position: Cursor position
        rotation: Pattern rotation transform

    Returns:
        Top-left position for centered pattern placement
    """
    x, y = cursor_position
    # Adjust dimensions based on rotation
    width = pattern.height if rotation.value in (90, 270) else pattern.width
    height = pattern.width if rotation.value in (90, 270) else pattern.height
    x_offset = width // 2
    y_offset = height // 2
    return (x - x_offset, y - y_offset)


def place_pattern(
    grid: Grid,
    pattern: Pattern,
    position: GridPosition,
    rotation: PatternTransform = PatternTransform.NONE,
    centered: bool = True,
) -> Grid:
    """Place a pattern on the grid.

    Args:
        grid: Target grid
        pattern: Pattern to place
        position: Position to place pattern at
        rotation: Pattern rotation transform
        centered: Whether to center pattern on position

    Returns:
        New grid with pattern placed
    """
    # Get rotated pattern cells
    rotated_cells = cast(PatternGrid, np.rot90(pattern.cells, k=-rotation.to_turns()))

    # Calculate placement position
    pos = get_centered_position(pattern, position, rotation) if centered else position
    x, y = pos

    # Create new grid
    new_grid = grid.copy()

    # Calculate valid placement region
    height, width = grid.shape
    pattern_height, pattern_width = rotated_cells.shape

    # Calculate valid slice ranges
    y_start = max(0, y)
    y_end = min(height, y + pattern_height)
    x_start = max(0, x)
    x_end = min(width, x + pattern_width)

    # Calculate pattern slice ranges
    pattern_y_start = max(0, -y)
    pattern_x_start = max(0, -x)

    # Place pattern in valid region
    new_grid[y_start:y_end, x_start:x_end] |= rotated_cells[
        pattern_y_start : pattern_y_start + (y_end - y_start),
        pattern_x_start : pattern_x_start + (x_end - x_start),
    ]

    return cast(Grid, new_grid)


def find_pattern(grid: Grid, pattern: Pattern) -> List[GridPosition]:
    """Find all occurrences of a pattern in the grid.

    Args:
        grid: Grid to search in
        pattern: Pattern to find

    Returns:
        List of positions where pattern was found
    """
    positions: List[GridPosition] = []
    pattern_height, pattern_width = pattern.cells.shape

    # Use NumPy's sliding window approach
    for y in range(grid.shape[0] - pattern_height + 1):
        for x in range(grid.shape[1] - pattern_width + 1):
            if np.array_equal(
                grid[y : y + pattern_height, x : x + pattern_width], pattern.cells
            ):
                positions.append((x, y))

    return positions


def get_pattern_cells(pattern: Pattern, rotation: int = 0) -> List[GridPosition]:
    """Get list of cell positions in a pattern.

    Args:
        pattern: Source pattern
        rotation: Number of 90-degree clockwise rotations

    Returns:
        List of (x, y) positions of live cells, adjusted for rotation
    """
    cells: List[GridPosition] = []
    for y in range(pattern.height):
        for x in range(pattern.width):
            if pattern.cells[y][x]:
                # Apply rotation
                match rotation:
                    case 0:  # 0 degrees
                        cells.append((x, y))
                    case 1:  # 90 degrees clockwise
                        cells.append((pattern.height - 1 - y, x))
                    case 2:  # 180 degrees
                        cells.append((pattern.width - 1 - x, pattern.height - 1 - y))
                    case 3:  # 270 degrees clockwise
                        cells.append((y, pattern.width - 1 - x))

    return cells
