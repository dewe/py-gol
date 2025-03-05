"""Tests for the terminal renderer module."""

import dataclasses
import re
from io import StringIO
from unittest.mock import Mock

import numpy as np
import pytest
from blessed import Terminal
from blessed.keyboard import Keystroke

from gol.grid import GridConfig, create_grid
from gol.metrics import create_metrics
from gol.patterns import PatternTransform
from gol.renderer import (
    BUILTIN_PATTERNS,
    RendererConfig,
    TerminalProtocol,
    cleanup_terminal,
    handle_resize_event,
    handle_user_input,
    initialize_terminal,
    render_grid,
    render_pattern_menu,
    render_status_line,
)
from gol.state import RendererState
from gol.types import Grid


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    ansi_escape = re.compile(
        r"(\x1b\[[0-9;]*[a-zA-Z]|\x1b\([0-9A-Z]|\x1b[@-_]|\x1b\[[0-?]*[ -/]*[@-~])"
    )
    return ansi_escape.sub("", text)


def create_mock_keystroke(name: str = "", value: str = "") -> Keystroke:
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
    key.configure_mock(__eq__=Mock(side_effect=lambda x: value == x))
    key.configure_mock(isdigit=Mock(return_value=value.isdigit() if value else False))
    return key


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
    Given: Terminal configuration
    When: Initializing terminal
    Then: Should return valid terminal and immutable state
    """
    term, state = initialize_terminal()
    try:
        assert term is not None
        assert state is not None
        assert isinstance(term, Terminal)
        assert isinstance(state, RendererState)

        # Verify state immutability
        with pytest.raises(dataclasses.FrozenInstanceError):
            state.terminal_width = 80  # type: ignore
    finally:
        if term is not None:
            cleanup_terminal(term)


def test_terminal_cleanup() -> None:
    """
    Given: Initialized terminal
    When: Cleaning up
    Then: Should restore terminal state without error
    """
    term, _ = initialize_terminal()
    try:
        assert term is not None
        cleanup_terminal(term)
    finally:
        if term is not None:
            cleanup_terminal(term)


def test_terminal_initialization_and_cleanup_cycle() -> None:
    """
    Given: Multiple terminal initializations and cleanups
    When: Running in sequence
    Then: Should handle multiple cycles without errors
    """
    for _ in range(3):  # Test multiple cycles
        term, _ = initialize_terminal()
        assert term is not None
        assert isinstance(term, Terminal)
        cleanup_terminal(term)


def test_grid_rendering() -> None:
    """Test grid rendering with known state."""
    term, state = initialize_terminal()
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
        metrics = create_metrics()
        new_state, new_metrics = render_grid(
            term, grid, RendererConfig(), state, metrics
        )

        # Assert
        assert new_state is not None
        assert new_metrics is not None
    finally:
        cleanup_terminal(term)


def test_grid_rendering_empty() -> None:
    """Test grid rendering with empty grid."""
    term, state = initialize_terminal()
    assert term is not None
    assert state is not None
    grid = create_grid(GridConfig(width=3, height=3, density=0.0))

    try:
        metrics = create_metrics()
        new_state, new_metrics = render_grid(
            term, grid, RendererConfig(), state, metrics
        )
        assert new_state is not None
        assert new_metrics is not None
    finally:
        cleanup_terminal(term)


@pytest.fixture
def term() -> TerminalProtocol:
    """Fixture providing a terminal for testing."""
    output = StringIO()
    term = Terminal(force_styling=True, stream=output)
    return term


def test_handle_user_input_quit_commands() -> None:
    """Test quit command handling."""
    config = RendererConfig()
    state = RendererState.create()

    # Test 'q' key
    key = Keystroke("q")
    result = handle_user_input(key, config, state)
    assert result == "quit"

    # Test ESC key (not in pattern mode)
    result = handle_user_input(Keystroke("\x1b"), config, state)
    assert result == "quit"

    # Test ESC key (in pattern mode)
    state = state.with_pattern_mode(True)
    result = handle_user_input(Keystroke("\x1b"), config, state)
    assert result == "exit_pattern"


def test_handle_user_input_restart_command() -> None:
    """Test restart command handling."""
    config = RendererConfig()
    state = RendererState.create()

    key = Keystroke("r")
    result = handle_user_input(key, config, state)
    assert result == "restart"


def test_handle_user_input_continue_command() -> None:
    """Test continue command handling."""
    config = RendererConfig()
    state = RendererState.create()

    key = Keystroke(" ")
    result = handle_user_input(key, config, state)
    assert result == "place_pattern"


def test_handle_user_input_interval_adjustment() -> None:
    """Test interval adjustment handling."""
    config = RendererConfig()
    state = RendererState.create()

    # Test increase interval
    key = Keystroke("KEY_UP")
    result = handle_user_input(key, config, state)
    assert result == "continue"

    # Test decrease interval
    key = Keystroke("KEY_DOWN")
    result = handle_user_input(key, config, state)
    assert result == "continue"


def test_handle_user_input_interval_limits() -> None:
    """Test interval adjustment limits."""
    config = RendererConfig()
    state = RendererState.create()

    # Test upper limit
    config.update_interval = config.max_interval
    key = Keystroke("KEY_UP")
    result = handle_user_input(key, config, state)
    assert result == "continue"

    # Test lower limit
    config.update_interval = config.min_interval
    key = Keystroke("KEY_DOWN")
    result = handle_user_input(key, config, state)
    assert result == "continue"


def test_handle_resize_event() -> None:
    """Test that resize events update terminal dimensions and clear state."""
    output = StringIO()
    terminal = Terminal(force_styling=True, stream=output, kind="xterm-256color")
    state = RendererState.create()

    # Verify initial dimensions
    assert state.terminal_width == 0
    assert state.terminal_height == 0

    # Redirect stdout to capture terminal output
    import sys

    old_stdout = sys.stdout
    sys.stdout = output

    try:
        # Handle resize
        new_state = handle_resize_event(terminal, state)

        # Verify new state has updated dimensions
        assert new_state.terminal_width == terminal.width
        assert new_state.terminal_height == terminal.height
        assert new_state.previous_grid is None
        assert new_state.previous_pattern_cells is None

        # Original state should be unchanged
        assert state.terminal_width == 0
        assert state.terminal_height == 0

        # Verify output contains expected terminal control sequences
        output_text = output.getvalue()
        assert terminal.clear() in output_text
        assert terminal.hide_cursor() in output_text
        assert terminal.move_xy(0, 0) in output_text
    finally:
        sys.stdout = old_stdout


def test_render_status_line(term: TerminalProtocol) -> None:
    """Test status line rendering."""
    config = RendererConfig()
    metrics = create_metrics()

    # Set up test metrics
    from dataclasses import replace

    from gol.metrics import GameMetrics

    metrics = replace(
        metrics,
        game=GameMetrics(
            active_cells=42,
            generation_count=100,
            birth_rate=5.0,
            death_rate=3.0,
            total_cells=100,
        ),
    )

    # Render status line and strip ANSI sequences
    status = strip_ansi(render_status_line(term, config, metrics))

    # Check that metrics values are included in output
    assert "Population: 42" in status
    assert "Generation: 100" in status
    assert "Births/s: 5.0" in status
    assert "Deaths/s: 3.0" in status


def test_render_pattern_menu(term: TerminalProtocol) -> None:
    """Test pattern menu rendering.

    Given: Pattern mode active
    When: Rendering pattern menu
    Then: Should show available patterns and controls
    """
    # Get the rendered menu
    menu_text = render_pattern_menu(term)

    # Verify menu contains expected elements
    assert "Pattern Mode" in menu_text
    assert "Select:" in menu_text
    assert "rotate" in menu_text
    assert "place" in menu_text
    assert "exit" in menu_text


def test_grid_rendering_with_patterns(term: TerminalProtocol) -> None:
    """Test grid rendering with pattern preview."""
    config = RendererConfig()
    state = RendererState.create()
    state = state.with_pattern_mode(True).with_cursor_position(5, 5)
    config.selected_pattern = list(BUILTIN_PATTERNS.keys())[0]  # Select first pattern

    grid = create_grid(GridConfig(width=20, height=20))
    metrics = create_metrics()

    new_state, new_metrics = render_grid(term, grid, config, state, metrics)
    assert new_state is not None
    assert new_metrics is not None


def test_grid_resize_handling(term: TerminalProtocol) -> None:
    """Test grid handling during resize events.

    Given: Different terminal dimensions
    When: Handling resize events
    Then: Should maintain margins and clear screen properly
    """
    state = RendererState.create()
    state = state.with_terminal_dimensions(80, 24)

    # Simulate resize event
    new_state = handle_resize_event(term, state)

    assert new_state.previous_grid is None  # Should force redraw
    assert new_state.previous_pattern_cells is None  # Should clear pattern preview
    assert new_state.terminal_width == term.width
    assert new_state.terminal_height == term.height


def test_resize_handling() -> None:
    """
    Given: Terminal instance
    When: Handling resize event
    Then: Should update dimensions and clear screen
    """
    term, _ = initialize_terminal()
    try:
        assert term is not None
        state = RendererState.create()
        new_state = handle_resize_event(term, state)
        assert new_state.terminal_width == term.width
        assert new_state.terminal_height == term.height
    finally:
        if term is not None:
            cleanup_terminal(term)


def test_render_grid_updates_metrics(term: TerminalProtocol) -> None:
    """Test that render_grid updates metrics correctly."""
    grid = np.array([[0, 1, 1], [1, 0, 0]], dtype=bool)
    config = RendererConfig()
    state = RendererState.create()
    metrics = create_metrics()

    new_state, new_metrics = render_grid(term, grid, config, state, metrics)
    assert new_metrics.game.total_cells == 6  # 2x3 grid
    assert new_metrics.game.active_cells == 3  # Three live cells


def test_immutable_renderer_state_creation() -> None:
    """Test creation of immutable renderer state.

    Given: Default immutable renderer state
    When: Creating new state
    Then: Should have expected default values
    """
    state = RendererState.create()
    assert state.start_x == 0
    assert state.start_y == 0
    assert state.terminal_width == 0
    assert state.terminal_height == 0
    assert state.pattern_mode is False
    assert state.previous_grid is None
    assert state.previous_pattern_cells is None


def test_immutable_renderer_state_updates() -> None:
    """Test immutable state updates return new instances.

    Given: An immutable renderer state
    When: Performing state updates
    Then: Should return new instances with updated values
    """
    state = RendererState.create()

    # Test grid position update
    new_state = state.with_grid_position(10, 20)
    assert new_state is not state
    assert new_state.start_x == 10
    assert new_state.start_y == 20
    assert state.start_x == 0  # Original unchanged

    # Test terminal dimensions update
    new_state = state.with_terminal_dimensions(80, 24)
    assert new_state is not state
    assert new_state.terminal_width == 80
    assert new_state.terminal_height == 24

    # Test pattern mode update
    new_state = state.with_pattern_mode(True)
    assert new_state is not state
    assert new_state.pattern_mode is True
    assert state.pattern_mode is False  # Original unchanged


def test_renderer_state_immutability() -> None:
    """Test that renderer state is immutable."""
    state = RendererState()
    with pytest.raises(dataclasses.FrozenInstanceError):
        state.terminal_width = 80  # type: ignore


def test_state_update_methods() -> None:
    """Test state update methods."""
    state = RendererState()
    new_state = state.with_terminal_dimensions(80, 24)
    assert new_state.terminal_width == 80
    assert new_state.terminal_height == 24
    assert state.terminal_width == 0  # Original unchanged


def test_state_chained_updates() -> None:
    """Test chained state updates."""
    state = RendererState()
    new_state = (
        state.with_terminal_dimensions(80, 24)
        .with_grid_position(10, 5)
        .with_pattern_mode(True)
    )
    assert new_state.terminal_width == 80
    assert new_state.terminal_height == 24
    assert new_state.start_x == 10
    assert new_state.start_y == 5
    assert new_state.pattern_mode is True


def test_state_grid_updates() -> None:
    """Test grid state updates."""
    state = RendererState()
    grid = {(0, 0): True, (1, 1): False}
    new_state = state.with_previous_grid(grid)
    assert new_state.previous_grid == grid
    assert state.previous_grid is None  # Original unchanged


def test_render_grid(
    mock_terminal: TerminalProtocol,
    mock_grid: Grid,
    mock_config: RendererConfig,
    mock_state: RendererState,
) -> None:
    """Test grid rendering."""
    metrics = create_metrics()
    state, new_metrics = render_grid(
        mock_terminal, mock_grid, mock_config, mock_state, metrics
    )
    mock_terminal.clear.assert_called_once()  # type: ignore


def test_render_grid_with_pattern_cells(
    mock_terminal: TerminalProtocol,
    mock_grid: Grid,
    mock_config: RendererConfig,
    mock_state: RendererState,
) -> None:
    """Test grid rendering with pattern cells."""
    pattern_cells = {(1, 1), (1, 2), (2, 1), (2, 2)}
    state = mock_state.with_pattern_cells(pattern_cells)
    metrics = create_metrics()
    new_state, new_metrics = render_grid(
        mock_terminal, mock_grid, mock_config, state, metrics
    )
    assert new_state is not None
    assert new_metrics is not None


@pytest.fixture
def mock_terminal() -> TerminalProtocol:
    """Create a mock terminal for testing."""
    terminal = Mock()
    terminal.width = 80
    terminal.height = 24
    terminal.clear = Mock(return_value="")
    terminal.move_xy = Mock(return_value="")
    terminal.black = Mock(return_value="")
    terminal.white = Mock(return_value="")
    terminal.on_black = Mock(return_value="")
    terminal.on_white = Mock(return_value="")
    terminal.yellow = ""
    terminal.blue = ""
    terminal.dim = ""
    terminal.normal = ""
    return terminal


@pytest.fixture
def mock_grid() -> Grid:
    """Create a mock grid for testing."""
    return np.zeros((10, 10), dtype=np.bool_)


@pytest.fixture
def mock_config() -> RendererConfig:
    """Create a mock renderer config for testing."""
    return RendererConfig(
        update_interval=100,
        selected_pattern=None,
        pattern_rotation=PatternTransform.NONE,
    )


@pytest.fixture
def mock_state() -> RendererState:
    """Create a mock renderer state for testing."""
    return RendererState()


def test_initialize_terminal() -> None:
    """Test terminal initialization."""
    terminal, state = initialize_terminal()
    assert terminal is not None
    assert state is not None


def test_cleanup_terminal() -> None:
    """Test terminal cleanup."""
    terminal = Mock()
    cleanup_terminal(terminal)
    terminal.clear.assert_called_once()


def test_handle_user_input_quit(
    mock_terminal: TerminalProtocol,
    mock_config: RendererConfig,
    mock_state: RendererState,
) -> None:
    """Test handling quit command."""
    key = Mock()
    key.name = "q"
    command = handle_user_input(key, mock_config, mock_state)
    assert command == "quit"


def test_handle_user_input_pattern_mode(
    mock_terminal: TerminalProtocol,
    mock_config: RendererConfig,
    mock_state: RendererState,
) -> None:
    """Test handling pattern mode command."""
    key = Mock()
    key.name = "p"
    command = handle_user_input(key, mock_config, mock_state)
    assert command == "pattern"


def test_handle_user_input_cursor_movement(
    mock_terminal: TerminalProtocol,
    mock_config: RendererConfig,
    mock_state: RendererState,
) -> None:
    """Test handling cursor movement commands."""
    state = mock_state.with_pattern_mode(True)  # Must be in pattern mode
    key = create_mock_keystroke(name="KEY_LEFT")
    command = handle_user_input(key, mock_config, state)
    assert command == "move_cursor_left"


def test_handle_user_input_pattern_placement(
    mock_terminal: TerminalProtocol,
    mock_config: RendererConfig,
    mock_state: RendererState,
) -> None:
    """Test handling pattern placement command."""
    key = create_mock_keystroke(name="KEY_SPACE", value=" ")
    command = handle_user_input(key, mock_config, mock_state)
    assert command == "place_pattern"


def test_handle_user_input_pattern_rotation(
    mock_terminal: TerminalProtocol,
    mock_config: RendererConfig,
    mock_state: RendererState,
) -> None:
    """Test handling pattern rotation command."""
    state = mock_state.with_pattern_mode(True)  # Must be in pattern mode
    key = create_mock_keystroke(name="r", value="r")
    command = handle_user_input(key, mock_config, state)
    assert command == "rotate_pattern"


def test_handle_user_input_resize(
    mock_terminal: TerminalProtocol,
    mock_config: RendererConfig,
    mock_state: RendererState,
) -> None:
    """Test handling resize commands."""
    key = create_mock_keystroke(name="KEY_PLUS", value="+")
    command = handle_user_input(key, mock_config, mock_state)
    assert command == "resize_larger"


def test_handle_user_input_exit_pattern_mode(
    mock_terminal: TerminalProtocol,
    mock_config: RendererConfig,
    mock_state: RendererState,
) -> None:
    """Test handling exit pattern mode command."""
    state = mock_state.with_pattern_mode(True)  # Must be in pattern mode
    key = create_mock_keystroke(name="KEY_ESCAPE", value="\x1b")
    command = handle_user_input(key, mock_config, state)
    assert command == "exit_pattern"


def test_handle_user_input_invalid_key(
    mock_terminal: TerminalProtocol,
    mock_config: RendererConfig,
    mock_state: RendererState,
) -> None:
    """Test handling invalid key."""
    key = create_mock_keystroke(name="invalid", value="x")
    command = handle_user_input(key, mock_config, mock_state)
    assert command == "continue"  # Invalid keys should return 'continue'
