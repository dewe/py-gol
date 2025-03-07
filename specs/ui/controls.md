# Game Controls

## Normal Mode

| Key         | Action                         |
|-------------|--------------------------------|
| Space       | Start/Stop simulation          |
| P           | Enter pattern mode             |
| C           | Clear grid                     |
| R           | Restart with new grid          |
| B           | Cycle boundary conditions      |
| +           | Resize grid larger             |
| -           | Resize grid smaller            |
| Arrow keys  | Pan viewport                   |
| Shift+Up    | Increase simulation speed      |
| Shift+Down  | Decrease simulation speed      |
| Q, Esc      | Quit game                      |

## Pattern Mode

| Key         | Action                         |
|-------------|--------------------------------|
| 1-9         | Select pattern                 |
| R           | Rotate pattern                 |
| Space       | Place pattern                  |
| Arrow keys  | Move cursor                    |
| P, Esc      | Exit pattern mode              |
| Q           | Quit game                      |

## Constraints

- No unspecified controls allowed.

## Simulation Constraints

- Max simulation speed: 10 generations/second.
- Min simulation speed: 0.5 generations/second.
- Simulation speed increased in steps inverse proportional to speed.
- Interval value should be rounded to nearest 10 ms.

## Grid Constraints

- Minimum grid size: 10x10 cells
- Maximum grid size: 200x200 cells
- Grid resize operations (+/-) maintain aspect ratio
- Viewport panning stops at grid boundaries
- Viewport size adapts to terminal dimensions

## Pattern Mode Constraints

- Pattern rotation occurs in 90-degree increments
- Patterns can be placed at grid boundaries
- Cursor movement is constrained to grid boundaries
- Pattern selection can be done repetedly.
- Pattern mode can be exited with 'P' or ESC.
- Pattern placement is allowed even if pattern extends beyond grid
- Cursor position is preserved when exiting/entering pattern mode
