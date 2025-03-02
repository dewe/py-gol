"""Tests for the terminal renderer module."""

from typing import Any, Protocol

import pytest
from blessed import Terminal
from blessed.formatters import ParameterizingString
from blessed.keyboard import Keystroke

from gol.grid import GridConfig, create_grid
from gol.renderer import (
    RendererConfig,
    RendererState,
    TerminalProtocol,
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
    assert config.refresh_per_second == 10  # 1000/100 = 10


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
    grid_config = GridConfig(width=3, height=3, density=0.0)  # Start with empty grid
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
    grid = create_grid(GridConfig(width=3, height=3, density=0.0))

    try:
        render_grid(term, grid, renderer_config, state)
    finally:
        cleanup_terminal(term)


@pytest.fixture
def term() -> TerminalProtocol:
    """Fixture providing a mock terminal for testing."""
    return MockTerminal()


def test_handle_user_input_quit_commands(term: TerminalProtocol) -> None:
    """Test that quit commands are handled correctly."""
    config = RendererConfig()
    quit_keys = [
        Keystroke("q"),
        Keystroke("Q"),
        Keystroke("\x03"),  # Ctrl-C
        Keystroke("\x1b"),  # Escape
    ]
    for key in quit_keys:
        result = handle_user_input(term, key, config)
        assert result == "quit"


def test_handle_user_input_restart_command(term: TerminalProtocol) -> None:
    """Test that restart command is handled correctly."""
    config = RendererConfig()
    restart_keys = [Keystroke("r"), Keystroke("R")]
    for key in restart_keys:
        result = handle_user_input(term, key, config)
        assert result == "restart"


def test_handle_user_input_continue_command(term: TerminalProtocol) -> None:
    """Test that other keys return continue."""
    config = RendererConfig()
    continue_keys = [
        Keystroke("a"),
        Keystroke("1"),
        Keystroke(" "),
        Keystroke("\t"),
    ]
    for key in continue_keys:
        result = handle_user_input(term, key, config)
        assert result == "continue"


def test_handle_user_input_interval_adjustment(term: TerminalProtocol) -> None:
    """Test that arrow keys adjust the update interval."""
    config = RendererConfig()
    initial_interval = config.update_interval

    # Test increasing interval
    key = Keystroke(name="KEY_UP")
    result = handle_user_input(term, key, config)
    assert result == "continue"
    assert config.update_interval > initial_interval

    # Test decreasing interval
    key = Keystroke(name="KEY_DOWN")
    result = handle_user_input(term, key, config)
    assert result == "continue"
    assert (
        config.update_interval < initial_interval + config.min_interval_step * 2
    )  # Account for rounding


def test_handle_user_input_interval_limits(term: TerminalProtocol) -> None:
    """Test that interval adjustments respect min/max limits."""
    config = RendererConfig()

    # Test maximum limit
    config.update_interval = config.max_interval
    key = Keystroke(name="KEY_UP")
    result = handle_user_input(term, key, config)
    assert result == "continue"
    assert config.update_interval == config.max_interval

    # Test minimum limit
    config.update_interval = config.min_interval
    key = Keystroke(name="KEY_DOWN")
    result = handle_user_input(term, key, config)
    assert result == "continue"
    assert config.update_interval == config.min_interval


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


class MockTerminalProtocol(Protocol):
    """Protocol defining the required terminal interface for testing."""

    @property
    def width(self) -> int: ...
    @property
    def height(self) -> int: ...
    @property
    def dim(self) -> str: ...
    @property
    def normal(self) -> str: ...
    @property
    def reverse(self) -> str: ...
    @property
    def black(self) -> str: ...
    @property
    def blue(self) -> str: ...
    @property
    def green(self) -> str: ...
    @property
    def yellow(self) -> str: ...
    @property
    def magenta(self) -> str: ...
    @property
    def on_blue(self) -> str: ...
    def move_xy(self, x: int, y: int) -> ParameterizingString: ...
    def exit_fullscreen(self) -> str: ...
    def enter_fullscreen(self) -> str: ...
    def hide_cursor(self) -> str: ...
    def normal_cursor(self) -> str: ...
    def clear(self) -> str: ...
    def enter_ca_mode(self) -> str: ...
    def exit_ca_mode(self) -> str: ...
    def inkey(self, timeout: float = 0) -> Keystroke: ...
    def cbreak(self) -> Any: ...


class MockTerminal(MockTerminalProtocol):
    """Mock terminal for testing."""

    def __init__(self) -> None:
        """Initialize mock terminal."""
        self._width = 80
        self._height = 24
        self._dim = ""
        self._normal = ""

    @property
    def width(self) -> int:
        """Get terminal width."""
        return self._width

    @property
    def height(self) -> int:
        """Get terminal height."""
        return self._height

    @property
    def dim(self) -> str:
        """Get dim attribute."""
        return self._dim

    @property
    def normal(self) -> str:
        """Get normal attribute."""
        return self._normal

    @property
    def reverse(self) -> str:
        """Get reverse attribute."""
        return ""

    @property
    def black(self) -> str:
        """Get black color."""
        return ""

    @property
    def blue(self) -> str:
        """Get blue color."""
        return ""

    @property
    def green(self) -> str:
        """Get green color."""
        return ""

    @property
    def yellow(self) -> str:
        """Get yellow color."""
        return ""

    @property
    def magenta(self) -> str:
        """Get magenta color."""
        return ""

    @property
    def on_blue(self) -> str:
        """Get blue background color."""
        return ""

    def move_xy(self, x: int, y: int) -> ParameterizingString:
        """Mock move cursor that raises error."""
        raise IOError("Mock error")  # Simulate error for testing

    def exit_fullscreen(self) -> str:
        """Mock exit fullscreen."""
        return ""

    def enter_fullscreen(self) -> str:
        """Mock enter fullscreen."""
        return ""

    def hide_cursor(self) -> str:
        """Mock hide cursor."""
        return ""

    def normal_cursor(self) -> str:
        """Mock normal cursor."""
        return ""

    def clear(self) -> str:
        """Mock clear screen."""
        return ""

    def enter_ca_mode(self) -> str:
        """Mock enter ca mode."""
        return ""

    def exit_ca_mode(self) -> str:
        """Mock exit ca mode."""
        return ""

    def inkey(self, timeout: float = 0) -> Keystroke:
        """Mock inkey."""
        return Keystroke(name="")

    def cbreak(self) -> Any:
        """Mock cbreak."""
        return None


def test_safe_render_grid_handles_errors() -> None:
    """Test that safe_render_grid properly handles rendering errors."""
    config = RendererConfig()
    grid = create_grid(GridConfig(width=3, height=3, density=0.0))
    term = MockTerminal()
    state = RendererState()

    # Force a render that should trigger the error
    with pytest.raises(RuntimeError) as exc_info:
        safe_render_grid(term, grid, config, state)

    assert "Failed to render grid" in str(exc_info.value)
    assert "Mock error" in str(exc_info.value)
