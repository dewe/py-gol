"""Tests for renderer metrics integration.

Focus on impure functions that handle metrics display and terminal output.
"""

import re
from dataclasses import dataclass, replace
from typing import Any

import pytest
from blessed.formatters import ParameterizingString
from blessed.keyboard import Keystroke

from gol.metrics import Metrics, create_metrics
from gol.renderer import (
    RendererConfig,
    RendererState,
    TerminalProtocol,
    render_status_line,
)


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


def test_render_status_line_with_boundary(
    terminal: TerminalProtocol,
    config: RendererConfig,
    metrics: Metrics,
) -> None:
    """Test that status line correctly displays boundary condition."""
    from gol.grid import BoundaryCondition

    config = replace(config, boundary_condition=BoundaryCondition.TOROIDAL)
    status = strip_ansi(render_status_line(terminal, config, metrics))
    assert "Boundary: TOROIDAL" in status


def test_render_status_line_formatting(
    terminal: TerminalProtocol,
    config: RendererConfig,
    metrics: Metrics,
) -> None:
    """Test that status line uses correct terminal formatting."""
    status = render_status_line(terminal, config, metrics)
    assert "blue" in status  # Population
    assert "green" in status  # Generation
    assert "magenta" in status  # Births/s
    assert "yellow" in status  # Deaths/s
    assert "white" in status  # Interval
