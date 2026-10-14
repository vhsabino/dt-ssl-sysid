"""Shared helpers for the paper analyses (``dtssl.analysis.*``).

Everything that used to be copy-pasted across ``scripts/*.py`` (SBR/LARS 2026)
lives here: the run context (repository root, output directory, timestamp),
the hold-out rollout helper, parameter variants, the result-file header, the
rSim rollout cache, the legacy CSV/parquet reader plus resampler used by the
identification-side analyses, and one FOPDT simulator with an explicit
alignment switch.

FOPDT alignment (``simulate_fopdt``)
------------------------------------
Four legacy scripts (``loo_translational``, ``r3_closedloop_omega_fit``,
``fig_omega_stepresponse_en``, ``fig_fit_holdout_vxvy``) carried their own
first-order-plus-dead-time recurrence. Two conventions exist and they are NOT
numerically identical:

``align="legacy"`` (default; reproduces the published tables)::

    m     = ceil(Td/dt)                  # integer delay, no epsilon
    ud[k] = u[k-m]  (0 for k < m)
    v[k]  = v[k-1] + a*(ud[k] - v[k-1]),   a = 1 - exp(-dt/tau),  v[-1] = ic
    y[k]  = K*v[k]                          k = 0 .. N-1

i.e. the delayed command at the SAME index ``k`` drives ``v[k]``. Because the
ZOH-exact update integrates the input held over ``[(k-1)dt, k dt)``, the
effective transport delay is ``(m-1)*dt`` — one sample LESS than
``AnalyticFOPDTPlant``.

``align="plant"`` (``dtssl.models.AnalyticFOPDTPlant`` / ``deadreckoning_p1d.m``)::

    m     = ceil(Td/dt - 1e-9)           # = j - floor(j - Td/dt + 1e-9)
    ud[k] = u[k-m]  (0 for k < m)
    v[0]  = ic
    v[k]  = v[k-1] + a*(ud[k-1] - v[k-1])
    y[k]  = K*v[k]

i.e. the command applied at step ``k-1`` produces the velocity at ``k``
(``free_run``: ``pose_sim[h] = step(cmd[h-1])``), effective delay ``m*dt``.
For ``m >= 1`` the two agree exactly when ``m_legacy = m_plant + 1``; with
``Td = 0`` the legacy form is non-causal by one sample and has no plant
equivalent. ``upsample > 1`` runs the same recurrence on a fine grid
``dt/upsample`` with the command held (ZOH) and decimates the output — this is
what ``fig_fit_holdout_vxvy`` does (fractional delay, ``align="plant"``,
``upsample=20``). See ``docs/refactor_notes/analysis.md``.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import numpy as np
import pandas as pd

from dtssl import __version__ as _DTSSL_VERSION
from dtssl.data.loader import DATASET_DEFAULT, event_dir, load_segment
from dtssl.data.schema import Segment
from dtssl.data.splits import load_holdout_segments
from dtssl.eval.metrics import ErrorTable, build_error_table, load_metrics_config
from dtssl.models import DOFS, AnalyticFOPDTPlant, DofParam, load_twin_params
from dtssl.paths import repo_root
from dtssl.sim.rollout import (DEFAULT_HMAX, DEFAULT_HORIZONS, DEFAULT_STRIDE, WindowRollout,
                               load_rollouts, rollout_segment, save_rollouts)

LW = 15                       # warm-up / lookback (mode A of the twin-vs-rSim gate)
SUB_MS = 1                    # rSim engine substep (ms), mode A
MIN_DISPLACEMENT_M = 0.1      # hold-out idle filter (all paper analyses)
STAMP_FMT = "%Y%m%d_%H%M"     # results/<name>_<stamp>.md
STAMP_FMT_S = "%Y%m%d_%H%M%S"
RSIM_CACHE_STEM = "_cache_rsim_rollouts"
THETA_ORDER = ("K_vx", "tau_vx", "Td_vx", "K_vy", "tau_vy", "Td_vy", "K_w", "tau_w", "Td_w")


# =========================================================================
# run context
# =========================================================================
def stamp(fmt: str = STAMP_FMT) -> str:
    """Timestamp used in output file names (``YYYYmmdd_HHMM`` by default)."""
    return datetime.now().strftime(fmt)


def git_commit(root: Path | None = None) -> str:
    """``<short-hash>[-dirty]`` of the repository at ``root`` or ``no-commit``."""
    cwd = str(root or repo_root())
    try:
        h = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=cwd,
                                    text=True, stderr=subprocess.DEVNULL).strip()
        dirty = subprocess.call(["git", "diff", "--quiet"], cwd=cwd,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0
        return h + ("-dirty" if dirty else "")
    except Exception:  # git missing, not a repo, ...
        return "no-commit"


@dataclass
class Ctx:
    """Resolved locations of one analysis run (root, output dir, timestamp)."""
    root: Path
    out: Path
    stamp: str
    seed: int | None = None
    _cache: dict = field(default_factory=dict, repr=False)

    # --- locations -------------------------------------------------------
    @property
    def config_dir(self) -> Path:
        return self.root / "config"

    def config(self, name: str) -> Path:
        return self.config_dir / name

    @property
    def data_root(self) -> Path:
        env = os.environ.get("DTSSL_DATA")
        return Path(env).expanduser().resolve() if env else self.root / "data" / "extracted"

    @property
    def models_dir(self) -> Path:
        return self.root / "models"

    @property
    def results_dir(self) -> Path:
        """Canonical ``results/`` of the repository (inputs such as the rSim cache)."""
        return self.root / "results"

    @property
    def figs(self) -> Path:
        p = self.out / "figs"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def latex_figures(self) -> Path:
        return self.root / "latex" / "figures"

    # --- configuration ----------------------------------------------------
    @property
    def twin_json(self) -> dict:
        if "twin_json" not in self._cache:
            with open(self.config("twin_params.json"), "r", encoding="utf-8") as f:
                self._cache["twin_json"] = json.load(f)
        return self._cache["twin_json"]

    @property
    def params(self) -> dict[str, DofParam]:
        if "params" not in self._cache:
            self._cache["params"] = load_twin_params(self.config("twin_params.json"))
        return self._cache["params"]

    @property
    def ts(self) -> float:
        return float(self.twin_json.get("ts", 1.0 / 60.0))

    @property
    def mcfg(self) -> dict:
        if "mcfg" not in self._cache:
            self._cache["mcfg"] = load_metrics_config(self.config("metrics.json"))
        return self._cache["mcfg"]

    @property
    def horizons(self) -> list[int]:
        return list(self.mcfg["horizons"])

    @property
    def holdout_cfg(self) -> dict:
        if "holdout_cfg" not in self._cache:
            with open(self.config("holdout_events.json"), "r", encoding="utf-8") as f:
                self._cache["holdout_cfg"] = json.load(f)
        return self._cache["holdout_cfg"]

    @property
    def dataset(self) -> str:
        return str(self.holdout_cfg.get("dataset", DATASET_DEFAULT))

    @property
    def team(self) -> str:
        return str(self.holdout_cfg.get("team", "allies"))

    @property
    def geometry(self) -> dict:
        if "geometry" not in self._cache:
            with open(self.config("robot_geometry.json"), "r", encoding="utf-8") as f:
                self._cache["geometry"] = json.load(f)
        return self._cache["geometry"]

    @property
    def splits_dir(self) -> Path:
        return self.data_root / self.dataset / "splits"

    # --- data -------------------------------------------------------------
    def holdout(self, min_displacement_m: float = MIN_DISPLACEMENT_M, *, cache: bool = True
                ) -> tuple[list[Segment], list[dict]]:
        """Hold-out segments (moving only) — cached per context unless ``cache=False``."""
        key = ("holdout", min_displacement_m)
        if not cache or key not in self._cache:
            val = load_holdout_segments(
                min_displacement_m=min_displacement_m, data_root=self.data_root,
                config=self.config("holdout_events.json"))
            if not cache:
                return val
            self._cache[key] = val
        return self._cache[key]

    def segment(self, label: str, event: str, **kw) -> Segment:
        return load_segment(label, event, dataset=self.dataset, data_root=self.data_root,
                            team=kw.pop("team", self.team), **kw)

    # --- output -----------------------------------------------------------
    def out_path(self, name: str, ext: str = "md", stamped: bool = True) -> Path:
        self.out.mkdir(parents=True, exist_ok=True)
        return self.out / (f"{name}_{self.stamp}.{ext}" if stamped else f"{name}.{ext}")

    def write_text(self, name: str, lines: Sequence[str], ext: str = "md",
                   stamped: bool = True, trailing_newline: bool = False) -> Path:
        p = self.out_path(name, ext, stamped)
        text = "\n".join(lines) + ("\n" if trailing_newline else "")
        p.write_text(text, encoding="utf-8")
        return p


def make_context(root: Path | str | None = None, out: Path | str | None = None, *,
                 stamp_fmt: str = STAMP_FMT, seed: int | None = None) -> Ctx:
    """Build the run context.

    ``root`` defaults to ``dtssl.paths.repo_root()``. Passing it explicitly also
    exports ``DTSSL_ROOT`` so that library code that resolves config paths on its
    own (``dtssl.eval.metrics``, ``dtssl.models.params``) sees the same tree.
    ``out`` defaults to ``<root>/results`` (created on demand).
    """
    if root is not None:
        root = Path(root).expanduser().resolve()
        os.environ["DTSSL_ROOT"] = str(root)
    else:
        root = repo_root()
    out = Path(out).expanduser().resolve() if out is not None else root / "results"
    out.mkdir(parents=True, exist_ok=True)
    return Ctx(root=root, out=out, stamp=stamp(stamp_fmt), seed=seed)


# =========================================================================
# result-file header
# =========================================================================
def theta_summary(params: dict[str, DofParam]) -> str:
    return "; ".join(f"{d}: K={params[d].K:.4f} tau={params[d].tau:.4f} Td={params[d].Td:.4f}"
                     + (" (placeholder)" if params[d].placeholder else "") for d in DOFS)


def result_header(title: str, ctx: Ctx, *, generator: str, seed: int | None = None,
                  extra: str | None = None) -> list[str]:
    """Markdown header: ``# title - stamp`` + one provenance line (commit, theta,
    dataset, seed, generator, dtssl version)."""
    seed = ctx.seed if seed is None else seed
    prov = (f"_Proveniencia: commit `{git_commit(ctx.root)}` | theta `config/twin_params.json` "
            f"({theta_summary(ctx.params)}) | dataset `{ctx.dataset}` | "
            f"seed {seed if seed is not None else 'n/a'} | gerado por `{generator}` "
            f"(dtssl {_DTSSL_VERSION})" + (f" | {extra}" if extra else "") + "_")
    return [f"# {title} - {ctx.stamp}", "", prov, ""]


# =========================================================================
# rollouts / parameters
# =========================================================================
def ros(segs: Iterable[Segment], factory: Callable[[], Any], *, h_max: int = DEFAULT_HMAX,
        stride: int = DEFAULT_STRIDE, lookback: int = LW,
        horizons: Sequence[int] = DEFAULT_HORIZONS) -> list[WindowRollout]:
    """One free-run rollout per segment with a FRESH plant from ``factory``
    (mode A of the gate: lookback ``LW``, stride 15, H_max 90)."""
    return [rollout_segment(s, factory(), h_max=h_max, stride=stride, lookback=lookback,
                            horizons=list(horizons)) for s in segs]


def variant_params(base: dict[str, DofParam], use_K: bool, use_tau: bool, use_Td: bool
                   ) -> dict[str, DofParam]:
    """Ablation variant: switch each parameter group on (identified value) or off
    (K=1, tau=0, Td=0). Replaces the old duck-typed ``DP`` class."""
    return {d: DofParam(K=base[d].K if use_K else 1.0, tau=base[d].tau if use_tau else 0.0,
                        Td=base[d].Td if use_Td else 0.0, placeholder=False) for d in DOFS}


def theta_from_vector(v: Sequence[float]) -> dict[str, DofParam]:
    """9-vector in the official order -> {vx, vy, w}."""
    v = [float(x) for x in v]
    if len(v) != 9:
        raise ValueError(f"theta must have 9 entries, got {len(v)}")
    return {d: DofParam(K=v[3 * i], tau=v[3 * i + 1], Td=v[3 * i + 2]) for i, d in enumerate(DOFS)}


def load_theta_mat(path: Path | str, key: str = "theta_opt") -> dict[str, DofParam]:
    """Read a 9-vector theta from a MATLAB ``.mat`` (v7.3/HDF5 via h5py, else scipy.io)."""
    path = Path(path)
    with open(path, "rb") as f:
        head = f.read(128)
    if b"MATLAB 7.3" in head:
        try:
            import h5py
        except ImportError as e:  # pragma: no cover
            raise ImportError(f"{path.name} is a v7.3 MAT-file: pip install h5py") from e
        with h5py.File(path, "r") as f:
            v = np.array(f[key]).squeeze()
    else:
        from scipy.io import loadmat
        v = np.asarray(loadmat(path)[key]).squeeze()
    return theta_from_vector(v)


def trans_mask(table: ErrorTable) -> np.ndarray:
    return np.asarray(table.bin) == "trans"


def per_event_medians(table: ErrorTable, k: int, mask: np.ndarray | None = None
                      ) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """Per-event medians of ``epos_twin`` / ``epos_def`` at horizon index ``k``
    over the rows in ``mask`` (default: translation bin). Events sorted by id."""
    m = trans_mask(table) if mask is None else mask
    sid = np.asarray(table.seg_id)[m]
    a = table.epos_twin[m, k]
    b = table.epos_def[m, k]
    ids = sorted(set(int(s) for s in sid))
    ev_a = np.array([np.median(a[sid == s]) for s in ids])
    ev_b = np.array([np.median(b[sid == s]) for s in ids])
    return ev_a, ev_b, ids


def paired_table(ctx: Ctx, twin_ros: list[WindowRollout], def_ros: list[WindowRollout]
                 ) -> ErrorTable:
    return build_error_table(twin_ros, def_ros, params=ctx.params, mcfg=ctx.mcfg)


def bootstrap_median_ci(d: np.ndarray, n_boot: int = 10000, seed: int = 42,
                        rng: np.random.Generator | None = None) -> tuple[float, float]:
    """Percentile 95% CI of the median by naive bootstrap (legacy scripts used
    ``default_rng(42)``, 10000 draws)."""
    rng = rng or np.random.default_rng(seed)
    bs = np.array([np.median(d[rng.integers(0, len(d), len(d))]) for _ in range(n_boot)])
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


# =========================================================================
# rSim rollout cache (results/_cache_rsim_rollouts.{npz,pkl})
# =========================================================================
def save_rsim_cache_npz(rollouts: Sequence[WindowRollout], path: Path | str) -> Path:
    """Serialise hold-out rollouts as ``.npz`` (thin wrapper over
    ``dtssl.sim.rollout.save_rollouts``; also writes the ``.json`` meta sidecar)."""
    return save_rollouts(Path(path), list(rollouts))


def load_rsim_cache_npz(path: Path | str) -> list[WindowRollout]:
    """Read an ``.npz`` rollout cache (``dtssl.sim.rollout.load_rollouts``)."""
    return list(load_rollouts(Path(path)))


def _rsim_cache_candidates(ctx: Ctx) -> list[Path]:
    dirs = [ctx.out, ctx.results_dir]
    return ([d / f"{RSIM_CACHE_STEM}.npz" for d in dirs]
            + [d / f"{RSIM_CACHE_STEM}.pkl" for d in dirs])


def rsim_cache_path(ctx: Ctx) -> Path | None:
    for p in _rsim_cache_candidates(ctx):
        if p.is_file():
            return p
    return None


def load_rsim_cache(ctx: Ctx, n_expected: int | None = None) -> list[WindowRollout]:
    """Persisted rSim (ODE) rollouts of the hold-out, one WindowRollout per segment
    in hold-out order. Reads ``_cache_rsim_rollouts.npz`` if present (``out`` then
    ``results/``), otherwise the legacy pickle (class paths ``phase0_replay.rollout``
    are remapped by ``dtssl.sim.rollout._LegacyUnpickler``; convert it once with
    ``dtssl cache-convert``)."""
    p = rsim_cache_path(ctx)
    if p is None:
        raise FileNotFoundError(
            f"rSim rollout cache not found ({RSIM_CACHE_STEM}.npz/.pkl in {ctx.out} or "
            f"{ctx.results_dir}); run `dtssl analysis run eval_rsim_delay_ablation --kw mode=cache` "
            "(requires robosim)")
    if p.suffix == ".npz":
        ros_ = load_rsim_cache_npz(p)
    else:
        from dtssl.sim.rollout import _LegacyUnpickler
        with open(p, "rb") as f:
            d = _LegacyUnpickler.load(f)
        ros_ = [d[str(i)] for i in range(len(d))] if isinstance(d, dict) else list(d)
    if n_expected is not None and len(ros_) < n_expected:
        raise RuntimeError(f"rSim cache incomplete: {len(ros_)}/{n_expected} segments ({p})")
    return ros_


# =========================================================================
# legacy CSV/parquet reader + resampler (identification-side analyses)
# =========================================================================
def read_event_csv(label: str, event: str, *, dataset: str = DATASET_DEFAULT,
                   data_root: Path | None = None, prefer: str = "csv"
                   ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """``(commands, processed_robots)`` of one event with the ABSOLUTE ``timestamp``
    column, as the legacy scripts read them from ``commands.csv`` /
    ``processed_robots.csv``.

    The CSV is read when present; otherwise the parquet twin of the same table
    (same columns, ``timestamp`` included) is used — both were written from the
    same DataFrame by the split builder, and the published numbers are
    reproduced from the parquet (verified, see docs/refactor_notes/analysis.md).
    """
    d = event_dir(label, event, dataset, data_root)

    def _read(name: str) -> pd.DataFrame:
        csv, pq = d / f"{name}.csv", d / f"{name}.parquet"
        order = (csv, pq) if prefer == "csv" else (pq, csv)
        for p in order:
            if p.is_file():
                return pd.read_csv(p) if p.suffix == ".csv" else pd.read_parquet(p)
        raise FileNotFoundError(f"{name}.csv/.parquet not found in {d}")

    return _read("commands"), _read("processed_robots")


def list_events(splits_dir: Path, label: str) -> list[str]:
    d = splits_dir / label
    if not d.is_dir():
        return []
    return sorted(p.name for p in d.iterdir() if p.is_dir())


_CMD_COL = {"vx": "move_x", "vy": "move_y", "w": "move_w"}


def legacy_uy_series(cmd: pd.DataFrame, rob: pd.DataFrame, dof: str, dt: float, *,
                     min_len: int = 60, pos_scale: float = 1.0, sg_win: int = 7,
                     sg_order: int = 2, tcol: str = "timestamp"
                     ) -> tuple[np.ndarray, np.ndarray] | None:
    """(u, y) on a uniform grid ``np.arange(0, T, dt)`` exactly as the legacy
    identification-side scripts built them:

    * ``t0`` = first command timestamp; ``T`` = min(last command, last vision) - t0;
    * ``u`` = LINEAR interpolation of ``move_*`` (NOT the ZOH of the loader);
    * ``y`` = body velocity from the vision pose: theta unwrapped then linearly
      interpolated; for ``w``: ``gradient(savgol(theta))/dt``; for ``vx``/``vy``:
      ``gradient(savgol(x|y))/dt`` rotated world->body (``pos_scale`` converts the
      logged mm — 1/1000 for m, 1.0 keeps mm/s as ``excitation_per_dof`` did).

    Returns ``None`` when the grid is shorter than ``min_len`` samples.
    """
    from scipy.signal import savgol_filter

    t0 = float(cmd[tcol].iloc[0])
    t_end = min(float(cmd[tcol].iloc[-1]), float(rob[tcol].iloc[-1])) - t0
    tg = np.arange(0.0, t_end, dt)
    if len(tg) < min_len:
        return None
    u = np.interp(tg, cmd[tcol].to_numpy(float) - t0, cmd[_CMD_COL[dof]].to_numpy(float))
    tr = rob[tcol].to_numpy(float) - t0
    thg = np.interp(tg, tr, np.unwrap(rob["position_w"].to_numpy(float)))
    n = len(thg)
    win = sg_win if n > sg_win else (n // 2 * 2 - 1)
    if dof == "w":
        y = np.gradient(savgol_filter(thg, win, sg_order)) / dt
    else:
        xg = np.interp(tg, tr, rob["position_x"].to_numpy(float) * pos_scale)
        yg = np.interp(tg, tr, rob["position_y"].to_numpy(float) * pos_scale)
        vx = np.gradient(savgol_filter(xg, win, sg_order)) / dt
        vy = np.gradient(savgol_filter(yg, win, sg_order)) / dt
        cs, sn = np.cos(thg), np.sin(thg)
        y = (cs * vx + sn * vy) if dof == "vx" else (-sn * vx + cs * vy)
    return u, y


def fit_percent(y: np.ndarray, yhat: np.ndarray) -> float:
    """NRMSE fit in % (MATLAB ``compare``): ``100*(1 - ||y-yhat|| / ||y-mean(y)||)``."""
    return float(100.0 * (1.0 - np.linalg.norm(y - yhat) / np.linalg.norm(y - np.mean(y))))


# =========================================================================
# FOPDT simulator (see module docstring)
# =========================================================================
def _delay_samples(Td: float, dt: float, align: str) -> int:
    if Td <= 0.0:
        return 0
    if align == "legacy":
        return int(math.ceil(Td / dt))
    return int(math.ceil(Td / dt - 1e-9))          # plant: j - floor(j - Td/dt + 1e-9)


def _lag(ud: np.ndarray, a: float | None, ic: float, align: str) -> np.ndarray:
    """First-order ZOH-exact lag with coefficient ``a`` (``None`` = instantaneous)."""
    from scipy.signal import lfilter
    n = ud.size
    v = np.empty(n)
    if align == "legacy":
        if a is None:
            return ud.astype(float, copy=True)
        v[:], _ = lfilter([a], [1.0, -(1.0 - a)], ud, zi=[(1.0 - a) * ic])
        return v
    v[0] = ic
    if n > 1:
        if a is None:
            v[1:] = ud[:-1]
        else:
            v[1:], _ = lfilter([a], [1.0, -(1.0 - a)], ud[:-1], zi=[(1.0 - a) * ic])
    return v


def simulate_fopdt(u: np.ndarray, dt: float, K: float, tau: float, Td: float, *,
                   ic: float = 0.0, align: str = "legacy", upsample: int = 1) -> np.ndarray:
    """Single-DOF FOPDT response ``y = K * lag(delay(u))`` on the grid of ``u``.

    ``ic`` is the initial lag state in pre-gain units (``y(0) = K*ic`` for
    ``align="plant"``; ``v[-1] = ic`` for ``align="legacy"``). ``align`` selects
    the convention documented in the module docstring; ``upsample`` runs the
    recurrence on ``dt/upsample`` with the command held and decimates back.
    """
    if align not in ("legacy", "plant"):
        raise ValueError("align must be 'legacy' or 'plant'")
    if upsample < 1:
        raise ValueError("upsample must be >= 1")
    u = np.asarray(u, dtype=float).reshape(-1)
    n = u.size
    if n == 0:
        return np.empty(0)
    dtf = dt / upsample
    if upsample > 1:
        nf = (n - 1) * upsample + 1
        uf = u[np.minimum(np.arange(nf) // upsample, n - 1)]
    else:
        uf = u
    m = _delay_samples(Td, dtf, align)
    ud = np.zeros(uf.size)
    if m < uf.size:
        ud[m:] = uf[:uf.size - m]
    a = None if tau <= 0.0 else 1.0 - math.exp(-dtf / tau)
    v = _lag(ud, a, ic, align)
    y = K * v
    return y[::upsample] if upsample > 1 else y


def simulate_fopdt_plant(u: np.ndarray, dt: float, K: float, tau: float, Td: float, *,
                         ic: float = 0.0) -> np.ndarray:
    """Reference for ``align="plant"``: drives ``AnalyticFOPDTPlant`` step by step
    (the command is put on the vx channel; heading is kept at zero so the body
    velocity equals the world x velocity). Slow; used in tests."""
    u = np.asarray(u, dtype=float).reshape(-1)
    p = DofParam(K=float(K), tau=float(tau), Td=float(Td))
    plant = AnalyticFOPDTPlant({"vx": p, "vy": p, "w": p})
    plant.reset((0.0, 0.0, 0.0), (K * ic, 0.0, 0.0))
    y = np.empty(u.size)
    if u.size:
        y[0] = K * ic
    for k in range(1, u.size):
        plant.step((u[k - 1], 0.0, 0.0), dt)
        y[k] = plant.body_velocity[0]
    return y


# =========================================================================
# misc
# =========================================================================
def copy_figure(src: Path, ctx: Ctx, name: str, enabled: bool) -> Path | None:
    """Copy a paper-candidate figure into ``latex/figures/<name>`` when enabled."""
    if not enabled:
        return None
    import shutil
    dst = ctx.latex_figures / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return dst


def parse_kv(items: Sequence[str] | None) -> dict[str, Any]:
    """``["k=v", ...]`` -> dict with JSON-decoded values (fallback: string)."""
    out: dict[str, Any] = {}
    for it in items or ():
        if "=" not in it:
            raise ValueError(f"expected key=value, got {it!r}")
        k, v = it.split("=", 1)
        try:
            out[k.strip()] = json.loads(v)
        except json.JSONDecodeError:
            out[k.strip()] = v
    return out


def cli_main(run: Callable[..., Any], description: str, argv: Sequence[str] | None = None,
             extra: Callable[[Any], None] | None = None) -> Any:
    """Minimal argparse wrapper shared by every analysis ``main(argv)``:
    ``--root DIR --out DIR --kw k=v ...`` (+ module-specific options via ``extra``)."""
    import argparse
    ap = argparse.ArgumentParser(description=description)
    ap.add_argument("--root", default=None, help="repository root (default: auto)")
    ap.add_argument("--out", default=None, help="output directory (default: <root>/results)")
    ap.add_argument("--kw", nargs="*", default=[], metavar="k=v",
                    help="extra keyword arguments passed to run() (JSON-decoded)")
    if extra is not None:
        extra(ap)
    a = ap.parse_args(argv)
    kw = parse_kv(a.kw)
    for k, v in vars(a).items():
        if k not in ("root", "out", "kw") and v is not None:
            kw.setdefault(k, v)
    return run(root=a.root, out=a.out, **kw)
