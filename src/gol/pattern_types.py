"""Shared type definitions for pattern management."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional

import numpy as np

from .types import PatternGrid


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
        shape = self.cells.shape
        return int(shape[1])

    @property
    def height(self) -> int:
        """Pattern height in cells."""
        shape = self.cells.shape
        return int(shape[0])
