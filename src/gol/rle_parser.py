"""RLE (Run Length Encoded) pattern file parser."""

import re
from dataclasses import dataclass
from typing import Tuple

import numpy as np

from gol.patterns import Pattern, PatternCategory, PatternMetadata
from gol.types import PatternGrid


class RLEParseError(Exception):
    """Raised when RLE pattern parsing fails."""


@dataclass(frozen=True)
class RLEDimensions:
    """Pattern dimensions from RLE header."""

    width: int
    height: int


def parse_header_line(line: str) -> Tuple[str, str]:
    """Parse a header line starting with # into key and value.

    Args:
        line: Header line starting with #

    Returns:
        Tuple of (key, value) where key is the header type (N/O/C)
        and value is the header content
    """
    if not line.startswith("#"):
        raise RLEParseError(f"Invalid header line: {line}")

    if len(line) < 3:
        raise RLEParseError(f"Header line too short: {line}")

    return line[1], line[2:].strip()


def parse_dimensions(line: str) -> RLEDimensions:
    """Parse the dimensions line of an RLE pattern.

    Args:
        line: Line containing pattern dimensions (x = N, y = M)

    Returns:
        RLEDimensions with parsed width and height

    Raises:
        RLEParseError: If dimensions line is invalid
    """
    # Extract dimensions with regex
    match = re.match(r"x\s*=\s*(\d+)\s*,\s*y\s*=\s*(\d+)", line)
    if not match:
        raise RLEParseError(f"Invalid dimensions line: {line}")

    try:
        width = int(match.group(1))
        height = int(match.group(2))
        if width <= 0 or height <= 0:
            raise RLEParseError(f"Invalid dimensions: {width}x{height}")
        return RLEDimensions(width=width, height=height)
    except ValueError as e:
        raise RLEParseError(f"Failed to parse dimensions: {e}")


def parse_pattern_data(data: str, dimensions: RLEDimensions) -> PatternGrid:
    """Parse the pattern data section of an RLE pattern.

    Args:
        data: Pattern data string in RLE format
        dimensions: Expected pattern dimensions

    Returns:
        Boolean numpy array representing the pattern

    Raises:
        RLEParseError: If pattern data is invalid or doesn't match dimensions
    """
    # Initialize empty pattern grid
    grid = np.zeros((dimensions.height, dimensions.width), dtype=np.bool_)

    # Remove whitespace and split into runs
    data = "".join(data.split())
    if not data.endswith("!"):
        raise RLEParseError("Pattern data must end with !")

    # Parse pattern data
    row = 0
    col = 0
    run_count = ""

    for char in data:
        if char.isdigit():
            run_count += char
            continue

        count = int(run_count) if run_count else 1
        run_count = ""

        if count <= 0:
            raise RLEParseError("Invalid run count: 0")

        if char == "$":  # End of line
            if col > 0:  # Only increment if we wrote something
                row += 1
                col = 0
            row += count - 1  # Additional rows for multi-line jumps
        elif char == "!":  # End of pattern
            break
        elif char in "bo":  # Dead or alive cell
            if col + count > dimensions.width:
                raise RLEParseError(f"Pattern data exceeds width at row {row}")
            if row >= dimensions.height:
                raise RLEParseError(f"Pattern data exceeds height")

            # Set cells in grid
            grid[row, col : col + count] = char == "o"
            col += count
        else:
            raise RLEParseError(f"Invalid character in pattern data: {char}")

    if row < dimensions.height - 1:
        raise RLEParseError("Pattern data has fewer rows than specified")

    return grid


def parse_rle_pattern(content: str) -> Pattern:
    """Parse an RLE pattern file into a Pattern object.

    Args:
        content: Complete RLE pattern file contents

    Returns:
        Pattern object with metadata and cell grid

    Raises:
        RLEParseError: If pattern cannot be parsed
    """
    lines = content.strip().split("\n")
    if not lines:
        raise RLEParseError("Empty pattern file")

    # Parse metadata from header
    metadata = {
        "name": "",
        "author": "",
        "description": "",
    }

    current_line = 0
    while current_line < len(lines) and lines[current_line].startswith("#"):
        key, value = parse_header_line(lines[current_line])
        if key == "N":
            metadata["name"] = value
        elif key == "O":
            metadata["author"] = value
        elif key == "C":
            if metadata["description"]:
                metadata["description"] += "\n"
            metadata["description"] += value
        current_line += 1

    if current_line >= len(lines):
        raise RLEParseError("No pattern data found")

    # Parse dimensions
    dimensions = parse_dimensions(lines[current_line])
    current_line += 1

    # Parse pattern data
    pattern_data = "".join(lines[current_line:])
    cells = parse_pattern_data(pattern_data, dimensions)

    # Create pattern object
    pattern_metadata = PatternMetadata(
        name=metadata["name"],
        description=metadata["description"],
        category=PatternCategory.CUSTOM,
        author=metadata["author"],
    )

    return Pattern(metadata=pattern_metadata, cells=cells)
