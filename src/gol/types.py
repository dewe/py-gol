"""Type definitions for Game of Life.

Defines core type aliases for grid operations, pattern management,
rendering, and NumPy array operations used throughout the codebase.
"""

from typing import TypeAlias, Union

import numpy as np
from numpy.typing import NDArray

# Core grid types
GridPosition: TypeAlias = tuple[int, int]  # (x, y) coordinates
Grid: TypeAlias = NDArray[np.bool_]  # Main game grid
GridView: TypeAlias = NDArray[np.bool_]  # View into a grid section
GridIndex: TypeAlias = Union[int, slice]  # Grid indexing types

# Pattern types
PatternGrid: TypeAlias = NDArray[np.bool_]  # Pattern definition grid

# Rendering types
ScreenPosition: TypeAlias = tuple[int, int]  # Terminal coordinates
RenderGrid: TypeAlias = dict[ScreenPosition, bool]  # Sparse render grid

# NumPy operation types
BoolArray: TypeAlias = NDArray[np.bool_]  # Boolean arrays
IntArray: TypeAlias = NDArray[np.int_]  # Integer arrays
