"""Tests for the game controller module."""

import queue
import time
from threading import Event
from typing import Any, cast

import pytest
from blessed.formatters import ParameterizingString
from blessed.keyboard import Keystroke

from gol.actor import CellActor
from gol.controller import (
    ControllerConfig,
    cleanup_game,
    initialize_game,
    process_generation,
)
from gol.grid import GridConfig
from gol.renderer import (
    RendererConfig,
    RendererState,
    TerminalProtocol,
    calculate_grid_position,
)


class MockTerminal(TerminalProtocol):
    """Mock terminal for testing."""

    def __init__(self) -> None:
        """Initialize mock terminal."""
        self._width = 80
        self._height = 24
        self._input_queue: queue.Queue[Keystroke] = queue.Queue()
        self._in_cbreak = False
        self._color_attrs = {
            "dim": "",
            "normal": "",
            "reverse": "",
            "black": "",
            "blue": "",
            "green": "",
            "yellow": "",
            "magenta": "",
            "on_blue": "",
            "white": "",
            "red": "",
        }

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
        """Get dim text style."""
        return self._color_attrs["dim"]

    @property
    def normal(self) -> str:
        """Get normal text style."""
        return self._color_attrs["normal"]

    @property
    def reverse(self) -> str:
        """Get reverse text style."""
        return self._color_attrs["reverse"]

    @property
    def black(self) -> str:
        """Get black color."""
        return self._color_attrs["black"]

    @property
    def blue(self) -> str:
        """Get blue color."""
        return self._color_attrs["blue"]

    @property
    def green(self) -> str:
        """Get green color."""
        return self._color_attrs["green"]

    @property
    def yellow(self) -> str:
        """Get yellow color."""
        return self._color_attrs["yellow"]

    @property
    def magenta(self) -> str:
        """Get magenta color."""
        return self._color_attrs["magenta"]

    @property
    def on_blue(self) -> str:
        """Get blue background color."""
        return self._color_attrs["on_blue"]

    @property
    def white(self) -> str:
        """Get white color."""
        return self._color_attrs["white"]

    @property
    def red(self) -> str:
        """Get red color."""
        return self._color_attrs["red"]

    def move_xy(self, x: int, y: int) -> ParameterizingString:
        """Move cursor to position."""
        return ParameterizingString(f"\x1b[{y+1};{x+1}H")

    def enter_fullscreen(self) -> str:
        """Enter fullscreen mode."""
        return ""

    def exit_fullscreen(self) -> str:
        """Exit fullscreen mode."""
        return ""

    def hide_cursor(self) -> str:
        """Hide cursor."""
        return ""

    def normal_cursor(self) -> str:
        """Show normal cursor."""
        return ""

    def enter_ca_mode(self) -> str:
        """Enter alternate screen mode."""
        return ""

    def exit_ca_mode(self) -> str:
        """Exit alternate screen mode."""
        return ""

    def clear(self) -> str:
        """Clear screen."""
        return ""

    def cbreak(self) -> Any:
        """Enter cbreak mode."""

        class CBreakContext:
            def __init__(self, terminal: "MockTerminal") -> None:
                self.terminal = terminal

            def __enter__(self) -> None:
                self.terminal._in_cbreak = True

            def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
                self.terminal._in_cbreak = False

        return CBreakContext(self)

    def inkey(self, timeout: float = 0) -> Keystroke:
        """Get key press with timeout."""
        try:
            return self._input_queue.get(timeout=timeout)
        except queue.Empty:
            return Keystroke("")


@pytest.fixture
def mock_terminal() -> TerminalProtocol:
    """Create mock terminal.

    Returns:
        Mock terminal instance
    """
    return MockTerminal()


@pytest.fixture
def config() -> ControllerConfig:
    """Create test configuration.

    Returns:
        Test configuration instance
    """
    return ControllerConfig(
        grid=GridConfig(width=20, height=15, density=0.5),
        renderer=RendererConfig(
            update_interval=100,
            refresh_per_second=5,
        ),
    )


def test_game_initialization(
    config: ControllerConfig, mock_terminal: TerminalProtocol
) -> None:
    """
    Given: Controller configuration
    When: Initializing game
    Then: Should create grid and actors
    And: Should set up terminal
    """
    # When
    from unittest.mock import patch

    with patch(
        "gol.controller.initialize_terminal",
        return_value=(mock_terminal, RendererState()),
    ):
        result = initialize_game(config)

        # Then
        assert isinstance(result, tuple)
        terminal, actors = result
        assert isinstance(terminal, TerminalProtocol)
        assert isinstance(actors, list)
        assert len(actors) > 0
        assert all(isinstance(actor, CellActor) for actor in actors)


def test_actor_setup(config: ControllerConfig, mock_terminal: TerminalProtocol) -> None:
    """
    Given: Game initialization
    When: Setting up actors
    Then: Should create correct number of actors
    And: Should set up message queues
    And: Should subscribe to neighbors
    """

    # When
    _, actors = initialize_game(config)

    # Then
    assert len(actors) == config.grid.width * config.grid.height
    for actor in actors:
        assert isinstance(actor, CellActor)
        assert actor.queue is not None
        assert len(actor.subscribers) > 0


def test_process_generation(
    config: ControllerConfig, mock_terminal: TerminalProtocol
) -> None:
    """
    Given: A set of actors
    When: Processing a generation
    Then: Should update all actor states
    And: Should synchronize with completion event
    """
    # Given
    _, actors = initialize_game(config)
    completion_event = Event()

    # When
    process_generation(actors, completion_event)

    # Then
    assert completion_event.is_set()


def test_process_generation_timing(
    config: ControllerConfig, mock_terminal: TerminalProtocol
) -> None:
    """
    Given: A set of actors
    When: Processing multiple generations
    Then: Should maintain consistent timing
    """
    # Given
    _, actors = initialize_game(config)
    completion_event = Event()

    # When/Then
    start_time = time.time()
    for _ in range(3):
        process_generation(actors, completion_event)
        completion_event.clear()
    end_time = time.time()

    # Verify timing is reasonable (not too fast or slow)
    elapsed = end_time - start_time
    assert 0 < elapsed < 1.0  # Should complete in reasonable time


def test_process_generation_state_changes(
    config: ControllerConfig, mock_terminal: TerminalProtocol
) -> None:
    """
    Given: A set of actors with known initial states
    When: Processing a generation
    Then: Should update states according to game rules
    """
    # Given
    _, actors = initialize_game(config)
    completion_event = Event()

    # Record initial states
    initial_states = [(actor.position, actor.state) for actor in actors]

    # When
    process_generation(actors, completion_event)

    # Then
    final_states = [(actor.position, actor.state) for actor in actors]
    assert initial_states != final_states  # Some states should change


def test_process_generation_error_handling(
    config: ControllerConfig, mock_terminal: TerminalProtocol
) -> None:
    """
    Given: A set of actors
    When: Processing a generation with errors
    Then: Should handle errors gracefully
    """
    # Given
    _, actors = initialize_game(config)
    completion_event = Event()

    # Inject an error by breaking an actor's queue
    actors[0].queue = None  # type: ignore

    # When/Then
    try:
        process_generation(actors, completion_event)
        assert False, "Expected error to be raised"
    except AttributeError as e:
        assert "'NoneType' object has no attribute 'put_nowait'" in str(e)


def test_handle_terminal_resize(mock_terminal: TerminalProtocol) -> None:
    """Test that the grid position is recalculated when terminal window is resized."""
    grid_width = 20  # Use a larger grid to make position changes more noticeable
    grid_height = 15
    total_width = grid_width * 2  # Each cell is 2 chars wide with spacing
    total_height = grid_height  # Each cell is 1 char high

    # Set initial terminal dimensions - slightly smaller than grid
    mock_terminal._width = total_width - 1  # type: ignore[attr-defined]
    mock_terminal._height = total_height - 1  # type: ignore[attr-defined]

    # Calculate initial grid position
    initial_x, initial_y = calculate_grid_position(
        mock_terminal, grid_width, grid_height
    )

    # Verify initial position is within bounds and at edges
    assert initial_x == 0, "Grid should start at left edge in small terminal"
    assert initial_y == 0, "Grid should start at top edge in small terminal"
    assert (
        initial_x + total_width > mock_terminal.width
    ), "Grid should extend beyond terminal width"
    assert (
        initial_y + total_height > mock_terminal.height
    ), "Grid should extend beyond terminal height"

    # Simulate terminal resize to much larger size
    mock_terminal._width = total_width * 4  # type: ignore[attr-defined]
    mock_terminal._height = total_height * 4  # type: ignore[attr-defined]

    # Calculate new grid position
    new_x, new_y = calculate_grid_position(mock_terminal, grid_width, grid_height)

    # Verify new position is still within bounds
    assert new_x >= 0, "Grid should not start outside left edge"
    assert new_y >= 0, "Grid should not start outside top edge"
    assert (
        new_x + total_width <= mock_terminal.width
    ), "Grid should fit within terminal width"
    assert (
        new_y + total_height <= mock_terminal.height
    ), "Grid should fit within terminal height"

    # Verify that the grid is more centered in the larger terminal
    assert new_x > initial_x, "Grid should move right in larger terminal"
    assert new_y > initial_y, "Grid should move down in larger terminal"

    # Verify that the grid is roughly centered
    expected_x = (mock_terminal.width - total_width) // 2
    expected_y = (mock_terminal.height - total_height) // 2
    assert abs(new_x - expected_x) <= 1, "Grid should be horizontally centered"
    assert abs(new_y - expected_y) <= 1, "Grid should be vertically centered"


def test_cleanup_game(
    config: ControllerConfig, mock_terminal: TerminalProtocol
) -> None:
    """
    Given: Running game state
    When: Cleaning up resources
    Then: Should restore terminal
    And: Should clear actor message queues
    """
    # Given
    terminal, actors = initialize_game(config)

    # When
    cleanup_game(terminal, actors)

    # Then
    for actor in actors:
        assert len(actor.subscribers) == 0
        assert actor.queue.empty()


def test_game_quit_and_cleanup(
    config: ControllerConfig, mock_terminal: TerminalProtocol
) -> None:
    """
    Given: A running game with active actors
    When: Quitting the game
    Then: Should clean up all resources
    And: Should terminate all actor threads
    And: Should restore terminal state
    """
    import time
    from threading import Thread

    from gol.grid import create_grid
    from gol.main import run_game_loop
    from gol.renderer import RendererState

    # Given
    mock_term = cast(MockTerminal, mock_terminal)  # Cast to access internal attributes
    mock_term._width = 80  # Ensure reasonable size
    mock_term._height = 24
    terminal = mock_terminal  # Use mock terminal directly

    # Patch initialize_terminal to return our mock
    from unittest.mock import patch

    with patch(
        "gol.controller.initialize_terminal",
        return_value=(mock_terminal, RendererState()),
    ):
        _, actors = initialize_game(config)
        grid = create_grid(config.grid)
        state = RendererState()

        # Run game in separate thread
        game_thread = Thread(target=run_game_loop, args=(terminal, grid, config, state))
        game_thread.start()

        # Let the game run for a short time
        time.sleep(0.1)

        # When - Simulate quit command with proper keystroke
        mock_term._input_queue.put(Keystroke("q", code=ord("q"), name="q"))

        # Then
        # Wait for game thread to end with timeout
        game_thread.join(timeout=1.0)
        assert not game_thread.is_alive(), "Game thread should have terminated"

        # Verify all actor queues are empty
        for actor in actors:
            assert actor.queue.empty(), "Actor queues should be empty"
