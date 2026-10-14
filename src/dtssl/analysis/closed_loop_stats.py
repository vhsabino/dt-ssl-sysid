"""C4 - closed-loop session of the real strategy on the twin vs the competition logs (P1-P5).

Question: when the real RoboCIn strategy (ssl-unification) closes the loop on the twin
(``dtssl serve --record``), does it emit *competition-like* commands? The recorded session(s)
(log contract: ``commands.parquet`` + ``processed_robots.parquet``) are compared with the
maneuver-labelled competition events of the dataset (selection caveat: the events were labelled
because they contain motion; the session is continuous play).

All command statistics are computed on the common uniform 60 Hz ZOH grid (``interp_previous``, the
loader's rule) for both sources - the competition commands are logged in bursts of 2-10 ms - so the
distributions are time-weighted. Per source (session: all robots, field players = all but the
robot with the highest idle fraction, per robot, per session; competition: pooled play events and
per label): quantiles of |v_cmd| and |w_cmd|, idle fraction (|v| < 0.05 m/s and |w| < 0.1 rad/s),
fraction |w| < 0.58 rad/s (body equivalent of the 1.567 rad/s wheel deadzone), fraction of samples
the firmware wheel deadzone alters / fully clamps (``apply_body_deadzone``), saturation fraction
(|v| > 2.9 m/s), median |delta v| and |delta w| per tick, ticks per minute with the straight kick /
chip armed, and on the MEASURED side |v_meas| (``velocity_x/y`` mm/s -> m/s: real robot in the
competition, twin in the session) with the tracking ratio median(|v_meas|)/median(|v_cmd|)
(descriptive).

Pre-registered criteria (docs/PREREGISTRO_C4_MALHA_FECHADA_20260908.md; session field players vs
the 46 competition play events, ``rotate`` descriptive only): P1 Wasserstein-1 of |v| <= 0.20 m/s
and of |w| <= 0.20 rad/s; P2 fraction |w| < 0.58 rad/s within +-10 pp; P3 saturation fraction
within +-2 pp; P4 per-window medians (10 s windows per field robot) vs per-event medians:
Mann-Whitney two-sided p > 0.05 OR |Cliff's delta| <= 0.33, for |v| and for |w|; P5 median
|delta v| per tick within a factor 2. Verdict = criteria met (0-5): plausible >= 4, partial 3,
not plausible <= 2.

    dtssl analysis run closed_loop_stats [--kw sessions=results/sessao_01[,DIR2] labels=... window_s=10]

Artefacts: ``results/closed_loop_stats_<stamp>.md`` (+ ``.json``) and one ECDF figure
``results/figs/closed_loop_stats_<stamp>.png`` (|v_cmd| and |w_cmd|, session vs competition).
"""
from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from dtssl.analysis import common as C
from dtssl.data.resample import interp_previous, matlab_colon
from dtssl.sim.twin_world import DEADZONE_WHEEL_RAD_S, apply_body_deadzone

NAME = "closed_loop_stats"
KIND = "analysis"
CLAIM = "C4: the real strategy closing the loop on the twin emits competition-like commands (P1-P5)"
REQUIRES = ("data",)

COMPETITION_LABELS: tuple[str, ...] = ("front_to_back", "side_to_side", "shoot_to_goal", "square")  # paper's 46 splits
EXTRA_LABELS: tuple[str, ...] = ("rotate",)          # dedicated open-loop collection: descriptive only
TS = 1.0 / 60.0
IDLE_V, IDLE_W = 0.05, 0.10                          # m/s, rad/s (session_report / rollout idle rule)
W_DEADZONE_BODY = 0.58                               # rad/s, body equivalent of the wheel deadzone (pure rotation)
V_SAT = 2.9                                          # m/s, saturation threshold of the criteria
WINDOW_S = 10.0
MIN_WINDOW_FILL = 0.5                                # windows with fewer samples than this fraction are dropped
QUANTILES = (10, 25, 50, 75, 90, 99)
RULES = dict(P1_v=0.20, P1_w=0.20, P2_pp=10.0, P3_pp=2.0, P4_p=0.05, P4_delta=0.33, P5_ratio=2.0)
VERDICT = dict(plausible=4, partial=3)


# =========================================================================
# command series on the common grid
# =========================================================================
@dataclass
class CmdSeries:
    """One command sequence on the uniform ``ts`` grid (ZOH), body frame, SI."""
    name: str
    t: np.ndarray          # (N,) grid [s]
    vx: np.ndarray
    vy: np.ndarray
    w: np.ndarray
    front: np.ndarray      # (N,) bool, straight kick armed
    chip: np.ndarray       # (N,) bool, chip kick armed
    group: str             # session name or competition label
    unit: str              # robot id (session) or event name (competition)

    @property
    def n(self) -> int:
        return int(self.t.size)

    @property
    def v(self) -> np.ndarray:
        return np.hypot(self.vx, self.vy)

    @property
    def duration_s(self) -> float:
        return float(self.t[-1] - self.t[0]) if self.n else 0.0


def to_grid(cmd: pd.DataFrame, *, name: str, group: str, unit: str, ts: float = TS,
            tcol: str = "timestamp") -> CmdSeries | None:
    """ZOH resampling of a command table (log contract) onto ``arange(t0, t_end, ts)`` (MATLAB colon,
    the loader's rule). Duplicate timestamps keep the last row. ``None`` for fewer than 2 samples."""
    c = cmd.sort_values(tcol, kind="stable").drop_duplicates(subset=tcol, keep="last")
    t = c[tcol].to_numpy(float)
    if t.size < 2:
        return None
    grid = matlab_colon(float(t[0]), float(t[-1]), ts)
    if grid.size < 2:
        return None

    def zoh(col: str, default: float = 0.0) -> np.ndarray:
        if col not in c.columns:
            return np.full(grid.size, default)
        return interp_previous(t, c[col].to_numpy(float), grid, default)

    return CmdSeries(name=name, t=grid, vx=zoh("move_x"), vy=zoh("move_y"), w=zoh("move_w"),
                     front=zoh("actuation_front") > 0.5, chip=zoh("actuation_chip") > 0.5, group=group, unit=unit)


def deadzone_flags(vx: np.ndarray, vy: np.ndarray, w: np.ndarray,
                   threshold: float = DEADZONE_WHEEL_RAD_S) -> tuple[np.ndarray, np.ndarray]:
    """Per sample: ``altered`` (the firmware wheel deadzone changes the body command) and ``clamped``
    (every wheel masked: body command zeroed), with ``apply_body_deadzone`` as the reference rule."""
    n = vx.size
    altered = np.zeros(n, dtype=bool)
    clamped = np.zeros(n, dtype=bool)
    for k in range(n):
        a, b, c = float(vx[k]), float(vy[k]), float(w[k])
        if a == 0.0 and b == 0.0 and c == 0.0:
            continue
        o = apply_body_deadzone(a, b, c, threshold)
        if abs(o[0] - a) > 1e-12 or abs(o[1] - b) > 1e-12 or abs(o[2] - c) > 1e-12:
            altered[k] = True
            if abs(o[0]) < 1e-12 and abs(o[1]) < 1e-12 and abs(o[2]) < 1e-12:
                clamped[k] = True
    return altered, clamped


def series_stats(S: Sequence[CmdSeries], ts: float = TS, threshold: float = DEADZONE_WHEEL_RAD_S) -> dict:
    """Pooled command statistics of a set of series (all on the same grid)."""
    if not S:
        return dict(n=0)
    v = np.concatenate([s.v for s in S])
    w = np.concatenate([np.abs(s.w) for s in S])
    vx = np.concatenate([s.vx for s in S])
    vy = np.concatenate([s.vy for s in S])
    wr = np.concatenate([s.w for s in S])
    dv = np.concatenate([np.hypot(np.diff(s.vx), np.diff(s.vy)) for s in S if s.n > 1])
    dw = np.concatenate([np.abs(np.diff(s.w)) for s in S if s.n > 1])
    idle = (v < IDLE_V) & (w < IDLE_W)
    altered, clamped = deadzone_flags(vx, vy, wr, threshold)
    front = np.concatenate([s.front for s in S])
    chip = np.concatenate([s.chip for s in S])
    dur = float(sum(s.duration_s for s in S))
    per_min = 60.0 / dur if dur > 0 else float("nan")
    return dict(n=int(v.size), n_series=len(S), duration_s=dur,
                v_q={f"p{q}": float(np.percentile(v, q)) for q in QUANTILES}, v_max=float(v.max()),
                w_q={f"p{q}": float(np.percentile(w, q)) for q in QUANTILES}, w_max=float(w.max()),
                v_med=float(np.median(v)), w_med=float(np.median(w)),
                frac_idle=float(idle.mean()), frac_w_below_dz=float((w < W_DEADZONE_BODY).mean()),
                frac_dz_altered=float(altered.mean()), frac_dz_clamped=float(clamped.mean()),
                frac_v_sat=float((v > V_SAT).mean()),
                dv_med=float(np.median(dv)) if dv.size else float("nan"), dv_mean=float(dv.mean()) if dv.size else float("nan"),
                dw_med=float(np.median(dw)) if dw.size else float("nan"), dw_mean=float(dw.mean()) if dw.size else float("nan"),
                kick_front_frac=float(front.mean()), kick_chip_frac=float(chip.mean()),
                kick_front_per_min=float(front.sum() * per_min), kick_chip_per_min=float(chip.sum() * per_min),
                v_med_nonidle=float(np.median(v[~idle])) if (~idle).any() else float("nan"),
                w_med_nonidle=float(np.median(w[~idle])) if (~idle).any() else float("nan"))


def measured_stats(rob: pd.DataFrame) -> dict:
    """|v_meas| (m/s) quantiles from the logged ``velocity_x/y`` (mm/s), native rows."""
    if rob is None or len(rob) == 0:
        return dict(n=0)
    v = np.hypot(rob["velocity_x"].to_numpy(float), rob["velocity_y"].to_numpy(float)) / 1000.0
    v = v[np.isfinite(v)]
    return dict(n=int(v.size), v_q={f"p{q}": float(np.percentile(v, q)) for q in QUANTILES},
                v_med=float(np.median(v)), v_max=float(v.max()))


def window_medians(S: Sequence[CmdSeries], window_s: float = WINDOW_S, ts: float = TS,
                   min_fill: float = MIN_WINDOW_FILL) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    """Per-window medians of |v| and |w|: each series is cut into windows of ``window_s`` from its
    first sample
    windows with fewer than ``min_fill`` of the expected samples are dropped."""
    mv, mw, meta = [], [], []
    n_expected = window_s / ts
    for s in S:
        idx = np.floor((s.t - s.t[0]) / window_s + 1e-9).astype(int)
        v, w = s.v, np.abs(s.w)
        for k in range(int(idx.max()) + 1):
            m = idx == k
            if m.sum() < min_fill * n_expected:
                continue
            mv.append(float(np.median(v[m])))
            mw.append(float(np.median(w[m])))
            meta.append(dict(series=s.name, window=k, n=int(m.sum())))
    return np.asarray(mv), np.asarray(mw), meta


def event_medians(S: Sequence[CmdSeries]) -> tuple[np.ndarray, np.ndarray]:
    return (np.asarray([float(np.median(s.v)) for s in S]), np.asarray([float(np.median(np.abs(s.w))) for s in S]))


# =========================================================================
# statistics
# =========================================================================
def cliffs_delta(x: Sequence[float], y: Sequence[float]) -> float:
    """Cliff's delta ``(#(x > y) - #(x < y)) / (n m)`` over all pairs (positive: x tends to be larger)."""
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    if x.size == 0 or y.size == 0:
        return float("nan")
    d = x[:, None] - y[None, :]
    return float((np.sum(d > 0) - np.sum(d < 0)) / (x.size * y.size))


def distances(a: np.ndarray, b: np.ndarray) -> dict:
    from scipy.stats import ks_2samp, wasserstein_distance

    ks = ks_2samp(a, b)
    return dict(w1=float(wasserstein_distance(a, b)), ks_stat=float(ks.statistic), ks_p=float(ks.pvalue),
                n_a=int(a.size), n_b=int(b.size))


def compare_medians(x: np.ndarray, y: np.ndarray) -> dict:
    """Per-window (x) vs per-event (y) medians: Mann-Whitney two-sided + Cliff's delta."""
    from scipy.stats import mannwhitneyu

    if x.size == 0 or y.size == 0:
        return dict(n_x=int(x.size), n_y=int(y.size), p=float("nan"), delta=float("nan"),
                    med_x=float("nan"), med_y=float("nan"))
    mw = mannwhitneyu(x, y, alternative="two-sided")
    return dict(n_x=int(x.size), n_y=int(y.size), p=float(mw.pvalue), delta=cliffs_delta(x, y),
                med_x=float(np.median(x)), med_y=float(np.median(y)))


def criteria(sess: dict, comp: dict, dist_v: dict, dist_w: dict, p4_v: dict, p4_w: dict,
             rules: dict | None = None) -> dict:
    """Pre-registered P1-P5 on the statistics of the session field players (``sess``) vs the
    competition pool (``comp``)
    returns per-criterion values, flags and the verdict."""
    R = dict(RULES, **(rules or {}))
    out: dict[str, Any] = {}
    out["P1"] = dict(w1_v=dist_v["w1"], w1_w=dist_w["w1"], limit_v=R["P1_v"], limit_w=R["P1_w"],
                     ok=bool(dist_v["w1"] <= R["P1_v"] and dist_w["w1"] <= R["P1_w"]))
    d2 = 100.0 * (sess["frac_w_below_dz"] - comp["frac_w_below_dz"])
    out["P2"] = dict(sess=sess["frac_w_below_dz"], comp=comp["frac_w_below_dz"], diff_pp=d2, limit_pp=R["P2_pp"],
                     ok=bool(abs(d2) <= R["P2_pp"]))
    d3 = 100.0 * (sess["frac_v_sat"] - comp["frac_v_sat"])
    out["P3"] = dict(sess=sess["frac_v_sat"], comp=comp["frac_v_sat"], diff_pp=d3, limit_pp=R["P3_pp"],
                     ok=bool(abs(d3) <= R["P3_pp"]))

    def p4ok(q: dict) -> bool:
        return bool((np.isfinite(q["p"]) and q["p"] > R["P4_p"]) or (np.isfinite(q["delta"]) and abs(q["delta"]) <= R["P4_delta"]))

    out["P4"] = dict(v=p4_v, w=p4_w, ok_v=p4ok(p4_v), ok_w=p4ok(p4_w), limit_p=R["P4_p"], limit_delta=R["P4_delta"],
                     ok=bool(p4ok(p4_v) and p4ok(p4_w)))
    stat = "dv_med"
    if not (sess["dv_med"] > 0.0 and comp["dv_med"] > 0.0):
        stat = "dv_mean"                       # declared fallback: a zero median (repeated commands)
    ratio = sess[stat] / comp[stat] if comp[stat] > 0.0 else float("nan")
    out["P5"] = dict(stat=stat, sess=sess[stat], comp=comp[stat], ratio=ratio, limit_ratio=R["P5_ratio"],
                     ok=bool(np.isfinite(ratio) and 1.0 / R["P5_ratio"] <= ratio <= R["P5_ratio"]))
    score = int(sum(out[k]["ok"] for k in ("P1", "P2", "P3", "P4", "P5")))
    verdict = ("plausivel" if score >= VERDICT["plausible"] else
               "parcial" if score >= VERDICT["partial"] else "nao plausivel")
    out.update(score=score, verdict=verdict, rules=R)
    return out


# =========================================================================
# data
# =========================================================================
def load_session(sdir: Path, ts: float = TS) -> dict:
    """Session directory (log contract) -> per-robot ``CmdSeries`` and measured-side tables."""
    c = pd.read_parquet(sdir / "commands.parquet")
    r = pd.read_parquet(sdir / "processed_robots.parquet")
    series, meas = {}, {}
    for rid in sorted(int(i) for i in c["robot_id"].unique()):
        s = to_grid(c[c["robot_id"] == rid], name=f"{sdir.name}/robot{rid}", group=sdir.name, unit=str(rid), ts=ts,
                    tcol="timestamp_event")
        if s is not None:
            series[rid] = s
            meas[rid] = r[r["robot_id"] == rid]
    return dict(name=sdir.name, path=str(sdir), series=series, measured=meas,
                n_cmd_rows=int(len(c)), n_rob_rows=int(len(r)), duration_s=float(c["timestamp_event"].max()),
                ticks=int(c["timestamp_event"].nunique()))


def load_competition(ctx: C.Ctx, labels: Sequence[str], ts: float = TS) -> dict[str, dict]:
    """Competition events per label -> ``CmdSeries`` (60 Hz grid) + measured tables."""
    out: dict[str, dict] = {}
    for label in labels:
        series, meas = [], []
        for ev in C.list_events(ctx.splits_dir, label):
            try:
                cmd, rob = C.read_event_csv(label, ev, dataset=ctx.dataset, data_root=ctx.data_root)
            except FileNotFoundError:
                continue
            s = to_grid(cmd, name=ev, group=label, unit=ev, ts=ts)
            if s is not None:
                series.append(s)
                meas.append(rob)
        if series:
            out[label] = dict(series=series, measured=pd.concat(meas, ignore_index=True))
    return out


def _raw_stats(c: pd.DataFrame) -> dict:
    """session_report's raw-row statistics (continuity with results/session_report_*)."""
    v = np.hypot(c["move_x"].to_numpy(float), c["move_y"].to_numpy(float))
    w = np.abs(c["move_w"].to_numpy(float))
    return dict(n=int(len(c)), v_med=float(np.median(v)), v_p90=float(np.percentile(v, 90)),
                w_med=float(np.median(w)), w_p90=float(np.percentile(w, 90)),
                frac_w_below_dz=float((w < W_DEADZONE_BODY).mean()), frac_idle=float(((v < IDLE_V) & (w < IDLE_W)).mean()))


# =========================================================================
# experiment
# =========================================================================
def compute(ctx: C.Ctx, sessions: Sequence[str | Path], labels: Sequence[str] | None = None,
            window_s: float = WINDOW_S, ts: float | None = None) -> dict:
    ts = float(ctx.ts if ts is None else ts)
    labels = tuple(labels) if labels else COMPETITION_LABELS
    # --- sessions ------------------------------------------------------------------------
    sess_list = []
    for sdir in sessions:
        p = Path(sdir)
        if not p.is_absolute():
            p = ctx.root / p
        if not (p / "commands.parquet").is_file():
            raise FileNotFoundError(f"session {p}: commands.parquet not found")
        sess_list.append(load_session(p, ts))
    per_session, field_series, keeper_series = [], [], []
    for S in sess_list:
        per_robot = {rid: series_stats([s], ts) for rid, s in S["series"].items()}
        keeper = max(per_robot, key=lambda k: per_robot[k]["frac_idle"])
        field = [S["series"][rid] for rid in S["series"] if rid != keeper]
        field_series += field
        keeper_series.append(S["series"][keeper])
        raw = pd.read_parquet(Path(S["path"]) / "commands.parquet")
        meas_field = pd.concat([S["measured"][rid] for rid in S["series"] if rid != keeper], ignore_index=True)
        per_session.append(dict(name=S["name"], path=S["path"], duration_s=S["duration_s"], ticks=S["ticks"],
                                robots=sorted(S["series"]), keeper=keeper, per_robot=per_robot,
                                all=series_stats(list(S["series"].values()), ts), field=series_stats(field, ts),
                                keeper_stats=per_robot[keeper], measured_field=measured_stats(meas_field),
                                measured_keeper=measured_stats(S["measured"][keeper]),
                                measured_per_robot={rid: measured_stats(S["measured"][rid]) for rid in S["series"]},
                                raw_all=_raw_stats(raw)))
    field = series_stats(field_series, ts)
    keeper_all = series_stats(keeper_series, ts)
    # --- competition ------------------------------------------------------------------------
    comp = load_competition(ctx, tuple(labels) + tuple(x for x in EXTRA_LABELS if x not in labels), ts)
    pool_series = [s for lab in labels if lab in comp for s in comp[lab]["series"]]
    if not pool_series:
        raise RuntimeError(f"no competition events found for labels {labels} in {ctx.splits_dir}")
    pool = series_stats(pool_series, ts)
    per_label = {lab: dict(stats=series_stats(d["series"], ts), n_events=len(d["series"]),
                           measured=measured_stats(d["measured"]), in_pool=lab in labels)
                 for lab, d in comp.items()}
    raw_pool = pd.concat([C.read_event_csv(lab, s.unit, dataset=ctx.dataset, data_root=ctx.data_root)[0]
                          for lab in labels if lab in comp for s in comp[lab]["series"]], ignore_index=True)
    meas_pool = measured_stats(pd.concat([comp[lab]["measured"] for lab in labels if lab in comp], ignore_index=True))
    meas_field = _measured_field(sess_list, per_session)
    # --- distributions, windows, criteria -------------------------------------------------
    v_s = np.concatenate([s.v for s in field_series])
    w_s = np.concatenate([np.abs(s.w) for s in field_series])
    v_c = np.concatenate([s.v for s in pool_series])
    w_c = np.concatenate([np.abs(s.w) for s in pool_series])
    dist_v, dist_w = distances(v_s, v_c), distances(w_s, w_c)
    idle_s = (v_s < IDLE_V) & (w_s < IDLE_W)
    idle_c = (v_c < IDLE_V) & (w_c < IDLE_W)
    dist_nonidle = dict(v=distances(v_s[~idle_s], v_c[~idle_c]), w=distances(w_s[~idle_s], w_c[~idle_c]))
    wv, ww, wmeta = window_medians(field_series, window_s, ts)
    ev, ew = event_medians(pool_series)
    p4_v, p4_w = compare_medians(wv, ev), compare_medians(ww, ew)
    crit = criteria(field, pool, dist_v, dist_w, p4_v, p4_w)
    per_label_dist = {}
    for lab, d in comp.items():
        vl = np.concatenate([s.v for s in d["series"]])
        wl = np.concatenate([np.abs(s.w) for s in d["series"]])
        el_v, el_w = event_medians(d["series"])
        per_label_dist[lab] = dict(v=distances(v_s, vl), w=distances(w_s, wl),
                                   p4_v=compare_medians(wv, el_v), p4_w=compare_medians(ww, el_w))
    tracking = dict(session_field=(meas_field["v_med"] / field["v_med"]) if field["v_med"] > 0 else float("nan"),
                    competition=(meas_pool["v_med"] / pool["v_med"]) if pool["v_med"] > 0 else float("nan"),
                    per_label={lab: (per_label[lab]["measured"]["v_med"] / per_label[lab]["stats"]["v_med"])
                               if per_label[lab]["stats"]["v_med"] > 0 else float("nan") for lab in per_label})
    return dict(sessions=per_session, field=field, keeper=keeper_all, n_field_series=len(field_series),
                competition=dict(labels=list(labels), n_events=len(pool_series), pool=pool, per_label=per_label,
                                 raw_pool=_raw_stats(raw_pool), measured_pool=meas_pool),
                measured_field=meas_field, tracking=tracking,
                dist=dict(v=dist_v, w=dist_w, nonidle=dist_nonidle), windows=dict(n=len(wmeta), window_s=window_s,
                                                                                  v=wv.tolist(), w=ww.tolist(), meta=wmeta),
                events=dict(n=int(ev.size), v=ev.tolist(), w=ew.tolist()), p4=dict(v=p4_v, w=p4_w),
                per_label_dist=per_label_dist, criteria=crit, ts=ts,
                ecdf=dict(v_s=v_s, w_s=w_s, v_c=v_c, w_c=w_c))


def _measured_field(sess_list: list[dict], per_session: list[dict]) -> dict:
    frames = []
    for S, P in zip(sess_list, per_session, strict=True):
        frames += [S["measured"][rid] for rid in S["series"] if rid != P["keeper"]]
    return measured_stats(pd.concat(frames, ignore_index=True))


# =========================================================================
# report
# =========================================================================
def _f(v: float, nd: int = 3) -> str:
    return "nan" if v is None or not np.isfinite(v) else f"{v:.{nd}f}"


def _pc(v: float, nd: int = 1) -> str:
    return "nan" if v is None or not np.isfinite(v) else f"{100.0 * v:.{nd}f}"


def _row(name: str, s: dict, m: dict | None = None) -> str:
    if not s or s.get("n", 0) == 0:
        return f"| {name} | - |"
    q, qw = s["v_q"], s["w_q"]
    meas = f"{_f(m['v_med'])} / {_f(m['v_q']['p90'])}" if m and m.get("n") else "-"
    return (f"| {name} | {s['n']} | {_f(q['p50'])} / {_f(q['p90'])} / {_f(s['v_max'], 2)} "
            f"| {_f(qw['p50'])} / {_f(qw['p90'])} / {_f(s['w_max'], 2)} | {_pc(s['frac_idle'])} | {_pc(s['frac_w_below_dz'])} "
            f"| {_pc(s['frac_dz_altered'])} / {_pc(s['frac_dz_clamped'])} | {_pc(s['frac_v_sat'], 2)} "
            f"| {_f(s['dv_med'], 4)} / {_f(s['dw_med'], 4)} | {s['kick_front_per_min']:.1f} / {s['kick_chip_per_min']:.1f} | {meas} |")


_HEAD = ("| conjunto | N (60 Hz) | \\|v\\| p50 / p90 / max (m/s) | \\|w\\| p50 / p90 / max (rad/s) | parado % | \\|w\\|<0.58 % "
         "| zona morta alterado / zerado % | \\|v\\|>2.9 % | med \\|dv\\| / \\|dw\\| por tick | chute / chip armado (ticks/min) "
         "| \\|v_meas\\| p50 / p90 |")
_SEP = "|---|---|---|---|---|---|---|---|---|---|---|"


def render(ctx: C.Ctx, R: dict, fig_rel: str | None = None) -> list[str]:
    comp, cr = R["competition"], R["criteria"]
    names = ", ".join(S["name"] for S in R["sessions"])
    L = C.result_header("C4 - Malha fechada da estrategia real sobre o gemeo vs logs de competicao (P1-P5)", ctx,
                        generator=f"dtssl.analysis.{NAME}",
                        extra=f"sessoes `{names}` | pool de competicao {comp['n_events']} eventos ({', '.join(comp['labels'])})")
    L += ["Pre-registro: docs/PREREGISTRO_C4_MALHA_FECHADA_20260908.md (criterios P1-P5 fixados a priori para as",
          "distribuicoes completas; medianas do session_report ja tinham sido vistas). Todas as estatisticas de",
          "comando na grade comum de 60 Hz (ZOH, regra do loader); a competicao e logada em rajadas de 2-10 ms.",
          "Jogadores de campo = robos da sessao exceto o de maior fracao parada (goleiro, reportado a parte).",
          "Pool de competicao = os 46 eventos de jogo do artigo (rotate = coleta dedicada, so descritivo).",
          "RESSALVA DE SELECAO: os eventos de competicao sao segmentos rotulados por manobra (parado 4 %),",
          "a sessao e jogo continuo; a massa perto de zero difere por construcao e nao e corrigida.", ""]
    for S in R["sessions"]:
        L.append(f"- Sessao `{S['name']}`: robos {S['robots']}, {S['ticks']} ticks = {S['duration_s']:.1f} s; goleiro = robo "
                 f"{S['keeper']} (parado {_pc(S['keeper_stats']['frac_idle'])} %).")
    L += ["", "## Tabela principal (grade de 60 Hz)", "", _HEAD, _SEP,
          _row("sessao: jogadores de campo", R["field"], R["measured_field"]),
          _row("sessao: goleiro", R["keeper"], R["sessions"][0]["measured_keeper"] if len(R["sessions"]) == 1 else None),
          _row("competicao: pool (46 ev.)" if comp["n_events"] == 46 else f"competicao: pool ({comp['n_events']} ev.)",
               comp["pool"], comp["measured_pool"])]
    for lab, d in comp["per_label"].items():
        tag = "" if d["in_pool"] else " (fora do pool)"
        L.append(_row(f"competicao: `{lab}` ({d['n_events']} ev.){tag}", d["stats"], d["measured"]))
    L += ["", "|v_meas| = velocidade logada (visao no robo real; gemeo na sessao), descritivo. Zona morta por roda "
          "(1.567 rad/s, `apply_body_deadzone`): 'alterado' = ao menos uma roda mascarada, 'zerado' = todas.", "",
          "## Distancias e criterios pre-registrados (jogadores de campo vs pool de competicao)", "",
          "| criterio | valor sessao | valor competicao | estatistica | limite | ok |", "|---|---|---|---|---|---|",
          f"| P1 W1(\\|v\\|) | - | - | {_f(cr['P1']['w1_v'], 4)} m/s | <= {cr['P1']['limit_v']} | {'SIM' if cr['P1']['w1_v'] <= cr['P1']['limit_v'] else 'nao'} |",
          f"| P1 W1(\\|w\\|) | - | - | {_f(cr['P1']['w1_w'], 4)} rad/s | <= {cr['P1']['limit_w']} | {'SIM' if cr['P1']['w1_w'] <= cr['P1']['limit_w'] else 'nao'} |",
          f"| P2 \\|w\\| < 0.58 rad/s | {_pc(cr['P2']['sess'])} % | {_pc(cr['P2']['comp'])} % | diff {cr['P2']['diff_pp']:+.1f} pp | +-{cr['P2']['limit_pp']:.0f} pp | {'SIM' if cr['P2']['ok'] else 'nao'} |",
          f"| P3 \\|v\\| > 2.9 m/s | {_pc(cr['P3']['sess'], 2)} % | {_pc(cr['P3']['comp'], 2)} % | diff {cr['P3']['diff_pp']:+.2f} pp | +-{cr['P3']['limit_pp']:.0f} pp | {'SIM' if cr['P3']['ok'] else 'nao'} |",
          f"| P4 medianas de \\|v\\| (janelas {R['windows']['n']} vs eventos {R['events']['n']}) | med {_f(cr['P4']['v']['med_x'])} | med {_f(cr['P4']['v']['med_y'])} "
          f"| MW p = {_f(cr['P4']['v']['p'], 4)}, delta = {_f(cr['P4']['v']['delta'], 3)} | p > {cr['P4']['limit_p']} ou \\|delta\\| <= {cr['P4']['limit_delta']} | {'SIM' if cr['P4']['ok_v'] else 'nao'} |",
          f"| P4 medianas de \\|w\\| | med {_f(cr['P4']['w']['med_x'])} | med {_f(cr['P4']['w']['med_y'])} "
          f"| MW p = {_f(cr['P4']['w']['p'], 4)}, delta = {_f(cr['P4']['w']['delta'], 3)} | idem | {'SIM' if cr['P4']['ok_w'] else 'nao'} |",
          f"| P5 rugosidade ({cr['P5']['stat']} por tick) | {_f(cr['P5']['sess'], 4)} m/s | {_f(cr['P5']['comp'], 4)} m/s | razao {_f(cr['P5']['ratio'], 2)} | [1/{cr['P5']['limit_ratio']:.0f}, {cr['P5']['limit_ratio']:.0f}] | {'SIM' if cr['P5']['ok'] else 'nao'} |",
          "", f"**Veredito: {cr['score']}/5 -> {cr['verdict'].upper()}** (plausivel >= 4, parcial 3, nao plausivel <= 2).", "",
          f"KS bilateral (descritivo): \\|v\\| D = {_f(R['dist']['v']['ks_stat'])} (p = {R['dist']['v']['ks_p']:.2e}), "
          f"\\|w\\| D = {_f(R['dist']['w']['ks_stat'])} (p = {R['dist']['w']['ks_p']:.2e}); n = {R['dist']['v']['n_a']} vs {R['dist']['v']['n_b']}.",
          f"Sem as amostras paradas (descritivo): W1(\\|v\\|) = {_f(R['dist']['nonidle']['v']['w1'], 4)} m/s, "
          f"W1(\\|w\\|) = {_f(R['dist']['nonidle']['w']['w1'], 4)} rad/s.",
          f"Razao de rastreamento mediana(\\|v_meas\\|)/mediana(\\|v_cmd\\|): sessao (gemeo) {_f(R['tracking']['session_field'])}, "
          f"competicao (robo real) {_f(R['tracking']['competition'])} -- diferenca descritiva, nao criterio.",
          "", "## Por rotulo (jogadores de campo da sessao vs cada rotulo; descritivo)", "",
          "| rotulo | ev. | W1 \\|v\\| (m/s) | W1 \\|w\\| (rad/s) | KS \\|v\\| | KS \\|w\\| | P4 \\|v\\|: p / delta | P4 \\|w\\|: p / delta | rastreamento |",
          "|---|---|---|---|---|---|---|---|---|"]
    for lab, d in R["per_label_dist"].items():
        pl = comp["per_label"][lab]
        L.append(f"| `{lab}`{'' if pl['in_pool'] else ' (fora do pool)'} | {pl['n_events']} | {_f(d['v']['w1'], 3)} | {_f(d['w']['w1'], 3)} "
                 f"| {_f(d['v']['ks_stat'])} | {_f(d['w']['ks_stat'])} | {_f(d['p4_v']['p'], 3)} / {_f(d['p4_v']['delta'], 2)} "
                 f"| {_f(d['p4_w']['p'], 3)} / {_f(d['p4_w']['delta'], 2)} | {_f(R['tracking']['per_label'][lab])} |")
    L += ["", "## Por robo (sessao)", "", _HEAD, _SEP]
    for S in R["sessions"]:
        for rid, s in S["per_robot"].items():
            tag = " (goleiro)" if rid == S["keeper"] else ""
            L.append(_row(f"`{S['name']}` robo {rid}{tag}", s, S["measured_per_robot"].get(rid)))
        L.append(_row(f"`{S['name']}` todos", S["all"], None))
    if len(R["sessions"]) > 1:
        L += ["", "## Por sessao (jogadores de campo)", "", _HEAD, _SEP]
        for S in R["sessions"]:
            L.append(_row(f"`{S['name']}` campo", S["field"], S["measured_field"]))
    r0 = R["sessions"][0]["raw_all"]
    rc = comp["raw_pool"]
    L += ["", "Continuidade com session_report (linhas brutas, sem grade): sessao todos os robos |v| med "
          f"{_f(r0['v_med'])} (p90 {_f(r0['v_p90'])}), |w| med {_f(r0['w_med'])} (p90 {_f(r0['w_p90'])}), |w|<0.58 em "
          f"{_pc(r0['frac_w_below_dz'])} %, parado {_pc(r0['frac_idle'])} %; pool de competicao bruto |v| med {_f(rc['v_med'])}, "
          f"|w| med {_f(rc['w_med'])}, |w|<0.58 em {_pc(rc['frac_w_below_dz'])} %, parado {_pc(rc['frac_idle'])} %."]
    if fig_rel:
        L += ["", f"![ECDF |v_cmd| e |w_cmd|]({fig_rel})"]
    L += ["", "## Leitura", ""]
    L += _reading(R)
    return L


def _reading(R: dict) -> list[str]:
    cr, f, p = R["criteria"], R["field"], R["competition"]["pool"]
    out = [f"- Veredito pre-registrado: {cr['score']}/5 ({cr['verdict']}). Criterios: " + ", ".join(
        f"{k} {'ok' if cr[k]['ok'] else 'FALHA'}" for k in ("P1", "P2", "P3", "P4", "P5")) + "."]
    out.append(f"- Amplitude: |v_cmd| mediano {_f(f['v_med'])} vs {_f(p['v_med'])} m/s (p90 {_f(f['v_q']['p90'])} vs "
               f"{_f(p['v_q']['p90'])}); |w_cmd| mediano {_f(f['w_med'])} vs {_f(p['w_med'])} rad/s (p90 {_f(f['w_q']['p90'])} vs "
               f"{_f(p['w_q']['p90'])}); parado {_pc(f['frac_idle'])} % vs {_pc(p['frac_idle'])} % (ressalva de selecao).")
    out.append(f"- Zona morta: |w| < 0.58 rad/s em {_pc(f['frac_w_below_dz'])} % (sessao) vs {_pc(p['frac_w_below_dz'])} % "
               f"(competicao); comando alterado por roda {_pc(f['frac_dz_altered'])} % vs {_pc(p['frac_dz_altered'])} %, "
               f"zerado {_pc(f['frac_dz_clamped'])} % vs {_pc(p['frac_dz_clamped'])} % -- o regime de guinada diluida do "
               "artigo reaparece quando a estrategia joga contra o gemeo.")
    out.append(f"- Rastreamento (descritivo): mediana(|v_meas|)/mediana(|v_cmd|) = {_f(R['tracking']['session_field'])} no gemeo "
               f"vs {_f(R['tracking']['competition'])} no robo real; o gemeo P1D nao contem escorregamento nem saturacao, o robo "
               "real sim.")
    if cr["score"] <= VERDICT["partial"] - 1:
        out.append("- Leitura de 'nao plausivel': a estrategia, fechando a malha sobre o gemeo, emite comandos com "
                   "amplitude/guinada/saturacao/rugosidade fora do que emite contra o robo real.")
    return out


def make_figure(R: dict, path: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    e = R["ecdf"]

    def ecdf(x):
        x = np.sort(np.asarray(x, dtype=float))
        return x, np.arange(1, x.size + 1) / x.size

    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.6))
    for ax, key, xl, xmax in ((axes[0], "v", "|v_cmd| (m/s)", 3.5), (axes[1], "w", "|w_cmd| (rad/s)", 8.0)):
        xs, ys = ecdf(e[f"{key}_s"])
        xc, yc = ecdf(e[f"{key}_c"])
        ax.step(xs, ys, where="post", color="#1f77b4", lw=1.6, label=f"sessao (jogadores de campo, n={xs.size})")
        ax.step(xc, yc, where="post", color="#d62728", lw=1.6, ls="--", label=f"competicao (pool, n={xc.size})")
        if key == "w":
            ax.axvline(W_DEADZONE_BODY, color="0.4", ls=":", lw=1.2)
            ax.text(W_DEADZONE_BODY + 0.08, 0.05, "zona morta 0.58 rad/s", color="0.3", fontsize=8)
        ax.set_xlim(0, xmax)
        ax.set_ylim(0, 1.0)
        ax.set_xlabel(xl)
        ax.set_ylabel("ECDF")
        ax.grid(alpha=0.3)
    axes[0].legend(loc="lower right", fontsize=8)
    fig.suptitle("C4 - comandos da estrategia real: malha fechada sobre o gemeo vs logs de competicao", fontsize=10)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def _jsonable(o):
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
    if isinstance(o, Path):
        return str(o)
    return o


def run(root: Path | None = None, out: Path | None = None, *, sessions: str | Sequence[str] = "results/sessao_01",
        labels: str | Sequence[str] | None = None, window_s: float = WINDOW_S, quiet: bool = False, **kw) -> dict:
    """Write ``closed_loop_stats_<stamp>.{md,json}`` and ``figs/closed_loop_stats_<stamp>.png`` into ``out``.
    ``sessions`` = one directory or a comma-separated list (pooled and reported one by one)."""
    ctx = C.make_context(root, out)
    sess = [s.strip() for s in sessions.split(",")] if isinstance(sessions, str) else [str(s) for s in sessions]
    labs = None if labels is None else ([s.strip() for s in labels.split(",")] if isinstance(labels, str) else list(labels))
    R = compute(ctx, sess, labs, float(window_s))
    fig = make_figure(R, ctx.figs / f"{NAME}_{ctx.stamp}.png")
    L = render(ctx, R, fig_rel=f"figs/{fig.name}")
    p = ctx.write_text(NAME, L)
    pj = ctx.out_path(NAME, "json")
    payload = {k: v for k, v in R.items() if k != "ecdf"}
    payload["artefacts"] = dict(md=p.name, json=pj.name, figure=str(fig.relative_to(ctx.out)))
    pj.write_text(json.dumps(_jsonable(payload), indent=1), encoding="utf-8")
    R.update(path=p, json=pj, figure=fig)
    if not quiet:
        print("\n".join(L))
        print(f"\nartefato: {p}\njson: {pj}\nfigura: {fig}")
    return R


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
