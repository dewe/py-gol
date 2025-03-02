# py-gol

A terminal-based implementation of Conway's Game of Life using an actor-based concurrent model where each cell operates independently.

## Features

- **Actor-Based Concurrency**: Each cell is implemented as an independent actor
- **Thread-Safe Communication**: Actors communicate via thread-safe message queues
- **Functional Approach**: Pure functional approach for state transitions
- **Terminal UI**: Full-screen terminal interface using the Blessed library
- **Configurable**: Adjustable grid size, update interval, and initial cell density
- **Adaptive Refresh Rate**: Screen refresh rate automatically optimized based on update interval
- **Toroidal Grid**: Optional wrapping of edges to create a continuous surface

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
./game.py [--width <width>] [--height <height>] [--interval <ms>] [--density <float>] [--toroidal]
```

### Parameters

- `--width`: Width of the grid (auto-sized to terminal width if not specified)
- `--height`: Height of the grid (auto-sized to terminal height if not specified)
- `--interval`: Update interval in milliseconds (default: 100)
- `--density`: Initial density of live cells (0.0-1.0, default: 0.3)
- `--toroidal`: Enable toroidal grid (edges wrap around)

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

Run with terminal-sized grid, fast updates, and toroidal wrapping:

```bash
./game.py --interval 50 --toroidal
```

## Game Controls

- Press `q` or `Q` to quit the game
- Press `Ctrl-C` to exit gracefully
- Press `Escape` to exit
- Press `r` to restart the game with a new grid
- Press `↑` to slow down the simulation (increase interval)
- Press `↓` to speed up the simulation (decrease interval)

## Game Rules

Conway's Game of Life follows these rules:

1. Any live cell with fewer than two live neighbors dies (underpopulation)
2. Any live cell with two or three live neighbors survives
3. Any live cell with more than three live neighbors dies (overpopulation)
4. Any dead cell with exactly three live neighbors becomes alive (reproduction)

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

- **Actor Model**: Each cell runs in its own thread and communicates via messages
- **No Shared State**: Cells don't share mutable state, preventing race conditions
- **Pure Functions**: State transitions are implemented as pure functions
- **Thread Safety**: All inter-actor communication is thread-safe
- **Adaptive Rendering**: Screen refresh rate automatically adjusts to update interval

### Components

- **Grid Management**: Handles the game's state representation
- **Cell Actor System**: Implements individual cell behavior
- **Message Queue System**: Provides thread-safe communication
- **Renderer**: Visualizes the game state in the terminal with adaptive refresh rate
- **Main Controller**: Orchestrates the game lifecycle
