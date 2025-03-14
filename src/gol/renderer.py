"""Terminal renderer for Game of Life."""

import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable

import numpy as np
from blessed import Terminal
from blessed.formatters import ParameterizingString
from blessed.keyboard import Keystroke

from .grid import BoundaryCondition
from .metrics import Metrics, update_frame_metrics, update_game_metrics
from .patterns import (
    BUILTIN_PATTERNS,
    FilePatternStorage,
    Pattern,
    PatternCategory,
    PatternTransform,
    get_centered_position,
    get_pattern_cells,
)
from .state import RendererState, ViewportState
from .types import (
    CommandType,
    Grid,
    GridPosition,
    RenderGrid,
    ScreenPosition,
    TerminalPosition,
    ViewportBounds,
)

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

    Speed Control Constraints:
    - Maximum speed: 10 generations/second (min_interval = 100ms)
    - Minimum speed: 0.5 generations/second (max_interval = 2000ms)
    - Speed adjustments are inverse proportional to current speed
    - Interval values are rounded to nearest 10ms
    - Speed changes use 20% of current interval as step size
    """

    cell_alive: str = "■"
    cell_dead: str = "□"
    cell_spacing: str = " "
    update_interval: int = 200  # Default 5 generations/second
    refresh_per_second: int = 5
    min_interval: int = 100  # Max speed: 10 generations/second
    max_interval: int = 2000  # Min speed: 0.5 generations/second
    min_interval_step: int = 10
    interval_change_factor: float = 0.2
    selected_pattern: Optional[str] = None
    pattern_rotation: PatternTransform = PatternTransform.NONE
    boundary_condition: BoundaryCondition = BoundaryCondition.FINITE
    pattern_category_idx: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "refresh_per_second", round(1000 / self.update_interval)
        )

    def _round_to_step(self, value: int) -> int:
        """Round value to nearest step size."""
        return round(value / self.min_interval_step) * self.min_interval_step

    def with_increased_interval(self) -> "RendererConfig":
        """Create new config with increased interval (slower speed).

        Steps are proportional to current interval, making changes smaller
        at higher speeds (lower intervals) and larger at lower speeds.
        """
        from dataclasses import replace

        # Calculate step size based on current interval
        step = max(
            self.min_interval_step,
            round(self.update_interval * self.interval_change_factor),
        )
        new_interval = self._round_to_step(self.update_interval + step)
        return replace(self, update_interval=min(new_interval, self.max_interval))

    def with_decreased_interval(self) -> "RendererConfig":
        """Create new config with decreased interval (faster speed).

        Steps are proportional to current interval, making changes smaller
        at higher speeds (lower intervals) and larger at lower speeds.
        """
        from dataclasses import replace

        # Calculate step size based on current interval
        step = max(
            self.min_interval_step,
            round(self.update_interval * self.interval_change_factor),
        )
        new_interval = self._round_to_step(self.update_interval - step)
        return replace(self, update_interval=max(new_interval, self.min_interval))

    def with_pattern(
        self,
        pattern_name: Optional[str],
        rotation: PatternTransform = PatternTransform.NONE,
    ) -> "RendererConfig":
        from dataclasses import replace

        return replace(self, selected_pattern=pattern_name, pattern_rotation=rotation)

    def with_update_interval(self, interval: int) -> "RendererConfig":
        """Create new config with updated update interval.

        Args:
            interval: New update interval in milliseconds

        Returns:
            New config with updated interval
        """
        from dataclasses import replace

        return replace(self, update_interval=interval)

    def with_pattern_category_idx(self, idx: int) -> "RendererConfig":
        """Create new config with updated pattern category index.

        Args:
            idx: New pattern category index

        Returns:
            New config with updated pattern category index
        """
        from dataclasses import replace

        return replace(self, pattern_category_idx=idx)


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
    """Handle keyboard input from user.

    Returns:
        Tuple of (command, updated_config)
    """
    # Global commands that work in both modes
    if str(key) == "q":
        return "quit", config
    if str(key) == "p":
        return "pattern", config

    # Pattern mode specific commands
    if state.pattern_mode:
        return handle_pattern_mode_input(key, config)

    # Normal mode specific commands
    return handle_normal_mode_input(key, config)


def handle_pattern_mode_input(
    key: Keystroke, config: RendererConfig
) -> tuple[CommandType, RendererConfig]:
    """Handle keyboard input when in pattern mode."""
    if str(key) == "\x1b" or key.name == "KEY_ESCAPE":
        return "exit_pattern", config

    if str(key) == "r":
        new_rotation = config.pattern_rotation.next_rotation()
        return "rotate_pattern", config.with_pattern(
            config.selected_pattern, new_rotation
        )

    if str(key) == "\t":  # Tab key
        current_idx = getattr(config, "pattern_category_idx", 0)
        new_idx = current_idx + 1
        config = config.with_pattern_category_idx(new_idx)
        return "continue", config

    if str(key).isdigit():
        pattern_num = int(str(key))
        if 1 <= pattern_num <= 9:
            # Get patterns for current category
            patterns_by_category: Dict[PatternCategory, List[str]] = {}
            for name, pattern in BUILTIN_PATTERNS.items():
                category = pattern.metadata.category
                if category not in patterns_by_category:
                    patterns_by_category[category] = []
                patterns_by_category[category].append(name)

            # Add custom patterns
            custom_patterns = FilePatternStorage().list_patterns()
            if custom_patterns:
                patterns_by_category[PatternCategory.CUSTOM] = custom_patterns

            # Get current category patterns
            categories = list(patterns_by_category.keys())
            current_category_idx = getattr(config, "pattern_category_idx", 0)
            current_category = categories[current_category_idx % len(categories)]
            current_patterns = patterns_by_category[current_category]

            if pattern_num <= len(current_patterns):
                return "select_pattern", config.with_pattern(
                    current_patterns[pattern_num - 1]
                )

    # Movement and action keys in pattern mode
    match key.name:
        case "KEY_LEFT":
            return "move_cursor_left", config
        case "KEY_RIGHT":
            return "move_cursor_right", config
        case "KEY_UP":
            return "move_cursor_up", config
        case "KEY_DOWN":
            return "move_cursor_down", config
        case _ if str(key) in (" ", "KEY_SPACE"):
            return "place_pattern", config

    return "continue", config


def handle_normal_mode_input(
    key: Keystroke, config: RendererConfig
) -> tuple[CommandType, RendererConfig]:
    """Handle keyboard input when in normal mode."""
    if str(key) == "\x1b" or key.name == "KEY_ESCAPE":
        return "quit", config

    # Grid commands
    match str(key):
        case "c":
            return "clear_grid", config
        case "b":
            return "cycle_boundary", config
        case "+":
            return "viewport_expand", config
        case "-":
            return "viewport_shrink", config
        case "r":
            return "restart", config
        case "d":
            return "toggle_debug", config
        case _ if str(key) in (" ", "KEY_SPACE"):
            return "toggle_simulation", config

    # Speed control
    match key.name:
        case "KEY_SUP":
            return "speed_up", config.with_decreased_interval()
        case "KEY_SDOWN":
            return "speed_down", config.with_increased_interval()

    # Viewport movement
    match key.name:
        case "KEY_LEFT":
            return "viewport_pan_left", config
        case "KEY_RIGHT":
            return "viewport_pan_right", config
        case "KEY_UP":
            return "viewport_pan_up", config
        case "KEY_DOWN":
            return "viewport_pan_down", config

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


def calculate_terminal_position(
    terminal: TerminalProtocol,
    grid: Grid,
) -> TerminalPosition:
    """Calculate where in the terminal to render the viewport.

    Only called on terminal resize or initial setup.

    Args:
        terminal: Terminal interface for rendering
        grid: Current grid state

    Returns:
        TerminalPosition for rendering the viewport
    """
    grid_height, grid_width = grid.shape
    cell_width = 2  # Each cell takes 2 characters (cell + spacing)
    total_width = grid_width * cell_width
    total_height = grid_height

    # Reserve space for status line and ensure proper vertical spacing
    usable_height = terminal.height - 3

    # Calculate start positions to center the grid
    # For horizontal centering, we need to account for each cell being 2 chars wide
    start_x = (terminal.width - total_width) // 2
    start_y = (usable_height - total_height) // 2 + 1

    # Ensure non-negative positions
    return TerminalPosition(x=max(0, start_x), y=max(1, start_y))


def calculate_viewport_bounds(
    viewport: ViewportState,
    terminal_width: int,
    terminal_height: int,
    terminal_pos: TerminalPosition,
    grid_width: int,
    grid_height: int,
) -> tuple[ViewportBounds, TerminalPosition]:
    """Calculate which portion of grid is visible through viewport.

    Args:
        viewport: Current viewport state
        terminal_width: Terminal width
        terminal_height: Terminal height
        terminal_pos: Position in terminal where viewport is rendered
        grid_width: Grid width
        grid_height: Grid height

    Returns:
        Tuple of (ViewportBounds defining visible portion of grid,
        updated terminal position)
    """
    # Calculate maximum visible area based on terminal constraints
    max_visible_width = min(
        (terminal_width - terminal_pos.x - 4) // 2, grid_width
    )  # Account for borders and terminal position
    max_visible_height = min(
        terminal_height - terminal_pos.y - 4, grid_height
    )  # Account for status lines and terminal position

    # Constrain visible area to viewport size
    visible_width = min(viewport.width, max_visible_width)
    visible_height = min(viewport.height, max_visible_height)

    # Calculate terminal position to center the viewport
    terminal_start_x = (
        terminal_width - (visible_width * 2)
    ) // 2  # Each cell is 2 chars
    terminal_start_y = (terminal_height - visible_height - 3) // 2 + 1  # Status lines

    # Update terminal position
    updated_terminal_pos = TerminalPosition(
        x=max(0, terminal_start_x), y=max(1, terminal_start_y)
    )

    # Get grid start position from viewport offset
    grid_start_x = viewport.offset_x
    grid_start_y = viewport.offset_y

    # Ensure within grid bounds
    grid_start_x = max(0, min(grid_start_x, grid_width - visible_width))
    grid_start_y = max(0, min(grid_start_y, grid_height - visible_height))

    bounds = ViewportBounds(
        grid_start=(grid_start_x, grid_start_y),
        visible_dims=(visible_width, visible_height),
    )
    return bounds, updated_terminal_pos


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

    # Add boundary condition
    plain_boundary = f"Boundary: {config.boundary_condition.name}"
    boundary_text = (
        f" | {terminal.green}Boundary: {terminal.normal}"
        f"{config.boundary_condition.name}"
    )
    plain_boundary_len = len(plain_boundary) + len(" | ")

    true_length = (
        len(plain_pop)
        + len(plain_gen)
        + len(plain_births)
        + len(plain_deaths)
        + len(plain_interval)
        + plain_boundary_len
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

    status = f"{pop} | {gen} | {births} | {deaths} | {interval}{boundary_text}"

    y = terminal.height - 1
    x = max(0, (terminal.width - true_length) // 2)

    return (
        terminal.move_xy(0, y) + " " * terminal.width + terminal.move_xy(x, y) + status
    )


def render_pattern_menu(
    terminal: TerminalProtocol,
    config: RendererConfig,
) -> str:
    """Renders pattern selection menu with categories."""
    # Group patterns by category
    patterns_by_category: Dict[PatternCategory, List[Tuple[str, Optional[Pattern]]]] = (
        {}
    )
    for name, pattern in BUILTIN_PATTERNS.items():
        category = pattern.metadata.category
        if category not in patterns_by_category:
            patterns_by_category[category] = []
        patterns_by_category[category].append((name, pattern))

    # Add custom patterns
    custom_patterns = FilePatternStorage().list_patterns()
    if custom_patterns:
        patterns_by_category[PatternCategory.CUSTOM] = [
            (name, None) for name in custom_patterns
        ]

    # Get current category and patterns
    categories = list(patterns_by_category.keys())
    current_category_idx = getattr(config, "pattern_category_idx", 0)
    current_category = categories[current_category_idx % len(categories)]
    current_patterns = patterns_by_category[current_category]

    # Format pattern list for current category
    pattern_list = ", ".join(
        f"{i+1}:{name}" for i, (name, _) in enumerate(current_patterns[:9])
    )

    # Build menu text
    category_name = current_category.name.replace("_", " ").title()
    menu_text = (
        f"Pattern Mode - {category_name} "
        f"({current_category_idx + 1}/{len(categories)})\n"
        f"Select: {pattern_list}\n"
        f"Tab: next | R: rotate | Space: place | ESC: exit"
    )

    true_length = len(menu_text.replace("\n", " "))
    y = terminal.height - 1
    x = (terminal.width - true_length) // 2
    x = max(0, x)

    return (
        terminal.move_xy(0, y)
        + " " * terminal.width
        + terminal.move_xy(x, y)
        + terminal.blue
        + menu_text.replace("\n", " ")
        + terminal.normal
    )


def calculate_render_metrics(
    grid: Grid,
    previous_grid: Optional[RenderGrid],
    metrics: Metrics,
) -> Metrics:
    """Pure function to calculate updated metrics based on grid state.

    Args:
        grid: Current grid state
        previous_grid: Previous grid state for calculating changes
        metrics: Current metrics state

    Returns:
        Updated metrics with new calculations
    """
    metrics = update_game_metrics(
        metrics,
        total_cells=grid.size,
        active_cells=np.count_nonzero(grid),
        births=0,
        deaths=0,
        increment_generation=False,  # Don't increment generation during rendering
    )

    if previous_grid is not None:
        prev_grid = np.zeros_like(grid)
        for (x, y), val in previous_grid.items():
            prev_grid[y, x] = val

        births = np.logical_and(~prev_grid, grid)
        deaths = np.logical_and(prev_grid, ~grid)

        metrics = update_game_metrics(
            metrics,
            total_cells=grid.size,
            active_cells=np.count_nonzero(grid),
            births=np.count_nonzero(births),
            deaths=np.count_nonzero(deaths),
            increment_generation=False,  # Don't increment generation during rendering
        )

    # Update frame metrics
    metrics = update_frame_metrics(metrics)

    return metrics


def calculate_pattern_cells(
    grid_width: int,
    grid_height: int,
    pattern_name: Optional[str],
    cursor_pos: GridPosition,
    rotation: PatternTransform,
    boundary_condition: BoundaryCondition = BoundaryCondition.FINITE,
) -> set[tuple[int, int]]:
    """Pure function to calculate pattern preview cell positions.

    Args:
        grid_width: Width of the grid
        grid_height: Height of the grid
        pattern_name: Name of the selected pattern
        cursor_pos: Current cursor position (x, y)
        rotation: Pattern rotation state
        boundary_condition: Current boundary condition

    Returns:
        Set of (x, y) coordinates for pattern cells
    """
    if not pattern_name:
        return set()

    pattern = BUILTIN_PATTERNS.get(pattern_name) or FilePatternStorage().load_pattern(
        pattern_name
    )
    if not pattern:
        return set()

    # Get pattern cells with rotation
    turns = rotation.to_turns()
    cells = get_pattern_cells(pattern, turns)

    # Calculate center position for pattern placement
    preview_pos = get_centered_position(pattern, cursor_pos, rotation=rotation)

    # Handle coordinates based on boundary condition
    if boundary_condition in (BoundaryCondition.FINITE, BoundaryCondition.TOROIDAL):
        return {
            ((preview_pos[0] + dx) % grid_width, (preview_pos[1] + dy) % grid_height)
            for dx, dy in cells
        }
    else:  # INFINITE boundary
        return {(preview_pos[0] + dx, preview_pos[1] + dy) for dx, dy in cells}


@dataclass(frozen=True)
class RenderInitialization:
    """Initialization data for renderer.

    Contains all data needed for initial rendering setup.
    Immutable to prevent accidental state modifications.
    """

    terminal_pos: TerminalPosition
    grid_dimensions: tuple[int, int]
    terminal_dimensions: tuple[int, int]


def initialize_render_state(
    terminal: TerminalProtocol,
    grid: Grid,
    state: RendererState,
) -> tuple[RenderInitialization, RendererState]:
    """Pure function to initialize rendering state.

    Calculates initial positions and dimensions without side effects.
    Should be called once at startup before first render.

    Args:
        terminal: Terminal interface for rendering
        grid: Initial grid state
        state: Current renderer state

    Returns:
        Tuple of (initialization data, updated state)
    """
    grid_height, grid_width = grid.shape
    terminal_pos = calculate_terminal_position(terminal, grid)

    new_state = state.with_terminal_position(terminal_pos).with_previous_grid(None)

    init_data = RenderInitialization(
        terminal_pos=terminal_pos,
        grid_dimensions=(grid_width, grid_height),
        terminal_dimensions=(terminal.width, terminal.height),
    )

    return init_data, new_state


def apply_initialization(
    terminal: TerminalProtocol,
    init: RenderInitialization,
) -> None:
    """Applies initialization by performing required side effects.

    Contains all terminal side effects needed for initialization.
    Should be called once after initialize_render_state.

    Args:
        terminal: Terminal interface for rendering
        init: Initialization data from initialize_render_state
    """
    print(terminal.clear(), end="", flush=True)
    print(terminal.move_xy(0, 0), end="", flush=True)
    for y in range(init.terminal_dimensions[1]):
        print(
            terminal.move_xy(0, y) + " " * init.terminal_dimensions[0],
            end="",
            flush=True,
        )
    sys.stdout.flush()


def calculate_cell_display(
    x: int,
    y: int,
    current_grid: RenderGrid,
    pattern_cells: set[tuple[int, int]],
    cursor_pos: tuple[int, int],
    pattern_mode: bool,
    config: RendererConfig,
    terminal: TerminalProtocol,
) -> tuple[str, str]:
    """Calculate display properties for a single cell.

    Args:
        x, y: Cell coordinates
        current_grid: Current grid state
        pattern_cells: Set of pattern preview cells
        cursor_pos: Current cursor position
        pattern_mode: Whether pattern mode is active
        config: Renderer configuration
        terminal: Terminal for color access

    Returns:
        Tuple of (character, color) to display
    """
    is_alive = current_grid.get((x, y), False)
    is_pattern = (x, y) in pattern_cells
    is_cursor = pattern_mode and x == cursor_pos[0] and y == cursor_pos[1]

    if is_cursor:
        return "+", terminal.yellow
    if is_pattern:
        return "◆", terminal.blue
    if is_alive:
        return config.cell_alive, terminal.white
    return config.cell_dead, terminal.dim


def render_cell(
    terminal: TerminalProtocol,
    screen_pos: tuple[int, int],
    cell_char: str,
    color: str,
    config: RendererConfig,
    is_highlighted: bool,
) -> None:
    """Render a single cell to the terminal.

    Args:
        terminal: Terminal interface
        screen_pos: Screen coordinates (x, y)
        cell_char: Character to display
        color: Color to use
        config: Renderer configuration
        is_highlighted: Whether cell should be highlighted
    """
    print(
        terminal.move_xy(screen_pos[0], screen_pos[1])
        + color
        + cell_char
        + (terminal.normal if is_highlighted else terminal.dim)
        + config.cell_spacing
        + terminal.normal,
        end="",
        flush=True,
    )


def render_debug_status_line(
    terminal: TerminalProtocol,
    grid: Grid,
    state: RendererState,
) -> str:
    """Renders debug status line with grid and viewport information."""
    grid_height, grid_width = grid.shape
    viewport = state.viewport
    bounds, _ = calculate_viewport_bounds(
        viewport,
        terminal.width,
        terminal.height,
        state.terminal_pos,
        grid_width,
        grid_height,
    )

    # Format each part separately to keep lines under length limit
    grid_info = f"{terminal.blue}Grid: {terminal.normal}{grid_width}x{grid_height}"
    viewport_info = (
        f"{terminal.green}Viewport: {terminal.normal}"
        f"{viewport.width}x{viewport.height}"
    )
    offset_info = (
        f"{terminal.magenta}Offset: {terminal.normal}"
        f"{viewport.offset_x},{viewport.offset_y}"
    )
    visible_info = (
        f"{terminal.yellow}Visible: {terminal.normal}"
        f"{bounds.visible_dims[0]}x{bounds.visible_dims[1]}"
    )
    visible_coords = (
        f"{terminal.white}Area: {terminal.normal}"
        f"({bounds.grid_start[0]},{bounds.grid_start[1]})-"
        f"({bounds.grid_start[0]+bounds.visible_dims[0]-1},"
        f"{bounds.grid_start[1]+bounds.visible_dims[1]-1})"
    )

    debug_info = (
        f"{grid_info} | {viewport_info} | {offset_info} | {visible_info} | "
        f"{visible_coords}"
    )

    true_length = len(debug_info) - len(terminal.blue + terminal.normal) * 5
    y = terminal.height - 2
    x = max(0, (terminal.width - true_length) // 2)

    return (
        terminal.move_xy(0, y)
        + " " * terminal.width
        + terminal.move_xy(x, y)
        + debug_info
    )


def render_grid_to_terminal(
    terminal: TerminalProtocol,
    grid: Grid,
    config: RendererConfig,
    state: RendererState,
    metrics: Metrics,
) -> tuple[RendererState, Metrics]:
    """Renders grid to terminal with side effects."""
    # Pure calculations
    grid_height, grid_width = grid.shape
    usable_height = terminal.height - (3 if state.debug_mode else 2)
    current_grid = grid_to_dict(grid)
    metrics = calculate_render_metrics(grid, current_grid, metrics)

    # Get current viewport bounds first
    viewport_bounds, updated_terminal_pos = calculate_viewport_bounds(
        state.viewport,
        terminal.width,
        terminal.height,
        state.terminal_pos,
        grid_width,
        grid_height,
    )

    # Get previous viewport bounds if available
    prev_viewport_bounds = None
    if state.previous_viewport is not None:
        prev_viewport_bounds, _ = calculate_viewport_bounds(
            state.previous_viewport,
            terminal.width,
            terminal.height,
            state.terminal_pos,
            grid_width,
            grid_height,
        )

    # Clear previous area if viewport changed
    if prev_viewport_bounds is not None:
        # Calculate screen coordinates for both previous and current viewports
        prev_screen_coords = {
            (state.terminal_pos.x + (vx * 2), state.terminal_pos.y + vy)
            for vy in range(prev_viewport_bounds.visible_dims[1])
            for vx in range(prev_viewport_bounds.visible_dims[0])
        }
        current_screen_coords = {
            (updated_terminal_pos.x + (vx * 2), updated_terminal_pos.y + vy)
            for vy in range(viewport_bounds.visible_dims[1])
            for vx in range(viewport_bounds.visible_dims[0])
        }

        # Clear cells that were in previous viewport but not in current viewport
        cells_to_clear = prev_screen_coords - current_screen_coords
        for screen_x, screen_y in cells_to_clear:
            if screen_x >= terminal.width - 1 or screen_y >= usable_height:
                continue
            print(
                terminal.move_xy(screen_x, screen_y) + "  ",
                end="",
                flush=True,
            )

    pattern_cells = calculate_pattern_cells(
        viewport_bounds.visible_dims[0],  # Use viewport dimensions for pattern calc
        viewport_bounds.visible_dims[1],
        config.selected_pattern if state.pattern_mode else None,
        (state.cursor_x, state.cursor_y),  # Use actual cursor position
        config.pattern_rotation,
        config.boundary_condition,
    )

    pattern_cells_array = (
        np.zeros_like(grid) if pattern_cells is None else np.array(list(pattern_cells))
    )

    # Render cells
    for vy in range(viewport_bounds.visible_dims[1]):
        for vx in range(viewport_bounds.visible_dims[0]):
            # Calculate grid coordinates based on boundary condition
            if config.boundary_condition in (
                BoundaryCondition.FINITE,
                BoundaryCondition.TOROIDAL,
            ):
                x = (viewport_bounds.grid_start[0] + vx) % grid_width
                y = (viewport_bounds.grid_start[1] + vy) % grid_height
            else:  # INFINITE boundary
                x = viewport_bounds.grid_start[0] + vx
                y = viewport_bounds.grid_start[1] + vy

            screen_x = updated_terminal_pos.x + (vx * 2)
            screen_y = updated_terminal_pos.y + vy

            if screen_x >= terminal.width - 1 or screen_y >= usable_height:
                continue

            # Check grid bounds for live cells in INFINITE mode
            if config.boundary_condition == BoundaryCondition.INFINITE:
                if x < 0 or x >= grid_width or y < 0 or y >= grid_height:
                    # Still show cursor and pattern cells outside grid
                    is_cursor = (
                        state.pattern_mode
                        and x == state.cursor_x
                        and y == state.cursor_y
                    )
                    is_pattern = (x, y) in pattern_cells
                    if not (is_cursor or is_pattern):
                        continue

            cell_char, color = calculate_cell_display(
                x,
                y,
                current_grid,
                pattern_cells,
                (state.cursor_x, state.cursor_y),  # Use actual cursor position
                state.pattern_mode,
                config,
                terminal,
            )

            is_highlighted = (
                current_grid.get((x, y), False)
                or (x, y) in pattern_cells
                or (state.pattern_mode and x == state.cursor_x and y == state.cursor_y)
            )

            render_cell(
                terminal,
                (screen_x, screen_y),
                cell_char,
                color,
                config,
                is_highlighted,
            )

    # Update state and metrics
    state = (
        state.with_previous_grid(grid)
        .with_pattern_cells(pattern_cells_array)
        .with_previous_viewport(state.viewport)
        .with_terminal_position(updated_terminal_pos)
    )
    metrics = update_frame_metrics(metrics)

    # Render status lines
    if state.pattern_mode:
        print(render_pattern_menu(terminal, config), end="", flush=True)
    else:
        # Always clear the debug line position
        print(
            terminal.move_xy(0, terminal.height - 2) + " " * terminal.width,
            end="",
            flush=True,
        )

        if state.debug_mode:
            print(render_debug_status_line(terminal, grid, state), end="", flush=True)
        print(render_status_line(terminal, config, metrics), end="", flush=True)

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
        return render_grid_to_terminal(terminal, grid, config, state, metrics)
    except (IOError, ValueError) as e:
        cleanup_terminal(terminal)
        raise RuntimeError(f"Failed to render grid: {e}") from e
    except KeyboardInterrupt:
        cleanup_terminal(terminal)
        raise
    except Exception as e:
        cleanup_terminal(terminal)
        raise RuntimeError(f"Unexpected error during rendering: {e}") from e
