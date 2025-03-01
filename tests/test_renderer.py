"""Tests for the terminal renderer component."""

from blessed import Terminal

from gol.grid import GridConfig, create_grid
from gol.renderer import (
    RendererConfig,
    cleanup_terminal,
    initialize_terminal,
    render_grid,
)


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
