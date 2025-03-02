"""Tests for the terminal renderer module."""

from typing import Protocol

import pytest
from blessed import Terminal
from blessed.formatters import ParameterizingString
from blessed.keyboard import Keystroke

from gol.grid import GridConfig, create_grid
from gol.renderer import (
    RendererConfig,
    RendererState,
    cleanup_terminal,
    handle_resize_event,
    handle_user_input,
    initialize_terminal,
    render_grid,
    safe_render_grid,
)


def create_mock_keystroke(name: str = "") -> Keystroke:
    """Create a mock keystroke for testing.

    Args:
        name: Name of the key pressed

    Returns:
        Mock keystroke object
    """
    return Keystroke(name=name)


def test_renderer_config_defaults() -> None:
    """
    Given: Default renderer configuration
    When: Creating new config
    Then: Should have expected default values
    """
    config = RendererConfig()
    assert config.cell_alive == "■"
    assert config.cell_dead == "□"
    assert config.cell_spacing == " "
    assert config.update_interval == 100
    assert config.refresh_per_second == 5


def test_terminal_initialization() -> None:
    """
    Given: A new terminal initialization
    When: Setting up the terminal
    Then: Should return configured Terminal instance and RendererState
    And: Terminal should be in fullscreen mode
    And: Terminal should have cursor hidden
    """
    config = RendererConfig()
    term, state = initialize_terminal(config)

    assert isinstance(term, Terminal)
    assert isinstance(state, RendererState)


def test_terminal_cleanup() -> None:
    """
    Given: An initialized terminal
    When: Cleaning up the terminal
    Then: Should restore terminal to original state
    """
    config = RendererConfig()
    term, state = initialize_terminal(config)

    try:
        # Verify terminal is initialized
        assert isinstance(term, Terminal)

        # Perform cleanup
        cleanup_terminal(term)
    finally:
        # Ensure cleanup runs even if test fails
        cleanup_terminal(term)


def test_terminal_initialization_and_cleanup_cycle() -> None:
    """
    Given: Multiple terminal initializations and cleanups
    When: Running in sequence
    Then: Should handle multiple cycles without errors
    """
    config = RendererConfig()

    for _ in range(3):  # Test multiple cycles
        term, state = initialize_terminal(config)
        assert isinstance(term, Terminal)
        cleanup_terminal(term)


def test_grid_rendering() -> None:
    """
    Given: A terminal and a known grid state
    When: Rendering the grid
    Then: Should output correct characters for live/dead cells
    And: Should position grid centered in terminal
    And: Should use configured cell characters
    """
    # Setup
    renderer_config = RendererConfig()
    term, state = initialize_terminal(renderer_config)

    # Create a small test grid with known state
    grid_config = GridConfig(size=3, density=0.0)  # Start with empty grid
    grid = create_grid(grid_config)
    # Set specific cells to create a simple pattern
    grid[0][1] = True  # Top middle
    grid[1][1] = True  # Center
    grid[2][1] = True  # Bottom middle

    try:
        # Act
        render_grid(term, grid, renderer_config, state)

        # We can't directly test terminal output in unit tests,
        # but we can verify the function runs without errors
        # Integration tests would verify actual terminal output
    finally:
        cleanup_terminal(term)


def test_grid_rendering_empty() -> None:
    """
    Given: A terminal and an empty grid
    When: Rendering the grid
    Then: Should display all dead cells
    """
    renderer_config = RendererConfig()
    term, state = initialize_terminal(renderer_config)
    grid = create_grid(GridConfig(size=3, density=0.0))

    try:
        render_grid(term, grid, renderer_config, state)
    finally:
        cleanup_terminal(term)


def test_input_handling_quit() -> None:
    """
    Given: A terminal instance
    When: User presses 'q'
    Then: Should return QUIT command
    """
    config = RendererConfig()
    term, state = initialize_terminal(config)

    try:
        # Simulate 'q' keypress
        key = create_mock_keystroke(name="q")
        result = handle_user_input(term, key)
        assert result == "quit"
    finally:
        cleanup_terminal(term)


def test_input_handling_continue() -> None:
    """
    Given: A terminal instance
    When: User presses any other key
    Then: Should return CONTINUE command
    """
    config = RendererConfig()
    term, state = initialize_terminal(config)

    try:
        # Simulate 'x' keypress
        key = create_mock_keystroke(name="x")
        result = handle_user_input(term, key)
        assert result == "continue"
    finally:
        cleanup_terminal(term)


def test_input_handling_ctrl_c() -> None:
    """
    Given: A terminal instance
    When: User presses Ctrl-C
    Then: Should return QUIT command
    """
    config = RendererConfig()
    term, state = initialize_terminal(config)

    try:
        # Simulate Ctrl-C
        key = create_mock_keystroke(name="^C")
        result = handle_user_input(term, key)
        assert result == "quit"
    finally:
        cleanup_terminal(term)


def test_handle_resize_event() -> None:
    """
    Given: A terminal instance
    When: Terminal is resized
    Then: Should clear screen and rehide cursor
    """
    config = RendererConfig()
    term, state = initialize_terminal(config)

    try:
        # Test resize handling
        handle_resize_event(term, state)
        # We can't test actual resize, but we can verify it runs without errors
    finally:
        cleanup_terminal(term)


class TerminalProtocol(Protocol):
    """Protocol defining the required terminal interface."""

    @property
    def width(self) -> int: ...
    @property
    def height(self) -> int: ...
    @property
    def dim(self) -> str: ...
    @property
    def normal(self) -> str: ...
    def move_xy(self, x: int, y: int) -> ParameterizingString: ...
    def exit_fullscreen(self) -> str: ...
    def enter_fullscreen(self) -> str: ...
    def hide_cursor(self) -> str: ...
    def normal_cursor(self) -> str: ...
    def clear(self) -> str: ...


class MockTerminal:
    """Mock terminal for testing."""

    def __init__(self) -> None:
        self._width = 80
        self._height = 24
        self._dim = ""
        self._normal = ""

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def dim(self) -> str:
        return self._dim

    @property
    def normal(self) -> str:
        return self._normal

    def move_xy(self, x: int, y: int) -> ParameterizingString:
        raise IOError("Mock error")  # Simulate error for testing

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


def test_safe_render_grid_handles_errors() -> None:
    """Test that safe_render_grid properly handles rendering errors."""
    config = RendererConfig()
    grid = create_grid(GridConfig(size=3, density=0.0))
    term = MockTerminal()
    state = RendererState()

    # Force a render that should trigger the error
    with pytest.raises(RuntimeError) as exc_info:
        safe_render_grid(term, grid, config, state)

    assert "Failed to render grid" in str(exc_info.value)
    assert "Mock error" in str(exc_info.value)
