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
- When live cells approach boundaries, grid expands
- Maintains original grid center position
- Preserves pattern evolution as if on infinite plane

## INFINITE Mode Behavior

### Grid Expansion

When live cells reach grid boundaries, the grid expands:

1. Expansion occurs when live cells are within 1 cell of any edge
2. Grid grows by adding cells in the direction of expansion
3. Original grid center remains fixed
4. All existing cell states are preserved

### Visual Examples

Below are examples showing grid expansion in INFINITE mode:

```
Initial state (x = live cell, . = dead cell):
┌───────┐
│...x...│ 
│...x...│ <- Live cells moving
│...x...│    toward edge
└───────┘

After expansion (grid grows downward):
┌───────┐
│...x...│ 
│...x...│
│...x...│
│.......│ <- New row added
└───────┘
```

Pattern reaching corner:
```
Before:          After:
┌─────┐         ┌───────┐
│..x..│         │..x....│
│...x.│   ->    │...x...|
│....x│         │....x..│
└─────┘         │.......│
                └───────┘
```

### Implementation Constraints

1. Grid expansion:
   - Minimum expansion: 1 row/column
   - Maximum expansion: 10% of current grid size
   - Expansion occurs before next generation calculation

2. Performance considerations:
   - Grid should not expand beyond available memory
   - Expansion operations should be optimized
   - Consider using sparse matrix for large grids

3. Viewport behavior:
   - Viewport should remain fixed during expansion
   - Maintain pattern visibility during expansion
