# Architecture Diagrams

## Component Architecture

```mermaid
graph TD
    %% Core Components
    subgraph Pure ["Pure Core"]
        Grid[Grid]
        Life[Life Rules]
        State[State]
        Pattern[Patterns]
        Metrics[Metrics]
        Types[Types]
    end

    %% Shell Components
    subgraph Shell ["Shell"]
        Main[Main]
        Commands[Commands]
        Controller[Controller]
        Renderer[Renderer]
    end

    %% Dependencies
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

    %% Styling
    classDef pure fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef shell fill:#ffebee,stroke:#b71c1c,stroke-width:2px
    class Grid,Life,State,Pattern,Metrics,Types pure
    class Main,Commands,Controller,Renderer shell
```

## Game Loop

```mermaid
sequenceDiagram
    participant Controller
    participant Commands
    participant Life
    participant Grid
    participant State
    participant Renderer
    
    loop Game Loop
        Controller->>Commands: handle_input()
        alt pattern_mode
            Commands->>Grid: place_pattern()
        end
        alt running
            Controller->>Life: process_generation()
            Life->>Grid: apply_rules()
        end
        Controller->>State: update_state()
        Controller->>Renderer: render_frame()
    end
```

## Pattern System

```mermaid
stateDiagram-v2
    [*] --> Normal
    Normal --> Pattern: P
    Pattern --> Selected: Number
    Selected --> Rotated: R
    Selected --> Pattern: Space
    Pattern --> Normal: Esc/P

    classDef state fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    class Normal,Pattern,Selected,Rotated state
```

## Type Dependencies

```mermaid
graph LR
    GameState --> Grid
    Pattern --> Grid
    Command --> GameState
    Metrics --> Statistics
    Position --> Grid
    Size --> Grid
    
    classDef type fill:#f9f,stroke:#333,stroke-width:2px
    class GameState,Grid,Pattern,Command,Metrics,Statistics,Position,Size type
```

## Key Features

1. **Pure Functions**: All state transitions and pattern operations
2. **Immutable State**: Grid and pattern states
3. **Type Safety**: Protocol classes and type hints
4. **Pattern System**: Metadata and transformations
5. **Performance**: Metrics tracking and optimization
