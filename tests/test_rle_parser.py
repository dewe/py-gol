"""Tests for RLE pattern file parsing."""

from pathlib import Path

import numpy as np
import pytest

from gol.patterns import PatternCategory
from gol.rle_parser import RLEParseError, parse_rle_pattern


def test_parse_basic_rle_pattern() -> None:
    """Test parsing a basic RLE pattern.

    Given: A simple RLE pattern string with header and pattern data
    When: Parsing the RLE pattern
    Then: Should return correct Pattern object with metadata and cells
    """
    rle_content = """
#N Test Pattern
#O Test Author
#C Test comment
x = 3, y = 3, rule = B3/S23
bob$2bo$3o!
""".strip()

    pattern = parse_rle_pattern(rle_content)

    assert pattern.metadata.name == "Test Pattern"
    assert pattern.metadata.author == "Test Author"
    assert pattern.metadata.description == "Test comment"
    assert pattern.metadata.category == PatternCategory.CUSTOM

    expected_cells = np.array(
        [[False, True, False], [False, False, True], [True, True, True]], dtype=np.bool_
    )

    assert np.array_equal(pattern.cells, expected_cells)


def test_parse_rle_pattern_with_minimal_header() -> None:
    """Test parsing RLE pattern with minimal header.

    Given: An RLE pattern with only required header fields
    When: Parsing the RLE pattern
    Then: Should return Pattern with default metadata values
    """
    rle_content = """
x = 2, y = 2
bo$bo!
""".strip()

    pattern = parse_rle_pattern(rle_content)

    assert pattern.metadata.name == ""
    assert pattern.metadata.author == ""
    assert pattern.metadata.description == ""
    assert pattern.metadata.category == PatternCategory.CUSTOM

    expected_cells = np.array([[False, True], [False, True]], dtype=np.bool_)

    assert np.array_equal(pattern.cells, expected_cells)


def test_parse_rle_pattern_with_run_counts() -> None:
    """Test parsing RLE pattern with run counts.

    Given: An RLE pattern using run counts for repeated cells
    When: Parsing the RLE pattern
    Then: Should correctly expand run counts into cell array
    """
    rle_content = """
#N Block
x = 4, y = 4
4b$b2ob$b2ob$4b!
""".strip()

    pattern = parse_rle_pattern(rle_content)

    expected_cells = np.array(
        [
            [False, False, False, False],
            [False, True, True, False],
            [False, True, True, False],
            [False, False, False, False],
        ],
        dtype=np.bool_,
    )

    assert np.array_equal(pattern.cells, expected_cells)


def test_parse_invalid_rle_pattern() -> None:
    """Test parsing invalid RLE pattern.

    Given: An invalid RLE pattern string
    When: Attempting to parse the pattern
    Then: Should raise RLEParseError with descriptive message
    """
    invalid_patterns = [
        # Missing dimensions
        "bob$2bo$3o!",
        # Invalid dimension format
        "x = a, y = 3\nbo$bo$bo!",
        # Pattern data doesn't match dimensions
        "x = 2, y = 2\nbo$bo$bo!",
        # Invalid run count
        "x = 2, y = 2\n0bo$bo!",
        # Invalid character in pattern
        "x = 2, y = 2\nbo$bx!",
    ]

    for invalid_pattern in invalid_patterns:
        with pytest.raises(RLEParseError):
            parse_rle_pattern(invalid_pattern)


def test_parse_rle_pattern_from_file(tmp_path: Path) -> None:
    """Test parsing RLE pattern from file.

    Given: An RLE pattern file
    When: Reading and parsing the file
    Then: Should return correct Pattern object
    """
    rle_content = """
#N Test Pattern
x = 3, y = 3
bob$2bo$3o!
""".strip()

    pattern_file = tmp_path / "test.rle"
    pattern_file.write_text(rle_content)

    pattern = parse_rle_pattern(pattern_file.read_text())

    expected_cells = np.array(
        [[False, True, False], [False, False, True], [True, True, True]], dtype=np.bool_
    )

    assert np.array_equal(pattern.cells, expected_cells)
