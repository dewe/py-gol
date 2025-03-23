"""Tests for RLE pattern storage functionality."""

from pathlib import Path

import numpy as np

from gol.patterns import FilePatternStorage, Pattern, PatternCategory, PatternMetadata


def test_list_patterns(tmp_path: Path) -> None:
    """Test listing available RLE patterns.

    Given: A directory with RLE pattern files
    When: Listing available patterns
    Then: Should return list of pattern names without extension
    """
    storage = FilePatternStorage(storage_dir=tmp_path)

    # Create test RLE files
    patterns = ["glider", "blinker", "block"]
    for name in patterns:
        pattern_file = tmp_path / f"{name}.rle"
        pattern_file.write_text(f"#N {name}\nx = 3, y = 3\nbo$2bo$3o!")

    # Create some non-RLE files that should be ignored
    (tmp_path / "test.txt").write_text("not a pattern")
    (tmp_path / "test.json").write_text("{}")

    available_patterns = storage.list_patterns()
    assert sorted(available_patterns) == sorted(patterns)


def test_load_pattern(tmp_path: Path) -> None:
    """Test loading an RLE pattern file.

    Given: An RLE pattern file
    When: Loading the pattern
    Then: Should return correct Pattern object
    """
    storage = FilePatternStorage(storage_dir=tmp_path)

    # Create test RLE file
    rle_content = """
#N Glider
#O Richard K. Guy
#C A glider moving southeast
x = 3, y = 3
bob$2bo$3o!
""".strip()

    pattern_file = tmp_path / "glider.rle"
    pattern_file.write_text(rle_content)

    pattern = storage.load_pattern("glider")
    assert pattern is not None
    assert pattern.metadata.name == "Glider"
    assert pattern.metadata.author == "Richard K. Guy"
    assert "glider moving southeast" in pattern.metadata.description.lower()
    assert pattern.metadata.category == PatternCategory.CUSTOM

    expected_cells = np.array(
        [[False, True, False], [False, False, True], [True, True, True]], dtype=np.bool_
    )

    assert np.array_equal(pattern.cells, expected_cells)


def test_load_nonexistent_pattern(tmp_path: Path) -> None:
    """Test loading a non-existent pattern.

    Given: A pattern name that doesn't exist
    When: Attempting to load the pattern
    Then: Should return None
    """
    storage = FilePatternStorage(storage_dir=tmp_path)
    assert storage.load_pattern("nonexistent") is None


def test_save_pattern(tmp_path: Path) -> None:
    """Test saving a pattern to RLE format.

    Given: A Pattern object
    When: Saving the pattern
    Then: Should create correct RLE file
    """
    storage = FilePatternStorage(storage_dir=tmp_path)

    pattern = Pattern(
        metadata=PatternMetadata(
            name="Test Pattern",
            description="A test pattern",
            category=PatternCategory.CUSTOM,
            author="Test Author",
        ),
        cells=np.array(
            [[False, True, False], [False, False, True], [True, True, True]],
            dtype=np.bool_,
        ),
    )

    storage.save_pattern(pattern)

    # Verify file was created
    pattern_file = tmp_path / "Test Pattern.rle"
    assert pattern_file.exists()

    # Verify file content
    content = pattern_file.read_text()
    assert "#N Test Pattern" in content
    assert "#O Test Author" in content
    assert "#C A test pattern" in content
    assert "x = 3, y = 3" in content

    # Load pattern back and verify it matches
    loaded_pattern = storage.load_pattern("Test Pattern")
    assert loaded_pattern is not None
    assert loaded_pattern.metadata.name == pattern.metadata.name
    assert loaded_pattern.metadata.author == pattern.metadata.author
    assert loaded_pattern.metadata.description == pattern.metadata.description
    assert np.array_equal(loaded_pattern.cells, pattern.cells)


def test_save_pattern_creates_directory(tmp_path: Path) -> None:
    """Test saving pattern creates storage directory if needed.

    Given: A non-existent storage directory
    When: Saving a pattern
    Then: Should create directory and save pattern
    """
    storage_dir = tmp_path / "patterns"
    storage = FilePatternStorage(storage_dir=storage_dir)

    pattern = Pattern(
        metadata=PatternMetadata(
            name="Test", description="Test pattern", category=PatternCategory.CUSTOM
        ),
        cells=np.array([[True]], dtype=np.bool_),
    )

    assert not storage_dir.exists()
    storage.save_pattern(pattern)
    assert storage_dir.exists()
    assert (storage_dir / "Test.rle").exists()


def test_pattern_storage_with_empty_directory(tmp_path: Path) -> None:
    """Test pattern storage with empty directory.

    Given: An empty storage directory
    When: Listing and loading patterns
    Then: Should handle empty directory gracefully
    """
    storage = FilePatternStorage(storage_dir=tmp_path)

    assert storage.list_patterns() == []
    assert storage.load_pattern("any") is None
