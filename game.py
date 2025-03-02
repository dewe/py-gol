#!/usr/bin/env python3
"""Entry point for Game of Life."""

import sys
from pathlib import Path


def run_game() -> None:
    """Run the Game of Life application."""
    # Add the src directory to the Python path
    src_path = Path(__file__).parent / "src"
    sys.path.insert(0, str(src_path))

    # Import after path modification
    from gol.main import main

    main()


if __name__ == "__main__":
    run_game()
