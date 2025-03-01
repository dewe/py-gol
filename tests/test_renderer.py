"""Tests for the terminal renderer component."""

from dataclasses import dataclass
from typing import Optional

from blessed import Terminal

from gol.grid import GridConfig, create_grid
from gol.renderer import (
    RendererConfig,
    cleanup_terminal,
    handle_resize_event,
    handle_user_input,
    initialize_terminal,
    render_grid,
    safe_render_grid,
)


@dataclass
class MockKeystroke:
    """Mock keystroke for testing."""

    name: str
    code: Optional[int] = None
    is_sequence: bool = False


def test_renderer_config_defaults() -> None:
    """
    Given: Default renderer configuration
    When: Creating a new config
    Then: Should have expected default values
    """
    config = RendererConfig()
    assert config.cell_alive == "■"
    assert config.cell_dead == "□"
    assert config.update_interval == 100


def test_terminal_initialization() -> None:
    """
    Given: A new terminal initialization
    When: Setting up the terminal
    Then: Should return configured Terminal instance
    And: Terminal should be in fullscreen mode
    And: Terminal should have cursor hidden
    """
    config = RendererConfig()
    term = initialize_terminal(config)

    assert isinstance(term, Terminal)
    # Note: We can't directly test terminal properties in unit tests
    # as they depend on actual terminal capabilities.
    # These would be better tested in integration tests.


def test_terminal_cleanup() -> None:
    """
    Given: An initialized terminal
    When: Cleaning up the terminal
    Then: Should restore terminal to original state
    """
    config = RendererConfig()
    term = initialize_terminal(config)

    try:
        # Verify terminal is initialized
        assert isinstance(term, Terminal)

        # Perform cleanup
        cleanup_terminal(term)
    finally:
        # Ensure cleanup runs even if test fails
        cleanup_terminal(term)


def test_terminal_initialization_and_cleanup_cycle() -> None:
    """
    Given: Multiple terminal initializations and cleanups
    When: Running in sequence
    Then: Should handle multiple cycles without errors
    """
    config = RendererConfig()

    for _ in range(3):  # Test multiple cycles
        term = initialize_terminal(config)
        assert isinstance(term, Terminal)
        cleanup_terminal(term)


def test_grid_rendering() -> None:
    """
    Given: A terminal and a known grid state
    When: Rendering the grid
    Then: Should output correct characters for live/dead cells
    And: Should position grid centered in terminal
    And: Should use configured cell characters
    """
    # Setup
    renderer_config = RendererConfig()
    term = initialize_terminal(renderer_config)

    # Create a small test grid with known state
    grid_config = GridConfig(size=3, density=0.0)  # Start with empty grid
    grid = create_grid(grid_config)
    # Set specific cells to create a simple pattern
    grid[0][1] = True  # Top middle
    grid[1][1] = True  # Center
    grid[2][1] = True  # Bottom middle

    try:
        # Act
        render_grid(term, grid, renderer_config)

        # We can't directly test terminal output in unit tests,
        # but we can verify the function runs without errors
        # Integration tests would verify actual terminal output
    finally:
        cleanup_terminal(term)


def test_grid_rendering_empty() -> None:
    """
    Given: A terminal and an empty grid
    When: Rendering the grid
    Then: Should display all dead cells
    """
    renderer_config = RendererConfig()
    term = initialize_terminal(renderer_config)
    grid = create_grid(GridConfig(size=3, density=0.0))

    try:
        render_grid(term, grid, renderer_config)
    finally:
        cleanup_terminal(term)


def test_input_handling_quit() -> None:
    """
    Given: A terminal instance
    When: User presses 'q'
    Then: Should return QUIT command
    """
    config = RendererConfig()
    term = initialize_terminal(config)

    try:
        # Simulate 'q' keypress
        key = MockKeystroke(name="q")
        result = handle_user_input(term, key)
        assert result == "quit"
    finally:
        cleanup_terminal(term)


def test_input_handling_continue() -> None:
    """
    Given: A terminal instance
    When: User presses any other key
    Then: Should return CONTINUE command
    """
    config = RendererConfig()
    term = initialize_terminal(config)

    try:
        # Simulate 'x' keypress
        key = MockKeystroke(name="x")
        result = handle_user_input(term, key)
        assert result == "continue"
    finally:
        cleanup_terminal(term)


def test_input_handling_ctrl_c() -> None:
    """
    Given: A terminal instance
    When: User presses Ctrl-C
    Then: Should return QUIT command
    """
    config = RendererConfig()
    term = initialize_terminal(config)

    try:
        # Simulate Ctrl-C
        key = MockKeystroke(name="^C", is_sequence=True)
        result = handle_user_input(term, key)
        assert result == "quit"
    finally:
        cleanup_terminal(term)


def test_handle_resize_event() -> None:
    """
    Given: A terminal instance
    When: Terminal is resized
    Then: Should clear screen and rehide cursor
    """
    config = RendererConfig()
    term = initialize_terminal(config)

    try:
        # Test resize handling
        handle_resize_event(term)
        # We can't test actual resize, but we can verify it runs without errors
    finally:
        cleanup_terminal(term)


def test_safe_render_grid_handles_errors() -> None:
    """
    Given: A terminal instance and grid
    When: Rendering encounters an error
    Then: Should cleanup terminal and raise appropriate error
    """
    config = RendererConfig()
    term = initialize_terminal(config)
    grid = create_grid(GridConfig(size=3, density=0.0))

    try:
        # Test normal rendering
        safe_render_grid(term, grid, config)

        # Test error handling by forcing an error
        # We'll do this by temporarily breaking the terminal's move_xy
        original_move_xy = term.move_xy
        term.move_xy = lambda x, y: (_ for _ in ()).throw(IOError("Mock error"))

        try:
            safe_render_grid(term, grid, config)
            assert False, "Expected RuntimeError"
        except RuntimeError as e:
            assert "Failed to render grid" in str(e)
        finally:
            # Restore original move_xy
            term.move_xy = original_move_xy

    finally:
        cleanup_terminal(term)
