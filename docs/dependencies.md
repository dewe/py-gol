# Dependencies

## Runtime Dependencies

- **numpy**: Grid operations
- **blessed**: Terminal UI
- **typing-extensions**: Type hints
- **attrs**: Immutable data
- **result**: Error handling

## Development Dependencies

- **pytest**: Testing
- **pytest-cov**: Coverage
- **mypy**: Type checking
- **ruff**: Linting
- **black**: Formatting
- **isort**: Import sorting

## Module Dependencies

```mermaid
graph TD
    A[main.py] --> B[controller.py]
    B --> C[commands.py]
    B --> D[grid.py]
    B --> E[life.py]
    B --> F[state.py]
    B --> G[patterns.py]
    B --> H[renderer.py]
    B --> I[metrics.py]
    C --> D
    C --> G
    D --> J[types.py]
    E --> D
    F --> D
    G --> D
    H --> D
    I --> D

    classDef module fill:#f9f,stroke:#333,stroke-width:2px
    class A,B,C,D,E,F,G,H,I,J module
```

## Module Responsibilities

### Core

- **types.py**: Type definitions and protocols
- **grid.py**: Grid operations and boundaries
- **life.py**: Game rules and transitions
- **state.py**: Game state management
- **patterns.py**: Pattern operations

### Shell

- **commands.py**: Input handling
- **renderer.py**: Terminal UI
- **controller.py**: Game coordination
- **main.py**: Application entry
- **metrics.py**: Performance tracking

## Development Tools

### Code Quality

- **mypy**: Type checking
- **ruff**: Linting
- **black**: Formatting
- **isort**: Import sorting

### Testing

- **pytest**: Testing framework
- **pytest-cov**: Coverage reporting
