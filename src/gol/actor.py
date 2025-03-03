"""Cell actor implementation for Game of Life."""

from dataclasses import dataclass
from queue import Empty, Queue
from threading import Event
from typing import Any, Tuple
from uuid import uuid4

from gol.grid import Position
from gol.messaging import Actor as ActorProtocol
from gol.messaging import broadcast_message


@dataclass
class CellActor:
    """Cell actor implementation."""

    id: str
    position: Position
    state: bool
    age: int
    queue: Queue[Any]
    subscribers: list[ActorProtocol]


def create_cell_actor(
    position: Position, initial_state: bool, initial_age: int = 0
) -> CellActor:
    """Creates a cell actor with message queue.

    Args:
        position: The x,y coordinates of the cell
        initial_state: True for live cell, False for dead cell
        initial_age: Initial age of the cell (default 0)

    Returns:
        A new cell actor instance with empty message queue and subscribers
    """
    return CellActor(
        id=str(uuid4()),
        position=position,
        state=initial_state,
        age=initial_age,
        queue=Queue(),
        subscribers=[],
    )


def calculate_next_state(
    is_alive: bool, age: int, live_neighbors: int
) -> Tuple[bool, int]:
    """Pure function implementing Conway's Game of Life rules with aging.

    Args:
        is_alive: Current state of the cell (True for live, False for dead)
        age: Current age of the cell
        live_neighbors: Number of live neighboring cells (0-8)

    Returns:
        Tuple[bool, int]: Next state and age of the cell based on Game of Life rules
    """
    if is_alive:
        if live_neighbors in (2, 3):  # Survives
            return True, age + 1
        else:  # Dies
            return False, 0
    else:
        if live_neighbors == 3:  # Becomes alive
            return True, 1
        else:  # Stays dead
            return False, 0


def process_messages(actor: CellActor, completion_event: Event) -> None:
    """Process state update messages from neighboring cells.

    Args:
        actor: The cell actor to process messages for
        completion_event: Threading event to signal processing completion
    """
    live_neighbors = 0
    has_messages = False
    neighbor_states = {}  # Track latest state per neighbor

    # Process all available messages without blocking
    while not completion_event.is_set():
        try:
            # Try to get a message without blocking
            neighbor_id, state = actor.queue.get_nowait()
            has_messages = True
            neighbor_states[neighbor_id] = state
        except Empty:
            break  # No more messages in queue

    # Count unique live neighbors
    live_neighbors = sum(1 for state in neighbor_states.values() if state)

    # Only update state if we received any messages
    if has_messages:
        new_state, new_age = calculate_next_state(
            actor.state, actor.age, live_neighbors
        )
        # Update state and age if either changes
        if new_state != actor.state or new_age != actor.age:
            actor.state = new_state
            actor.age = new_age
            broadcast_state(actor, new_state)  # Broadcast state to neighbors


def broadcast_state(actor: CellActor, state: bool) -> None:
    """Broadcast cell's current state to all subscribers.

    Args:
        actor: The cell actor whose state to broadcast
        state: The state to broadcast
    """
    # We only broadcast the alive/dead state to neighbors
    # Age is only used for rendering and doesn't affect neighbor calculations
    broadcast_message(actor, state)
