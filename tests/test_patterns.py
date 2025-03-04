"""Tests for pattern functionality."""

import shutil
from pathlib import Path
from typing import Generator

import numpy as np
import pytest

from gol.patterns import (
    BUILTIN_PATTERNS,
    FilePatternStorage,
    Pattern,
    PatternCategory,
    PatternMetadata,
    extract_pattern,
    find_pattern,
    get_centered_position,
    get_pattern_cells,
    place_pattern,
)
from gol.types import Grid, GridPosition


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


@pytest.fixture
def simple_pattern() -> Pattern:
    """Provides a simple 2x2 test pattern."""
    return Pattern(
        metadata=PatternMetadata(
            name="test", description="test pattern", category=PatternCategory.CUSTOM
        ),
        cells=np.array([[True, False], [False, True]], dtype=np.bool_),
    )


@pytest.fixture
def test_grid() -> Grid:
    """Provides a 3x3 test grid with a known pattern."""
    return np.array(
        [[False, True, False], [False, False, True], [True, True, True]], dtype=np.bool_
    )


def test_pattern_creation() -> None:
    """
    Given: Pattern metadata and cells
    When: Creating a pattern
    Then: Pattern should be created with correct attributes
    """
    metadata = PatternMetadata(
        name="test", description="Test pattern", category=PatternCategory.CUSTOM
    )
    cells = np.array([[True, True], [True, True]], dtype=np.bool_)

    pattern = Pattern(metadata=metadata, cells=cells)
    assert pattern.width == 2
    assert pattern.height == 2
    assert np.array_equal(pattern.cells, cells)


def test_pattern_validation() -> None:
    """Test pattern dimension validation and type conversion."""
    # Test list conversion
    pattern = Pattern(
        metadata=PatternMetadata(
            name="test", description="test pattern", category=PatternCategory.CUSTOM
        ),
        cells=np.array([[True, False], [False, True]], dtype=np.bool_),
    )
    assert isinstance(pattern.cells, np.ndarray)
    assert pattern.cells.dtype == np.bool_

    # Test non-boolean array conversion
    pattern2 = Pattern(
        metadata=PatternMetadata(
            name="test2", description="test pattern", category=PatternCategory.CUSTOM
        ),
        cells=np.array([[1, 0], [0, 1]], dtype=np.int32),  # Integer array input
    )
    assert isinstance(pattern2.cells, np.ndarray)
    assert pattern2.cells.dtype == np.bool_
    assert np.array_equal(
        pattern2.cells, np.array([[True, False], [False, True]], dtype=np.bool_)
    )


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
    assert np.array_equal(loaded.cells, pattern.cells)
    assert loaded.width == pattern.width
    assert loaded.height == pattern.height


def test_pattern_extraction() -> None:
    """
    Given: A grid with a known pattern
    When: Extracting a region
    Then: Should create correct pattern
    """
    # Create grid with a block pattern
    grid = np.array(
        [
            [True, True, False],
            [True, True, False],
            [False, False, False],
        ],
        dtype=np.bool_,
    )

    metadata = PatternMetadata(
        name="extracted",
        description="Extracted pattern",
        category=PatternCategory.CUSTOM,
    )

    pattern = extract_pattern(grid, (0, 0), (1, 1), metadata)
    assert pattern.width == 2
    assert pattern.height == 2
    assert np.array_equal(
        pattern.cells, np.array([[True, True], [True, True]], dtype=np.bool_)
    )


def test_pattern_placement() -> None:
    """
    Given: A grid and a pattern
    When: Placing the pattern
    Then: Should correctly place pattern at specified position
    """
    # Create empty grid
    grid = np.zeros((5, 5), dtype=np.bool_)
    pattern = Pattern(
        metadata=PatternMetadata(
            name="test",
            description="Test pattern",
            category=PatternCategory.CUSTOM,
        ),
        cells=np.array([[True, True], [True, True]], dtype=np.bool_),
    )

    new_grid = place_pattern(grid, pattern, (1, 1), centered=False)
    assert np.array_equal(
        new_grid[1:3, 1:3], np.array([[True, True], [True, True]], dtype=np.bool_)
    )


def test_centered_pattern_placement() -> None:
    """
    Given: A grid and a pattern
    When: Placing the pattern with centering enabled
    Then: Should correctly center the pattern at the specified position
    """
    # Create empty 7x7 grid
    grid = np.zeros((7, 7), dtype=np.bool_)
    pattern = Pattern(
        metadata=PatternMetadata(
            name="test",
            description="Test pattern",
            category=PatternCategory.CUSTOM,
        ),
        cells=np.array([[True, True], [True, True]], dtype=np.bool_),
    )

    new_grid = place_pattern(grid, pattern, (3, 3), centered=True)
    assert np.array_equal(
        new_grid[2:4, 2:4], np.array([[True, True], [True, True]], dtype=np.bool_)
    )


def test_pattern_finding() -> None:
    """Test finding patterns in a grid."""
    # Create a grid with two non-overlapping block patterns
    grid = np.array(
        [
            [False, False, False, False, False, False],
            [False, True, True, False, False, False],
            [False, True, True, False, False, False],
            [False, False, False, True, True, False],
            [False, False, False, True, True, False],
            [False, False, False, False, False, False],
        ],
        dtype=np.bool_,
    )

    pattern = Pattern(
        metadata=PatternMetadata(
            name="block",
            description="2x2 block",
            category=PatternCategory.STILL_LIFE,
        ),
        cells=np.array([[True, True], [True, True]], dtype=np.bool_),
    )

    positions = find_pattern(grid, pattern)
    assert len(positions) == 2
    assert (1, 1) in positions
    assert (3, 3) in positions


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
    pattern = Pattern(
        metadata=PatternMetadata(
            name="block",
            description="2x2 block",
            category=PatternCategory.STILL_LIFE,
        ),
        cells=np.array([[True, True], [True, True]], dtype=np.bool_),
    )
    cursor_pos: GridPosition = (10, 10)
    pos = get_centered_position(pattern, cursor_pos)
    assert pos == (9, 9)


def test_get_centered_position_blinker_pattern() -> None:
    """
    Given: A 1x3 blinker pattern
    When: Calculating centered position at (10, 10)
    Then: Should return position (9, 10) to center horizontally
    """
    pattern = Pattern(
        metadata=PatternMetadata(
            name="blinker",
            description="1x3 blinker",
            category=PatternCategory.OSCILLATOR,
        ),
        cells=np.array([[True, True, True]], dtype=np.bool_),
    )
    cursor_pos: GridPosition = (10, 10)
    pos = get_centered_position(pattern, cursor_pos)
    assert pos == (9, 10)


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
    pattern = Pattern(metadata=metadata, cells=np.zeros((2, 2), dtype=np.bool_))
    cursor_pos: GridPosition = (10, 10)
    pos = get_centered_position(pattern, cursor_pos)
    assert pos == (9, 9)


def test_get_centered_position(simple_pattern: Pattern) -> None:
    """Test centered position calculation."""
    pos = get_centered_position(simple_pattern, (5, 5))
    assert pos == (4, 4)

    # Test with rotation
    pos = get_centered_position(simple_pattern, (5, 5), rotation=90)
    assert pos == (4, 4)


def test_place_pattern(test_grid: Grid, simple_pattern: Pattern) -> None:
    """Test pattern placement on grid."""
    # Create a fresh empty grid to avoid interference from existing patterns
    grid = np.zeros((5, 5), dtype=np.bool_)

    # Test normal placement
    new_grid = place_pattern(grid, simple_pattern, (0, 0), centered=False)
    # The simple_pattern is [[True, False], [False, True]]
    assert bool(new_grid[0, 0])  # Should be True
    assert not bool(new_grid[0, 1])  # Should be False
    assert not bool(new_grid[1, 0])  # Should be False
    assert bool(new_grid[1, 1])  # Should be True

    # Test centered placement
    new_grid = place_pattern(grid, simple_pattern, (2, 2), centered=True)
    assert isinstance(new_grid, np.ndarray)
    assert new_grid.dtype == np.bool_


def test_find_pattern(test_grid: Grid) -> None:
    """Test pattern finding in grid."""
    # Create a specific test grid with exactly one occurrence of the pattern
    grid = np.array(
        [
            [False, False, False, False],
            [False, True, True, False],
            [False, False, False, False],
        ],
        dtype=np.bool_,
    )

    pattern = Pattern(
        metadata=PatternMetadata(
            name="test", description="test pattern", category=PatternCategory.CUSTOM
        ),
        cells=np.array([[True, True]], dtype=np.bool_),
    )

    positions = find_pattern(grid, pattern)
    assert len(positions) == 1
    assert (1, 1) in positions  # Pattern starts at (1,1)


def test_get_pattern_cells(simple_pattern: Pattern) -> None:
    """Test pattern cell position calculation with rotation"""
    # Test no rotation
    cells: list[GridPosition] = get_pattern_cells(simple_pattern)
    assert (0, 0) in cells
    assert (1, 1) in cells

    # Test 90 degree rotation
    cells = get_pattern_cells(simple_pattern, rotation=1)
    assert len(cells) == 2

    # Test 180 degree rotation
    cells = get_pattern_cells(simple_pattern, rotation=2)
    assert len(cells) == 2

    # Test 270 degree rotation
    cells = get_pattern_cells(simple_pattern, rotation=3)
    assert len(cells) == 2


def test_file_pattern_storage(tmp_path: Path) -> None:
    """Test pattern storage and retrieval with NumPy arrays."""
    storage = FilePatternStorage(storage_dir=tmp_path)
    pattern = Pattern(
        metadata=PatternMetadata(
            name="test", description="test pattern", category=PatternCategory.CUSTOM
        ),
        cells=np.array([[True]], dtype=np.bool_),
    )

    storage.save_pattern(pattern)
    loaded = storage.load_pattern("test")
    assert loaded is not None
    assert loaded.metadata.name == pattern.metadata.name
    assert np.array_equal(loaded.cells, pattern.cells)
    assert "test" in storage.list_patterns()


def test_extract_pattern(test_grid: Grid) -> None:
    """Test pattern extraction from grid."""
    metadata = PatternMetadata(
        name="extracted",
        description="extracted pattern",
        category=PatternCategory.CUSTOM,
    )
    pattern = extract_pattern(test_grid, (0, 0), (1, 1), metadata)
    assert pattern.width == 2
    assert pattern.height == 2
    assert np.array_equal(
        pattern.cells, np.array([[False, True], [False, False]], dtype=np.bool_)
    )
