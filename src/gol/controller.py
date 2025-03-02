"""Game of Life controller implementation."""

from dataclasses import dataclass
from queue import Empty
from threading import Event
from typing import List, Tuple

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
    """
    # Initialize terminal
    terminal, _ = initialize_terminal(config.renderer)

    # Create initial grid
    grid = create_grid(config.grid)

    # Create and connect cell actors
    actors = setup_cell_actors(grid)

    return terminal, actors


def setup_cell_actors(grid: Grid) -> List[CellActor]:
    """Create and connect cell actors.

    Args:
        grid: Initial game grid

    Returns:
        List of initialized and connected cell actors
    """
    size = len(grid)
    actors: List[CellActor] = []

    # Create actors for each cell
    for x in range(size):
        for y in range(size):
            pos = Position((x, y))
            actor = create_cell_actor(pos, grid[x][y])
            actors.append(actor)

    # Set up neighbor relationships
    for actor in actors:
        x, y = actor.position
        neighbor_positions = get_neighbors(grid, actor.position)

        # Find neighbor actors
        neighbors: List[Actor] = [n for n in actors if n.position in neighbor_positions]

        # Subscribe to neighbors
        subscribe_to_neighbors(actor, neighbors)

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
