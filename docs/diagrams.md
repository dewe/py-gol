# Component Interaction Diagrams

This document illustrates the key interactions between components in the Game of Life implementation using sequence diagrams.

## 1. Game Initialization Sequence

This diagram shows how the game components are initialized, including terminal setup, grid creation, and actor initialization.

```mermaid
sequenceDiagram
    participant Main
    participant Controller
    participant Terminal
    participant Grid
    participant CellActor
    
    Main->>Controller: parse_arguments()
    Controller->>Terminal: initialize_terminal()
    Terminal-->>Controller: return terminal, renderer_state
    Controller->>Grid: create_grid(config)
    Grid-->>Controller: return initial_grid
    loop For each cell in grid
        Controller->>CellActor: create_cell_actor(position, state)
        Controller->>CellActor: subscribe_to_neighbors()
    end
    Controller-->>Main: return terminal, actors
```

## 2. Game Loop and Cell Interaction Sequence

This diagram illustrates the main game loop, showing how cell processing, rendering, and user input are handled.

```mermaid
sequenceDiagram
    participant Main
    participant Controller
    participant CellActor
    participant Renderer
    participant Terminal
    
    Main->>Controller: run_game_loop()
    loop Game Loop
        Controller->>CellActor: process_generation()
        par Cell Processing
            CellActor->>CellActor: process_messages()
            CellActor->>CellActor: calculate_next_state()
            CellActor->>CellActor: broadcast_state()
        end
        Controller->>Renderer: safe_render_grid()
        Renderer->>Terminal: update display
        Terminal->>Controller: handle_user_input()
        alt quit command
            Controller->>Main: break loop
        else restart command
            Controller->>Grid: create_grid()
            Controller->>CellActor: setup_cell_actors()
        end
    end
```

## 3. Cell Actor Communication Sequence

This diagram shows how individual cell actors communicate state changes through message queues.

```mermaid
sequenceDiagram
    participant CellA as Cell Actor A
    participant Queue as Message Queue
    participant CellB as Cell Actor B
    participant Event as Completion Event
    
    CellA->>Queue: broadcast_state(new_state)
    Queue->>CellB: queue.put(state_message)
    Note over CellB: Wait for completion event
    Event->>CellB: process_messages()
    CellB->>CellB: calculate_next_state()
    alt state changed
        CellB->>Queue: broadcast_state(new_state)
    end
```

## 4. Renderer Update Sequence

This diagram shows how the game state is visualized in the terminal with differential updates.

```mermaid
sequenceDiagram
    participant Controller
    participant Renderer
    participant Terminal
    participant Grid
    
    Controller->>Renderer: safe_render_grid()
    Renderer->>Grid: get current state
    Grid-->>Renderer: return grid state
    alt state changed
        Renderer->>Terminal: move_xy()
        Renderer->>Terminal: update cell display
    end
    Renderer->>Terminal: refresh display
```

## Key Architectural Features

The sequence diagrams highlight several important architectural features of the implementation:

1. **Actor-Based Concurrency**: Each cell operates independently and communicates through message passing
2. **Event-Driven Updates**: State changes are propagated through events and message queues
3. **Differential Rendering**: Only changed cells are updated in the display for better performance
4. **Component Separation**: Clear boundaries between different system components
5. **Thread-Safe Communication**: All inter-actor communication happens through thread-safe message queues
6. **Synchronization**: Completion events ensure proper coordination between components

The implementation follows functional programming principles with:

- Immutable state transitions
- Pure functions for state calculations
- Thread-safe communication patterns
- No shared mutable state

This architecture makes the system robust and well-suited for concurrent execution while maintaining clear separation of concerns. 

# Architecture Diagrams

<!-- Actor Communication Flow -->
## Actor Communication Flow

```mermaid
graph LR
    A[Cell Actor] -->|State Update| B[Neighbors]
    B -->|Live Count| A
    A -->|Grid State| C[Renderer]
    D[Controller] -->|Generation Tick| A
    D -->|Refresh Rate| C

    %% Styling
    classDef component fill:#f9f,stroke:#333,stroke-width:2px;
    class A,B,C,D component;
```

This diagram illustrates how cell actors communicate with each other and other components:

1. Each cell actor broadcasts its state to neighboring cells
2. Neighbors respond with their live/dead status
3. The renderer receives grid state updates for display
4. The controller orchestrates generation updates and refresh rates

<!-- Component Architecture -->
## Component Architecture

```mermaid
graph TD
    Controller -->|Manages| Grid
    Controller -->|Orchestrates| Renderer
    Grid -->|Contains| CellActors
    CellActors -->|Update| MessageQueues
    MessageQueues -->|Notify| CellActors
    Renderer -->|Displays| Grid
    Terminal -->|Input| Controller

    %% Styling
    classDef component fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef system fill:#f3e5f5,stroke:#4a148c,stroke-width:2px;
    class Controller,Grid,Renderer,CellActors component;
    class MessageQueues,Terminal system;
```

This diagram shows the high-level architecture and relationships between components:

1. The Controller is the central orchestrator
2. Grid manages the game state through Cell Actors
3. Cell Actors communicate via thread-safe Message Queues
4. The Renderer visualizes the grid state
5. Terminal input is processed by the Controller

<!-- Cell State Transitions -->
## Cell State Transitions

```mermaid
stateDiagram-v2
    [*] --> Dead
    Dead --> Alive: 3 live neighbors
    Alive --> Dead: <2 live neighbors
    Alive --> Dead: >3 live neighbors
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
