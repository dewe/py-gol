# py-gol

A terminal-based implementation of Conway's Game of Life with a focus on functional programming and pattern management.

## Features

- **Functional Core**: Pure functions for state transitions and pattern management
- **Pattern System**: Built-in patterns and custom pattern support
- **Terminal UI**: Full-screen terminal interface using the Blessed library
- **Cell Age Visualization**: Cells change color based on their age:
  - White (youngest, age 1)
  - Light gray (age 2-3)
  - Gray (age 4-5)
  - Faded pink (age 6-10)
  - Dark pink (age 11-20)
  - Dark red (oldest, age 21+)
  - Dimmed cells for dead state
- **Pattern Management**: Support for loading, saving, and manipulating patterns
- **Configurable**: Adjustable grid size, update interval, initial density, and boundary conditions
- **Adaptive Refresh**: Screen refresh rate automatically optimized based on update interval
- **Multiple Boundary Types**: Support for finite, toroidal, and infinite boundaries

![demo](./docs/demo.gif)

## Architecture Diagrams

The architecture of this project is documented with Mermaid diagrams in [docs/diagrams.md](docs/diagrams.md). The diagrams include:

1. **Actor Communication Flow** - Shows how cell actors interact with neighbors, the renderer, and controller
2. **Component Architecture** - Illustrates the relationships between major system components
3. **Cell State Transitions** - Visualizes the rules of Conway's Game of Life as state transitions

## Installation

Clone the repository and install the package:

```bash
git clone https://github.com/yourusername/py-gol.git
cd py-gol
pip install -e .
```

## Usage

Run the game using the provided entry point script:

```bash
./game.py [--width <width>] [--height <height>] [--interval <ms>] [--density <float>] [--boundary <type>]
```

### Parameters

- `--width`: Width of the grid (auto-sized to terminal width if not specified)
- `--height`: Height of the grid (auto-sized to terminal height if not specified)
- `--interval`: Update interval in milliseconds (default: 100)
- `--density`: Initial density of live cells (0.0-1.0, default: 0.3)
- `--boundary`: Boundary condition type: 'finite', 'toroidal', or 'infinite' (default: finite)

### Examples

Run with default settings (grid sized to terminal dimensions):

```bash
./game.py
```

Run with a custom 20×20 grid:

```bash
./game.py --width 20 --height 20
```

Run with a 30×30 grid, slower updates, and higher initial density:

```bash
./game.py --width 30 --height 30 --interval 200 --density 0.5
```

Run with terminal-sized grid, fast updates, and toroidal boundaries:

```bash
./game.py --interval 50 --boundary toroidal
```

## Game Controls

- Press `q` or `Q` to quit the game
- Press `Ctrl-C` to exit gracefully
- Press `Escape` to exit
- Press `r` to restart with a new grid
- Press `↑` to slow down the simulation
- Press `↓` to speed up the simulation
- Press `p` to enter pattern mode
- Press `r` to rotate pattern (in pattern mode)
- Press `Space` to place pattern
- Press `Escape` to exit pattern mode
- Press `1-9` to select patterns
- Press `b` to cycle boundary conditions

## Pattern System

The game includes a pattern system that allows you to place and manipulate predefined patterns on the grid:

### Built-in Patterns

- **Block**: A stable 2×2 square pattern
- **Blinker**: A simple period-2 oscillator
- **Glider**: A classic pattern that moves diagonally across the grid

### Pattern Mode Controls

1. Press `p` to enter pattern mode
2. Select a pattern from the numbered list
3. Use arrow keys to move the cursor
4. Press `[` or `]` to rotate the pattern (90-degree increments)
5. Press `Space` to place the pattern at the cursor position
6. Press `Escape` to exit pattern mode

### Pattern Storage

The game automatically saves custom patterns to `~/.gol/patterns/`. Each pattern is stored as a JSON file containing:

- Pattern metadata (name, description, category)
- Cell configuration
- Pattern dimensions

### Pattern Categories

Patterns are organized into categories:
- Still Life: Stable patterns that don't change
- Oscillator: Patterns that repeat in a cycle
- Spaceship: Patterns that move across the grid
- Gun: Patterns that emit other patterns
- Methuselah: Patterns with long evolutionary sequences
- Custom: User-created patterns

## Game Rules

Conway's Game of Life follows these rules:

1. Any live cell with fewer than two live neighbors dies (underpopulation)
2. Any live cell with two or three live neighbors survives
3. Any live cell with more than three live neighbors dies (overpopulation)
4. Any dead cell with exactly three live neighbors becomes alive (reproduction)

### Cell Age Visualization

The game tracks the age of each living cell, which is visualized through a color progression:

- Cells start white when they first come alive
- As cells survive more generations, their color gradually changes:
  1. White (age 1) - Newly born cells
  2. Light gray (age 2-3) - Young cells
  3. Gray (age 4-5) - Maturing cells
  4. Faded pink (age 6-10) - Established cells
  5. Dark pink (age 11-20) - Aging cells
  6. Dark red (age 21+) - Ancient cells
- Dead cells are shown in a dimmed state

This visualization helps track stable structures and identify areas of high activity in the grid.

## Development

### Project Structure

```text
py-gol/
├── src/
│   └── gol/
│       ├── __init__.py
│       ├── actor.py          # Cell actor implementation
│       ├── controller.py     # Game controller
│       ├── grid.py           # Grid management
│       ├── main.py           # Main application
│       ├── messaging.py      # Message queue system
│       └── renderer.py       # Terminal renderer
├── tests/
│   ├── __init__.py
│   ├── test_actor.py        # Actor system tests
│   ├── test_controller.py   # Game controller tests
│   ├── test_grid.py         # Grid management tests
│   ├── test_messaging.py    # Message system tests
│   └── test_renderer.py     # Terminal UI tests
├── game.py                  # Entry point script
├── setup.py                 # Package setup
├── pyproject.toml           # Project configuration
├── Makefile                 # Build automation
└── README.md                # This file
```

### Running Tests

Tests are organized to match the source code structure, with dedicated test files for each core component. The test suite includes:

- Unit tests for individual components
- Integration tests for component interactions
- Thread safety tests for concurrent operations
- Terminal rendering tests with mock terminal

Run the full test suite with:

```bash
make test
```

Or run specific test files:

```bash
pytest tests/test_actor.py    # Test actor system only
pytest tests/test_grid.py     # Test grid management only
```

## License

[MIT License](LICENSE)

## Development Requirements

- **blessed**: Terminal UI library for rendering and input handling
- **pytest**: Testing framework for unit and integration tests
- **mypy**: Static type checking
- **ruff**: Fast Python linter

## Architecture

The implementation follows these architectural principles:

- **Functional Core**: State transitions and pattern operations are pure functions
- **Immutable State**: Grid and pattern states are immutable
- **Type Safety**: Strong typing with Protocol classes and type hints
- **Pattern Management**: Extensible pattern system with metadata
- **Efficient Updates**: Differential rendering for performance
- **Boundary Handling**: Multiple boundary condition support

### Components

- **Grid Management**: Handles the game grid with boundary conditions
- **Pattern System**: Manages pattern storage, placement, and manipulation
- **State Management**: Pure functions for game state transitions
- **Renderer**: Terminal-based visualization with adaptive refresh
- **Controller**: Game lifecycle and user input management
