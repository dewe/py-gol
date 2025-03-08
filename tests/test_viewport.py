"""Test viewport functionality for Game of Life.

Tests viewport state management, resizing, panning and coordinate translation.
"""

from unittest.mock import Mock, PropertyMock

import pytest
from blessed.keyboard import Keystroke

from gol.controller import handle_viewport_pan, handle_viewport_resize
from gol.grid import BoundaryCondition
from gol.renderer import TerminalProtocol, calculate_viewport_bounds
from gol.state import RendererState, ViewportState


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
    new_state = handle_viewport_pan(state, dx=1, dy=1)
    assert new_state.viewport.offset_x <= grid_width - viewport.width
    assert new_state.viewport.offset_y <= grid_height - viewport.height

    # Test panning to negative coordinates
    viewport = ViewportState(dimensions=(40, 30), offset_x=5, offset_y=5)
    state = RendererState().with_viewport(viewport)
    new_state = handle_viewport_pan(state, dx=-10, dy=-10)
    assert new_state.viewport.offset_x >= 0
    assert new_state.viewport.offset_y >= 0


def test_viewport_bounds_basic() -> None:
    """Test basic viewport bounds calculation."""
    viewport = ViewportState(dimensions=(40, 30))
    bounds = calculate_viewport_bounds(
        viewport=viewport,
        terminal_width=80,
        terminal_height=24,
        start_x=0,
        start_y=0,
        grid_width=100,
        grid_height=80,
    )
    viewport_start_x, viewport_start_y, visible_width, visible_height = bounds

    assert viewport_start_x == 0
    assert viewport_start_y == 0
    assert visible_width <= viewport.width
    assert visible_height <= viewport.height


def test_viewport_bounds_with_offset() -> None:
    """Test viewport bounds calculation with offset."""
    viewport = ViewportState(dimensions=(40, 30), offset_x=20, offset_y=15)
    bounds = calculate_viewport_bounds(
        viewport=viewport,
        terminal_width=80,
        terminal_height=24,
        start_x=0,
        start_y=0,
        grid_width=100,
        grid_height=80,
    )
    viewport_start_x, viewport_start_y, visible_width, visible_height = bounds

    assert viewport_start_x == 20
    assert viewport_start_y == 15
    assert visible_width <= viewport.width
    assert visible_height <= viewport.height


def test_viewport_bounds_terminal_constraints() -> None:
    """Test viewport bounds respect terminal constraints."""
    viewport = ViewportState(dimensions=(60, 40))  # Larger than terminal
    bounds = calculate_viewport_bounds(
        viewport=viewport,
        terminal_width=80,
        terminal_height=24,
        start_x=5,
        start_y=2,
        grid_width=100,
        grid_height=80,
    )
    viewport_start_x, viewport_start_y, visible_width, visible_height = bounds

    # Terminal width - start_x - margins
    max_visible_width = (80 - 5) // 2
    # Terminal height - start_y - status lines
    max_visible_height = 24 - 2 - 2

    assert visible_width <= max_visible_width
    assert visible_height <= max_visible_height


def test_viewport_infinite_mode_expansion() -> None:
    """Test viewport behavior during grid expansion in INFINITE mode."""
    viewport = ViewportState(dimensions=(40, 30), offset_x=10, offset_y=10)

    # Simulate grid expansion to the right
    bounds = calculate_viewport_bounds(
        viewport=viewport,
        terminal_width=80,
        terminal_height=24,
        start_x=0,
        start_y=0,
        grid_width=100,
        grid_height=80,
        boundary_condition=BoundaryCondition.INFINITE,
        grid_expansion=(1, 0, 0, 0),  # right expansion
    )
    viewport_start_x, viewport_start_y, visible_width, visible_height = bounds

    # Viewport position should remain stable relative to original cells
    assert viewport_start_x == 10  # Original offset preserved
    assert viewport_start_y == 10  # Original offset preserved
    assert visible_width <= viewport.width
    assert visible_height <= viewport.height


def test_viewport_infinite_mode_multiple_expansion() -> None:
    """Test viewport behavior during multiple grid expansions in INFINITE mode."""
    viewport = ViewportState(dimensions=(40, 30), offset_x=20, offset_y=15)

    # Simulate grid expansion in multiple directions
    bounds = calculate_viewport_bounds(
        viewport=viewport,
        terminal_width=80,
        terminal_height=24,
        start_x=0,
        start_y=0,
        grid_width=120,
        grid_height=100,
        boundary_condition=BoundaryCondition.INFINITE,
        grid_expansion=(1, 1, 1, 1),  # expansion in all directions
    )
    viewport_start_x, viewport_start_y, visible_width, visible_height = bounds

    # Viewport should maintain relative position to original cells
    assert viewport_start_x == 21  # Original offset + right expansion
    assert viewport_start_y == 16  # Original offset + down expansion
    assert visible_width <= viewport.width
    assert visible_height <= viewport.height


def test_viewport_infinite_mode_no_expansion() -> None:
    """Test viewport behavior with no grid expansion in INFINITE mode."""
    viewport = ViewportState(dimensions=(40, 30), offset_x=5, offset_y=5)

    bounds = calculate_viewport_bounds(
        viewport=viewport,
        terminal_width=80,
        terminal_height=24,
        start_x=0,
        start_y=0,
        grid_width=100,
        grid_height=80,
        boundary_condition=BoundaryCondition.INFINITE,
        grid_expansion=(0, 0, 0, 0),  # no expansion
    )
    viewport_start_x, viewport_start_y, visible_width, visible_height = bounds

    # Viewport should maintain exact position when no expansion occurs
    assert viewport_start_x == 5
    assert viewport_start_y == 5
    assert visible_width <= viewport.width
    assert visible_height <= viewport.height
