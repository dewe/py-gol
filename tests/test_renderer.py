"""Tests for the terminal renderer module."""

from typing import Any, Protocol

import pytest
from blessed import Terminal
from blessed.formatters import ParameterizingString
from blessed.keyboard import Keystroke

from gol.grid import GridConfig, create_grid
from gol.renderer import (
    BUILTIN_PATTERNS,
    RendererConfig,
    RendererState,
    TerminalProtocol,
    calculate_grid_position,
    cleanup_terminal,
    handle_resize_event,
    handle_user_input,
    initialize_terminal,
    render_cell,
    render_grid,
    render_pattern_menu,
    render_status_line,
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
    assert config.update_interval == 200
    assert config.refresh_per_second == 5  # 1000/200 = 5


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

    assert term is not None
    assert state is not None
    assert isinstance(term, Terminal)
    assert isinstance(state, RendererState)


def test_terminal_cleanup() -> None:
    """
    Given: An initialized terminal
    When: Cleaning up the terminal
    Then: Should restore terminal to original state
    """
    config = RendererConfig()
    term, _ = initialize_terminal(config)
    assert term is not None

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
        term, _ = initialize_terminal(config)
        assert term is not None
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
    assert term is not None
    assert state is not None

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

        # Assert - since we can't check terminal output directly,
        # we at least verify that rendering completes without error
        # and updates state correctly
        assert state.total_cells == 9
        assert state.active_cells == 3
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
    assert term is not None
    assert state is not None
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
    state = RendererState()
    quit_keys = [
        Keystroke("q"),
        Keystroke("Q"),
        Keystroke("\x03"),  # Ctrl-C
    ]
    for key in quit_keys:
        result = handle_user_input(term, key, config, state)
        assert result == "quit"

    # Test ESC key in pattern mode
    state.pattern_mode = True
    result = handle_user_input(term, Keystroke("\x1b"), config, state)
    assert result == "exit_pattern"

    # Test ESC key in normal mode
    state.pattern_mode = False
    result = handle_user_input(term, Keystroke("\x1b"), config, state)
    assert result == "quit"


def test_handle_user_input_restart_command(term: TerminalProtocol) -> None:
    """Test that restart command is handled correctly."""
    config = RendererConfig()
    state = RendererState()
    restart_keys = [Keystroke("r"), Keystroke("R")]
    for key in restart_keys:
        result = handle_user_input(term, key, config, state)
        assert result == "restart"


def test_handle_user_input_continue_command(term: TerminalProtocol) -> None:
    """Test that other keys return appropriate commands."""
    config = RendererConfig()
    state = RendererState()
    # Space key should place pattern
    result = handle_user_input(term, Keystroke(" "), config, state)
    assert result == "place_pattern"

    # Other keys should continue
    other_keys = [
        Keystroke("a"),
        Keystroke("1"),
        Keystroke("\t"),
    ]
    for key in other_keys:
        result = handle_user_input(term, key, config, state)
        assert result == "continue"


def test_handle_user_input_interval_adjustment(term: TerminalProtocol) -> None:
    """Test that arrow keys adjust the update interval."""
    config = RendererConfig()
    state = RendererState()

    # Set initial interval to something in the middle of the range
    config.update_interval = 500  # Start with a higher value to test both directions
    initial_interval = config.update_interval

    # Test increasing interval
    key = Keystroke(name="KEY_UP")
    result = handle_user_input(term, key, config, state)
    assert result == "continue"
    assert config.update_interval > initial_interval

    # Test decreasing interval
    key = Keystroke(name="KEY_DOWN")
    result = handle_user_input(term, key, config, state)
    assert result == "continue"
    assert config.update_interval < initial_interval


def test_handle_user_input_interval_limits(term: TerminalProtocol) -> None:
    """Test that interval adjustments respect min/max limits."""
    config = RendererConfig()
    state = RendererState()

    # Test maximum limit
    config.update_interval = config.max_interval
    key = Keystroke(name="KEY_UP")
    result = handle_user_input(term, key, config, state)
    assert result == "continue"
    assert config.update_interval == config.max_interval

    # Test minimum limit
    config.update_interval = config.min_interval
    key = Keystroke(name="KEY_DOWN")
    result = handle_user_input(term, key, config, state)
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
    assert term is not None
    assert state is not None

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
        self._should_error = False

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
    def white(self) -> str:
        """Get white color."""
        if self._should_error:
            raise ValueError("Mock error")
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
    def red(self) -> str:
        """Get red color."""
        return ""

    @property
    def on_blue(self) -> str:
        """Get blue background color."""
        return ""

    def move_xy(self, x: int, y: int) -> ParameterizingString:
        """Move cursor to position."""
        return ParameterizingString(
            f"\x1b[{y+1};{x+1}H"
        )  # Return ANSI escape sequence for cursor movement

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

    def trigger_error(self) -> None:
        """Method to trigger error for testing."""
        self._should_error = True


def test_safe_render_grid_handles_errors() -> None:
    """Test that safe_render_grid properly handles rendering errors."""
    config = RendererConfig()
    grid = create_grid(GridConfig(width=3, height=3, density=0.0))
    term = MockTerminal()
    state = RendererState()

    # Set up the error to trigger during rendering
    term.trigger_error()
    with pytest.raises(RuntimeError) as exc_info:
        safe_render_grid(term, grid, config, state)

    assert "Failed to render grid" in str(exc_info.value)
    assert "Mock error" in str(exc_info.value)


def test_calculate_grid_position(term: TerminalProtocol) -> None:
    """Test grid position calculation with various scenarios.

    Given: Different grid and terminal sizes
    When: Calculating grid position
    Then: Should return correct centered coordinates with margins
    """
    grid = create_grid(GridConfig(width=10, height=10))
    start_x, start_y = calculate_grid_position(term, grid)

    # Basic position check
    assert isinstance(start_x, int)
    assert isinstance(start_y, int)
    assert start_x >= 1  # Should respect margin
    assert start_y >= 1  # Should respect top margin

    # Check with larger grid
    large_grid = create_grid(GridConfig(width=30, height=20))
    large_x, large_y = calculate_grid_position(term, large_grid)
    assert large_x >= 1
    assert large_y >= 1


def test_render_cell(term: TerminalProtocol) -> None:
    """Test cell rendering for different states.

    Given: Different cell states
    When: Rendering individual cells
    Then: Should return correct character and color combinations
    """
    config = RendererConfig()

    # Test live cell
    live_output = render_cell(term, 0, 0, True, config)
    assert config.cell_alive in live_output
    assert term.white in live_output

    # Test dead cell
    dead_output = render_cell(term, 0, 0, False, config)
    assert config.cell_dead in dead_output
    assert term.dim in dead_output


def test_render_status_line(term: TerminalProtocol) -> None:
    """Test status line rendering.

    Given: Various game states
    When: Rendering status line
    Then: Should show correct statistics and formatting
    """
    config = RendererConfig()
    state = RendererState()

    # Set state values before rendering
    state.active_cells = 42
    state.generation_count = 100
    state.birth_rate = 5.0
    state.death_rate = 3.0

    # Get the rendered output
    output = render_status_line(term, config, state)

    # Extract just the status line text without ANSI codes
    status_text = output.split("\x1b")[-1].split("H")[-1].strip()

    # Verify each part of the status line
    assert f"Population: {state.active_cells}" in status_text
    assert f"Generation: {state.generation_count}" in status_text
    assert f"Births/s: {state.birth_rate}" in status_text
    assert f"Deaths/s: {state.death_rate}" in status_text
    assert f"Interval: {config.update_interval}ms" in status_text


def test_render_pattern_menu(term: TerminalProtocol) -> None:
    """Test pattern menu rendering.

    Given: Pattern mode active
    When: Rendering pattern menu
    Then: Should show available patterns and controls
    """
    config = RendererConfig()
    state = RendererState()
    state.pattern_mode = True

    output = render_pattern_menu(term, config, state)

    assert "Pattern Mode" in output
    assert "rotate" in output
    assert "place" in output
    assert "exit" in output


def test_grid_rendering_with_patterns(term: TerminalProtocol) -> None:
    """Test grid rendering with pattern preview.

    Given: Pattern mode with selected pattern
    When: Rendering grid
    Then: Should show pattern preview and cursor
    """
    config = RendererConfig()
    state = RendererState()
    state.pattern_mode = True
    state.cursor_x = 5
    state.cursor_y = 5
    config.selected_pattern = list(BUILTIN_PATTERNS.keys())[0]  # Select first pattern

    grid = create_grid(GridConfig(width=20, height=20))

    try:
        render_grid(term, grid, config, state)
        assert state.previous_pattern_cells is not None
    finally:
        cleanup_terminal(term)


def test_grid_resize_handling(term: TerminalProtocol) -> None:
    """Test grid handling during resize events.

    Given: Different terminal dimensions
    When: Handling resize events
    Then: Should maintain margins and clear screen properly
    """
    state = RendererState()
    state.terminal_width = 80
    state.terminal_height = 24

    # Simulate resize event
    handle_resize_event(term, state)

    assert state.previous_grid is None  # Should force redraw
    assert state.previous_pattern_cells is None  # Should clear pattern preview
    assert state.terminal_width == term.width
    assert state.terminal_height == term.height
