"""Type definitions for Game of Life.

Defines core type aliases for grid operations, pattern management,
rendering, and NumPy array operations used throughout the codebase.
"""

import dataclasses
from typing import TypeAlias, Union

import numpy as np
from numpy.typing import NDArray

# Core grid types
GridPosition: TypeAlias = tuple[int, int]  # (x, y) coordinates
Grid: TypeAlias = NDArray[np.bool_]  # Main game grid
GridView: TypeAlias = NDArray[np.bool_]  # View into a grid section
GridIndex: TypeAlias = Union[int, slice]  # Grid indexing types

# Grid dimensions
GridShape: TypeAlias = tuple[int, int]  # (height, width) of grid
GridDimensions: TypeAlias = tuple[int, int]  # (width, height) for grid creation
GridPadding: TypeAlias = tuple[
    tuple[int, int], tuple[int, int]
]  # ((top, bottom), (left, right))
GridSlice: TypeAlias = slice  # Type for grid slicing operations

# Grid expansion
ExpansionFlags: TypeAlias = tuple[bool, bool, bool, bool]  # (up, right, down, left)

# Pattern types
PatternGrid: TypeAlias = NDArray[np.bool_]  # Pattern definition grid

# Rendering types
ScreenPosition: TypeAlias = tuple[int, int]  # Terminal coordinates
RenderGrid: TypeAlias = dict[ScreenPosition, bool]  # Sparse render grid

# Game dimensions
GameDimensions: TypeAlias = tuple[
    int, int
]  # (width, height) for both grid and viewport

# Viewport types
ViewportOffset: TypeAlias = tuple[int, int]  # (offset_x, offset_y)
ViewportDimensions: TypeAlias = tuple[int, int]  # (width, height)


@dataclasses.dataclass(frozen=True)
class TerminalPosition:
    """Position in terminal space where viewport is rendered."""

    x: int  # Terminal x coordinate
    y: int  # Terminal y coordinate


@dataclasses.dataclass(frozen=True)
class ViewportBounds:
    """Visible portion of grid through viewport."""

    grid_start: tuple[int, int]  # Start coordinates in grid
    visible_dims: tuple[int, int]  # Width, height that can be shown


# NumPy operation types
BoolArray: TypeAlias = NDArray[np.bool_]  # Boolean arrays
IntArray: TypeAlias = NDArray[np.int_]  # Integer arrays
