"""Tests for pattern system integration."""

from pathlib import Path
from typing import cast
from unittest.mock import patch

import numpy as np
import pytest
from blessed import Terminal

from gol.commands import ControllerConfig, handle_place_pattern
from gol.pattern_types import Pattern, PatternCategory, PatternMetadata
from gol.patterns import FilePatternStorage, PatternTransform
from gol.renderer import RendererConfig, RendererState, render_pattern_menu
from gol.types import Grid, PatternGrid
from tests.conftest import create_test_grid


@pytest.fixture
def test_pattern() -> Pattern:
    """Create a test pattern."""
    return Pattern(
        metadata=PatternMetadata(
            name="test_pattern",
            description="Test pattern",
            category=PatternCategory.CUSTOM,
        ),
        cells=cast(PatternGrid, np.array([[True, True], [True, True]], dtype=np.bool_)),
    )


@pytest.fixture
def test_grid() -> Grid:
    """Create an empty test grid."""
    return create_test_grid([[False] * 10 for _ in range(10)])


def test_pattern_storage_integration(tmp_path: Path, test_pattern: Pattern) -> None:
    """Test pattern storage integration.

    Given: A pattern storage system
    When: Saving and loading patterns
    Then: Should maintain pattern integrity
    """
    storage = FilePatternStorage(storage_dir=tmp_path)

    # Save pattern
    storage.save_pattern(test_pattern)

    # Load pattern
    loaded = storage.load_pattern(test_pattern.metadata.name)
    assert loaded is not None
    assert loaded.metadata.name == test_pattern.metadata.name
    assert loaded.metadata.category == test_pattern.metadata.category
    assert np.array_equal(loaded.cells, test_pattern.cells)


def test_pattern_placement_integration(test_grid: Grid, test_pattern: Pattern) -> None:
    """Test pattern placement integration.

    Given: A pattern and grid
    When: Placing pattern through command handler
    Then: Should correctly update grid state
    """
    renderer_config = RendererConfig()
    renderer_config = renderer_config.with_pattern(test_pattern.metadata.name)

    config = ControllerConfig(
        dimensions=(10, 10),
        grid=ControllerConfig.create(width=10, height=10).grid,
        renderer=renderer_config,
    )
    state = RendererState(pattern_mode=True, cursor_x=5, cursor_y=5)

    # Place pattern
    new_grid, new_config, new_state, _ = handle_place_pattern(test_grid, config, state)

    # Verify pattern was placed
    pattern_region = new_grid[4:6, 4:6]  # 2x2 region centered at (5,5)
    assert np.array_equal(pattern_region, test_pattern.cells)
    assert new_config.renderer.selected_pattern is None  # Pattern selection cleared


def test_pattern_rotation_integration(test_grid: Grid, test_pattern: Pattern) -> None:
    """Test pattern rotation integration.

    Given: A pattern and grid
    When: Rotating and placing pattern
    Then: Should correctly place rotated pattern
    """
    renderer_config = RendererConfig()
    renderer_config = renderer_config.with_pattern(
        test_pattern.metadata.name, rotation=PatternTransform.RIGHT
    )

    config = ControllerConfig(
        dimensions=(10, 10),
        grid=ControllerConfig.create(width=10, height=10).grid,
        renderer=renderer_config,
    )
    state = RendererState(pattern_mode=True, cursor_x=5, cursor_y=5)

    # Place rotated pattern
    new_grid, new_config, new_state, _ = handle_place_pattern(test_grid, config, state)

    # Verify rotated pattern was placed correctly
    pattern_region = new_grid[4:6, 4:6]
    rotated_cells = np.rot90(test_pattern.cells, k=-1)  # -1 for clockwise rotation
    assert np.array_equal(pattern_region, rotated_cells)


def test_pattern_menu_integration(test_pattern: Pattern) -> None:
    """Test pattern menu integration.

    Given: A pattern system with stored patterns
    When: Rendering pattern menu
    Then: Should show available patterns and categories
    """
    terminal = Terminal()
    config = RendererConfig()

    # Mock storage to return our test pattern
    with patch.object(
        FilePatternStorage, "list_patterns", return_value=[test_pattern.metadata.name]
    ):
        # Set category to CUSTOM to see our test pattern
        custom_idx = next(
            i for i, cat in enumerate(PatternCategory) if cat == PatternCategory.CUSTOM
        )
        config = config.with_pattern_category_idx(custom_idx)

        # Render menu
        menu_text = render_pattern_menu(terminal, config)

        # Verify menu content
        assert "Pattern Mode" in menu_text
        assert "Custom" in menu_text
        assert test_pattern.metadata.name in menu_text
