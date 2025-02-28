"""Tests for message queue system."""

from dataclasses import dataclass
from queue import Empty, Queue
from threading import Event
from typing import Any


@dataclass
class MockActor:
    """Mock actor for testing message queue system."""

    id: str
    queue: Queue[Any]
    subscribers: list["MockActor"]
    state: bool = False


def test_create_message_queue() -> None:
    """
    Given a request to create a message queue
    When creating the queue
    Then should return a thread-safe Queue instance
    """
    from gol.messaging import create_message_queue

    queue = create_message_queue()

    assert isinstance(queue, Queue)
    assert queue.maxsize == 0  # Unlimited queue size


def test_subscribe_to_neighbors() -> None:
    """
    Given two actors
    When one subscribes to the other
    Then should be added to subscribers list
    """
    from gol.messaging import create_message_queue, subscribe_to_neighbors

    # Create actors
    actor1 = MockActor("1", create_message_queue(), [])
    actor2 = MockActor("2", create_message_queue(), [])

    # Subscribe actor1 to actor2
    subscribe_to_neighbors(actor1, [actor2])

    assert actor1 in actor2.subscribers


def test_broadcast_state() -> None:
    """
    Given an actor with subscribers
    When broadcasting state change
    Then all subscribers should receive the update
    """
    from gol.messaging import (
        broadcast_state,
        create_message_queue,
        subscribe_to_neighbors,
    )

    # Create actors
    publisher = MockActor("pub", create_message_queue(), [])
    subscriber1 = MockActor("sub1", create_message_queue(), [])
    subscriber2 = MockActor("sub2", create_message_queue(), [])

    # Set up subscriptions
    subscribe_to_neighbors(subscriber1, [publisher])
    subscribe_to_neighbors(subscriber2, [publisher])

    # Broadcast state change
    new_state = True
    broadcast_state(publisher, new_state)

    # Check that subscribers received the message
    msg1 = subscriber1.queue.get_nowait()
    msg2 = subscriber2.queue.get_nowait()

    assert msg1 == (publisher.id, new_state)
    assert msg2 == (publisher.id, new_state)
    assert subscriber1.queue.empty()
    assert subscriber2.queue.empty()


def test_message_queue_thread_safety() -> None:
    """
    Given multiple threads using the same queue
    When sending messages concurrently
    Then all messages should be delivered without data races
    """
    import threading

    from gol.messaging import broadcast_state, create_message_queue

    # Create actors
    publisher = MockActor("pub", create_message_queue(), [])
    subscriber = MockActor("sub", create_message_queue(), [])
    publisher.subscribers = [subscriber]

    # Number of messages each thread will send
    msg_count = 100
    received_count = 0
    completion_event = Event()

    def send_messages() -> None:
        for _ in range(msg_count):
            broadcast_state(publisher, True)

    def receive_messages() -> None:
        nonlocal received_count
        while received_count < msg_count * 2:  # Two sender threads
            try:
                subscriber.queue.get_nowait()
                received_count += 1
            except Empty:
                if completion_event.is_set():
                    break

    # Create and start threads
    sender1 = threading.Thread(target=send_messages)
    sender2 = threading.Thread(target=send_messages)
    receiver = threading.Thread(target=receive_messages)

    sender1.start()
    sender2.start()
    receiver.start()

    # Wait for senders to finish
    sender1.join(timeout=1)
    sender2.join(timeout=1)
    completion_event.set()
    receiver.join(timeout=1)

    assert received_count == msg_count * 2
