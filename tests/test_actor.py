from dataclasses import dataclass
from queue import Empty, Queue
from threading import Event
from typing import NamedTuple

import pytest


# Position type for cell coordinates
class Position(NamedTuple):
    x: int
    y: int


# Actor type definition
@dataclass
class Actor:
    position: Position
    state: bool
    message_queue: Queue
    subscribers: list["Actor"]


def test_create_cell_actor_with_initial_state():
    """
    Given a position and initial state
    When creating a cell actor
    Then it should have correct position, state and empty queues
    """
    # Arrange
    pos = Position(1, 2)
    initial_state = True

    # Act
    from actor import create_cell_actor

    actor = create_cell_actor(pos, initial_state)

    # Assert
    assert actor.position == pos
    assert actor.state == initial_state
    assert isinstance(actor.message_queue, Queue)
    assert actor.message_queue.empty()
    assert actor.subscribers == []


def test_create_cell_actor_with_different_states():
    """
    Given different initial states
    When creating cell actors
    Then they should maintain their given states
    """
    # Arrange
    pos1 = Position(0, 0)
    pos2 = Position(1, 1)

    # Act
    from actor import create_cell_actor

    live_actor = create_cell_actor(pos1, True)
    dead_actor = create_cell_actor(pos2, False)

    # Assert
    assert live_actor.state is True
    assert dead_actor.state is False


@pytest.mark.parametrize(
    "current_state,live_neighbors,expected",
    [
        # Underpopulation cases
        (True, 0, False),  # Live cell with 0 neighbors dies
        (True, 1, False),  # Live cell with 1 neighbor dies
        # Survival cases
        (True, 2, True),  # Live cell with 2 neighbors survives
        (True, 3, True),  # Live cell with 3 neighbors survives
        # Overpopulation cases
        (True, 4, False),  # Live cell with 4 neighbors dies
        (True, 8, False),  # Live cell with 8 neighbors dies
        # Reproduction cases
        (False, 3, True),  # Dead cell with 3 neighbors becomes alive
        # Dead cell stays dead cases
        (False, 0, False),  # Dead cell with 0 neighbors stays dead
        (False, 2, False),  # Dead cell with 2 neighbors stays dead
        (False, 4, False),  # Dead cell with 4 neighbors stays dead
    ],
)
def test_calculate_next_state(current_state: bool, live_neighbors: int, expected: bool):
    """
    Given a cell's current state and number of live neighbors
    When calculating its next state
    Then it should follow Conway's Game of Life rules
    """
    # Act
    from actor import calculate_next_state

    next_state = calculate_next_state(current_state, live_neighbors)

    # Assert
    assert next_state == expected


def test_process_messages_updates_state():
    """
    Given a cell actor with state update messages in queue
    When processing messages
    Then should update state based on live neighbor count
    """
    # Arrange
    from actor import create_cell_actor, process_messages

    actor = create_cell_actor(Position(0, 0), True)
    completion_event = Event()

    # Add 3 live neighbor messages (survival case)
    for _ in range(3):
        actor.message_queue.put(True)

    # Act
    process_messages(actor, completion_event)
    completion_event.set()  # Signal completion

    # Assert
    assert actor.state is True  # Should survive with 3 neighbors


def test_process_messages_handles_empty_queue():
    """
    Given a cell actor with empty message queue
    When processing messages
    Then should maintain current state
    """
    # Arrange
    from actor import create_cell_actor, process_messages

    actor = create_cell_actor(Position(0, 0), True)
    completion_event = Event()
    initial_state = actor.state

    # Act
    process_messages(actor, completion_event)
    completion_event.set()

    # Assert
    assert actor.state == initial_state


def test_process_messages_handles_underpopulation():
    """
    Given a live cell actor with 1 live neighbor message
    When processing messages
    Then should die from underpopulation
    """
    # Arrange
    from actor import create_cell_actor, process_messages

    actor = create_cell_actor(Position(0, 0), True)
    completion_event = Event()

    # Add 1 live neighbor message (underpopulation case)
    actor.message_queue.put(True)

    # Act
    process_messages(actor, completion_event)
    completion_event.set()

    # Assert
    assert actor.state is False  # Should die with only 1 neighbor


def test_subscribe_to_neighbors():
    """
    Given a cell actor and list of neighbors
    When subscribing to neighbors
    Then actor should be added to their subscribers list
    """
    # Arrange
    from actor import create_cell_actor, subscribe_to_neighbors

    cell = create_cell_actor(Position(1, 1), False)
    neighbors = [
        create_cell_actor(Position(0, 0), True),
        create_cell_actor(Position(0, 1), False),
        create_cell_actor(Position(1, 0), True),
    ]

    # Act
    subscribe_to_neighbors(cell, neighbors)

    # Assert
    for neighbor in neighbors:
        assert cell in neighbor.subscribers


def test_broadcast_state():
    """
    Given a cell actor with subscribers
    When broadcasting state
    Then all subscribers should receive state message
    """
    # Arrange
    from actor import broadcast_state, create_cell_actor

    cell = create_cell_actor(Position(1, 1), True)
    subscribers = [
        create_cell_actor(Position(0, 0), False),
        create_cell_actor(Position(0, 1), False),
        create_cell_actor(Position(1, 0), False),
    ]
    cell.subscribers = subscribers

    # Act
    broadcast_state(cell)

    # Assert - each subscriber should have cell's state in queue
    for subscriber in subscribers:
        assert not subscriber.message_queue.empty()
        assert subscriber.message_queue.get() == cell.state
