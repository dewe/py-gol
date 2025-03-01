from dataclasses import dataclass
from queue import Empty, Queue
from threading import Event
from typing import List, NamedTuple


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


def create_cell_actor(position: Position, initial_state: bool) -> Actor:
    """Creates a cell actor with message queue

    Args:
        position: The x,y coordinates of the cell
        initial_state: True for live cell, False for dead cell

    Returns:
        Actor: A new cell actor instance with empty message queue and subscribers
    """
    return Actor(
        position=position, state=initial_state, message_queue=Queue(), subscribers=[]
    )


def calculate_next_state(current: bool, live_neighbors: int) -> bool:
    """Pure function implementing Conway's Game of Life rules

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


def process_messages(actor: Actor, completion_event: Event) -> None:
    """Process state update messages from neighboring cells

    Args:
        actor: The cell actor to process messages for
        completion_event: Threading event to signal processing completion

    This function processes all available messages in the queue to determine
    the next state based on the number of live neighbors.
    """
    live_neighbors = 0
    has_messages = False

    # Process all available messages without blocking
    while not completion_event.is_set():
        try:
            # Try to get a message without blocking
            neighbor_state = actor.message_queue.get_nowait()
            has_messages = True
            if neighbor_state:  # Count live neighbors
                live_neighbors += 1
        except Empty:
            break  # No more messages in queue

    # Only update state if we received any messages
    if has_messages:
        actor.state = calculate_next_state(actor.state, live_neighbors)


def subscribe_to_neighbors(cell: Actor, neighbors: List[Actor]) -> None:
    """Subscribe a cell to receive state updates from its neighbors

    Args:
        cell: The cell actor to subscribe
        neighbors: List of neighboring cell actors

    This function adds the cell to each neighbor's subscriber list so it
    will receive state updates from them.
    """
    for neighbor in neighbors:
        neighbor.subscribers.append(cell)


def broadcast_state(cell: Actor) -> None:
    """Broadcast cell's current state to all subscribers

    Args:
        cell: The cell actor whose state to broadcast

    This function sends the cell's current state to all subscribed neighbors
    via their message queues.
    """
    for subscriber in cell.subscribers:
        subscriber.message_queue.put(cell.state)
