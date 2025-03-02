"""Terminal renderer for Game of Life."""

from dataclasses import dataclass
from time import time
from typing import Any, Dict, Literal, Optional, Protocol, Tuple

import psutil
from blessed import Terminal
from blessed.formatters import ParameterizingString
from blessed.keyboard import Keystroke

from .grid import Grid

# Type alias for cell positions
CellPos = Tuple[int, int]

# Get current process for metrics
_process = psutil.Process()


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
    @property
    def reverse(self) -> str: ...
    @property
    def black(self) -> str: ...
    @property
    def blue(self) -> str: ...
    @property
    def green(self) -> str: ...
    @property
    def yellow(self) -> str: ...
    @property
    def magenta(self) -> str: ...
    @property
    def on_blue(self) -> str: ...
    def move_xy(self, x: int, y: int) -> ParameterizingString: ...
    def exit_fullscreen(self) -> str: ...
    def enter_fullscreen(self) -> str: ...
    def hide_cursor(self) -> str: ...
    def normal_cursor(self) -> str: ...
    def clear(self) -> str: ...
    def enter_ca_mode(self) -> str: ...
    def exit_ca_mode(self) -> str: ...
    def inkey(self, timeout: float = 0) -> Keystroke: ...
    def cbreak(self) -> Any: ...


@dataclass
class RendererConfig:
    """Configuration for renderer."""

    cell_alive: str = "■"
    cell_dead: str = "□"
    cell_spacing: str = " "  # Space between cells
    update_interval: int = 100  # milliseconds
    refresh_per_second: int = None  # type: ignore # Calculated from interval
    min_interval: int = 10  # Minimum interval in milliseconds
    max_interval: int = 1000  # Maximum interval in milliseconds
    min_interval_step: int = 10  # Minimum step size for interval adjustments
    interval_change_factor: float = 0.2  # 20% change per adjustment

    def __post_init__(self) -> None:
        """Calculate refresh rate based on update interval."""
        self._update_refresh_rate()

    def _update_refresh_rate(self) -> None:
        """Update refresh rate based on current interval."""
        self.refresh_per_second = round(1000 / self.update_interval)

    def _round_to_step(self, value: int) -> int:
        """Round value to nearest step size."""
        return round(value / self.min_interval_step) * self.min_interval_step

    def increase_interval(self) -> None:
        """Increase update interval proportionally."""
        # Calculate proportional change
        change = max(
            self.min_interval_step,
            round(self.update_interval * self.interval_change_factor),
        )
        # Round to nearest step
        new_interval = self._round_to_step(self.update_interval + change)
        # Apply bounds
        self.update_interval = min(new_interval, self.max_interval)
        self._update_refresh_rate()

    def decrease_interval(self) -> None:
        """Decrease update interval proportionally."""
        # Calculate proportional change
        change = max(
            self.min_interval_step,
            round(self.update_interval * self.interval_change_factor),
        )
        # Round to nearest step
        new_interval = self._round_to_step(self.update_interval - change)
        # Apply bounds
        self.update_interval = max(new_interval, self.min_interval)
        self._update_refresh_rate()


@dataclass
class RendererState:
    """Maintains renderer state between frames."""

    previous_grid: Optional[Dict[CellPos, bool]] = None
    start_x: int = 0
    start_y: int = 0
    last_frame_time: float = 0.0
    frames_this_second: int = 0
    actual_fps: float = 0.0
    last_fps_update: float = 0.0
    total_cells: int = 0
    active_cells: int = 0
    messages_this_second: int = 0
    messages_per_second: float = 0.0
    last_message_update: float = 0.0
    changes_this_second: int = 0
    changes_per_second: float = 0.0
    cpu_percent: float = 0.0
    memory_mb: float = 0.0


CommandType = Literal["continue", "quit", "restart"]


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


def handle_user_input(
    terminal: TerminalProtocol, key: Keystroke, config: RendererConfig
) -> CommandType:
    """Handles keyboard input from user.

    Args:
        terminal: Terminal instance
        key: Keystroke from user containing input details
        config: Renderer configuration for adjusting settings

    Returns:
        CommandType: Command based on input:
            - Returns "quit" for 'q', 'Q', Ctrl-C (^C), or Escape
            - Returns "restart" for 'r' or 'R'
            - Returns "continue" for any other key

    Side effects:
        - Adjusts update_interval when up/down arrow keys are pressed
    """
    # Check for quit commands
    if (
        key.name in ("q", "Q", "^C", "KEY_ESCAPE", "escape")  # Named keys
        or key == "\x1b"  # Raw escape character
        or key == "\x03"  # Raw Ctrl-C
        or key in ("q", "Q")  # Raw key values
    ):
        return "quit"

    # Check for restart command
    if key.name in ("r", "R") or key in ("r", "R"):
        return "restart"

    # Handle interval adjustment
    if key.name == "KEY_UP":
        config.increase_interval()
    elif key.name == "KEY_DOWN":
        config.decrease_interval()

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


def clear_screen(terminal: TerminalProtocol) -> None:
    """Clears the terminal screen.

    Args:
        terminal: Terminal instance
    """
    print(terminal.clear())


def cleanup_terminal(terminal: TerminalProtocol) -> None:
    """Restores terminal to original state.

    Args:
        terminal: Terminal instance to cleanup
    """
    # Disable double buffering
    print(terminal.exit_ca_mode())
    print(terminal.exit_fullscreen() + terminal.normal_cursor())


def calculate_grid_position(
    terminal: TerminalProtocol, grid_width: int, grid_height: int
) -> tuple[int, int]:
    """Calculates centered position for grid.

    Args:
        terminal: Terminal instance
        grid_width: Width of the grid
        grid_height: Height of the grid

    Returns:
        Tuple of (start_x, start_y) coordinates for centered grid.
        If terminal is too small, returns (0, 0) to align grid to top-left corner.
    """
    # Calculate total grid dimensions including spacing
    total_width = grid_width * 2  # Each cell is 2 chars wide with spacing
    total_height = grid_height  # Each cell is 1 char high

    # Account for status line at bottom
    usable_height = terminal.height - 1

    # If terminal is smaller than grid in either dimension, align to top-left
    if terminal.width <= total_width or usable_height <= total_height:
        return 0, 0

    # Calculate center position
    center_y = usable_height // 2
    center_x = terminal.width // 2

    # Calculate top-left corner of grid
    start_y = center_y - (total_height // 2)
    start_x = center_x - (total_width // 2)

    # Ensure we don't start outside the terminal
    start_y = max(0, start_y)
    start_x = max(0, start_x)

    # Ensure grid doesn't extend beyond terminal edges
    start_x = min(start_x, terminal.width - total_width)
    start_y = min(start_y, usable_height - total_height)

    return start_x, start_y


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


def render_status_line(
    terminal: TerminalProtocol,
    config: RendererConfig,
    state: RendererState,
) -> str:
    """Renders status line at bottom of screen.

    Args:
        terminal: Terminal instance
        config: Renderer configuration
        state: Current renderer state

    Returns:
        String containing the rendered status line
    """
    # Update FPS calculation
    current_time = time()
    state.frames_this_second += 1
    state.messages_this_second += state.active_cells  # Each active cell sends a message

    # Update metrics every second
    if current_time - state.last_fps_update >= 1.0:
        state.actual_fps = state.frames_this_second
        state.messages_per_second = state.messages_this_second
        state.changes_per_second = state.changes_this_second
        state.frames_this_second = 0
        state.messages_this_second = 0
        state.changes_this_second = 0
        state.last_fps_update = current_time

        # Update process metrics
        state.cpu_percent = _process.cpu_percent()
        state.memory_mb = _process.memory_info().rss / 1024 / 1024  # Convert to MB

    # Create plain text version to calculate true length
    plain_cells = f"Cells: {state.total_cells}"
    plain_active = f"(Active: {state.active_cells})"
    plain_changes = f"Changes/s: {state.changes_per_second:.0f}"
    msg_count = state.messages_per_second / 1000
    plain_msgs = f"Msgs/s: {msg_count:.1f}k"
    plain_fps = f"FPS: {state.actual_fps:.1f}"
    plain_interval = f"Interval: {config.update_interval}ms"
    plain_cpu = f"CPU: {state.cpu_percent:.1f}%"

    # Calculate true length without escape sequences
    true_length = (
        len(plain_cells)
        + len(plain_active)
        + len(plain_changes)
        + len(plain_msgs)
        + len(plain_fps)
        + len(plain_interval)
        + len(plain_cpu)
        + len(" | ") * 5
        + len(" ")
    )

    # Format colored version
    cells = f"{terminal.blue}Cells: {terminal.normal}{state.total_cells}"
    active = f"({terminal.green}Active: {state.active_cells}{terminal.normal})"
    changes = (
        f"{terminal.magenta}Changes/s: {terminal.normal}{state.changes_per_second:.0f}"
    )
    msgs = f"{terminal.yellow}Msgs/s: {terminal.normal}{msg_count:.1f}k"
    fps = f"{terminal.blue}FPS: {terminal.normal}{state.actual_fps:.1f}"
    interval = (
        f"{terminal.magenta}Interval: {terminal.normal}{config.update_interval}ms"
    )
    cpu = f"{terminal.yellow}CPU: {terminal.normal}{state.cpu_percent:.1f}%"

    # Combine metrics with separators
    status = f"{cells} {active} | {changes} | {msgs} | {fps} | {interval} | {cpu}"

    # Position at bottom of screen
    y = terminal.height - 1

    # Center based on true content length
    x = (terminal.width - true_length) // 2
    x = max(0, x)  # Ensure we don't go negative

    # Clear the line and render the status
    return (
        terminal.move_xy(0, y) + " " * terminal.width + terminal.move_xy(x, y) + status
    )


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
    # Grid dimensions - grid is stored as [rows][columns]
    grid_height = len(grid)  # Number of rows
    grid_width = len(grid[0])  # Number of columns in first row

    # Reserve bottom line for status
    usable_height = terminal.height - 1

    start_x, start_y = calculate_grid_position(terminal, grid_width, grid_height)

    # Update stored position if changed
    if start_x != state.start_x or start_y != state.start_y:
        state.start_x = start_x
        state.start_y = start_y
        state.previous_grid = None  # Force full redraw on position change

    # Convert current grid to dictionary
    current_grid = grid_to_dict(grid)

    # Update statistics
    state.total_cells = grid_width * grid_height
    state.active_cells = sum(1 for cell in current_grid.values() if cell)

    # Count state changes if we have a previous grid
    if state.previous_grid is not None:
        state.changes_this_second += sum(
            1
            for pos, current_state in current_grid.items()
            if state.previous_grid.get(pos) != current_state
        )

    # If no previous state or position changed, do full redraw
    if state.previous_grid is None:
        clear_screen(terminal)
        buffer = []
        for (x, y), cell_state in current_grid.items():
            screen_x = start_x + (x * 2)  # Account for spacing
            screen_y = start_y + y
            if screen_y < usable_height:  # Don't render in status line area
                buffer.append(
                    render_cell(terminal, screen_x, screen_y, cell_state, config)
                )
        # Add status line without newline
        buffer.append(render_status_line(terminal, config, state))
        print("".join(buffer), end="", flush=True)
    else:
        # Only render cells that changed
        buffer = []
        for (x, y), cell_state in current_grid.items():
            if state.previous_grid.get((x, y)) != cell_state:
                screen_x = start_x + (x * 2)  # Account for spacing
                screen_y = start_y + y
                if screen_y < usable_height:  # Don't render in status line area
                    buffer.append(
                        render_cell(terminal, screen_x, screen_y, cell_state, config)
                    )
        # Always update status line without newline
        buffer.append(render_status_line(terminal, config, state))
        if buffer:
            print("".join(buffer), end="", flush=True)

    # Store current state for next frame
    state.previous_grid = current_grid


def safe_render_grid(
    terminal: TerminalProtocol,  # Accept any terminal that implements the protocol
    grid: Grid,
    config: RendererConfig,
    state: RendererState,
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
