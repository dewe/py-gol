"""Terminal renderer for Game of Life."""

import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional, Protocol, Tuple, runtime_checkable

import psutil
from blessed import Terminal
from blessed.formatters import ParameterizingString
from blessed.keyboard import Keystroke

from .grid import Grid

# Type alias for cell positions and states
CellPos = Tuple[int, int]
CellState = Tuple[bool, int]  # (is_alive, age)

# Get current process for metrics
_process = psutil.Process()

# Age color thresholds and their meanings
AGE_COLORS = [
    (1, 15),  # white - youngest
    (3, 250),  # light gray
    (5, 247),  # gray
    (10, 133),  # faded pink
    (20, 89),  # dark pink
    (float("inf"), 52),  # dark red - oldest
]


@runtime_checkable
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
    def white(self) -> str: ...
    @property
    def blue(self) -> str: ...
    @property
    def green(self) -> str: ...
    @property
    def yellow(self) -> str: ...
    @property
    def magenta(self) -> str: ...
    @property
    def red(self) -> str: ...
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

    previous_grid: Optional[Dict[CellPos, CellState]] = None
    start_x: int = 0
    start_y: int = 0
    terminal_width: int = 0
    terminal_height: int = 0
    last_frame_time: float = 0.0
    generation_count: int = 0
    total_cells: int = 0
    active_cells: int = 0
    births_this_second: int = 0
    deaths_this_second: int = 0
    birth_rate: float = 0.0
    death_rate: float = 0.0
    last_stats_update: float = 0.0
    frames_this_second: int = 0
    actual_fps: float = 0.0
    last_fps_update: float = 0.0
    messages_this_second: int = 0
    messages_per_second: float = 0.0
    last_message_update: float = 0.0
    changes_this_second: int = 0
    changes_per_second: float = 0.0
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    pattern_mode: bool = False
    cursor_x: int = 0
    cursor_y: int = 0


CommandType = Literal["continue", "quit", "restart", "pattern"]


def initialize_terminal(
    config: RendererConfig,
) -> Tuple[TerminalProtocol, RendererState]:
    """Sets up blessed terminal interface.

    Args:
        config: Renderer configuration parameters

    Returns:
        Tuple of (Terminal instance, RendererState)
    """
    try:
        term = Terminal()

        # Clear screen and hide cursor
        sys.stdout.write(term.enter_ca_mode())
        sys.stdout.write(term.hide_cursor())
        sys.stdout.write(term.clear())
        sys.stdout.flush()

        return term, RendererState()
    except Exception as e:
        print(f"Failed to initialize terminal: {str(e)}", file=sys.stderr)
        raise


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
            - Returns "pattern" for 'p' or 'P'
            - Returns "continue" for any other key

    Side effects:
        - Adjusts update_interval when up/down arrow keys are pressed
    """
    # Check for quit commands
    if (
        key.name in ("q", "Q", "^C", "KEY_ESCAPE")  # Named keys
        or key == "\x1b"  # Raw escape character
        or key == "\x03"  # Raw Ctrl-C
        or key in ("q", "Q")  # Raw key values
        or key.code == 27  # Escape key code
    ):
        return "quit"

    # Check for restart command
    if key.name in ("r", "R") or key in ("r", "R"):
        return "restart"

    # Check for pattern mode
    if key.name in ("p", "P") or key in ("p", "P"):
        return "pattern"

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
    try:
        # Restore terminal to normal state
        sys.stdout.write(terminal.exit_ca_mode())
        sys.stdout.write(terminal.normal_cursor())
        sys.stdout.write(terminal.clear())
        sys.stdout.flush()
    except Exception as e:
        print(f"Error during terminal cleanup: {str(e)}", file=sys.stderr)


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


def grid_to_dict(grid: Grid) -> Dict[CellPos, CellState]:
    """Converts grid to dictionary format for comparison.

    Args:
        grid: Current grid state

    Returns:
        Dictionary mapping positions to cell states (is_alive, age)
    """
    return {(x, y): grid[y][x] for y in range(len(grid)) for x in range(len(grid[0]))}


def render_cell(
    terminal: TerminalProtocol,
    x: int,
    y: int,
    cell_state: CellState,
    config: RendererConfig,
) -> str:
    """Renders a single cell.

    Args:
        terminal: Terminal instance
        x: X coordinate
        y: Y coordinate
        cell_state: Tuple of (is_alive, age)
        config: Renderer configuration

    Returns:
        String to render cell
    """
    is_alive, age = cell_state
    if not is_alive:
        return str(
            terminal.dim + config.cell_dead + terminal.normal + config.cell_spacing
        )

    # Get color code based on age
    color_code = AGE_COLORS[0][1]  # Default to youngest color
    for threshold, code in AGE_COLORS:
        if age <= threshold:
            color_code = code
            break

    # Apply ANSI color code without dimming
    colored_cell = f"\x1b[38;5;{color_code}m{config.cell_alive}"
    return f"{colored_cell}{terminal.normal}{config.cell_spacing}"


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
    # Update statistics every second
    current_time = time.time()
    if current_time - state.last_stats_update >= 1.0:
        state.birth_rate = state.births_this_second
        state.death_rate = state.deaths_this_second
        state.births_this_second = 0
        state.deaths_this_second = 0
        state.last_stats_update = current_time

    # Create plain text version to calculate true length
    plain_pop = f"Population: {state.active_cells}"
    plain_gen = f"Generation: {state.generation_count}"
    plain_births = f"Births/s: {state.birth_rate:.1f}"
    plain_deaths = f"Deaths/s: {state.death_rate:.1f}"
    plain_interval = f"Interval: {config.update_interval}ms"

    # Calculate true length without escape sequences
    true_length = (
        len(plain_pop)
        + len(plain_gen)
        + len(plain_births)
        + len(plain_deaths)
        + len(plain_interval)
        + len(" | ") * 4
        + len(" ")
    )

    # Format colored version
    pop = f"{terminal.blue}Population: {terminal.normal}{state.active_cells}"
    gen = f"{terminal.green}Generation: {terminal.normal}{state.generation_count}"
    births = f"{terminal.magenta}Births/s: {terminal.normal}{state.birth_rate:.1f}"
    deaths = f"{terminal.yellow}Deaths/s: {terminal.normal}{state.death_rate:.1f}"
    interval = f"{terminal.white}Interval: {terminal.normal}{config.update_interval}ms"

    # Combine metrics with separators
    status = f"{pop} | {gen} | {births} | {deaths} | {interval}"

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
    state.active_cells = sum(
        1 for cell in current_grid.values() if cell[0]
    )  # Check is_alive field

    # Track births and deaths if we have a previous grid
    if state.previous_grid is not None:
        for pos, current_state in current_grid.items():
            previous_state = state.previous_grid.get(pos)
            if previous_state is not None:
                # Count births (was dead, now alive)
                if not previous_state[0] and current_state[0]:
                    state.births_this_second += 1
                # Count deaths (was alive, now dead)
                elif previous_state[0] and not current_state[0]:
                    state.deaths_this_second += 1

    # If no previous state or position changed, do full redraw
    if state.previous_grid is None:
        # Clear entire terminal area
        buffer = [terminal.clear()]

        # Clear each line in the grid area to prevent artifacts
        for y in range(usable_height):
            buffer.append(str(terminal.move_xy(0, y)))
            buffer.append(" " * terminal.width)

        # Render grid cells
        for (x, y), cell_state in current_grid.items():
            screen_x = start_x + (x * 2)  # Account for spacing
            screen_y = start_y + y
            if screen_y < usable_height:  # Don't render in status line area
                buffer.append(str(terminal.move_xy(screen_x, screen_y)))
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
                    buffer.append(str(terminal.move_xy(screen_x, screen_y)))
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
