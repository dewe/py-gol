# py-gol

A terminal-based implementation of Conway's Game of Life with a focus on functional programming and pattern management.

## Features

- **Functional Core**: Pure functions for state transitions and pattern management
- **Pattern System**: Built-in patterns and custom pattern support
- **Terminal UI**: Full-screen terminal interface using the Blessed library
- **Pattern Management**: Support for loading, saving, and manipulating patterns
- **Configurable**: Adjustable grid size, update interval, initial density, and boundary conditions
- **Dynamic Resizing**: Grid automatically fits terminal dimensions with proper margins (minimum 30×20)
- **Adaptive Refresh**: Screen refresh rate automatically optimized based on update interval
- **Multiple Boundary Types**: Support for finite, toroidal, and infinite boundaries
- **Performance Metrics**: Built-in performance monitoring and optimization
- **Type Safety**: Comprehensive type hints and static type checking

![demo](./docs/demo.gif)

## Architecture

The implementation follows a functional core/imperative shell architecture:

### Pure Functional Core

- **Grid Operations**: Pure functions for grid manipulation
- **Life Rules**: Pure functions implementing game rules
- **State Transitions**: Immutable state updates
- **Pattern Operations**: Pure pattern transformations
- **Performance Metrics**: Pure metrics collection and analysis

### Impure Shell

- **Terminal I/O**: Display updates and user input
- **File Operations**: Pattern storage and loading
- **Signal Handling**: System signal management
- **Game Loop**: State coordination and updates

### Key Principles

- Clear separation between pure and impure code
- Immutable data structures for state management
- Side effects isolated to specific modules
- Type safety through static typing
- Efficient updates through SciPy operations
- Performance monitoring and optimization

## Architecture Diagrams

The architecture of this project is documented with Mermaid diagrams in [docs/diagrams.md](docs/diagrams.md). The diagrams include:

1. **Component Architecture** - Illustrates the relationships between major system components
2. **Game Loop Flow** - Shows the main game loop and state transitions
3. **Pattern System Flow** - Visualizes pattern management and placement
4. **Renderer Update Sequence** - Details the rendering pipeline

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

- `--width`: Width of the grid (auto-sized to terminal width if not specified or set to 0, minimum 30)
- `--height`: Height of the grid (auto-sized to terminal height if not specified or set to 0, minimum 20)
- `--interval`: Update interval in milliseconds (default: 200)
- `--density`: Initial density of live cells (0.0-1.0, default: 0.3)
- `--boundary`: Boundary condition type: 'finite', 'toroidal', or 'infinite' (default: finite)

### Examples

Run with default settings (grid auto-sized to terminal dimensions):

```bash
./game.py
```

Run with a custom 40×30 grid (must be at least 30×20):

```bash
./game.py --width 40 --height 30
```

Run with auto-sized grid, slower updates, and higher initial density:

```bash
./game.py --interval 200 --density 0.5
```

Run with auto-sized grid, fast updates, and toroidal boundaries:

```bash
./game.py --interval 50 --boundary toroidal
```

## Game Controls

### Normal Mode

| Key         | Action                         |
|-------------|--------------------------------|
| Space       | Start/Stop simulation          |
| P           | Enter pattern mode             |
| C           | Clear grid                     |
| R           | Restart with new grid          |
| B           | Cycle boundary conditions      |
| +           | Resize grid larger             |
| -           | Resize grid smaller            |
| Arrow keys  | Pan viewport                   |
| Shift+Up    | Increase simulation speed      |
| Shift+Down  | Decrease simulation speed      |
| Q, Esc      | Quit game                      |

### Pattern Mode

| Key         | Action                         |
|-------------|--------------------------------|
| 1-9         | Select pattern                 |
| R           | Rotate pattern                 |
| Space       | Place pattern                  |
| Arrow keys  | Move cursor                    |
| P, Esc      | Exit pattern mode              |
| Q           | Quit game                      |

### Speed Control

The simulation speed can be adjusted using Shift+Up/Down keys:

- Maximum speed: 10 generations/second (100ms interval)
- Minimum speed: 0.5 generations/second (2000ms interval)
- Speed adjustments are inverse proportional to current speed
  - At lower speeds, changes are larger
  - At higher speeds, changes are smaller
- All interval values are rounded to nearest 10ms
- Default speed: 5 generations/second (200ms interval)

### Grid Constraints

- Minimum grid size: 10×10 cells
- Maximum grid size: 200×200 cells
- Grid resize operations maintain aspect ratio
- Viewport panning stops at grid boundaries
- Viewport size adapts to terminal dimensions

### Pattern Mode Features

- Pattern rotation occurs in 90-degree increments
- Patterns can be placed at grid boundaries
- Cursor movement wraps around grid edges
- Pattern selection can be done repeatedly
- Pattern mode can be exited with 'P' or ESC
- Pattern placement is allowed even if pattern extends beyond grid
- Cursor position is preserved when exiting/entering pattern mode

## Pattern System

The game includes a pattern system that allows you to place and manipulate predefined patterns on the grid:

### Built-in Patterns

- **Block**: A stable 2×2 square pattern
- **Blinker**: A simple period-2 oscillator
- **Glider**: A classic pattern that moves diagonally across the grid
- **Gosper Glider Gun**: A pattern that continuously emits gliders

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

### Cell Visualization

Dead cells are shown in a dimmed state, while live cells are shown in bright white. The grid is automatically centered in the terminal with proper margins for UI elements.

## Development

### Project Structure

```text
py-gol/
├── src/
│   └── gol/
│       ├── __init__.py
│       ├── controller.py     # Game controller
│       ├── grid.py          # Grid management
│       ├── life.py          # Life rules
│       ├── main.py          # Main application
│       ├── metrics.py       # Performance metrics
│       ├── patterns.py      # Pattern management
│       ├── renderer.py      # Terminal renderer
│       ├── state.py         # State management
│       └── types.py         # Type definitions
├── tests/
│   ├── __init__.py
│   ├── test_controller.py   # Game controller tests
│   ├── test_grid.py        # Grid management tests
│   ├── test_life.py        # Life rules tests
│   ├── test_patterns.py    # Pattern system tests
│   └── test_renderer.py    # Terminal UI tests
├── docs/
│   ├── dependencies.md      # Module dependencies
│   ├── diagrams.md         # Architecture diagrams
│   └── demo.gif            # Demo animation
├── game.py                 # Entry point script
├── setup.py               # Package setup
├── pyproject.toml        # Project configuration
├── Makefile             # Build automation
└── README.md            # This file
```

### Running Tests

Tests are organized to match the source code structure, with dedicated test files for each core component. The test suite includes:

- Unit tests for individual components
- Integration tests for component interactions
- Performance tests for optimization
- Terminal rendering tests with mock terminal

Run the full test suite with:

```bash
make test
```

Or run specific test files:

```bash
pytest tests/test_grid.py     # Test grid management only
pytest tests/test_life.py     # Test life rules only
```

## License

[MIT License](LICENSE)

## Development Requirements

- **blessed**: Terminal UI library for rendering and input handling
- **scipy**: Scientific computing library for array operations
- **pytest**: Testing framework for unit and integration tests
- **mypy**: Static type checking
- **ruff**: Fast Python linter

## Architecture principles

The implementation follows these architectural principles:

- **Functional Core**: State transitions and pattern operations are pure functions
- **Immutable State**: Grid and pattern states are immutable
- **Type Safety**: Strong typing with Protocol classes and type hints
- **Pattern Management**: Extensible pattern system with metadata
- **Efficient Updates**: Differential rendering for performance
- **Boundary Handling**: Multiple boundary condition support
- **Performance Monitoring**: Built-in metrics collection and analysis

### Components

- **Grid Management**: Handles the game grid with boundary conditions
- **Pattern System**: Manages pattern storage, placement, and manipulation
- **State Management**: Pure functions for game state transitions
- **Performance Metrics**: Tracks and analyzes system performance
- **Terminal Renderer**: Efficient terminal display and user input
