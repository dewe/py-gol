"""Pattern management for Game of Life."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Protocol, cast

import numpy as np

from .pattern_types import Pattern, PatternCategory, PatternMetadata
from .rle_parser import parse_rle_pattern
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
    """RLE-based pattern storage in user's home directory."""

    storage_dir: Path = field(default_factory=lambda: Path.home() / ".gol" / "patterns")

    def save_pattern(self, pattern: Pattern) -> None:
        """Serializes pattern to RLE format."""
        # Create storage directory if needed
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Build RLE content
        lines = []

        # Add metadata
        lines.append(f"#N {pattern.metadata.name}")
        if pattern.metadata.author:
            lines.append(f"#O {pattern.metadata.author}")
        if pattern.metadata.description:
            for line in pattern.metadata.description.split("\n"):
                lines.append(f"#C {line}")

        # Add dimensions
        lines.append(f"x = {pattern.width}, y = {pattern.height}")

        # Convert cells to RLE format
        rle_data = []
        for row in pattern.cells:
            run_count = 1
            current_cell = row[0]

            for cell in row[1:]:
                if cell == current_cell:
                    run_count += 1
                else:
                    rle_data.append(str(run_count) if run_count > 1 else "")
                    rle_data.append("o" if current_cell else "b")
                    run_count = 1
                    current_cell = cell

            # Handle last run in row
            rle_data.append(str(run_count) if run_count > 1 else "")
            rle_data.append("o" if current_cell else "b")
            rle_data.append("$")

        # Replace last $ with !
        rle_data[-1] = "!"
        lines.append("".join(rle_data))

        # Write to file
        file_path = self.storage_dir / f"{pattern.metadata.name}.rle"
        file_path.write_text("\n".join(lines))

    def load_pattern(self, name: str) -> Optional[Pattern]:
        """Loads pattern from RLE file."""
        file_path = self.storage_dir / f"{name}.rle"
        if not file_path.exists():
            return None

        return parse_rle_pattern(file_path.read_text())

    def list_patterns(self) -> List[str]:
        """Lists all RLE pattern files in storage directory."""
        return [f.stem for f in self.storage_dir.glob("*.rle")]


# Built-in pattern library with historically significant patterns
BUILTIN_PATTERNS = {
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
    "pulsar": Pattern(
        metadata=PatternMetadata(
            name="pulsar",
            description="Period 3 oscillator, one of the most common oscillators",
            category=PatternCategory.OSCILLATOR,
            oscillator_period=3,
            discovery_year=1970,
            tags=["oscillator", "common"],
        ),
        cells=np.array(
            [
                [
                    False,
                    False,
                    True,
                    True,
                    True,
                    False,
                    False,
                    False,
                    True,
                    True,
                    True,
                    False,
                    False,
                ],
                [
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                ],
                [
                    True,
                    False,
                    False,
                    False,
                    False,
                    True,
                    False,
                    True,
                    False,
                    False,
                    False,
                    False,
                    True,
                ],
                [
                    True,
                    False,
                    False,
                    False,
                    False,
                    True,
                    False,
                    True,
                    False,
                    False,
                    False,
                    False,
                    True,
                ],
                [
                    True,
                    False,
                    False,
                    False,
                    False,
                    True,
                    False,
                    True,
                    False,
                    False,
                    False,
                    False,
                    True,
                ],
                [
                    False,
                    False,
                    True,
                    True,
                    True,
                    False,
                    False,
                    False,
                    True,
                    True,
                    True,
                    False,
                    False,
                ],
                [
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                ],
                [
                    False,
                    False,
                    True,
                    True,
                    True,
                    False,
                    False,
                    False,
                    True,
                    True,
                    True,
                    False,
                    False,
                ],
                [
                    True,
                    False,
                    False,
                    False,
                    False,
                    True,
                    False,
                    True,
                    False,
                    False,
                    False,
                    False,
                    True,
                ],
                [
                    True,
                    False,
                    False,
                    False,
                    False,
                    True,
                    False,
                    True,
                    False,
                    False,
                    False,
                    False,
                    True,
                ],
                [
                    True,
                    False,
                    False,
                    False,
                    False,
                    True,
                    False,
                    True,
                    False,
                    False,
                    False,
                    False,
                    True,
                ],
                [
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                ],
                [
                    False,
                    False,
                    True,
                    True,
                    True,
                    False,
                    False,
                    False,
                    True,
                    True,
                    True,
                    False,
                    False,
                ],
            ],
            dtype=np.bool_,
        ),
    ),
    "lwss": Pattern(
        metadata=PatternMetadata(
            name="lwss",
            description="Lightweight spaceship that moves horizontally",
            category=PatternCategory.SPACESHIP,
            discovery_year=1970,
            tags=["spaceship", "common"],
        ),
        cells=np.array(
            [
                [False, True, True, True, True],
                [True, False, False, False, True],
                [True, False, False, False, False],
                [True, False, False, True, False],
            ],
            dtype=np.bool_,
        ),
    ),
    "pentadecathlon": Pattern(
        metadata=PatternMetadata(
            name="pentadecathlon",
            description="Period 15 oscillator",
            category=PatternCategory.OSCILLATOR,
            oscillator_period=15,
            discovery_year=1970,
            tags=["oscillator", "common"],
        ),
        cells=np.array(
            [
                [False, False, True, False, False, False, False, True, False, False],
                [True, True, False, True, True, True, True, False, True, True],
                [False, False, True, False, False, False, False, True, False, False],
            ],
            dtype=np.bool_,
        ),
    ),
    "rpentomino": Pattern(
        metadata=PatternMetadata(
            name="rpentomino",
            description="Methuselah that evolves for many generations",
            category=PatternCategory.METHUSELAH,
            discovery_year=1970,
            tags=["methuselah", "common"],
        ),
        cells=np.array(
            [
                [False, True, True],
                [True, True, False],
                [False, True, False],
            ],
            dtype=np.bool_,
        ),
    ),
    "gosperglider": Pattern(
        metadata=PatternMetadata(
            name="gosperglider",
            description="First discovered gun pattern",
            category=PatternCategory.GUN,
            discovery_year=1970,
            tags=["gun", "common"],
        ),
        cells=np.array(
            [
                [
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    True,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                ],
                [
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    True,
                    False,
                    True,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                ],
                [
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    True,
                    True,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    True,
                    True,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    True,
                    True,
                ],
                [
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    True,
                    False,
                    False,
                    False,
                    True,
                    False,
                    False,
                    False,
                    False,
                    True,
                    True,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    True,
                    True,
                ],
                [
                    True,
                    True,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    True,
                    False,
                    False,
                    False,
                    False,
                    False,
                    True,
                    False,
                    False,
                    False,
                    True,
                    True,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                ],
                [
                    True,
                    True,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    True,
                    False,
                    False,
                    False,
                    True,
                    False,
                    True,
                    True,
                    False,
                    False,
                    False,
                    False,
                    True,
                    False,
                    True,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                ],
                [
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    True,
                    False,
                    False,
                    False,
                    False,
                    False,
                    True,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    True,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                ],
                [
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    True,
                    False,
                    False,
                    False,
                    True,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                ],
                [
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    True,
                    True,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                ],
            ],
            dtype=np.bool_,
        ),
    ),
    "beehive": Pattern(
        metadata=PatternMetadata(
            name="beehive",
            description="Common stable formation",
            category=PatternCategory.STILL_LIFE,
            discovery_year=1970,
            tags=["still life", "common"],
        ),
        cells=np.array(
            [
                [False, True, True, False],
                [True, False, False, True],
                [False, True, True, False],
            ],
            dtype=np.bool_,
        ),
    ),
}


def get_pattern_cells(pattern: Pattern, turns: int = 0) -> List[GridPosition]:
    """Returns list of (x,y) coordinates for live cells after rotation.

    Args:
        pattern: Pattern to get cells from
        turns: Number of 90-degree clockwise rotations to apply

    Returns:
        List of (x, y) coordinates for live cells after rotation
    """
    cells: List[GridPosition] = []
    height, width = pattern.cells.shape

    for y in range(height):
        for x in range(width):
            if pattern.cells[y][x]:
                # Transform coordinates based on rotation angle
                match turns:
                    case 0:  # Original orientation
                        cells.append((x, y))
                    case 1:  # 90° clockwise
                        cells.append((y, width - 1 - x))
                    case 2:  # 180°
                        cells.append((width - 1 - x, height - 1 - y))
                    case 3:  # 270° clockwise
                        cells.append((height - 1 - y, x))

    return cells


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
    """Places pattern on grid with boundary handling."""
    new_grid = grid.copy()
    turns = rotation.to_turns()
    cells = get_pattern_cells(pattern, turns)

    if centered:
        position = get_centered_position(pattern, position, rotation)

    grid_height, grid_width = grid.shape
    for dx, dy in cells:
        x = (position[0] + dx) % grid_width
        y = (position[1] + dy) % grid_height
        new_grid[y, x] = True

    return new_grid


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
