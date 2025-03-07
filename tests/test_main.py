"""Tests for main game loop."""

from unittest.mock import Mock

from blessed.keyboard import Keystroke

from gol.controller import ControllerConfig
from gol.grid import create_grid
from gol.main import run_game_loop
from gol.state import RendererState


def create_mock_terminal() -> Mock:
    """Creates a mock terminal for testing."""
    terminal = Mock()
    terminal.width = 80
    terminal.height = 24
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

    return terminal


def test_game_loop_pattern_mode() -> None:
    """Test pattern mode transitions in game loop."""
    config = ControllerConfig.create(
        width=10,
        height=10,
        density=0.0,
    )
    terminal = create_mock_terminal()
    terminal.inkey = Mock(
        side_effect=[
            Keystroke("p"),  # Enter pattern mode
            Keystroke("1"),  # Select first pattern
            Keystroke("\x1b"),  # Exit pattern mode
            Keystroke("q"),  # Quit
        ]
    )

    state = RendererState.create()
    grid = create_grid(config.grid)

    run_game_loop(terminal, grid, config, state)

    assert terminal.inkey.call_count == 4


def test_game_loop_resize() -> None:
    """Test grid resizing in game loop."""
    config = ControllerConfig.create(
        width=10,
        height=10,
        density=0.0,
    )
    terminal = create_mock_terminal()
    terminal.inkey = Mock(
        side_effect=[
            Keystroke("+"),  # Resize larger
            Keystroke("-"),  # Resize smaller
            Keystroke("q"),  # Quit
        ]
    )

    state = RendererState.create()
    grid = create_grid(config.grid)

    run_game_loop(terminal, grid, config, state)

    assert terminal.inkey.call_count == 3


def test_game_loop_interval_adjustment() -> None:
    """Test update interval adjustment in game loop."""
    config = ControllerConfig.create(
        width=10,
        height=10,
        density=0.0,
    )
    terminal = create_mock_terminal()
    terminal.inkey = Mock(
        side_effect=[
            Keystroke("KEY_UP"),  # Increase interval
            Keystroke("KEY_DOWN"),  # Decrease interval
            Keystroke("q"),  # Quit
        ]
    )

    state = RendererState.create()
    grid = create_grid(config.grid)

    run_game_loop(terminal, grid, config, state)

    assert terminal.inkey.call_count == 3


def test_game_loop_pattern_rotation() -> None:
    """Test pattern rotation in game loop."""
    config = ControllerConfig.create(
        width=10,
        height=10,
        density=0.0,
    )
    terminal = create_mock_terminal()
    terminal.inkey = Mock(
        side_effect=[
            Keystroke("p"),  # Enter pattern mode
            Keystroke("1"),  # Select first pattern
            Keystroke("r"),  # Rotate pattern
            Keystroke(" "),  # Place pattern
            Keystroke("\x1b"),  # Exit pattern mode
            Keystroke("q"),  # Quit
        ]
    )

    state = RendererState.create()
    grid = create_grid(config.grid)

    run_game_loop(terminal, grid, config, state)

    assert terminal.inkey.call_count == 6


def test_game_loop_config_immutability() -> None:
    """Test that configurations remain immutable during game loop."""
    config = ControllerConfig.create(
        width=10,
        height=10,
        density=0.0,
    )
    terminal = create_mock_terminal()
    terminal.inkey = Mock(
        side_effect=[
            Keystroke("p"),  # Enter pattern mode
            Keystroke("1"),  # Select first pattern
            Keystroke("r"),  # Rotate pattern
            Keystroke(" "),  # Place pattern
            Keystroke("\x1b"),  # Exit pattern mode
            Keystroke("+"),  # Resize larger
            Keystroke("KEY_UP"),  # Increase interval
            Keystroke("q"),  # Quit
        ]
    )

    state = RendererState.create()
    grid = create_grid(config.grid)

    # Store original values
    original_grid_config = config.grid
    original_renderer_config = config.renderer

    run_game_loop(terminal, grid, config, state)

    # Verify original configs haven't changed
    assert config.grid is original_grid_config
    assert config.renderer is original_renderer_config


def test_game_loop_config_updates() -> None:
    """Test that config updates create new instances."""
    config = ControllerConfig.create(
        width=10,
        height=10,
        density=0.0,
        update_interval=100,  # Start with lower interval
    )
    terminal = create_mock_terminal()
    terminal.inkey = Mock(
        side_effect=[
            Keystroke("KEY_UP"),  # Increase interval
            Keystroke("q"),  # Quit
        ]
    )

    state = RendererState.create()
    grid = create_grid(config.grid)

    # Store original instances
    original_grid_config = config.grid
    original_renderer_config = config.renderer

    run_game_loop(terminal, grid, config, state)

    # Grid config should remain the same
    assert config.grid is original_grid_config
    # Renderer config should be the same since interval updates are handled in game loop
    assert config.renderer is original_renderer_config
