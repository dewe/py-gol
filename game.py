#!/usr/bin/env python3
"""Entry point for Game of Life."""

import sys

from gol.main import main


def run_game() -> None:
    """Run the Game of Life application."""
    try:
        main()
    except SystemExit as e:
        # Preserve exit code from argparse help/error
        sys.exit(e.code)
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print("\nGame terminated by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run_game()
