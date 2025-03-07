"""Test viewport functionality for Game of Life.

Tests viewport state management, resizing, panning and coordinate translation.
"""

from unittest.mock import Mock

from blessed.keyboard import Keystroke

from gol.controller import handle_viewport_pan, handle_viewport_resize
from gol.renderer import RendererConfig, calculate_viewport_bounds, handle_user_input
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
    key.name = name
    key.configure_mock(__str__=Mock(return_value=value))
    key.configure_mock(__eq__=Mock(side_effect=lambda x: str(key) == x))
    key.configure_mock(isdigit=Mock(return_value=value.isdigit() if value else False))
    return key


def test_viewport_state_defaults() -> None:
    """Test default viewport state initialization."""
    viewport = ViewportState(dimensions=(40, 25))
    assert viewport.dimensions == (40, 25)
    assert viewport.offset_x == 0
    assert viewport.offset_y == 0


def test_viewport_state_custom_values() -> None:
    """Test viewport state with custom values."""
    viewport = ViewportState(dimensions=(30, 20), offset_x=5, offset_y=-3)
    assert viewport.dimensions == (30, 20)
    assert viewport.offset_x == 5
    assert viewport.offset_y == -3


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
    """Test viewport panning in all directions."""
    grid_width, grid_height = 50, 30
    initial_viewport = ViewportState(dimensions=(40, 25))
    state = RendererState().with_viewport(initial_viewport)

    # Test panning right
    new_state = handle_viewport_pan(state, 5, 0, grid_width, grid_height)
    assert new_state.viewport.offset_x == 5
    assert new_state.viewport.offset_y == 0
    assert new_state.viewport.dimensions == initial_viewport.dimensions

    # Test panning down
    new_state = handle_viewport_pan(state, 0, 3, grid_width, grid_height)
    assert new_state.viewport.offset_x == 0
    assert new_state.viewport.offset_y == 3
    assert new_state.viewport.dimensions == initial_viewport.dimensions

    # Test panning diagonally
    new_state = handle_viewport_pan(state, 2, 2, grid_width, grid_height)
    assert new_state.viewport.offset_x == 2
    assert new_state.viewport.offset_y == 2
    assert new_state.viewport.dimensions == initial_viewport.dimensions


def test_viewport_pan_grid_boundaries() -> None:
    """Test viewport panning respects grid boundaries."""
    grid_width, grid_height = 50, 30
    viewport_width, viewport_height = 20, 10
    initial_state = RendererState().with_viewport(
        ViewportState(dimensions=(viewport_width, viewport_height))
    )

    # Test right boundary
    state = initial_state
    max_x_offset = grid_width - viewport_width
    for _ in range(max_x_offset + 5):
        state = handle_viewport_pan(state, 1, 0, grid_width, grid_height)
    assert state.viewport.offset_x == max_x_offset

    # Test bottom boundary
    state = initial_state
    max_y_offset = grid_height - viewport_height
    for _ in range(max_y_offset + 5):
        state = handle_viewport_pan(state, 0, 1, grid_width, grid_height)
    assert state.viewport.offset_y == max_y_offset


def test_viewport_bounds_basic() -> None:
    """Test basic viewport bounds calculation."""
    viewport = ViewportState(dimensions=(40, 25))
    grid_width, grid_height = 100, 60
    terminal_width, terminal_height = 120, 40
    start_x, start_y = 2, 1

    bounds = calculate_viewport_bounds(
        viewport,
        terminal_width,
        terminal_height,
        start_x,
        start_y,
        grid_width,
        grid_height,
    )
    viewport_start_x, viewport_start_y, visible_width, visible_height = bounds

    assert viewport_start_x == 0
    assert viewport_start_y == 0
    assert visible_width == 40
    assert visible_height == 25


def test_viewport_bounds_with_offset() -> None:
    """Test viewport bounds with offset."""
    viewport = ViewportState(dimensions=(40, 25), offset_x=5, offset_y=3)
    grid_width, grid_height = 100, 60
    terminal_width, terminal_height = 120, 40
    start_x, start_y = 2, 1

    bounds = calculate_viewport_bounds(
        viewport,
        terminal_width,
        terminal_height,
        start_x,
        start_y,
        grid_width,
        grid_height,
    )
    viewport_start_x, viewport_start_y, visible_width, visible_height = bounds

    assert viewport_start_x == 5
    assert viewport_start_y == 3
    assert visible_width == 40
    assert visible_height == 25


def test_viewport_bounds_terminal_constraints() -> None:
    """Test viewport bounds respect terminal constraints."""
    viewport = ViewportState(dimensions=(100, 50))
    grid_width, grid_height = 80, 40
    terminal_width, terminal_height = 60, 30
    start_x, start_y = 2, 1

    bounds = calculate_viewport_bounds(
        viewport,
        terminal_width,
        terminal_height,
        start_x,
        start_y,
        grid_width,
        grid_height,
    )
    _, _, visible_width, visible_height = bounds

    assert visible_width <= terminal_width // 2  # Account for cell width
    assert visible_height <= terminal_height - 1  # Account for status line


def test_viewport_key_bindings() -> None:
    """Test viewport key bindings in both modes."""
    config = RendererConfig()

    # Test pattern mode
    pattern_state = RendererState(pattern_mode=True)

    # Viewport resize
    plus_key = create_mock_keystroke(value="+")
    command, _ = handle_user_input(plus_key, config, pattern_state)
    assert command == "viewport_expand"

    minus_key = create_mock_keystroke(value="-")
    command, _ = handle_user_input(minus_key, config, pattern_state)
    assert command == "viewport_shrink"

    # Test normal mode
    normal_state = RendererState(pattern_mode=False)

    # Viewport panning
    left_key = create_mock_keystroke(name="KEY_LEFT")
    command, _ = handle_user_input(left_key, config, normal_state)
    assert command == "viewport_pan_left"

    right_key = create_mock_keystroke(name="KEY_RIGHT")
    command, _ = handle_user_input(right_key, config, normal_state)
    assert command == "viewport_pan_right"
