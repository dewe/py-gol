"""Tests for Game of Life metrics functionality."""

import time

import pytest

from gol.metrics import (
    Metrics,
    create_metrics,
    update_frame_metrics,
    update_game_metrics,
)


@pytest.fixture
def metrics() -> Metrics:
    """Create a fresh metrics instance for each test."""
    return create_metrics()


def test_create_metrics() -> None:
    """Test metrics creation with default values."""
    metrics = create_metrics()

    # Game metrics should start at zero
    assert metrics.game.generation_count == 0
    assert metrics.game.total_cells == 0
    assert metrics.game.active_cells == 0
    assert metrics.game.births_this_second == 0
    assert metrics.game.deaths_this_second == 0
    assert metrics.game.birth_rate == 0.0
    assert metrics.game.death_rate == 0.0

    # Performance metrics should start at zero
    assert metrics.perf.frames_this_second == 0
    assert metrics.perf.actual_fps == 0.0


def test_update_game_metrics_accumulation(metrics: Metrics) -> None:
    """Test that game metrics accumulate correctly within a second."""
    # First update
    metrics = update_game_metrics(
        metrics,
        total_cells=100,
        active_cells=30,
        births=10,
        deaths=5,
    )

    assert metrics.game.total_cells == 100
    assert metrics.game.active_cells == 30
    assert metrics.game.births_this_second == 10
    assert metrics.game.deaths_this_second == 5

    # Second update within the same second
    metrics = update_game_metrics(
        metrics,
        total_cells=100,
        active_cells=35,
        births=2,
        deaths=1,
    )

    assert metrics.game.total_cells == 100
    assert metrics.game.active_cells == 35
    assert metrics.game.births_this_second == 12  # Accumulated
    assert metrics.game.deaths_this_second == 6  # Accumulated


def test_update_game_metrics_rates(metrics: Metrics) -> None:
    """Test that birth and death rates are calculated correctly after one second."""
    # Initial update
    metrics = update_game_metrics(
        metrics,
        total_cells=100,
        active_cells=30,
        births=10,
        deaths=5,
    )

    # Force time to advance by modifying last_stats_update
    from dataclasses import replace

    metrics = replace(
        metrics,
        perf=replace(metrics.perf, last_stats_update=time.time() - 1.1),
    )

    # Update after one second
    metrics = update_game_metrics(
        metrics,
        total_cells=100,
        active_cells=35,
        births=2,
        deaths=1,
    )

    # Rates should be calculated from accumulated values
    assert metrics.game.birth_rate == pytest.approx(10, rel=0.1)  # ~10 births/second
    assert metrics.game.death_rate == pytest.approx(5, rel=0.1)  # ~5 deaths/second
    # Counters should be reset
    assert metrics.game.births_this_second == 2
    assert metrics.game.deaths_this_second == 1


def test_update_frame_metrics(metrics: Metrics) -> None:
    """Test frame rate calculation and accumulation."""
    # Accumulate frames
    for _ in range(30):
        metrics = update_frame_metrics(metrics)

    assert metrics.perf.frames_this_second == 30
    assert metrics.perf.actual_fps == 0.0  # Not updated until 1 second passes

    # Force time to advance
    from dataclasses import replace

    metrics = replace(
        metrics,
        perf=replace(metrics.perf, last_fps_update=time.time() - 1.1),
    )

    # Update after one second
    metrics = update_frame_metrics(metrics)

    # FPS should be calculated and counter reset
    assert metrics.perf.actual_fps == pytest.approx(30, rel=0.1)
    assert metrics.perf.frames_this_second == 1  # Reset and counted current frame
