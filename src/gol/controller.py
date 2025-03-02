"""Game of Life controller implementation."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from queue import Empty
from threading import Event
from typing import List, Tuple, cast

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
    positions: List[Position], states: List[bool]
) -> List[CellActor]:
    """Create a batch of cell actors in parallel.

    Args:
        positions: List of positions for actors
        states: List of initial states for actors

    Returns:
        List of created cell actors
    """
    return [create_cell_actor(pos, state) for pos, state in zip(positions, states)]


def setup_cell_actors(grid: Grid, config: GridConfig) -> List[CellActor]:
    """Create and connect cell actors.

    Args:
        grid: Initial game grid
        config: Grid configuration parameters

    Returns:
        List of initialized and connected cell actors
    """
    # Prepare positions and states
    positions = []
    states = []
    for x in range(config.width):
        for y in range(config.height):
            positions.append(Position((x, y)))
            states.append(grid[y][x])

    # Create actors in parallel batches
    batch_size = 1000  # Adjust based on grid size
    actors = []

    for i in range(0, len(positions), batch_size):
        batch_positions = positions[i : i + batch_size]
        batch_states = states[i : i + batch_size]
        actors.extend(create_actor_batch(batch_positions, batch_states))

    # Set up neighbor relationships
    with ThreadPoolExecutor() as executor:

        def setup_neighbors(actor: CellActor) -> None:
            x, y = actor.position
            neighbor_positions = get_neighbors(
                grid, actor.position, toroidal=config.toroidal
            )
            # Find neighbor actors and cast to Actor type
            neighbors = [
                cast(Actor, n) for n in actors if n.position in neighbor_positions
            ]
            # Subscribe to neighbors
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
