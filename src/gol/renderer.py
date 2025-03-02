"""Terminal renderer for Game of Life."""

from dataclasses import dataclass
from typing import Literal

from blessed import Terminal
from blessed.keyboard import Keystroke

from .grid import Grid


@dataclass(frozen=True)
class RendererConfig:
    """Configuration for renderer."""

    cell_alive: str = "■"
    cell_dead: str = "□"
    cell_spacing: str = " "  # Space between cells
    update_interval: int = 100  # milliseconds


CommandType = Literal["continue", "quit"]


def initialize_terminal(config: RendererConfig) -> Terminal:
    """Sets up blessed terminal interface.

    Args:
        config: Renderer configuration parameters

    Returns:
        Configured blessed Terminal instance
    """
    term = Terminal()

    # Enter fullscreen mode
    print(term.enter_fullscreen())

    # Hide cursor
    print(term.hide_cursor())

    return term


def cleanup_terminal(terminal: Terminal) -> None:
    """Restores terminal to original state.

    Args:
        terminal: Terminal instance to cleanup
    """
    print(terminal.exit_fullscreen())
    print(terminal.normal_cursor())


def calculate_grid_position(terminal: Terminal, grid_size: int) -> tuple[int, int]:
    """Calculates centered position for grid.

    Args:
        terminal: Terminal instance
        grid_size: Size of the grid

    Returns:
        Tuple of (start_x, start_y) coordinates for centered grid
    """
    # Calculate center position
    center_y = terminal.height // 2
    center_x = terminal.width // 2

    # Calculate top-left corner of grid
    # Account for cell width (1 char) plus spacing (1 char)
    total_width = grid_size * 2  # Each cell is now 2 chars wide with spacing
    start_y = center_y - (grid_size // 2)
    start_x = center_x - (total_width // 2)

    # Ensure we don't start outside the terminal
    start_y = max(0, start_y)
    start_x = max(0, start_x)

    return start_x, start_y


def clear_screen(terminal: Terminal) -> None:
    """Clears the terminal screen.

    Args:
        terminal: Terminal instance
    """
    print(terminal.clear())


def render_grid(terminal: Terminal, grid: Grid, config: RendererConfig) -> None:
    """Renders current grid state.

    Args:
        terminal: Terminal instance
        grid: Current game grid
        config: Renderer configuration
    """
    # Clear the screen before rendering
    clear_screen(terminal)

    # Calculate grid position
    grid_size = len(grid)
    start_x, start_y = calculate_grid_position(terminal, grid_size)

    # Build and render each line
    for y, row in enumerate(grid):
        # Skip if we're outside the terminal
        if start_y + y >= terminal.height:
            break

        line = ""
        for x, cell in enumerate(row):
            char = config.cell_alive if cell else config.cell_dead
            line += char + config.cell_spacing  # Add spacing between cells

        # Position cursor and print line
        print(terminal.move_xy(start_x, start_y + y) + line)


def handle_user_input(terminal: Terminal, key: Keystroke) -> CommandType:
    """Handles keyboard input from user.

    Args:
        terminal: Terminal instance
        key: Keystroke from user containing input details

    Returns:
        CommandType: Either "quit" or "continue" based on input:
            - Returns "quit" for 'q', 'Q' or Ctrl-C (^C)
            - Returns "continue" for 'x' or any other key
    """
    # Check for quit commands (q, Q, or Ctrl-C)
    if key.name in ("q", "Q", "^C"):
        return "quit"

    # All other keys (including 'x') continue the game
    return "continue"


def handle_resize_event(terminal: Terminal) -> None:
    """Handles terminal resize events.

    Args:
        terminal: Terminal instance to handle resize for
    """
    # Clear screen to prevent artifacts
    clear_screen(terminal)

    # Re-hide cursor as resize can reset terminal state
    print(terminal.hide_cursor())


def safe_render_grid(terminal: Terminal, grid: Grid, config: RendererConfig) -> None:
    """Safely renders grid with error handling.

    Args:
        terminal: Terminal instance
        grid: Current game grid
        config: Renderer configuration

    This function wraps render_grid with error handling to ensure
    the terminal is always left in a valid state, even if rendering fails.
    """
    try:
        render_grid(terminal, grid, config)
    except (IOError, ValueError) as e:
        # Handle I/O errors (like broken pipe) and value errors
        cleanup_terminal(terminal)
        raise RuntimeError(f"Failed to render grid: {e}") from e
    except KeyboardInterrupt:
        # Handle Ctrl-C gracefully
        cleanup_terminal(terminal)
        raise
    except Exception as e:
        # Handle any other unexpected errors
        cleanup_terminal(terminal)
        raise RuntimeError(f"Unexpected error during rendering: {e}") from e
