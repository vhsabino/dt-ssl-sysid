"""Statistical helpers of the evaluation harness (pure numerics, no config access).

- ``rank_biserial``: paired effect size for the Wilcoxon signed-rank test (direction
  ``default - twin``: positive = twin better).
- ``wilcoxon_less``: one-sided paired Wilcoxon p-value of ``twin < default``.
- moving-block bootstrap (``block_pool`` / ``resample_blocks`` / ``moving_block_bootstrap``)
  over the dense (overlapping) window set, with an EXPLICIT ``rng`` argument.
- ``percentile_ci`` and ``bootstrap_rng`` (deterministic per-(scope, curve) generators).

The numerics are those of the 2026-08 ``phase0_replay.metrics`` implementation; only the
random-stream bookkeeping changed (see ``dtssl.eval.verdict.evaluate``).
"""
from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np
from scipy.stats import rankdata, wilcoxon

__all__ = [
    "rank_biserial", "wilcoxon_less", "block_pool", "resample_blocks",
    "moving_block_bootstrap", "percentile_ci", "bootstrap_rng",
]


# =========================================================================
# Effect size / paired test
def rank_biserial(default: np.ndarray, twin: np.ndarray) -> float:
    """Rank-biserial correlation of the paired differences ``default - twin`` (ties dropped).

    +1: twin better on every pair; -1: default better on every pair; 0: no effect.
    """
    d = np.asarray(default, dtype=float) - np.asarray(twin, dtype=float)
    d = d[d != 0]
    if d.size == 0:
        return 0.0
    r = rankdata(np.abs(d))
    rp = r[d > 0].sum(); rm = r[d < 0].sum()
    tot = rp + rm
    return float((rp - rm) / tot) if tot > 0 else 0.0


def wilcoxon_less(twin: np.ndarray, default: np.ndarray) -> float:
    """One-sided paired Wilcoxon p-value for ``twin < default``; robust to all-ties (-> 1.0)."""
    twin = np.asarray(twin, dtype=float); default = np.asarray(default, dtype=float)
    if np.allclose(twin, default):
        return 1.0
    try:
        return float(wilcoxon(twin, default, alternative="less", zero_method="wilcox").pvalue)
    except ValueError:
        return 1.0


# =========================================================================
# Moving-block bootstrap over the dense window set (blocks never cross segments)
def block_pool(rows: np.ndarray, seg_id: np.ndarray, L: int) -> list[np.ndarray]:
    """All contiguous blocks of ``L`` rows within each segment (a short segment is one block)."""
    pool: list[np.ndarray] = []
    for s in np.unique(seg_id[rows]):
        idx = rows[seg_id[rows] == s]                  # rows of this segment (dense order)
        ws = idx.size
        if ws <= L:
            pool.append(idx)
        else:
            for start in range(0, ws - L + 1):
                pool.append(idx[start:start + L])
    return pool


def resample_blocks(pool: Sequence[np.ndarray], W: int, rng: np.random.Generator) -> np.ndarray:
    """Concatenate random blocks (with replacement) until ``W`` rows are drawn (truncated to W)."""
    chosen, total = [], 0
    while total < W:
        b = pool[rng.integers(len(pool))]
        chosen.append(b); total += b.size
    return np.concatenate(chosen)[:W]


def moving_block_bootstrap(rows: np.ndarray, seg_id: np.ndarray, L: int, W: int, n_boot: int,
                           rng: np.random.Generator, fn: Callable[[np.ndarray], np.ndarray]) -> np.ndarray:
    """``n_boot`` replicates of ``fn(resampled_rows)`` (moving-block bootstrap). Shape (n_boot, ...)."""
    pool = block_pool(rows, seg_id, L)
    return np.array([fn(resample_blocks(pool, W, rng)) for _ in range(n_boot)])


def percentile_ci(dist: np.ndarray, ci: float) -> np.ndarray:
    """Percentile CI of a bootstrap distribution along axis 0 -> (n, 2) [lo, hi]."""
    lo = (1 - ci) / 2 * 100
    return np.percentile(dist, [lo, 100 - lo], axis=0).T


def bootstrap_rng(seed: int, *key: int) -> np.random.Generator:
    """Deterministic generator for one (scope, curve) combination.

    ``bootstrap_rng(seed)`` reproduces ``np.random.default_rng(seed)``; with a key the stream is
    derived through ``SeedSequence(seed, spawn_key=key)`` so every curve gets an independent,
    reproducible stream regardless of evaluation order.
    """
    if not key:
        return np.random.default_rng(int(seed))
    return np.random.default_rng(np.random.SeedSequence(int(seed), spawn_key=tuple(int(k) for k in key)))
