"""Pattern management for Game of Life."""

import json
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Protocol, cast

import numpy as np

from .types import Grid, GridPosition, PatternGrid


class PatternTransform(Enum):
    """Manages pattern rotations in 90-degree increments."""

    NONE = 0
    RIGHT = 90
    FLIP = 180
    LEFT = 270

    def next_rotation(self) -> "PatternTransform":
        """Cycles to next 90-degree clockwise rotation for pattern preview."""
        rotations = list(PatternTransform)
        current_idx = rotations.index(self)
        return rotations[(current_idx + 1) % len(rotations)]

    def to_turns(self) -> int:
        """Converts rotation angle to number of numpy rot90 operations needed."""
        return self.value // 90


class PatternCategory(Enum):
    """Classification system for organizing patterns by behavior and complexity."""

    STILL_LIFE = auto()
    OSCILLATOR = auto()
    SPACESHIP = auto()
    GUN = auto()
    METHUSELAH = auto()
    CUSTOM = auto()


@dataclass(frozen=True)
class PatternMetadata:
    """Immutable pattern attributes for categorization and attribution."""

    name: str
    description: str
    category: PatternCategory
    author: Optional[str] = None
    oscillator_period: Optional[int] = None
    discovery_year: Optional[int] = None
    tags: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Pattern:
    """Immutable pattern representation optimized for numpy operations."""

    metadata: PatternMetadata
    cells: PatternGrid

    def __post_init__(self) -> None:
        """Ensures consistent numpy boolean array representation."""
        if not isinstance(self.cells, np.ndarray) or self.cells.dtype != np.bool_:
            object.__setattr__(self, "cells", np.array(self.cells, dtype=np.bool_))

    @property
    def width(self) -> int:
        """Pattern width in cells."""
        return self.cells.shape[1]

    @property
    def height(self) -> int:
        """Pattern height in cells."""
        return self.cells.shape[0]


class PatternStorage(Protocol):
    """Interface for pattern persistence implementations."""

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
    """JSON-based pattern storage in user's home directory."""

    storage_dir: Path = field(default_factory=lambda: Path.home() / ".gol" / "patterns")

    def __post_init__(self) -> None:
        """Ensures storage directory exists."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_pattern(self, pattern: Pattern) -> None:
        """Serializes pattern to JSON with numpy array conversion."""
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
            "cells": pattern.cells.tolist(),
        }

        file_path = self.storage_dir / f"{pattern.metadata.name}.json"
        with open(file_path, "w") as f:
            json.dump(pattern_data, f, indent=2)

    def load_pattern(self, name: str) -> Optional[Pattern]:
        """Deserializes pattern from JSON with numpy array reconstruction."""
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

        cells = np.array(data["cells"], dtype=np.bool_)
        return Pattern(metadata=metadata, cells=cells)

    def list_patterns(self) -> List[str]:
        """Lists all JSON pattern files in storage directory."""
        return [f.stem for f in self.storage_dir.glob("*.json")]


# Built-in pattern library with historically significant patterns
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
                # Row 1
                [False] * 24 + [True] + [False] * 11,
                # Row 2
                [False] * 22 + [True, False, True] + [False] * 11,
                # Row 3
                [False] * 12
                + [True, True]
                + [False] * 6
                + [True, True]
                + [False] * 12
                + [True, True],
                # Row 4
                [False] * 11
                + [True]
                + [False] * 3
                + [True]
                + [False] * 4
                + [True, True]
                + [False] * 12
                + [True, True],
                # Row 5
                [True, True]
                + [False] * 8
                + [True]
                + [False] * 5
                + [True]
                + [False] * 3
                + [True, True]
                + [False] * 14,
                # Row 6
                [True, True]
                + [False] * 8
                + [True]
                + [False] * 3
                + [True, False, True, True]
                + [False] * 4
                + [True, False, True]
                + [False] * 11,
                # Row 7
                [False] * 10
                + [True]
                + [False] * 5
                + [True]
                + [False] * 7
                + [True]
                + [False] * 11,
                # Row 8
                [False] * 11 + [True] + [False] * 3 + [True] + [False] * 20,
                # Row 9
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
    """Creates a new pattern from a section of an existing grid."""
    x1, y1 = top_left
    x2, y2 = bottom_right

    cells = cast(PatternGrid, grid[y1 : y2 + 1, x1 : x2 + 1].copy())
    return Pattern(metadata=metadata, cells=cells)


def get_centered_position(
    pattern: Pattern,
    cursor_position: GridPosition,
    rotation: PatternTransform = PatternTransform.NONE,
) -> GridPosition:
    """Calculates pattern placement position to center it on cursor."""
    x, y = cursor_position
    # Adjust dimensions for rotated patterns
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
    """Places pattern on grid with boundary handling and rotation support."""
    rotated_cells = cast(PatternGrid, np.rot90(pattern.cells, k=-rotation.to_turns()))
    pos = get_centered_position(pattern, position, rotation) if centered else position
    x, y = pos

    new_grid = grid.copy()
    height, width = grid.shape
    pattern_height, pattern_width = rotated_cells.shape

    # Calculate valid intersection between pattern and grid
    y_start = max(0, y)
    y_end = min(height, y + pattern_height)
    x_start = max(0, x)
    x_end = min(width, x + pattern_width)

    # Handle patterns partially outside grid bounds
    pattern_y_start = max(0, -y)
    pattern_x_start = max(0, -x)

    new_grid[y_start:y_end, x_start:x_end] |= rotated_cells[
        pattern_y_start : pattern_y_start + (y_end - y_start),
        pattern_x_start : pattern_x_start + (x_end - x_start),
    ]

    return cast(Grid, new_grid)


def find_pattern(grid: Grid, pattern: Pattern) -> List[GridPosition]:
    """Locates all instances of pattern in grid using sliding window comparison."""
    positions: List[GridPosition] = []
    pattern_height, pattern_width = pattern.cells.shape

    for y in range(grid.shape[0] - pattern_height + 1):
        for x in range(grid.shape[1] - pattern_width + 1):
            if np.array_equal(
                grid[y : y + pattern_height, x : x + pattern_width], pattern.cells
            ):
                positions.append((x, y))

    return positions


def get_pattern_cells(pattern: Pattern, rotation: int = 0) -> List[GridPosition]:
    """Generates list of live cell positions with rotation transformation."""
    cells: List[GridPosition] = []
    for y in range(pattern.height):
        for x in range(pattern.width):
            if pattern.cells[y][x]:
                # Transform coordinates based on rotation angle
                match rotation:
                    case 0:  # Original orientation
                        cells.append((x, y))
                    case 1:  # 90° clockwise
                        cells.append((pattern.height - 1 - y, x))
                    case 2:  # 180°
                        cells.append((pattern.width - 1 - x, pattern.height - 1 - y))
                    case 3:  # 270° clockwise
                        cells.append((y, pattern.width - 1 - x))

    return cells
