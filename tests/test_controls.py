"""Test keyboard controls for Game of Life.

Tests all keyboard controls specified in controls.md to ensure they work as expected
in both normal and pattern modes.
"""

from unittest.mock import Mock, PropertyMock, patch

import pytest
from blessed.keyboard import Keystroke

from gol.controller import ControllerConfig
from gol.renderer import RendererConfig, TerminalProtocol, handle_user_input
from gol.state import RendererState, ViewportState


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

    def test_simulation_controls(self) -> None:
        """Test simulation control keys (space, c, r)."""
        config = RendererConfig()
        state = RendererState()

        # Space - Start/Stop simulation
        key = Keystroke(name="KEY_SPACE", ucs=" ")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "toggle_simulation"

        # C - Clear grid
        key = Keystroke(ucs="c")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "clear_grid"

        # R - Restart with new grid
        key = Keystroke(ucs="r")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "restart"

    def test_mode_controls(self) -> None:
        """Test mode switching and exit controls."""
        config = RendererConfig()
        state = RendererState()

        # P - Enter pattern mode
        key = Keystroke(ucs="p")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "pattern"

        # Q - Quit game
        key = Keystroke(ucs="q")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "quit"

        # Esc - Quit game
        key = Keystroke(name="KEY_ESCAPE")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "quit"

    def test_grid_controls(self) -> None:
        """Test grid manipulation controls."""
        config = RendererConfig()
        state = RendererState()

        # B - Cycle boundary conditions
        key = Keystroke(ucs="b")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "cycle_boundary"

        # + - Resize grid larger
        key = Keystroke(ucs="+")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "resize_larger"

        # - - Resize grid smaller
        key = Keystroke(ucs="-")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "resize_smaller"

    def test_speed_controls(self) -> None:
        """Test simulation speed controls."""
        config = RendererConfig()
        state = RendererState()

        # Shift+Up - Increase simulation speed
        key = Keystroke(name="KEY_SUP")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "speed_up"

        # Shift+Down - Decrease simulation speed
        key = Keystroke(name="KEY_SDOWN")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "speed_down"

    def test_viewport_panning(self) -> None:
        """Test viewport panning with arrow keys."""
        config = RendererConfig()
        state = RendererState()

        # Test all arrow key directions
        movement_keys = {
            "KEY_LEFT": "viewport_pan_left",
            "KEY_RIGHT": "viewport_pan_right",
            "KEY_UP": "viewport_pan_up",
            "KEY_DOWN": "viewport_pan_down",
        }

        for key_name, expected_cmd in movement_keys.items():
            key = Keystroke(name=key_name)
            cmd, _ = handle_user_input(key, config, state)
            assert cmd == expected_cmd, f"Arrow key {key_name} should pan viewport"

    def test_viewport_boundaries(self) -> None:
        """Test viewport panning respects boundaries."""
        config = RendererConfig()
        state = RendererState.create(
            dimensions=(50, 30),
            viewport=ViewportState(dimensions=(20, 10), offset_x=0, offset_y=0),
        )

        # Test left boundary
        key = Keystroke(name="KEY_LEFT")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "viewport_pan_left"
        assert (
            state.viewport.offset_x == 0
        ), "Viewport should not move beyond left boundary"

        # Test top boundary
        key = Keystroke(name="KEY_UP")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "viewport_pan_up"
        assert (
            state.viewport.offset_y == 0
        ), "Viewport should not move beyond top boundary"

        # Move viewport to bottom-right
        state = state.with_viewport(
            ViewportState(dimensions=(20, 10), offset_x=30, offset_y=20)
        )

        # Test right boundary
        key = Keystroke(name="KEY_RIGHT")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "viewport_pan_right"
        assert (
            state.viewport.offset_x == 30
        ), "Viewport should not move beyond right boundary"

        # Test bottom boundary
        key = Keystroke(name="KEY_DOWN")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "viewport_pan_down"
        assert (
            state.viewport.offset_y == 20
        ), "Viewport should not move beyond bottom boundary"

    def test_invalid_controls(self) -> None:
        """Test that unspecified controls are not allowed."""
        config = RendererConfig()
        state = RendererState()

        # Test some unspecified keys
        invalid_keys = [
            Keystroke(ucs="x"),  # Random letter
            Keystroke(ucs="m"),  # Random letter
            Keystroke(ucs="0"),  # Number (only valid in pattern mode)
            Keystroke(name="KEY_F1"),  # Function key
            Keystroke(name="KEY_HOME"),  # Navigation key
            Keystroke(name="KEY_INSERT"),  # Special key
        ]

        for key in invalid_keys:
            cmd, new_config = handle_user_input(key, config, state)
            assert cmd == "continue", f"Unspecified key {key} should continue"
            assert new_config is config, "Config should not change for invalid keys"


class TestPatternModeControls:
    """Test pattern mode keyboard controls."""

    def test_pattern_selection(self) -> None:
        """Test pattern selection controls."""
        config = RendererConfig()
        state = RendererState(pattern_mode=True)

        # Mock BUILTIN_PATTERNS
        mock_patterns = {f"pattern{i}": [[1]] for i in range(1, 10)}
        with patch("gol.renderer.BUILTIN_PATTERNS", mock_patterns):
            # 1-9 - Select pattern
            for i in range(1, 10):
                key = Keystroke(ucs=str(i))
                cmd, new_config = handle_user_input(key, config, state)
                assert cmd == "select_pattern"
                assert (
                    new_config is not config
                )  # Config should be updated with new pattern

    def test_pattern_manipulation(self) -> None:
        """Test pattern manipulation controls."""
        config = RendererConfig()
        state = RendererState(pattern_mode=True)

        # R - Rotate pattern
        key = Keystroke(ucs="r")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "rotate_pattern"

        # Space - Place pattern
        key = Keystroke(name="KEY_SPACE", ucs=" ")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "place_pattern"

    def test_pattern_navigation(self) -> None:
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
            key = Keystroke(name=key_name)
            cmd, _ = handle_user_input(key, config, state)
            assert cmd == expected_cmd

    def test_pattern_mode_exit(self) -> None:
        """Test pattern mode exit controls."""
        config = RendererConfig()
        state = RendererState(pattern_mode=True)

        # P - Exit pattern mode
        key = Keystroke(ucs="p")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "pattern"

        # Esc - Exit pattern mode
        key = Keystroke(name="KEY_ESCAPE")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "exit_pattern"

    def test_pattern_mode_exit_constraints(self) -> None:
        """Test pattern mode exit constraints."""
        config = RendererConfig()
        state = RendererState(pattern_mode=True)

        # ESC should exit pattern mode
        key = Keystroke(name="KEY_ESCAPE")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "exit_pattern", "ESC should exit pattern mode"

        # Q should quit game
        key = Keystroke(ucs="q")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "quit", "Q should quit game"

        # P should exit pattern mode
        key = Keystroke(ucs="p")
        cmd, _ = handle_user_input(key, config, state)
        assert cmd == "pattern", "P should exit pattern mode"

        # Other keys should not exit pattern mode
        invalid_exit_keys = [
            Keystroke(ucs="x"),
            Keystroke(ucs="m"),
            Keystroke(name="KEY_F1"),
            Keystroke(name="KEY_HOME"),
        ]

        for key in invalid_exit_keys:
            cmd, _ = handle_user_input(key, config, state)
            assert (
                cmd != "pattern" and cmd != "exit_pattern"
            ), f"Key {key} should not exit pattern mode"

    def test_repeated_pattern_selection(self) -> None:
        """Test that patterns can be selected repeatedly."""
        config = RendererConfig()
        state = RendererState(pattern_mode=True)

        # Mock BUILTIN_PATTERNS
        mock_patterns = {f"pattern{i}": [[1]] for i in range(1, 10)}
        with patch("gol.renderer.BUILTIN_PATTERNS", mock_patterns):
            # Select pattern 1 multiple times
            key = Keystroke(ucs="1")
            for _ in range(3):
                cmd, new_config = handle_user_input(key, config, state)
                assert cmd == "select_pattern"
                assert new_config is not config

            # Switch between patterns repeatedly
            for _ in range(3):
                # Select pattern 2
                key = Keystroke(ucs="2")
                cmd, new_config = handle_user_input(key, config, state)
                assert cmd == "select_pattern"
                assert new_config.selected_pattern == "pattern2"

                # Select pattern 3
                key = Keystroke(ucs="3")
                cmd, new_config = handle_user_input(key, config, state)
                assert cmd == "select_pattern"
                assert new_config.selected_pattern == "pattern3"

                # Select pattern 4
                key = Keystroke(ucs="4")
                cmd, new_config = handle_user_input(key, config, state)
                assert cmd == "select_pattern"
                assert new_config.selected_pattern == "pattern4"

    def test_pattern_rotation_edge_cases(self) -> None:
        """Test pattern rotation with various pattern shapes."""
        config = RendererConfig()
        state = RendererState(pattern_mode=True)

        # Test single cell pattern
        config = config.with_pattern("single_cell")
        key = Keystroke(ucs="r")
        cmd, new_config = handle_user_input(key, config, state)
        assert cmd == "rotate_pattern"
        assert (
            new_config.selected_pattern == "single_cell"
        ), "Single cell pattern name should not change on rotation"

        # Test asymmetric pattern
        config = config.with_pattern("asymmetric")
        key = Keystroke(ucs="r")
        cmd, new_config = handle_user_input(key, config, state)
        assert cmd == "rotate_pattern"
        assert (
            new_config.selected_pattern == "asymmetric"
        ), "Pattern name should not change on rotation"
        assert (
            new_config.pattern_rotation != config.pattern_rotation
        ), "Pattern rotation should change"

        # Test empty pattern
        config = config.with_pattern(None)
        key = Keystroke(ucs="r")
        cmd, new_config = handle_user_input(key, config, state)
        assert cmd == "rotate_pattern"
        assert (
            new_config.selected_pattern is None
        ), "Empty pattern should remain None after rotation"

        # Test full rotation sequence
        config = config.with_pattern("glider")
        current_rotation = config.pattern_rotation

        # Rotate 4 times to get back to original
        for i in range(4):
            key = Keystroke(ucs="r")
            cmd, new_config = handle_user_input(key, config, state)
            assert cmd == "rotate_pattern"
            assert (
                new_config.pattern_rotation != current_rotation
            ), f"Pattern rotation should change on rotation {i+1}"
            current_rotation = new_config.pattern_rotation
            config = new_config

        assert (
            current_rotation == config.pattern_rotation
        ), "Pattern rotation should return to original after 4 rotations"

    def test_pattern_placement_at_boundaries(self) -> None:
        """Test pattern placement behavior at grid boundaries."""
        config = ControllerConfig.create(width=50, height=30)
        state = RendererState(pattern_mode=True)

        # Mock a pattern larger than 1x1
        mock_patterns = {"test_pattern": [[1, 1], [1, 1]]}  # 2x2 pattern
        with patch("gol.renderer.BUILTIN_PATTERNS", mock_patterns):
            # Select test pattern
            key = Keystroke(ucs="1")
            cmd, new_config = handle_user_input(key, config.renderer, state)
            assert cmd == "select_pattern"
            config = config.with_renderer(new_config)

            # Test pattern placement at boundaries
            # Pattern should still be placeable at edges
            state = state.with_cursor(0, 0)  # Top-left corner
            key = Keystroke(name="KEY_SPACE", ucs=" ")
            cmd, _ = handle_user_input(key, config.renderer, state)
            assert cmd == "place_pattern"

            # Pattern should still be placeable at bottom-right
            max_x = config.dimensions[0] - 1
            max_y = config.dimensions[1] - 1
            state = state.with_cursor(max_x, max_y)
            key = Keystroke(name="KEY_SPACE", ucs=" ")
            cmd, _ = handle_user_input(key, config.renderer, state)
            assert cmd == "place_pattern"

    def test_cursor_movement_limits(self) -> None:
        """Test cursor movement limits in pattern mode."""
        config = ControllerConfig.create(width=50, height=30)
        state = RendererState(pattern_mode=True)

        # Test cursor movement at boundaries
        movement_tests = [
            # (direction_key, x, y, expected_cmd)
            ("KEY_LEFT", 0, 5, "move_cursor_left"),
            ("KEY_RIGHT", config.dimensions[0] - 1, 5, "move_cursor_right"),
            ("KEY_UP", 5, 0, "move_cursor_up"),
            ("KEY_DOWN", 5, config.dimensions[1] - 1, "move_cursor_down"),
        ]

        for key_name, x, y, expected_cmd in movement_tests:
            state = state.with_cursor(x, y)
            key = Keystroke(name=key_name)
            cmd, _ = handle_user_input(key, config.renderer, state)
            assert cmd == expected_cmd

    def test_pattern_rotation_angles(self) -> None:
        """Test pattern rotation angles."""
        config = ControllerConfig.create(width=50, height=30)
        state = RendererState(pattern_mode=True)

        # Mock an asymmetric pattern to test rotation
        mock_patterns = {"test_pattern": [[1, 0], [1, 1]]}  # L-shaped pattern
        with patch("gol.renderer.BUILTIN_PATTERNS", mock_patterns):
            # Select test pattern
            key = Keystroke(ucs="1")
            cmd, new_config = handle_user_input(key, config.renderer, state)
            assert cmd == "select_pattern"
            config = config.with_renderer(new_config)

            # Test full rotation sequence (should rotate 90 degrees each time)
            rotations = []
            current_rotation = config.renderer.pattern_rotation
            for _ in range(4):
                key = Keystroke(ucs="r")
                cmd, new_config = handle_user_input(key, config.renderer, state)
                assert cmd == "rotate_pattern"
                assert new_config.pattern_rotation != current_rotation
                rotations.append(new_config.pattern_rotation)
                current_rotation = new_config.pattern_rotation
                config = config.with_renderer(new_config)

            # After 4 rotations, should be back to original position
            assert len(set(rotations)) == 4, "Should have 4 unique rotation states"
            assert (
                rotations[0] != rotations[1]
            ), "90 degree rotation should be different"
            assert (
                rotations[1] != rotations[2]
            ), "180 degree rotation should be different"
            assert (
                rotations[2] != rotations[3]
            ), "270 degree rotation should be different"
            # The last rotation should be different from the previous one
            assert rotations[3] != rotations[2], "Last rotation should be different"

    def test_grid_size_limits(self) -> None:
        """Test grid resize limits."""
        config = ControllerConfig.create(width=50, height=30)
        state = RendererState()

        # Test minimum grid size
        for _ in range(20):  # Try many times to ensure we hit the limit
            key = Keystroke(ucs="-")
            cmd, new_config = handle_user_input(key, config.renderer, state)
            assert cmd == "resize_smaller"
            # Grid should not become too small to be usable
            assert config.dimensions[0] >= 10, "Grid width should not go below 10"
            assert config.dimensions[1] >= 10, "Grid height should not go below 10"
            config = config.with_renderer(new_config)

        # Test maximum grid size
        config = ControllerConfig.create(width=50, height=30)  # Reset to default
        for _ in range(20):  # Try many times to ensure we hit the limit
            key = Keystroke(ucs="+")
            cmd, new_config = handle_user_input(key, config.renderer, state)
            assert cmd == "resize_larger"
            # Grid should not become too large to be manageable
            assert config.dimensions[0] <= 200, "Grid width should not exceed 200"
            assert config.dimensions[1] <= 200, "Grid height should not exceed 200"
            config = config.with_renderer(new_config)
