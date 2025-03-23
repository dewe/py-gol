# py-gol

A terminal-based implementation of Conway's Game of Life using functional
programming principles.

## Features

- Pure functional core with immutable state
- Pattern system with built-in and custom patterns
- Full-screen terminal interface with dynamic resizing
- Multiple boundary types (finite, toroidal, infinite)
- Performance metrics and optimization

![demo](./docs/demo.gif)

## Architecture

The implementation follows functional core/imperative shell architecture:

### Pure Core

- Grid operations and life rules
- State transitions and pattern operations
- Performance metrics

### Shell

- Terminal I/O and user input
- Pattern storage and loading
- Game loop coordination

## Installation

```bash
git clone https://github.com/yourusername/py-gol.git
cd py-gol
pip install -e .
```

## Usage

```bash
./game.py [--width <width>] [--height <height>] [--interval <ms>] \
          [--density <float>] [--boundary <type>]
```

### Parameters

- `--width`: Grid width (auto-sized if 0, min 30)
- `--height`: Grid height (auto-sized if 0, min 20)
- `--interval`: Update interval in ms (default: 200)
- `--density`: Initial density (0.0-1.0, default: 0.3)
- `--boundary`: Boundary type: 'finite', 'toroidal', 'infinite' (default: finite)

## Controls

### Normal Mode

| Key         | Action                    |
|-------------|---------------------------|
| Space       | Start/Stop               |
| P           | Pattern mode             |
| C           | Clear grid               |
| R           | Restart                  |
| B           | Cycle boundaries         |
| +/-         | Resize grid              |
| Arrows      | Pan viewport             |
| Shift+↑/↓   | Speed control            |
| Q, Esc      | Quit                     |

### Pattern Mode

| Key         | Action                    |
|-------------|---------------------------|
| 1-9         | Select pattern           |
| R           | Rotate pattern           |
| Space       | Place pattern            |
| Arrows      | Move cursor              |
| P, Esc      | Exit pattern mode        |

## Pattern System

Built-in patterns include:

- Block (stable)
- Blinker (oscillator)
- Glider (spaceship)
- Gosper Glider Gun (pattern generator)

Custom patterns are stored in `patterns/` as RLE files.

The RLE (Run Length Encoded) format is the standard format for Life patterns,
as specified in [LifeWiki's RLE format](https://conwaylife.com/wiki/Run_Length_Encoded).
It provides a compact representation for patterns and includes metadata like
author, description, and discovery year.

Example RLE file:

```text
#N Glider
#O Richard K. Guy
#C The smallest, most common spaceship.
#C www.conwaylife.com/wiki/index.php?title=Glider
x = 3, y = 3
bob$2bo$3o!
```

## Development

### Project Structure

```text
py-gol/
├── src/gol/
│   ├── controller.py   # Game controller and state management
│   ├── commands.py     # Command processing and handlers
│   ├── grid.py        # Grid operations and boundaries
│   ├── life.py        # Life rules and transitions
│   ├── main.py        # Application entry and config
│   ├── metrics.py     # Performance tracking
│   ├── patterns.py    # Pattern management and operations
│   ├── pattern_types.py # Pattern-related type definitions
│   ├── rle_parser.py  # RLE pattern format parser
│   ├── renderer.py    # Terminal UI and display
│   ├── state.py       # State management
│   └── types.py       # Type definitions
├── tests/             # Test modules
├── docs/              # Documentation
├── specs/             # Specifications
├── patterns/          # Pattern files
└── game.py           # Entry point
```

See [docs/diagrams.md](docs/diagrams.md) for architecture diagrams and
[docs/dependencies.md](docs/dependencies.md) for detailed dependency information.
