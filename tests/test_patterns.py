"""Tests for pattern functionality."""

import shutil
from pathlib import Path
from typing import Generator

import pytest

from gol.grid import Grid, Position
from gol.patterns import (
    BUILTIN_PATTERNS,
    FilePatternStorage,
    Pattern,
    PatternCategory,
    PatternMetadata,
    extract_pattern,
    find_pattern,
    get_centered_position,
    place_pattern,
)


@pytest.fixture
def temp_pattern_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for pattern storage."""
    temp_dir = Path("test_patterns")
    temp_dir.mkdir(exist_ok=True)
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def pattern_storage(temp_pattern_dir: Path) -> FilePatternStorage:
    """Create pattern storage with temporary directory."""
    return FilePatternStorage(storage_dir=temp_pattern_dir)


def test_pattern_creation() -> None:
    """
    Given: Pattern metadata and cells
    When: Creating a pattern
    Then: Pattern should be created with correct attributes
    """
    metadata = PatternMetadata(
        name="test", description="Test pattern", category=PatternCategory.CUSTOM
    )
    cells = [[True, True], [True, True]]

    pattern = Pattern(metadata=metadata, cells=cells, width=2, height=2)

    assert pattern.metadata.name == "test"
    assert pattern.width == 2
    assert pattern.height == 2
    assert pattern.cells == cells


def test_pattern_validation() -> None:
    """
    Given: Invalid pattern dimensions
    When: Creating a pattern
    Then: Should raise ValueError
    """
    metadata = PatternMetadata(
        name="invalid", description="Invalid pattern", category=PatternCategory.CUSTOM
    )
    cells = [[True]]  # 1x1 cells

    with pytest.raises(ValueError):
        Pattern(metadata=metadata, cells=cells, width=2, height=2)  # Wrong dimensions


def test_pattern_storage_save_load(temp_pattern_dir: Path) -> None:
    """
    Given: A pattern and storage system
    When: Saving and loading the pattern
    Then: Loaded pattern should match saved pattern
    """
    pattern = BUILTIN_PATTERNS["glider"]
    storage = FilePatternStorage(storage_dir=temp_pattern_dir)

    # Save pattern
    storage.save_pattern(pattern)

    # Load pattern
    loaded = storage.load_pattern("glider")

    assert loaded is not None
    assert loaded.metadata.name == pattern.metadata.name
    assert loaded.cells == pattern.cells
    assert loaded.width == pattern.width
    assert loaded.height == pattern.height


def test_pattern_extraction() -> None:
    """
    Given: A grid with a known pattern
    When: Extracting a region
    Then: Should create correct pattern
    """
    # Create grid with a block pattern
    grid = Grid(
        [
            [True, True, False],
            [True, True, False],
            [False, False, False],
        ]
    )

    metadata = PatternMetadata(
        name="extracted_block",
        description="Extracted block pattern",
        category=PatternCategory.STILL_LIFE,
    )

    pattern = extract_pattern(
        grid,
        top_left=Position((0, 0)),
        bottom_right=Position((1, 1)),
        metadata=metadata,
    )

    assert pattern.width == 2
    assert pattern.height == 2
    assert all(all(cell for cell in row) for row in pattern.cells)


def test_pattern_placement() -> None:
    """
    Given: A grid and a pattern
    When: Placing the pattern
    Then: Should correctly place pattern at specified position
    """
    # Create empty grid
    grid = Grid([[False] * 5 for _ in range(5)])
    pattern = BUILTIN_PATTERNS["block"]

    # Place pattern with centering disabled to test exact position
    new_grid = place_pattern(grid, pattern, Position((1, 1)), centered=False)

    # Check block placement
    assert new_grid[1][1]  # Top-left
    assert new_grid[1][2]  # Top-right
    assert new_grid[2][1]  # Bottom-left
    assert new_grid[2][2]  # Bottom-right


def test_centered_pattern_placement() -> None:
    """
    Given: A grid and a pattern
    When: Placing the pattern with centering enabled
    Then: Should correctly center the pattern at the specified position
    """
    # Create empty 7x7 grid
    grid = Grid([[False] * 7 for _ in range(7)])
    pattern = BUILTIN_PATTERNS["block"]

    # Place pattern at (3, 3) with centering enabled (default)
    # For a 2x2 block pattern:
    # - Geometric center is at (1, 1) in pattern coordinates
    # - When centered at (3, 3), top-left should be at (2, 2)
    new_grid = place_pattern(grid, pattern, Position((3, 3)))

    # Check block placement - should be centered around (3, 3)
    assert new_grid[2][2]  # Top-left
    assert new_grid[2][3]  # Top-right
    assert new_grid[3][2]  # Bottom-left
    assert new_grid[3][3]  # Bottom-right

    # Verify surrounding cells are empty
    assert not new_grid[1][1]  # Upper-left empty
    assert not new_grid[1][4]  # Upper-right empty
    assert not new_grid[4][1]  # Lower-left empty
    assert not new_grid[4][4]  # Lower-right empty


def test_pattern_finding() -> None:
    """Test finding patterns in a grid."""
    # Create a grid with two non-overlapping block patterns
    grid = Grid(
        [
            [False, False, False, False, False, False],
            [False, True, True, False, False, False],
            [False, True, True, False, False, False],
            [False, False, False, True, True, False],
            [False, False, False, True, True, False],
            [False, False, False, False, False, False],
        ]
    )

    pattern = BUILTIN_PATTERNS["block"]
    positions = find_pattern(grid, pattern)

    assert len(positions) == 2
    assert Position((1, 1)) in positions
    assert Position((3, 3)) in positions


def test_builtin_patterns() -> None:
    """
    Given: Built-in pattern library
    When: Accessing patterns
    Then: Should provide valid patterns
    """
    assert "glider" in BUILTIN_PATTERNS
    assert "blinker" in BUILTIN_PATTERNS
    assert "block" in BUILTIN_PATTERNS

    # Verify each pattern is valid
    for name, pattern in BUILTIN_PATTERNS.items():
        assert pattern.metadata.name == name
        assert pattern.width > 0
        assert pattern.height > 0
        assert len(pattern.cells) == pattern.height
        assert all(len(row) == pattern.width for row in pattern.cells)


def test_get_centered_position_block_pattern() -> None:
    """
    Given: A 2x2 block pattern
    When: Calculating centered position at (10, 10)
    Then: Should return position (9, 9) to center the block
    """
    pattern = BUILTIN_PATTERNS["block"]
    cursor_pos = Position((10, 10))

    result = get_centered_position(pattern, cursor_pos)

    assert result == Position((9, 9))


def test_get_centered_position_blinker_pattern() -> None:
    """
    Given: A 1x3 blinker pattern
    When: Calculating centered position at (10, 10)
    Then: Should return position (9, 10) to center horizontally
    """
    pattern = BUILTIN_PATTERNS["blinker"]
    cursor_pos = Position((10, 10))

    result = get_centered_position(pattern, cursor_pos)

    assert result == Position((9, 10))


def test_get_centered_position_empty_pattern() -> None:
    """
    Given: A pattern with no active cells
    When: Calculating centered position
    Then: Should use geometric center
    """
    metadata = PatternMetadata(
        name="empty",
        description="Empty pattern",
        category=PatternCategory.CUSTOM,
    )
    pattern = Pattern(
        metadata=metadata,
        cells=[[False, False], [False, False]],
        width=2,
        height=2,
    )
    cursor_pos = Position((10, 10))

    result = get_centered_position(pattern, cursor_pos)

    assert result == Position((9, 9))  # Same as block pattern
