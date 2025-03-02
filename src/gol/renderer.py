"""Terminal renderer for Game of Life."""

from dataclasses import dataclass
from typing import Dict, Literal, Optional, Protocol, Tuple

from blessed import Terminal
from blessed.formatters import ParameterizingString
from blessed.keyboard import Keystroke

from .grid import Grid

# Type alias for cell positions
CellPos = Tuple[int, int]


class TerminalProtocol(Protocol):
    """Protocol defining the required terminal interface."""

    @property
    def width(self) -> int: ...
    @property
    def height(self) -> int: ...
    @property
    def dim(self) -> str: ...
    @property
    def normal(self) -> str: ...
    def move_xy(self, x: int, y: int) -> ParameterizingString: ...
    def exit_fullscreen(self) -> str: ...
    def enter_fullscreen(self) -> str: ...
    def hide_cursor(self) -> str: ...
    def normal_cursor(self) -> str: ...
    def clear(self) -> str: ...
    def enter_ca_mode(self) -> str: ...
    def exit_ca_mode(self) -> str: ...


@dataclass(frozen=True)
class RendererConfig:
    """Configuration for renderer."""

    cell_alive: str = "■"
    cell_dead: str = "□"
    cell_spacing: str = " "  # Space between cells
    update_interval: int = 100  # milliseconds
    refresh_per_second: int = 5  # Lower refresh rate for larger grids


@dataclass
class RendererState:
    """Maintains renderer state between frames."""

    previous_grid: Optional[Dict[CellPos, bool]] = None
    start_x: int = 0
    start_y: int = 0


CommandType = Literal["continue", "quit"]


def initialize_terminal(
    config: RendererConfig,
) -> Tuple[TerminalProtocol, RendererState]:
    """Sets up blessed terminal interface.

    Args:
        config: Renderer configuration parameters

    Returns:
        Tuple of (Terminal instance, RendererState)
    """
    term = Terminal()

    # Enter fullscreen mode with alternate screen buffer
    print(term.enter_fullscreen() + term.hide_cursor())

    # Enable double buffering by using alternate screen
    print(term.enter_ca_mode())

    return term, RendererState()


def cleanup_terminal(terminal: TerminalProtocol) -> None:
    """Restores terminal to original state.

    Args:
        terminal: Terminal instance to cleanup
    """
    # Disable double buffering
    print(terminal.exit_ca_mode())
    print(terminal.exit_fullscreen() + terminal.normal_cursor())


def calculate_grid_position(
    terminal: TerminalProtocol, grid_size: int
) -> tuple[int, int]:
    """Calculates centered position for grid.

    Args:
        terminal: Terminal instance
        grid_size: Size of the grid

    Returns:
        Tuple of (start_x, start_y) coordinates for centered grid.
        If terminal is too small, returns (0, 0) to align grid to top-left corner.
    """
    # Calculate total grid dimensions including spacing
    total_width = grid_size * 2  # Each cell is 2 chars wide with spacing
    total_height = grid_size  # Each cell is 1 char high

    # If terminal is smaller than grid in either dimension, align to top-left
    if terminal.width <= total_width or terminal.height <= total_height:
        return 0, 0

    # Calculate center position
    center_y = terminal.height // 2
    center_x = terminal.width // 2

    # Calculate top-left corner of grid
    start_y = center_y - (total_height // 2)
    start_x = center_x - (total_width // 2)

    # Ensure we don't start outside the terminal
    start_y = max(0, start_y)
    start_x = max(0, start_x)

    # Ensure grid doesn't extend beyond terminal edges
    start_x = min(start_x, terminal.width - total_width)
    start_y = min(start_y, terminal.height - total_height)

    return start_x, start_y


def clear_screen(terminal: TerminalProtocol) -> None:
    """Clears the terminal screen.

    Args:
        terminal: Terminal instance
    """
    print(terminal.clear())


def grid_to_dict(grid: Grid) -> Dict[CellPos, bool]:
    """Convert grid to dictionary for efficient comparison.

    Args:
        grid: Current game grid

    Returns:
        Dictionary mapping positions to cell states
    """
    return {(x, y): cell for y, row in enumerate(grid) for x, cell in enumerate(row)}


def render_cell(
    terminal: TerminalProtocol, x: int, y: int, state: bool, config: RendererConfig
) -> str:
    """Render a single cell.

    Args:
        terminal: Terminal instance
        x: Cell x coordinate
        y: Cell y coordinate
        state: Cell state
        config: Renderer configuration

    Returns:
        String to render the cell
    """
    char = config.cell_alive if state else config.cell_dead
    # Apply dim attribute to dead cells
    if not state:
        char = terminal.dim + char + terminal.normal
    return terminal.move_xy(x, y) + char + config.cell_spacing


def render_grid(
    terminal: TerminalProtocol, grid: Grid, config: RendererConfig, state: RendererState
) -> None:
    """Renders current grid state.

    Args:
        terminal: Terminal instance
        grid: Current game grid
        config: Renderer configuration
        state: Current renderer state
    """
    grid_size = len(grid)
    start_x, start_y = calculate_grid_position(terminal, grid_size)

    # Update stored position if changed
    if start_x != state.start_x or start_y != state.start_y:
        state.start_x = start_x
        state.start_y = start_y
        state.previous_grid = None  # Force full redraw on position change

    # Convert current grid to dictionary
    current_grid = grid_to_dict(grid)

    # If no previous state or position changed, do full redraw
    if state.previous_grid is None:
        clear_screen(terminal)
        buffer = []
        for (x, y), cell_state in current_grid.items():
            screen_x = start_x + (x * 2)  # Account for spacing
            screen_y = start_y + y
            if screen_y < terminal.height:
                buffer.append(
                    render_cell(terminal, screen_x, screen_y, cell_state, config)
                )
        print("".join(buffer))
    else:
        # Only render cells that changed
        buffer = []
        for (x, y), cell_state in current_grid.items():
            if state.previous_grid.get((x, y)) != cell_state:
                screen_x = start_x + (x * 2)  # Account for spacing
                screen_y = start_y + y
                if screen_y < terminal.height:
                    buffer.append(
                        render_cell(terminal, screen_x, screen_y, cell_state, config)
                    )
        if buffer:
            print("".join(buffer), end="", flush=True)

    # Store current state for next frame
    state.previous_grid = current_grid


def handle_user_input(terminal: TerminalProtocol, key: Keystroke) -> CommandType:
    """Handles keyboard input from user.

    Args:
        terminal: Terminal instance
        key: Keystroke from user containing input details

    Returns:
        CommandType: Either "quit" or "continue" based on input:
            - Returns "quit" for 'q', 'Q', Ctrl-C (^C), or Escape
            - Returns "continue" for any other key
    """
    # Check for quit commands (q, Q, Ctrl-C, or Escape)
    if key.name in ("q", "Q", "^C", "KEY_ESCAPE"):
        return "quit"

    # All other keys continue the game
    return "continue"


def handle_resize_event(terminal: TerminalProtocol, state: RendererState) -> None:
    """Handles terminal resize events.

    Args:
        terminal: Terminal instance to handle resize for
        state: Current renderer state
    """
    # Force full redraw on next frame
    state.previous_grid = None

    # Clear screen to prevent artifacts
    clear_screen(terminal)

    # Re-hide cursor as resize can reset terminal state
    print(terminal.hide_cursor())


def safe_render_grid(
    terminal: TerminalProtocol, grid: Grid, config: RendererConfig, state: RendererState
) -> None:
    """Safely renders grid with error handling.

    Args:
        terminal: Terminal instance
        grid: Current game grid
        config: Renderer configuration
        state: Current renderer state

    This function wraps render_grid with error handling to ensure
    the terminal is always left in a valid state, even if rendering fails.
    """
    try:
        render_grid(terminal, grid, config, state)
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
