# Component Interaction Diagrams

This document illustrates the key interactions between components in the Game of Life implementation using sequence diagrams.

## 1. Game Initialization Sequence

```mermaid
sequenceDiagram
    participant Main
    participant Controller
    participant Terminal
    participant Grid
    participant State
    participant Metrics
    
    Main->>Controller: parse_arguments()
    Controller->>Terminal: initialize_terminal()
    Terminal-->>Controller: return terminal, renderer_state
    Controller->>Grid: create_grid(config)
    Grid-->>Controller: return initial_grid
    Controller->>State: initialize_game()
    State-->>Controller: return game_state
    Controller->>Metrics: initialize_metrics()
    Metrics-->>Controller: return metrics_state
```

## 2. Game Loop and Pattern Management

```mermaid
sequenceDiagram
    participant Main
    participant Controller
    participant Grid
    participant Patterns
    participant Renderer
    participant State
    participant Metrics
    
    Main->>Controller: run_game_loop()
    loop Game Loop
        Controller->>Grid: process_generation()
        Grid-->>Controller: return new_grid
        Controller->>State: update_state()
        State-->>Controller: return new_state
        alt pattern_mode
            Controller->>Patterns: get_centered_position()
            Patterns-->>Controller: return position
            Controller->>Patterns: place_pattern()
            Patterns-->>Controller: return updated_grid
        end
        Controller->>Renderer: render_grid()
        Renderer->>Renderer: update_display()
        Controller->>Metrics: update_metrics()
        Controller->>Controller: handle_user_input()
    end
```

## 3. Pattern System Flow

```mermaid
sequenceDiagram
    participant Controller
    participant Patterns
    participant Storage
    participant Grid
    participant State
    
    Controller->>Patterns: load_pattern()
    Patterns->>Storage: read_pattern_file()
    Storage-->>Patterns: return pattern_data
    Patterns->>Grid: place_pattern()
    Grid-->>Patterns: return updated_grid
    Patterns->>State: update_state()
    State-->>Controller: return updated_state
```

## 4. Renderer Update Sequence

```mermaid
sequenceDiagram
    participant Controller
    participant Renderer
    participant Grid
    participant Terminal
    participant Metrics
    
    Controller->>Renderer: render_grid()
    Renderer->>Grid: grid_to_dict()
    Grid-->>Renderer: return cell_states
    alt pattern_mode
        Renderer->>Renderer: render_pattern_preview()
    end
    Renderer->>Terminal: update_display()
    Renderer->>Terminal: render_status_line()
    Renderer->>Metrics: update_render_metrics()
```

## Key Architectural Features

The sequence diagrams highlight several important architectural features:

1. **Pure Functions**: All state transitions and pattern operations are pure functions
2. **Immutable State**: Grid and pattern states are immutable
3. **Pattern Management**: Centralized pattern system with metadata
4. **Type Safety**: Strong typing with Protocol classes
5. **Boundary Handling**: Support for multiple boundary conditions
6. **Efficient Updates**: Differential rendering for changed cells only
7. **Performance Monitoring**: Metrics tracking for optimization

The implementation follows functional programming principles with:

- Immutable data structures
- Pure functions for state transitions
- Type-safe operations through protocols
- Pattern-based abstractions
- Performance metrics collection

## Component Architecture

```mermaid
---
title: Component Architecture
---
graph TD
    %% Pure Core
    subgraph Pure ["Pure Functional Core"]
        Grid[Grid Operations]
        Life[Life Rules]
        State[State Transitions]
        Pattern[Pattern Operations]
        Metrics[Performance Metrics]
    end

    %% Impure Shell
    subgraph Impure ["Impure Shell"]
        Terminal[Terminal I/O]
        FileIO[File I/O]
        Signals[Signal Handlers]
        GameLoop[Game Loop]
    end

    %% Connections
    GameLoop --> Grid
    GameLoop --> Life
    GameLoop --> State
    GameLoop --> Pattern
    GameLoop --> Metrics
    Terminal --> GameLoop
    FileIO --> Pattern
    Signals --> GameLoop

    %% Styling
    classDef pure fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef impure fill:#ffebee,stroke:#b71c1c,stroke-width:2px;
    class Grid,Life,State,Pattern,Metrics pure;
    class Terminal,FileIO,Signals,GameLoop impure;
```

## Pattern State Flow

```mermaid
stateDiagram-v2
    [*] --> Preview
    Preview --> Selected: Number Key
    Selected --> Rotated: R Key
    Rotated --> Selected: R Key
    Selected --> Placed: Space
    Placed --> [*]

    %% Styling
    classDef state fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px;
    class Preview,Selected,Rotated,Placed state;
```

This diagram shows the pattern placement workflow:

1. Enter pattern mode (P key)
2. Select pattern (number keys)
3. Optional: Rotate pattern (R key)
4. Place pattern (Space)
5. Exit pattern mode (Esc)
