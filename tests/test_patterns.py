"""Tests for pattern functionality."""

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from gol.patterns import (
    Pattern,
    PatternCategory,
    PatternMetadata,
    extract_pattern,
    find_pattern,
    place_pattern,
)
from gol.types import Grid, GridPosition

# Load test patterns from JSON
with open(Path(__file__).parent / "test_data" / "patterns.json") as f:
    TEST_PATTERNS = json.load(f)["test_patterns"]


@pytest.mark.parametrize("pattern_name", TEST_PATTERNS.keys())
def test_pattern_creation(pattern_name: str) -> None:
    """Test pattern creation from test data.

    Given: Pattern data from test patterns
    When: Creating a pattern object
    Then: Pattern should be created with correct attributes
    """
    pattern_data = TEST_PATTERNS[pattern_name]
    pattern = Pattern(
        metadata=PatternMetadata(
            name=pattern_data["name"],
            description=pattern_data["description"],
            category=PatternCategory[pattern_data["category"]],
        ),
        cells=np.array(pattern_data["pattern"], dtype=np.bool_),
    )

    assert pattern.metadata.name == pattern_data["name"]
    assert pattern.width == len(pattern_data["pattern"][0])
    assert pattern.height == len(pattern_data["pattern"])
    assert np.array_equal(
        pattern.cells, np.array(pattern_data["pattern"], dtype=np.bool_)
    )


@pytest.mark.parametrize("pattern_data", TEST_PATTERNS.values())
def test_pattern_placement(pattern_data: dict[str, Any], test_grid: Grid) -> None:
    """Test pattern placement on grid.

    Given: A pattern and target grid
    When: Placing the pattern at different positions
    Then: Pattern should be correctly placed
    """
    pattern = Pattern(
        metadata=PatternMetadata(
            name=pattern_data["name"],
            description=pattern_data["description"],
            category=PatternCategory[pattern_data["category"]],
        ),
        cells=np.array(pattern_data["pattern"], dtype=np.bool_),
    )

    # Test non-centered placement first
    pos: GridPosition = (1, 1)  # Use (1,1) to ensure pattern fits
    grid_with_pattern = place_pattern(test_grid.copy(), pattern, pos, centered=False)
    pattern_region = grid_with_pattern[
        pos[0] : pos[0] + pattern.height,
        pos[1] : pos[1] + pattern.width,
    ]
    assert np.array_equal(pattern_region, pattern.cells)

    # Test centered placement
    cursor_pos: GridPosition = (test_grid.shape[0] // 2, test_grid.shape[1] // 2)
    grid_with_centered_pattern = place_pattern(
        test_grid.copy(), pattern, cursor_pos, centered=True
    )

    # Find the pattern in the grid to verify placement
    found_positions = find_pattern(grid_with_centered_pattern, pattern)
    assert len(found_positions) == 1
    found_pos = found_positions[0]

    # Verify pattern was placed correctly at the found position
    pattern_region = grid_with_centered_pattern[
        found_pos[0] : found_pos[0] + pattern.height,
        found_pos[1] : found_pos[1] + pattern.width,
    ]
    assert np.array_equal(pattern_region, pattern.cells)


@pytest.mark.parametrize("pattern_data", TEST_PATTERNS.values())
def test_pattern_finding(pattern_data: dict[str, Any], test_grid: Grid) -> None:
    """Test finding patterns in grid.

    Given: A pattern and grid containing that pattern
    When: Searching for pattern occurrences
    Then: Should find all pattern instances
    """
    pattern = Pattern(
        metadata=PatternMetadata(
            name=pattern_data["name"],
            description=pattern_data["description"],
            category=PatternCategory[pattern_data["category"]],
        ),
        cells=np.array(pattern_data["pattern"], dtype=np.bool_),
    )

    # Place pattern at known position without centering
    pos: GridPosition = (1, 1)  # Use (1,1) to ensure pattern fits
    grid_with_pattern = place_pattern(test_grid.copy(), pattern, pos, centered=False)

    # Find pattern
    found_positions = find_pattern(grid_with_pattern, pattern)
    assert pos in found_positions

    # Test finding centered pattern
    cursor_pos: GridPosition = (test_grid.shape[0] // 2, test_grid.shape[1] // 2)
    grid_with_centered_pattern = place_pattern(
        test_grid.copy(), pattern, cursor_pos, centered=True
    )
    found_positions = find_pattern(grid_with_centered_pattern, pattern)
    assert len(found_positions) == 1


@pytest.mark.parametrize("pattern_data", TEST_PATTERNS.values())
def test_pattern_extraction(pattern_data: dict[str, Any], test_grid: Grid) -> None:
    """Test pattern extraction from grid.

    Given: A grid with known pattern
    When: Extracting pattern region
    Then: Should extract correct pattern
    """
    pattern = Pattern(
        metadata=PatternMetadata(
            name=pattern_data["name"],
            description=pattern_data["description"],
            category=PatternCategory[pattern_data["category"]],
        ),
        cells=np.array(pattern_data["pattern"], dtype=np.bool_),
    )

    # Place pattern at known position without centering
    pos: GridPosition = (1, 1)  # Use (1,1) to ensure pattern fits
    grid_with_pattern = place_pattern(test_grid.copy(), pattern, pos, centered=False)

    # Extract pattern
    extracted = extract_pattern(
        grid_with_pattern,
        pos,
        (pos[0] + pattern.height - 1, pos[1] + pattern.width - 1),
        pattern.metadata,
    )

    assert np.array_equal(extracted.cells, pattern.cells)
    assert extracted.metadata.name == pattern.metadata.name
