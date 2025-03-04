"""Terminal renderer for Game of Life."""

import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional, Protocol, Tuple, runtime_checkable

import psutil
from blessed import Terminal
from blessed.formatters import ParameterizingString
from blessed.keyboard import Keystroke

from .grid import Grid, Position
from .patterns import (
    BUILTIN_PATTERNS,
    FilePatternStorage,
    get_centered_position,
    get_pattern_cells,
)

# Type alias for cell positions and states
CellPos = Tuple[int, int]

# Get current process for metrics
_process = psutil.Process()


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
    update_interval: int = 200  # milliseconds
    refresh_per_second: int = None  # type: ignore # Calculated from interval
    min_interval: int = 10  # Minimum interval in milliseconds
    max_interval: int = 1000  # Maximum interval in milliseconds
    min_interval_step: int = 10  # Minimum step size for interval adjustments
    interval_change_factor: float = 0.2  # 20% change per adjustment
    selected_pattern: Optional[str] = None
    pattern_rotation: int = 0

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

    def set_pattern(self, pattern_name: Optional[str], rotation: int = 0) -> None:
        """Set the selected pattern and rotation.

        Args:
            pattern_name: Name of the pattern to select, or None to clear
            rotation: Pattern rotation in degrees (0, 90, 180, 270)
        """
        self.selected_pattern = pattern_name
        self.pattern_rotation = rotation


@dataclass
class RendererState:
    """Maintains renderer state between frames."""

    previous_grid: Optional[Dict[CellPos, bool]] = None
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
    previous_pattern_cells: set[CellPos] = None  # type: ignore
    was_in_pattern_mode: bool = False
    pattern_menu: str = ""


CommandType = Literal[
    "continue",
    "quit",
    "restart",
    "pattern",
    "move_cursor_left",
    "move_cursor_right",
    "move_cursor_up",
    "move_cursor_down",
    "place_pattern",
    "rotate_pattern",
    "exit_pattern",
]


# Type aliases
TerminalResult = Tuple[Optional[TerminalProtocol], Optional[RendererState]]


def initialize_terminal(
    config: RendererConfig,
) -> Tuple[Optional[TerminalProtocol], Optional[RendererState]]:
    """Initialize terminal for game display.

    Args:
        config: Renderer configuration

    Returns:
        Tuple of (terminal, state) if successful, (None, None) otherwise
    """
    try:
        # Initialize terminal
        terminal = Terminal()

        # Enter alternate screen mode and hide cursor
        print(terminal.enter_fullscreen(), end="", flush=True)
        print(terminal.hide_cursor(), end="", flush=True)

        # Clear screen
        print(terminal.clear(), end="", flush=True)

        # Initialize renderer state
        state = RendererState()

        return terminal, state
    except Exception:
        if "terminal" in locals():
            cleanup_terminal(terminal)
        return None, None


def handle_user_input(
    terminal: TerminalProtocol,
    key: Keystroke,
    config: RendererConfig,
    state: RendererState,
) -> CommandType:
    """Handles keyboard input from user.

    Args:
        terminal: Terminal instance
        key: Keystroke from user containing input details
        config: Renderer configuration for adjusting settings
        state: Current renderer state

    Returns:
        CommandType: Command based on input:
            - Returns "quit" for 'q', 'Q', Ctrl-C (^C), or ESC (not in pattern mode)
            - Returns "restart" for 'r' or 'R' (when not in pattern mode)
            - Returns "pattern" for 'p' or 'P'
            - Returns "exit_pattern" for Escape (in pattern mode)
            - Returns movement commands for arrow keys in pattern mode
            - Returns "place_pattern" for space
            - Returns "rotate_pattern" for 'r' or 'R' (when in pattern mode)
            - Returns "continue" for any other key
    """
    # Check for quit commands
    if (
        key.name in ("q", "Q", "^C")  # Named keys
        or key == "\x03"  # Raw Ctrl-C
        or key in ("q", "Q")  # Raw key values
        or (key.name == "KEY_ESCAPE" and not state.pattern_mode)  # ESC
        or (key == "\x1b" and not state.pattern_mode)  # Raw ESC
    ):
        return "quit"

    # Check for Escape key to exit pattern mode
    if (key.name == "KEY_ESCAPE" or key == "\x1b") and state.pattern_mode:
        return "exit_pattern"

    # Check for restart/rotate command
    if key.name in ("r", "R") or key in ("r", "R"):
        if state.pattern_mode:  # In pattern mode
            return "rotate_pattern"
        return "restart"

    # Check for pattern mode
    if key.name in ("p", "P") or key in ("p", "P"):
        return "pattern"

    # Handle pattern selection via number keys
    if key.isdigit():
        patterns = list(BUILTIN_PATTERNS.keys()) + FilePatternStorage().list_patterns()
        pattern_idx = int(key) - 1  # Convert to 0-based index
        if 0 <= pattern_idx < len(patterns):
            config.set_pattern(patterns[pattern_idx])
        return "continue"

    # Handle cursor movement in pattern mode or interval changes in game mode
    if key.name == "KEY_LEFT":
        if state.pattern_mode:
            return "move_cursor_left"
        return "continue"
    elif key.name == "KEY_RIGHT":
        if state.pattern_mode:
            return "move_cursor_right"
        return "continue"
    elif key.name == "KEY_UP":
        if state.pattern_mode:
            return "move_cursor_up"
        else:
            config.increase_interval()
        return "continue"
    elif key.name == "KEY_DOWN":
        if state.pattern_mode:
            return "move_cursor_down"
        else:
            config.decrease_interval()
        return "continue"

    # Handle pattern placement
    if key == " " or key.name == "KEY_SPACE":
        return "place_pattern"

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
        print(terminal.normal_cursor(), end="", flush=True)  # Show cursor
        print(terminal.exit_ca_mode(), end="", flush=True)  # Exit alternate screen
        print(terminal.exit_fullscreen(), end="", flush=True)
        print(terminal.normal, end="", flush=True)  # Reset attributes
        print(terminal.clear(), end="", flush=True)  # Clear screen
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


def grid_to_dict(grid: Grid) -> Dict[CellPos, bool]:
    """Convert grid to dictionary for efficient lookup.

    Args:
        grid: Grid to convert

    Returns:
        Dictionary mapping cell positions to states
    """
    return {(x, y): grid[y][x] for y in range(len(grid)) for x in range(len(grid[0]))}


def render_cell(
    terminal: TerminalProtocol,
    x: int,
    y: int,
    is_alive: bool,
    config: RendererConfig,
) -> str:
    """Render a single cell.

    Args:
        terminal: Terminal instance
        x: X coordinate
        y: Y coordinate
        is_alive: Whether cell is alive
        config: Renderer configuration

    Returns:
        String to render cell
    """
    if is_alive:
        # Use bright white for maximum visibility
        return (
            terminal.white + config.cell_alive + terminal.normal + config.cell_spacing
        )
    # Make dead cells very dim
    return terminal.dim + config.cell_dead + terminal.normal + config.cell_spacing


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


def render_pattern_menu(
    terminal: TerminalProtocol,
    config: RendererConfig,
    state: RendererState,
) -> str:
    """Renders pattern selection menu.

    Args:
        terminal: Terminal instance
        config: Renderer configuration
        state: Current renderer state

    Returns:
        String containing the rendered pattern menu
    """
    # Get available patterns
    patterns = list(BUILTIN_PATTERNS.keys()) + FilePatternStorage().list_patterns()

    # Create menu text
    pattern_list = ", ".join(f"{i+1}:{name}" for i, name in enumerate(patterns))
    menu_text = (
        f"Pattern Mode - Select: {pattern_list} | R: rotate | Space: place | ESC: exit"
    )

    # Calculate true length without escape sequences
    true_length = len(menu_text)

    # Position at bottom of screen
    y = terminal.height - 1

    # Center based on true content length
    x = (terminal.width - true_length) // 2
    x = max(0, x)  # Ensure we don't go negative

    # Clear line and render menu
    return (
        terminal.move_xy(0, y)
        + " " * terminal.width
        + terminal.move_xy(x, y)
        + terminal.blue
        + menu_text
        + terminal.normal
    )


def render_grid(
    terminal: TerminalProtocol, grid: Grid, config: RendererConfig, state: RendererState
) -> None:
    """Renders current grid state.

    Args:
        terminal: Terminal instance
        grid: Grid to render
        config: Renderer configuration
        state: Current renderer state
    """
    # Grid dimensions - grid is stored as [rows][columns]
    grid_height = len(grid)  # Number of rows
    grid_width = len(grid[0])  # Number of columns in first row

    # Reserve bottom two lines for menu and status
    usable_height = terminal.height - 2

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

    # Track births and deaths if we have a previous grid
    if state.previous_grid is not None:
        for pos, current_state in current_grid.items():
            previous_state = state.previous_grid.get(pos)
            if previous_state is not None:
                if not previous_state and current_state:
                    state.births_this_second += 1
                elif previous_state and not current_state:
                    state.deaths_this_second += 1

    # Get pattern preview cells if in pattern mode
    pattern_cells = set()
    if state.pattern_mode:
        if config.selected_pattern:
            pattern = BUILTIN_PATTERNS.get(
                config.selected_pattern
            ) or FilePatternStorage().load_pattern(config.selected_pattern)

            if pattern:
                # Get centered position for pattern preview
                preview_pos = get_centered_position(
                    pattern, Position((state.cursor_x, state.cursor_y))
                )
                cells = get_pattern_cells(pattern, config.pattern_rotation)
                # Add all pattern cells to the set, adjusting for centered position
                for dx, dy in cells:
                    x = (preview_pos[0] + dx) % grid_width
                    y = (preview_pos[1] + dy) % grid_height
                    pattern_cells.add((x, y))

    # Track previous pattern cells to detect changes
    previous_pattern_cells = state.previous_pattern_cells or set()
    force_redraw = (
        state.previous_grid is None or state.pattern_mode != state.was_in_pattern_mode
    )

    # If no previous state, position changed, or pattern mode changed, do full redraw
    if force_redraw:
        # Clear entire terminal area
        buffer = [terminal.clear()]

        # Clear each line in the grid area to prevent artifacts
        for y in range(usable_height):
            buffer.append(str(terminal.move_xy(0, y)))
            buffer.append(" " * terminal.width)

        # First render the base grid
        for (x, y), cell_state in current_grid.items():
            screen_x = start_x + (x * 2)  # Account for spacing
            screen_y = start_y + y
            if screen_y < usable_height:  # Don't render in status line area
                buffer.append(str(terminal.move_xy(screen_x, screen_y)))
                # Only render base grid if not a pattern cell
                if not state.pattern_mode or (x, y) not in pattern_cells:
                    buffer.append(
                        render_cell(terminal, screen_x, screen_y, cell_state, config)
                    )

        # Then overlay pattern preview if in pattern mode
        if state.pattern_mode:
            for x, y in pattern_cells:
                screen_x = start_x + (x * 2)  # Account for spacing
                screen_y = start_y + y
                if screen_y < usable_height:  # Don't render in status line area
                    buffer.append(str(terminal.move_xy(screen_x, screen_y)))
                    buffer.append(
                        terminal.yellow
                        + config.cell_alive
                        + terminal.normal
                        + config.cell_spacing
                    )

            # Add pattern menu instead of status line
            buffer.append(render_pattern_menu(terminal, config, state))
        else:
            # Add status line when not in pattern mode
            buffer.append(render_status_line(terminal, config, state))

        print("".join(buffer), end="", flush=True)
    else:
        # Only render cells that changed
        buffer = []

        # Update cells that changed in the base grid
        for (x, y), cell_state in current_grid.items():
            should_update = (state.previous_grid or {}).get((x, y)) != cell_state or (
                (x, y) in pattern_cells
            ) != ((x, y) in previous_pattern_cells)
            if should_update:
                screen_x = start_x + (x * 2)  # Account for spacing
                screen_y = start_y + y
                if screen_y < usable_height:  # Don't render in status line area
                    buffer.append(str(terminal.move_xy(screen_x, screen_y)))
                    if not state.pattern_mode or (x, y) not in pattern_cells:
                        buffer.append(
                            render_cell(
                                terminal, screen_x, screen_y, cell_state, config
                            )
                        )
                    elif state.pattern_mode and (x, y) in pattern_cells:
                        buffer.append(
                            terminal.yellow
                            + config.cell_alive
                            + terminal.normal
                            + config.cell_spacing
                        )

        # Update bottom line based on mode
        if state.pattern_mode:
            buffer.append(render_pattern_menu(terminal, config, state))
        else:
            buffer.append(render_status_line(terminal, config, state))

        if buffer:
            print("".join(buffer), end="", flush=True)

    # Store current state for next frame
    state.previous_grid = current_grid
    state.previous_pattern_cells = pattern_cells
    state.was_in_pattern_mode = state.pattern_mode


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
