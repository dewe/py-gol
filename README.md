# py-gol

A terminal-based implementation of Conway's Game of Life using an actor-based concurrent model where each cell operates independently.

## Features

- **Actor-Based Concurrency**: Each cell is implemented as an independent actor
- **Thread-Safe Communication**: Actors communicate via thread-safe message queues
- **Functional Approach**: Pure functional approach for state transitions
- **Terminal UI**: Full-screen terminal interface using the Blessed library
- **Configurable**: Adjustable grid size, update interval, and initial cell density

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
./gol.py <grid_size> [--interval <ms>] [--density <float>]
```

### Command-Line Arguments

- `grid_size`: Size of the grid (N for N×N) - **required**
- `--interval`: Update interval in milliseconds (default: 100)
- `--density`: Initial density of live cells between 0.0 and 1.0 (default: 0.3)

### Examples

Run with a 20×20 grid using default settings:
```bash
./gol.py 20
```

Run with a 30×30 grid, slower updates, and higher initial density:
```bash
./gol.py 30 --interval 200 --density 0.5
```

Run with a small 10×10 grid and fast updates:
```bash
./gol.py 10 --interval 50
```

## Game Controls

- Press `q` to quit the game
- Press `Ctrl+C` to exit gracefully

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

### Components

- **Grid Management**: Handles the game's state representation
- **Cell Actor System**: Implements individual cell behavior
- **Message Queue System**: Provides thread-safe communication
- **Renderer**: Visualizes the game state in the terminal
- **Main Controller**: Orchestrates the game lifecycle

## Development

### Project Structure

```
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
├── gol.py                # Entry point script
├── setup.py              # Package setup
└── README.md             # This file
```

### Running Tests

```bash
make test
```

## License

[MIT License](LICENSE)
