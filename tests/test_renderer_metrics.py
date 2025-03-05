"""Tests for renderer metrics integration."""

import re
from dataclasses import dataclass, replace
from typing import Any

import numpy as np
import pytest
from blessed.formatters import ParameterizingString
from blessed.keyboard import Keystroke

from gol.metrics import Metrics, create_metrics
from gol.renderer import (
    RendererConfig,
    RendererState,
    TerminalProtocol,
    render_grid,
    render_status_line,
)
from gol.types import Grid


def strip_ansi(text: str) -> str:
    """Strip ANSI sequences, terminal commands, and color/style names."""
    # Handle terminal movement commands
    text = re.sub(r"move\(\d+,\d+\)", "", text)
    # Handle color and style names
    text = re.sub(r"(blue|green|magenta|yellow|white|normal)", "", text)
    # Handle ANSI escape sequences
    ansi_escape = re.compile(r"\x1b[^m]*m")
    return ansi_escape.sub("", text)


@dataclass
class MockTerminal(TerminalProtocol):
    """Mock terminal for testing renderer functions."""

    width: int = 80
    height: int = 24
    _output: list[str] = None  # type: ignore

    def __post_init__(self) -> None:
        """Initialize output buffer."""
        self._output = []

    def move_xy(self, x: int, y: int) -> ParameterizingString:
        """Mock cursor movement."""
        return ParameterizingString(f"move({x},{y})")

    def clear(self) -> str:
        """Mock clear screen."""
        return "clear"

    def enter_fullscreen(self) -> str:
        """Mock enter fullscreen."""
        return "fullscreen"

    def exit_fullscreen(self) -> str:
        """Mock exit fullscreen."""
        return "exit_fullscreen"

    def enter_ca_mode(self) -> str:
        """Mock enter ca mode."""
        return "ca_mode"

    def exit_ca_mode(self) -> str:
        """Mock exit ca mode."""
        return "exit_ca_mode"

    def hide_cursor(self) -> str:
        """Mock hide cursor."""
        return "hide_cursor"

    def normal_cursor(self) -> str:
        """Mock normal cursor."""
        return "normal_cursor"

    @property
    def normal(self) -> str:
        return "normal"

    @property
    def dim(self) -> str:
        return "dim"

    @property
    def white(self) -> str:
        return "white"

    @property
    def blue(self) -> str:
        return "blue"

    @property
    def green(self) -> str:
        return "green"

    @property
    def yellow(self) -> str:
        return "yellow"

    @property
    def magenta(self) -> str:
        return "magenta"

    def inkey(self, timeout: float = 0) -> Keystroke:
        """Mock key input."""
        return Keystroke("")

    def cbreak(self) -> Any:
        """Mock context manager."""
        return self


@pytest.fixture
def terminal() -> TerminalProtocol:
    """Create a mock terminal for testing."""
    return MockTerminal()


@pytest.fixture
def state() -> RendererState:
    """Create a fresh renderer state for testing."""
    return RendererState.create()


@pytest.fixture
def config() -> RendererConfig:
    """Create a renderer config for testing."""
    return RendererConfig()


@pytest.fixture
def metrics() -> Metrics:
    """Create a fresh metrics instance for testing."""
    return create_metrics()


@pytest.fixture
def grid() -> Grid:
    """Create a test grid."""
    return np.zeros((10, 10), dtype=bool)


def test_render_status_line_metrics(
    terminal: TerminalProtocol,
    config: RendererConfig,
    metrics: Metrics,
) -> None:
    """Test that status line correctly displays metrics."""
    # Set up test metrics
    metrics = replace(
        metrics,
        game=replace(
            metrics.game,
            active_cells=42,
            generation_count=100,
            birth_rate=2.5,
            death_rate=1.5,
        ),
    )

    # Render status line and strip ANSI sequences
    status = strip_ansi(render_status_line(terminal, config, metrics))

    # Check that metrics values are included in output
    assert "Population: 42" in status
    assert "Generation: 100" in status
    assert "Births/s: 2.5" in status
    assert "Deaths/s: 1.5" in status


def test_render_grid_updates_metrics(
    terminal: TerminalProtocol,
    config: RendererConfig,
    state: RendererState,
    metrics: Metrics,
) -> None:
    """Test that render_grid properly updates metrics."""
    # Create test grid with some active cells
    grid = np.zeros((10, 10), dtype=bool)
    grid[4:7, 4:7] = True  # 9 active cells

    # First render to establish baseline
    state, metrics = render_grid(terminal, grid, config, state, metrics)

    assert metrics.game.total_cells == 100  # 10x10 grid
    assert metrics.game.active_cells == 9  # 3x3 block of active cells

    # Modify grid to trigger births/deaths
    prev_grid = grid.copy()
    grid[3:8, 3:8] = True  # Expand to 5x5 block

    # Update state with previous grid
    state = state.with_previous_grid(
        {(x, y): prev_grid[y, x] for y, x in np.ndindex(prev_grid.shape)}
    )

    # Second render should detect changes
    state, metrics = render_grid(terminal, grid, config, state, metrics)

    assert metrics.game.total_cells == 100
    assert metrics.game.active_cells == 25  # 5x5 block
    assert metrics.game.births_this_second == 16  # New cells added
    assert metrics.game.deaths_this_second == 0  # No cells died


def test_render_grid_frame_metrics(
    terminal: TerminalProtocol,
    config: RendererConfig,
    state: RendererState,
    metrics: Metrics,
    grid: Grid,
) -> None:
    """Test that render_grid properly tracks frame metrics."""
    # Render multiple frames
    for _ in range(5):
        state, metrics = render_grid(terminal, grid, config, state, metrics)

    assert metrics.perf.frames_this_second == 5
    assert metrics.perf.actual_fps == 0.0  # Not updated until 1 second passes

    # Force time update and render one more frame
    import time
    from dataclasses import replace

    metrics = replace(
        metrics,
        perf=replace(metrics.perf, last_fps_update=time.time() - 1.1),
    )

    state, metrics = render_grid(terminal, grid, config, state, metrics)

    assert metrics.perf.frames_this_second == 1  # Reset after time update
    assert metrics.perf.actual_fps == pytest.approx(
        5, rel=0.1
    )  # ~5 FPS from previous frames
