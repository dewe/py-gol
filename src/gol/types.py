"""Type definitions for Game of Life."""

from typing import Literal, TypeAlias, Union

import numpy as np
from numpy.typing import NDArray

# Core grid types
GridPosition: TypeAlias = tuple[int, int]  # (x, y) coordinates in game grid space
Grid: TypeAlias = NDArray[np.bool_]
GridView: TypeAlias = NDArray[np.bool_]
GridIndex: TypeAlias = Union[int, slice]

# Pattern types
PatternGrid: TypeAlias = NDArray[np.bool_]
PatternTransform: TypeAlias = Literal[0, 90, 180, 270]  # Rotation angles

# Rendering types
ScreenPosition: TypeAlias = tuple[
    int, int
]  # (x, y) coordinates in terminal/display space
RenderGrid: TypeAlias = dict[ScreenPosition, bool]

# Type aliases for numpy operations
BoolArray: TypeAlias = NDArray[np.bool_]
IntArray: TypeAlias = NDArray[np.int_]
