from queue import Queue
from threading import Event
from typing import Sequence

from gol.actor import broadcast_state, create_cell_actor, process_messages
from gol.grid import Position
from gol.messaging import Actor


def test_create_cell_actor() -> None:
    """
    Given a position and initial state
    When creating a cell actor
    Then it should implement the Actor protocol
    """
    # Arrange
    pos = Position((1, 2))
    initial_state = True

    # Act
    actor = create_cell_actor(pos, initial_state)

    # Assert
    assert isinstance(actor.id, str)  # Should have unique ID
    assert actor.position == pos
    assert actor.state == initial_state
    assert isinstance(actor.queue, Queue)
    assert actor.queue.empty()
    assert actor.subscribers == []


def test_process_messages_updates_state() -> None:
    """
    Given a cell actor with state update messages in queue
    When processing messages
    Then should update state based on live neighbor count
    """
    # Arrange
    actor = create_cell_actor(Position((0, 0)), True)
    completion_event = Event()

    # Create neighbor actors and send state updates
    neighbors = []
    for i in range(3):  # Add 3 live neighbors
        neighbor = create_cell_actor(Position((i + 1, 0)), True)
        neighbor.id = f"neighbor_{i}"
        neighbors.append(neighbor)
        actor.queue.put((neighbor.id, True))

    # Act
    process_messages(actor, completion_event)
    completion_event.set()

    # Assert
    assert actor.state is True  # Should survive with 3 neighbors


def test_process_messages_handles_empty_queue() -> None:
    """
    Given a cell actor with empty message queue
    When processing messages
    Then should maintain current state
    """
    # Arrange
    actor = create_cell_actor(Position((0, 0)), True)
    completion_event = Event()
    initial_state = actor.state

    # Act
    process_messages(actor, completion_event)
    completion_event.set()

    # Assert
    assert actor.state == initial_state


def test_process_messages_handles_underpopulation() -> None:
    """
    Given a live cell actor with 1 live neighbor message
    When processing messages
    Then should die from underpopulation
    """
    # Arrange
    actor = create_cell_actor(Position((0, 0)), True)
    completion_event = Event()

    # Add 1 live neighbor message (underpopulation case)
    neighbor = create_cell_actor(Position((1, 0)), True)
    neighbor.id = "neighbor_1"
    actor.queue.put((neighbor.id, True))

    # Act
    process_messages(actor, completion_event)
    completion_event.set()

    # Assert
    assert actor.state is False  # Should die with only 1 neighbor


def test_broadcast_state_to_subscribers() -> None:
    """
    Given a cell actor with subscribers
    When broadcasting state
    Then all subscribers should receive state message
    """
    # Arrange
    actor = create_cell_actor(Position((1, 1)), True)
    actor.id = "test_cell"

    # Create subscribers as a sequence of actors
    subscribers: Sequence[Actor] = [
        create_cell_actor(Position((i, i)), False) for i in range(3)
    ]
    actor.subscribers = list(subscribers)

    # Act
    broadcast_state(actor, actor.state)

    # Assert - each subscriber should have actor's state in queue
    for subscriber in subscribers:
        message = subscriber.queue.get_nowait()
        assert message == (actor.id, True)
