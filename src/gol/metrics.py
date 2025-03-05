"""Game of Life metrics functionality."""

import time
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class GameMetrics:
    """Game state metrics."""

    generation_count: int = 0
    total_cells: int = 0
    active_cells: int = 0
    births_this_second: int = 0
    deaths_this_second: int = 0
    birth_rate: float = 0.0
    death_rate: float = 0.0


@dataclass(frozen=True)
class PerformanceMetrics:
    """Performance metrics."""

    frames_this_second: int = 0
    actual_fps: float = 0.0
    last_fps_update: float = 0.0
    last_stats_update: float = 0.0


@dataclass(frozen=True)
class Metrics:
    """Combined game and performance metrics."""

    game: GameMetrics = GameMetrics()
    perf: PerformanceMetrics = PerformanceMetrics()


def create_metrics() -> Metrics:
    """Create initial metrics instance."""
    return Metrics()


def update_game_metrics(
    metrics: Metrics,
    total_cells: int,
    active_cells: int,
    births: int,
    deaths: int,
) -> Metrics:
    """Update game metrics with new values.

    Args:
        metrics: Current metrics instance
        total_cells: Total number of cells in grid
        active_cells: Number of active cells
        births: Number of births in this update
        deaths: Number of deaths in this update

    Returns:
        New metrics instance with updated values
    """
    now = time.time()
    game = metrics.game

    # Accumulate births and deaths within the current second
    births_this_second = game.births_this_second + births
    deaths_this_second = game.deaths_this_second + deaths

    # Check if a second has passed
    if now - metrics.perf.last_stats_update >= 1.0:
        # Calculate rates and reset counters
        birth_rate = float(game.births_this_second)
        death_rate = float(game.deaths_this_second)
        births_this_second = births
        deaths_this_second = deaths
        perf = replace(metrics.perf, last_stats_update=now)
    else:
        birth_rate = game.birth_rate
        death_rate = game.death_rate
        perf = metrics.perf

    # Create new game metrics
    game = replace(
        game,
        generation_count=game.generation_count + 1,
        total_cells=total_cells,
        active_cells=active_cells,
        births_this_second=births_this_second,
        deaths_this_second=deaths_this_second,
        birth_rate=birth_rate,
        death_rate=death_rate,
    )

    return replace(metrics, game=game, perf=perf)


def update_frame_metrics(metrics: Metrics) -> Metrics:
    """Update frame rate metrics.

    Args:
        metrics: Current metrics instance

    Returns:
        New metrics instance with updated frame rate
    """
    now = time.time()
    perf = metrics.perf

    # Increment frame counter
    frames_this_second = perf.frames_this_second + 1

    # Check if a second has passed
    if now - perf.last_fps_update >= 1.0:
        # Calculate FPS and reset counter
        actual_fps = float(perf.frames_this_second)
        frames_this_second = 1  # Count current frame
        perf = replace(perf, last_fps_update=now)
    else:
        actual_fps = perf.actual_fps

    # Update frame metrics
    perf = replace(
        perf,
        frames_this_second=frames_this_second,
        actual_fps=actual_fps,
    )

    return replace(metrics, perf=perf)
