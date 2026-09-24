"""Coupled (MIMO) first-order check: do cross-command terms between vx, vy and w change what the
competition logs identify, with the same data and the same estimator as the per-DOF structure?

Answers reviewer R2 of the SBR/LARS 2026 paper ("joint or coupled identification, e.g. a MIMO
model") and tests on real data the mechanism that C1b demonstrated in silico (the closed-loop yaw
gain is inflated by translation-induced yaw that is correlated with the yaw commands).
Pre-registration: docs/PREREGISTRO_MIMO_CHECK_20260923.md (written before any run).

Model per output ``i`` on the uniform grid ``dt``, in the ``align="plant"`` convention of
``AnalyticFOPDTPlant`` (the command applied at step ``k-1`` produces the velocity at ``k``)::

    y_i[0] = measured y_i[0]
    y_i[k] = A_i y_i[k-1] + sum_j B_ij u_j[k-1-M_ij]          (u = 0 before the event start)

* ``diagonal`` arm: ``B_ij = 0`` for ``i != j``; this is exactly the per-DOF FOPDT structure
  (``A = exp(-dt/tau)``, ``B_ii = K (1 - A)``), re-estimated on the same events;
* ``coupled`` arm: full ``B`` (3 x 3), one pole per output;
* ``promoted`` arm: the official theta (``config/twin_params.json``) on the same grid, the anchor of
  the published numbers.

Estimator (both arms; output error, i.e. the simulation error that Eq. (2) of the paper scores): for a
fixed pole ``A`` the simulated output is linear in the row of ``B``, so ``B`` is the least-squares
solution and ``A`` is a scalar search (log-spaced tau grid 5 ms to 1 s, then bounded Brent refinement
in log tau around the best grid point). Separable least squares; deterministic. Primary run: delays
fixed at the promoted plant delays ``m_i = ceil(Td_i/dt)`` for every input of row ``i`` (item B3 of the
camera-ready plan). Secondary run (``pair_delays``): the delays of each row searched exhaustively in
``0..M_MAX`` samples (the diagonal arm's own delay searched the same way), then Brent on the pole.

Data: the 46 competition events (labels front_to_back, side_to_side, shoot_to_goal, square) with the
paper's identification pre-processing (``common.legacy_uy_series``: linear command interpolation,
Savitzky-Golay 7/2 + central differences, world -> body rotation, positions mm -> m); hold-out = the
10 frozen events of ``config/holdout_events.json``; train = the other 36.

Reported: pooled hold-out fit per DOF (Eq. (2) over the concatenated hold-out samples, deviations from
each event's own mean), per-event fits, static gains ``G = B/(1-A)``, cross-contribution ratio per
output (RMS of the cross terms over RMS of the direct term, hold-out), a bootstrap over training
events (percentile 95 % intervals, delays held at the full-sample values) and, with ``harness=True``,
per-event ``e_pos`` medians in the paper's free-run harness for the refitted plants
(:class:`CoupledFirstOrderPlant`) on the same windows as every other number of the paper.

In-silico controls (``control=fopdt`` / ``control=mujoco-rollers-delay``): the same pipeline on
synthetic logs generated from the logged commands by the promoted twin (no coupling: negative
control) or by the untuned MuJoCo route b with the identified delay (the translation -> yaw coupling of
C1b: positive control), noise-free as the idealized cell of C1b; the yaw reference of a control is the
same diagonal estimator on the generator's response to the dedicated rotation events.

Does NOT touch config/twin_params.json nor any promoted model.
"""
from __future__ import annotations

import csv
import json
import math
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.signal import lfilter

from dtssl.analysis import common as C
from dtssl.eval.stats import rank_biserial, wilcoxon_less
from dtssl.models import DOFS, AnalyticFOPDTPlant, DofParam, Plant

NAME = "coupled_mimo_check"
KIND = "analysis"
CLAIM = "Cross-coupling check (R2): coupled 3x3 first-order model vs per-DOF on the frozen hold-out"
REQUIRES = ("data",)
SEED = 42
LABELS = ("front_to_back", "side_to_side", "shoot_to_goal", "square")
STG_LABEL = "shoot_to_goal"          # M2 sensitivity: yaw fitted on the game label only
POS_SCALE = 1e-3                     # logged mm -> m (as loo_translational / identifiability_insilico)
MIN_LEN = 60
TAU_GRID = tuple(float(x) for x in np.geomspace(0.005, 1.0, 121))
M_MAX = 10                           # pair-delay search: 0..10 samples (0 to 0.167 s)
N_BOOT = 200                         # bootstrap replicates over training events
ROTATE_LINEAR = tuple(f"rotate_01_{k:02d}" for k in range(5, 11))   # +-1, +-2.5, +-5 rad/s (D9 split)
CONTROLS = ("fopdt", "mujoco-rollers-delay", "mujoco-rollers")
# --- pre-registered decision rules (docs/PREREGISTRO_MIMO_CHECK_20260923.md) ---------------------
FIT_GAIN_MIN_PP = 3.0                # M1: pooled hold-out fit gain of the coupled arm on some DOF ...
CONTRIB_MIN = 0.10                   # ... AND cross/direct contribution ratio >= 0.10 on the same DOF
M2_INFLATION_MIN = 0.10              # M2 premise: diagonal yaw gain >= (1 + 10 %) x reference
M2_REDUCTION_MIN = 0.50              # M2: the coupled arm removes >= 50 % of the diagonal excess
HARNESS_GATE = dict(wins=8, p=0.05, rb=0.5)   # M3: coupled beats diagonal in the harness (per event)
NEG_CONTROL_TOL = 0.05               # C-: |G_ww - truth| / truth <= 5 % in both arms


# =========================================================================
# model container and simulation
# =========================================================================
def _tau_of(a: float) -> float:
    if a >= 1.0:
        return float("inf")
    return float(-1.0 / math.log(a)) if a > 0.0 else 0.0


@dataclass
class MimoModel:
    """``y_i[k] = A_i y_i[k-1] + sum_j B_ij u_j[k-1-M_ij]`` (plant alignment, grid ``dt``)."""
    A: np.ndarray                    # (3,)
    B: np.ndarray                    # (3, 3) row = output, column = input
    M: np.ndarray                    # (3, 3) integer delays in samples
    coupled: bool
    dt: float
    sse: np.ndarray = field(default_factory=lambda: np.zeros(3))   # training SSE per row

    @property
    def tau(self) -> np.ndarray:
        """Time constant per row (s): ``A = exp(-dt/tau)``."""
        return np.array([_tau_of(float(a)) * self.dt for a in self.A])

    @property
    def G(self) -> np.ndarray:
        """Static gains ``B_ij / (1 - A_i)`` (output units per input unit)."""
        return self.B / (1.0 - self.A)[:, None]

    def to_json(self) -> dict:
        return dict(A=self.A.tolist(), B=self.B.tolist(), M=self.M.astype(int).tolist(),
                    tau_s=self.tau.tolist(), G=self.G.tolist(), coupled=self.coupled, dt=self.dt,
                    sse=np.asarray(self.sse, float).tolist())


def plant_delays(params: dict[str, DofParam], dt: float) -> list[int]:
    """Delays of ``AnalyticFOPDTPlant`` (``ceil(Td/dt - 1e-9)``): 5 / 4 / 6 samples for the official theta."""
    return [0 if params[d].Td <= 0 else int(math.ceil(params[d].Td / dt - 1e-9)) for d in DOFS]


def shift(u: np.ndarray, m: int) -> np.ndarray:
    """``u[k - m]`` with zeros before the start (``m >= 0``)."""
    u = np.asarray(u, dtype=float)
    out = np.zeros_like(u)
    if m == 0:
        out[:] = u
    elif 0 < m < u.size:
        out[m:] = u[:u.size - m]
    return out


def filtered(u: np.ndarray, A: float, m: int) -> np.ndarray:
    """Unit-``B`` response of one input: ``psi[0] = 0``, ``psi[k] = A psi[k-1] + u[k-1-m]``."""
    return lfilter([1.0], [1.0, -A], shift(u, m + 1))


def simulate(model: MimoModel, U: np.ndarray, y0: np.ndarray) -> np.ndarray:
    """Free-run velocity (N, 3) of ``model`` driven by ``U`` (N, 3) from ``y0`` (the first sample)."""
    U = np.asarray(U, dtype=float)
    n = U.shape[0]
    Y = np.empty((n, 3))
    k = np.arange(n)
    for i in range(3):
        y = float(np.asarray(y0, float)[i]) * model.A[i] ** k
        for j in range(3):
            if model.B[i, j] != 0.0:
                y = y + model.B[i, j] * filtered(U[:, j], float(model.A[i]), int(model.M[i, j]))
        Y[:, i] = y
    return Y


def promoted_model(params: dict[str, DofParam], dt: float) -> MimoModel:
    """The official theta written as a diagonal :class:`MimoModel` (same recurrence as the plant)."""
    A = np.array([math.exp(-dt / params[d].tau) if params[d].tau > 0 else 0.0 for d in DOFS])
    B = np.diag([params[d].K * (1.0 - A[i]) for i, d in enumerate(DOFS)])
    m = plant_delays(params, dt)
    M = np.array([[m[i]] * 3 for i in range(3)], dtype=int)
    return MimoModel(A=A, B=B, M=M, coupled=False, dt=dt)


# =========================================================================
# estimator: separable least squares (output error)
# =========================================================================
Event = tuple[np.ndarray, np.ndarray]          # (U (N, 3), Y (N, 3))


def _row_problem(events: Sequence[Event], i: int, A: float, inputs: Sequence[int],
                 delays: Sequence[int]) -> tuple[np.ndarray, np.ndarray]:
    """Stacked regressors (N_total, len(inputs)) and free-response-corrected targets of row ``i``."""
    cols, rhs = [], []
    for U, Y in events:
        n = Y.shape[0]
        cols.append(np.column_stack([filtered(U[:, j], A, int(m)) for j, m in zip(inputs, delays, strict=True)]))
        rhs.append(Y[:, i] - Y[0, i] * A ** np.arange(n))
    return np.vstack(cols), np.concatenate(rhs)


def _lsq(Phi: np.ndarray, r: np.ndarray) -> tuple[np.ndarray, float]:
    b, *_ = np.linalg.lstsq(Phi, r, rcond=None)
    e = r - Phi @ b
    return b, float(e @ e)


def fit_row(events: Sequence[Event], i: int, inputs: Sequence[int], delays: Sequence[int], dt: float,
            tau_grid: Sequence[float] = TAU_GRID) -> tuple[float, np.ndarray, float]:
    """Output-error fit of row ``i`` with fixed ``delays``: returns ``(A, b, sse)``.

    Cost evaluated on the tau grid, then minimised by bounded Brent in ``log(tau)`` between the two
    neighbours of the best grid point (kept only if it improves on the grid)."""
    taus = np.asarray(tau_grid, dtype=float)

    def cost(t: float) -> float:
        return _lsq(*_row_problem(events, i, math.exp(-dt / t), inputs, delays))[1]

    grid = np.array([cost(float(t)) for t in taus])
    kb = int(np.argmin(grid))
    t_best, c_best = float(taus[kb]), float(grid[kb])
    lo, hi = math.log(taus[max(kb - 1, 0)]), math.log(taus[min(kb + 1, taus.size - 1)])
    if hi > lo:
        res = minimize_scalar(lambda lt: cost(math.exp(lt)), bounds=(lo, hi), method="bounded",
                              options=dict(xatol=1e-7))
        if float(res.fun) < c_best:
            t_best = float(math.exp(res.x))
    A = math.exp(-dt / t_best)
    b, sse = _lsq(*_row_problem(events, i, A, inputs, delays))
    return A, b, sse


def fit_model(events: Sequence[Event], dt: float, delays: Sequence[Sequence[int]], coupled: bool,
              tau_grid: Sequence[float] = TAU_GRID) -> MimoModel:
    """Fit both arms' structure with the delay matrix ``delays`` (3 x 3; only the used entries matter)."""
    Md = np.asarray(delays, dtype=int).reshape(3, 3)
    A = np.zeros(3)
    B = np.zeros((3, 3))
    sse = np.zeros(3)
    for i in range(3):
        inputs = (0, 1, 2) if coupled else (i,)
        a, b, s = fit_row(events, i, inputs, [Md[i, j] for j in inputs], dt, tau_grid)
        A[i], sse[i] = a, s
        for j, bj in zip(inputs, b, strict=True):
            B[i, j] = bj
    return MimoModel(A=A, B=B, M=Md.copy(), coupled=coupled, dt=dt, sse=sse)


def search_pair_delays(events: Sequence[Event], dt: float, coupled: bool, m_max: int = M_MAX,
                       tau_grid: Sequence[float] = TAU_GRID) -> MimoModel:
    """Exhaustive integer delays per row (``0..m_max`` for each used input) on the tau grid, by the
    normal equations of the precomputed delayed columns; then :func:`fit_row` (Brent on the pole)
    at the selected delays. Unused entries of ``M`` keep the row's direct delay."""
    import itertools

    taus = np.asarray(tau_grid, dtype=float)
    Md = np.zeros((3, 3), dtype=int)
    for i in range(3):
        inputs = (0, 1, 2) if coupled else (i,)
        best = (math.inf, None)
        for t in taus:
            A = math.exp(-dt / t)
            cols, rhs = {}, []
            for _U, Y in events:
                n = Y.shape[0]
                rhs.append(Y[:, i] - Y[0, i] * A ** np.arange(n))
            r = np.concatenate(rhs)
            for j in inputs:
                base = [filtered(U[:, j], A, 0) for U, _ in events]
                for m in range(m_max + 1):
                    cols[(j, m)] = np.concatenate([shift(b, m) for b in base])
            keys = list(cols)
            X = np.column_stack([cols[k] for k in keys])
            G = X.T @ X
            g = X.T @ r
            rr = float(r @ r)
            idx = {k: n for n, k in enumerate(keys)}
            for combo in itertools.product(range(m_max + 1), repeat=len(inputs)):
                sel = [idx[(j, m)] for j, m in zip(inputs, combo, strict=True)]
                Gs = G[np.ix_(sel, sel)]
                gs = g[sel]
                try:
                    b = np.linalg.solve(Gs, gs)
                except np.linalg.LinAlgError:
                    continue
                c = rr - float(b @ gs)
                if c < best[0]:
                    best = (c, combo)
        combo = best[1]
        direct = combo[inputs.index(i)]
        Md[i, :] = direct
        for j, m in zip(inputs, combo, strict=True):
            Md[i, j] = m
    return fit_model(events, dt, Md, coupled, tau_grid)


# =========================================================================
# scoring
# =========================================================================
def pooled_fit(ys: Sequence[np.ndarray], yhats: Sequence[np.ndarray]) -> float:
    """Eq. (2) over concatenated events, deviations from each event's own mean."""
    num = sum(float(np.sum((y - yh) ** 2)) for y, yh in zip(ys, yhats, strict=True))
    den = sum(float(np.sum((y - np.mean(y)) ** 2)) for y in ys)
    return float(100.0 * (1.0 - math.sqrt(num) / math.sqrt(den))) if den > 0 else float("nan")


def contribution_ratios(model: MimoModel, events: Sequence[Event]) -> dict[str, Any]:
    """Per output: RMS of each cross term and of their sum, over the RMS of the direct term."""
    out: dict[str, Any] = {}
    for i, d in enumerate(DOFS):
        direct, cross = [], {j: [] for j in range(3) if j != i}
        for U, _ in events:
            direct.append(model.B[i, i] * filtered(U[:, i], float(model.A[i]), int(model.M[i, i])))
            for j in cross:
                cross[j].append(model.B[i, j] * filtered(U[:, j], float(model.A[i]), int(model.M[i, j])))
        dr = np.concatenate(direct)
        rms_d = float(np.sqrt(np.mean(dr ** 2)))
        csum = sum(np.concatenate(v) for v in cross.values())
        per = {DOFS[j]: (float(np.sqrt(np.mean(np.concatenate(v) ** 2))) / rms_d if rms_d > 0 else float("nan"))
               for j, v in cross.items()}
        out[d] = dict(total=(float(np.sqrt(np.mean(csum ** 2))) / rms_d if rms_d > 0 else float("nan")),
                      per_input=per, rms_direct=rms_d)
    return out


def score(models: dict[str, MimoModel], test: Sequence[dict]) -> dict[str, Any]:
    """Per-event and pooled hold-out fits of every arm; ``test`` items carry ``U``, ``Y``, names."""
    per_event, pooled = [], {}
    sims = {k: [simulate(m, e["U"], e["Y"][0]) for e in test] for k, m in models.items()}
    for n, e in enumerate(test):
        row = dict(label=e["label"], event=e["event"], n=int(e["Y"].shape[0]))
        for k in models:
            for i, d in enumerate(DOFS):
                row[f"{k}_{d}"] = C.fit_percent(e["Y"][:, i], sims[k][n][:, i])
        per_event.append(row)
    for k in models:
        pooled[k] = {d: pooled_fit([e["Y"][:, i] for e in test], [s[:, i] for s in sims[k]])
                     for i, d in enumerate(DOFS)}
    mean = {k: {d: float(np.mean([r[f"{k}_{d}"] for r in per_event])) for d in DOFS} for k in models}
    return dict(per_event=per_event, pooled=pooled, mean=mean)


# =========================================================================
# decision rules
# =========================================================================
def verdict_m1(pooled: dict[str, dict[str, float]], ratios: dict[str, Any]) -> dict[str, Any]:
    """M1 (primary): coupling matters iff on some DOF the coupled arm gains >= FIT_GAIN_MIN_PP p.p. of
    pooled hold-out fit over the diagonal arm AND its cross/direct contribution ratio is >= CONTRIB_MIN."""
    per = {}
    for d in DOFS:
        gain = pooled["coupled"][d] - pooled["diagonal"][d]
        ratio = ratios[d]["total"]
        per[d] = dict(fit_gain_pp=gain, contrib_ratio=ratio,
                      matters=bool(gain >= FIT_GAIN_MIN_PP and ratio >= CONTRIB_MIN))
    return dict(per_dof=per, coupling_matters=any(v["matters"] for v in per.values()))


def verdict_m2(G_diag_w: float, G_coupled_w: float, K_ref: float) -> dict[str, Any]:
    """M2 (mechanism): with the diagonal yaw gain inflated by >= M2_INFLATION_MIN over ``K_ref`` (the
    premise), the coupled arm must remove >= M2_REDUCTION_MIN of the excess."""
    excess_d = G_diag_w - K_ref
    excess_c = G_coupled_w - K_ref
    premise = bool(excess_d >= M2_INFLATION_MIN * K_ref)
    removed = (1.0 - abs(excess_c) / abs(excess_d)) if excess_d != 0 else float("nan")
    if not premise:
        status = "nao testavel (premissa nao reproduzida)"
    elif abs(excess_c) <= (1.0 - M2_REDUCTION_MIN) * abs(excess_d):
        status = "CORROBORADA"
    else:
        status = "FALSIFICADA"
    return dict(K_ref=K_ref, G_diag=G_diag_w, G_coupled=G_coupled_w, inflation_diag=excess_d / K_ref,
                inflation_coupled=excess_c / K_ref, fraction_removed=removed, premise=premise, status=status)


def verdict_m3(ev_coupled: Sequence[float], ev_diag: Sequence[float]) -> dict[str, Any]:
    """M3: coupled beats diagonal in the harness per event (>= 8/10 wins, p < 0.05, rb >= 0.5)."""
    a, b = np.asarray(ev_coupled, float), np.asarray(ev_diag, float)
    wins = int(np.sum(a < b))
    p = wilcoxon_less(a, b)
    rb = rank_biserial(b, a)
    ok = bool(wins >= HARNESS_GATE["wins"] and p < HARNESS_GATE["p"] and rb >= HARNESS_GATE["rb"])
    return dict(wins=wins, n=int(a.size), p=p, rb=rb, improves=ok)


# =========================================================================
# harness plant
# =========================================================================
class CoupledFirstOrderPlant(Plant):
    """:class:`MimoModel` as a harness ``Plant``: same recurrence as :func:`simulate` and the same
    trapezoidal pose integration as ``AnalyticFOPDTPlant``. ``params`` (the official theta) only fixes
    the window grid of the harness; the dynamics are the model's."""

    def __init__(self, model: MimoModel, params: dict[str, DofParam] | None = None):
        self.model = model
        self.params = params
        self._A = np.asarray(model.A, float).reshape(3)
        self._B = np.asarray(model.B, float).reshape(3, 3)
        self._M = np.asarray(model.M, int).reshape(3, 3)

    def reset(self, pose0, velb0=(0.0, 0.0, 0.0)) -> None:
        self.x, self.y, self.th = (float(v) for v in pose0)
        vb = np.asarray(velb0, dtype=float).reshape(3)
        self._vbody = vb.copy()
        c, s = math.cos(self.th), math.sin(self.th)
        self._gx_prev = c * vb[0] - s * vb[1]
        self._gy_prev = s * vb[0] + c * vb[1]
        self._vw_prev = float(vb[2])
        self._hist: list[np.ndarray] = []
        self._base = 0
        self._k = 0

    def prime_delay(self, prev_cmds) -> None:
        self._hist = [np.asarray(c, dtype=float).reshape(3) for c in prev_cmds]
        self._base = len(self._hist)

    def step(self, cmd, dt: float):
        j = self._k
        self._hist.append(np.asarray(cmd, dtype=float).reshape(3))
        v_new = np.empty(3)
        for i in range(3):
            acc = self._A[i] * self._vbody[i]
            for q in range(3):
                if self._B[i, q] == 0.0:
                    continue
                pos = j - int(self._M[i, q]) + self._base
                if 0 <= pos < len(self._hist):
                    acc += self._B[i, q] * self._hist[pos][q]
            v_new[i] = acc
        th_new = self.th + 0.5 * dt * (v_new[2] + self._vw_prev)
        c, s = math.cos(th_new), math.sin(th_new)
        gx = c * v_new[0] - s * v_new[1]
        gy = s * v_new[0] + c * v_new[1]
        self.x += 0.5 * dt * (gx + self._gx_prev)
        self.y += 0.5 * dt * (gy + self._gy_prev)
        self.th = th_new
        self._vbody = v_new
        self._gx_prev, self._gy_prev, self._vw_prev = gx, gy, float(v_new[2])
        self._k = j + 1
        return (self.x, self.y, self.th)


# =========================================================================
# data
# =========================================================================
def event_series(cmd, rob, dt: float, min_len: int = MIN_LEN) -> tuple[np.ndarray, np.ndarray] | None:
    """``(U, Y)`` (N, 3) on the shared legacy grid of one event, or ``None`` if too short."""
    cols = []
    for d in DOFS:
        s = C.legacy_uy_series(cmd, rob, d, dt, min_len=min_len, pos_scale=POS_SCALE)
        if s is None:
            return None
        cols.append(s)
    n = min(u.size for u, _ in cols)
    return (np.column_stack([u[:n] for u, _ in cols]), np.column_stack([y[:n] for _, y in cols]))


def load_events(ctx: C.Ctx, labels: Sequence[str] = LABELS, min_len: int = MIN_LEN) -> list[dict]:
    """Every competition event of ``labels`` with its (U, Y) and the hold-out flag."""
    ho = {(e["label"], e["event"]) for e in ctx.holdout_cfg["events"]}
    out = []
    for label in labels:
        for ev in C.list_events(ctx.splits_dir, label):
            cmd, rob = C.read_event_csv(label, ev, dataset=ctx.dataset, data_root=ctx.data_root)
            s = event_series(cmd, rob, ctx.ts, min_len)
            if s is not None:
                out.append(dict(label=label, event=ev, U=s[0], Y=s[1], holdout=(label, ev) in ho))
    return out


def control_events(ctx: C.Ctx, generator: str, labels: Sequence[str] = LABELS, *,
                   noise: tuple[float, float] = (0.0, 0.0), seed: int = SEED,
                   events: Sequence[str] | None = None) -> list[dict]:
    """Synthetic logs: the logged commands of ``labels`` replayed through ``generator`` from rest,
    through the C1 measurement chain (optional Gaussian noise, mm / rad) and the same (U, Y) extraction."""
    from dtssl.analysis import identifiability_insilico as II

    ho = {(e["label"], e["event"]) for e in ctx.holdout_cfg["events"]}
    plant = II.make_generator(generator, ctx.params, False)
    rng = np.random.default_rng(seed)
    out = []
    try:
        for label in labels:
            for ev in II.dataset_events(ctx, label):
                if events is not None and ev.name not in events:
                    continue
                pose = II.simulate_poses_plant(plant, ev, ctx.ts)
                z = rng.standard_normal((ev.n, 3)) if (noise[0] > 0 or noise[1] > 0) else None
                cmd_df, rob_df = II.measurement_tables(ev, pose, noise[0], noise[1], z)
                s = event_series(cmd_df, rob_df, ctx.ts)
                if s is not None:
                    out.append(dict(label=label, event=ev.name, U=s[0], Y=s[1], holdout=(label, ev.name) in ho))
    finally:
        if hasattr(plant, "close"):
            plant.close()
    return out


# =========================================================================
# core computation (pure: testable without the dataset)
# =========================================================================
def _uy(items: Sequence[dict]) -> list[Event]:
    return [(e["U"], e["Y"]) for e in items]


def fit_arms(train: Sequence[dict], params: dict[str, DofParam], dt: float, *, pair_delays: bool = False,
             tau_grid: Sequence[float] = TAU_GRID, m_max: int = M_MAX) -> dict[str, MimoModel]:
    """``diagonal`` and ``coupled`` fits on ``train`` (+ the ``promoted`` anchor)."""
    ev = _uy(train)
    if pair_delays:
        diag = search_pair_delays(ev, dt, False, m_max, tau_grid)
        coup = search_pair_delays(ev, dt, True, m_max, tau_grid)
    else:
        m = plant_delays(params, dt)
        Md = [[m[i]] * 3 for i in range(3)]
        diag = fit_model(ev, dt, Md, False, tau_grid)
        coup = fit_model(ev, dt, Md, True, tau_grid)
    return dict(promoted=promoted_model(params, dt), diagonal=diag, coupled=coup)


def bootstrap(train: Sequence[dict], test: Sequence[dict], models: dict[str, MimoModel], dt: float, *,
              n_boot: int = N_BOOT, seed: int = SEED, tau_grid: Sequence[float] = TAU_GRID) -> dict[str, Any]:
    """Event-level bootstrap of the training set (delays held at the full-sample fits): percentile 95 %
    intervals of the yaw gains of both arms, the pooled fit gain per DOF and the contribution ratios."""
    rng = np.random.default_rng(seed)
    n = len(train)
    rec: dict[str, list[float]] = {k: [] for k in
                                   ["G_diag_w", "G_coupled_w", *(f"gain_{d}" for d in DOFS),
                                    *(f"ratio_{d}" for d in DOFS)]}
    test_ev = _uy(test)
    for _ in range(int(n_boot)):
        idx = rng.integers(0, n, n)
        ev = [(train[k]["U"], train[k]["Y"]) for k in idx]
        d = fit_model(ev, dt, models["diagonal"].M, False, tau_grid)
        c = fit_model(ev, dt, models["coupled"].M, True, tau_grid)
        rec["G_diag_w"].append(float(d.G[2, 2]))
        rec["G_coupled_w"].append(float(c.G[2, 2]))
        sd = [simulate(d, U, Y[0]) for U, Y in test_ev]
        sc = [simulate(c, U, Y[0]) for U, Y in test_ev]
        rat = contribution_ratios(c, test_ev)
        for i, dof in enumerate(DOFS):
            ys = [Y[:, i] for _, Y in test_ev]
            rec[f"gain_{dof}"].append(pooled_fit(ys, [s[:, i] for s in sc]) - pooled_fit(ys, [s[:, i] for s in sd]))
            rec[f"ratio_{dof}"].append(rat[dof]["total"])
    ci = {k: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for k, v in rec.items()}
    return dict(n_boot=int(n_boot), seed=int(seed), ci95=ci)


def compute_from_series(items: Sequence[dict], params: dict[str, DofParam], dt: float, *,
                        K_ref_w: float | None = None, pair_delays: bool = True, n_boot: int = N_BOOT,
                        seed: int = SEED, stg_sensitivity: bool = True,
                        tau_grid: Sequence[float] = TAU_GRID, m_max: int = M_MAX) -> dict[str, Any]:
    """Everything except the harness, from (U, Y) event dicts (``holdout`` flag splits train/test)."""
    train = [e for e in items if not e["holdout"]]
    test = [e for e in items if e["holdout"]]
    if not train or not test:
        raise ValueError(f"need train and hold-out events (got {len(train)} / {len(test)})")
    K_ref = float(params["w"].K if K_ref_w is None else K_ref_w)
    t0 = time.perf_counter()
    models = fit_arms(train, params, dt, tau_grid=tau_grid)
    sc = score(models, test)
    ratios = contribution_ratios(models["coupled"], _uy(test))
    out: dict[str, Any] = dict(
        n_train=len(train), n_test=len(test), dt=dt, K_ref_w=K_ref,
        train_events=[f"{e['label']}/{e['event']}" for e in train],
        test_events=[f"{e['label']}/{e['event']}" for e in test],
        models={k: m.to_json() for k, m in models.items()}, score=sc, ratios=ratios,
        m1=verdict_m1(sc["pooled"], ratios),
        m2=verdict_m2(float(models["diagonal"].G[2, 2]), float(models["coupled"].G[2, 2]), K_ref),
        _models=models)
    if stg_sensitivity:
        stg = [e for e in train if e["label"] == STG_LABEL]
        if stg:
            ms = fit_arms(stg, params, dt, tau_grid=tau_grid)
            out["m2_stg_only"] = dict(n_train=len(stg), **verdict_m2(float(ms["diagonal"].G[2, 2]),
                                                                     float(ms["coupled"].G[2, 2]), K_ref))
    if pair_delays:
        mp = fit_arms(train, params, dt, pair_delays=True, tau_grid=tau_grid, m_max=m_max)
        scp = score(mp, test)
        rp = contribution_ratios(mp["coupled"], _uy(test))
        out["pair_delays"] = dict(models={k: m.to_json() for k, m in mp.items()}, score=scp, ratios=rp,
                                  m1=verdict_m1(scp["pooled"], rp),
                                  m2=verdict_m2(float(mp["diagonal"].G[2, 2]), float(mp["coupled"].G[2, 2]),
                                                K_ref))
    if n_boot and n_boot > 0:
        out["bootstrap"] = bootstrap(train, test, models, dt, n_boot=n_boot, seed=seed, tau_grid=tau_grid)
    out["cost_s"] = time.perf_counter() - t0
    return out


def harness_eval(ctx: C.Ctx, models: dict[str, MimoModel]) -> dict[str, Any]:
    """Per-event e_pos / e_ang medians at h_ref in the paper's free-run harness (translation bin) for
    the promoted twin and the refitted diagonal and coupled plants; the same windows as the paper."""
    segs, dropped = ctx.holdout()
    P, H = ctx.params, ctx.horizons
    h_ref = int(ctx.mcfg["verdict"]["h_ref"])
    k = H.index(h_ref)
    ros = {"promoted": C.ros(segs, lambda: AnalyticFOPDTPlant(P), horizons=H)}
    for name in ("diagonal", "coupled"):
        ros[name] = C.ros(segs, lambda name=name: CoupledFirstOrderPlant(models[name], P), horizons=H)
    T_dc = C.paired_table(ctx, ros["diagonal"], ros["coupled"])      # epos_twin = diagonal, epos_def = coupled
    T_pc = C.paired_table(ctx, ros["promoted"], ros["coupled"])      # epos_twin = promoted
    m = C.trans_mask(T_dc)
    if not np.array_equal(m, C.trans_mask(T_pc)) or not np.array_equal(T_dc.t0, T_pc.t0):
        raise RuntimeError("harness tables disagree on windows/bins (same grid expected)")
    ev_d, ev_c, ids = C.per_event_medians(T_dc, k, m)
    ev_p, _, _ = C.per_event_medians(T_pc, k, m)
    rows = []
    for kk, h in enumerate(H):
        rows.append(dict(h_s=float(h * T_dc.ts),
                         epos=dict(promoted=float(np.median(T_pc.epos_twin[m, kk])),
                                   diagonal=float(np.median(T_dc.epos_twin[m, kk])),
                                   coupled=float(np.median(T_dc.epos_def[m, kk]))),
                         eang=dict(promoted=float(np.median(T_pc.eang_twin[m, kk])),
                                   diagonal=float(np.median(T_dc.eang_twin[m, kk])),
                                   coupled=float(np.median(T_dc.eang_def[m, kk])))))
    return dict(h_ref=h_ref, h_ref_s=float(h_ref * T_dc.ts), n_windows=int(T_dc.W), n_trans=int(m.sum()),
                events=[s.meta.get("event") for s in segs], dropped=dropped, rows=rows,
                per_event=[dict(event=segs[i].meta.get("event"), promoted=float(p), diagonal=float(d),
                                coupled=float(c)) for i, p, d, c in zip(ids, ev_p, ev_d, ev_c, strict=True)],
                m3=verdict_m3(ev_c, ev_d),
                coupled_vs_promoted=verdict_m3(ev_c, ev_p),
                diagonal_vs_promoted=verdict_m3(ev_d, ev_p),
                sanity_promoted_event_median=float(np.median(ev_p)))


def control_reference(ctx: C.Ctx, generator: str, dt: float, noise=(0.0, 0.0), seed: int = SEED) -> float:
    """Yaw gain of the diagonal estimator on the generator's response to the dedicated rotation events
    (``ROTATE_LINEAR``, all used for fitting): the open-loop reference of a control run."""
    items = control_events(ctx, generator, ("rotate",), noise=noise, seed=seed, events=ROTATE_LINEAR)
    if not items:
        raise RuntimeError("no rotate events for the control reference")
    m = plant_delays(ctx.params, dt)
    A, b, _ = fit_row(_uy(items), 2, (2,), (m[2],), dt)
    return float(b[0] / (1.0 - A))


def compute(ctx: C.Ctx, *, control: str | None = None, pair_delays: bool = True, n_boot: int = N_BOOT,
            seed: int = SEED, do_harness: bool = True, stg_sensitivity: bool = True) -> dict[str, Any]:
    dt = ctx.ts
    t0 = time.perf_counter()
    if control is None:
        items = load_events(ctx)
        K_ref = float(ctx.params["w"].K)
        ref_src = "theta oficial (identificacao dedicada em malha aberta, config/twin_params.json)"
    else:
        if control not in CONTROLS:
            raise ValueError(f"unknown control {control!r}; known: {', '.join(CONTROLS)}")
        items = control_events(ctx, control)
        K_ref = control_reference(ctx, control, dt)
        ref_src = f"estimador diagonal na resposta do gerador `{control}` aos eventos {ROTATE_LINEAR[0]}..{ROTATE_LINEAR[-1]}"
        do_harness = False
    load_s = time.perf_counter() - t0
    r = compute_from_series(items, ctx.params, dt, K_ref_w=K_ref, pair_delays=pair_delays, n_boot=n_boot,
                            seed=seed, stg_sensitivity=stg_sensitivity)
    r.update(control=control, K_ref_source=ref_src, load_s=load_s,
             labels=list(LABELS), delays_primary=plant_delays(ctx.params, dt))
    if control == "fopdt":
        G = {k: r["models"][k]["G"][2][2] for k in ("diagonal", "coupled")}
        r["negative_control"] = dict(truth=K_ref, G=G, ok=bool(
            all(abs(g - float(ctx.params["w"].K)) / float(ctx.params["w"].K) <= NEG_CONTROL_TOL for g in G.values())
            and not r["m1"]["coupling_matters"]))
    if do_harness:
        t1 = time.perf_counter()
        r["harness"] = harness_eval(ctx, r["_models"])
        r["harness"]["cost_s"] = time.perf_counter() - t1
    return r


# =========================================================================
# rendering
# =========================================================================
def _f(v: float, nd: int = 3) -> str:
    return "nan" if v is None or (isinstance(v, float) and not math.isfinite(v)) else f"{v:.{nd}f}"


def _gain_table(mj: dict) -> list[str]:
    L = ["| saida \\ comando | vx | vy | w | tau (s) | atrasos (amostras) |", "|---|---|---|---|---|---|"]
    for i, d in enumerate(DOFS):
        g = mj["G"][i]
        L.append(f"| {d} | {_f(g[0])} | {_f(g[1])} | {_f(g[2])} | {_f(mj['tau_s'][i], 4)} | "
                 f"{'/'.join(str(x) for x in mj['M'][i])} |")
    return L


def render(ctx: C.Ctx, r: dict) -> list[str]:
    ctl = r.get("control")
    title = "Checagem MIMO: termos cruzados de comando vs. estrutura por DOF"
    if ctl:
        title += f" (CONTROLE in silico: gerador `{ctl}`)"
    L = C.result_header(title, ctx, generator=f"dtssl.analysis.{NAME}", seed=SEED,
                        extra=f"atrasos primarios {r['delays_primary']} amostras (ceil(Td/dt), alinhamento plant); "
                              "pre-registro docs/PREREGISTRO_MIMO_CHECK_20260923.md")
    L += [f"Eventos: treino {r['n_train']} / hold-out {r['n_test']} (config/holdout_events.json); rotulos "
          f"{', '.join(r['labels'])}; grade {r['dt']:.5f} s; referencia de yaw K_ref = {_f(r['K_ref_w'], 4)} "
          f"({r['K_ref_source']}).", ""]
    if ctl:
        L += ["**Controle in silico**: logs sinteticos gerados a partir dos comandos registrados; nenhum numero "
              "deste arquivo e do robo real.", ""]
    sc = r["score"]
    L += ["## 1. Fit de hold-out (Eq. 2)", "",
          "| braco | vx pooled | vy pooled | w pooled | vx media ev. | vy media ev. | w media ev. |",
          "|---|---|---|---|---|---|---|"]
    for k in ("promoted", "diagonal", "coupled"):
        L.append(f"| {k} | " + " | ".join(f"{_f(sc['pooled'][k][d], 1)} %" for d in DOFS) + " | "
                 + " | ".join(f"{_f(sc['mean'][k][d], 1)} %" for d in DOFS) + " |")
    L += ["", "## 2. Ganhos estaticos G = B/(1-A) (linha = saida, coluna = comando)", "", "Diagonal:", ""]
    L += _gain_table(r["models"]["diagonal"])
    L += ["", "Acoplado:", ""] + _gain_table(r["models"]["coupled"])
    L += ["", "## 3. Contribuicao cruzada no hold-out (RMS cruzado / RMS direto, braco acoplado)", "",
          "| saida | total | " + " | ".join(f"de {d}" for d in DOFS) + " |", "|---|---|---|---|---|"]
    for d in DOFS:
        rr = r["ratios"][d]
        L.append(f"| {d} | {_f(rr['total'])} | " + " | ".join(
            _f(rr["per_input"][q]) if q in rr["per_input"] else "-" for q in DOFS) + " |")
    m1 = r["m1"]
    L += ["", "## 4. Vereditos pre-registrados", "",
          f"**M1 (primario; ganho de fit pooled >= {FIT_GAIN_MIN_PP} p.p. E razao de contribuicao >= "
          f"{CONTRIB_MIN} no MESMO DOF):**", ""]
    for d in DOFS:
        v = m1["per_dof"][d]
        L.append(f"- {d}: ganho {v['fit_gain_pp']:+.2f} p.p., razao {_f(v['contrib_ratio'])} -> "
                 f"{'importa' if v['matters'] else 'nao importa'}")
    L += ["", f"- **M1: {'ACOPLAMENTO IMPORTA' if m1['coupling_matters'] else 'acoplamento nao importa neste envelope'}**", ""]
    m2 = r["m2"]
    L += [f"**M2 (mecanismo; premissa G_ww diagonal >= (1 + {M2_INFLATION_MIN:.2f}) x K_ref; o acoplado remove "
          f">= {M2_REDUCTION_MIN:.0%} do excesso):** G_ww diagonal {_f(m2['G_diag'], 4)} "
          f"({m2['inflation_diag']:+.1%}), acoplado {_f(m2['G_coupled'], 4)} ({m2['inflation_coupled']:+.1%}), "
          f"fracao removida {_f(m2['fraction_removed'], 2)} -> **{m2['status']}**", ""]
    if "m2_stg_only" in r:
        s = r["m2_stg_only"]
        L += [f"- sensibilidade (treino so `{STG_LABEL}`, {s['n_train']} eventos): G_ww diagonal {_f(s['G_diag'], 4)} "
              f"({s['inflation_diag']:+.1%}), acoplado {_f(s['G_coupled'], 4)} ({s['inflation_coupled']:+.1%}) -> "
              f"{s['status']}", ""]
    if "pair_delays" in r:
        pdl = r["pair_delays"]
        L += ["## 5. Secundario: atrasos por par (busca exaustiva 0.." + str(M_MAX) + " amostras)", "",
              "| braco | vx pooled | vy pooled | w pooled |", "|---|---|---|---|"]
        for k in ("diagonal", "coupled"):
            L.append(f"| {k} | " + " | ".join(f"{_f(pdl['score']['pooled'][k][d], 1)} %" for d in DOFS) + " |")
        L += ["", "Acoplado (atrasos por par):", ""] + _gain_table(pdl["models"]["coupled"])
        L += ["", f"- M1 (atrasos por par): {'ACOPLAMENTO IMPORTA' if pdl['m1']['coupling_matters'] else 'nao importa'}"
              f"; M2: {pdl['m2']['status']} (G_ww {_f(pdl['m2']['G_diag'], 4)} -> {_f(pdl['m2']['G_coupled'], 4)})", ""]
    if "bootstrap" in r:
        b = r["bootstrap"]
        L += [f"## 6. Bootstrap por eventos de treino ({b['n_boot']} replicas, seed {b['seed']}; IC 95 % percentil)", "",
              "| quantidade | IC 95 % |", "|---|---|"]
        for k, v in b["ci95"].items():
            L.append(f"| {k} | [{_f(v[0], 3)}, {_f(v[1], 3)}] |")
        L.append("")
    if "harness" in r:
        h = r["harness"]
        L += [f"## 7. Harness do artigo (free-run, janelas re-ancoradas, bin translacional; h_ref = {h['h_ref_s']:.2f} s)",
              "", f"{h['n_windows']} janelas ({h['n_trans']} translacionais) em {len(h['events'])} eventos.", "",
              "| h (s) | e_pos promoted | e_pos diagonal | e_pos acoplado | e_ang promoted | e_ang diagonal | e_ang acoplado |",
              "|---|---|---|---|---|---|---|"]
        for row in h["rows"]:
            L.append(f"| {row['h_s']:.2f} | " + " | ".join(_f(row["epos"][k], 4) for k in ("promoted", "diagonal", "coupled"))
                     + " | " + " | ".join(_f(row["eang"][k], 4) for k in ("promoted", "diagonal", "coupled")) + " |")
        m3 = h["m3"]
        L += ["", f"Sanidade: mediana por evento do promoted em h_ref = {_f(h['sanity_promoted_event_median'], 4)} m "
              "(artigo: 0.0421).", "",
              f"**M3 (acoplado < diagonal por evento: >= {HARNESS_GATE['wins']}/10, p < {HARNESS_GATE['p']}, "
              f"rb >= {HARNESS_GATE['rb']}):** {m3['wins']}/{m3['n']}, p = {m3['p']:.3g}, rb = {m3['rb']:+.2f} -> "
              f"**{'MELHORA' if m3['improves'] else 'nao melhora'}**",
              f"- acoplado vs promoted: {h['coupled_vs_promoted']['wins']}/{h['coupled_vs_promoted']['n']}, "
              f"p = {h['coupled_vs_promoted']['p']:.3g}; diagonal vs promoted: {h['diagonal_vs_promoted']['wins']}/"
              f"{h['diagonal_vs_promoted']['n']}, p = {h['diagonal_vs_promoted']['p']:.3g}", ""]
    if "negative_control" in r:
        nc = r["negative_control"]
        L += [f"**Controle negativo:** G_ww diagonal {_f(nc['G']['diagonal'], 4)}, acoplado {_f(nc['G']['coupled'], 4)} "
              f"vs verdade {_f(nc['truth'], 4)} (tolerancia {NEG_CONTROL_TOL:.0%}), M1 sem acoplamento -> "
              f"**{'OK' if nc['ok'] else 'FALHOU'}**", ""]
    L += ["## Leitura", "",
          "- M1 e o criterio do camera-ready (item B3): responde se, no envelope destes logs, termos cruzados de comando "
          "melhoram o que o modelo reproduz no hold-out.",
          "- M2 testa em dado real o mecanismo do C1b: se o vies do ganho de yaw em malha fechada vem da guinada induzida "
          "pela translacao, dar ao modelo os comandos de translacao como entradas deve reduzir o ganho direto de yaw.",
          "- M3 mede o efeito no uso do modelo (free-run no harness), com o mesmo gate por evento do C2b.",
          f"- Custo: ajuste e bootstrap {r['cost_s']:.0f} s"
          + (f"; harness {r['harness']['cost_s']:.0f} s" if "harness" in r else "") + "."]
    return L


def _jsonable(o: Any) -> Any:
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items() if not str(k).startswith("_")}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o


def run(root: Path | None = None, out: Path | None = None, *, control: str | None = None,
        pair_delays: bool = True, n_boot: int = N_BOOT, harness: bool = True, quiet: bool = False,
        **kw) -> dict:
    ctx = C.make_context(root, out, seed=SEED)
    r = compute(ctx, control=control, pair_delays=bool(pair_delays), n_boot=int(n_boot), do_harness=bool(harness))
    stem = NAME if control is None else f"{NAME}_control-{control}"
    L = render(ctx, r)
    p = ctx.write_text(stem, L)
    pj = ctx.out_path(stem, "json")
    pj.write_text(json.dumps(_jsonable(r), indent=1, ensure_ascii=True), encoding="utf-8")
    pc = ctx.out_path(stem, "csv")
    rows = r["score"]["per_event"]
    with open(pc, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    if not quiet:
        print("\n".join(L))
        print(f"\nartefato: {p}\njson: {pj}\ncsv: {pc}")
    r.update(path=p, json=pj, csv=pc)
    return r


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
