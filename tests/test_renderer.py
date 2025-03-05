"""Tests for the terminal renderer module."""

import re
import time
from io import StringIO

import pytest
from blessed import Terminal
from blessed.keyboard import Keystroke

from gol.grid import GridConfig, create_grid
from gol.renderer import (
    BUILTIN_PATTERNS,
    RendererConfig,
    RendererState,
    TerminalProtocol,
    cleanup_terminal,
    handle_resize_event,
    handle_user_input,
    initialize_terminal,
    render_grid,
    render_pattern_menu,
    render_status_line,
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
    """Fixture providing a terminal for testing."""
    output = StringIO()
    term = Terminal(force_styling=True, stream=output)
    return term


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


def strip_ansi(text: str) -> str:
    """Strip ANSI escape sequences from text.

    Args:
        text: Text containing ANSI escape sequences

    Returns:
        Text with ANSI escape sequences removed
    """
    # Handle both standard ANSI escapes and blessed's special sequences
    ansi_escape = re.compile(r"(\x1b\[[0-9;]*[a-zA-Z]|\x1b\([0-9A-Z]|\x1b[@-_])")
    return ansi_escape.sub("", text)


def test_render_status_line(term: TerminalProtocol) -> None:
    """Test status line rendering with real Terminal instance."""
    config = RendererConfig()
    state = RendererState()
    state.active_cells = 42
    state.generation_count = 100
    state.birth_rate = 5.0
    state.death_rate = 3.0
    # Set last_stats_update to current time to prevent stats reset
    state.last_stats_update = time.time()

    # Get the rendered status line and strip ANSI sequences
    status_text = strip_ansi(render_status_line(term, config, state))

    # Verify content
    assert "Population: 42" in status_text
    assert "Generation: 100" in status_text
    assert "Births/s: 5.0" in status_text
    assert "Deaths/s: 3.0" in status_text


def test_render_pattern_menu(term: TerminalProtocol) -> None:
    """Test pattern menu rendering.

    Given: Pattern mode active
    When: Rendering pattern menu
    Then: Should show available patterns and controls
    """
    config = RendererConfig()
    state = RendererState()
    state.pattern_mode = True

    # Get the rendered menu
    menu_text = render_pattern_menu(term, config, state)

    # Verify content
    assert "Pattern Mode" in menu_text
    assert "rotate" in menu_text
    assert "place" in menu_text
    assert "exit" in menu_text


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

    render_grid(term, grid, config, state)
    assert state.previous_pattern_cells is not None


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
