"""State management for Game of Life renderer.

This module provides immutable state management for the Game of Life renderer.
It uses frozen dataclasses to ensure state immutability and provides pure functions
for state updates.
"""

import dataclasses
from typing import Optional

import numpy as np

from gol.types import GameDimensions, TerminalPosition, ViewportOffset


@dataclasses.dataclass(frozen=True)
class ViewportState:
    """Immutable viewport state.

    Manages the viewport dimensions and position relative to the grid origin.
    All fields are immutable to ensure thread safety and predictable state updates.
    """

    dimensions: GameDimensions  # Use game dimensions for viewport
    offset_x: int = 0  # Viewport offset from grid origin
    offset_y: int = 0  # Viewport offset from grid origin

    @property
    def width(self) -> int:
        """Get viewport width."""
        return self.dimensions[0]

    @property
    def height(self) -> int:
        """Get viewport height."""
        return self.dimensions[1]

    @property
    def offset(self) -> ViewportOffset:
        """Get viewport offset as (offset_x, offset_y)."""
        return (self.offset_x, self.offset_y)

    def with_adjusted_offset(self, dx: int, dy: int) -> "ViewportState":
        """Create new viewport state with adjusted offset for grid expansion.

        Args:
            dx: Horizontal offset adjustment
            dy: Vertical offset adjustment

        Returns:
            New ViewportState with adjusted offset
        """
        return dataclasses.replace(
            self, offset_x=self.offset_x + dx, offset_y=self.offset_y + dy
        )

    @classmethod
    def create(cls, dimensions: tuple[int, int]) -> "ViewportState":
        """Create a new viewport state with specified dimensions."""
        return cls(dimensions=dimensions)


@dataclasses.dataclass(frozen=True)
class RendererState:
    """Immutable renderer state.

    Manages the current state of the renderer including viewport position,
    cursor position, and pattern mode.
    """

    viewport: ViewportState = dataclasses.field(
        default_factory=lambda: ViewportState(dimensions=(50, 30))
    )
    terminal_pos: TerminalPosition = dataclasses.field(
        default_factory=lambda: TerminalPosition(x=0, y=0)
    )
    cursor_x: int = 0  # Cursor position in grid coordinates
    cursor_y: int = 0
    pattern_mode: bool = False  # Whether pattern placement mode is active
    previous_grid: Optional[np.ndarray] = None
    pattern_cells: Optional[np.ndarray] = None
    paused: bool = False
    debug_mode: bool = False  # Whether debug info should be shown

    @classmethod
    def create(
        cls,
        dimensions: tuple[int, int] = (50, 30),
        pattern_mode: bool = False,
        cursor_x: int = 0,
        cursor_y: int = 0,
        previous_grid: Optional[np.ndarray] = None,
        pattern_cells: Optional[np.ndarray] = None,
        viewport: Optional[ViewportState] = None,
        paused: bool = False,
        terminal_pos: Optional[TerminalPosition] = None,
    ) -> "RendererState":
        """Create a new renderer state with optional overrides."""
        return cls(
            pattern_mode=pattern_mode,
            cursor_x=cursor_x,
            cursor_y=cursor_y,
            previous_grid=previous_grid,
            pattern_cells=pattern_cells,
            viewport=viewport or ViewportState.create(dimensions),
            paused=paused,
            terminal_pos=terminal_pos or TerminalPosition(x=0, y=0),
        )

    def with_viewport(self, viewport: ViewportState) -> "RendererState":
        """Create new state with updated viewport."""
        return dataclasses.replace(self, viewport=viewport)

    def with_cursor(self, x: int, y: int) -> "RendererState":
        """Create new state with updated cursor position."""
        return dataclasses.replace(self, cursor_x=x, cursor_y=y)

    def with_pattern_mode(self, enabled: bool) -> "RendererState":
        """Create new state with updated pattern mode."""
        return dataclasses.replace(self, pattern_mode=enabled)

    def with_previous_grid(self, grid: Optional[np.ndarray]) -> "RendererState":
        """Create new state with updated previous grid."""
        return dataclasses.replace(self, previous_grid=grid)

    def with_pattern_cells(self, cells: Optional[np.ndarray]) -> "RendererState":
        """Create new state with updated pattern cells."""
        return dataclasses.replace(self, pattern_cells=cells)

    def with_paused(self, paused: bool) -> "RendererState":
        """Create new state with updated pause state."""
        return dataclasses.replace(self, paused=paused)

    def with_terminal_dimensions(self, width: int, height: int) -> "RendererState":
        """Create new state with updated terminal dimensions."""
        return dataclasses.replace(
            self,
            viewport=ViewportState.create((width, height)),
            previous_grid=None,
            pattern_cells=None,
        )

    def with_terminal_position(self, terminal_pos: TerminalPosition) -> "RendererState":
        """Create new state with updated terminal position."""
        return dataclasses.replace(self, terminal_pos=terminal_pos)

    def with_debug_mode(self, enabled: bool) -> "RendererState":
        """Create new state with updated debug mode."""
        return dataclasses.replace(self, debug_mode=enabled)
