"""C1 - in-silico identifiability: excitation regime x measurement noise x deadzone (known truth).

Thesis claim under test: *identifiability follows the excitation regime, not the DOF*.
The ground truth is the official theta (``config/twin_params.json``). Command sequences of
each regime are replayed through the twin itself (``AnalyticFOPDTPlant``, same driver as
``dtssl.sim.rollout.free_run`` with an empty delay buffer), the generated poses go through a
vision-like measurement chain (Gaussian noise on ``position_x/y`` [mm] and ``position_w``
[rad], heading wrapped to (-pi, pi]) and theta is re-identified per DOF with the paper's
Python chain: ``common.legacy_uy_series`` (linear command interpolation, Savitzky-Golay 7/2 +
central differences, world->body rotation) and the output-error cost of
``r3_closedloop_omega_fit`` on ``common.simulate_fopdt`` (legacy alignment, clamps
``tau >= 1e-4``, ``Td >= 0``).

Factors (full factorial per DOF, Monte Carlo over replicates):

* **A - regime**: ``R1`` competition closed-loop commands (vx: front_to_back, vy: side_to_side,
  w: shoot_to_goal - the paper's pairing); ``R2-rotate`` dedicated open-loop rotation (label
  ``rotate``, all 10 events, for every DOF); ``R2-square`` translational open-loop-like
  (label ``square``); ``R3`` designed excitation (12 synthetic events x 10 s, PRBS-like steps on
  the three DOFs simultaneously, design seed 42, identical in every replicate).
* **B - noise**: ``none`` / ``vision`` (2 mm, 0.01 rad) / ``heavy`` (5 mm, 0.03 rad), i.i.d.,
  common random numbers across levels (seed ``42 + rep``).
* **C - generator deadzone**: ``off`` / ``on`` (``dtssl.sim.twin_world.apply_body_deadzone`` with
  the firmware per-wheel threshold 1.567 rad/s applied to the command BEFORE the plant; the
  estimator always sees the original command).

Estimator search (pre-registered deviation from the 3-D Nelder-Mead of ``r3``): the cost is
piecewise constant in Td (integer delay ``m = ceil(Td/Ts)``) and the 3-D NM stalls on the wrong
plateau even without noise, so the fit is a Nelder-Mead on ``(K, tau)`` for every integer delay
``m in 0..12`` keeping the ``m`` of minimum training cost. Under the legacy alignment the
effective transport delay is ``m_eff = m - 1`` samples (one sample less than the plant, see
``common.py``), which is what the tables compare with ``Td*/Ts``.

Decision rule per cell (median/IQR over replicates): ``|bias_K| <= 10 %``, ``|bias_tau| <= 15 %``,
``|median(m_eff) - Td*/Ts| <= 1`` sample, ``IQR(K)/K* <= 20 %``; score = criteria met (0-4),
recovered = 4/4. Pre-registration: docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_20260907.md.

Artefacts: ``results/identifiability_insilico_<stamp>.md`` (+ ``.csv`` with every replicate,
``.json`` with the design and per-cell summaries).
"""
from __future__ import annotations

import json
import math
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from dtssl.analysis import common as C
from dtssl.models import DOFS, AnalyticFOPDTPlant, DofParam
from dtssl.sim.twin_world import DEADZONE_WHEEL_RAD_S, apply_body_deadzone, load_deadzone

NAME = "identifiability_insilico"
KIND = "analysis"
CLAIM = "C1: in-silico identifiability (known theta) follows the excitation regime, not the DOF"
REQUIRES = ("data",)

SEED = 42                      # noise seed = SEED + rep; split seed = SEED + SPLIT_OFFSET + rep
SPLIT_OFFSET = 1000
SEED_DESIGN = 42               # synthetic R3 command design (fixed across replicates)
N_REP = 20
R1_LABELS = {"vx": "front_to_back", "vy": "side_to_side", "w": "shoot_to_goal"}
REGIME_LABELS = {"R2-rotate": "rotate", "R2-square": "square"}
REGIMES: tuple[str, ...] = ("R1", "R2-rotate", "R2-square", "R3")
NOISES: dict[str, tuple[float, float]] = {"none": (0.0, 0.0), "vision": (2.0, 0.01), "heavy": (5.0, 0.03)}
DEADZONES: tuple[str, ...] = ("off", "on")
X0 = {"vx": (1.0, 0.08, 0.06), "vy": (1.0, 0.08, 0.06), "w": (1.3, 0.03, 0.10)}
NM_OPTIONS = dict(maxiter=400, xatol=1e-4, fatol=1e-3)
M_MAX = 12                     # integer delays searched: 0..M_MAX samples (0 .. 0.2 s)
R3_DESIGN = dict(n_events=12, duration_s=10.0, step_s=(0.3, 1.2), amp_trans=(0.6, 1.5), amp_rot=(1.5, 4.0))
RULE = dict(bias_K=0.10, bias_tau=0.15, dTd_samples=1.0, iqr_K=0.20)
MIN_LEN = 60
POS_SCALE = 1e-3               # logged mm -> m
DEGENERATE_STD = 1e-9          # training command std below this: no excitation of the DOF
REALISTIC = ("vision", "on")
IDEALIZED = ("none", "off")

# --- C1b: physical generators (docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_C1B_20260907.md) ---
GENERATORS: tuple[str, ...] = ("fopdt", "mujoco-velocity", "mujoco-rollers", "mujoco-rollers-delay")
TRUTH_KNOWN: tuple[str, ...] = ("fopdt", "mujoco-velocity")   # theta* is the generator's own truth
N_REP_MUJOCO = 12              # pre-registered replicate count for the MuJoCo generators
WONLY_SUFFIX = "@wonly"        # R1-wonly control: R1 command sequences with vx = vy = 0
REFERENCE_CELL = ("R3", "none", "off")                        # C1b-v1 reference (all DOFs)
REGIME_BIAS = dict(dev_K=0.10, dev_tau=0.15)                  # v1 composite flag: |dev K| OR |dev tau|
# --- C1b-v2 re-registration (docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_C1B_V2_20260907.md) ---
R3_MILD_DESIGN = dict(n_events=12, duration_s=10.0, step_s=(0.5, 1.5), amp_trans=(0.3, 1.0), amp_rot=(0.5, 2.0))
R3_DESIGNS = {"R3": R3_DESIGN, "R3-mild": R3_MILD_DESIGN}    # synthetic regimes (route b tracking envelope: mild)
REFERENCE_V2: dict[str, tuple[str, str, str]] = {"vx": ("R2-square", "none", "off"),
                                                 "vy": ("R2-square", "none", "off"),
                                                 "w": ("R2-rotate", "none", "off")}
VARIANTS = ("v1", "v2")                                       # v2: K-only rule, per-DOF references, stem suffix


# =========================================================================
# command events (one per regime), generator and measurement chain
# =========================================================================
@dataclass
class CmdEvent:
    """One command sequence on the uniform ``Ts`` grid (body frame, SI) plus the initial pose."""
    name: str
    t: np.ndarray            # (N,) absolute timestamps [s]
    cmd: np.ndarray          # (N, 3) commanded (vx, vy, w) as logged / designed
    pose0: tuple[float, float, float]

    @property
    def n(self) -> int:
        return int(self.t.size)


def _prbs_steps(rng: np.random.Generator, n: int, dt: float, amp: tuple[float, float],
                step_s: tuple[float, float]) -> np.ndarray:
    """Piecewise-constant steps: duration ~ U(step_s), magnitude ~ U(amp), sign +-1 equiprobable."""
    u = np.empty(n)
    k = 0
    while k < n:
        d = max(1, int(round(rng.uniform(*step_s) / dt)))
        a = rng.uniform(*amp) * (1.0 if rng.random() < 0.5 else -1.0)
        u[k:k + d] = a
        k += d
    return u


def synthetic_events(ts: float, design: dict | None = None, seed: int = SEED_DESIGN) -> list[CmdEvent]:
    """R3 - designed excitation: every event excites the three DOFs simultaneously with
    independent PRBS-like step sequences (fixed design seed, identical in all replicates)."""
    d = dict(R3_DESIGN, **(design or {}))
    rng = np.random.default_rng(seed)
    n = int(round(d["duration_s"] / ts))
    out = []
    for e in range(int(d["n_events"])):
        cmd = np.column_stack([_prbs_steps(rng, n, ts, d["amp_trans"], d["step_s"]),
                               _prbs_steps(rng, n, ts, d["amp_trans"], d["step_s"]),
                               _prbs_steps(rng, n, ts, d["amp_rot"], d["step_s"])])
        out.append(CmdEvent(name=f"R3_{e + 1:02d}", t=np.arange(n) * ts, cmd=cmd, pose0=(0.0, 0.0, 0.0)))
    return out


def dataset_events(ctx: C.Ctx, label: str) -> list[CmdEvent]:
    """Logged command sequences of one label on the loader's 60 Hz ZOH grid (``ctx.segment``)."""
    out = []
    for ev in C.list_events(ctx.splits_dir, label):
        s = ctx.segment(label, ev)
        cmd = np.column_stack([s.cmd_vx, s.cmd_vy, s.cmd_w]).astype(float)
        out.append(CmdEvent(name=ev, t=np.asarray(s.t, dtype=float), cmd=cmd, pose0=tuple(s.pose0)))
    return out


def regime_label(regime: str, dof: str) -> str:
    """Event-set key of ``(regime, dof)``: the dataset label for R1/R2, ``"R3"`` for the synthetic set,
    ``<label>@wonly`` for the R1-wonly control (R1 sequences with vx = vy = 0)."""
    if regime == "R1":
        return R1_LABELS[dof]
    if regime == "R1-wonly":
        return R1_LABELS[dof] + WONLY_SUFFIX
    if regime in REGIME_LABELS:
        return REGIME_LABELS[regime]
    if regime in R3_DESIGNS:
        return regime
    raise KeyError(f"unknown regime {regime!r}; known: {', '.join(REGIMES + ('R1-wonly', 'R3-mild'))}")


def wonly_events(events: Sequence[CmdEvent]) -> list[CmdEvent]:
    """R1-wonly control: the same command sequences with ``vx = vy = 0`` (w untouched)."""
    out = []
    for ev in events:
        cmd = np.array(ev.cmd, dtype=float, copy=True)
        cmd[:, :2] = 0.0
        out.append(CmdEvent(name=ev.name + WONLY_SUFFIX, t=ev.t, cmd=cmd, pose0=ev.pose0))
    return out


def cell_applies(regime: str, dof: str) -> bool:
    """The R1-wonly control is defined for the w DOF only (vx/vy would be degenerate by construction)."""
    return not (regime == "R1-wonly" and dof != "w")


def mask_deadzone(cmd: np.ndarray, threshold: float = DEADZONE_WHEEL_RAD_S
                  ) -> tuple[np.ndarray, np.ndarray]:
    """Apply the firmware per-wheel deadzone sample by sample (``apply_body_deadzone``).

    Returns ``(cmd_masked (N, 3), changed (N, 3) bool)`` where ``changed`` marks the components
    the deadzone altered (|delta| > 1e-12)."""
    cmd = np.asarray(cmd, dtype=float)
    out = np.empty_like(cmd)
    for k in range(cmd.shape[0]):
        out[k] = apply_body_deadzone(float(cmd[k, 0]), float(cmd[k, 1]), float(cmd[k, 2]), threshold)
    changed = np.abs(out - cmd) > 1e-12
    return out, changed


def simulate_poses_plant(plant, ev: CmdEvent, ts: float, cmd_plant: np.ndarray | None = None) -> np.ndarray:
    """Trajectory of any harness ``Plant``: ``pose[k] = step(cmd[k-1])``, ``pose[0] = pose0``,
    ``velb0 = 0``, empty delay buffer (the ``free_run`` driver with ``prev_cmds=None``).
    ``cmd_plant`` (default ``ev.cmd``) is what the plant receives."""
    cmd = ev.cmd if cmd_plant is None else np.asarray(cmd_plant, dtype=float)
    plant.reset(ev.pose0, (0.0, 0.0, 0.0))
    pose = np.empty((ev.n, 3))
    pose[0] = ev.pose0
    for k in range(1, ev.n):
        pose[k] = plant.step(cmd[k - 1], ts)
    return pose


def simulate_poses(params: dict[str, DofParam], ev: CmdEvent, ts: float,
                   cmd_plant: np.ndarray | None = None) -> np.ndarray:
    """Twin (``AnalyticFOPDTPlant``) trajectory, see :func:`simulate_poses_plant`."""
    return simulate_poses_plant(AnalyticFOPDTPlant(params), ev, ts, cmd_plant)


def make_generator(name: str, params: dict[str, DofParam], deadzone: bool, **world_opts):
    """Generator plant for ``name`` in ``GENERATORS``. MuJoCo generators come from
    ``dtssl.sim.world_plant.make_harness_plant`` (single-robot MuJoCoWorld seen as a harness Plant);
    their firmware deadzone is the world's own (``deadzone=True``: route a masks like
    ``apply_body_deadzone``, route b per wheel setpoint). ``fopdt`` returns the analytic plant (the
    deadzone is applied to its commands by the caller)."""
    if name not in GENERATORS:
        raise ValueError(f"unknown generator {name!r}; known: {', '.join(GENERATORS)}")
    if name == "fopdt":
        return AnalyticFOPDTPlant(params)
    from dtssl.sim.world_plant import make_harness_plant

    opts = dict(world_opts)
    opts["deadzone"] = bool(deadzone)
    return make_harness_plant(name, params, **opts)


def measurement_tables(ev: CmdEvent, pose: np.ndarray, sigma_pos_mm: float, sigma_theta: float,
                       z: np.ndarray | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """``(commands, processed_robots)`` in the contract of the logs: positions in mm with
    Gaussian noise ``sigma_pos_mm * z[:, :2]``, heading + ``sigma_theta * z[:, 2]`` wrapped to
    (-pi, pi]. ``z`` (N, 3) standard normal draws (``None`` = noise-free)."""
    cmd_df = pd.DataFrame(dict(timestamp=ev.t, move_x=ev.cmd[:, 0], move_y=ev.cmd[:, 1], move_w=ev.cmd[:, 2]))
    x_mm = pose[:, 0] / POS_SCALE
    y_mm = pose[:, 1] / POS_SCALE
    th = pose[:, 2].copy()
    if z is not None and (sigma_pos_mm > 0.0 or sigma_theta > 0.0):
        x_mm = x_mm + sigma_pos_mm * z[:, 0]
        y_mm = y_mm + sigma_pos_mm * z[:, 1]
        th = th + sigma_theta * z[:, 2]
    th_w = np.arctan2(np.sin(th), np.cos(th))          # vectorised ``dtssl.models.wrap_to_pi``
    rob_df = pd.DataFrame(dict(timestamp=ev.t, position_x=x_mm, position_y=y_mm, position_w=th_w))
    return cmd_df, rob_df


def uy_series(cmd_df: pd.DataFrame, rob_df: pd.DataFrame, dof: str, ts: float
              ) -> tuple[np.ndarray, np.ndarray] | None:
    """The paper's ``(u, y)`` extraction (``legacy_uy_series``, positions mm -> m)."""
    return C.legacy_uy_series(cmd_df, rob_df, dof, ts, min_len=MIN_LEN, pos_scale=POS_SCALE)


# =========================================================================
# estimator
# =========================================================================
def _sim(u: np.ndarray, dt: float, K: float, tau: float, Td: float, align: str) -> np.ndarray:
    # legacy clamps of r3_closedloop_omega_fit: tau >= 1e-4, Td >= 0
    return C.simulate_fopdt(u, dt, K, max(tau, 1e-4), max(Td, 0.0), align=align)


def _td_of_m(m: int, dt: float) -> float:
    """A Td strictly inside the plateau whose integer delay is ``m`` (``ceil(Td/dt) == m``)."""
    return 0.0 if m <= 0 else (m - 0.5) * dt


def effective_delay_samples(m: int, align: str) -> int:
    """Transport delay actually applied by ``simulate_fopdt`` for integer delay ``m``: the legacy
    alignment drives ``v[k]`` with ``u[k-m]`` (one sample less than the plant)."""
    return m - 1 if align == "legacy" else m


def plant_delay_samples(Td: float, dt: float) -> int:
    """Integer delay applied by ``AnalyticFOPDTPlant`` for a continuous ``Td``."""
    return 0 if Td <= 0.0 else int(math.ceil(Td / dt - 1e-9))


def fit_safe(y: np.ndarray, yhat: np.ndarray) -> float:
    """``common.fit_percent`` with a NaN guard for a constant ``y`` (zero response)."""
    den = float(np.linalg.norm(y - np.mean(y)))
    if not np.isfinite(den) or den < 1e-12:
        return float("nan")
    return C.fit_percent(y, yhat)


def fit_profile(D: Sequence[tuple[np.ndarray, np.ndarray]], dt: float, dof: str, *,
                align: str = "legacy", m_max: int = M_MAX, x0: Sequence[float] | None = None,
                nm_options: dict | None = None) -> dict:
    """Output-error fit on the training pairs ``D = [(u, y), ...]``: Nelder-Mead on ``(K, tau)``
    for every integer delay ``m = 0..m_max`` (``Td = m*dt`` in the alignment's convention),
    keeping the ``m`` of minimum cost. Returns K, tau, m, Td (= m*dt), Td_eff, cost, profile."""
    x0 = tuple(x0 if x0 is not None else X0[dof][:2])
    opts = dict(NM_OPTIONS, **(nm_options or {}))
    best = None
    profile = []
    for m in range(0, m_max + 1):
        Td = _td_of_m(m, dt)

        def cost(p, Td=Td):
            return float(sum(np.sum((y - _sim(u, dt, p[0], p[1], Td, align)) ** 2) for u, y in D))

        r = minimize(cost, list(x0), method="Nelder-Mead", options=opts)
        profile.append((m, float(r.x[0]), float(r.x[1]), float(r.fun)))
        if best is None or r.fun < best[3]:
            best = profile[-1]
    m, K, tau, J = best
    m_eff = effective_delay_samples(m, align)
    return dict(K=K, tau=max(tau, 1e-4), m=m, Td=m * dt, m_eff=m_eff, Td_eff=m_eff * dt, cost=J,
                profile=profile, align=align)


def fit_nm3(D: Sequence[tuple[np.ndarray, np.ndarray]], dt: float, dof: str, *,
            align: str = "legacy", nm_options: dict | None = None) -> dict:
    """The literal paper estimator (``r3_closedloop_omega_fit.compute``): 3-D Nelder-Mead on
    ``[K, tau, Td]`` from ``X0[dof]``. Kept for the documentation check in the idealized cell."""
    opts = dict(NM_OPTIONS, **(nm_options or {}))

    def cost(p):
        return float(sum(np.sum((y - _sim(u, dt, p[0], p[1], p[2], align)) ** 2) for u, y in D))

    r = minimize(cost, list(X0[dof]), method="Nelder-Mead", options=opts)
    K, tau, Td = (float(v) for v in r.x)
    m = C._delay_samples(max(Td, 0.0), dt, align)
    m_eff = effective_delay_samples(m, align)
    return dict(K=K, tau=max(tau, 1e-4), Td=max(Td, 0.0), m=m, m_eff=m_eff, cost=float(r.fun),
                nfev=int(r.nfev), align=align)


def event_split(n: int, rng: np.random.Generator) -> tuple[list[int], list[int]]:
    """Seeded 2/3 train - 1/3 hold-out split by event (``r3`` idiom): ``(train, holdout)``."""
    idx = rng.permutation(n)
    nho = max(1, round(n / 3))
    return sorted(int(i) for i in idx[nho:]), sorted(int(i) for i in idx[:nho])


# =========================================================================
# experiment
# =========================================================================
def _as_tuple(v: Any, default: Sequence[str]) -> tuple[str, ...]:
    if v is None:
        return tuple(default)
    if isinstance(v, str):
        return tuple(s.strip() for s in v.split(",") if s.strip())
    return tuple(str(s) for s in v)


class _Experiment:
    """State of one run: event sets, clean trajectories per (label, deadzone) and noise draws."""

    def __init__(self, ctx: C.Ctx, *, seed: int, threshold: float, design: dict | None, align: str,
                 m_max: int, nm_options: dict | None, generator: str = "fopdt",
                 generator_opts: dict | None = None):
        if generator not in GENERATORS:
            raise ValueError(f"unknown generator {generator!r}; known: {', '.join(GENERATORS)}")
        self.ctx = ctx
        self.params = ctx.params
        self.ts = ctx.ts
        self.seed = seed
        self.threshold = threshold
        self.design = dict(R3_DESIGN, **(design or {}))
        self.align = align
        self.m_max = m_max
        self.nm_options = nm_options
        self.generator = generator
        self.generator_opts = dict(generator_opts or {})
        self._plants: dict[str, Any] = {}                 # deadzone -> generator plant (one per run)
        self.gen_time_s = 0.0                             # wall-clock spent generating trajectories
        self._events: dict[str, list[CmdEvent]] = {}
        self._clean: dict[tuple[str, str], list[np.ndarray]] = {}
        self._masked: dict[str, np.ndarray] = {}          # label -> changed (N_total, 3) bool
        self._clamped: dict[str, np.ndarray] = {}         # label -> fully clamped (N_total,) bool
        self._z: dict[tuple[str, int], list[np.ndarray]] = {}

    # --- data ---------------------------------------------------------------
    def events(self, label: str) -> list[CmdEvent]:
        if label not in self._events:
            if label == "R3":
                self._events[label] = synthetic_events(self.ts, self.design, SEED_DESIGN)
            elif label in R3_DESIGNS:
                self._events[label] = synthetic_events(self.ts, R3_DESIGNS[label], SEED_DESIGN)
            elif label.endswith(WONLY_SUFFIX):
                self._events[label] = wonly_events(self.events(label[:-len(WONLY_SUFFIX)]))
            else:
                self._events[label] = dataset_events(self.ctx, label)
            if not self._events[label]:
                raise RuntimeError(f"no events for label {label!r} in {self.ctx.splits_dir}")
        return self._events[label]

    def plant(self, dz: str):
        """The generator plant for deadzone ``dz`` - built once per run and re-used across events
        (``reset`` re-anchors it). For MuJoCo generators the deadzone lives inside the world."""
        if dz not in self._plants:
            self._plants[dz] = make_generator(self.generator, self.params, dz == "on", **self.generator_opts)
        return self._plants[dz]

    def close(self) -> None:
        for p in self._plants.values():
            if hasattr(p, "close"):
                p.close()
        self._plants.clear()

    def clean_poses(self, label: str, dz: str) -> list[np.ndarray]:
        """Noise-free trajectories of every event of ``label``, generated ONCE per (label, deadzone)
        and shared by all replicates. ``fopdt``: the deadzone masks the command with
        ``apply_body_deadzone`` before the plant; MuJoCo generators: the world applies it."""
        key = (label, dz)
        if key not in self._clean:
            t0 = time.time()
            evs = self.events(label)
            plant = self.plant(dz)
            in_world = self.generator != "fopdt"
            poses, changed, clamped = [], [], []
            for ev in evs:
                if dz == "on":
                    cmd_masked, ch = mask_deadzone(ev.cmd, self.threshold)
                    # fully clamped: a non-zero command that every wheel masks (body command -> 0)
                    clamped.append(np.all(np.abs(cmd_masked) < 1e-12, axis=1) & np.any(np.abs(ev.cmd) > 1e-12, axis=1))
                    cmd_plant = ev.cmd if in_world else cmd_masked
                else:
                    cmd_plant, ch = ev.cmd, np.zeros(ev.cmd.shape, dtype=bool)
                poses.append(simulate_poses_plant(plant, ev, self.ts, cmd_plant))
                changed.append(ch)
            self._clean[key] = poses
            if dz == "on":
                self._masked[label] = np.concatenate(changed, axis=0)
                self._clamped[label] = np.concatenate(clamped, axis=0)
            self.gen_time_s += time.time() - t0
        return self._clean[key]

    def masked_fraction(self, label: str) -> dict[str, float]:
        """Fractions of samples the deadzone alters: ``any`` component (at least one wheel masked,
        command altered through the pseudo-inverse), per DOF component (``vx``/``vy``/``w``) and
        ``clamped`` (every wheel masked: body command zeroed - the paper's "fully clamped")."""
        if label not in self._masked:
            self.clean_poses(label, "on")
        ch = self._masked[label]
        out = {"any": float(ch.any(axis=1).mean())}
        out.update({d: float(ch[:, i].mean()) for i, d in enumerate(DOFS)})
        out["clamped"] = float(self._clamped[label].mean())
        return out

    def noise_draws(self, label: str, rep: int) -> list[np.ndarray]:
        key = (label, rep)
        if key not in self._z:
            rng = np.random.default_rng(self.seed + rep)
            self._z[key] = [rng.standard_normal((ev.n, 3)) for ev in self.events(label)]
        return self._z[key]

    # --- one replicate ---------------------------------------------------------
    def replicate(self, regime: str, dof: str, noise: str, dz: str, rep: int) -> dict:
        label = regime_label(regime, dof)
        evs = self.events(label)
        poses = self.clean_poses(label, dz)
        sig_pos, sig_th = NOISES[noise]
        z = self.noise_draws(label, rep) if noise != "none" else [None] * len(evs)
        pairs, names = [], []
        for ev, pose, zz in zip(evs, poses, z, strict=True):
            cmd_df, rob_df = measurement_tables(ev, pose, sig_pos, sig_th, zz)
            s = uy_series(cmd_df, rob_df, dof, self.ts)
            if s is not None:
                pairs.append(s)
                names.append(ev.name)
        rng_split = np.random.default_rng(self.seed + SPLIT_OFFSET + rep)
        tr, ho = event_split(len(pairs), rng_split)
        row = dict(regime=regime, dof=dof, noise=noise, deadzone=dz, rep=rep, label=label,
                   seed_noise=self.seed + rep, seed_split=self.seed + SPLIT_OFFSET + rep,
                   n_events=len(pairs), n_train=len(tr), n_holdout=len(ho),
                   holdout_events=";".join(names[i] for i in ho))
        u_tr = np.concatenate([pairs[i][0] for i in tr])
        if float(np.std(u_tr)) < DEGENERATE_STD:
            row.update(degenerate=True, K=np.nan, tau=np.nan, m=-99, Td=np.nan, m_eff=np.nan, Td_eff=np.nan,
                       cost=np.nan, fit_holdout_mean=np.nan, fit_train_median=np.nan)
            return row
        f = fit_profile([pairs[i] for i in tr], self.ts, dof, align=self.align, m_max=self.m_max,
                        nm_options=self.nm_options)
        Td_in = _td_of_m(f["m"], self.ts)

        def fits(ids):
            return [fit_safe(pairs[i][1], _sim(pairs[i][0], self.ts, f["K"], f["tau"], Td_in, self.align))
                    for i in ids]

        f_ho, f_tr = fits(ho), fits(tr)
        row.update(degenerate=False, K=f["K"], tau=f["tau"], m=f["m"], Td=f["Td"], m_eff=f["m_eff"],
                   Td_eff=f["Td_eff"], cost=f["cost"],
                   fit_holdout_mean=float(np.nanmean(f_ho)) if np.isfinite(f_ho).any() else np.nan,
                   fit_train_median=float(np.nanmedian(f_tr)) if np.isfinite(f_tr).any() else np.nan)
        return row

    def paper_estimator_check(self, dof: str, regime: str = "R3") -> dict:
        """3-D NM (literal ``r3`` estimator) vs the profile search in the idealized cell, rep 0."""
        label = regime_label(regime, dof)
        evs, poses = self.events(label), self.clean_poses(label, "off")
        pairs = [uy_series(*measurement_tables(ev, pose, 0.0, 0.0, None), dof, self.ts)
                 for ev, pose in zip(evs, poses, strict=True)]
        pairs = [p for p in pairs if p is not None]
        tr, _ = event_split(len(pairs), np.random.default_rng(self.seed + SPLIT_OFFSET))
        D = [pairs[i] for i in tr]
        a = fit_nm3(D, self.ts, dof, align=self.align, nm_options=self.nm_options)
        b = fit_profile(D, self.ts, dof, align=self.align, m_max=self.m_max, nm_options=self.nm_options)
        return dict(dof=dof, regime=regime, nm3=dict(K=a["K"], tau=a["tau"], Td=a["Td"], m_eff=a["m_eff"],
                                                     cost=a["cost"], nfev=a["nfev"]),
                    profile=dict(K=b["K"], tau=b["tau"], Td=b["Td"], m_eff=b["m_eff"], cost=b["cost"]))


# =========================================================================
# summaries and decision rule
# =========================================================================
def _iqr(x: np.ndarray) -> tuple[float, float, float]:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return float("nan"), float("nan"), float("nan")
    return float(np.median(x)), float(np.percentile(x, 25)), float(np.percentile(x, 75))


def cell_summary(rows: pd.DataFrame, truth: DofParam, ts: float, rule: dict | None = None) -> dict:
    """Median / IQR over the replicates of one cell, relative biases and the four criteria."""
    R = dict(RULE, **(rule or {}))
    K_med, K_lo, K_hi = _iqr(rows["K"].to_numpy(float))
    t_med, t_lo, t_hi = _iqr(rows["tau"].to_numpy(float))
    m_med, m_lo, m_hi = _iqr(rows["m_eff"].to_numpy(float))
    Td_star_samples = truth.Td / ts
    bias_K = (K_med - truth.K) / truth.K if np.isfinite(K_med) else float("nan")
    bias_tau = (t_med - truth.tau) / truth.tau if np.isfinite(t_med) else float("nan")
    dTd = m_med - Td_star_samples if np.isfinite(m_med) else float("nan")
    iqr_K_rel = (K_hi - K_lo) / truth.K if np.isfinite(K_hi) else float("nan")
    crit = dict(K=bool(np.isfinite(bias_K) and abs(bias_K) <= R["bias_K"]),
                tau=bool(np.isfinite(bias_tau) and abs(bias_tau) <= R["bias_tau"]),
                Td=bool(np.isfinite(dTd) and abs(dTd) <= R["dTd_samples"]),
                iqr=bool(np.isfinite(iqr_K_rel) and iqr_K_rel <= R["iqr_K"]))
    score = int(sum(crit.values()))
    fh = rows["fit_holdout_mean"].to_numpy(float)
    ft = rows["fit_train_median"].to_numpy(float)
    return dict(n_rep=int(len(rows)), n_degenerate=int(rows["degenerate"].sum()),
                n_events=int(rows["n_events"].iloc[0]), n_train=int(rows["n_train"].iloc[0]),
                n_holdout=int(rows["n_holdout"].iloc[0]),
                K_med=K_med, K_p25=K_lo, K_p75=K_hi, tau_med=t_med, tau_p25=t_lo, tau_p75=t_hi,
                m_eff_med=m_med, m_eff_p25=m_lo, m_eff_p75=m_hi, Td_star_samples=Td_star_samples,
                m_plant=plant_delay_samples(truth.Td, ts),
                bias_K=bias_K, bias_tau=bias_tau, dTd_samples=dTd, iqr_K_rel=iqr_K_rel,
                fit_holdout_med=float(np.nanmedian(fh)) if np.isfinite(fh).any() else float("nan"),
                fit_train_med=float(np.nanmedian(ft)) if np.isfinite(ft).any() else float("nan"),
                crit=crit, score=score, recovered=bool(score == 4))


def normalize_reference(ref: Any, dofs: Sequence[str] = DOFS) -> dict[str, tuple[str, str, str]]:
    """Per-DOF reference cells ``{dof: (regime, noise, deadzone)}`` from: ``None`` (v1: R3/none/off
    for every DOF), ``"v1"``/``"v2"`` presets, one ``"regime,noise,dz"`` string or triple (all DOFs),
    or a dict ``{dof: triple | "regime,noise,dz"}``."""
    if ref is None or ref == "v1":
        return {d: tuple(REFERENCE_CELL) for d in dofs}
    if ref == "v2":
        return {d: tuple(REFERENCE_V2[d]) for d in dofs}
    if isinstance(ref, dict):
        out = {}
        for d in dofs:
            if d not in ref:
                raise ValueError(f"reference_cell dict lacks dof {d!r}")
            out[d] = tuple(_as_tuple(ref[d], ()))
    else:
        t = tuple(_as_tuple(ref, ()))
        out = {d: t for d in dofs}
    for d, t in out.items():
        if len(t) != 3 or t[1] not in NOISES or t[2] not in DEADZONES:
            raise ValueError(f"reference cell of {d!r} must be (regime, noise, deadzone), got {t!r}")
        regime_label(t[0], d)
    return out


def reference_kind(refs: dict[str, tuple[str, str, str]]) -> str:
    """``"v1"`` / ``"v2"`` when the references equal a pre-registered preset, else ``"custom"``."""
    if all(tuple(t) == tuple(REFERENCE_CELL) for t in refs.values()):
        return "v1"
    if all(tuple(t) == tuple(REFERENCE_V2[d]) for d, t in refs.items() if d in REFERENCE_V2):
        return "v2"
    return "custom"


def reference_deviation(cells: list[dict], dofs: Sequence[str],
                        ref_cells: dict[str, tuple[str, str, str]] | Sequence[str] = REFERENCE_CELL,
                        rule: dict | None = None) -> dict[str, dict]:
    """C1b view for a non-FOPDT generator: per DOF the reference = median estimate of that DOF's
    reference cell (v1: R3/none/off for all; v2: R2-rotate for w, R2-square for vx/vy); every cell
    gets ``dev_K``, ``dev_tau`` (relative), ``dm_eff`` (samples), the v1 composite flag
    ``regime_bias`` (|dev_K| > 10 % or |dev_tau| > 15 %) and the v2 flag ``regime_bias_K``
    (|dev_K| > 10 % only). Cells are updated in place; returns the references."""
    R = dict(REGIME_BIAS, **(rule or {}))
    if not isinstance(ref_cells, dict):
        ref_cells = {d: tuple(ref_cells) for d in dofs}
    refs: dict[str, dict] = {}
    for dof in dofs:
        rc = tuple(ref_cells[dof])
        ref = _find(cells, rc[0], dof, rc[1], rc[2])
        refs[dof] = (dict(K=ref["K_med"], tau=ref["tau_med"], m_eff=ref["m_eff_med"], cell=list(rc))
                     if ref is not None else dict(K=float("nan"), tau=float("nan"), m_eff=float("nan"), cell=list(rc)))
    for c in cells:
        rf = refs[c["dof"]]
        dev_K = (c["K_med"] - rf["K"]) / rf["K"] if np.isfinite(c["K_med"]) and np.isfinite(rf["K"]) else float("nan")
        dev_tau = ((c["tau_med"] - rf["tau"]) / rf["tau"] if np.isfinite(c["tau_med"]) and np.isfinite(rf["tau"])
                   else float("nan"))
        dm = c["m_eff_med"] - rf["m_eff"] if np.isfinite(c["m_eff_med"]) and np.isfinite(rf["m_eff"]) else float("nan")
        c.update(dev_K=dev_K, dev_tau=dev_tau, dm_eff=dm,
                 regime_bias=bool((np.isfinite(dev_K) and abs(dev_K) > R["dev_K"])
                                  or (np.isfinite(dev_tau) and abs(dev_tau) > R["dev_tau"])),
                 regime_bias_defined=bool(np.isfinite(dev_K) and np.isfinite(dev_tau)),
                 regime_bias_K=bool(np.isfinite(dev_K) and abs(dev_K) > R["dev_K"]),
                 regime_bias_K_defined=bool(np.isfinite(dev_K)))
    return refs


def compute(ctx: C.Ctx, *, n_rep: int = N_REP, regimes: Sequence[str] = REGIMES,
            noises: Sequence[str] = tuple(NOISES), deadzones: Sequence[str] = DEADZONES,
            dofs: Sequence[str] = DOFS, seed: int = SEED, align: str = "legacy", m_max: int = M_MAX,
            design: dict | None = None, nm_options: dict | None = None, threshold: float | None = None,
            paper_check: bool = True, generator: str = "fopdt", generator_opts: dict | None = None,
            reference_cell: Any = None, variant: str = "v1", quiet: bool = False) -> dict:
    """Run the factorial Monte Carlo; returns replicate rows, per-cell summaries and the design.

    ``generator``: ``fopdt`` (C1, default) or a MuJoCo harness plant (C1b: ``mujoco-velocity``,
    ``mujoco-rollers``, ``mujoco-rollers-delay``; ``generator_opts`` -> world options). Trajectories
    are generated once per (event set, deadzone) and shared by every replicate; the generator plant
    is built once per deadzone level and closed at the end. ``reference_cell`` selects the per-DOF
    reference of the C1b deviations (see :func:`normalize_reference`): ``None``/``"v1"`` = R3/none/off
    for every DOF (C1b-v1), ``"v2"`` = R2-rotate for w and R2-square for vx/vy (C1b-v2 re-registration);
    anything else is an exploratory reading and is labelled as such. ``variant`` (``"v1"`` | ``"v2"``)
    selects the pre-registered reading (v2: K-only rule, R3-mild regime, ``_v2`` artefact stem).
    """
    if threshold is None:
        _, threshold = load_deadzone(ctx.config("robot_limits.json"))
    ex = _Experiment(ctx, seed=seed, threshold=float(threshold), design=design, align=align,
                     m_max=m_max, nm_options=nm_options, generator=generator, generator_opts=generator_opts)
    t_start = time.time()
    rows: list[dict] = []
    grid = [(regime, dof) for regime in regimes for dof in dofs if cell_applies(regime, dof)]
    n_cells = len(grid) * len(deadzones) * len(noises)
    i_cell = 0
    try:
        for regime, dof in grid:
            for dz in deadzones:
                for noise in noises:
                    i_cell += 1
                    t0 = time.time()
                    for rep in range(n_rep):
                        rows.append(ex.replicate(regime, dof, noise, dz, rep))
                    if not quiet:
                        last = rows[-1]
                        print(f"[{i_cell:3d}/{n_cells}] {generator:20s} {regime:9s} {dof:2s} dz={dz:3s} "
                              f"noise={noise:6s} n_rep={n_rep} K={last['K']:.4f} tau={last['tau']:.4f} "
                              f"m_eff={last['m_eff']} ({time.time() - t0:.1f} s, total {time.time() - t_start:.0f} s)",
                              flush=True)
        masked = {}
        for regime, dof in grid:
            label = regime_label(regime, dof)
            if label not in masked:
                masked[label] = dict(ex.masked_fraction(label), n_events=len(ex.events(label)),
                                     n_samples=int(sum(ev.n for ev in ex.events(label))))
        check = []
        r3_like = [rg for rg in ("R3", "R3-mild") if rg in regimes]
        if paper_check and r3_like:
            check = [ex.paper_estimator_check(dof, r3_like[0]) for dof in dofs]
    finally:
        ex.close()
    df = pd.DataFrame(rows)
    if generator != "fopdt":
        df.insert(0, "generator", generator)
    cells = []
    for regime, dof in grid:
        for dz in deadzones:
            for noise in noises:
                sel = df[(df.regime == regime) & (df.dof == dof) & (df.deadzone == dz) & (df.noise == noise)]
                s = cell_summary(sel, ctx.params[dof], ctx.ts)
                label = regime_label(regime, dof)
                s.update(regime=regime, dof=dof, deadzone=dz, noise=noise, label=label,
                         masked_any=masked[label]["any"], masked_dof=masked[label][dof],
                         masked_clamped=masked[label]["clamped"])
                cells.append(s)
    if variant not in VARIANTS:
        raise ValueError(f"variant must be one of {VARIANTS}, got {variant!r}")
    ref_cells = normalize_reference("v2" if (reference_cell is None and variant == "v2") else reference_cell, dofs)
    reference = reference_deviation(cells, dofs, ref_cells) if generator != "fopdt" else None
    design_out = dict(theta_star={d: dict(K=ctx.params[d].K, tau=ctx.params[d].tau, Td=ctx.params[d].Td,
                                          Td_samples=ctx.params[d].Td / ctx.ts,
                                          m_plant=plant_delay_samples(ctx.params[d].Td, ctx.ts)) for d in dofs},
                      ts=ctx.ts, regimes=list(regimes), noises={k: NOISES[k] for k in noises},
                      deadzones=list(deadzones), dofs=list(dofs), n_rep=n_rep, seed=seed,
                      seed_design=SEED_DESIGN, split_offset=SPLIT_OFFSET, r1_labels=R1_LABELS,
                      regime_labels=REGIME_LABELS, r3_design=ex.design, deadzone_wheel_rad_s=float(threshold),
                      estimator=dict(kind="profile-NM", align=align, m_max=m_max, x0=X0,
                                     nm_options=dict(NM_OPTIONS, **(nm_options or {})), min_len=MIN_LEN,
                                     pos_scale=POS_SCALE), rule=RULE, events={k: [e.name for e in v]
                                                                             for k, v in ex._events.items()},
                      masked=masked, realistic=REALISTIC, idealized=IDEALIZED)
    if "R3-mild" in regimes:
        design_out["r3_mild_design"] = R3_MILD_DESIGN
    if generator != "fopdt":
        kind = reference_kind(ref_cells)
        design_out.update(generator=generator, generator_opts=ex.generator_opts,
                          truth_known=generator in TRUTH_KNOWN,
                          reference_cell=list(REFERENCE_CELL) if kind == "v1" else {d: list(t) for d, t in ref_cells.items()},
                          reference_cells={d: list(t) for d, t in ref_cells.items()}, reference_kind=kind,
                          reference_preregistered=bool(kind == variant),
                          regime_bias_rule=REGIME_BIAS, reference=reference, gen_time_s=ex.gen_time_s)
    else:
        design_out["generator"] = "fopdt"
    if variant != "v1":
        design_out["variant"] = variant
    return dict(rows=df, cells=cells, design=design_out, paper_check=check,
                runtime_s=time.time() - t_start, n_fits=int((~df.degenerate).sum()))


# =========================================================================
# report
# =========================================================================
def _f(v: float, nd: int = 3) -> str:
    return "nan" if v is None or not np.isfinite(v) else f"{v:.{nd}f}"


def _pct(v: float) -> str:
    return "nan" if v is None or not np.isfinite(v) else f"{100.0 * v:+.1f}"


def _flag(c: dict) -> str:
    return f"{'SIM' if c['recovered'] else 'nao'} ({c['score']}/4)"


def _find(cells: list[dict], regime: str, dof: str, noise: str, dz: str) -> dict | None:
    for c in cells:
        if (c["regime"], c["dof"], c["noise"], c["deadzone"]) == (regime, dof, noise, dz):
            return c
    return None


def _hypotheses(r: dict) -> list[str]:
    """Pre-registered readings H1-H4 evaluated on the cell flags of the realistic cell (ASCII)."""
    cells, d = r["cells"], r["design"]
    regs, dofs, noises, dzs = d["regimes"], d["dofs"], list(d["noises"]), d["deadzones"]
    nz, dz = REALISTIC
    out = []

    def have(*keys: str) -> bool:
        return all(k in pool for k, pool in zip(keys, (regs, dofs, noises, dzs), strict=False))

    def rec(regime: str, dof: str, noise: str = nz, deadzone: str = dz) -> bool:
        c = _find(cells, regime, dof, noise, deadzone)
        return bool(c is not None and c["recovered"])

    def bias(regime: str, dof: str, noise: str = nz, deadzone: str = dz) -> float:
        c = _find(cells, regime, dof, noise, deadzone)
        return float("nan") if c is None else c["bias_K"]

    yn = {True: "SIM", False: "nao"}
    if have("R1", "w", nz, dz) and "R2-rotate" in regs and "R3" in regs:
        r1, r2, r3 = rec("R1", "w"), rec("R2-rotate", "w"), rec("R3", "w")
        ok = r2 and r3 and not r1
        tail = ""
        if r1:
            tail = (" (w E recuperado em R1: o conteudo de comando de competicao basta para o gerador linear; "
                    "o mecanismo do K~1.38 real esta fora do gerador - diluicao/realimentacao)")
        out.append(f"- H1 (w recuperado em R2-rotate/R3 e NAO em R1 com zona morta on, celula realista): "
                   f"R2-rotate={yn[r2]}, R3={yn[r3]}, R1={yn[r1]} -> {'CORROBORADA' if ok else 'FALSIFICADA'}{tail}")
    if have("R1", "vx", nz, dz) and "R3" in regs and "vy" in dofs:
        ok_r1 = all(rec("R1", dd) for dd in ("vx", "vy"))
        ok_r3 = all(rec("R3", dd) for dd in ("vx", "vy"))
        deg = "R2-rotate" in regs and not any(rec("R2-rotate", dd) for dd in ("vx", "vy"))
        ok = ok_r1 and ok_r3 and (deg or "R2-rotate" not in regs)
        out.append(f"- H2 (vx/vy recuperados em R1 e R3, degradados em R2-rotate): R1={yn[ok_r1]}, R3={yn[ok_r3]}, "
                   f"R2-rotate degradado={yn[deg]} -> {'CORROBORADA' if ok else 'FALSIFICADA'}")
    if {"none", "heavy"} <= set(noises):
        viol, widen = [], []
        for regime in regs:
            for dof in dofs:
                for ddz in dzs:
                    c0, c2 = _find(cells, regime, dof, "none", ddz), _find(cells, regime, dof, "heavy", ddz)
                    if c0 and c2 and c0["recovered"] and not c2["crit"]["K"]:
                        viol.append(f"{regime}/{dof}/{ddz}")
                    cs = [_find(cells, regime, dof, n_, ddz) for n_ in noises]
                    if all(c is not None and np.isfinite(c["iqr_K_rel"]) for c in cs):
                        widen.append(all(cs[i]["iqr_K_rel"] <= cs[i + 1]["iqr_K_rel"] + 1e-12
                                         for i in range(len(cs) - 1)))
        frac = (sum(widen) / len(widen)) if widen else float("nan")
        out.append(f"- H3 (ruido alarga o IQR de K mas nao enviesa K): celulas recuperadas em `none` que perdem o "
                   f"criterio de K em `heavy`: {len(viol)}{' ' + ', '.join(viol) if viol else ''}; IQR(K) nao "
                   f"decrescente none->vision->heavy em {100 * frac:.0f} % das combinacoes regime x DOF x zona morta "
                   f"-> {'CORROBORADA' if not viol else 'FALSIFICADA'}")
    if have("R1", "w", nz, dz) and "off" in dzs:
        b_on, b_off = bias("R1", "w", nz, "on"), bias("R1", "w", nz, "off")
        ok = bool(np.isfinite(b_on) and abs(b_on) > RULE["bias_K"] and abs(b_off) <= RULE["bias_K"])
        tail = ("" if ok else " (a zona morta nao explica o K~1.38 de malha fechada: reforca a leitura de "
                "diluicao/realimentacao do artigo, ausente do gerador)")
        out.append(f"- H4 (zona morta e o mecanismo principal do vies de K em R1/w): vies K on={_pct(b_on)} %, "
                   f"off={_pct(b_off)} % -> {'CORROBORADA' if ok else 'FALSIFICADA'}{tail}")
    return out


FIT_GATE = 60.0                # paper's pre-registered hold-out fit gate (%)


def _fit_gate_reading(cells: list[dict]) -> list[str]:
    """Recovered cells (4/4) whose median hold-out fit is below the paper's 60 % gate: fit % follows
    the signal-to-noise ratio of the regime, not the recovery of the parameters."""
    rec = [c for c in cells if c["recovered"]]
    low = [c for c in rec if np.isfinite(c["fit_holdout_med"]) and c["fit_holdout_med"] < FIT_GATE]
    if not rec:
        return []
    ex = "; ".join(f"{c['regime']}/{c['dof']}/{c['noise']}/{c['deadzone']} = {c['fit_holdout_med']:.1f} %"
                   for c in sorted(low, key=lambda c: c["fit_holdout_med"])[:6])
    return [f"- Fit % vs recuperacao: {len(low)} de {len(rec)} celulas recuperadas (4/4) tem fit hold-out mediano "
            f"< {FIT_GATE:.0f} % (gate do artigo){': ' + ex if low else ''}"
            + (" -> o fit % (NRMSE) mede a relacao sinal-ruido da excitacao do regime (variancia de y explicada "
               "pelo comando), nao a recuperacao dos parametros: parametros exatos podem coexistir com fit baixo "
               "em regimes de pouca excitacao ou muito ruido" if low else "")]


def _flag_bias(c: dict) -> str:
    """C1b-v1 composite flag (``regime_bias``: |dev K| > 10 % or |dev tau| > 15 %)."""
    if not c.get("regime_bias_defined", False):
        return "indef."
    return "VIES" if c["regime_bias"] else "ok"


def _flag_bias_K(c: dict) -> str:
    """C1b-v2 flag (``regime_bias_K``: |dev K| > 10 % only)."""
    if not c.get("regime_bias_K_defined", False):
        return "indef."
    return "VIES" if c["regime_bias_K"] else "ok"


def _ref_label(d: dict) -> str:
    """Human-readable reference cells of the design (v1: one cell; v2/custom: per DOF)."""
    rc = d.get("reference_cells") or {}
    if not rc:
        return "/".join(d.get("reference_cell", REFERENCE_CELL))
    if len({tuple(v) for v in rc.values()}) == 1:
        return "/".join(next(iter(rc.values())))
    return "; ".join(f"{dof}: {'/'.join(v)}" for dof, v in rc.items())


def _hypotheses_c1b_v2(r: dict) -> list[str]:
    """C1b-v2 re-registered readings H5'-H7' (K-only rule, per-DOF references), realistic cell and
    idealized cell (ASCII)."""
    cells, d = r["cells"], r["design"]
    regs, dofs, noises, dzs = d["regimes"], d["dofs"], list(d["noises"]), d["deadzones"]
    out = []

    def cell(regime, dof, noise, dz):
        return _find(cells, regime, dof, noise, dz)

    def dev(regime, dof, noise, dz):
        c = cell(regime, dof, noise, dz)
        return float("nan") if c is None else c.get("dev_K", float("nan"))

    def flag(regime, dof, noise, dz):
        c = cell(regime, dof, noise, dz)
        return None if c is None or not c.get("regime_bias_K_defined", False) else bool(c["regime_bias_K"])

    yn = {True: "SIM", False: "nao", None: "indef."}
    views = [v for v in ((REALISTIC, "realista"), (IDEALIZED, "idealizada"))
             if v[0][0] in noises and v[0][1] in dzs]
    thr = REGIME_BIAS["dev_K"]
    if "w" in dofs and "R1" in regs:
        for (nz, dz), name in views:
            dk = dev("R1", "w", nz, dz)
            f3 = flag("R3-mild", "w", nz, dz) if "R3-mild" in regs else None
            ok = bool(np.isfinite(dk) and dk >= thr and f3 is not True)
            tail = ""
            if np.isfinite(dk) and 0.0 < dk < thr:
                tail = " (efeito parcial: desvio positivo abaixo do nivel pre-registrado)"
            elif np.isfinite(dk) and dk <= 0.0:
                tail = " (sem inflacao: desvio nulo ou negativo)"
            out.append(f"- H5' (dev K_w(R1) >= +10 % vs referencia R2-rotate e regime_bias_K falsa em R3-mild), "
                       f"celula {name} ({nz}/{dz}): dev K_w(R1) = {_pct(dk)} %, regime_bias_K R3-mild = {yn[f3]} "
                       f"-> {'CORROBORADA' if ok else 'FALSIFICADA'}{tail}")
    if "w" in dofs and "R1-wonly" in regs:
        for (nz, dz), name in views:
            dk_w, dk_r1 = dev("R1-wonly", "w", nz, dz), dev("R1", "w", nz, dz)
            f = flag("R1-wonly", "w", nz, dz)
            ok = f is False
            out.append(f"- H6' (controle R1-wonly: |dev K_w| <= 10 %), celula {name}: dev K_w(R1-wonly) = {_pct(dk_w)} % "
                       f"vs R1 = {_pct(dk_r1)} %, regime_bias_K R1-wonly = {yn[f]} -> {'CORROBORADA' if ok else 'FALSIFICADA'}")
    if "R1" in regs and any(dd in dofs for dd in ("vx", "vy")):
        for (nz, dz), name in views:
            parts, flags = [], []
            for dd in ("vx", "vy"):
                if dd in dofs:
                    f = flag("R1", dd, nz, dz)
                    dk = dev("R1", dd, nz, dz)
                    flags.append(f)
                    sig = ""
                    if f and np.isfinite(dk):
                        sig = " [desvio negativo: assinatura de saturacao de velocidade]" if dk < 0 else \
                              " [desvio positivo]"
                    parts.append(f"{dd}: dev K {_pct(dk)} %, regime_bias_K {yn[f]}{sig}")
            ok = all(f is False for f in flags)
            out.append(f"- H7' (vx/vy: regime_bias_K falsa em R1 vs referencia R2-square), celula {name}: "
                       + "; ".join(parts) + f" -> {'CORROBORADA' if ok else 'FALSIFICADA'}")
    return out


def _hypotheses_c1b(r: dict) -> list[str]:
    """Pre-registered readings H5-H7 of C1b (physical generator), realistic cell, checked on the
    idealized one (ASCII). H8 (mujoco-velocity vs the C1 artefact) is a cross-run comparison."""
    cells, d = r["cells"], r["design"]
    regs, dofs, noises, dzs = d["regimes"], d["dofs"], list(d["noises"]), d["deadzones"]
    out = []

    def cell(regime, dof, noise, dz):
        return _find(cells, regime, dof, noise, dz)

    def dev(regime, dof, noise, dz):
        c = cell(regime, dof, noise, dz)
        return float("nan") if c is None else c.get("dev_K", float("nan"))

    def bias(regime, dof, noise, dz):
        c = cell(regime, dof, noise, dz)
        return None if c is None or not c.get("regime_bias_defined", False) else bool(c["regime_bias"])

    yn = {True: "SIM", False: "nao", None: "indef."}
    views = [v for v in ((REALISTIC, "realista"), (IDEALIZED, "idealizada"))
             if v[0][0] in noises and v[0][1] in dzs]
    if "w" in dofs and "R1" in regs and "R3" in regs:
        for (nz, dz), name in views:
            dk = dev("R1", "w", nz, dz)
            b_r2 = bias("R2-rotate", "w", nz, dz) if "R2-rotate" in regs else None
            ok = bool(np.isfinite(dk) and dk >= REGIME_BIAS["dev_K"] and (b_r2 is False or "R2-rotate" not in regs))
            out.append(f"- H5 (gerador fisico: K_w em R1 desvia >= +10 % da referencia R3 e R2-rotate/R3 nao), "
                       f"celula {name} ({nz}/{dz}): dev K_w(R1) = {_pct(dk)} %, regime_bias R2-rotate = {yn[b_r2]} "
                       f"-> {'CORROBORADA' if ok else 'FALSIFICADA'}"
                       + ("" if ok else (" (desvio negativo/abaixo de +10 %: o modelo fisico como entregue nao produz a "
                                         "inflacao de malha fechada)" if np.isfinite(dk) and dk < REGIME_BIAS["dev_K"]
                                         else "")))
    if "w" in dofs and "R1-wonly" in regs and "R1" in regs:
        for (nz, dz), name in views:
            dk_w, dk_r1 = dev("R1-wonly", "w", nz, dz), dev("R1", "w", nz, dz)
            b = bias("R1-wonly", "w", nz, dz)
            ok = b is False
            out.append(f"- H6 (controle R1-wonly: sem translacao o desvio de K_w some), celula {name}: "
                       f"dev K_w(R1-wonly) = {_pct(dk_w)} % vs R1 = {_pct(dk_r1)} %, regime_bias R1-wonly = {yn[b]} "
                       f"-> {'CORROBORADA' if ok else 'FALSIFICADA'}")
    if "R1" in regs and any(dd in dofs for dd in ("vx", "vy")):
        for (nz, dz), name in views:
            parts, flags = [], []
            for dd in ("vx", "vy"):
                if dd in dofs:
                    b = bias("R1", dd, nz, dz)
                    flags.append(b)
                    parts.append(f"{dd}: dev K {_pct(dev('R1', dd, nz, dz))} %, dev tau "
                                 f"{_pct(cell('R1', dd, nz, dz)['dev_tau'] if cell('R1', dd, nz, dz) else float('nan'))} %, "
                                 f"regime_bias {yn[b]}")
            ok = all(b is False for b in flags)
            out.append(f"- H7 (vx/vy sem dependencia de regime comparavel em R1), celula {name}: "
                       + "; ".join(parts) + f" -> {'CORROBORADA' if ok else 'FALSIFICADA'}")
    if d.get("truth_known"):
        rec = [c for c in cells if c["recovered"]]
        nd = [c for c in cells if not c["n_degenerate"]]
        out.append(f"- H8 (gerador = gemeo embutido, verdade conhecida): {len(rec)} de {len(nd)} celulas nao degeneradas "
                   f"recuperam theta* (4/4); comparacao numerica com o artefato de C1 (fopdt, `_1552`) feita fora do "
                   f"modulo (mesmas seeds; criterio 1 % em K e tau, mesmo m_eff).")
    return out


def render(ctx: C.Ctx, r: dict, note: str | None = None) -> list[str]:
    d, cells = r["design"], r["cells"]
    gen = d.get("generator", "fopdt")
    physical = gen != "fopdt"
    truth_known = (not physical) or bool(d.get("truth_known"))
    v2 = d.get("variant", "v1") == "v2"
    if v2:
        title = f"Identificabilidade in-silico (C1b-v2, re-registro): gerador {gen} - regime x ruido x zona morta"
    elif physical:
        title = f"Identificabilidade in-silico (C1b): gerador {gen} - regime x ruido x zona morta"
    else:
        title = "Identificabilidade in-silico (C1): regime de excitacao x ruido x zona morta"
    extra = (f"n_rep={d['n_rep']} | estimador profile-NM align={d['estimator']['align']} "
             f"| {r['n_fits']} ajustes em {r['runtime_s'] / 60:.1f} min")
    if physical:
        extra = f"gerador {gen} (opts {d.get('generator_opts') or {}}) | " + extra + \
                f" (geracao de trajetorias {d.get('gen_time_s', 0.0) / 60:.1f} min)"
    L = C.result_header(title, ctx, generator=f"dtssl.analysis.{NAME}", seed=d["seed"], extra=extra)
    if v2:
        L += ["Re-registro C1b-v2: docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_C1B_V2_20260907.md (emenda documentada",
              "apos a execucao v1; muda SO: regime R3-mild dentro do envelope da rota b, referencias por DOF =",
              "regimes dedicados de malha aberta (w: R2-rotate/none/off; vx, vy: R2-square/none/off) e regra",
              "K-only regime_bias_K = |dev K| > 10 %; dev tau e dm_eff sao descritivos). v1 e seus artefatos",
              "ficam intocados.", ""]
    if not physical:
        L += ["Pre-registro: docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_20260907.md (hipoteses H1-H4, regra",
              "de decisao e seeds fixadas antes de rodar). Verdade conhecida: theta* = theta oficial; o gemeo",
              "(AnalyticFOPDTPlant) gera as trajetorias a partir dos comandos de cada regime, a cadeia de medicao",
              "tipo visao adiciona ruido, e a cadeia de estimacao Python do artigo (legacy_uy_series + custo de",
              "erro de saida de r3_closedloop_omega_fit) re-identifica (K, tau, Td) por DOF.", ""]
    else:
        L += ["Pre-registro: docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_C1B_20260907.md (adendo C1b: hipoteses",
              "H5-H8, referencia e bandeira regime_bias fixadas antes de rodar) sobre o desenho de C1",
              "(docs/PREREGISTRO_IDENTIFICABILIDADE_INSILICO_20260907.md).",
              f"GERADOR: `{gen}` via `dtssl.sim.world_plant.make_harness_plant` (MuJoCoWorld de um robo visto como",
              "Plant do harness; `mujoco-velocity` = rota a, a AnalyticFOPDTPlant(theta*) dirigindo o chassi;",
              "`mujoco-rollers` = rota b, rodas omni + roletes livres, sem sintonia e sem atraso;",
              "`mujoco-rollers-delay` = rota b + tap de atraso ceil(Td*/Ts) por DOF no comando). Zona morta do",
              "fator C aplicada DENTRO do mundo (`deadzone=True`: rota a = regra de corpo de apply_body_deadzone;",
              "rota b = por roda, no setpoint de cada atuador); o estimador ve sempre o comando original.",
              "Trajetoria por evento gerada UMA vez por (conjunto, zona morta) e partilhada pelas replicas."]
        if truth_known:
            L += ["Este gerador embute a propria AnalyticFOPDTPlant(theta*): a verdade e conhecida e as bandeiras",
                  "'recuperado' de C1 continuam validas; o desvio da referencia R3 e reportado em paralelo.", ""]
        else:
            L += ["Para este gerador theta* NAO e a verdade do modelo: a pergunta e se a estimativa P1D depende do",
                  "regime. Referencia por DOF = mediana das estimativas na celula R3 / none / off do proprio gerador;",
                  "cada celula reporta o desvio (dev) da referencia e a bandeira regime_bias = |dev K| > 10 % ou",
                  "|dev tau| > 15 % (substitui 'recuperado'). theta* fica na tabela so como contexto.", ""]
    if note:
        L += [f"**Desvio declarado:** {note}", ""]
    L += ["## Desenho", "",
          "| DOF | K* | tau* (s) | Td* (s) | Td*/Ts (amostras) | atraso da planta (amostras) |", "|---|---|---|---|---|---|"]
    for dof, t in d["theta_star"].items():
        L.append(f"| {dof} | {t['K']:.4f} | {t['tau']:.4f} | {t['Td']:.5f} | {t['Td_samples']:.2f} | {t['m_plant']} |")
    gen_line = ("gerador `AnalyticFOPDTPlant(theta*)`" if not physical else
                f"gerador `{gen}` (`make_harness_plant`, opts {d.get('generator_opts') or {}})")
    L += ["", f"- Ts = {d['ts']:.6f} s; {gen_line}, `reset(pose0, velb0=0)`, "
          "`pose[k] = step(cmd[k-1])` (driver de `free_run`, buffer de atraso vazio).",
          "- Regimes (eventos): " + "; ".join(f"`{k}` = {len(v)} eventos" for k, v in d["events"].items()),
          f"- R1 (pareamento do artigo): vx `{d['r1_labels']['vx']}`, vy `{d['r1_labels']['vy']}`, w `{d['r1_labels']['w']}`; "
          + ("R1-wonly = as mesmas sequencias de R1 com vx = vy = 0 (controle, so DOF w); "
             if "R1-wonly" in d["regimes"] else "")
          + "R2-rotate `rotate` (10 eventos, inclui +-0.25/+-0.5 rad/s); R2-square `square`; "
          f"R3 sintetico: {d['r3_design']['n_events']} eventos x {d['r3_design']['duration_s']:.0f} s, degraus de "
          f"{d['r3_design']['step_s'][0]}-{d['r3_design']['step_s'][1]} s, amplitude +-[{d['r3_design']['amp_trans'][0]}, "
          f"{d['r3_design']['amp_trans'][1]}] m/s (vx, vy) e +-[{d['r3_design']['amp_rot'][0]}, {d['r3_design']['amp_rot'][1]}] rad/s (w), "
          f"3 DOFs simultaneos, seed de desenho {d['seed_design']}."
          + ((f" R3-mild (envelope da rota b): amplitude +-[{d['r3_mild_design']['amp_trans'][0]}, "
              f"{d['r3_mild_design']['amp_trans'][1]}] m/s (vx, vy) e +-[{d['r3_mild_design']['amp_rot'][0]}, "
              f"{d['r3_mild_design']['amp_rot'][1]}] rad/s (w), degraus de {d['r3_mild_design']['step_s'][0]}-"
              f"{d['r3_mild_design']['step_s'][1]} s, mesma construcao e seed.") if d.get("r3_mild_design") else ""),
          "- Ruido (sigma_pos mm, sigma_theta rad): " + "; ".join(f"`{k}` = ({v[0]}, {v[1]})" for k, v in d["noises"].items())
          + f"; i.i.d. por amostra, seed {d['seed']} + rep (numeros aleatorios comuns entre niveis).",
          (f"- Zona morta do gerador: `apply_body_deadzone` por roda, limiar {d['deadzone_wheel_rad_s']} rad/s "
           "(corpo ~0.58-0.60 rad/s em rotacao pura), aplicada ao comando ANTES da planta; o estimador ve o comando original."
           if not physical else
           f"- Zona morta do gerador: limiar de firmware {d['deadzone_wheel_rad_s']} rad/s por roda aplicado pelo MuJoCoWorld "
           "(`deadzone=True`); as fracoes mascaradas abaixo usam a mesma regra por roda (`mask_deadzone`)."),
          f"- Monte Carlo: n_rep = {d['n_rep']} por celula; split 2/3-1/3 por evento seeded (seed {d['seed']} + "
          f"{d['split_offset']} + rep); fit nos eventos de treino, fit % medio no hold-out.",
          f"- Estimador: `legacy_uy_series` (SG 7/2 + diferencas centrais, mm -> m) + Nelder-Mead em (K, tau) para cada "
          f"atraso inteiro m = 0..{d['estimator']['m_max']} (custo de erro de saida, `simulate_fopdt` align="
          f"{d['estimator']['align']}, clamps tau >= 1e-4), m de menor custo de treino; X0 (K, tau) = "
          f"{tuple(X0['vx'][:2])} (vx, vy) / {tuple(X0['w'][:2])} (w); NM {d['estimator']['nm_options']}. "
          "m_eff = m - 1 (align legacy aplica uma amostra a menos de atraso que a planta; common.py).",
          f"- Regra (por celula, mediana/IQR sobre as replicas): |vies K| <= {100 * RULE['bias_K']:.0f} %, "
          f"|vies tau| <= {100 * RULE['bias_tau']:.0f} %, |mediana(m_eff) - Td*/Ts| <= {RULE['dTd_samples']:.0f} amostra, "
          f"IQR(K)/K* <= {100 * RULE['iqr_K']:.0f} %; escore = criterios satisfeitos (0-4); recuperado = 4/4."
          + ("" if not physical else
             f" Regra C1b: referencia = celula {'/'.join(d['reference_cell'])} por DOF; regime_bias = |dev K| > "
             f"{100 * d['regime_bias_rule']['dev_K']:.0f} % ou |dev tau| > {100 * d['regime_bias_rule']['dev_tau']:.0f} %."),
          "",
          "Fracao de amostras em que a zona morta altera o comando (`qualquer roda`: ao menos uma roda abaixo",
          "de 1.567 rad/s, comando de corpo alterado pela pseudo-inversa; colunas vx/vy/w: a componente do DOF",
          "muda; `todas as rodas`: comando de corpo zerado = 'fully clamped' do artigo):", "",
          "| conjunto | eventos | amostras | qualquer roda | vx | vy | w | todas as rodas |",
          "|---|---|---|---|---|---|---|---|"]
    for k, m in d["masked"].items():
        L.append(f"| `{k}` | {m['n_events']} | {m['n_samples']} | {100 * m['any']:.1f} % | {100 * m['vx']:.1f} % "
                 f"| {100 * m['vy']:.1f} % | {100 * m['w']:.1f} % | {100 * m['clamped']:.1f} % |")
    if physical and d.get("reference"):
        kind = d.get("reference_kind", "v1")
        tag = (f" - pre-registrada C1b-{kind}" if d.get("reference_preregistered", True)
               else " - EXPLORATORIA, nao pre-registrada")
        L += ["", f"Referencia por DOF (gerador `{gen}`; celulas {_ref_label(d)}{tag}) e sua distancia ao theta* "
              "do gemeo (contexto, nao criterio):", "",
              "| DOF | celula de referencia | K ref | tau ref (s) | m_eff ref | K ref / K* - 1 | tau ref / tau* - 1 "
              "| m_eff ref - Td*/Ts |", "|---|---|---|---|---|---|---|---|"]
        for dof, rf in d["reference"].items():
            t = d["theta_star"][dof]
            L.append(f"| {dof} | {'/'.join(rf['cell'])} | {_f(rf['K'], 4)} | {_f(rf['tau'], 4)} | {_f(rf['m_eff'], 1)} "
                     f"| {_pct(rf['K'] / t['K'] - 1.0)} % | {_pct(rf['tau'] / t['tau'] - 1.0)} % "
                     f"| {_f(rf['m_eff'] - t['Td_samples'], 2)} |")
    if r.get("paper_check"):
        L += ["", "Checagem do estimador literal do artigo (NM 3-D em [K, tau, Td] a partir de X0, `r3`) contra o perfil "
              "em m, celula idealizada R3/none/off, split da replica 0:", "",
              "| DOF | NM 3-D: K | tau | Td (s) | m_eff | custo | perfil: K | tau | m_eff | custo |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for c in r["paper_check"]:
            a, b = c["nm3"], c["profile"]
            L.append(f"| {c['dof']} | {a['K']:.4f} | {a['tau']:.4f} | {a['Td']:.4f} | {a['m_eff']} | {a['cost']:.3f} "
                     f"| {b['K']:.4f} | {b['tau']:.4f} | {b['m_eff']} | {b['cost']:.3f} |")
    for dof in d["dofs"]:
        t = d["theta_star"][dof]
        head = ("| regime | ruido | zona morta | ev (tr/ho) | masc. % (qq roda/DOF/todas) | K med [P25, P75] | vies K % "
                "| tau med [P25, P75] | vies tau % | m_eff med [P25, P75] | dTd (am.) | IQR(K)/K* % | fit ho % | fit tr % ")
        sep = "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"
        if physical:
            head += "| dev K % | dev tau % | dm (am.) | regime_bias | regime_bias_K "
            sep += "---|---|---|---|---|"
        if truth_known:
            head += "| escore | recuperado "
            sep += "---|---|"
        L += ["", f"## DOF {dof} (K* = {t['K']:.4f}, tau* = {t['tau']:.4f} s, Td*/Ts = {t['Td_samples']:.2f} amostras, "
              f"planta aplica {t['m_plant']})", "", head + "|", sep]
        for c in cells:
            if c["dof"] != dof:
                continue
            deg = f" ({c['n_degenerate']} degen.)" if c["n_degenerate"] else ""
            row = (f"| {c['regime']} | {c['noise']} | {c['deadzone']} | {c['n_events']} ({c['n_train']}/{c['n_holdout']}){deg} "
                   f"| {100 * c['masked_any']:.1f} / {100 * c['masked_dof']:.1f} / {100 * c['masked_clamped']:.1f} "
                   f"| {_f(c['K_med'], 4)} [{_f(c['K_p25'], 4)}, {_f(c['K_p75'], 4)}] | {_pct(c['bias_K'])} "
                   f"| {_f(c['tau_med'], 4)} [{_f(c['tau_p25'], 4)}, {_f(c['tau_p75'], 4)}] | {_pct(c['bias_tau'])} "
                   f"| {_f(c['m_eff_med'], 1)} [{_f(c['m_eff_p25'], 1)}, {_f(c['m_eff_p75'], 1)}] | {_f(c['dTd_samples'], 2)} "
                   f"| {_f(100 * c['iqr_K_rel'], 1) if np.isfinite(c['iqr_K_rel']) else 'nan'} "
                   f"| {_f(c['fit_holdout_med'], 1)} | {_f(c['fit_train_med'], 1)} ")
            if physical:
                row += (f"| {_pct(c['dev_K'])} | {_pct(c['dev_tau'])} | {_f(c['dm_eff'], 1)} | {_flag_bias(c)} "
                        f"| {_flag_bias_K(c)} ")
            if truth_known:
                row += f"| {c['score']} | {_flag(c)} "
            L.append(row + "|")
    for title, (noise, dz) in (("celula realista", d["realistic"]), ("celula idealizada", d["idealized"])):
        if noise not in d["noises"] or dz not in d["deadzones"]:
            continue
        if truth_known:
            what = "recuperado?"
        elif v2:
            what = f"regime_bias_K? (|dev K| > 10 % vs referencia {_ref_label(d)})"
        else:
            what = f"regime_bias? (dev K vs referencia {_ref_label(d)})"
        L += ["", f"## Resumo regime x DOF -> {what} ({title}: ruido `{noise}`, zona morta `{dz}`)", "",
              "| regime | " + " | ".join(d["dofs"]) + " |", "|---|" + "---|" * len(d["dofs"])]
        for regime in d["regimes"]:
            cs = [_find(cells, regime, dof, noise, dz) for dof in d["dofs"]]
            if truth_known:
                L.append(f"| {regime} | " + " | ".join(f"{_flag(c)} K {_pct(c['bias_K'])} %" if c else "-" for c in cs) + " |")
            elif v2:
                L.append(f"| {regime} | " + " | ".join(f"{_flag_bias_K(c)} dev K {_pct(c['dev_K'])} %" if c else "-"
                                                        for c in cs) + " |")
            else:
                L.append(f"| {regime} | " + " | ".join(f"{_flag_bias(c)} dev K {_pct(c['dev_K'])} %" if c else "-"
                                                        for c in cs) + " |")
    if "w" in d["dofs"]:
        extended = physical or "R1-wonly" in d["regimes"]
        L += ["", "## w: R1 (zona morta on/off) vs R1-wonly vs R2-rotate vs R2-square vs R3/R3-mild" if extended else
              "## w: R1 (zona morta on) vs R2-rotate", ""]
        if physical:
            L += [f"| celula | K med | dev K % | tau med | dev tau % | m_eff med | fit ho % | {'regime_bias_K' if v2 else 'regime_bias'} |",
                  "|---|---|---|---|---|---|---|---|"]
        else:
            L += ["| celula | K med | vies K % | tau med | vies tau % | m_eff med | fit ho % | escore |",
                  "|---|---|---|---|---|---|---|---|"]
        for regime in (("R1", "R1-wonly", "R2-rotate", "R2-square", "R3", "R3-mild") if extended else ("R1", "R2-rotate")):
            for dz in ("on", "off"):
                for noise in d["noises"]:
                    c = _find(cells, regime, "w", noise, dz)
                    if c is None:
                        continue
                    if physical:
                        L.append(f"| {regime} / {noise} / {dz} | {_f(c['K_med'], 4)} | {_pct(c['dev_K'])} | {_f(c['tau_med'], 4)} "
                                 f"| {_pct(c['dev_tau'])} | {_f(c['m_eff_med'], 1)} | {_f(c['fit_holdout_med'], 1)} "
                                 f"| {_flag_bias_K(c) if v2 else _flag_bias(c)} |")
                    else:
                        L.append(f"| {regime} / {noise} / {dz} | {_f(c['K_med'], 4)} | {_pct(c['bias_K'])} | {_f(c['tau_med'], 4)} "
                                 f"| {_pct(c['bias_tau'])} | {_f(c['m_eff_med'], 1)} | {_f(c['fit_holdout_med'], 1)} | {c['score']} |")
    L += ["", "## Leitura", ""]
    if physical and v2:
        L += _hypotheses_c1b_v2(r)
        L += ["", "Descritivo (nao entra no veredito v2): dev tau e dm_eff por celula nas tabelas acima; a bandeira",
              "composta regime_bias de v1 e mantida so para comparacao."]
    elif physical:
        L += _hypotheses_c1b(r)
        L += ["", "Leitura geral (C1b): para cada DOF fixo, compare regime_bias entre R1, R1-wonly, R2-rotate e R3.",
              "Se o desvio de K_w aparece em R1 e some em R1-wonly (mesmos comandos de w, sem translacao), o",
              "mecanismo e o acoplamento translacao -> guinada do modelo fisico, correlacionado com os comandos",
              "de w da estrategia; se aparece tambem em R1-wonly, vem do conteudo dos comandos de w; se nao",
              "aparece em lugar nenhum, o modelo fisico como entregue nao reproduz a inflacao de malha fechada",
              "(K_w ~ 1.38 do artigo). O desvio da referencia R3 em relacao a theta* (tabela acima) e a distancia",
              "entre o modelo fisico e o gemeo P1D no regime projetado, nao um erro do estimador."]
    else:
        L += _hypotheses(r)
        L += _fit_gate_reading(cells)
        L += ["", "Leitura geral: para cada DOF fixo, compare o escore entre regimes (o que muda e a excitacao, nao o",
              "DOF); em R3 (excitacao projetada dos tres DOFs) os tres DOFs devem ser recuperados. Celulas",
              "'degeneradas' (comando de treino com variancia nula, ex. vx/vy em `rotate`) nao tem ajuste: sem",
              "excitacao nao ha identificabilidade, qualquer que seja o DOF. O gerador e o gemeo linear sem",
              "escorregamento nem realimentacao: R1 in-silico mede apenas o conteudo informacional dos comandos",
              "de competicao (mais ruido e zona morta), nao o mecanismo de diluicao/realimentacao do artigo.",
              "Td: a planta aplica ceil(Td*/Ts) amostras; o estimador legacy devolve m_eff = m - 1, comparavel",
              "com Td*/Ts; o Td* continuo nao e recuperavel abaixo dessa quantizacao (criterio de 1 amostra)."]
    return L


def _jsonable(o):
    """Recursively convert numpy scalars/arrays and non-finite floats (-> null) for ``json.dump``."""
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return _jsonable(o.tolist())
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return float(o) if math.isfinite(float(o)) else None
    return o


def run(root: Path | None = None, out: Path | None = None, *, n_rep: int | None = None,
        regimes: Sequence[str] | str | None = None, noises: Sequence[str] | str | None = None,
        deadzones: Sequence[str] | str | None = None, dofs: Sequence[str] | str | None = None,
        seed: int = SEED, align: str = "legacy", m_max: int = M_MAX, nm_maxiter: int | None = None,
        paper_check: bool = True, generator: str = "fopdt", generator_opts: dict | str | None = None,
        reference_cell: Any = None, variant: str = "v1", note: str | None = None, quiet: bool = False,
        **kw) -> dict:
    """Run the experiment and write ``identifiability_insilico[_<generator>]_<stamp>.{md,csv,json}``
    into ``out`` (the generator is part of the file name for the MuJoCo generators, C1b).

    ``n_rep`` defaults to the pre-registered value of the generator (20 for ``fopdt``, 12 for the
    MuJoCo generators). Quick runs: ``regimes="R3"``, ``noises="none"``, ``deadzones="off"``,
    ``dofs="w"``, ``n_rep=1``. ``generator_opts`` (dict or JSON string) are world options of the
    MuJoCo generator (e.g. ``force_max``). ``variant="v2"`` selects the C1b-v2 re-registration
    (K-only rule, references ``"v2"`` = R2-rotate for w / R2-square for vx, vy, artefact stem
    ``identifiability_insilico_<generator>_v2``; pass ``regimes`` including ``R3-mild``).
    ``reference_cell`` (``"v1"``, ``"v2"``, ``"regime,noise,dz"`` or a JSON dict per DOF) overrides
    the variant's pre-registered references for an exploratory reading - flagged in the report.
    ``note`` is printed in the report as a declared deviation (e.g. reduced ``n_rep``).
    """
    ctx = C.make_context(root, out, seed=seed)
    if generator not in GENERATORS:
        raise ValueError(f"unknown generator {generator!r}; known: {', '.join(GENERATORS)}")
    if generator != "fopdt":
        import importlib.util

        if importlib.util.find_spec("mujoco") is None:
            raise ImportError(f"generator {generator!r} needs the 'mujoco' package: pip install dtssl[mujoco]")
    if isinstance(generator_opts, str):
        generator_opts = json.loads(generator_opts) if generator_opts.strip() else None
    regs, nzs, dzs, dfs = (_as_tuple(regimes, REGIMES), _as_tuple(noises, tuple(NOISES)),
                           _as_tuple(deadzones, DEADZONES), _as_tuple(dofs, DOFS))
    for reg in regs:
        regime_label(reg, "w")                  # KeyError for an unknown regime
    for nz in nzs:
        if nz not in NOISES:
            raise ValueError(f"unknown noise level {nz!r}; known: {', '.join(NOISES)}")
    for dz in dzs:
        if dz not in DEADZONES:
            raise ValueError(f"deadzone must be one of {DEADZONES}, got {dz!r}")
    nm_options = dict(maxiter=int(nm_maxiter)) if nm_maxiter else None
    if variant not in VARIANTS:
        raise ValueError(f"variant must be one of {VARIANTS}, got {variant!r}")
    if isinstance(reference_cell, str) and reference_cell.strip().startswith("{"):
        reference_cell = json.loads(reference_cell)
    ref_cells = normalize_reference("v2" if (reference_cell is None and variant == "v2") else reference_cell, dfs)
    kind = reference_kind(ref_cells)
    if generator != "fopdt" and kind != variant:
        pre = "/".join(REFERENCE_CELL) if variant == "v1" else "; ".join(f"{k}: {'/'.join(v)}" for k, v in REFERENCE_V2.items())
        cur = "; ".join(f"{k}: {'/'.join(v)}" for k, v in ref_cells.items())
        note = (note + " | " if note else "") + f"referencia EXPLORATORIA ({cur}) em vez da pre-registrada {variant} ({pre}); leitura post-hoc"
    n_pre = N_REP if generator == "fopdt" else N_REP_MUJOCO
    n_rep = n_pre if n_rep is None else int(n_rep)
    if n_rep != n_pre and not note:
        note = f"n_rep = {n_rep} (pre-registrado: {n_pre})"
    r = compute(ctx, n_rep=int(n_rep), regimes=regs, noises=nzs, deadzones=dzs, dofs=dfs, seed=int(seed),
                align=align, m_max=int(m_max), nm_options=nm_options, paper_check=bool(paper_check),
                generator=generator, generator_opts=generator_opts, reference_cell=ref_cells, variant=variant,
                quiet=quiet)
    L = render(ctx, r, note=note)
    if variant == "v2":
        stem = f"{NAME}_{generator}_v2"
    else:
        stem = NAME if generator == "fopdt" else f"{NAME}_{generator}"
    p_md = ctx.write_text(stem, L)
    p_csv = ctx.out_path(stem, "csv")
    r["rows"].to_csv(p_csv, index=False)
    p_json = ctx.out_path(stem, "json")
    with open(p_json, "w", encoding="utf-8") as f:
        json.dump(_jsonable(dict(design=r["design"], cells=r["cells"], paper_check=r["paper_check"],
                                 runtime_s=r["runtime_s"], n_fits=r["n_fits"], note=note,
                                 artefacts=dict(md=p_md.name, csv=p_csv.name))), f, indent=1)
    r.update(path=p_md, csv=p_csv, json=p_json)
    if not quiet:
        print("\n".join(L))
        print(f"\nartefato: {p_md}\ncsv: {p_csv}\njson: {p_json}\nruntime: {r['runtime_s'] / 60:.1f} min")
    return r


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
