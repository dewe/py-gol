"""Tests for renderer initialization functions.

Tests the pure initialization functions and side effect handling.
"""

import dataclasses
from typing import Any, cast
from unittest.mock import Mock, PropertyMock, call

import numpy as np
import pytest
from blessed.formatters import ParameterizingString

from gol.renderer import (
    RenderInitialization,
    TerminalPosition,
    TerminalProtocol,
    apply_initialization,
    initialize_render_state,
)
from gol.state import RendererState
from gol.types import Grid


@pytest.fixture
def mock_terminal() -> TerminalProtocol:
    """Create a mock terminal for testing."""
    terminal = Mock(spec=TerminalProtocol)

    # Mock properties to return integer values
    type(terminal).width = PropertyMock(return_value=80)
    type(terminal).height = PropertyMock(return_value=24)

    # Mock methods with proper return types
    terminal.clear = Mock(return_value="")
    terminal.move_xy = Mock(return_value=ParameterizingString(""))

    return terminal


@pytest.fixture
def test_grid() -> Grid:
    """Create a test grid."""
    return np.array([[0, 1], [1, 0]], dtype=bool)


@pytest.fixture
def test_state() -> RendererState:
    """Create a test renderer state."""
    return RendererState.create()


def test_initialize_render_state_pure_function(
    mock_terminal: TerminalProtocol,
    test_grid: Grid,
    test_state: RendererState,
) -> None:
    """Test that initialize_render_state is a pure function.

    Given: Terminal, grid, and state
    When: Initializing render state
    Then: Should return new state and initialization data without side effects
    """
    # Cast to Any for mock assertions
    mock = cast(Any, mock_terminal)

    # When
    init_data, new_state = initialize_render_state(mock_terminal, test_grid, test_state)

    # Then
    assert isinstance(init_data, RenderInitialization)
    assert isinstance(new_state, RendererState)

    # Verify terminal was not modified
    mock.clear.assert_not_called()
    mock.move_xy.assert_not_called()

    # Verify initialization data is correct
    assert init_data.grid_dimensions == (2, 2)
    assert init_data.terminal_dimensions == (mock_terminal.width, mock_terminal.height)
    assert isinstance(init_data.terminal_pos, TerminalPosition)

    # Verify state updates
    assert new_state.previous_grid is None
    assert new_state.terminal_pos == init_data.terminal_pos


def test_apply_initialization_side_effects(
    mock_terminal: TerminalProtocol,
) -> None:
    """Test that apply_initialization properly applies side effects.

    Given: Terminal and initialization data
    When: Applying initialization
    Then: Should perform expected terminal operations
    """
    # Cast to Any for mock assertions
    mock = cast(Any, mock_terminal)

    # Given
    init_data = RenderInitialization(
        terminal_pos=TerminalPosition(x=10, y=5),
        grid_dimensions=(2, 2),
        terminal_dimensions=(80, 24),
    )

    # When
    apply_initialization(mock_terminal, init_data)

    # Then
    assert mock.clear.call_count == 1
    assert (
        mock.move_xy.call_count == init_data.terminal_dimensions[1] + 1
    )  # +1 for initial move to 0,0

    # Verify terminal operations sequence
    expected_calls = [
        call.clear(),
        call.move_xy(0, 0),
    ] + [call.move_xy(0, y) for y in range(init_data.terminal_dimensions[1])]

    mock.assert_has_calls(expected_calls, any_order=False)


def test_initialization_data_immutability() -> None:
    """Test that RenderInitialization is immutable.

    Given: Initialization data
    When: Attempting to modify fields
    Then: Should raise FrozenInstanceError
    """
    # Given
    init_data = RenderInitialization(
        terminal_pos=TerminalPosition(x=0, y=0),
        grid_dimensions=(10, 10),
        terminal_dimensions=(80, 24),
    )

    # Then
    with pytest.raises(dataclasses.FrozenInstanceError):
        init_data.terminal_pos = TerminalPosition(x=1, y=1)  # type: ignore

    with pytest.raises(dataclasses.FrozenInstanceError):
        init_data.grid_dimensions = (20, 20)  # type: ignore

    with pytest.raises(dataclasses.FrozenInstanceError):
        init_data.terminal_dimensions = (100, 30)  # type: ignore


def test_initialize_render_state_with_different_dimensions(
    mock_terminal: TerminalProtocol,
    test_state: RendererState,
) -> None:
    """Test initialization with different grid dimensions.

    Given: Different grid sizes
    When: Initializing render state
    Then: Should calculate correct positions and dimensions
    """
    # Test cases with different grid dimensions
    test_cases = [
        (np.zeros((10, 10), dtype=bool), (10, 10)),
        (np.zeros((20, 30), dtype=bool), (30, 20)),
        (np.zeros((5, 15), dtype=bool), (15, 5)),
    ]

    for grid, expected_dims in test_cases:
        # When
        init_data, new_state = initialize_render_state(mock_terminal, grid, test_state)

        # Then
        assert init_data.grid_dimensions == expected_dims
        assert init_data.terminal_dimensions == (
            mock_terminal.width,
            mock_terminal.height,
        )
        assert isinstance(init_data.terminal_pos, TerminalPosition)
        assert new_state.previous_grid is None
