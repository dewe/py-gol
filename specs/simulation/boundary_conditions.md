# Boundary Conditions

This document specifies the behavior of different boundary conditions in the Game of Life implementation.

## Types

### FINITE

- Grid edges act as fixed boundaries
- Cells outside the grid are considered permanently dead
- No wrapping of cells around edges
- Edge cells have fewer neighbors than interior cells

### TOROIDAL

- Grid edges wrap around to opposite edges
- Creates a surface topology of a torus
- All cells have exactly 8 neighbors
- Patterns can move seamlessly across boundaries

### INFINITE

- Grid simulates an infinite plane
- Grid expands ONLY when live cells are directly adjacent to boundaries
- Maintains original grid center position
- Preserves pattern evolution as if on infinite plane

## INFINITE Mode Behavior

### Grid Expansion Rules

The grid MUST expand if and ONLY if:

- A live cell exists in the outermost row or column of the grid
- No expansion occurs for any other condition

Examples of when expansion MUST occur:

- Live cell in the last row triggers downward expansion
- Live cell in the first row triggers upward expansion
- Live cell in the last column triggers rightward expansion
- Live cell in the first column triggers leftward expansion

Examples of when expansion MUST NOT occur:

- Live cells exist near (but not adjacent to) boundaries
- Only dead cells exist at boundaries

### Game Loop Timing

Grid expansion in INFINITE mode MUST occur at these specific points:

1. BEFORE calculating the next generation
2. AFTER user input processing
3. ONLY ONCE per game loop iteration

The sequence in the game loop MUST be:

```
1. Process user input
2. Check boundary conditions
3. If INFINITE mode and live cells at boundary:
   - Perform grid expansion
4. Calculate next generation
5. Update display
```

### Visual Examples

Below are examples showing grid expansion in INFINITE mode:

```text
Example 1: Expansion REQUIRED (x = live cell, . = dead cell)
┌───────┐
│...x...│ 
│...x...│
│...x...│ <- Live cell at boundary
└───────┘

Example 2: Expansion NOT REQUIRED
┌───────┐
│...x...│ 
│...x...│ <- Live cells not at boundary
│.......│    No expansion needed
└───────┘
```

Pattern at corner - Expansion REQUIRED:
```
Before:          After:
┌─────┐         ┌───────┐
│..x..│         │..x....│
│...x.│   ->    │...x...|
│....x│         │....x..│ <- Expansion required
└─────┘         │.......│    due to corner cell
                └───────┘
```

### Implementation Constraints

1. Grid expansion:
   - MUST ONLY occur when live cells are at grid boundaries
   - MUST occur before next generation calculation
   - MUST NOT occur multiple times in same game loop
   - Expansion: 1 row/column

2. Performance considerations:
   - Grid should not expand beyond available memory
   - Expansion operations should be optimized
   - Consider using sparse matrix for large grids

3. Viewport behavior:
   - Viewport should remain fixed during expansion
