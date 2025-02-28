"""Message queue system for inter-actor communication."""

from queue import Queue
from typing import Any, Protocol


class Actor(Protocol):
    """Protocol defining the required attributes for an actor."""

    id: str
    queue: Queue[Any]
    subscribers: list["Actor"]
    state: bool


def create_message_queue() -> Queue[Any]:
    """Creates a thread-safe message queue.

    Returns:
        A new Queue instance with unlimited capacity
    """
    return Queue()


def subscribe_to_neighbors(actor: Actor, neighbors: list[Actor]) -> None:
    """Sets up message subscriptions between cells.

    Args:
        actor: The actor subscribing to updates
        neighbors: List of actors to subscribe to
    """
    for neighbor in neighbors:
        neighbor.subscribers.append(actor)


def broadcast_state(actor: Actor, state: bool) -> None:
    """Broadcasts state changes to subscribers.

    Args:
        actor: The actor broadcasting its state
        state: The new state to broadcast
    """
    message = (actor.id, state)
    for subscriber in actor.subscribers:
        subscriber.queue.put_nowait(message)
