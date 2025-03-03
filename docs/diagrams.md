# Component Interaction Diagrams

This document illustrates the key interactions between components in the Game of Life implementation using sequence diagrams.

## 1. Game Initialization Sequence

This diagram shows how the game components are initialized, including terminal setup and grid creation.

```mermaid
sequenceDiagram
    participant Main
    participant Controller
    participant Terminal
    participant Grid
    participant State
    
    Main->>Controller: parse_arguments()
    Controller->>Terminal: initialize_terminal()
    Terminal-->>Controller: return terminal, renderer_state
    Controller->>Grid: create_grid(config)
    Grid-->>Controller: return initial_grid
    Controller->>State: initialize_state(grid)
    State-->>Controller: return initial_state
    Controller-->>Main: return game_state
```

## 2. Game Loop and State Transition Sequence

This diagram illustrates the main game loop, showing how state transitions and rendering are handled.

```mermaid
sequenceDiagram
    participant Main
    participant Controller
    participant State
    participant Grid
    participant Renderer
    participant Terminal
    
    Main->>Controller: run_game_loop()
    loop Game Loop
        Controller->>State: calculate_next_generation()
        State->>Grid: get_cell_neighbors()
        Grid-->>State: return neighbors
        State->>State: apply_rules()
        State-->>Controller: return new_state
        Controller->>Renderer: render_grid(new_state)
        Renderer->>Terminal: update display
        Terminal->>Controller: handle_user_input()
        alt quit command
            Controller->>Main: break loop
        else restart command
            Controller->>Grid: create_grid()
            Controller->>State: initialize_state()
        end
    end
```

## 3. State Transition Flow

This diagram shows how state transitions are handled through pure functions.

```mermaid
sequenceDiagram
    participant State
    participant Grid
    participant Rules
    
    State->>Grid: get_cell_neighbors()
    Grid-->>State: return neighbors
    State->>Rules: apply_rules(cell, neighbors)
    Rules-->>State: return new_cell_state
    State->>State: update_grid_state()
```

## 4. Renderer Update Sequence

This diagram shows how the game state is visualized in the terminal with differential updates.

```mermaid
sequenceDiagram
    participant Controller
    participant Renderer
    participant Terminal
    participant Grid
    
    Controller->>Renderer: render_grid(state)
    Renderer->>Grid: get_current_state()
    Grid-->>Renderer: return grid_state
    alt state changed
        Renderer->>Terminal: move_xy()
        Renderer->>Terminal: update cell display
    end
    Renderer->>Terminal: refresh display
```

## Key Architectural Features

The sequence diagrams highlight several important architectural features of the implementation:

1. **Pure Functions**: All state transitions are handled by pure functions
2. **Immutable State**: State changes create new immutable states
3. **Functional Patterns**: Clear data flow through pure functions
4. **Component Separation**: Clear boundaries between different system components
5. **Type Safety**: Strong typing ensures correct state handling
6. **Efficient Updates**: Only changed cells trigger re-renders

The implementation follows functional programming principles with:

- Immutable state transitions
- Pure functions for state calculations
- Type-safe operations
- No shared mutable state

This architecture makes the system robust and maintainable while ensuring correctness through functional patterns.

# Architecture Diagrams

## State Transition Flow

```mermaid
graph LR
    A[Current State] -->|Pure Function| B[Next State]
    B -->|Grid Update| C[New Grid]
    C -->|Render| D[Display]
    E[Controller] -->|Tick| A

    %% Styling
    classDef component fill:#f9f,stroke:#333,stroke-width:2px;
    class A,B,C,D,E component;
```

This diagram illustrates how state transitions flow through pure functions:

1. Current state is processed by pure functions
2. Next state is calculated immutably
3. New grid state is created
4. Display is updated with changes

## Component Architecture

```mermaid
graph TD
    Controller -->|Manages| State
    Controller -->|Orchestrates| Renderer
    State -->|Updates| Grid
    Grid -->|Pure Functions| State
    Renderer -->|Displays| Grid
    Terminal -->|Input| Controller

    %% Styling
    classDef component fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef system fill:#f3e5f5,stroke:#4a148c,stroke-width:2px;
    class Controller,State,Renderer,Grid component;
    class Terminal system;
```

This diagram shows the high-level architecture and relationships between components:

1. The Controller manages game flow
2. State handles immutable transitions
3. Grid provides pure grid operations
4. The Renderer visualizes the grid state
5. Terminal input is processed by the Controller

## Cell State Transitions

```mermaid
stateDiagram-v2
    [*] --> Dead
    Dead --> Alive: 3 live neighbors
    Alive --> Dead: less than 2 live neighbors
    Alive --> Dead: more than 3 live neighbors
    Alive --> Alive: 2-3 live neighbors

    %% Styling
    classDef dead fill:#ffebee,stroke:#b71c1c,stroke-width:2px;
    classDef alive fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px;
    class Dead dead;
    class Alive alive;
```

This diagram illustrates Conway's Game of Life rules as state transitions:

1. A dead cell becomes alive when it has exactly 3 live neighbors (reproduction)
2. A live cell dies when it has fewer than 2 live neighbors (underpopulation)
3. A live cell dies when it has more than 3 live neighbors (overpopulation)
4. A live cell stays alive when it has 2 or 3 live neighbors (survival)
