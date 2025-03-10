"""Test viewport functionality for Game of Life.

Tests viewport state management, resizing, panning and coordinate translation.
"""

from typing import Any
from unittest.mock import Mock, PropertyMock

import numpy as np
import pytest
from blessed.formatters import ParameterizingString
from blessed.keyboard import Keystroke

from gol.controller import handle_viewport_pan, handle_viewport_resize
from gol.renderer import (
    TerminalProtocol,
    calculate_terminal_position,
    calculate_viewport_bounds,
)
from gol.state import RendererState, ViewportState
from gol.types import TerminalPosition


def create_mock_keystroke(name: str = "", value: str = "") -> Mock:
    """Create a mock keystroke for testing.

    Args:
        name: Name of the key pressed
        value: Value of the key pressed

    Returns:
        Mock keystroke object
    """
    key = Mock(spec=Keystroke)
    key.name = name or value
    key.configure_mock(__str__=Mock(return_value=value))
    key.configure_mock(__eq__=Mock(side_effect=lambda x: str(key) == x))
    key.configure_mock(isdigit=Mock(return_value=value.isdigit() if value else False))
    return key


@pytest.fixture
def mock_terminal() -> TerminalProtocol:
    """Create a mock terminal for testing."""
    terminal = Mock(spec=TerminalProtocol)
    type(terminal).width = PropertyMock(return_value=80)
    type(terminal).height = PropertyMock(return_value=24)
    terminal.clear.return_value = ""
    terminal.move_xy.return_value = ""
    terminal.hide_cursor.return_value = ""
    terminal.normal_cursor.return_value = ""
    terminal.enter_fullscreen.return_value = ""
    terminal.exit_fullscreen.return_value = ""
    terminal.enter_ca_mode.return_value = ""
    terminal.exit_ca_mode.return_value = ""
    type(terminal).normal = PropertyMock(return_value="")
    type(terminal).dim = PropertyMock(return_value="")
    type(terminal).white = PropertyMock(return_value="")
    type(terminal).blue = PropertyMock(return_value="")
    type(terminal).green = PropertyMock(return_value="")
    type(terminal).yellow = PropertyMock(return_value="")
    type(terminal).magenta = PropertyMock(return_value="")
    terminal.inkey.return_value = Keystroke("")
    terminal.cbreak.return_value = terminal
    return terminal


def test_viewport_state_defaults() -> None:
    """Test viewport state default values."""
    state = RendererState()
    assert state.viewport.width == 50
    assert state.viewport.height == 30
    assert state.viewport.offset == (0, 0)


def test_viewport_state_custom_values() -> None:
    """Test viewport state with custom values."""
    viewport = ViewportState(dimensions=(50, 30), offset_x=5, offset_y=10)
    assert viewport.width == 50
    assert viewport.height == 30
    assert viewport.offset == (5, 10)


def test_viewport_resize_expand() -> None:
    """Test viewport expansion behavior."""
    state = RendererState()
    initial_dimensions = state.viewport.dimensions
    new_state = handle_viewport_resize(state, expand=True)

    assert new_state.viewport.dimensions[0] == initial_dimensions[0] + 4
    assert new_state.viewport.dimensions[1] == initial_dimensions[1] + 4
    assert new_state.viewport.offset == state.viewport.offset


def test_viewport_resize_shrink() -> None:
    """Test viewport shrinking behavior."""
    initial_viewport = ViewportState(dimensions=(40, 30))
    state = RendererState().with_viewport(initial_viewport)
    new_state = handle_viewport_resize(state, expand=False)

    assert new_state.viewport.dimensions[0] == 36  # 40 - 4
    assert new_state.viewport.dimensions[1] == 26  # 30 - 4
    assert new_state.viewport.offset == initial_viewport.offset


def test_viewport_resize_minimum_bounds() -> None:
    """Test viewport minimum size constraints."""
    initial_viewport = ViewportState(dimensions=(22, 12))
    state = RendererState().with_viewport(initial_viewport)
    new_state = handle_viewport_resize(state, expand=False)

    assert new_state.viewport.dimensions[0] >= 20  # Minimum width
    assert new_state.viewport.dimensions[1] >= 10  # Minimum height


def test_viewport_pan() -> None:
    """Test viewport panning behavior."""
    grid_width, grid_height = 100, 80
    initial_viewport = ViewportState(dimensions=(40, 30), offset_x=5, offset_y=5)
    state = RendererState().with_viewport(initial_viewport)

    # Test panning in all directions
    state = handle_viewport_pan(
        state, dx=1, dy=0, grid_width=grid_width, grid_height=grid_height
    )  # Right
    assert state.viewport.offset == (6, 5)

    state = handle_viewport_pan(
        state, dx=-1, dy=0, grid_width=grid_width, grid_height=grid_height
    )  # Left
    assert state.viewport.offset == (5, 5)

    state = handle_viewport_pan(
        state, dx=0, dy=1, grid_width=grid_width, grid_height=grid_height
    )  # Down
    assert state.viewport.offset == (5, 6)

    state = handle_viewport_pan(
        state, dx=0, dy=-1, grid_width=grid_width, grid_height=grid_height
    )  # Up
    assert state.viewport.offset == (5, 5)


def test_viewport_pan_grid_boundaries() -> None:
    """Test viewport panning respects grid boundaries."""
    grid_width, grid_height = 100, 80
    viewport = ViewportState(dimensions=(40, 30), offset_x=80, offset_y=60)
    state = RendererState().with_viewport(viewport)

    # Test panning beyond grid boundaries
    new_state = handle_viewport_pan(
        state, dx=1, dy=1, grid_width=grid_width, grid_height=grid_height
    )

    # Ensure viewport offset is clamped to grid boundaries
    assert new_state.viewport.offset_x <= grid_width - viewport.width
    assert new_state.viewport.offset_y <= grid_height - viewport.height
    assert new_state.viewport.offset_x >= 0
    assert new_state.viewport.offset_y >= 0


def test_viewport_bounds_basic() -> None:
    """Test basic viewport bounds calculation."""
    viewport = ViewportState(dimensions=(40, 30))
    terminal_pos = TerminalPosition(x=0, y=0)
    bounds = calculate_viewport_bounds(
        viewport=viewport,
        terminal_width=80,
        terminal_height=24,
        terminal_pos=terminal_pos,
        grid_width=100,
        grid_height=80,
    )

    assert bounds.grid_start == (0, 0)
    assert bounds.visible_dims[0] <= viewport.width
    assert bounds.visible_dims[1] <= viewport.height


def test_viewport_bounds_with_offset() -> None:
    """Test viewport bounds calculation with offset."""
    viewport = ViewportState(dimensions=(40, 30), offset_x=20, offset_y=15)
    terminal_pos = TerminalPosition(x=0, y=0)
    bounds = calculate_viewport_bounds(
        viewport=viewport,
        terminal_width=80,
        terminal_height=24,
        terminal_pos=terminal_pos,
        grid_width=100,
        grid_height=80,
    )

    assert bounds.grid_start == (20, 15)
    assert bounds.visible_dims[0] <= viewport.width
    assert bounds.visible_dims[1] <= viewport.height


def test_viewport_bounds_terminal_constraints() -> None:
    """Test viewport bounds respect terminal constraints."""
    viewport = ViewportState(dimensions=(60, 40))  # Larger than terminal
    terminal_pos = TerminalPosition(x=5, y=2)
    bounds = calculate_viewport_bounds(
        viewport=viewport,
        terminal_width=80,
        terminal_height=24,
        terminal_pos=terminal_pos,
        grid_width=100,
        grid_height=80,
    )

    # Terminal width - terminal_pos.x - margins
    max_visible_width = (80 - terminal_pos.x) // 2
    # Terminal height - terminal_pos.y - status lines
    max_visible_height = 24 - terminal_pos.y - 2

    assert bounds.visible_dims[0] <= max_visible_width
    assert bounds.visible_dims[1] <= max_visible_height


def test_terminal_position_calculation() -> None:
    """Test terminal position calculation centers grid properly."""

    class MockTerminal(TerminalProtocol):
        """Mock terminal for testing."""

        @property
        def width(self) -> int:
            return 100

        @property
        def height(self) -> int:
            return 30

        @property
        def dim(self) -> str:
            return ""

        @property
        def normal(self) -> str:
            return ""

        @property
        def white(self) -> str:
            return ""

        @property
        def blue(self) -> str:
            return ""

        @property
        def green(self) -> str:
            return ""

        @property
        def yellow(self) -> str:
            return ""

        @property
        def magenta(self) -> str:
            return ""

        def move_xy(self, x: int, y: int) -> ParameterizingString:
            return ParameterizingString("")

        def exit_fullscreen(self) -> str:
            return ""

        def enter_fullscreen(self) -> str:
            return ""

        def hide_cursor(self) -> str:
            return ""

        def normal_cursor(self) -> str:
            return ""

        def clear(self) -> str:
            return ""

        def enter_ca_mode(self) -> str:
            return ""

        def exit_ca_mode(self) -> str:
            return ""

        def inkey(self, timeout: float = 0) -> Keystroke:
            return Keystroke("")

        def cbreak(self) -> Any:
            return self

    grid = np.zeros((40, 60), dtype=bool)  # 40 rows, 60 columns
    terminal = MockTerminal()

    pos = calculate_terminal_position(terminal, grid)

    # Expected center position:
    # Terminal width: 100, Grid display width: 60*2=120 chars
    # Terminal height: 30, Grid height: 40, Status lines: 3
    expected_x = (100 - (60 * 2)) // 2  # Center horizontally
    expected_y = (27 - 40) // 2 + 1  # Center vertically with status line space

    assert pos.x == max(0, expected_x)
    assert pos.y == max(1, expected_y)


def test_viewport_pan_boundaries() -> None:
    """
    Given: A grid and viewport of known dimensions
    When: Panning the viewport in different directions
    Then: Should stop at grid boundaries
    """
    # Create initial state with viewport smaller than grid
    grid_width, grid_height = 50, 30
    viewport_width, viewport_height = 20, 10
    initial_state = RendererState().with_viewport(
        ViewportState(
            dimensions=(viewport_width, viewport_height),
            offset_x=0,
            offset_y=0,
        )
    )

    # Test panning right to boundary
    max_x_offset = grid_width - viewport_width
    state = initial_state
    for _ in range(max_x_offset + 5):  # Try to pan beyond boundary
        state = handle_viewport_pan(state, 1, 0, grid_width, grid_height)
    assert state.viewport.offset_x == max_x_offset  # Should stop at boundary
    # Verify viewport right edge aligns with grid right edge
    assert state.viewport.offset_x + viewport_width == grid_width

    # Test panning down to boundary
    max_y_offset = grid_height - viewport_height
    state = initial_state
    for _ in range(max_y_offset + 5):  # Try to pan beyond boundary
        state = handle_viewport_pan(state, 0, 1, grid_width, grid_height)
    assert state.viewport.offset_y == max_y_offset  # Should stop at boundary
    # Verify viewport bottom edge aligns with grid bottom edge
    assert state.viewport.offset_y + viewport_height == grid_height
