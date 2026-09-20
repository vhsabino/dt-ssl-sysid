"""SE(2) multi-horizon error tables and movement stratification.

CONSUMES ``WindowRollout`` objects (pose_sim/pose_real already aligned) — it never recomputes
dynamics. Per window ``w`` and horizon ``h`` (samples):

    e_pos(w,h) = ||(x_sim[h]-x_real[h], y_sim[h]-y_real[h])||_2          [m]
    e_ang(w,h) = |wrap_to_pi(theta_sim[h]-theta_real[h])|                [rad]
    e_se2(w,h) = sqrt(e_pos^2 + (rho*e_ang)^2)   (rho = robot_radius; OPTIONAL)

Independence: CURVES use ALL windows (dense, stride 15); INFERENCE uses only
non-overlapping windows (stride >= H_max) for the paired Wilcoxon test, plus a moving-block
bootstrap (block ~H_max) over the dense set for the CI of the gap (``dtssl.eval.stats``).
Verdict gates live in ``dtssl.eval.verdict``; figures/markdown in ``dtssl.eval.report``.

This module keeps re-exporting the whole harness API for backwards compatibility::

    from dtssl.eval.metrics import evaluate, make_figures, markdown_report, rank_biserial
"""
from __future__ import annotations

import importlib
import math
import warnings
from dataclasses import dataclass

import numpy as np

from dtssl.config import load_json, load_metrics_config  # noqa: F401  (re-export)
from dtssl.eval.stats import (  # noqa: F401  (re-exports, incl. legacy private names)
    bootstrap_rng, moving_block_bootstrap, percentile_ci, rank_biserial, wilcoxon_less,
)

BIN_ORDER = ("trans", "misto", "rot")
BIN_LABEL = {"trans": "trans-dominado", "misto": "misto", "rot": "rot-dominado"}

# legacy private aliases (dtssl.analysis.* and old scripts import these)
_wilcoxon_less = wilcoxon_less
_mbb = moving_block_bootstrap
_ci = percentile_ci

__all__ = [
    "BIN_ORDER", "BIN_LABEL", "ErrorTable", "build_error_table", "classify_bin",
    "bin_distribution", "format_bin_distribution", "load_metrics_config", "pose_errors",
    "rank_biserial", "wilcoxon_less", "moving_block_bootstrap", "percentile_ci", "bootstrap_rng",
    # provided lazily from verdict/report (see __getattr__)
    "evaluate", "verdict_bin", "make_figures", "markdown_report",  # noqa: F822
]

_LAZY = {
    "evaluate": "dtssl.eval.verdict", "verdict_bin": "dtssl.eval.verdict",
    "_verdict_bin": "dtssl.eval.verdict",
    "make_figures": "dtssl.eval.report", "markdown_report": "dtssl.eval.report",
}


def __getattr__(name: str):
    """Lazy re-exports of ``evaluate``/``verdict_bin``/``make_figures``/``markdown_report``.

    They live in ``dtssl.eval.verdict`` / ``dtssl.eval.report`` (which import this module), so
    a lazy hook avoids a circular import while keeping the historical import path working.
    """
    mod = _LAZY.get(name)
    if mod is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(mod), name)


# =========================================================================
def classify_bin(razao: float, bins_cfg: dict) -> str:
    """``trans`` if ratio < trans_max, ``rot`` if ratio > rot_min, else ``misto``."""
    if razao < bins_cfg["trans_max"]:
        return "trans"
    if razao > bins_cfg["rot_min"]:
        return "rot"
    return "misto"


# =========================================================================
@dataclass
class ErrorTable:
    horizons: np.ndarray         # (nh,) samples
    ts: float
    robot_radius: float
    seg_id: np.ndarray           # (W,)
    seg_name: list               # (W,)
    t0: np.ndarray               # (W,)
    bin: np.ndarray              # (W,) str
    razao: np.ndarray            # (W,)
    indep: np.ndarray            # (W,) bool (non-overlapping)
    epos_twin: np.ndarray        # (W, nh)
    eang_twin: np.ndarray        # (W, nh)
    epos_def: np.ndarray         # (W, nh)
    eang_def: np.ndarray         # (W, nh)
    ese2_twin: np.ndarray        # (W, nh) or None
    ese2_def: np.ndarray         # (W, nh) or None
    block_windows: int           # MBB block size (in windows)

    @property
    def W(self) -> int:
        return self.t0.size

    def mask(self, scope: str) -> np.ndarray:
        return np.ones(self.W, bool) if scope == "all" else (self.bin == scope)


def pose_errors(pose_sim: np.ndarray, pose_real: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-sample ``(e_pos, e_ang)`` between two (N, 3) pose arrays (angle error wrapped)."""
    ps = np.asarray(pose_sim, dtype=float); pr = np.asarray(pose_real, dtype=float)
    epos = np.hypot(ps[:, 0] - pr[:, 0], ps[:, 1] - pr[:, 1])
    dth = ps[:, 2] - pr[:, 2]
    eang = np.abs(np.arctan2(np.sin(dth), np.cos(dth)))   # vectorised wrap_to_pi
    return epos, eang


def _window_errors(win, horizons):
    ps, pr = win.pose_sim, win.pose_real            # (H+1,3)
    dx = ps[horizons, 0] - pr[horizons, 0]
    dy = ps[horizons, 1] - pr[horizons, 1]
    epos = np.hypot(dx, dy)
    dth = ps[horizons, 2] - pr[horizons, 2]
    eang = np.abs(np.arctan2(np.sin(dth), np.cos(dth)))   # vectorised wrap_to_pi
    return epos, eang


def _window_activity(win, robot_radius, ts):
    tr = np.hypot(win.cmd[:, 0], win.cmd[:, 1])      # translational command
    rot = np.abs(win.cmd[:, 2]) * robot_radius       # rad/s -> m/s at the contact radius
    ativ_trans = float(tr.sum() * ts)
    ativ_rot = float(rot.sum() * ts)
    denom = ativ_rot + ativ_trans
    razao = ativ_rot / denom if denom > 1e-12 else 0.0
    return ativ_trans, ativ_rot, razao


def _get_robot_radius() -> float:
    """``robot_radius`` of config/twin_params.json (= R_contact_m of the CAD geometry)."""
    cfg = load_json(None, "twin_params.json")
    return float(cfg.get("robot_radius", 0.0796))


def _pair_windows(rt, rd, si: int) -> list[tuple]:
    """Pair the windows of two rollouts of the same segment by ``t0`` (dense order kept)."""
    t0_t = [w.t0 for w in rt.windows]
    t0_d = [w.t0 for w in rd.windows]
    if t0_t == t0_d:
        return list(zip(rt.windows, rd.windows))
    by_t0 = {w.t0: w for w in rd.windows}
    pairs = [(w, by_t0[w.t0]) for w in rt.windows if w.t0 in by_t0]
    name = rt.meta.get("event")
    if not pairs:
        raise ValueError(
            f"segment {si} ({name}): twin windows t0={t0_t[:3]}... and default windows "
            f"t0={t0_d[:3]}... have no t0 in common — roll both plants on the same grid "
            "(same stride/t0_anchor in rollout_segment)")
    dropped = len(t0_t) + len(t0_d) - 2 * len(pairs)
    warnings.warn(f"segment {si} ({name}): windows paired by t0, {dropped} unmatched window(s) "
                  f"dropped ({len(t0_t)} twin, {len(t0_d)} default, {len(pairs)} paired)",
                  RuntimeWarning, stacklevel=3)
    return pairs


def build_error_table(twin_rollouts, default_rollouts, *, params=None, mcfg=None,
                      robot_radius: float | None = None) -> ErrorTable:
    """Paired error table (twin vs default) over the SAME t0 (same windows).

    ``twin_rollouts``/``default_rollouts``: lists of ``WindowRollout`` (one per segment),
    paired by position; inside a segment the windows are paired by ``t0``. Both plants are
    normally rolled on the same window grid (``rollout_segment`` anchors it on the official
    theta); if one side lacks some windows (larger dead time -> first window inadmissible)
    only the common ``t0`` are kept (a ``RuntimeWarning`` reports how many were dropped) and
    a ``ValueError`` is raised when a segment has no common window at all.
    ``params`` is accepted for API symmetry with ``evaluate`` (the table itself does not
    depend on theta); ``robot_radius`` defaults to ``twin_params.json: robot_radius``.
    Raises ``ValueError`` on empty input or lists of different length.
    """
    twin_rollouts = list(twin_rollouts); default_rollouts = list(default_rollouts)
    if not twin_rollouts or not default_rollouts:
        raise ValueError("build_error_table: no rollouts given (empty twin/default list)")
    if len(twin_rollouts) != len(default_rollouts):
        raise ValueError("build_error_table: twin and default lists have different lengths "
                         f"({len(twin_rollouts)} vs {len(default_rollouts)})")
    if sum(len(r.windows) for r in twin_rollouts) == 0:
        raise ValueError("build_error_table: the rollouts contain no windows "
                         "(segments shorter than h_max + idx_min?)")
    mcfg = mcfg or load_metrics_config()
    horizons = np.asarray(mcfg["horizons"], int)
    use_se2 = bool(mcfg.get("use_se2", False))
    robot_radius = float(_get_robot_radius() if robot_radius is None else robot_radius)

    seg_id, seg_name, t0s, bins, razoes, indep = [], [], [], [], [], []
    EPT, EAT, EPD, EAD = [], [], [], []
    block_windows = 1
    ts = None
    for si, (rt, rd) in enumerate(zip(twin_rollouts, default_rollouts)):
        if rt.meta["h_max"] != rd.meta["h_max"]:
            raise ValueError(f"h_max differs between twin and default in segment {si}")
        ts = rt.meta["ts"]
        stride = rt.meta["stride"]
        h_max = rt.meta["h_max"]
        step = max(1, math.ceil(h_max / stride))          # windows per ~H_max
        block_windows = max(block_windows, max(1, round(mcfg["bootstrap"]["block_samples"] / stride)))
        pairs = _pair_windows(rt, rd, si)
        for wi, (wt, wd) in enumerate(pairs):
            ept, eat = _window_errors(wt, horizons)
            epd, ead = _window_errors(wd, horizons)
            _, _, razao = _window_activity(wt, robot_radius, ts)
            seg_id.append(si); seg_name.append(rt.meta.get("event"))
            t0s.append(wt.t0); razoes.append(razao)
            bins.append(classify_bin(razao, mcfg["bins"]))
            indep.append(wi % step == 0)                  # non-overlapping within the segment
            EPT.append(ept); EAT.append(eat); EPD.append(epd); EAD.append(ead)

    epos_twin = np.array(EPT); eang_twin = np.array(EAT)
    epos_def = np.array(EPD); eang_def = np.array(EAD)
    ese2_twin = ese2_def = None
    if use_se2:
        ese2_twin = np.sqrt(epos_twin**2 + (robot_radius * eang_twin)**2)
        ese2_def = np.sqrt(epos_def**2 + (robot_radius * eang_def)**2)

    return ErrorTable(horizons=horizons, ts=ts, robot_radius=robot_radius,
                      seg_id=np.array(seg_id), seg_name=seg_name, t0=np.array(t0s),
                      bin=np.array(bins), razao=np.array(razoes), indep=np.array(indep, bool),
                      epos_twin=epos_twin, eang_twin=eang_twin, epos_def=epos_def,
                      eang_def=eang_def, ese2_twin=ese2_twin, ese2_def=ese2_def,
                      block_windows=block_windows)


# =========================================================================
# Stratification / distribution
def bin_distribution(table: ErrorTable) -> dict:
    out = {}
    for b in BIN_ORDER:
        m = table.bin == b
        out[b] = {"total": int(m.sum()), "indep": int((m & table.indep).sum())}
    out["all"] = {"total": table.W, "indep": int(table.indep.sum())}
    return out


def format_bin_distribution(table: ErrorTable) -> str:
    d = bin_distribution(table)
    lines = ["Distribuicao de bins (razao = ativ_rot/(ativ_rot+ativ_trans)):",
             f"  {'bin':14s} {'total':>7s} {'indep':>7s}"]
    for b in BIN_ORDER:
        lines.append(f"  {BIN_LABEL[b]:14s} {d[b]['total']:7d} {d[b]['indep']:7d}")
    lines.append(f"  {'TODOS':14s} {d['all']['total']:7d} {d['all']['indep']:7d}")
    return "\n".join(lines)
