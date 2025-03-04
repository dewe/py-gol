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
    
    Main->>Controller: parse_arguments()
    Controller->>Terminal: initialize_terminal()
    Terminal-->>Controller: return terminal, renderer_state
    Controller->>Grid: create_grid(config)
    Grid-->>Controller: return initial_grid
    Controller->>State: initialize_game()
    State-->>Controller: return game_state
```

## 2. Game Loop and Pattern Management

```mermaid
sequenceDiagram
    participant Main
    participant Controller
    participant Grid
    participant Patterns
    participant Renderer
    
    Main->>Controller: run_game_loop()
    loop Game Loop
        Controller->>Grid: process_generation()
        Grid-->>Controller: return new_grid
        alt pattern_mode
            Controller->>Patterns: get_centered_position()
            Patterns-->>Controller: return position
            Controller->>Patterns: place_pattern()
            Patterns-->>Controller: return updated_grid
        end
        Controller->>Renderer: render_grid()
        Renderer->>Renderer: update_display()
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
    
    Controller->>Patterns: load_pattern()
    Patterns->>Storage: read_pattern_file()
    Storage-->>Patterns: return pattern_data
    Patterns->>Grid: place_pattern()
    Grid-->>Controller: return updated_grid
```

## 4. Renderer Update Sequence

```mermaid
sequenceDiagram
    participant Controller
    participant Renderer
    participant Grid
    participant Terminal
    
    Controller->>Renderer: render_grid()
    Renderer->>Grid: grid_to_dict()
    Grid-->>Renderer: return cell_states
    alt pattern_mode
        Renderer->>Renderer: render_pattern_preview()
    end
    Renderer->>Terminal: update_display()
    Renderer->>Terminal: render_status_line()
```

## Key Architectural Features

The sequence diagrams highlight several important architectural features:

1. **Pure Functions**: All state transitions and pattern operations are pure functions
2. **Immutable State**: Grid and pattern states are immutable
3. **Pattern Management**: Centralized pattern system with metadata
4. **Type Safety**: Strong typing with Protocol classes
5. **Boundary Handling**: Support for multiple boundary conditions
6. **Efficient Updates**: Differential rendering for changed cells only

The implementation follows functional programming principles with:

- Immutable data structures
- Pure functions for state transitions
- Type-safe operations through protocols
- Pattern-based abstractions

## Component Architecture

```mermaid
graph TD
    Controller -->|Manages| Grid
    Controller -->|Uses| Patterns
    Controller -->|Updates| Renderer
    Patterns -->|Modifies| Grid
    Grid -->|Displays| Renderer
    Terminal -->|Input| Controller
    Storage -->|Loads/Saves| Patterns

    %% Styling
    classDef component fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef system fill:#f3e5f5,stroke:#4a148c,stroke-width:2px;
    class Controller,Grid,Patterns,Renderer component;
    class Terminal,Storage system;
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
