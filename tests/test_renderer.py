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


def test_handle_user_input_quit_command(
    mock_terminal: TerminalProtocol,
    mock_config: RendererConfig,
    mock_state: RendererState,
) -> None:
    """Test quit command handling."""
    key = create_mock_keystroke("q")
    result = handle_user_input(key, mock_config, mock_state)
    assert result[0] == "quit"


def test_handle_user_input_pattern_mode_command(
    mock_terminal: TerminalProtocol,
    mock_config: RendererConfig,
    mock_state: RendererState,
) -> None:
    """Test pattern mode command handling."""
    key = create_mock_keystroke("p")
    result = handle_user_input(key, mock_config, mock_state)
    assert result[0] == "pattern"


def test_handle_user_input_cursor_movement_command(
    mock_terminal: TerminalProtocol,
    mock_config: RendererConfig,
    mock_state: RendererState,
) -> None:
    """Test cursor movement command handling."""
    state = mock_state.with_pattern_mode(True)
    key = create_mock_keystroke(name="KEY_LEFT")
    result = handle_user_input(key, mock_config, state)
    assert result[0] == "move_cursor_left"


def test_handle_user_input_pattern_placement_command(
    mock_terminal: TerminalProtocol,
    mock_config: RendererConfig,
    mock_state: RendererState,
) -> None:
    """Test pattern placement command handling."""
    state = mock_state.with_pattern_mode(True)
    config = mock_config.with_pattern("glider")  # Must have a pattern selected
    key = create_mock_keystroke(" ")
    result = handle_user_input(key, config, state)
    assert result[0] == "continue"  # Command is handled by game loop
    assert result[1] is config  # Config remains unchanged


def test_handle_user_input_pattern_rotation_command(
    mock_terminal: TerminalProtocol,
    mock_config: RendererConfig,
    mock_state: RendererState,
) -> None:
    """Test pattern rotation command handling."""
    state = mock_state.with_pattern_mode(True)
    key = create_mock_keystroke("r")
    result = handle_user_input(key, mock_config, state)
    assert result[0] == "rotate_pattern"


def test_handle_user_input_resize_command(
    mock_terminal: TerminalProtocol,
    mock_config: RendererConfig,
    mock_state: RendererState,
) -> None:
    """Test resize command handling."""
    key = create_mock_keystroke("+")
    result = handle_user_input(key, mock_config, mock_state)
    assert result[0] == "continue"  # Command is handled by game loop
    assert result[1] is mock_config  # Config remains unchanged


def test_handle_user_input_exit_pattern_mode_command(
    mock_terminal: TerminalProtocol,
    mock_config: RendererConfig,
    mock_state: RendererState,
) -> None:
    """Test exit pattern mode command handling."""
    state = mock_state.with_pattern_mode(True)
    key = create_mock_keystroke(name="KEY_ESCAPE")
    result = handle_user_input(key, mock_config, state)
    assert result[0] == "exit_pattern"


def test_handle_user_input_invalid_key_command(
    mock_terminal: TerminalProtocol,
    mock_config: RendererConfig,
    mock_state: RendererState,
) -> None:
    """Test invalid key command handling."""
    key = create_mock_keystroke("x")  # Invalid key
    result = handle_user_input(key, mock_config, mock_state)
    assert result[0] == "continue"


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
    config = config.with_pattern(
        list(BUILTIN_PATTERNS.keys())[0]
    )  # Select first pattern
    state = RendererState.create()
    state = state.with_pattern_mode(True).with_cursor_position(5, 5)

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

    _, new_metrics = render_grid(term, grid, config, state, metrics)
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
    test_grid: Grid,  # Use test_grid from conftest
    mock_config: RendererConfig,
    mock_state: RendererState,
) -> None:
    """Test grid rendering."""
    metrics = create_metrics()
    render_grid(mock_terminal, test_grid, mock_config, mock_state, metrics)
    mock_terminal.clear.assert_called_once()  # type: ignore


def test_render_grid_with_pattern_cells(
    mock_terminal: TerminalProtocol,
    test_grid: Grid,  # Use test_grid from conftest
    mock_config: RendererConfig,
    mock_state: RendererState,
) -> None:
    """Test grid rendering with pattern cells."""
    pattern_cells = {(1, 1), (1, 2), (2, 1), (2, 2)}
    state = mock_state.with_pattern_cells(pattern_cells)
    metrics = create_metrics()
    new_state, new_metrics = render_grid(
        mock_terminal, test_grid, mock_config, state, metrics
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


def test_handle_user_input_restart_command() -> None:
    """Test restart command handling."""
    config = RendererConfig()
    state = RendererState.create()

    key = Keystroke("r")
    command, new_config = handle_user_input(key, config, state)
    assert command == "restart"
    assert new_config is config  # Config unchanged


def test_handle_user_input_continue_command() -> None:
    """Test continue command handling."""
    config = RendererConfig()
    state = RendererState.create()

    key = Keystroke(" ")
    command, new_config = handle_user_input(key, config, state)
    assert command == "place_pattern"
    assert new_config is config  # Config unchanged


def test_handle_user_input_interval_adjustment() -> None:
    """Test interval adjustment handling."""
    config = RendererConfig(update_interval=100)  # Start with lower interval
    state = RendererState.create()

    # Test increase interval
    key = Keystroke("KEY_UP")
    command, new_config = handle_user_input(key, config, state)
    assert command == "continue"
    assert isinstance(new_config, RendererConfig)
    assert new_config.update_interval == 100  # Interval is updated in game loop

    # Test decrease interval
    key = Keystroke("KEY_DOWN")
    command, new_config = handle_user_input(key, config, state)
    assert command == "continue"
    assert isinstance(new_config, RendererConfig)
    assert new_config.update_interval == 100  # Interval is updated in game loop


def test_handle_user_input_interval_limits() -> None:
    """Test interval adjustment limits."""
    # Test upper limit
    config = RendererConfig(update_interval=RendererConfig().max_interval)
    state = RendererState.create()
    key = Keystroke("KEY_UP")
    command, new_config = handle_user_input(key, config, state)
    assert command == "continue"
    assert new_config.update_interval == config.max_interval  # Cannot exceed max

    # Test lower limit
    config = RendererConfig(update_interval=RendererConfig().min_interval)
    key = Keystroke("KEY_DOWN")
    command, new_config = handle_user_input(key, config, state)
    assert command == "continue"
    assert new_config.update_interval == config.min_interval  # Cannot go below min


def test_renderer_config_immutability() -> None:
    """Test that RendererConfig is immutable."""
    config = RendererConfig()

    # Verify that attempting to modify attributes raises FrozenInstanceError
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.update_interval = 100  # type: ignore

    # Verify original values remain unchanged
    assert config.update_interval == 200  # Default value
    assert config.refresh_per_second == 5  # 1000/200 = 5


def test_renderer_config_interval_updates() -> None:
    """Test that interval updates return new instances."""
    config = RendererConfig()
    original_interval = config.update_interval

    # Test increase
    new_config = config.with_increased_interval()
    assert new_config is not config
    assert new_config.update_interval > original_interval
    assert config.update_interval == original_interval  # Original unchanged

    # Test decrease
    new_config = config.with_decreased_interval()
    assert new_config is not config
    assert new_config.update_interval < original_interval
    assert config.update_interval == original_interval  # Original unchanged


def test_renderer_config_pattern_updates() -> None:
    """Test pattern selection and rotation updates."""
    config = RendererConfig()

    # Test pattern selection
    new_config = config.with_pattern("glider")
    assert new_config is not config
    assert new_config.selected_pattern == "glider"
    assert config.selected_pattern is None  # Original unchanged

    # Test pattern rotation
    new_config = config.with_pattern("glider", PatternTransform.RIGHT)
    assert new_config is not config
    assert new_config.selected_pattern == "glider"
    assert new_config.pattern_rotation == PatternTransform.RIGHT
    assert config.pattern_rotation == PatternTransform.NONE  # Original unchanged


def test_renderer_config_interval_limits() -> None:
    """Test that interval updates respect limits."""
    # Test upper limit
    config = RendererConfig(update_interval=RendererConfig().max_interval)
    new_config = config.with_increased_interval()
    assert new_config.update_interval == config.max_interval  # Cannot exceed max

    # Test lower limit
    config = RendererConfig(update_interval=RendererConfig().min_interval)
    new_config = config.with_decreased_interval()
    assert new_config.update_interval == config.min_interval  # Cannot go below min


def test_handle_user_input_cycle_boundary_command(
    mock_terminal: TerminalProtocol,
    mock_config: RendererConfig,
    mock_state: RendererState,
) -> None:
    """Test boundary cycle command handling."""
    key = create_mock_keystroke("b")
    result = handle_user_input(key, mock_config, mock_state)
    assert result[0] == "cycle_boundary"
    assert result[1] is mock_config  # Config remains unchanged
