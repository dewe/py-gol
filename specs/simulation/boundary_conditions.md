# Boundary Conditions

This document specifies the behavior of different boundary conditions in the Game
of Life implementation. Boundary conditions describe what happens at grid edges
during simulation. It is strictly about the life simulation and not tied to
viewports or pattern management.

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

## INFINITE Mode Implementation

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

### Grid Expansion Behavior

When grid expansion occurs:

- New rows/columns MUST be initialized as dead cells
- Original grid content MUST be preserved in its new position
- No live cells are copied to expanded rows/columns
- This ensures consistent pattern evolution at boundaries

### Grid Shrinking Behavior

- Grid MUST NOT shrink during game loop
- Once expanded, grid dimensions remain fixed
- Empty regions at boundaries are preserved
- This ensures stable viewport behavior and pattern evolution

### Game Loop Timing

Grid expansion in INFINITE mode MUST occur at these specific points:

1. BEFORE calculating the next generation
2. AFTER user input processing
3. ONLY ONCE per game loop iteration

The sequence in the game loop MUST be:

1. Process user input
2. Check boundary conditions
3. If INFINITE mode and live cells at boundary:
   - Perform grid expansion
4. Calculate next generation
5. Update display

### Implementation Constraints

1. Grid expansion:
   - MUST ONLY occur when live cells are at grid boundaries
   - MUST occur before next generation calculation
   - MUST NOT occur multiple times in same game loop
   - Expansion: 1 row/column
   - MUST NOT occur in pattern mode
   - MUST initialize new rows/columns as dead cells
   - MUST preserve original grid content in its new position

2. Performance considerations:
   - Grid should not expand beyond available memory
   - Expansion operations should be optimized
   - Consider using sparse matrix for large grids

3. Viewport behavior:
   - Viewport size should not change during expansion
   - Viewport position in terminal should not change during expansion
   - Same grid cells should be visible in the viewport after expansion
   - Expansion happens outside of the viewport
   - Viewport offset MUST be adjusted:
     - When expanding left: increase offset_x by 1
     - When expanding up: increase offset_y by 1
     - When expanding right/down: no offset adjustment needed
   - This ensures viewport remains stationary in terminal while grid expands

### Visual Examples

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

Pattern at corner - Expansion REQUIRED:
Before:          After:
┌─────┐         ┌───────┐
│..x..│         │..x....│
│...x.│   ->    │...x...|
│....x│         │....x..│ <- Expansion required
└─────┘         │.......│    due to corner cell
                └───────┘

Viewport behavior during expansion:
Before:         Next generation:
Grid:           Grid:
┌───────┐       ┌───────┐
│..xxx..│       │...x...│
│.......│       │...x...│
│.......│       │.......│
└───────┘       │.......│
                └───────┘
       
Viewport:       Viewport:
┌───────┐       ┌───────┐
│..xxx..│       │...x...│
│.......│       │...x...│
│.......│       │.......│
└───────┘       └───────┘
Offset(0,0)      Offset(0,1)
```
