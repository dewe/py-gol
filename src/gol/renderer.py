"""Terminal renderer for Game of Life."""

import sys
from dataclasses import dataclass
from typing import Any, Literal, Optional, Protocol, Tuple, runtime_checkable

import numpy as np
from blessed import Terminal
from blessed.formatters import ParameterizingString
from blessed.keyboard import Keystroke

from .metrics import Metrics, update_frame_metrics, update_game_metrics
from .patterns import (
    BUILTIN_PATTERNS,
    FilePatternStorage,
    PatternTransform,
    get_centered_position,
    get_pattern_cells,
)
from .state import RendererState
from .types import Grid, RenderGrid, ScreenPosition

CellPos = ScreenPosition


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
    def white(self) -> str: ...
    @property
    def blue(self) -> str: ...
    @property
    def green(self) -> str: ...
    @property
    def yellow(self) -> str: ...
    @property
    def magenta(self) -> str: ...
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


@dataclass(frozen=True)
class RendererConfig:
    """Configuration for renderer.

    This class is immutable. All modifications return new instances.
    """

    cell_alive: str = "■"
    cell_dead: str = "□"
    cell_spacing: str = " "
    update_interval: int = 200
    refresh_per_second: int = 5
    min_interval: int = 10
    max_interval: int = 1000
    min_interval_step: int = 10
    interval_change_factor: float = 0.2
    selected_pattern: Optional[str] = None
    pattern_rotation: PatternTransform = PatternTransform.NONE

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "refresh_per_second", round(1000 / self.update_interval)
        )

    def _round_to_step(self, value: int) -> int:
        return round(value / self.min_interval_step) * self.min_interval_step

    def with_increased_interval(self) -> "RendererConfig":
        from dataclasses import replace

        change = max(
            self.min_interval_step,
            round(self.update_interval * self.interval_change_factor),
        )
        new_interval = self._round_to_step(self.update_interval + change)
        return replace(self, update_interval=min(new_interval, self.max_interval))

    def with_decreased_interval(self) -> "RendererConfig":
        from dataclasses import replace

        change = max(
            self.min_interval_step,
            round(self.update_interval * self.interval_change_factor),
        )
        new_interval = self._round_to_step(self.update_interval - change)
        return replace(self, update_interval=max(new_interval, self.min_interval))

    def with_pattern(
        self,
        pattern_name: Optional[str],
        rotation: PatternTransform = PatternTransform.NONE,
    ) -> "RendererConfig":
        from dataclasses import replace

        return replace(self, selected_pattern=pattern_name, pattern_rotation=rotation)


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
    "cycle_boundary",
    "resize_larger",
    "resize_smaller",
    "exit_pattern",
]

TerminalResult = Tuple[Optional[TerminalProtocol], Optional[RendererState]]


def initialize_terminal() -> TerminalResult:
    """Initialize terminal for game display in fullscreen mode.

    Sets up alternate screen buffer and hides cursor for clean rendering.
    """
    try:
        terminal = Terminal()
        print(terminal.enter_fullscreen(), end="", flush=True)
        print(terminal.hide_cursor(), end="", flush=True)
        print(terminal.clear(), end="", flush=True)
        state = RendererState.create()
        return terminal, state
    except Exception:
        if "terminal" in locals():
            cleanup_terminal(terminal)
        return None, None


def handle_user_input(
    key: Keystroke,
    config: RendererConfig,
    state: RendererState,
) -> tuple[CommandType, RendererConfig]:
    """Handles keyboard input from user."""
    if (
        key.name in ("q", "Q", "^C")
        or key == "\x03"
        or key in ("q", "Q")
        or (key.name == "KEY_ESCAPE" and not state.pattern_mode)
        or (key == "\x1b" and not state.pattern_mode)
    ):
        return "quit", config

    if (key.name == "KEY_ESCAPE" or key == "\x1b") and state.pattern_mode:
        return "exit_pattern", config

    if key.name in ("r", "R") or key in ("r", "R"):
        if state.pattern_mode:
            new_config = config.with_pattern(
                config.selected_pattern,
                config.pattern_rotation.next_rotation(),
            )
            return "rotate_pattern", new_config
        return "restart", config

    if key.name in ("p", "P") or key in ("p", "P"):
        return "pattern", config

    if key in ("+", "="):
        return "resize_larger", config
    if key == "-":
        return "resize_smaller", config

    if key.isdigit():
        patterns = list(BUILTIN_PATTERNS.keys()) + FilePatternStorage().list_patterns()
        pattern_idx = int(key) - 1
        if 0 <= pattern_idx < len(patterns):
            new_config = config.with_pattern(patterns[pattern_idx])
            return "continue", new_config
        return "continue", config

    if key.name == "KEY_LEFT":
        if state.pattern_mode:
            return "move_cursor_left", config
        return "continue", config
    elif key.name == "KEY_RIGHT":
        if state.pattern_mode:
            return "move_cursor_right", config
        return "continue", config
    elif key.name == "KEY_UP":
        if state.pattern_mode:
            return "move_cursor_up", config
        else:
            new_config = config.with_increased_interval()
            return "continue", new_config
    elif key.name == "KEY_DOWN":
        if state.pattern_mode:
            return "move_cursor_down", config
        else:
            new_config = config.with_decreased_interval()
            return "continue", new_config

    if key == " " or key.name == "KEY_SPACE":
        return "place_pattern", config

    return "continue", config


def handle_resize_event(
    terminal: TerminalProtocol, state: RendererState
) -> RendererState:
    """Handles terminal resize events by updating dimensions and clearing display."""
    new_state = (
        state.with_previous_grid(None)
        .with_pattern_cells(None)
        .with_terminal_dimensions(terminal.width, terminal.height)
    )

    print(terminal.clear(), end="", flush=True)
    print(terminal.move_xy(0, 0), end="", flush=True)
    print(terminal.hide_cursor(), end="", flush=True)

    for y in range(terminal.height):
        print(terminal.move_xy(0, y) + " " * terminal.width, end="", flush=True)

    sys.stdout.flush()

    return new_state


def cleanup_terminal(terminal: TerminalProtocol) -> None:
    """Restores terminal to original state, ensuring proper cleanup even on errors."""
    try:
        print(terminal.normal_cursor(), end="", flush=True)
        print(terminal.exit_ca_mode(), end="", flush=True)
        print(terminal.exit_fullscreen(), end="", flush=True)
        print(terminal.normal, end="", flush=True)
        print(terminal.clear(), end="", flush=True)
        sys.stdout.flush()
    except Exception as e:
        print(f"Error during terminal cleanup: {str(e)}", file=sys.stderr)


def calculate_grid_position(
    terminal: TerminalProtocol,
    grid: Grid,
) -> tuple[int, int]:
    """Calculates optimal centered position for grid display.

    Accounts for terminal dimensions, grid size, and necessary margins
    to ensure the grid fits within the visible area while maintaining
    proper spacing for status lines and borders.
    """
    grid_height, grid_width = grid.shape
    total_width = grid_width * 2
    total_height = grid_height

    margin = 1
    usable_height = terminal.height - 2
    usable_width = terminal.width - (2 * margin)

    center_x = (usable_width // 2) + margin
    center_y = ((usable_height - 2) // 2) + margin

    start_x = center_x - (total_width // 2)
    start_y = center_y - (total_height // 2)

    start_x = max(margin, min(start_x, terminal.width - total_width - margin))
    start_y = max(margin, min(start_y, usable_height - total_height - margin))

    return start_x, start_y


def grid_to_dict(grid: Grid) -> RenderGrid:
    """Convert grid to dictionary for efficient lookup using NumPy operations."""
    rows, cols = grid.shape
    return {(x, y): grid[y, x] for y in range(rows) for x in range(cols)}


def render_status_line(
    terminal: TerminalProtocol,
    config: RendererConfig,
    metrics: Metrics,
) -> str:
    """Renders status line with game metrics and performance indicators."""
    plain_pop = f"Population: {metrics.game.active_cells}"
    plain_gen = f"Generation: {metrics.game.generation_count}"
    plain_births = f"Births/s: {metrics.game.birth_rate:.1f}"
    plain_deaths = f"Deaths/s: {metrics.game.death_rate:.1f}"
    plain_interval = f"Interval: {config.update_interval}ms"

    true_length = (
        len(plain_pop)
        + len(plain_gen)
        + len(plain_births)
        + len(plain_deaths)
        + len(plain_interval)
        + len(" | ") * 4
        + len(" ")
    )

    pop = f"{terminal.blue}Population: {terminal.normal}{metrics.game.active_cells}"
    gen = (
        f"{terminal.green}Generation: {terminal.normal}{metrics.game.generation_count}"
    )
    births = (
        f"{terminal.magenta}Births/s: {terminal.normal}{metrics.game.birth_rate:.1f}"
    )
    deaths = (
        f"{terminal.yellow}Deaths/s: {terminal.normal}{metrics.game.death_rate:.1f}"
    )
    interval = f"{terminal.white}Interval: {terminal.normal}{config.update_interval}ms"

    status = f"{pop} | {gen} | {births} | {deaths} | {interval}"

    y = terminal.height - 1
    x = max(0, (terminal.width - true_length) // 2)

    return (
        terminal.move_xy(0, y) + " " * terminal.width + terminal.move_xy(x, y) + status
    )


def render_pattern_menu(
    terminal: TerminalProtocol,
) -> str:
    """Renders pattern selection menu."""
    patterns = list(BUILTIN_PATTERNS.keys()) + FilePatternStorage().list_patterns()
    pattern_list = ", ".join(f"{i+1}:{name}" for i, name in enumerate(patterns))
    menu_text = (
        f"Pattern Mode - Select: {pattern_list} | R: rotate | Space: place | ESC: exit"
    )

    true_length = len(menu_text)
    y = terminal.height - 1
    x = (terminal.width - true_length) // 2
    x = max(0, x)

    return (
        terminal.move_xy(0, y)
        + " " * terminal.width
        + terminal.move_xy(x, y)
        + terminal.blue
        + menu_text
        + terminal.normal
    )


def render_grid(
    terminal: TerminalProtocol,
    grid: Grid,
    config: RendererConfig,
    state: RendererState,
    metrics: Metrics,
) -> tuple[RendererState, Metrics]:
    """Renders grid with optimized updates and pattern preview support.

    Uses NumPy operations for efficient state tracking and updates.
    Handles terminal resizing, pattern preview rendering, and maintains
    performance statistics for the status display.
    """
    grid_height, grid_width = grid.shape
    usable_height = terminal.height - 2
    start_x, start_y = calculate_grid_position(terminal, grid)

    dimensions_changed = (
        start_x != state.start_x
        or start_y != state.start_y
        or state.previous_grid is None
    )

    if dimensions_changed:
        state = state.with_grid_position(start_x, start_y).with_previous_grid(None)

        print(terminal.clear(), end="", flush=True)
        print(terminal.move_xy(0, 0), end="", flush=True)
        for y in range(terminal.height):
            print(terminal.move_xy(0, y) + " " * terminal.width, end="", flush=True)
        sys.stdout.flush()

    current_grid = grid_to_dict(grid)

    metrics = update_game_metrics(
        metrics,
        total_cells=grid.size,
        active_cells=np.count_nonzero(grid),
        births=0,
        deaths=0,
    )

    if state.previous_grid is not None:
        prev_grid = np.zeros_like(grid)
        for (x, y), val in state.previous_grid.items():
            prev_grid[y, x] = val

        births = np.logical_and(~prev_grid, grid)
        deaths = np.logical_and(prev_grid, ~grid)

        metrics = update_game_metrics(
            metrics,
            total_cells=grid.size,
            active_cells=np.count_nonzero(grid),
            births=np.count_nonzero(births),
            deaths=np.count_nonzero(deaths),
        )

    pattern_cells = set()
    if state.pattern_mode and config.selected_pattern:
        pattern = BUILTIN_PATTERNS.get(
            config.selected_pattern
        ) or FilePatternStorage().load_pattern(config.selected_pattern)

        if pattern:
            turns = config.pattern_rotation.to_turns()
            preview_pos = get_centered_position(
                pattern,
                (state.cursor_x, state.cursor_y),
                rotation=config.pattern_rotation,
            )
            cells = get_pattern_cells(pattern, turns)

            for dx, dy in cells:
                x = (preview_pos[0] + dx) % grid_width
                y = (preview_pos[1] + dy) % grid_height
                pattern_cells.add((x, y))

    visible_width = (terminal.width - start_x) // 2
    visible_height = usable_height - start_y

    for y in range(min(grid_height, visible_height)):
        for x in range(min(grid_width, visible_width)):
            screen_x = start_x + (x * 2)
            screen_y = start_y + y

            if screen_x >= terminal.width - 1 or screen_y >= usable_height:
                continue

            is_alive = current_grid.get((x, y), False)
            is_pattern = (x, y) in pattern_cells
            is_cursor = (
                state.pattern_mode and x == state.cursor_x and y == state.cursor_y
            )

            if is_cursor:
                cell_char = "+"
                color = terminal.yellow
            elif is_pattern:
                cell_char = "◆"
                color = terminal.blue
            else:
                cell_char = config.cell_alive if is_alive else config.cell_dead
                if is_alive:
                    color = terminal.white
                else:
                    color = terminal.dim

            print(
                terminal.move_xy(screen_x, screen_y)
                + color
                + cell_char
                + (
                    terminal.normal
                    if is_alive or is_cursor or is_pattern
                    else terminal.dim
                )
                + config.cell_spacing
                + terminal.normal,
                end="",
                flush=True,
            )

    state = state.with_previous_grid(current_grid).with_pattern_cells(pattern_cells)
    metrics = update_frame_metrics(metrics)

    if state.pattern_mode:
        print(render_pattern_menu(terminal), end="", flush=True)
    else:
        print(render_status_line(terminal, config, metrics), end="", flush=True)

    sys.stdout.flush()

    return state, metrics


def safe_render_grid(
    terminal: TerminalProtocol,
    grid: Grid,
    config: RendererConfig,
    state: RendererState,
    metrics: Metrics,
) -> tuple[RendererState, Metrics]:
    """Safely renders grid with comprehensive error handling.

    Ensures terminal is restored to a valid state even if rendering fails,
    handling I/O errors, keyboard interrupts, and unexpected exceptions.
    """
    try:
        return render_grid(terminal, grid, config, state, metrics)
    except (IOError, ValueError) as e:
        cleanup_terminal(terminal)
        raise RuntimeError(f"Failed to render grid: {e}") from e
    except KeyboardInterrupt:
        cleanup_terminal(terminal)
        raise
    except Exception as e:
        cleanup_terminal(terminal)
        raise RuntimeError(f"Unexpected error during rendering: {e}") from e
