"""Shared test fixtures and utilities."""

from pathlib import Path
from typing import Generator

import numpy as np
import pytest

from gol.patterns import Pattern, PatternCategory, PatternMetadata
from gol.types import Grid


@pytest.fixture
def test_grid() -> Grid:
    """Provides a 5x5 empty test grid.

    Returns:
        A 5x5 empty grid for testing
    """
    return np.zeros((5, 5), dtype=np.bool_)


@pytest.fixture
def simple_pattern() -> Pattern:
    """Provides a simple 2x2 test pattern.

    Returns:
        A 2x2 pattern for testing
    """
    return Pattern(
        metadata=PatternMetadata(
            name="test", description="test pattern", category=PatternCategory.CUSTOM
        ),
        cells=np.array([[True, False], [False, True]], dtype=np.bool_),
    )


def create_test_grid(pattern: list[list[bool]]) -> Grid:
    """Creates a test grid from a pattern.

    Args:
        pattern: List of boolean lists representing the grid

    Returns:
        Grid array with proper type
    """
    return np.array(pattern, dtype=np.bool_)


@pytest.fixture
def temp_test_dir() -> Generator[Path, None, None]:
    """Creates a temporary directory for test data.

    Yields:
        Path to temporary directory that is cleaned up after test
    """
    temp_dir = Path("test_data")
    temp_dir.mkdir(exist_ok=True)
    yield temp_dir
    import shutil

    shutil.rmtree(temp_dir)
