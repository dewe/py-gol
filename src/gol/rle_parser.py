"""RLE pattern parser for Game of Life."""

import re
from dataclasses import dataclass
from typing import cast

import numpy as np

from .pattern_types import Pattern, PatternCategory, PatternMetadata
from .types import PatternGrid


class RLEParseError(Exception):
    """Raised when RLE pattern parsing fails."""


@dataclass
class RLEDimensions:
    """Pattern dimensions from RLE header."""

    width: int
    height: int


def parse_header_line(line: str) -> tuple[str, str]:
    """Parse a header line from RLE file.

    Args:
        line: Line starting with # followed by type and value

    Returns:
        Tuple of (type, value) where type is the character after #

    Raises:
        RLEParseError: If header line format is invalid
    """
    match = re.match(r"#(\w)\s+(.+)", line)
    if not match:
        raise RLEParseError(f"Invalid header line format: {line}")
    return match.group(1), match.group(2)


def parse_dimensions(line: str) -> RLEDimensions:
    """Parse the dimensions line from an RLE file.

    Args:
        line: Line containing x = W, y = H format, optionally with rule

    Returns:
        RLEDimensions with width and height

    Raises:
        RLEParseError: If dimensions line is invalid
    """
    # Extract width and height using regex
    width_match = re.search(r"x\s*=\s*(\d+)", line)
    height_match = re.search(r"y\s*=\s*(\d+)", line)

    if not width_match or not height_match:
        raise RLEParseError(f"Invalid dimensions line format: {line}")

    try:
        width = int(width_match.group(1))
        height = int(height_match.group(1))
        return RLEDimensions(width=width, height=height)
    except ValueError:
        raise RLEParseError(f"Invalid dimension values: {line}")


def parse_pattern_data(data: str, dimensions: RLEDimensions) -> PatternGrid:
    """Parse the RLE pattern data into a numpy array.

    Args:
        data: RLE encoded pattern data
        dimensions: Pattern dimensions

    Returns:
        Boolean numpy array of pattern cells

    Raises:
        RLEParseError: If pattern data is invalid
    """
    # Initialize empty pattern grid
    pattern = np.zeros((dimensions.height, dimensions.width), dtype=np.bool_)

    # Remove whitespace and split into runs
    data = "".join(data.split())
    if not data.endswith("!"):
        raise RLEParseError("Pattern data must end with !")

    # Parse pattern data
    x, y = 0, 0
    run_count = ""

    for char in data:
        if char.isdigit():
            run_count += char
            if run_count.startswith("0"):
                raise RLEParseError("Run count cannot start with 0")
        elif char in "bo$!":
            try:
                count = int(run_count) if run_count else 1
            except ValueError:
                raise RLEParseError(f"Invalid run count: {run_count}")
            run_count = ""

            if char == "b":  # Dead cells
                x += count
            elif char == "o":  # Live cells
                for i in range(count):
                    if x >= dimensions.width:
                        raise RLEParseError("Pattern data exceeds specified width")
                    if y >= dimensions.height:
                        raise RLEParseError("Pattern data exceeds specified height")
                    pattern[y, x] = True
                    x += 1
            elif char == "$":  # End of row
                if x > dimensions.width:
                    raise RLEParseError("Pattern data exceeds specified width")
                y += count
                x = 0
            elif char == "!":  # End of pattern
                break
        else:
            raise RLEParseError(f"Invalid character in pattern data: {char}")

    if y > dimensions.height:
        raise RLEParseError("Pattern data exceeds specified height")

    return cast(PatternGrid, pattern)


def parse_rle_pattern(content: str) -> Pattern:
    """Parse RLE pattern file content into Pattern object.

    Args:
        content: RLE file content as string

    Returns:
        Pattern object with metadata and cells

    Raises:
        RLEParseError: If pattern format is invalid
    """
    lines = content.strip().split("\n")
    if not lines:
        raise RLEParseError("Empty pattern file")

    # Parse metadata from header
    name = ""
    description = ""
    author = ""
    current_line = 0

    while current_line < len(lines) and lines[current_line].startswith("#"):
        line_type, value = parse_header_line(lines[current_line])
        if line_type == "N":
            name = value
        elif line_type == "C":
            description = value
        elif line_type == "O":
            author = value
        current_line += 1

    if current_line >= len(lines):
        raise RLEParseError("Missing pattern data")

    # Parse dimensions
    try:
        dimensions = parse_dimensions(lines[current_line])
    except (RLEParseError, ValueError) as e:
        raise RLEParseError(f"Invalid dimensions: {e}")
    current_line += 1

    if current_line >= len(lines):
        raise RLEParseError("Missing pattern data")

    # Parse pattern data
    pattern_data = "".join(lines[current_line:])
    try:
        cells = parse_pattern_data(pattern_data, dimensions)
    except RLEParseError as e:
        raise RLEParseError(f"Invalid pattern data: {e}")

    return Pattern(
        metadata=PatternMetadata(
            name=name,
            description=description,
            category=PatternCategory.CUSTOM,
            author=author,
        ),
        cells=cells,
    )
