"""Cell actor implementation for Game of Life."""

from dataclasses import dataclass
from queue import Empty, Queue
from threading import Event
from typing import Any
from uuid import uuid4

from gol.grid import Position
from gol.messaging import Actor as ActorProtocol
from gol.messaging import broadcast_state as broadcast_message


@dataclass
class CellActor:
    """Cell actor implementation."""

    id: str
    position: Position
    state: bool
    queue: Queue[Any]
    subscribers: list[ActorProtocol]


def create_cell_actor(position: Position, initial_state: bool) -> CellActor:
    """Creates a cell actor with message queue.

    Args:
        position: The x,y coordinates of the cell
        initial_state: True for live cell, False for dead cell

    Returns:
        A new cell actor instance with empty message queue and subscribers
    """
    return CellActor(
        id=str(uuid4()),
        position=position,
        state=initial_state,
        queue=Queue(),
        subscribers=[],
    )


def calculate_next_state(current: bool, live_neighbors: int) -> bool:
    """Pure function implementing Conway's Game of Life rules.

    Args:
        current: Current state of the cell (True for live, False for dead)
        live_neighbors: Number of live neighboring cells (0-8)

    Returns:
        bool: Next state of the cell based on Game of Life rules
    """
    if current:
        # Live cell rules
        return live_neighbors in (2, 3)  # Survives with 2-3 neighbors, dies otherwise
    else:
        # Dead cell rules
        return live_neighbors == 3  # Becomes alive with exactly 3 neighbors


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
        new_state = calculate_next_state(actor.state, live_neighbors)
        if new_state != actor.state:
            actor.state = new_state
            broadcast_state(actor, new_state)


def broadcast_state(actor: CellActor, state: bool) -> None:
    """Broadcast cell's current state to all subscribers.

    Args:
        actor: The cell actor whose state to broadcast
        state: The state to broadcast
    """
    broadcast_message(actor, state)
