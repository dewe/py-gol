"""State management for Game of Life renderer.

This module provides immutable state management for the Game of Life renderer.
It uses frozen dataclasses to ensure state immutability and provides pure functions
for state updates.
"""

from dataclasses import dataclass
from typing import Optional, Set

from .types import RenderGrid, ScreenPosition

CellPos = ScreenPosition


@dataclass(frozen=True)
class RendererState:
    """Immutable core renderer state.

    This class maintains the core state of the renderer between frames.
    All fields are immutable to ensure thread safety and predictable state updates.
    State updates are performed through pure functions that return new state instances.
    """

    previous_grid: Optional[RenderGrid] = None
    start_x: int = 0
    start_y: int = 0
    terminal_width: int = 0
    terminal_height: int = 0

    pattern_mode: bool = False
    cursor_x: int = 0
    cursor_y: int = 0
    previous_pattern_cells: Optional[frozenset[CellPos]] = None
    was_in_pattern_mode: bool = False
    pattern_menu: str = ""

    @classmethod
    def create(cls) -> "RendererState":
        return cls()

    def with_grid_position(self, x: int, y: int) -> "RendererState":
        from dataclasses import replace

        return replace(self, start_x=x, start_y=y)

    def with_terminal_dimensions(self, width: int, height: int) -> "RendererState":
        from dataclasses import replace

        return replace(self, terminal_width=width, terminal_height=height)

    def with_pattern_mode(self, enabled: bool) -> "RendererState":
        from dataclasses import replace

        return replace(self, pattern_mode=enabled)

    def with_cursor_position(self, x: int, y: int) -> "RendererState":
        from dataclasses import replace

        return replace(self, cursor_x=x, cursor_y=y)

    def with_previous_grid(self, grid: Optional[RenderGrid]) -> "RendererState":
        from dataclasses import replace

        return replace(self, previous_grid=grid)

    def with_pattern_cells(self, cells: Optional[Set[CellPos]]) -> "RendererState":
        from dataclasses import replace

        frozen_cells = frozenset(cells) if cells is not None else None
        return replace(self, previous_pattern_cells=frozen_cells)
