"""Test viewport functionality for Game of Life.

Tests viewport state management, resizing, panning and coordinate translation.
"""

from unittest.mock import Mock

from blessed.keyboard import Keystroke

from gol.controller import handle_viewport_pan, handle_viewport_resize
from gol.renderer import RendererConfig, calculate_viewport_bounds, handle_user_input
from gol.state import RendererState, ViewportState
from gol.types import ViewportBounds, ViewportDimensions, ViewportOffset


def test_viewport_state_defaults() -> None:
    """Given a new viewport state
    When created with defaults
    Then it should have expected initial values
    """
    viewport = ViewportState()
    dimensions: ViewportDimensions = viewport.dimensions
    offset: ViewportOffset = viewport.offset
    assert dimensions == (40, 25)
    assert offset == (0, 0)


def test_viewport_state_custom_values() -> None:
    """Given a viewport state
    When created with custom values
    Then it should preserve those values
    """
    viewport = ViewportState(width=30, height=20, offset_x=5, offset_y=-3)
    dimensions: ViewportDimensions = viewport.dimensions
    offset: ViewportOffset = viewport.offset
    assert dimensions == (30, 20)
    assert offset == (5, -3)


def test_renderer_state_default_viewport() -> None:
    """Given a new renderer state
    When created with defaults
    Then it should have a default viewport
    """
    state = RendererState()
    assert isinstance(state.viewport, ViewportState)
    dimensions: ViewportDimensions = state.viewport.dimensions
    assert dimensions == (40, 25)


def test_viewport_resize_expand() -> None:
    """Given a renderer state with default viewport
    When expanding the viewport
    Then dimensions should increase by delta while preserving offset
    """
    state = RendererState()
    new_state = handle_viewport_resize(state, expand=True)

    dimensions: ViewportDimensions = new_state.viewport.dimensions
    offset: ViewportOffset = new_state.viewport.offset
    assert dimensions == (state.viewport.width + 4, state.viewport.height + 4)
    assert offset == (state.viewport.offset_x, state.viewport.offset_y)


def test_viewport_resize_shrink() -> None:
    """Given a renderer state with large viewport
    When shrinking the viewport
    Then dimensions should decrease by delta while preserving offset
    """
    initial_viewport = ViewportState(width=40, height=30)
    state = RendererState(viewport=initial_viewport)
    new_state = handle_viewport_resize(state, expand=False)

    dimensions: ViewportDimensions = new_state.viewport.dimensions
    offset: ViewportOffset = new_state.viewport.offset
    assert dimensions == (state.viewport.width - 4, state.viewport.height - 4)
    assert offset == (state.viewport.offset_x, state.viewport.offset_y)


def test_viewport_resize_minimum_bounds() -> None:
    """Given a renderer state with small viewport
    When shrinking below minimum size
    Then dimensions should not go below minimum bounds
    """
    initial_viewport = ViewportState(width=22, height=12)
    state = RendererState(viewport=initial_viewport)
    new_state = handle_viewport_resize(state, expand=False)

    dimensions: ViewportDimensions = new_state.viewport.dimensions
    assert dimensions == (20, 10)  # Minimum dimensions


def test_viewport_pan() -> None:
    """Given a renderer state with viewport
    When panning in different directions
    Then offset should update accordingly while preserving dimensions
    and respecting grid boundaries
    """
    grid_width, grid_height = 50, 30
    initial_viewport = ViewportState(width=40, height=25, offset_x=0, offset_y=0)
    state = RendererState(viewport=initial_viewport)

    # Pan right
    state = handle_viewport_pan(
        state, dx=1, dy=0, grid_width=grid_width, grid_height=grid_height
    )
    dimensions: ViewportDimensions = state.viewport.dimensions
    offset: ViewportOffset = state.viewport.offset
    assert offset == (1, 0)
    assert dimensions == (40, 25)

    # Pan down
    state = handle_viewport_pan(
        state, dx=0, dy=1, grid_width=grid_width, grid_height=grid_height
    )
    offset = state.viewport.offset
    assert offset == (1, 1)

    # Pan left twice (should stop at 0)
    state = handle_viewport_pan(
        state, dx=-2, dy=0, grid_width=grid_width, grid_height=grid_height
    )
    offset = state.viewport.offset
    assert offset == (0, 1)  # Clamped at left boundary

    # Pan up twice (should stop at 0)
    state = handle_viewport_pan(
        state, dx=0, dy=-2, grid_width=grid_width, grid_height=grid_height
    )
    offset = state.viewport.offset
    assert offset == (0, 0)  # Clamped at top boundary

    # Pan beyond right boundary
    max_x = grid_width - initial_viewport.width
    state = handle_viewport_pan(
        state, dx=max_x + 5, dy=0, grid_width=grid_width, grid_height=grid_height
    )
    offset = state.viewport.offset
    assert offset == (max_x, 0)  # Clamped at right boundary

    # Pan beyond bottom boundary
    max_y = grid_height - initial_viewport.height
    state = handle_viewport_pan(
        state, dx=0, dy=max_y + 5, grid_width=grid_width, grid_height=grid_height
    )
    offset = state.viewport.offset
    assert offset == (max_x, max_y)  # Clamped at bottom boundary


def test_viewport_key_bindings_pattern_mode() -> None:
    """Given a renderer state in pattern mode
    When pressing viewport control keys
    Then appropriate viewport commands should be returned
    """
    state = RendererState(pattern_mode=True)
    config = RendererConfig()

    # Test viewport resize keys
    plus_key = Mock(spec=Keystroke)
    plus_key.configure_mock(__str__=Mock(return_value="+"))
    plus_key.configure_mock(name="")
    plus_key.configure_mock(isdigit=Mock(return_value=False))
    plus_key.configure_mock(__eq__=Mock(side_effect=lambda x: str(plus_key) == x))
    command, _ = handle_user_input(plus_key, config, state)
    assert command == "viewport_expand"

    minus_key = Mock(spec=Keystroke)
    minus_key.configure_mock(__str__=Mock(return_value="-"))
    minus_key.configure_mock(name="")
    minus_key.configure_mock(isdigit=Mock(return_value=False))
    minus_key.configure_mock(__eq__=Mock(side_effect=lambda x: str(minus_key) == x))
    command, _ = handle_user_input(minus_key, config, state)
    assert command == "viewport_shrink"


def test_viewport_key_bindings_normal_mode() -> None:
    """Given a renderer state in normal mode
    When pressing viewport control keys
    Then appropriate viewport commands should be returned
    """
    state = RendererState(pattern_mode=False)
    config = RendererConfig()

    # Test arrow keys for viewport panning
    left_key = Mock(spec=Keystroke)
    left_key.configure_mock(name="KEY_LEFT")
    left_key.configure_mock(__str__=Mock(return_value=""))
    left_key.configure_mock(isdigit=Mock(return_value=False))
    command, _ = handle_user_input(left_key, config, state)
    assert command == "viewport_pan_left"

    right_key = Mock(spec=Keystroke)
    right_key.configure_mock(name="KEY_RIGHT")
    right_key.configure_mock(__str__=Mock(return_value=""))
    right_key.configure_mock(isdigit=Mock(return_value=False))
    command, _ = handle_user_input(right_key, config, state)
    assert command == "viewport_pan_right"

    up_key = Mock(spec=Keystroke)
    up_key.configure_mock(name="KEY_UP")
    up_key.configure_mock(__str__=Mock(return_value=""))
    up_key.configure_mock(isdigit=Mock(return_value=False))
    command, _ = handle_user_input(up_key, config, state)
    assert command == "viewport_pan_up"

    down_key = Mock(spec=Keystroke)
    down_key.configure_mock(name="KEY_DOWN")
    down_key.configure_mock(__str__=Mock(return_value=""))
    down_key.configure_mock(isdigit=Mock(return_value=False))
    command, _ = handle_user_input(down_key, config, state)
    assert command == "viewport_pan_down"


def test_calculate_viewport_bounds_basic() -> None:
    """Given basic viewport settings
    When calculating viewport bounds
    Then should return correct coordinate mappings
    """
    # Given
    viewport = ViewportState(width=40, height=25, offset_x=0, offset_y=0)
    terminal_width = 100
    terminal_height = 30
    start_x = 5
    start_y = 2
    grid_width = 50
    grid_height = 30

    # When
    bounds: ViewportBounds = calculate_viewport_bounds(
        viewport,
        terminal_width,
        terminal_height,
        start_x,
        start_y,
        grid_width,
        grid_height,
    )
    viewport_start_x, viewport_start_y, visible_width, visible_height = bounds

    # Then
    assert viewport_start_x == 0  # No offset
    assert viewport_start_y == 0  # No offset
    assert visible_width == min(viewport.width, (terminal_width - start_x) // 2)
    assert visible_height == min(viewport.height, terminal_height - start_y - 2)


def test_calculate_viewport_bounds_with_offset() -> None:
    """Given viewport with offset
    When calculating viewport bounds
    Then should handle offset correctly
    """
    # Given
    viewport = ViewportState(width=40, height=25, offset_x=5, offset_y=3)
    terminal_width = 100
    terminal_height = 30
    start_x = 5
    start_y = 2
    grid_width = 50
    grid_height = 30

    # When
    bounds: ViewportBounds = calculate_viewport_bounds(
        viewport,
        terminal_width,
        terminal_height,
        start_x,
        start_y,
        grid_width,
        grid_height,
    )
    viewport_start_x, viewport_start_y, visible_width, visible_height = bounds

    # Then
    assert viewport_start_x == 5  # Offset within grid bounds
    assert viewport_start_y == 3  # Offset within grid bounds
    assert visible_width == min(viewport.width, (terminal_width - start_x) // 2)
    assert visible_height == min(viewport.height, terminal_height - start_y - 2)


def test_calculate_viewport_bounds_wrapping() -> None:
    """Given viewport offset larger than grid
    When calculating viewport bounds
    Then should wrap coordinates correctly
    """
    # Given
    viewport = ViewportState(width=40, height=25, offset_x=55, offset_y=35)
    terminal_width = 100
    terminal_height = 30
    start_x = 5
    start_y = 2
    grid_width = 50
    grid_height = 30

    # When
    bounds: ViewportBounds = calculate_viewport_bounds(
        viewport,
        terminal_width,
        terminal_height,
        start_x,
        start_y,
        grid_width,
        grid_height,
    )
    viewport_start_x, viewport_start_y, visible_width, visible_height = bounds

    # Then
    assert viewport_start_x == 55 % grid_width  # Should wrap around grid width
    assert viewport_start_y == 35 % grid_height  # Should wrap around grid height
    assert visible_width == min(viewport.width, (terminal_width - start_x) // 2)
    assert visible_height == min(viewport.height, terminal_height - start_y - 2)


def test_calculate_viewport_bounds_terminal_constraints() -> None:
    """Given viewport larger than terminal
    When calculating viewport bounds
    Then should constrain to terminal size
    """
    # Given
    viewport = ViewportState(width=100, height=50)  # Large viewport
    terminal_width = 80
    terminal_height = 24
    start_x = 5
    start_y = 2
    grid_width = 50
    grid_height = 30

    # When
    bounds: ViewportBounds = calculate_viewport_bounds(
        viewport,
        terminal_width,
        terminal_height,
        start_x,
        start_y,
        grid_width,
        grid_height,
    )
    viewport_start_x, viewport_start_y, visible_width, visible_height = bounds

    # Then
    assert visible_width == (terminal_width - start_x) // 2  # Constrained by terminal
    assert visible_height == terminal_height - start_y - 2  # Constrained by terminal
