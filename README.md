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

## Game Rules

Conway's Game of Life follows these rules:

1. Any live cell with fewer than two live neighbors dies (underpopulation)
2. Any live cell with two or three live neighbors survives
3. Any live cell with more than three live neighbors dies (overpopulation)
4. Any dead cell with exactly three live neighbors becomes alive (reproduction)

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

## Development

### Project Structure

```text
py-gol/
├── src/
│   └── gol/
│       ├── __init__.py
│       ├── actor.py      # Cell actor implementation
│       ├── controller.py # Game controller
│       ├── grid.py       # Grid management
│       ├── main.py       # Main application
│       ├── messaging.py  # Message queue system
│       └── renderer.py   # Terminal renderer
├── tests/
│   └── ...               # Test files
├── game.py               # Entry point script
├── setup.py              # Package setup
└── README.md             # This file
```

### Running Tests

```bash
make test
```

## License

[MIT License](LICENSE)
