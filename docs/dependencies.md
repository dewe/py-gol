<!-- markdownlint-disable MD033 -->

# Module Dependencies

This document shows the dependencies between different modules in the Game of Life implementation.

## Core Module Dependencies

```mermaid
graph TD
    %% Core modules
    grid[gol.grid]
    life[gol.life]
    controller[gol.controller]
    main[gol.main]
    renderer[gol.renderer]
    patterns[gol.patterns]
    types[gol.types]
    state[gol.state]
    metrics[gol.metrics]

    %% Core dependencies
    types --> blessed[blessed]
    types --> scipy[scipy]
    grid --> types
    life --> grid
    controller --> grid
    controller --> life
    controller --> renderer
    controller --> state
    patterns --> grid
    patterns --> types
    renderer --> types
    renderer --> patterns
    renderer --> blessed
    renderer --> scipy
    main --> controller
    main --> patterns
    main --> blessed
    metrics --> types
    state --> types
    state --> grid

    %% Styling
    classDef core fill:#f9f,stroke:#333,stroke-width:2px;
    classDef external fill:#dfd,stroke:#333,stroke-width:1px;
    
    class grid,life,controller,main,renderer,patterns,types,state,metrics core;
    class scipy,blessed external;
```

## Module Responsibilities

### Core Modules

- **gol.types**: Type definitions and aliases
  - Defines core type system using SciPy arrays and Blessed types
  - Provides type aliases for grid operations and pattern transformations
  - Ensures consistent typing across modules

- **gol.grid**: Core grid operations and boundary conditions
  - Implements grid operations using SciPy arrays
  - Handles boundary conditions and neighbor calculations
  - Provides efficient array-based operations

- **gol.life**: Game of Life rules implementation
  - Applies game rules using vectorized operations
  - Depends on grid operations for state transitions
  - Optimized for SciPy array operations

- **gol.controller**: Game state management
  - Coordinates between components
  - Manages game state and configuration
  - Handles game loop and state transitions

- **gol.renderer**: Terminal display and user input
  - Implements efficient grid rendering using Blessed
  - Handles pattern preview and placement
  - Manages terminal display and user interaction
  - Uses type-safe pattern transformations

- **gol.patterns**: Pattern management and manipulation
  - Manages pattern storage and loading
  - Implements pattern transformations
  - Provides pattern placement operations
  - Uses SciPy arrays for pattern storage

- **gol.state**: Game state management
  - Manages game state transitions
  - Handles state validation
  - Provides immutable state operations

- **gol.metrics**: Performance monitoring
  - Tracks performance metrics
  - Provides timing information
  - Monitors resource usage

- **gol.main**: Application entry point and game loop
  - Initializes game components
  - Manages main game loop
  - Handles configuration and startup
  - Provides CLI interface using Blessed

## Key Dependencies

1. **Type System**
   - `gol.types` provides SciPy and Blessed type definitions
   - Ensures type safety across all modules
   - Defines specialized types for patterns and transformations

2. **Grid Operations**
   - `gol.grid` implements efficient SciPy array operations
   - Provides optimized neighbor calculations
   - Handles boundary conditions using array operations

3. **Game Logic**
   - `gol.life` uses vectorized operations for rule application
   - Optimized for performance with SciPy arrays
   - Maintains pure functional approach

4. **State Management**
   - `gol.state` provides immutable state operations
   - `gol.controller` coordinates component interactions
   - Manages game state transitions
   - Handles configuration and user input

5. **User Interface**
   - `gol.renderer` provides efficient terminal display using Blessed
   - Implements type-safe pattern transformations
   - Uses optimized SciPy operations for updates

6. **Pattern Management**
   - `gol.patterns` handles pattern operations
   - Uses SciPy arrays for pattern storage
   - Provides type-safe pattern transformations

7. **Performance Monitoring**
   - `gol.metrics` tracks performance metrics
   - Monitors resource usage
   - Provides timing information

## External Dependencies

- **SciPy**: Core numerical operations
  - Used for efficient array operations
  - Provides optimized grid manipulations
  - Enables vectorized calculations

- **Blessed**: Terminal handling
  - Manages terminal display
  - Handles user input
  - Provides terminal formatting
   