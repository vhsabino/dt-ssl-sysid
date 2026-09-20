"""rotate ETL (port of scripts/build_rotate_splits.py + build_rotate_qc.py) on a synthetic rotate_raw.csv."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from dtssl.data import rotate as RT
from dtssl.data.extract import COLUMNS
from dtssl.data.loader import load_event

ROBOT_ID = 6
STEP_S = 2.5          # per amplitude (the real collection used ~10 s)
T0_NS = 1_783_000_000_000_000_000


def _rows_raw(step_s: float = STEP_S, fs_vision: float = 70.0, fs_cmd: float = 100.0,
              fs_fb: float = 10.0, fs_ref: float = 40.0) -> pd.DataFrame:
    """Multiplexed export: one row per record, sparse columns per record_type/stream."""
    rows: list[dict] = []
    amps = RT.EXPECTED_AMPLITUDES
    total = step_s * len(amps)
    r_over_r = 2.61
    K = 1.0  # body gain

    def amp_at(t: float) -> float:
        return amps[min(int(t // step_s), len(amps) - 1)]

    def active(w: float) -> bool:
        return abs(w) >= 1.0  # +-0.25/+-0.5 are inside the electrical dead zone (pwm=0)

    # vision (record_type 1): robot heading integrates K*w when the motor is active
    theta = 1.6
    t_prev = 0.0
    for k in range(int(total * fs_vision)):
        t = k / fs_vision
        w = amp_at(t)
        theta += (K * w if active(w) else 0.0) * (t - t_prev)
        t_prev = t
        rows.append({"record_type": 1, "stream": "vision_robot", "timestamp_ns": T0_NS + int(t * 1e9),
                     "robot_id": ROBOT_ID, "team": "yellow", "x": 1645.0 + 2 * math.sin(t),
                     "y": -1654.0 + 2 * math.cos(t), "orientation": math.atan2(math.sin(theta), math.cos(theta))})
        rows.append({"record_type": 1, "stream": "vision_ball", "timestamp_ns": T0_NS + int(t * 1e9) + 1000,
                     "x": 100.0 + 0.5 * t, "y": 50.0})
    # referee (record_type 2)
    for k in range(int(total * fs_ref)):
        t = k / fs_ref
        rows.append({"record_type": 2, "stream": "referee", "timestamp_ns": T0_NS + int(t * 1e9) + 500,
                     "stage": "NORMAL_FIRST_HALF", "command": "FORCE_START", "blue_score": 0, "yellow_score": 0})
    # feedback (record_type 4): wheel setpoint d_speed = R/r * |w| (0 inside dead zone), pwm ~ 4 * d_speed
    for k in range(int(total * fs_fb)):
        t = k / fs_fb + 0.05
        w = amp_at(t)
        d = r_over_r * abs(w) if active(w) else 0.0
        sgn = 1.0 if w >= 0 else -1.0
        row = {"record_type": 4, "stream": "feedback", "timestamp_ns": T0_NS + int(t * 1e9), "robot_id": ROBOT_ID,
               "vx": 0.0, "vy": 0.0, "w": K * w if active(w) else 0.0, "kick_load": 150.0, "has_ball": False,
               "battery": 16.0}
        for i in range(1, 5):
            row[f"d_speed_m{i}"] = sgn * d
            row[f"c_speed_m{i}"] = sgn * d * 0.98
            row[f"pwm_m{i}"] = sgn * 4.0 * d
            row[f"error_m{i}"] = sgn * d * 0.02
            row[f"current_m{i}"] = 0.1 * d
        rows.append(row)
    # command (record_type 5): pure rotation steps
    for k in range(int(total * fs_cmd)):
        t = k / fs_cmd + 0.012
        if t >= total:
            break
        rows.append({"record_type": 5, "stream": "command", "timestamp_ns": T0_NS + int(t * 1e9),
                     "robot_id": ROBOT_ID, "vx": 0.0, "vy": 0.0, "w": amp_at(t), "kick_strength": 0.0,
                     "front": False, "chip": False, "charge": False, "dribbler": False, "dribbler_speed": 0.0})
    df = pd.DataFrame(rows)
    return df.sort_values("timestamp_ns", kind="stable").reset_index(drop=True)


@pytest.fixture(scope="module")
def raw_csv(tmp_path_factory) -> Path:
    p = tmp_path_factory.mktemp("rotate") / "rotate_raw.csv"
    _rows_raw().to_csv(p, index=False)
    return p


@pytest.fixture(scope="module")
def built(raw_csv, tmp_path_factory) -> tuple[Path, list[dict]]:
    out = tmp_path_factory.mktemp("splits") / "rotate"
    metas = RT.build_rotate_splits(raw_csv, out, pad_s=0.2, commit="test")
    return out, metas


def test_geometry_from_config():
    g = RT.GeometryConstants.from_json(RT.load_robot_geometry())
    assert g.r_over_r_cad == pytest.approx(0.079601 / 0.029492, rel=1e-3)
    assert g.wheel_deadzone_rad_s == 1.567 and g.r_over_r_deprecated == 3.3208
    assert g.omega_cmd_deadzone_range[0] < g.omega_cmd_deadzone_range[1]
    assert RT.load_robot_geometry({"x": 1}) == {"x": 1}


def test_demux_detects_the_ten_steps(raw_csv):
    raw = RT.demux_rotate_raw(raw_csv)
    assert raw.robot_id == ROBOT_ID
    assert [s.w_cmd for s in raw.segs] == RT.EXPECTED_AMPLITUDES
    assert [s.name for s in raw.segs] == [f"rotate_01_{i:02d}" for i in range(1, 11)]
    for s in raw.segs:
        assert STEP_S - 0.05 < s.t_end - s.t_start <= STEP_S
    assert raw.vr["t"].iloc[0] == 0.0  # t0 = first vision record
    assert len(raw.rs.omega) == len(raw.vr) and len(raw.bs.acc_x) == len(raw.vb)
    with pytest.raises(ValueError):
        RT.demux_rotate_raw(raw_csv, expected=[1.0, 2.0])


def test_build_rotate_splits_layout_and_contract(built):
    out, metas = built
    assert len(metas) == 10
    for md in metas:
        d = out / md["event"]
        for name in RT.STREAM_ORDER:
            assert (d / f"{name}.parquet").is_file(), (md["event"], name)
            assert not (d / f"{name}.csv").exists()
        assert json.loads((d / "metadata.json").read_text(encoding="utf-8"))["event"] == md["event"]
        assert md["split"] == RT.SPLIT_BY_AMPLITUDE[md["cmd_w_amplitude_rad_s"]]
        assert md["label"] == "rotate" and md["robot_id"] == ROBOT_ID and md["commit"] == "test"
        assert md["window_padded_s"][0] == pytest.approx(md["window_raw_s"][0] + 0.2)
    cmd = pd.read_parquet(out / "rotate_01_05" / "commands.parquet")
    rob = pd.read_parquet(out / "rotate_01_05" / "processed_robots.parquet")
    assert list(cmd.columns) == list(COLUMNS["commands"]) + ["timestamp_event"]
    assert list(rob.columns) == list(COLUMNS["processed_robots"]) + ["timestamp_event"]
    assert (cmd["move_w"] == 1.0).all() and (cmd["robot_id"] == ROBOT_ID).all()
    assert (rob["team"] == "allies").all() and (rob["timestamp_event"] >= 0).all()
    assert cmd["timestamp_event"].iloc[0] == pytest.approx(cmd["timestamp"].iloc[0] - metas[4]["window_padded_s"][0])
    raw_r = pd.read_parquet(out / "rotate_01_05" / "raw_robots.parquet")
    assert (raw_r["team"] == "robots_yellow").all()
    tel = pd.read_parquet(out / "rotate_01_05" / "telemetry.parquet")
    assert tel["dribbler_speed"].isna().all() and tel["count"].isna().all()
    assert "wheel1_pwm" in tel.columns and (tel["wheel1"].abs() > 2.0).all()
    ref = pd.read_parquet(out / "rotate_01_05" / "referee.parquet")
    assert list(ref.columns) == ["timestamp", "stage", "command", "blue_score", "yellow_score", "timestamp_event"]


def test_processed_robot_velocity_is_sg_gradient(built):
    out, _ = built
    rob = pd.read_parquet(out / "rotate_01_09" / "processed_robots.parquet")  # +5 rad/s, motor active
    theta = np.unwrap(rob["position_w"].to_numpy())
    omega = np.gradient(theta, rob["timestamp"].to_numpy())
    assert np.median(omega) == pytest.approx(5.0, rel=0.05)
    np.testing.assert_allclose(rob["velocity_norm"], np.hypot(rob["velocity_x"], rob["velocity_y"]))


def test_rotate_event_loads_in_dtssl_loader(built):
    out, _ = built
    d = out / "rotate_01_07"
    seg = load_event(d / "commands.parquet", d / "processed_robots.parquet", team="allies", robot_id=ROBOT_ID)
    assert seg.n > 50 and np.allclose(seg.cmd_w, 2.5)
    assert np.median(seg.velb_w) == pytest.approx(2.5, rel=0.1)


def test_rotate_qc_report(raw_csv, built, tmp_path):
    pytest.importorskip("matplotlib")
    out, metas = built
    raw = RT.demux_rotate_raw(raw_csv)
    md = RT.rotate_qc(raw, metas, pad_s=0.2, commit="test", out_md=tmp_path / "qc.md",
                      figs_dir=tmp_path / "figs")
    text = md.read_text(encoding="utf-8")
    assert "## 8. Tabela final por evento" in text and "rotate_01_10" in text
    assert "(figs/qc_rotate_cmd_profile_" in text  # links relative to the report
    pngs = sorted(p.name for p in (tmp_path / "figs").glob("*.png"))
    assert len(pngs) == 5 and any("deadzone" in p for p in pngs)


def test_csv_option_and_geometry_path(raw_csv, tmp_path):
    from dtssl.paths import config_path

    out = tmp_path / "rot"
    metas = RT.build_rotate_splits(raw_csv, out, geometry=config_path("robot_geometry.json"), csv=True,
                                   commit="test")
    assert (out / "rotate_01_01" / "commands.csv").is_file()
    assert metas[0]["geometry_source"].endswith("robot_geometry.json")
