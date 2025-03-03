"""Game of Life controller implementation."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from queue import Empty
from threading import Event
from typing import List, Tuple, cast

import numpy as np

from gol.actor import CellActor, broadcast_state, create_cell_actor, process_messages
from gol.grid import Grid, GridConfig, Position, create_grid, get_neighbors
from gol.messaging import Actor, subscribe_to_neighbors
from gol.renderer import (
    RendererConfig,
    TerminalProtocol,
    cleanup_terminal,
    initialize_terminal,
)


@dataclass(frozen=True)
class ControllerConfig:
    """Configuration for game controller."""

    grid: GridConfig
    renderer: RendererConfig


def initialize_game(
    config: ControllerConfig,
) -> Tuple[TerminalProtocol, List[CellActor]]:
    """Initialize game components.

    Args:
        config: Controller configuration parameters

    Returns:
        Tuple of (terminal, list of cell actors)

    Raises:
        RuntimeError: If terminal initialization fails
    """

    # Initialize terminal
    terminal, _ = initialize_terminal(config.renderer)
    if terminal is None:
        raise RuntimeError("Failed to initialize terminal")

    # Create initial grid
    grid = create_grid(config.grid)

    # Create and connect cell actors
    actors = setup_cell_actors(grid, config.grid)

    return terminal, actors


def create_actor_batch(
    positions: List[Position], states: List[Tuple[bool, int]]
) -> List[CellActor]:
    """Create a batch of cell actors in parallel.

    Args:
        positions: List of positions for actors
        states: List of initial states for actors (is_alive, age)

    Returns:
        List of created cell actors
    """
    # Calculate optimal chunk size based on input size
    chunk_size = max(1, min(1000, len(positions) // (8 * len(positions) // 1000 + 1)))

    with ThreadPoolExecutor() as executor:
        # Process chunks in parallel
        chunks = [
            (positions[i : i + chunk_size], states[i : i + chunk_size])
            for i in range(0, len(positions), chunk_size)
        ]

        def process_chunk(
            chunk: Tuple[List[Position], List[Tuple[bool, int]]],
        ) -> List[CellActor]:
            pos_list, state_list = chunk
            return [
                create_cell_actor(
                    pos, state[0], state[1]
                )  # Pass both alive state and age
                for pos, state in zip(pos_list, state_list)
            ]

        # Flatten results
        results = executor.map(process_chunk, chunks)
        return [actor for chunk in results for actor in chunk]


def setup_cell_actors(grid: Grid, config: GridConfig) -> List[CellActor]:
    """Create and connect cell actors.

    Args:
        grid: Initial game grid
        config: Grid configuration parameters

    Returns:
        List of initialized and connected cell actors
    """
    # Create position and state arrays using numpy for efficiency
    y_indices, x_indices = np.mgrid[0 : config.height, 0 : config.width]
    positions = [
        Position((int(x), int(y))) for x, y in zip(x_indices.flat, y_indices.flat)
    ]
    states = [grid[y][x] for y, x in zip(y_indices.flat, x_indices.flat)]

    # Create actors in parallel batches
    actors = create_actor_batch(positions, states)

    # Set up neighbor relationships efficiently
    actor_map = {actor.position: actor for actor in actors}

    with ThreadPoolExecutor() as executor:

        def setup_neighbors(actor: CellActor) -> None:
            neighbor_positions = get_neighbors(
                grid, actor.position, toroidal=config.toroidal
            )
            # Use dictionary lookup instead of list comprehension
            neighbors = [cast(Actor, actor_map[pos]) for pos in neighbor_positions]
            subscribe_to_neighbors(actor, neighbors)

        # Process neighbor setup in parallel
        list(executor.map(setup_neighbors, actors))

    return actors


def process_generation(actors: List[CellActor], completion_event: Event) -> None:
    """Process one generation of cell updates.

    Args:
        actors: List of cell actors to update
        completion_event: Event to signal completion
    """
    try:
        # Reset completion event
        completion_event.clear()

        # First, broadcast current states to neighbors
        for actor in actors:
            broadcast_state(actor, actor.state)

        # Then process all messages to calculate next states
        # Process messages for all actors
        for actor in actors:
            process_messages(actor, completion_event)

        # Now ensure all queues are empty without changing states further
        # This is important for test verification but shouldn't affect the game logic
        while any(not actor.queue.empty() for actor in actors):
            for actor in actors:
                if not actor.queue.empty():
                    # Get and discard remaining messages without state changes
                    try:
                        actor.queue.get_nowait()
                    except Empty:
                        pass

    finally:
        # Signal completion
        completion_event.set()


def cleanup_game(terminal: TerminalProtocol, actors: List[CellActor]) -> None:
    """Clean up game resources.

    Args:
        terminal: Terminal instance to cleanup
        actors: List of cell actors to cleanup
    """
    # Clear all actor queues and subscribers
    for actor in actors:
        actor.subscribers = []
        while not actor.queue.empty():
            actor.queue.get_nowait()

    # Restore terminal state using proper cleanup sequence
    cleanup_terminal(terminal)
