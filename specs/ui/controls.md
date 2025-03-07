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
- Max simulation speed: 10 generations/second.
- Min simulation speed: 0.5 generations/second.
- Simulation speed increased in steps inverse proportional to speed.
- Interval value should be rounded to nearest 10 ms.
- Pattern selection can be done repetedly.
- Pattern mode can be exited with 'P' or ESC.
