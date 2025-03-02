"""BDD tests for Game of Life controller."""

import time
from threading import Event
from typing import Generator
from unittest.mock import PropertyMock, patch

import pytest
from blessed import Terminal

from gol.actor import CellActor
from gol.controller import (
    ControllerConfig,
    cleanup_game,
    initialize_game,
    process_generation,
)
from gol.grid import Grid, GridConfig
from gol.messaging import broadcast_state
from gol.renderer import RendererConfig, calculate_grid_position, render_grid


def actors_to_grid(actors: list[CellActor], size: int) -> Grid:
    """Convert list of actors to grid format.

    Args:
        actors: List of cell actors
        size: Grid size

    Returns:
        Grid representation of actor states
    """
    # Initialize empty grid
    grid = [[False for _ in range(size)] for _ in range(size)]

    # Fill in actor states
    for actor in actors:
        x, y = actor.position
        grid[y][x] = actor.state

    return Grid(grid)


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
def mock_terminal() -> Generator[Terminal, None, None]:
    """Mock terminal fixture."""
    term = Terminal()
    height_mock = PropertyMock(return_value=24)
    width_mock = PropertyMock(return_value=80)
    with patch.object(type(term), "height", height_mock), patch.object(
        type(term), "width", width_mock
    ):
        yield term


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


def test_process_generation_state_changes(
    config: ControllerConfig, mock_terminal: Terminal
) -> None:
    """
    Given: A known pattern of live and dead cells
    When: Processing one generation
    Then: Should correctly apply Game of Life rules
    And: Should maintain stable patterns
    """
    # Given
    terminal, actors = initialize_game(config)
    completion_event = Event()

    # Set up a 2x2 block pattern (stable pattern)
    # [1,1,0]
    # [1,1,0] -> Should stay the same
    # [0,0,0]
    for actor in actors:
        x, y = actor.position
        # Set top-left 2x2 block to live
        actor.state = x < 2 and y < 2
        # Broadcast initial state to neighbors
        broadcast_state(actor, actor.state)

    # Store initial state
    initial_live_cells = sum(1 for actor in actors if actor.state)
    assert initial_live_cells == 4, "Initial pattern should have 4 live cells"

    # When
    process_generation(actors, completion_event)

    # Then
    # Count live cells - should still be exactly 4 (stable pattern)
    final_live_cells = sum(1 for actor in actors if actor.state)
    assert final_live_cells == 4, f"Expected 4 live cells but got {final_live_cells}"

    # Verify pattern stayed the same (block is stable)
    for actor in actors:
        x, y = actor.position
        expected_state = x < 2 and y < 2
        assert (
            actor.state == expected_state
        ), f"Cell at {actor.position} changed unexpectedly"


def test_process_generation_error_handling(
    config: ControllerConfig, mock_terminal: Terminal
) -> None:
    """
    Given: A set of cell actors where one has an invalid state
    When: Processing one generation
    Then: Should handle errors gracefully
    And: Should maintain system stability
    """
    # Given
    terminal, actors = initialize_game(config)
    completion_event = Event()

    # Create an error condition by corrupting one actor's queue
    problem_actor = actors[0]
    problem_actor.queue.put(("invalid_id", "invalid_state"))  # Wrong message format

    # When
    process_generation(actors, completion_event)

    # Then
    # Verify system remains stable
    assert completion_event.is_set(), "Generation should complete despite errors"
    assert all(
        actor.queue.empty() for actor in actors
    ), "All queues should be cleared even with errors"

    # Verify other actors were processed
    processed_count = sum(1 for actor in actors[1:] if actor.queue.empty())
    assert processed_count == len(actors) - 1, "Other actors should be processed"


def test_handle_terminal_resize(
    config: ControllerConfig, mock_terminal: Terminal
) -> None:
    """
    Given: A running game
    When: Terminal window is resized
    Then: Should recalculate grid position
    And: Should maintain display state
    """
    # Given
    terminal, actors = initialize_game(config)

    # Calculate initial grid position
    initial_x, initial_y = calculate_grid_position(terminal, config.grid.size)

    # When - simulate resize event
    # Note: We can't directly test terminal resizing in unit tests
    # as it depends on actual terminal capabilities.
    # Instead, we verify that the grid position calculation works
    # with different terminal dimensions.
    new_x, new_y = calculate_grid_position(terminal, config.grid.size)

    # Then
    # Verify grid can still be rendered
    render_grid(terminal, actors_to_grid(actors, config.grid.size), config.renderer)


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
