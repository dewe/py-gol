"""Test keyboard controls for Game of Life.

Tests all keyboard controls specified in controls.md to ensure they work as expected
in both normal and pattern modes.
"""

from unittest.mock import Mock, PropertyMock, patch

import pytest
from blessed.keyboard import Keystroke

from gol.renderer import RendererConfig, TerminalProtocol, handle_user_input
from gol.state import RendererState


def create_mock_keystroke(name: str = "", value: str = "") -> Mock:
    """Create a mock keystroke for testing."""
    key = Mock(spec=Keystroke)
    key.name = name or value
    key.configure_mock(__str__=Mock(return_value=value))
    key.configure_mock(__eq__=Mock(side_effect=lambda x: str(key) == x))
    key.configure_mock(isdigit=Mock(return_value=value.isdigit() if value else False))
    return key


@pytest.fixture
def mock_terminal() -> TerminalProtocol:
    """Create a mock terminal for testing."""
    terminal = Mock(spec=TerminalProtocol)
    type(terminal).width = PropertyMock(return_value=80)
    type(terminal).height = PropertyMock(return_value=24)
    terminal.clear.return_value = ""
    terminal.move_xy.return_value = ""
    terminal.hide_cursor.return_value = ""
    terminal.normal_cursor.return_value = ""
    terminal.enter_fullscreen.return_value = ""
    terminal.exit_fullscreen.return_value = ""
    terminal.enter_ca_mode.return_value = ""
    terminal.exit_ca_mode.return_value = ""
    type(terminal).normal = PropertyMock(return_value="")
    type(terminal).dim = PropertyMock(return_value="")
    type(terminal).white = PropertyMock(return_value="")
    type(terminal).blue = PropertyMock(return_value="")
    type(terminal).green = PropertyMock(return_value="")
    type(terminal).yellow = PropertyMock(return_value="")
    type(terminal).magenta = PropertyMock(return_value="")
    terminal.inkey.return_value = Keystroke("")
    terminal.cbreak.return_value = terminal
    return terminal


class TestNormalModeControls:
    """Test normal mode keyboard controls."""

    def test_simulation_controls(self, mock_terminal: TerminalProtocol) -> None:
        """Test simulation control keys (space, c, r)."""
        config = RendererConfig()
        state = RendererState()

        # Space - Start/Stop simulation
        key = create_mock_keystroke("KEY_SPACE", " ")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "toggle_simulation"

        # C - Clear grid
        key = create_mock_keystroke("c", "c")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "clear_grid"

        # R - Restart with new grid
        key = create_mock_keystroke("r", "r")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "restart"

    def test_mode_controls(self, mock_terminal: TerminalProtocol) -> None:
        """Test mode switching and exit controls."""
        config = RendererConfig()
        state = RendererState()

        # P - Enter pattern mode
        key = create_mock_keystroke("p", "p")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "pattern"

        # Q, Esc - Quit game
        for key_name in ["q", "KEY_ESCAPE"]:
            key = create_mock_keystroke(key_name)
            cmd, _ = handle_user_input(key, config, state)
            assert cmd == "quit"

    def test_grid_controls(self, mock_terminal: TerminalProtocol) -> None:
        """Test grid manipulation controls."""
        config = RendererConfig()
        state = RendererState()

        # B - Cycle boundary conditions
        key = create_mock_keystroke("b", "b")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "cycle_boundary"

        # + - Resize grid larger
        key = create_mock_keystroke(value="+")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "resize_larger"

        # - - Resize grid smaller
        key = create_mock_keystroke(value="-")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "resize_smaller"

    def test_speed_controls(self, mock_terminal: TerminalProtocol) -> None:
        """Test simulation speed controls."""
        config = RendererConfig()
        state = RendererState()

        # Shift+Up - Increase simulation speed
        key = create_mock_keystroke("KEY_SUP")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "speed_up"

        # Shift+Down - Decrease simulation speed
        key = create_mock_keystroke("KEY_SDOWN")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "speed_down"


class TestPatternModeControls:
    """Test pattern mode keyboard controls."""

    def test_pattern_selection(self, mock_terminal: TerminalProtocol) -> None:
        """Test pattern selection controls."""
        config = RendererConfig()
        state = RendererState(pattern_mode=True)

        # Mock BUILTIN_PATTERNS and FilePatternStorage
        mock_patterns = {f"pattern{i}": [[1]] for i in range(1, 10)}
        with (
            patch("gol.renderer.BUILTIN_PATTERNS", mock_patterns),
            patch("gol.renderer.FilePatternStorage") as mock_storage,
        ):
            mock_storage.return_value.list_patterns.return_value = []

            # 1-9 - Select pattern
            for i in range(1, 10):
                key = create_mock_keystroke(value=str(i))
                cmd, new_config = handle_user_input(key, config, state)
                assert cmd == "pattern"
                assert (
                    new_config is not config
                )  # Config should be updated with new pattern

    def test_pattern_manipulation(self, mock_terminal: TerminalProtocol) -> None:
        """Test pattern manipulation controls."""
        config = RendererConfig()
        state = RendererState(pattern_mode=True)

        # R - Rotate pattern
        key = create_mock_keystroke("r", "r")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "rotate_pattern"

        # Space - Place pattern
        key = create_mock_keystroke("KEY_SPACE", " ")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "place_pattern"

    def test_pattern_navigation(self, mock_terminal: TerminalProtocol) -> None:
        """Test pattern mode navigation controls."""
        config = RendererConfig()
        state = RendererState(pattern_mode=True)

        # Test cursor movement
        movement_keys = {
            "KEY_LEFT": "move_cursor_left",
            "KEY_RIGHT": "move_cursor_right",
            "KEY_UP": "move_cursor_up",
            "KEY_DOWN": "move_cursor_down",
        }

        for key_name, expected_cmd in movement_keys.items():
            key = create_mock_keystroke(key_name)
            cmd, _ = handle_user_input(key, config, state)
            assert cmd == expected_cmd

    def test_pattern_mode_exit(self, mock_terminal: TerminalProtocol) -> None:
        """Test pattern mode exit controls."""
        config = RendererConfig()
        state = RendererState(pattern_mode=True)

        # P - Exit pattern mode
        key = create_mock_keystroke("p", "p")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "pattern"

        # Esc - Exit pattern mode
        key = create_mock_keystroke("KEY_ESCAPE", "\x1b")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "exit_pattern"
