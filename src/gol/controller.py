"""Game of Life controller implementation."""

from dataclasses import dataclass
from threading import Event
from typing import List, Tuple

from blessed import Terminal

from gol.actor import CellActor, create_cell_actor, process_messages
from gol.grid import Grid, GridConfig, Position, create_grid, get_neighbors
from gol.messaging import Actor, subscribe_to_neighbors
from gol.renderer import RendererConfig, initialize_terminal


@dataclass(frozen=True)
class ControllerConfig:
    """Configuration for game controller."""

    grid: GridConfig
    renderer: RendererConfig


def initialize_game(config: ControllerConfig) -> Tuple[Terminal, List[CellActor]]:
    """Initialize game components.

    Args:
        config: Controller configuration parameters

    Returns:
        Tuple of (terminal, list of cell actors)
    """
    # Initialize terminal
    terminal = initialize_terminal(config.renderer)

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

        # Broadcast current states
        for actor in actors:
            actor.subscribers = []  # Clear old subscribers
            actor.queue.queue.clear()  # Clear old messages

        # Process all messages
        for actor in actors:
            process_messages(actor, completion_event)

    finally:
        # Signal completion
        completion_event.set()


def cleanup_game(terminal: Terminal, actors: List[CellActor]) -> None:
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

    # Restore terminal state
    terminal.exit_fullscreen()
    terminal.normal_cursor()
