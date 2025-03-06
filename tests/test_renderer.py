"""Tests for the terminal renderer module.

Focus on impure functions that handle terminal I/O, user input, and state management.
"""

import dataclasses
import re
from unittest.mock import Mock, PropertyMock

import pytest
from blessed import Terminal
from blessed.keyboard import Keystroke

from gol.metrics import create_metrics
from gol.patterns import PatternTransform
from gol.renderer import (
    RendererConfig,
    TerminalProtocol,
    cleanup_terminal,
    handle_resize_event,
    handle_user_input,
    initialize_terminal,
    render_pattern_menu,
    render_status_line,
)
from gol.state import RendererState


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
    assert result[0] == "continue"  # Resize is handled by game loop
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


def test_handle_resize_event(
    mock_terminal: TerminalProtocol,
    mock_state: RendererState,
) -> None:
    """
    Given: A terminal that has been resized
    When: Handling the resize event
    Then: Should update state with new dimensions
    """
    # Create a new mock with updated dimensions
    resized_terminal = Mock(spec=TerminalProtocol)
    # Configure dimensions as properties
    type(resized_terminal).width = PropertyMock(return_value=100)
    type(resized_terminal).height = PropertyMock(return_value=40)

    # Configure mock methods to return empty strings
    resized_terminal.clear.return_value = ""
    resized_terminal.move_xy.return_value = ""
    resized_terminal.hide_cursor.return_value = ""

    new_state = handle_resize_event(resized_terminal, mock_state)

    assert new_state.terminal_width == 100
    assert new_state.terminal_height == 40
    assert new_state.previous_grid is None
    assert new_state.previous_pattern_cells is None


def test_render_pattern_menu(mock_terminal: TerminalProtocol) -> None:
    """Test pattern menu rendering."""
    menu_text = render_pattern_menu(mock_terminal)
    stripped_text = strip_ansi(menu_text)
    assert "Pattern Mode" in stripped_text
    assert "Select:" in stripped_text
    assert "rotate" in stripped_text
    assert "place" in stripped_text
    assert "exit" in stripped_text


def test_render_status_line(
    mock_terminal: TerminalProtocol,
    mock_config: RendererConfig,
) -> None:
    """Test status line rendering."""
    metrics = create_metrics()
    status_text = render_status_line(mock_terminal, mock_config, metrics)
    stripped_text = strip_ansi(status_text)
    assert "Population:" in stripped_text
    assert "Generation:" in stripped_text
    assert "Births/s:" in stripped_text
    assert "Deaths/s:" in stripped_text
    assert "Interval:" in stripped_text


@pytest.fixture
def mock_terminal() -> TerminalProtocol:
    """Create a mock terminal for testing.

    Returns:
        Mock terminal that returns empty strings for display operations
    """
    terminal = Mock(spec=TerminalProtocol)

    # Configure dimensions as properties
    type(terminal).width = PropertyMock(return_value=80)
    type(terminal).height = PropertyMock(return_value=24)

    # Configure mock methods to return empty strings
    terminal.clear.return_value = ""
    terminal.move_xy.return_value = ""
    terminal.hide_cursor.return_value = ""
    terminal.normal_cursor.return_value = ""
    terminal.enter_fullscreen.return_value = ""
    terminal.exit_fullscreen.return_value = ""
    terminal.enter_ca_mode.return_value = ""
    terminal.exit_ca_mode.return_value = ""

    # Configure mock properties
    type(terminal).normal = PropertyMock(return_value="")
    type(terminal).dim = PropertyMock(return_value="")
    type(terminal).white = PropertyMock(return_value="")
    type(terminal).blue = PropertyMock(return_value="")
    type(terminal).green = PropertyMock(return_value="")
    type(terminal).yellow = PropertyMock(return_value="")
    type(terminal).magenta = PropertyMock(return_value="")

    # Configure inkey and cbreak
    terminal.inkey.return_value = Keystroke("")
    terminal.cbreak.return_value = terminal

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
