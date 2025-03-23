"""Tests for simulation speed controls."""

from blessed.keyboard import Keystroke

from gol.controller import ControllerConfig
from gol.grid import create_grid
from gol.renderer import RendererConfig, handle_user_input
from gol.state import RendererState


def test_speed_control_inverse_proportional_steps() -> None:
    """Test that speed adjustments follow inverse proportional steps.

    Speed should be adjusted in steps that are inverse proportional to the
    current speed.
    - At lower speeds (higher intervals), steps should be larger
    - At higher speeds (lower intervals), steps should be smaller
    """
    # Start with default interval (200ms = 5 gen/s)
    config = RendererConfig()
    state = RendererState()

    # Test speed increase (decreasing intervals)
    intervals = []
    current_config = config

    # Simulate multiple speed increases
    for _ in range(5):
        key = Keystroke(name="KEY_SUP")  # Shift+Up
        cmd, new_config = handle_user_input(key, current_config, state)
        assert cmd == "speed_up"
        intervals.append(new_config.update_interval)
        current_config = new_config

    # Verify steps get smaller as speed increases (intervals decrease)
    steps = [intervals[i - 1] - intervals[i] for i in range(1, len(intervals))]
    assert all(
        steps[i] >= steps[i + 1] for i in range(len(steps) - 1)
    ), "Speed increase steps should get smaller as speed increases"

    # Test speed decrease (increasing intervals)
    intervals = []
    current_config = config

    # Simulate multiple speed decreases
    for _ in range(5):
        key = Keystroke(name="KEY_SDOWN")  # Shift+Down
        cmd, new_config = handle_user_input(key, current_config, state)
        assert cmd == "speed_down"
        intervals.append(new_config.update_interval)
        current_config = new_config

    # Verify steps get larger as speed decreases (intervals increase)
    steps = [intervals[i] - intervals[i - 1] for i in range(1, len(intervals))]
    assert all(
        steps[i] >= steps[i - 1] for i in range(1, len(steps))
    ), "Speed decrease steps should get larger as speed decreases"


def test_speed_control_boundaries() -> None:
    """Test that speed controls respect min/max boundaries.

    - Max speed: 20 generations/second (50ms interval)
    - Min speed: 0.5 generations/second (2000ms interval)
    """
    config = RendererConfig()
    state = RendererState()

    # Test maximum speed limit
    current_config = config
    for _ in range(20):  # Try many times to ensure we hit the limit
        key = Keystroke(name="KEY_SUP")  # Shift+Up
        cmd, new_config = handle_user_input(key, current_config, state)
        assert cmd == "speed_up"
        assert new_config.update_interval >= 50, "Speed should not exceed 20 gen/s"
        current_config = new_config

    # Test minimum speed limit
    current_config = config
    for _ in range(20):  # Try many times to ensure we hit the limit
        key = Keystroke(name="KEY_SDOWN")  # Shift+Down
        cmd, new_config = handle_user_input(key, current_config, state)
        assert cmd == "speed_down"
        assert new_config.update_interval <= 2000, "Speed should not go below 0.5 gen/s"
        current_config = new_config


def test_speed_control_in_game_loop() -> None:
    """Test that speed controls work correctly in the game loop."""
    from unittest.mock import Mock, PropertyMock

    from gol.main import run_game_loop

    # Create mock terminal
    terminal = Mock()
    type(terminal).width = PropertyMock(return_value=80)
    type(terminal).height = PropertyMock(return_value=24)
    terminal.normal = ""
    terminal.dim = ""
    terminal.white = ""
    terminal.yellow = ""
    terminal.blue = ""
    terminal.move_xy = Mock(return_value="")
    terminal.clear = Mock(return_value="")
    terminal.normal_cursor = Mock(return_value="")
    terminal.exit_ca_mode = Mock(return_value="")
    terminal.exit_fullscreen = Mock(return_value="")

    # Create a context manager mock for cbreak
    cbreak_context = Mock()
    cbreak_context.__enter__ = Mock(return_value=None)
    cbreak_context.__exit__ = Mock(return_value=None)
    terminal.cbreak = Mock(return_value=cbreak_context)

    # Set up test sequence
    terminal.inkey = Mock(
        side_effect=[
            Keystroke(name="KEY_SUP"),  # Speed up
            Keystroke(name="KEY_SUP"),  # Speed up again
            Keystroke(name="KEY_SDOWN"),  # Speed down
            Keystroke("q"),  # Quit
            None,  # Return None when no more keystrokes
        ]
    )

    # Create initial game state
    config = ControllerConfig.create(
        width=10, height=10, density=0.0, update_interval=200  # Start at default speed
    )
    state = RendererState.create()
    grid = create_grid(config.grid)

    # Run game loop
    run_game_loop(terminal, grid, config, state)

    # Verify all keys were processed
    assert terminal.inkey.call_count == 5, "Not all speed control keys were processed"


def test_speed_interval_rounding() -> None:
    """Test that speed intervals are always rounded to nearest 10ms."""
    config = RendererConfig()
    state = RendererState()

    # Test multiple speed adjustments
    current_config = config
    for _ in range(10):
        key = Keystroke(name="KEY_SUP")
        _, new_config = handle_user_input(key, current_config, state)
        assert (
            new_config.update_interval % 10 == 0
        ), "Interval should be rounded to nearest 10ms"
        current_config = new_config

    current_config = config
    for _ in range(10):
        key = Keystroke(name="KEY_SDOWN")
        _, new_config = handle_user_input(key, current_config, state)
        assert (
            new_config.update_interval % 10 == 0
        ), "Interval should be rounded to nearest 10ms"
        current_config = new_config
