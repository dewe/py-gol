"""RLE (Run Length Encoded) pattern file parser."""

import re
from dataclasses import dataclass
from typing import Tuple

import numpy as np

from gol.pattern_types import Pattern, PatternCategory, PatternMetadata
from gol.types import PatternGrid


class RLEParseError(Exception):
    """Raised when RLE pattern parsing fails."""

    pass


@dataclass
class RLEDimensions:
    """Pattern dimensions from RLE header."""

    width: int
    height: int


def parse_header_line(line: str) -> Tuple[str, str]:
    """Parse a header line from an RLE file.

    Args:
        line: Line starting with # from RLE file

    Returns:
        Tuple of (key, value) where key is N/O/C and value is the content

    Raises:
        RLEParseError: If header line is invalid
    """
    if not line.startswith("#"):
        raise RLEParseError(f"Invalid header line: {line}")

    try:
        key = line[1].upper()
        value = line[2:].strip()
        if key not in ["N", "O", "C"]:
            raise RLEParseError(f"Invalid header key: {key}")
        return key, value
    except IndexError:
        raise RLEParseError(f"Invalid header line format: {line}")


def parse_dimensions(line: str) -> RLEDimensions:
    """Parse the dimensions line from an RLE file.

    Args:
        line: Line containing x = W, y = H format

    Returns:
        RLEDimensions with width and height

    Raises:
        RLEParseError: If dimensions line is invalid
    """
    # Remove whitespace and split on comma
    parts = [p.strip() for p in line.split(",")]
    if len(parts) != 2:
        raise RLEParseError(f"Invalid dimensions line format: {line}")

    try:
        # Extract width and height values
        width_match = re.search(r"x\s*=\s*(\d+)", parts[0])
        height_match = re.search(r"y\s*=\s*(\d+)", parts[1])

        if not width_match or not height_match:
            raise RLEParseError(f"Invalid dimensions format: {line}")

        width = int(width_match.group(1))
        height = int(height_match.group(1))
        return RLEDimensions(width=width, height=height)
    except (AttributeError, ValueError):
        raise RLEParseError(f"Invalid dimensions format: {line}")


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
        elif char in "bo$!":
            count = int(run_count) if run_count else 1
            run_count = ""

            if char == "b":  # Dead cells
                x += count
            elif char == "o":  # Live cells
                for i in range(count):
                    if x >= dimensions.width:
                        raise RLEParseError("Pattern data exceeds specified width")
                    pattern[y, x] = True
                    x += 1
            elif char == "$":  # End of row
                if x > dimensions.width:
                    raise RLEParseError("Pattern data exceeds specified width")
                y += count
                x = 0
            elif char == "!":  # End of pattern
                if y >= dimensions.height:
                    raise RLEParseError("Pattern data exceeds specified height")
        else:
            raise RLEParseError(f"Invalid character in pattern data: {char}")

    if y >= dimensions.height:
        raise RLEParseError("Pattern data exceeds specified height")

    return pattern


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
