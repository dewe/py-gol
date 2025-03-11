"""Tests for the terminal renderer module.

Focus on impure functions that handle terminal I/O and state management.
"""

import dataclasses
import re
from typing import Any, List
from unittest.mock import Mock, PropertyMock, patch

import pytest
from blessed import Terminal
from blessed.formatters import ParameterizingString
from blessed.keyboard import Keystroke

from gol.metrics import create_metrics
from gol.patterns import FilePatternStorage, PatternCategory, PatternTransform
from gol.renderer import (
    RendererConfig,
    TerminalProtocol,
    cleanup_terminal,
    handle_resize_event,
    initialize_terminal,
    render_grid_to_terminal,
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


class MockTerminal(TerminalProtocol):
    """Mock terminal for testing that implements TerminalProtocol."""

    def __init__(self) -> None:
        self._width = 80
        self._height = 24
        self._move_xy_calls: List[tuple[int, int]] = []
        self._mock_calls: List[str] = []

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def dim(self) -> str:
        return ""

    @property
    def normal(self) -> str:
        return ""

    @property
    def white(self) -> str:
        return ""

    @property
    def blue(self) -> str:
        return ""

    @property
    def green(self) -> str:
        return ""

    @property
    def yellow(self) -> str:
        return ""

    @property
    def magenta(self) -> str:
        return ""

    def move_xy(self, x: int, y: int) -> ParameterizingString:
        self._move_xy_calls.append((x, y))
        return ParameterizingString("")

    def exit_fullscreen(self) -> str:
        self._mock_calls.append("exit_fullscreen")
        return ""

    def enter_fullscreen(self) -> str:
        self._mock_calls.append("enter_fullscreen")
        return ""

    def hide_cursor(self) -> str:
        self._mock_calls.append("hide_cursor")
        return ""

    def normal_cursor(self) -> str:
        self._mock_calls.append("normal_cursor")
        return ""

    def clear(self) -> str:
        self._mock_calls.append("clear")
        return ""

    def enter_ca_mode(self) -> str:
        self._mock_calls.append("enter_ca_mode")
        return ""

    def exit_ca_mode(self) -> str:
        self._mock_calls.append("exit_ca_mode")
        return ""

    def inkey(self, timeout: float = 0) -> Keystroke:
        return Keystroke("")

    def cbreak(self) -> Any:
        return self

    def set_dimensions(self, width: int, height: int) -> None:
        """Test helper to simulate terminal resize."""
        self._width = width
        self._height = height

    @property
    def move_xy_calls(self) -> List[tuple[int, int]]:
        """Test helper to verify move_xy calls."""
        return self._move_xy_calls

    @property
    def mock_calls(self) -> List[str]:
        """Test helper to verify method calls."""
        return self._mock_calls


@pytest.fixture
def mock_terminal() -> MockTerminal:
    """Create a mock terminal for testing."""
    return MockTerminal()


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

    assert new_state.viewport.width == 100
    assert new_state.viewport.height == 40
    assert new_state.previous_grid is None
    assert new_state.pattern_cells is None


def test_render_pattern_menu(mock_terminal: TerminalProtocol) -> None:
    """Test pattern menu rendering."""
    config = RendererConfig()
    menu_text = render_pattern_menu(mock_terminal, config)
    stripped_text = strip_ansi(menu_text)

    # Basic menu elements
    assert "Pattern Mode" in stripped_text
    assert "Select:" in stripped_text
    assert "rotate" in stripped_text
    assert "place" in stripped_text
    assert "exit" in stripped_text

    # Category navigation
    assert "Tab: next" in stripped_text
    assert "(1/" in stripped_text  # Category counter

    # Pattern category name
    assert any(
        cat.name.replace("_", " ").title() in stripped_text for cat in PatternCategory
    )


def test_pattern_menu_category_cycling(mock_terminal: TerminalProtocol) -> None:
    """Test cycling through pattern categories."""
    config = RendererConfig()

    # Get initial category
    menu_text = render_pattern_menu(mock_terminal, config)
    initial_category = next(
        cat.name
        for cat in PatternCategory
        if cat.name.replace("_", " ").title() in strip_ansi(menu_text)
    )

    # Cycle to next category
    config = config.with_pattern_category_idx(1)
    menu_text = render_pattern_menu(mock_terminal, config)
    next_category = next(
        cat.name
        for cat in PatternCategory
        if cat.name.replace("_", " ").title() in strip_ansi(menu_text)
    )

    assert initial_category != next_category
    assert "(2/" in strip_ansi(menu_text)


def test_pattern_menu_custom_patterns(mock_terminal: TerminalProtocol) -> None:
    """Test menu with custom patterns."""
    config = RendererConfig()

    # Mock custom patterns
    with patch.object(
        FilePatternStorage, "list_patterns", return_value=["custom1", "custom2"]
    ):
        menu_text = render_pattern_menu(mock_terminal, config)
        stripped_text = strip_ansi(menu_text)

        # Find Custom category
        custom_idx = next(
            i for i, cat in enumerate(PatternCategory) if cat == PatternCategory.CUSTOM
        )
        config = config.with_pattern_category_idx(custom_idx)
        menu_text = render_pattern_menu(mock_terminal, config)
        stripped_text = strip_ansi(menu_text)

        assert "Custom" in stripped_text
        assert "custom1" in stripped_text
        assert "custom2" in stripped_text


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


def test_debug_status_bar_clearing(mock_terminal: MockTerminal) -> None:
    """Test that debug status bar is properly cleared when debug mode changes."""
    # Create test grid
    import numpy as np

    grid = np.zeros((10, 10), dtype=bool)

    # Create initial state with debug mode on
    state = RendererState.create(dimensions=(10, 10)).with_debug_mode(True)
    config = RendererConfig()
    metrics = create_metrics()

    # First render with debug mode on
    state, _ = render_grid_to_terminal(mock_terminal, grid, config, state, metrics)

    # Verify debug line was rendered
    debug_line_y = mock_terminal.height - 2
    debug_line_calls = [
        pos for pos in mock_terminal.move_xy_calls if pos[1] == debug_line_y
    ]
    assert (
        len(debug_line_calls) > 0
    ), "Debug line should be rendered when debug mode is on"

    # Toggle debug mode off
    state = state.with_debug_mode(False)

    # Clear mock call history
    mock_terminal._move_xy_calls.clear()

    # Second render with debug mode off
    state, _ = render_grid_to_terminal(mock_terminal, grid, config, state, metrics)

    # Verify debug line was cleared
    debug_line_calls = [
        pos for pos in mock_terminal.move_xy_calls if pos[1] == debug_line_y
    ]
    assert any(
        pos[0] == 0 for pos in debug_line_calls
    ), "Debug line should be cleared when debug mode is off"

    # Verify no debug info was printed after clearing
    debug_info_calls = [
        pos
        for pos in mock_terminal.move_xy_calls
        if pos[1] == debug_line_y and pos[0] > 1  # More than just spaces
    ]
    assert (
        not debug_info_calls
    ), "No debug info should be printed when debug mode is off"
