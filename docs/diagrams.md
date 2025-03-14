# Component Interaction Diagrams

This document illustrates the key interactions between components in the Game of Life implementation using sequence diagrams.

## Game Initialization Sequence

```mermaid
sequenceDiagram
    participant Main
    participant Controller
    participant Commands
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
    Controller->>Commands: initialize_command_handler()
    Commands-->>Controller: return command_handler
    Controller->>Metrics: initialize_metrics()
    Metrics-->>Controller: return metrics_state
```

## Game Loop and Pattern Management

```mermaid
sequenceDiagram
    participant Main
    participant Controller
    participant Commands
    participant Grid
    participant Patterns
    participant Renderer
    participant State
    participant Life
    participant Metrics
    
    Main->>Controller: run_game_loop()
    loop Game Loop
        Controller->>Commands: handle_input()
        Commands-->>Controller: return command
        alt pattern_mode
            Controller->>Patterns: handle_pattern_command()
            Patterns-->>Controller: return updated_grid
        end
        alt running
            Controller->>Life: process_generation()
            Life->>Grid: apply_rules()
            Grid-->>Life: return new_grid
            Life-->>Controller: return new_grid
        end
        Controller->>State: update_state()
        State-->>Controller: return new_state
        Controller->>Renderer: render_frame()
        Renderer->>Renderer: update_display()
        Controller->>Metrics: update_metrics()
    end
```

## Pattern System Flow

```mermaid
sequenceDiagram
    participant Controller
    participant Commands
    participant Patterns
    participant Grid
    participant State
    
    Controller->>Commands: handle_pattern_command()
    Commands->>Patterns: load_pattern()
    Patterns->>Grid: place_pattern()
    Grid-->>Patterns: return updated_grid
    Patterns->>State: update_state()
    State-->>Controller: return updated_state
```

## Renderer Update Sequence

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
        Types[Type Definitions]
    end

    %% Impure Shell
    subgraph Impure ["Impure Shell"]
        Main[Main Application]
        Commands[Command Handler]
        Controller[Game Controller]
        Renderer[Terminal Renderer]
    end

    %% Connections
    Main --> Controller
    Controller --> Commands
    Controller --> Grid
    Controller --> Life
    Controller --> State
    Controller --> Pattern
    Controller --> Metrics
    Commands --> Pattern
    Commands --> Grid
    Renderer --> Grid
    
    %% Type System
    Types --> Grid
    Types --> Life
    Types --> State
    Types --> Pattern
    Types --> Metrics
    Types --> Controller
    Types --> Commands
    Types --> Renderer

    %% Styling
    classDef pure fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef impure fill:#ffebee,stroke:#b71c1c,stroke-width:2px;
    class Grid,Life,State,Pattern,Metrics,Types pure;
    class Main,Commands,Controller,Renderer impure;
```

## Pattern State Flow

```mermaid
stateDiagram-v2
    [*] --> Normal
    Normal --> PatternMode: P Key
    PatternMode --> Preview: Enter
    Preview --> Selected: Number Key
    Selected --> Rotated: R Key
    Rotated --> Selected: R Key
    Selected --> Placed: Space
    Placed --> PatternMode
    PatternMode --> Normal: Esc/P Key

    %% Styling
    classDef state fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px;
    class Normal,PatternMode,Preview,Selected,Rotated,Placed state;
```

## Pattern Placement Workflow

1. Enter pattern mode (P key)
2. Select pattern (number keys)
3. Optional: Rotate pattern (R key)
4. Place pattern (Space)
5. Exit pattern mode (Esc)
