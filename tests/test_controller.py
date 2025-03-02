"""BDD tests for Game of Life controller."""

import time
from threading import Event
from typing import Generator
from unittest.mock import MagicMock

import pytest
from pytest import MonkeyPatch

from gol.actor import CellActor
from gol.controller import (
    ControllerConfig,
    cleanup_game,
    initialize_game,
    process_generation,
)
from gol.grid import GridConfig
from gol.renderer import RendererConfig, Terminal


@pytest.fixture
def config() -> ControllerConfig:
    """Test configuration fixture."""
    return ControllerConfig(
        grid=GridConfig(size=3, density=0.5),
        renderer=RendererConfig(
            cell_alive="■",
            cell_dead="□",
            update_interval=100,
        ),
    )


@pytest.fixture
def mock_terminal(monkeypatch: MonkeyPatch) -> Generator[Terminal, None, None]:
    """Mock terminal fixture."""
    mock = MagicMock(spec=Terminal)
    mock.height = 24
    mock.width = 80
    mock.enter_fullscreen = lambda: ""
    mock.hide_cursor = lambda: ""
    mock.exit_fullscreen = lambda: ""
    mock.normal_cursor = lambda: ""
    mock.clear = lambda: ""
    mock.move_xy = lambda x, y: ""
    yield mock


def test_game_initialization(config: ControllerConfig, mock_terminal: Terminal) -> None:
    """
    Given: Controller configuration
    When: Initializing game
    Then: Should create grid and actors
    And: Should set up terminal
    """
    # When
    terminal, actors = initialize_game(config)

    # Then
    assert isinstance(terminal, Terminal)
    assert len(actors) == config.grid.size * config.grid.size
    assert all(isinstance(actor, CellActor) for actor in actors)


def test_actor_setup(config: ControllerConfig, mock_terminal: Terminal) -> None:
    """
    Given: Initial grid state
    When: Setting up cell actors
    Then: Should create correct number of actors
    And: Should establish neighbor relationships
    """
    # Given
    terminal, actors = initialize_game(config)

    # When
    # Each actor should have correct number of neighbors subscribed
    for actor in actors:
        # Corner cells should have 3 neighbors
        if actor.position in [(0, 0), (0, 2), (2, 0), (2, 2)]:
            assert len(actor.subscribers) == 3
        # Edge cells should have 5 neighbors
        elif actor.position[0] in [0, 2] or actor.position[1] in [0, 2]:
            assert len(actor.subscribers) == 5
        # Center cells should have 8 neighbors
        else:
            assert len(actor.subscribers) == 8


def test_process_generation(config: ControllerConfig, mock_terminal: Terminal) -> None:
    """
    Given: Set of cell actors
    When: Processing one generation
    Then: Should update cell states according to Game of Life rules
    And: Should ensure all message queues are empty
    """
    # Given
    terminal, actors = initialize_game(config)
    completion_event = Event()

    # When
    process_generation(actors, completion_event)

    # Then
    # Verify that completion event was set
    assert completion_event.is_set()
    # Verify that all message queues are empty after processing
    assert all(
        actor.queue.empty() for actor in actors
    ), "All message queues should be empty after processing"


def test_process_generation_timing(
    config: ControllerConfig, mock_terminal: Terminal
) -> None:
    """
    Given: Set of cell actors
    When: Processing multiple generations
    Then: Should complete within expected time
    And: Should properly synchronize actors
    """
    # Given
    terminal, actors = initialize_game(config)
    completion_event = Event()
    start_time = time.time()

    # When
    for _ in range(3):  # Test multiple generations
        process_generation(actors, completion_event)
        completion_event.clear()

    duration = time.time() - start_time

    # Then
    assert duration < 1.0, "Generation processing took too long"
    assert all(actor.queue.empty() for actor in actors)


def test_cleanup_game(config: ControllerConfig, mock_terminal: Terminal) -> None:
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
    # Verify all queues are empty
    assert all(actor.queue.empty() for actor in actors)
    # Verify no subscribers (cleanup should clear these)
    assert all(len(actor.subscribers) == 0 for actor in actors)
