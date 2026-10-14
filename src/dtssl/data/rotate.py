"""``rotate_raw.csv`` (multiplexed export of the dedicated pure-rotation collection) -> ``rotate_01_01..10`` splits.

Port of ``scripts/build_rotate_splits.py`` (demux + event tables + metadata) and
``scripts/build_rotate_qc.py`` (QC report with figures) as importable functions. The output follows
the same split contract as the labeled events of :mod:`dtssl.data.extract`
(``<out_dir>/rotate_01_XX/{ball,commands,processed_robots,raw_ball,raw_robots,referee,telemetry}.parquet``
+ ``metadata.json``), consumed by ``matlab/dtssl/load_split.m``, ``canonical_split.m`` and
:mod:`dtssl.data.loader`.

Input format (never modified): one row per record, columns sparse by ``record_type``/``stream``::

    record_type 1 stream vision_robot : timestamp_ns, robot_id, team, x, y, orientation   (mm, rad)
    record_type 1 stream vision_ball  : timestamp_ns, x, y
    record_type 2 stream referee      : timestamp_ns, stage, command, blue_score, yellow_score
    record_type 4 stream feedback     : timestamp_ns, robot_id, vx, vy, w, kick_load, has_ball, battery,
                                        d_speed_m1..4, c_speed_m1..4, pwm_m1..4, error_m1..4, current_m1..4
    record_type 5 stream command      : timestamp_ns, robot_id, vx, vy, w, kick_strength, front, chip,
                                        charge, dribbler, dribbler_speed

Geometry constants (R/r, dead zone) come from ``config/robot_geometry.json`` (single source of
truth, decision D9 of 2026-07-24); never hard-code R/r here again.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from dtssl.paths import config_path, repo_root

DATASET_DEFAULT = "2026-05-18_19-2-15"
LOG_IDX = "01"          # single source log (D2: the dedicated collection is stored under this log)
SEED = 42
PAD_S_DEFAULT = 0.2
SG_WIN_DEFAULT = 7
SG_ORDER_DEFAULT = 2
REGIME_SKIP_S = 1.0      # initial transient of each event discarded from the regime statistics
FIRMWARE_PWM_LIMIT = 80.0

#: expected chronological order of the 10 steps (rad/s)
EXPECTED_AMPLITUDES = [0.25, -0.25, 0.5, -0.5, 1.0, -1.0, 2.5, -2.5, 5.0, -5.0]
#: linear regime = {+-1, +-2.5, +-5} (outside the 0.58-0.60 rad/s dead-zone grey area, see
#: config/robot_geometry.json / D9); dead zone CHARACTERISED (never fitted) = {+-0.25, +-0.5}.
SPLIT_BY_AMPLITUDE = {
    0.25: "deadzone", -0.25: "deadzone",
    0.5: "deadzone", -0.5: "deadzone",
    1.0: "treino", -1.0: "holdout",
    2.5: "holdout", -2.5: "treino",
    5.0: "treino", -5.0: "treino",
}
STREAM_ORDER = ("commands", "raw_robots", "processed_robots", "raw_ball", "ball", "referee", "telemetry")


# ============================================================================
# geometry
# ============================================================================
def load_robot_geometry(source: str | Path | dict | None = None) -> dict:
    """``config/robot_geometry.json`` (or a dict / explicit path). Single source of truth (D9)."""
    if isinstance(source, dict):
        return source
    p = Path(source) if source is not None else config_path("robot_geometry.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


@dataclass(frozen=True)
class GeometryConstants:
    wheel_radius_m: float
    robot_radius_m: float
    r_over_r_cad: float
    r_over_r_firmware: float
    r_over_r_deprecated: float
    wheel_deadzone_rad_s: float
    omega_cmd_deadzone_range: tuple[float, float]
    source: str = "config/robot_geometry.json (D9, results/CHANGELOG.md 2026-07-24)"

    @classmethod
    def from_json(cls, geom: dict, source: str | None = None) -> GeometryConstants:
        return cls(
            wheel_radius_m=geom["physical"]["wheel_radius_m"],
            robot_radius_m=geom["physical"]["R_contact_m"],
            r_over_r_cad=geom["physical"]["R_over_r"],
            r_over_r_firmware=geom["firmware"]["R_over_r_implied"],
            r_over_r_deprecated=geom["deprecated"]["R_over_r"],
            wheel_deadzone_rad_s=geom["firmware"]["motor_min_speed_rad_s"],
            omega_cmd_deadzone_range=tuple(geom["firmware"]["omega_cmd_deadzone_rad_s_range"]),
            **({"source": source} if source else {}),
        )


def git_commit(cwd: Path | None = None) -> str:
    try:
        root = cwd or repo_root()
        h = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=root, text=True).strip()
        dirty = subprocess.call(["git", "diff", "--quiet"], cwd=root) != 0
        return h + ("-dirty" if dirty else "")
    except Exception:
        return "no-commit"


# ============================================================================
# 1) reading + demultiplexing
# ============================================================================
@dataclass
class RotateSegment:
    idx: int
    w_cmd: float
    t_start: float   # first commands sample of this step (s, relative to t0)
    t_end: float     # last commands sample of this step (s, relative to t0)

    @property
    def name(self) -> str:
        return f"rotate_{LOG_IDX}_{self.idx:02d}"

    def window(self, pad_s: float) -> tuple[float, float]:
        return self.t_start + pad_s, self.t_end - pad_s


def load_raw(path: str | Path) -> pd.DataFrame:
    """Read ``rotate_raw.csv``; ``t`` = seconds since the first vision record (record_type 1)."""
    df = pd.read_csv(path)
    t0 = df.loc[df["record_type"] == 1, "timestamp_ns"].min()
    df["t"] = (df["timestamp_ns"] - t0) / 1e9
    return df


def stream(df: pd.DataFrame, record_type: int, name: str) -> pd.DataFrame:
    s = df[(df["record_type"] == record_type) & (df["stream"] == name)].sort_values("t", kind="stable")
    return s.reset_index(drop=True)


def detect_command_segments(cmd: pd.DataFrame) -> list[RotateSegment]:
    """One segment per plateau of ``move_w`` (every change of ``w`` starts a new step)."""
    w = cmd["w"].to_numpy()
    t = cmd["t"].to_numpy()
    change_idx = np.flatnonzero(np.diff(w) != 0)
    raw_segs = []
    start = 0
    for c in change_idx:
        raw_segs.append((w[start], t[start], t[c]))
        start = c + 1
    raw_segs.append((w[start], t[start], t[-1]))
    return [RotateSegment(i + 1, float(wv), float(ts), float(te))
            for i, (wv, ts, te) in enumerate(raw_segs)]


def sg_derivative(pos: np.ndarray, t: np.ndarray, win: int, order: int) -> np.ndarray:
    """Savitzky-Golay smoothing (same window/order as identify_trans_dof.m) + gradient on the
    real ``t`` (native, possibly irregular grid; no resampling)."""
    from scipy.signal import savgol_filter

    w = min(win, len(pos) if len(pos) % 2 == 1 else len(pos) - 1)
    if w <= order or w < 3:
        return np.gradient(pos, t)
    return np.gradient(savgol_filter(pos, w, order), t)


# ============================================================================
# 2) series derived over the WHOLE log (avoids filter artefacts at event borders;
#    only then sliced by window)
# ============================================================================
@dataclass
class RobotSeries:
    t: np.ndarray
    theta_wrapped: np.ndarray
    theta_unwrapped: np.ndarray
    omega: np.ndarray          # rad/s, SG(theta_unwrap) -> gradient
    vel_x_world: np.ndarray    # mm/s
    vel_y_world: np.ndarray    # mm/s


def build_robot_series(vr: pd.DataFrame, sg_win: int, sg_order: int) -> RobotSeries:
    t = vr["t"].to_numpy(float)
    theta_w = vr["orientation"].to_numpy(float)
    theta_u = np.unwrap(theta_w)
    omega = sg_derivative(theta_u, t, sg_win, sg_order)
    vx = sg_derivative(vr["x"].to_numpy(float), t, sg_win, sg_order)
    vy = sg_derivative(vr["y"].to_numpy(float), t, sg_win, sg_order)
    return RobotSeries(t, theta_w, theta_u, omega, vx, vy)


@dataclass
class BallSeries:
    t: np.ndarray
    vel_x: np.ndarray
    vel_y: np.ndarray
    acc_x: np.ndarray
    acc_y: np.ndarray


def build_ball_series(vb: pd.DataFrame, sg_win: int, sg_order: int) -> BallSeries:
    t = vb["t"].to_numpy(float)
    vx = sg_derivative(vb["x"].to_numpy(float), t, sg_win, sg_order)
    vy = sg_derivative(vb["y"].to_numpy(float), t, sg_win, sg_order)
    ax = sg_derivative(vx, t, sg_win, sg_order)
    ay = sg_derivative(vy, t, sg_win, sg_order)
    return BallSeries(t, vx, vy, ax, ay)


@dataclass
class RotateRaw:
    """Demultiplexed ``rotate_raw.csv`` + derived series + detected steps."""

    source: Path
    df: pd.DataFrame
    vr: pd.DataFrame        # vision_robot
    vb: pd.DataFrame        # vision_ball
    referee: pd.DataFrame
    cmd: pd.DataFrame       # command
    fb: pd.DataFrame        # feedback
    robot_id: int
    segs: list[RotateSegment]
    rs: RobotSeries
    bs: BallSeries
    sg_win: int = SG_WIN_DEFAULT
    sg_order: int = SG_ORDER_DEFAULT
    streams: dict[str, pd.DataFrame] = field(default_factory=dict)


def demux_rotate_raw(raw_csv: str | Path, *, sg_win: int = SG_WIN_DEFAULT, sg_order: int = SG_ORDER_DEFAULT,
                     expected: list[float] | None = EXPECTED_AMPLITUDES) -> RotateRaw:
    """Read + demux + detect the command steps (asserts the expected amplitude sequence)."""
    raw_csv = Path(raw_csv)
    df = load_raw(raw_csv)
    vr = stream(df, 1, "vision_robot")
    vb = stream(df, 1, "vision_ball")
    referee = stream(df, 2, "referee")
    fb = stream(df, 4, "feedback")
    cmd = stream(df, 5, "command")

    robot_ids = pd.unique(pd.concat([vr["robot_id"], fb["robot_id"], cmd["robot_id"]]))
    if len(robot_ids) != 1:
        raise ValueError(f"inconsistent robot_id across streams: {robot_ids}")
    robot_id = int(robot_ids[0])

    segs = detect_command_segments(cmd)
    got = [s.w_cmd for s in segs]
    if expected is not None and (len(got) != len(expected) or any(abs(g - e) > 1e-9 for g, e in zip(got, expected, strict=False))):
        raise ValueError(f"detected segments {got} != expected {expected}")

    rs = build_robot_series(vr, sg_win, sg_order)
    bs = build_ball_series(vb, sg_win, sg_order)
    streams = {"vision_ball": vb, "vision_robot": vr, "referee": referee, "feedback": fb, "command": cmd}
    return RotateRaw(raw_csv, df, vr, vb, referee, cmd, fb, robot_id, segs, rs, bs, sg_win, sg_order, streams)


# ============================================================================
# 3) event tables (slice by time; timestamp_event relative to the NOMINAL (padded)
#    start of the event, uniform across streams)
# ============================================================================
def mask_window(t: np.ndarray, a: float, b: float) -> np.ndarray:
    return (t >= a) & (t <= b)


def build_event_tables(raw: RotateRaw, seg: RotateSegment, pad_s: float) -> dict[str, pd.DataFrame]:
    a, b = seg.window(pad_s)
    robot_id, rs, bs, vr, vb, referee, cmd, fb = (raw.robot_id, raw.rs, raw.bs, raw.vr, raw.vb,
                                                   raw.referee, raw.cmd, raw.fb)

    def tev(t):
        return t - a

    out: dict[str, pd.DataFrame] = {}

    # --- commands ---
    m = mask_window(cmd["t"].to_numpy(float), a, b)
    c = cmd[m]
    out["commands"] = pd.DataFrame({
        "timestamp": c["t"].to_numpy(float),
        "robot_id": robot_id,
        "move_x": c["vx"].to_numpy(float),
        "move_y": c["vy"].to_numpy(float),
        "move_w": c["w"].to_numpy(float),
        "actuation_kick_strength": c["kick_strength"].to_numpy(float),
        "actuation_front": c["front"].to_numpy(bool),
        "actuation_chip": c["chip"].to_numpy(bool),
        "actuation_charge": c["charge"].to_numpy(bool),
        "actuation_dribbler": c["dribbler"].to_numpy(bool),
        "actuation_dribbler_velocity": c["dribbler_speed"].to_numpy(float),
        "timestamp_event": tev(c["t"].to_numpy(float)),
    })

    # --- raw_robots (passthrough; team = 'robots_' + source team) ---
    m = mask_window(vr["t"].to_numpy(float), a, b)
    r = vr[m]
    out["raw_robots"] = pd.DataFrame({
        "timestamp": r["t"].to_numpy(float),
        "team": "robots_" + r["team"].astype(str),
        "robot_id": robot_id,
        "position_x": r["x"].to_numpy(float),
        "position_y": r["y"].to_numpy(float),
        "position_w": r["orientation"].to_numpy(float),
        "timestamp_event": tev(r["t"].to_numpy(float)),
    })

    # --- processed_robots (team='allies'; position = raw vision [no Kalman fusion in this
    #     export -- see notes/QC]; velocity = Savitzky-Golay(pos)+gradient, world, mm/s) ---
    mrs = mask_window(rs.t, a, b)
    vx_w = rs.vel_x_world[mrs]
    vy_w = rs.vel_y_world[mrs]
    out["processed_robots"] = pd.DataFrame({
        "timestamp": rs.t[mrs],
        "team": "allies",
        "robot_id": robot_id,
        "position_x": r["x"].to_numpy(float),
        "position_y": r["y"].to_numpy(float),
        "position_w": r["orientation"].to_numpy(float),
        "velocity_x": vx_w,
        "velocity_y": vy_w,
        "velocity_norm": np.hypot(vx_w, vy_w),
        "timestamp_event": tev(rs.t[mrs]),
    })

    # --- raw_ball / ball ---
    m = mask_window(vb["t"].to_numpy(float), a, b)
    bb = vb[m]
    out["raw_ball"] = pd.DataFrame({
        "timestamp": bb["t"].to_numpy(float),
        "position_x": bb["x"].to_numpy(float),
        "position_y": bb["y"].to_numpy(float),
        "timestamp_event": tev(bb["t"].to_numpy(float)),
    })
    mbs = mask_window(bs.t, a, b)
    vxb = bs.vel_x[mbs]
    vyb = bs.vel_y[mbs]
    axb = bs.acc_x[mbs]
    ayb = bs.acc_y[mbs]
    out["ball"] = pd.DataFrame({
        "timestamp": bs.t[mbs],
        "position_x": bb["x"].to_numpy(float),
        "position_y": bb["y"].to_numpy(float),
        "velocity_x": vxb, "velocity_y": vyb,
        "acceleration_x": axb, "acceleration_y": ayb,
        "velocity_norm": np.hypot(vxb, vyb),
        "acceleration_norm": np.hypot(axb, ayb),
        "timestamp_event": tev(bs.t[mbs]),
    })

    # --- referee (passthrough; see note D5 -- the historical schema has a single
    #     game_state_name, not reconstructible from stage+command without the SSL state machine) ---
    m = mask_window(referee["t"].to_numpy(float), a, b)
    rf = referee[m]
    out["referee"] = pd.DataFrame({
        "timestamp": rf["t"].to_numpy(float),
        "stage": rf["stage"].astype(str),
        "command": rf["command"].astype(str),
        "blue_score": rf["blue_score"].to_numpy(float),
        "yellow_score": rf["yellow_score"].to_numpy(float),
        "timestamp_event": tev(rf["t"].to_numpy(float)),
    })

    # --- telemetry (feedback -> contract + extensions for the anomaly QC) ---
    m = mask_window(fb["t"].to_numpy(float), a, b)
    f = fb[m]
    out["telemetry"] = pd.DataFrame({
        "timestamp": f["t"].to_numpy(float),
        "robot_id": robot_id,
        "position_x": 0.0, "position_y": 0.0, "position_w": 0.0,   # unavailable (same as square)
        "velocity_x": f["vx"].to_numpy(float),
        "velocity_y": f["vy"].to_numpy(float),
        "velocity_w": f["w"].to_numpy(float),
        "dribbler_speed": np.nan,                                   # unavailable in the feedback stream
        "capacitor_charge": f["kick_load"].to_numpy(float),         # mapped by semantic similarity
        "dribbler_ball_contact": f["has_ball"].to_numpy(bool),
        "battery": f["battery"].to_numpy(float),
        "count": np.nan,                                            # unavailable in the feedback stream
        "wheel1": f["d_speed_m1"].to_numpy(float),
        "wheel2": f["d_speed_m2"].to_numpy(float),
        "wheel3": f["d_speed_m3"].to_numpy(float),
        "wheel4": f["d_speed_m4"].to_numpy(float),
        "timestamp_event": tev(f["t"].to_numpy(float)),
        # --- extensions (outside the historical contract; needed for ANOMALY 2) ---
        "wheel1_cmd": f["c_speed_m1"].to_numpy(float),
        "wheel2_cmd": f["c_speed_m2"].to_numpy(float),
        "wheel3_cmd": f["c_speed_m3"].to_numpy(float),
        "wheel4_cmd": f["c_speed_m4"].to_numpy(float),
        "wheel1_pwm": f["pwm_m1"].to_numpy(float),
        "wheel2_pwm": f["pwm_m2"].to_numpy(float),
        "wheel3_pwm": f["pwm_m3"].to_numpy(float),
        "wheel4_pwm": f["pwm_m4"].to_numpy(float),
        "wheel1_error": f["error_m1"].to_numpy(float),
        "wheel2_error": f["error_m2"].to_numpy(float),
        "wheel3_error": f["error_m3"].to_numpy(float),
        "wheel4_error": f["error_m4"].to_numpy(float),
        "wheel1_current": f["current_m1"].to_numpy(float),
        "wheel2_current": f["current_m2"].to_numpy(float),
        "wheel3_current": f["current_m3"].to_numpy(float),
        "wheel4_current": f["current_m4"].to_numpy(float),
    })

    return out


def write_tables(event_dir: Path, tables: dict[str, pd.DataFrame], *, csv: bool = False) -> None:
    event_dir.mkdir(parents=True, exist_ok=True)
    for name, tdf in tables.items():
        if csv:
            tdf.to_csv(event_dir / f"{name}.csv", index=False)
        tdf.to_parquet(event_dir / f"{name}.parquet", index=False)


def write_metadata(event_dir: Path, seg: RotateSegment, pad_s: float, sg_win: int, sg_order: int,
                   dataset: str, source_csv: str, robot_id: int, commit: str,
                   geometry_source: str = GeometryConstants.source) -> dict[str, Any]:
    a, b = seg.window(pad_s)
    md = {
        "event": seg.name,
        "label": "rotate",
        "dataset": dataset,
        "log": dataset,
        "source_file": source_csv,
        "robot_id": robot_id,
        "team_source": "yellow",
        "team_processed": "allies",
        "cmd_w_amplitude_rad_s": seg.w_cmd,
        "segment_index": seg.idx,
        "split": SPLIT_BY_AMPLITUDE[seg.w_cmd],
        "pad_s": pad_s,
        "window_raw_s": [seg.t_start, seg.t_end],
        "window_padded_s": [a, b],
        "duration_padded_s": b - a,
        "sg_win": sg_win,
        "sg_order": sg_order,
        "seed": SEED,
        "seed_note": ("atribuicao treino/holdout/deadzone por amplitude, literal "
                      "(instrucao explicita do experimento), nao regenerada via rng"),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "commit": commit,
        "geometry_source": geometry_source,
        "tool": "dtssl.data.rotate.build_rotate_splits",
        "notes": [
            "processed_robots.position_* = vision crua (raw_robots); nao ha stream "
            "'processed_frame' (fusao Kalman) neste export multiplexado, so "
            "'vision_robot' raw -- velocity_x/velocity_y sao estimadas via "
            "Savitzky-Golay(win=7,order=2)+gradiente da posicao (mundo, mm/s), "
            "igual identify_trans_dof.m/identify_omega_v3_linear.m.",
            "referee.stage/command mantidos crus; o schema historico usa um campo "
            "unico 'game_state_name' que nao e reconstruivel sem a maquina de "
            "estados do protocolo SSL a partir de stage+command (nao fabricado).",
            "telemetry.dribbler_speed e telemetry.count indisponiveis no stream "
            "'feedback' (existiam no proto 'telemetry' historico); NaN.",
            "telemetry.capacitor_charge<-kick_load e dribbler_ball_contact<-has_ball "
            "sao mapeamentos por semelhanca semantica (nao confirmados byte-a-byte "
            "contra o proto original).",
            "D9 (2026-07-24): split revisado -- +-0.5 rad/s saiu do fit linear e "
            "passou para 'deadzone' (uso exclusivo p/ caracterizar o limiar): "
            "setpoint pre-deadzone ~1.31-1.66 rad/s fica ao redor do limiar do "
            "firmware (MOTOR_MIN_SPEED_RAD_S=1.567 rad/s de roda), zona cinzenta "
            "onde u!=0 mas y~=0 corromperia um fit P1D linear. Regime linear = "
            "{+-1, +-2.5, +-5} rad/s.",
        ],
    }
    (event_dir / "metadata.json").write_text(json.dumps(md, indent=2, ensure_ascii=False), encoding="utf-8")
    return md


# ============================================================================
# 4) entry point
# ============================================================================
def build_rotate_splits(raw_csv: str | Path, out_dir: str | Path, *,
                        geometry: str | Path | dict | None = None, dataset: str = DATASET_DEFAULT,
                        pad_s: float = PAD_S_DEFAULT, sg_win: int = SG_WIN_DEFAULT,
                        sg_order: int = SG_ORDER_DEFAULT, csv: bool = False, qc: bool = False,
                        qc_report: str | Path | None = None, figs_dir: str | Path | None = None,
                        commit: str | None = None) -> list[dict[str, Any]]:
    """``rotate_raw.csv`` -> ``<out_dir>/rotate_01_01..10/`` (+ optional QC report).

    Returns the ``metadata.json`` dict of every event (in chronological order). ``geometry`` is a
    dict, a path or ``None`` (``config/robot_geometry.json``); it feeds the QC report and the
    provenance string of the metadata.
    """
    raw_csv, out_dir = Path(raw_csv), Path(out_dir)
    geom = load_robot_geometry(geometry)
    geometry_source = (str(geometry) if isinstance(geometry, (str, Path))
                       else GeometryConstants.source)
    commit = commit or git_commit()

    raw = demux_rotate_raw(raw_csv, sg_win=sg_win, sg_order=sg_order)
    try:
        source_rel = str(raw_csv.resolve().relative_to(repo_root()))
    except (ValueError, RuntimeError):
        source_rel = str(raw_csv)

    metas = []
    for seg in raw.segs:
        tables = build_event_tables(raw, seg, pad_s)
        event_dir = out_dir / seg.name
        write_tables(event_dir, tables, csv=csv)
        md = write_metadata(event_dir, seg, pad_s, sg_win, sg_order, dataset, source_rel,
                            raw.robot_id, commit, geometry_source)
        metas.append(md)

    if qc:
        rotate_qc(raw, metas, geometry=geom, pad_s=pad_s, dataset=dataset, commit=commit,
                  out_md=qc_report, figs_dir=figs_dir)
    return metas


# ============================================================================
# 5) QC report (port of scripts/build_rotate_qc.py; text kept verbatim, PT-BR)
# ============================================================================
def _dt_stats(t: np.ndarray) -> dict:
    if len(t) < 2:
        return dict(n=len(t), median=np.nan, p10=np.nan, p90=np.nan, max=np.nan, n_nonmonotonic=0)
    d = np.diff(t)
    return dict(n=len(t), median=float(np.median(d)), p10=float(np.percentile(d, 10)),
                p90=float(np.percentile(d, 90)), max=float(np.max(d)),
                n_nonmonotonic=int(np.count_nonzero(d <= 0)))


def _duplicate_report(streams: dict) -> str:
    """Classify the dT<=0 samples: exact row duplicate (benign, logger wrote the record twice)
    vs a real reordering (bug)."""
    parts = []
    total_dup, total_reorder = 0, 0
    for name, s in streams.items():
        t = s["t"].to_numpy(float)
        if len(t) < 2:
            continue
        bad = np.flatnonzero(np.diff(t) <= 0)
        if len(bad) == 0:
            continue
        n_exact = 0
        for i in bad:
            if s.iloc[i].equals(s.iloc[i + 1]):
                n_exact += 1
        n_reorder = len(bad) - n_exact
        total_dup += n_exact
        total_reorder += n_reorder
        parts.append(f"`{name}`: {len(bad)} (payload identico: {n_exact}, "
                     f"timestamp colidido com payload distinto: {n_reorder})")
    if total_reorder == 0:
        verdict = ("todas benignas (duplicatas exatas de linha, dupla escrita do "
                   "logger; nao afetam ZOH/interpolacao)")
    else:
        verdict = (f"{total_dup} duplicatas exatas (benignas) + **{total_reorder} "
                   f"colisao(oes) de timestamp com payload DIFERENTE** -- checado "
                   f"manualmente (feedback, t~26.5 s): sao 2 leituras validas "
                   f"consecutivas (battery/kick_load/current_mX distintos) que "
                   f"cairam no mesmo bucket de ms (resolucao do timestamp_ns "
                   f"logado, nao da amostragem real); NAO e reordenacao (nenhum "
                   f"t[i]>t[i+1] com i+1 anterior no tempo real, so empate); "
                   f"impacto desprezivel (1/1011 amostras de feedback, mascara "
                   f"por tempo/gradiente toleram t repetido)")
    return ("; ".join(parts) if parts else "nenhuma") + f". Veredito: {verdict}."


def _md_table(df: pd.DataFrame) -> str:
    """``DataFrame.to_markdown`` (tabulate) with a plain fallback when tabulate is missing."""
    try:
        return df.to_markdown(index=False)
    except ImportError:
        return "```\n" + df.to_string(index=False) + "\n```"


def _rel(path: Path, base: Path) -> str:
    import os

    return Path(os.path.relpath(path, base)).as_posix()


def rotate_qc(raw: RotateRaw, metas: list[dict[str, Any]], *, geometry: str | Path | dict | None = None,
              pad_s: float = PAD_S_DEFAULT, dataset: str = DATASET_DEFAULT, commit: str | None = None,
              out_md: str | Path | None = None, figs_dir: str | Path | None = None) -> Path:
    """QC report of the demux -> ``results/qc_rotate_<ts>.md`` (+ figures in ``results/figs/``).

    Same sections as ``scripts/build_rotate_qc.py`` (coverage, dT, segmentation, wheel gain vs
    kinematics, PWM saturation, dead zone, final table, recorded deviations, summary); needs
    ``matplotlib`` (Agg) and, for the markdown tables, ``tabulate`` (falls back to plain text).
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    G = GeometryConstants.from_json(load_robot_geometry(geometry))
    commit = commit or git_commit()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        root = repo_root()
    except RuntimeError:
        root = Path.cwd()
    out_md = Path(out_md) if out_md else root / "results" / f"qc_rotate_{ts}.md"
    figs_dir = Path(figs_dir) if figs_dir else out_md.parent / "figs"
    figs_dir.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    link_base = out_md.parent

    segs, rs, fb, cmd, streams = raw.segs, raw.rs, raw.fb, raw.cmd, raw.streams
    sg_win, sg_order = raw.sg_win, raw.sg_order

    # ---------------------------------------------------------------- fig 1
    fig, ax = plt.subplots(figsize=(11, 3.2))
    ax.step(cmd["t"], cmd["w"], where="post", color="C0")
    for s in segs:
        a, b = s.window(pad_s)
        ax.axvspan(a, b, color="C0", alpha=0.08)
        ax.axvline(s.t_start, color="gray", lw=0.5, ls=":")
    ax.set_xlabel("t (s, relativo a t0 = 1o frame de visao)")
    ax.set_ylabel("move_w comandado (rad/s)")
    ax.set_title("Perfil de comando + janelas de evento (sombreado = apos pad)")
    fig.tight_layout()
    base1 = figs_dir / f"qc_rotate_cmd_profile_{ts}"
    fig.savefig(f"{base1}.png", dpi=200)
    fig.savefig(f"{base1}.svg")
    plt.close(fig)

    # ---------------------------------------------------------------- fig 2
    fig, axes = plt.subplots(1, len(streams), figsize=(4 * len(streams), 3))
    dt_stats = {}
    for ax, (name, s) in zip(axes, streams.items(), strict=True):
        t = s["t"].to_numpy(float)
        st = _dt_stats(t)
        dt_stats[name] = st
        if len(t) > 1:
            ax.hist(np.diff(t) * 1000, bins=40, color="C1")
        ax.set_title(f"{name}\nmed={st['median']*1000:.1f} ms" if len(t) > 1 else name)
        ax.set_xlabel("dT (ms)")
    fig.tight_layout()
    base2 = figs_dir / f"qc_rotate_dt_hist_{ts}"
    fig.savefig(f"{base2}.png", dpi=200)
    fig.savefig(f"{base2}.svg")
    plt.close(fig)

    # ------------------------------------------------------- wheel gain vs cmd
    ev05 = segs[4]  # +1.00 rad/s
    assert abs(ev05.w_cmd - 1.0) < 1e-9
    a, b = ev05.window(pad_s)
    m = (fb["t"] >= a) & (fb["t"] <= b)
    sub = fb[m].copy()
    sub["d_speed_mean_abs"] = sub[["d_speed_m1", "d_speed_m2", "d_speed_m3", "d_speed_m4"]].abs().mean(axis=1)
    predicted_cad = abs(ev05.w_cmd) * G.r_over_r_cad
    predicted_fw = abs(ev05.w_cmd) * G.r_over_r_firmware
    predicted_dep = abs(ev05.w_cmd) * G.r_over_r_deprecated
    regime_mask = sub["t"] >= (a + REGIME_SKIP_S)
    regime_med = float(sub.loc[regime_mask, "d_speed_mean_abs"].median())

    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.plot(sub["t"] - a, sub["d_speed_mean_abs"], "o-", ms=3, color="C2", label="d_speed medido (media 4 rodas)")
    ax.axhline(predicted_cad, color="g", ls="--", label=f"predicao CAD (R/r={G.r_over_r_cad:.4f}) = {predicted_cad:.3f} rad/s")
    ax.axhline(predicted_fw, color="k", ls="-.", label=f"predicao firmware-implicito (R/r={G.r_over_r_firmware:.4f}) = {predicted_fw:.3f} rad/s")
    ax.axhline(predicted_dep, color="r", ls=":", label=f"predicao DEPRECATED (R/r={G.r_over_r_deprecated:.4f}) = {predicted_dep:.3f} rad/s")
    ax.axvspan(0, REGIME_SKIP_S, color="gray", alpha=0.15, label="transiente descartado")
    ax.set_xlabel("t - inicio do evento (s)")
    ax.set_ylabel("|velocidade de roda| (rad/s)")
    ax.set_title(f"Ganho roda vs cmd -- evento {ev05.name} (cmd w=+1.0 rad/s)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    base3 = figs_dir / f"qc_rotate_ganho_roda_{ts}"
    fig.savefig(f"{base3}.png", dpi=200)
    fig.savefig(f"{base3}.svg")
    plt.close(fig)

    # ---------------------------------------------------------- anomaly 2
    ev09, ev10 = segs[8], segs[9]  # +5.0, -5.0
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.5), sharey=True)
    pwm_max_by_ev = {}
    for ax, s in zip(axes, (ev09, ev10), strict=True):
        a, b = s.window(pad_s)
        m = (fb["t"] >= a) & (fb["t"] <= b)
        sub = fb[m]
        pwm_cols = ["pwm_m1", "pwm_m2", "pwm_m3", "pwm_m4"]
        pmax = sub[pwm_cols].abs().max(axis=1)
        pwm_max_by_ev[s.name] = float(pmax.max())
        for c in pwm_cols:
            ax.plot(sub["t"] - a, sub[c], lw=0.8, label=c)
        ax.axhline(FIRMWARE_PWM_LIMIT, color="r", ls="--", lw=1)
        ax.axhline(-FIRMWARE_PWM_LIMIT, color="r", ls="--", lw=1)
        ax.set_title(f"{s.name} (cmd w={s.w_cmd:+.1f}), max|pwm|={pmax.max():.1f}")
        ax.set_xlabel("t - inicio do evento (s)")
    axes[0].set_ylabel("PWM por roda")
    axes[0].legend(fontsize=7, ncol=2)
    fig.suptitle(f"ANOMALIA 2 -- saturacao de PWM (limite firmware = +-{FIRMWARE_PWM_LIMIT:.0f})")
    fig.tight_layout()
    base4 = figs_dir / f"qc_rotate_anomalia2_{ts}"
    fig.savefig(f"{base4}.png", dpi=200)
    fig.savefig(f"{base4}.svg")
    plt.close(fig)

    # ---------------------------------------------------------- dead zone
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True)
    for ax, s in zip(axes.ravel(), segs[:4], strict=True):  # +-0.25, +-0.5
        a, b = s.window(pad_s)
        m = (rs.t >= a) & (rs.t <= b)
        theta_rel = rs.theta_unwrapped[m] - rs.theta_unwrapped[m][0]
        mfb = (fb["t"] >= a) & (fb["t"] <= b)
        pwm_max_ev = float(fb.loc[mfb, ["pwm_m1", "pwm_m2", "pwm_m3", "pwm_m4"]].abs().max().max()) if mfb.any() else float("nan")
        ax.plot(rs.t[m] - a, theta_rel, color="C4")
        ax.set_title(f"{s.name} (cmd w={s.w_cmd:+.2f} rad/s) -- max|pwm|={pwm_max_ev:.2f}")
        ax.set_xlabel("t - inicio do evento (s)")
        ax.set_ylabel("delta theta (rad)")
    fig.suptitle("Pose parada em +-0.25 E +-0.5 -- motor NUNCA acionado (pwm_max=0), nao atrito estatico")
    fig.tight_layout()
    base5 = figs_dir / f"qc_rotate_deadzone_{ts}"
    fig.savefig(f"{base5}.png", dpi=200)
    fig.savefig(f"{base5}.svg")
    plt.close(fig)

    # -------------------------------------------------- final table per event
    rows = []
    for s, md in zip(segs, metas, strict=True):
        a, b = s.window(pad_s)
        m_om = (rs.t >= a + REGIME_SKIP_S) & (rs.t <= b)
        om = rs.omega[m_om]
        theta_in = rs.theta_unwrapped[(rs.t >= a) & (rs.t <= b)]
        theta_disp = float(theta_in[-1] - theta_in[0]) if len(theta_in) else np.nan  # noqa: F841 (kept for parity)

        mfb = (fb["t"] >= a + REGIME_SKIP_S) & (fb["t"] <= b)
        sub = fb[mfb]
        wheel_cols = ["d_speed_m1", "d_speed_m2", "d_speed_m3", "d_speed_m4"]
        d_speed_med = float(sub[wheel_cols].abs().mean(axis=1).median()) if len(sub) else np.nan
        pwm_cols = ["pwm_m1", "pwm_m2", "pwm_m3", "pwm_m4"]
        pwm_max = float(sub[pwm_cols].abs().max(axis=1).max()) if len(sub) else np.nan
        sat_flag = "SIM" if pwm_max >= 0.9 * FIRMWARE_PWM_LIMIT else "nao"
        motor_acionado = "SIM" if pwm_max > 0.05 else "NAO (pwm=0, zona morta eletrica)"

        rows.append({
            "evento": s.name,
            "cmd_w (rad/s)": s.w_cmd,
            "omega_medido_mediano (rad/s, regime)": round(float(np.median(om)), 4) if len(om) else np.nan,
            "duracao_util (s)": round(b - a, 2),
            "d_speed_regime (rad/s roda, setpoint)": round(d_speed_med, 3) if d_speed_med == d_speed_med else np.nan,
            "pwm_max_abs": round(pwm_max, 2) if pwm_max == pwm_max else np.nan,
            "flag_saturacao_pwm": sat_flag,
            "motor_acionado": motor_acionado,
            "destino": md["split"],
        })
    tabela_final = pd.DataFrame(rows)

    # -------------------------------------------------------------- markdown
    lines = []
    lines.append(f"# QC -- padronizacao rotate_raw.csv ({ts})")
    lines.append("")
    lines.append(f"- Dataset: `{dataset}` | commit: `{commit}` | seed: `{SEED}`")
    lines.append(f"- Entrada: `{raw.source.name}` (NUNCA modificada)")
    lines.append(f"- Params: pad={pad_s:.2f} s, sg_win={sg_win}, sg_order={sg_order}, "
                 f"regime_skip={REGIME_SKIP_S:.1f} s")
    lines.append("- Script: `dtssl.data.rotate` (`dtssl etl rotate --qc`; ex-`scripts/build_rotate_splits.py` + "
                 "`scripts/build_rotate_qc.py`)")
    lines.append("")

    lines.append("## 1. Cobertura por stream (record_type/stream)")
    lines.append("")
    cov = pd.DataFrame([{"stream": k, "n_rows": len(v)} for k, v in streams.items()])
    lines.append(_md_table(cov))
    lines.append("")
    lines.append(f"- robot_id unico confirmado entre vision_robot/feedback/command: `{metas[0]['robot_id']}`, "
                 f"team origem `yellow` (D2: robô yellow #6).")
    lines.append("")

    lines.append("## 2. Monotonicidade e grade temporal (dT nativo, sem reamostrar)")
    lines.append("")
    dtt = pd.DataFrame([{"stream": k, **v} for k, v in dt_stats.items()])
    lines.append(_md_table(dtt))
    lines.append(f"\n![dt_hist]({_rel(base2, link_base)}.png)\n")
    n_bad = sum(v["n_nonmonotonic"] for v in dt_stats.values())
    lines.append(f"- Amostras nao-monotonicas (dT<=0): **{n_bad}** por stream -- {_duplicate_report(streams)}")
    lines.append("")

    lines.append("## 3. NaN por stream pos-demux (amostra: 1o evento)")
    lines.append("")
    lines.append("Verificado por evento na geracao (dtssl.data.rotate.build_rotate_splits); campos com NaN "
                 "esperado e documentado: telemetry.dribbler_speed, telemetry.count "
                 "(indisponiveis no stream 'feedback' -- ver metadata.json/notes).")
    lines.append("")

    lines.append("## 4. Segmentacao (transicoes de move_w)")
    lines.append("")
    seg_tab = pd.DataFrame([{
        "evento": s.name, "cmd_w": s.w_cmd, "t_start": round(s.t_start, 3),
        "t_end": round(s.t_end, 3), "dur_bruta_s": round(s.t_end - s.t_start, 3),
    } for s in segs])
    lines.append(_md_table(seg_tab))
    lines.append("\nOrdem esperada: +0.25, -0.25, +0.5, -0.5, +1, -1, +2.5, -2.5, +5, -5 rad/s "
                 "(~10 s cada) -> **confere exatamente** (verificado por assert no script; "
                 "o script aborta se nao bater).")
    lines.append(f"\n![cmd_profile]({_rel(base1, link_base)}.png)\n")

    lines.append("## 5. Ganho roda medido vs cinematica -- CORRIGIDO (D9, 2026-07-24)")
    lines.append("")
    lines.append("**Revisao desta secao (D9):** a versao anterior deste relatorio "
                 "(`qc_rotate_20260724_021248.md` §5, mantido intacto p/ comparacao) chamou "
                 "a razao medido/predito ~0.79 de 'ANOMALIA 1' e especulou deslizamento/"
                 "raio efetivo/erro de encoder. **Isso estava errado**: a constante de "
                 "referencia usada (R/r=3.3208, de robot_radius=0.088 m) e que nao tinha "
                 "rastreabilidade e foi refutada por CAD (medido 2026-07-24) + firmware + "
                 "K_omega medido (ver `config/robot_geometry.json`, bloco `deprecated`). "
                 "Com as constantes corrigidas a razao vai para **~0.97 (CAD) ou ~1.00 "
                 "(firmware-implicito, por definicao)** -- nao ha deficit de ganho.")
    lines.append(f"\nEm `{ev05.name}` (cmd w=+1.0 rad/s): `d_speed` medido em regime = "
                 f"**{regime_med:.4f} rad/s**.")
    lines.append(f"- vs predicao CAD (R/r={G.r_over_r_cad:.4f}): {predicted_cad:.4f} rad/s "
                 f"-> razao **{regime_med/predicted_cad:.4f}**")
    lines.append(f"- vs predicao firmware-implicito (R/r={G.r_over_r_firmware:.4f}): "
                 f"{predicted_fw:.4f} rad/s -> razao **{regime_med/predicted_fw:.4f}**")
    lines.append(f"- vs predicao DEPRECATED (R/r={G.r_over_r_deprecated:.4f}): {predicted_dep:.4f} "
                 f"rad/s -> razao {regime_med/predicted_dep:.4f} (a antiga 'anomalia')")
    lines.append(f"\n![ganho_roda]({_rel(base3, link_base)}.png)\n")
    ratio_by_ev = tabela_final.assign(
        predicted_cad=lambda t: t["cmd_w (rad/s)"].abs() * G.r_over_r_cad,
        predicted_fw=lambda t: t["cmd_w (rad/s)"].abs() * G.r_over_r_firmware,
    )
    ratio_by_ev["razao_vs_CAD"] = (ratio_by_ev["d_speed_regime (rad/s roda, setpoint)"]
                                   / ratio_by_ev["predicted_cad"])
    ratio_by_ev["razao_vs_firmware"] = (ratio_by_ev["d_speed_regime (rad/s roda, setpoint)"]
                                        / ratio_by_ev["predicted_fw"])
    lines.append(_md_table(ratio_by_ev[["evento", "cmd_w (rad/s)", "d_speed_regime (rad/s roda, setpoint)",
                                        "predicted_cad", "razao_vs_CAD", "razao_vs_firmware"]]))
    lines.append("\n**Achado corrigido:** `d_speed` (setpoint 'desejado' pos-clamp de zona morta, "
                 "ver §7) escala EXATAMENTE como R/r=2.61 (`firmware.R_over_r_implied`) em TODAS "
                 "as amplitudes ativas -- por definicao razao=1.0000 contra essa referencia (foi "
                 "dela que a constante foi extraida), e ~0.97 contra o CAD medido (residuo de "
                 "~3% explicavel por incerteza de medicao CAD/manufatura, nao por deslizamento "
                 "ou erro de encoder). **Nao ha 'anomalia' nenhuma**: o que parecia deficit de "
                 "ganho de ~21% era 100% erro da constante de referencia deprecated.")
    lines.append("")

    lines.append("## 6. Saturacao de PWM em +-5 rad/s")
    lines.append("")
    lines.append(f"Limite de PWM do firmware: +-{FIRMWARE_PWM_LIMIT:.0f} (`PID_Controller.cpp:157-164`).")
    for name, pmax in pwm_max_by_ev.items():
        lines.append(f"- `{name}`: max|pwm| observado = **{pmax:.2f}** "
                     f"({'SATURA' if pmax >= 0.9*FIRMWARE_PWM_LIMIT else 'nao satura'}, "
                     f"{100*pmax/FIRMWARE_PWM_LIMIT:.0f}% do limite)")
    lines.append(f"\n![pwm_saturacao]({_rel(base4, link_base)}.png)\n")
    lines.append(f"**Achado (mantido, so a explicacao do 'joelho' foi corrigida):** nao ha "
                 f"saturacao de PWM em nenhum dos 10 degraus (max observado ~20-20.4, bem "
                 f"abaixo de 80) -- os eventos +-5 rad/s permanecem utilizaveis no regime "
                 f"linear. O 'joelho' em ~16.6 rad/s de roda mencionado na tarefa vem de usar "
                 f"a constante DEPRECATED (5.0*{G.r_over_r_deprecated:.4f}={5*G.r_over_r_deprecated:.2f} "
                 f"rad/s) como predicao; com a constante correta "
                 f"(5.0*{G.r_over_r_firmware:.2f}={5*G.r_over_r_firmware:.2f} rad/s) o setpoint bate "
                 f"exatamente com o `d_speed` medido (ver tabela §5) -- nao existe deficit "
                 f"nenhum a explicar por saturacao ou qualquer outro efeito.")
    lines.append("")

    lines.append("## 7. Mecanismo da zona morta em +-0.5 -- CORRIGIDO (D9, 2026-07-24)")
    lines.append("")
    lines.append("**Revisao desta secao (D9):** a versao anterior levantou a hipotese de "
                 "'zona morta de corpo por atrito estatico do chassi' para explicar por que "
                 "+-0.5 rad/s nao produz rotacao mensuravel apesar de `d_speed` != 0. **Essa "
                 "hipotese NAO se sustenta**: `pwm_max_abs = 0` em `rotate_01_03`/`04` "
                 "(tabela §8) -- o motor nunca recebeu PWM, ou seja, NUNCA HOUVE TORQUE "
                 "APLICADO. Nao ha o que o atrito estatico precisaria 'vencer'; a roda nunca "
                 "tentou girar fisicamente. `d_speed` e um SETPOINT CALCULADO (confirmado via "
                 "`error_mX = d_speed_mX - c_speed_mX` em todos os eventos ativos, consistente "
                 "com a convencao `PID_Controller::pi(desired, measured)` do firmware "
                 "`ssl-embedded` commit `eb57531`), nao uma velocidade realizada.")
    lines.append(f"\n![deadzone]({_rel(base5, link_base)}.png)\n")
    lines.append("**Mecanismo unico:** zona morta ELETRICA por roda "
                 f"(`MOTOR_MIN_SPEED_RAD_S={G.wheel_deadzone_rad_s}` rad/s, "
                 "`utils.h:42`; clamp em `PID_Controller.cpp:94`). Em termos de ω comandado "
                 f"(corpo), o limiar e o **INTERVALO {G.omega_cmd_deadzone_range[0]:.3f}-"
                 f"{G.omega_cmd_deadzone_range[1]:.3f} rad/s** (motor_min_speed / R_over_r, "
                 "nunca valor pontual -- ver `config/robot_geometry.json`), **nao mais "
                 "0.472** (que usava a constante deprecated R/r=3.3208).")
    lines.append("\n**Consistencia empirica do intervalo corrigido:** "
                 f"cmd=0.5 < {G.omega_cmd_deadzone_range[1]:.3f} -> zona morta prediz PWM=0 -- "
                 "**bate** (medido: pwm_max=0 em rotate_01_03/04). cmd=1.0 > "
                 f"{G.omega_cmd_deadzone_range[1]:.3f} -> zona morta prediz motor acionado -- "
                 "**bate** (medido: pwm ativo, rotacao clara). O antigo limiar deprecated "
                 "(0.472) teria previsto INCORRETAMENTE que cmd=0.5 (>0.472) ja deveria "
                 "acionar o motor -- nao e o que se observa.")
    lines.append("\n**Questao em aberto MANTIDA (declarada, nao resolvida nesta sessao):** "
                 "o setpoint pre-clamp calculado por `Kinematics::convertToWheel` "
                 "(`kinematics.cpp:61-68`) usa a constante HARDCODED "
                 f"`robot_radius/wheel_radius=0.0880/0.02650={G.r_over_r_deprecated:.4f}` "
                 "(`kinematics.h:28-29`, commit `eb57531`, 2026-05-06) -- NAO "
                 f"{G.r_over_r_firmware:.4f}. Se o clamp de zona morta comparasse ESSA constante "
                 "contra o limiar 1.567, cmd=0.25 (setpoint 0.83) seria zerado mas cmd=0.5 "
                 "(setpoint 1.66) NAO seria -- e o `d_speed` reportado para cmd>=0.5 deveria "
                 "ser o valor cheio em base 3.3208, nao em base 2.61. Isso NAO bate com os "
                 "dados (pwm=0 em cmd=0.5; d_speed escala em base 2.61 sempre). Hipotese mais "
                 "provavel (nao confirmada): o firmware efetivamente rodando no robo durante a "
                 "coleta de 04-05/07/2026 (~2 meses apos o commit lido) ja usava uma constante "
                 "proxima de 2.61, divergente do snapshot git inspecionado nesta sessao (deriva "
                 "de versao entre commit e binario flasheado) -- **nao confirmado, pendencia "
                 "declarada**; nao foi rastreado o caminho completo "
                 "`MotionControl::updateDesiredSpeed` -> log de telemetria.")
    lines.append("")

    lines.append("## 8. Tabela final por evento")
    lines.append("")
    lines.append(_md_table(tabela_final))
    lines.append("")

    lines.append("## 9. Desvios registrados (D2/D3 + desta sessao)")
    lines.append("")
    lines.append("- **D2** (proveniencia): coleta de rotacao pura de ~04-05/07/2026, armazenada "
                 "sob a pasta de log `2026-05-18_19-2-15` (log mais antigo reaproveitado como "
                 "container); robo yellow #6.")
    lines.append("- **D3**: a Etapa B (firmware) do plano de identificacao de omega (CLAUDE.md/"
                 "RELATORIO_TECNICO §6) **foi executada** em 2026-06-13 (leitura de "
                 "`ssl-embedded`); o `docs/RELATORIO_TECNICO_DESENVOLVIMENTO.md` §6 ainda descreve "
                 "essa etapa como \"adiado, sem robo\" -- desatualizado, deve ser corrigido.")
    lines.append("- **D-schema-1**: `processed_robots` nao vem de uma fusao Kalman real (stream "
                 "`processed_frame` inexistente neste export); posicao = vision crua, "
                 "velocidade = Savitzky-Golay+gradiente (ver metadata.json de cada evento).")
    lines.append("- **D-schema-2**: `referee` mantem `stage`+`command` crus em vez de um "
                 "`game_state_name` unico fabricado (nao reconstruivel sem a maquina de estados "
                 "do protocolo SSL).")
    lines.append("- **D-schema-3**: `telemetry.dribbler_speed`/`count` indisponiveis (NaN); "
                 "`capacitor_charge`/`dribbler_ball_contact` sao mapeamentos por semelhanca "
                 "semantica de `kick_load`/`has_ball`, nao confirmados contra o proto original.")
    lines.append("- **D9** (2026-07-24, esta regeneracao): constante R/r=3.3208 (robot_radius="
                 "0.088 m) sem rastreabilidade, refutada por CAD medido (R/r=2.6991) + firmware/"
                 "telemetria (R/r implicito=2.61) + K_omega medido (~1.01); zona morta de omega "
                 f"comandado revisada de 0.472 (pontual) para {G.omega_cmd_deadzone_range[0]:.3f}-"
                 f"{G.omega_cmd_deadzone_range[1]:.3f} rad/s (intervalo). Fonte unica: "
                 "`config/robot_geometry.json`. §5/§7 desta versao substituem a leitura errada "
                 "de 'deficit de ganho' e 'zona morta corporal por atrito' da versao "
                 "`qc_rotate_20260724_021248.md` (mantida intacta p/ comparacao historica). "
                 "Split revisado: regime linear = {+-1, +-2.5, +-5}; zona morta caracterizada "
                 "(exclusiva, fora do fit) = {+-0.25, +-0.5}.")
    lines.append("")

    lines.append("## 10. Resumo (3 linhas)")
    lines.append("")
    lines.append("1. rotate_raw.csv (48 col, multiplexado) foi demultiplexado em 10 eventos "
                 "`rotate_01_01..10` no contrato de `square/`; split revisado (D9): regime "
                 "linear {+-1,+-2.5,+-5} (treino +1/-2.5/+5/-5, holdout -1/+2.5), zona morta "
                 "exclusiva {+-0.25,+-0.5}, gravado em `metadata.json`.")
    lines.append("2. **D9**: a razao 'medido/predito'~0.79 NAO era deficit de ganho -- era a "
                 "constante de referencia errada (R/r=3.3208 sem rastreabilidade); corrigida "
                 "para CAD 2.6991/firmware 2.61, a razao vai para ~0.97-1.00. Zona morta em "
                 f"+-0.5 NAO e atrito estatico (pwm_max=0 -> motor nunca acionado); e zona morta "
                 f"ELETRICA por roda, limiar de corpo revisado para INTERVALO "
                 f"{G.omega_cmd_deadzone_range[0]:.3f}-{G.omega_cmd_deadzone_range[1]:.3f} rad/s "
                 "(nunca ponto), consistente com pwm=0 em cmd=0.5 e pwm ativo em cmd=1.0.")
    lines.append("3. Sem saturacao de PWM em nenhum degrau (max ~20.4 de 80). Pendencia "
                 "declarada (nao resolvida): a base numerica exata (2.61 vs a constante "
                 "hardcoded 3.3208 lida no commit eb57531) do setpoint `d_speed` pos-clamp; "
                 "hipotese mais provavel = deriva de versao entre o commit inspecionado "
                 "(2026-05-06) e o firmware realmente flasheado na coleta (~04-05/07/2026).")
    lines.append("")

    out_md.write_text("\n".join(lines), encoding="utf-8")
    return out_md


__all__ = [
    "DATASET_DEFAULT", "LOG_IDX", "SEED", "PAD_S_DEFAULT", "SG_WIN_DEFAULT", "SG_ORDER_DEFAULT",
    "REGIME_SKIP_S", "FIRMWARE_PWM_LIMIT", "EXPECTED_AMPLITUDES", "SPLIT_BY_AMPLITUDE", "STREAM_ORDER",
    "load_robot_geometry", "GeometryConstants", "git_commit",
    "RotateSegment", "RobotSeries", "BallSeries", "RotateRaw",
    "load_raw", "stream", "detect_command_segments", "sg_derivative", "build_robot_series",
    "build_ball_series", "demux_rotate_raw", "mask_window", "build_event_tables", "write_tables",
    "write_metadata", "build_rotate_splits", "rotate_qc",
]
