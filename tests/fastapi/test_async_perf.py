"""A/B performance comparison: HttpPipeline (sync) vs AsyncHttpPipeline (concurrent).

Simulates I/O-bound steps (e.g. DB lookups, HTTP calls) using sleep. The key
comparison is:

  - HttpPipeline      — sync, steps block the thread; pipelines run one at a time
  - AsyncHttpPipeline — async, multiple pipelines can overlap with asyncio.gather

For CPU-bound work the two are equivalent; the win is purely I/O concurrency.
"""

import asyncio
import time

import pytest

from mayhaps.fastapi import AsyncHttpPipeline, HttpPipeline, Ok

# Tune these to keep the suite fast while keeping the ratio meaningful.
STEP_LATENCY_S = 0.005   # 5 ms simulated I/O per step
N_PIPELINES = 20
N_STEPS = 3

# Expected wall time ceilings (generous to avoid flakiness on slow CI).
# Sequential: N_PIPELINES × N_STEPS × STEP_LATENCY_S
SEQUENTIAL_UPPER_S = N_PIPELINES * N_STEPS * STEP_LATENCY_S * 3.0
# Concurrent: roughly N_STEPS × STEP_LATENCY_S (all pipelines overlap)
CONCURRENT_UPPER_S = N_STEPS * STEP_LATENCY_S * 4.0


# ---------------------------------------------------------------------------
# Step factories
# ---------------------------------------------------------------------------

def sync_step(x: int) -> Ok[int]:
    """Sync step that blocks for STEP_LATENCY_S to simulate I/O."""
    time.sleep(STEP_LATENCY_S)
    return Ok(x + 1)


async def async_step(x: int) -> Ok[int]:
    """Async step that yields for STEP_LATENCY_S to simulate I/O."""
    await asyncio.sleep(STEP_LATENCY_S)
    return Ok(x + 1)


def build_sync_pipeline(seed: int) -> HttpPipeline[int]:
    p = HttpPipeline(seed)
    for _ in range(N_STEPS):
        p = p.then(sync_step)
    return p


def build_async_pipeline(seed: int) -> AsyncHttpPipeline[int]:
    p = AsyncHttpPipeline(seed)
    for _ in range(N_STEPS):
        p = p.then(async_step)
    return p


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------

def test_sync_sequential_baseline() -> None:
    """HttpPipeline — N_PIPELINES run one after the other (sync, blocking)."""
    start = time.perf_counter()

    results = [build_sync_pipeline(i).run() for i in range(N_PIPELINES)]

    elapsed = time.perf_counter() - start
    expected_value = N_STEPS  # each pipeline starts at i and increments N_STEPS times...
    # actually each starts at i, so result is i + N_STEPS
    assert results == [i + N_STEPS for i in range(N_PIPELINES)]

    print(f"\n[sync  sequential] {N_PIPELINES}× {N_STEPS}-step pipelines: {elapsed * 1000:.1f} ms")
    assert elapsed < SEQUENTIAL_UPPER_S, (
        f"sync sequential took {elapsed:.3f}s, ceiling is {SEQUENTIAL_UPPER_S:.3f}s"
    )


def test_async_sequential_for_comparison() -> None:
    """AsyncHttpPipeline — same N_PIPELINES but run sequentially (no concurrency).

    Should be similar to the sync baseline; demonstrates that async alone does
    not speed things up — concurrency does.
    """
    async def run_all() -> list[int]:
        return [await build_async_pipeline(i).run() for i in range(N_PIPELINES)]

    start = time.perf_counter()
    results = asyncio.run(run_all())
    elapsed = time.perf_counter() - start

    assert results == [i + N_STEPS for i in range(N_PIPELINES)]
    print(f"\n[async sequential] {N_PIPELINES}× {N_STEPS}-step pipelines: {elapsed * 1000:.1f} ms")
    assert elapsed < SEQUENTIAL_UPPER_S, (
        f"async sequential took {elapsed:.3f}s, ceiling is {SEQUENTIAL_UPPER_S:.3f}s"
    )


def test_async_concurrent_speedup() -> None:
    """AsyncHttpPipeline — N_PIPELINES run concurrently via asyncio.gather.

    Wall time should be close to a *single* pipeline's cost (all pipelines overlap).
    """
    async def run_all() -> list[int]:
        pipelines = [build_async_pipeline(i) for i in range(N_PIPELINES)]
        return list(await asyncio.gather(*[p.run() for p in pipelines]))

    start = time.perf_counter()
    results = asyncio.run(run_all())
    elapsed = time.perf_counter() - start

    assert results == [i + N_STEPS for i in range(N_PIPELINES)]
    print(f"\n[async concurrent] {N_PIPELINES}× {N_STEPS}-step pipelines: {elapsed * 1000:.1f} ms")
    assert elapsed < CONCURRENT_UPPER_S, (
        f"async concurrent took {elapsed:.3f}s, ceiling is {CONCURRENT_UPPER_S:.3f}s"
    )


def test_concurrent_faster_than_sequential() -> None:
    """Asserts that concurrent async is meaningfully faster than sequential sync.

    With pure I/O-bound steps the speedup should approach N_PIPELINES×; we only
    require ≥ 3× to stay well clear of measurement noise.
    """
    # sync sequential
    start = time.perf_counter()
    [build_sync_pipeline(i).run() for i in range(N_PIPELINES)]
    sync_elapsed = time.perf_counter() - start

    # async concurrent
    async def run_concurrent() -> None:
        pipelines = [build_async_pipeline(i) for i in range(N_PIPELINES)]
        await asyncio.gather(*[p.run() for p in pipelines])

    start = time.perf_counter()
    asyncio.run(run_concurrent())
    async_elapsed = time.perf_counter() - start

    speedup = sync_elapsed / async_elapsed
    print(
        f"\n[a/b comparison] sync={sync_elapsed * 1000:.1f} ms  "
        f"async={async_elapsed * 1000:.1f} ms  "
        f"speedup={speedup:.1f}×"
    )
    assert speedup >= 3.0, (
        f"Expected concurrent async to be ≥3× faster than sync sequential, "
        f"got {speedup:.2f}× (sync={sync_elapsed:.3f}s, async={async_elapsed:.3f}s)"
    )
