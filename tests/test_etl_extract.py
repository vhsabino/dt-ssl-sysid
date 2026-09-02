"""ETL (notebooks 01/02 port): synthetic ssl-unification log -> streams -> dataset -> splits -> loader.

A small log is generated with the recordio writer + the vendored ``RCLog`` bindings, so the
tests run without the 300 MB real logs. Set ``DTSSL_TEST_LOG=<path>.log.gz`` to also run the
real-log checks at the end (optionally ``DTSSL_TEST_LOG_MANIFEST=<manifest.json>`` produced by the
notebook to compare row counts/time spans).
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from dtssl.data import _proto as P
from dtssl.data import extract as X
from dtssl.data.loader import load_event
from dtssl.data.recordio import pack_record
from dtssl.paths import repo_root

DATASET = "2026-05-18_19-2-15"
T0_NS = 1_779_144_202_000_000_000  # ~2026-05-18, epoch ns like the real logs
FS = 60.0
N_FRAMES = 100
ALLIES = (3, 6)
ENEMIES = (1,)


# ----------------------------------------------------------------------------- synthetic log
def _ally_pose(rid: int, t: float) -> tuple[float, float, float]:
    """Circle of radius 1 m around (rid*500 mm, 0), heading tangent; mm / rad."""
    w = 0.8
    x = rid * 500.0 + 1000.0 * math.cos(w * t)
    y = 1000.0 * math.sin(w * t)
    theta = math.atan2(math.cos(w * t), -math.sin(w * t))  # tangent direction
    return x, y, theta


def _ally_cmd(rid: int, t: float) -> tuple[float, float, float]:
    return 0.8, 0.05 * rid * math.sin(t), 0.8  # body frame, m/s, m/s, rad/s


def build_synthetic_log(path: Path, *, n_frames: int = N_FRAMES, fs: float = FS,
                        t0_ns: int = T0_NS, junk: bool = True) -> dict:
    """Write a recordio log with ``n_frames`` records (60 Hz) and return the expected counts."""
    dt_ns = int(round(1e9 / fs))
    payloads: list[bytes] = []
    n_referee = 0
    n_telemetry = 0

    if junk:  # records that the notebook drops: processed_frame with ts 0, commands with ts 1
        log = P.new_log()
        log.timestamp = 1
        log.processed_frame.publish_timestamp = 0
        r = log.processed_frame.allies.add()
        r.id = 3
        c = log.robots_command.navigation.add()
        c.publish_timestamp = 1
        c.id = 3
        payloads.append(P.encode_log(log))

    for k in range(n_frames):
        t = k / fs
        ts = t0_ns + k * dt_ns
        log = P.new_log()
        log.timestamp = 1_000_000 + k * dt_ns  # GlobalTimer ns (unused by the ETL)

        # processed frame (vision fusion): ball + allies + enemies, mm / mm/s / rad
        pf = log.processed_frame
        pf.publish_timestamp = ts
        pf.ball.position.x = 100.0 * t
        pf.ball.position.y = -50.0 * t
        pf.ball.velocity.x = 100.0
        pf.ball.velocity.y = -50.0
        pf.ball.acceleration.x = 0.0
        pf.ball.acceleration.y = -1.0
        for rid in ALLIES:
            x, y, th = _ally_pose(rid, t)
            r = pf.allies.add()
            r.id = rid
            r.position.x, r.position.y, r.position.omega = x, y, th
            r.velocity.x, r.velocity.y = -800.0 * math.sin(0.8 * t), 800.0 * math.cos(0.8 * t)
        for rid in ENEMIES:
            r = pf.enemies.add()
            r.id = rid
            r.position.x, r.position.y, r.position.omega = -2000.0, 500.0, 1.0

        # raw vision (SSL_WrapperPacket) published 5 ms before the fused frame
        rf = log.raw_frame.add()
        rf.publish_timestamp = ts - 5_000_000
        det = rf.packet.detection
        det.frame_number, det.t_capture, det.t_sent, det.camera_id = k, t, t, 0
        b = det.balls.add()
        b.confidence, b.x, b.y, b.pixel_x, b.pixel_y = 0.9, 100.0 * t + 1.0, -50.0 * t + 1.0, 0.0, 0.0
        for rid in ALLIES:
            x, y, th = _ally_pose(rid, t)
            rr = det.robots_yellow.add()
            rr.confidence, rr.robot_id, rr.x, rr.y, rr.orientation = 0.95, rid, x + 2.0, y + 2.0, th
            rr.pixel_x = rr.pixel_y = 0.0
        for rid in ENEMIES:
            rr = det.robots_blue.add()
            rr.confidence, rr.robot_id, rr.x, rr.y, rr.orientation = 0.95, rid, -2000.0, 500.0, 1.0
            rr.pixel_x = rr.pixel_y = 0.0
        if k % 30 == 0:  # geometry-only packet (no detection) -> must yield no rows
            rg = log.raw_frame.add()
            rg.publish_timestamp = ts - 4_000_000
            rg.packet.geometry.field.field_length = 9000
            rg.packet.geometry.field.field_width = 6000
            rg.packet.geometry.field.goal_width = 1000
            rg.packet.geometry.field.goal_depth = 180
            rg.packet.geometry.field.boundary_width = 300

        # navigation commands for the allies (body frame)
        for rid in ALLIES:
            vx, vy, w = _ally_cmd(rid, t)
            c = log.robots_command.navigation.add()
            c.publish_timestamp = ts + 1_000_000
            c.id = rid
            c.move.x, c.move.y, c.move.omega = vx, vy, w
            c.actuation.kick_strength = 0.0
            c.actuation.front = c.actuation.chip = c.actuation.charge = False
            c.actuation.dribbler = rid == 6
            c.actuation.dribbler_velocity = 3000.0 if rid == 6 else 0.0

        # telemetry of robot 3 every other frame
        if k % 2 == 0:
            tl = log.telemetry.telemetries.add()
            tl.receive_timestamp = ts + 2_000_000
            tl.id = 3
            tl.wheel1, tl.wheel2, tl.wheel3, tl.wheel4 = 1.0, 2.0, 3.0, 4.0
            tl.position.x, tl.position.y, tl.position.omega = 1.0, 2.0, 0.5
            tl.dribbler_speed, tl.capacitor_charge, tl.dribbler_ball_contact = 0.0, 150.0, False
            tl.battery, tl.count = 16.2, k
            n_telemetry += 1

        # referee game state (empty name on some records -> dropped by the notebook rule)
        log.referee.publish_timestamp = ts + 100_000
        if k % 10 != 5:
            log.referee.game_state_name = "Running" if k > 10 else "Halt"
            n_referee += 1
        if k % 25 == 0:  # raw referee packet
            log.rawReferee.publish_timestamp = ts
            log.rawReferee.packet.packet_timestamp = ts // 1000
            log.rawReferee.packet.stage = 1
            log.rawReferee.packet.command = 3
            log.rawReferee.packet.command_counter = k
            log.rawReferee.packet.command_timestamp = ts // 1000
            for team in (log.rawReferee.packet.yellow, log.rawReferee.packet.blue):
                team.name = "x"
                team.score = team.red_cards = team.yellow_cards = team.timeouts = 0
                team.timeout_time = team.goalkeeper = 0
        payloads.append(P.encode_log(log))

    if junk:
        payloads.append(b"\xff\xfe\x00garbage-not-a-protobuf" * 3)  # valid record, undecodable

    with open(path, "wb") as f:
        for i, p in enumerate(payloads):
            f.write(pack_record(p))
            if junk and i == 2:
                f.write(b"JUNKJUNKJUNK")  # container-level garbage -> resync
    return {
        "records": len(payloads),
        "ball": n_frames,
        "raw_ball": n_frames,
        "processed_robots": n_frames * (len(ALLIES) + len(ENEMIES)),
        "raw_robots": n_frames * (len(ALLIES) + len(ENEMIES)),
        "commands": n_frames * len(ALLIES),
        "telemetry": n_telemetry,
        "referee": n_referee,
        "dt_ns": dt_ns,
    }


@pytest.fixture(scope="module")
def synthetic(tmp_path_factory) -> tuple[Path, dict]:
    d = tmp_path_factory.mktemp("etl")
    path = d / f"{DATASET}.log.gz"
    expected = build_synthetic_log(path)
    return path, expected


@pytest.fixture(scope="module")
def streams(synthetic) -> X.Streams:
    return X.extract_streams(synthetic[0])


# ----------------------------------------------------------------------------- extraction
def test_extract_streams_contract(streams, synthetic):
    _, exp = synthetic
    assert tuple(streams.keys()) == X.STREAMS
    for name in X.STREAMS:
        df = streams[name]
        assert list(df.columns) == list(X.COLUMNS[name]), name
        assert len(df) == exp[name], name
        assert df["timestamp"].dtype == np.float64
        assert df["timestamp"].is_monotonic_increasing
        assert df["timestamp"].iloc[0] >= 0.0
    assert streams.meta["n_records"] == exp["records"] - 1  # the undecodable payload
    assert streams.meta["n_bad_records"] == 1 and streams.meta["n_resyncs"] == 1
    assert streams.meta["timeref_ns"] == float(T0_NS - 5_000_000)  # first raw_ball sample


def test_time_reference_and_units(streams):
    raw_ball, ball, cmd, robots = streams["raw_ball"], streams["ball"], streams["commands"], streams["processed_robots"]
    assert raw_ball["timestamp"].iloc[0] == 0.0                      # t=0 at the first raw frame
    # epoch-ns timestamps are cast to float64 (256 ns resolution at 1.8e18) before the subtraction,
    # exactly like the notebook -> sub-microsecond tolerance
    assert ball["timestamp"].iloc[0] == pytest.approx(0.005, abs=1e-6)  # fused frame 5 ms later
    assert cmd["timestamp"].iloc[0] == pytest.approx(0.006, abs=1e-6)
    # ns -> s exactly as the notebook: ((ts - timeref) % 1e13) / 1e9 with float64 ns
    ts_ns = np.float64(T0_NS + 7 * round(1e9 / FS))
    expect = ((ts_ns - np.float64(T0_NS - 5_000_000)) % 1e13) / 1e9
    assert ball["timestamp"].iloc[7] == expect
    # positions in mm (vision frame), commands in body frame m/s, rad/s -- no conversion here
    r3 = robots[(robots["team"] == "allies") & (robots["robot_id"] == 3)]
    assert 500.0 < r3["position_x"].abs().max() < 3000.0
    assert r3["position_w"].abs().max() <= math.pi
    assert (cmd["move_x"] == 0.8).all() and (cmd["move_w"] == 0.8).all()
    assert set(cmd["robot_id"]) == set(ALLIES)
    assert set(robots["team"]) == {"allies", "enemies"}
    assert set(streams["raw_robots"]["team"]) == {"robots_blue", "robots_yellow"}


def test_dtypes_and_derived_columns(streams):
    cmd, robots, ball, tel = streams["commands"], streams["processed_robots"], streams["ball"], streams["telemetry"]
    assert cmd["robot_id"].dtype == np.int64 and robots["robot_id"].dtype == np.int64
    for c in ("actuation_front", "actuation_chip", "actuation_charge", "actuation_dribbler"):
        assert cmd[c].dtype == np.bool_, c
    assert cmd.loc[cmd["robot_id"] == 6, "actuation_dribbler"].all()
    assert tel["dribbler_ball_contact"].dtype == np.bool_ and tel["count"].dtype == np.int64
    np.testing.assert_array_equal(robots["velocity_norm"].to_numpy(),
                                  np.sqrt(robots["velocity_x"] ** 2 + robots["velocity_y"] ** 2).to_numpy())
    np.testing.assert_allclose(ball["velocity_norm"], math.hypot(100.0, -50.0))
    np.testing.assert_allclose(ball["acceleration_norm"], 1.0)
    assert set(streams["referee"]["game_state_name"]) == {"Halt", "Running"}


def test_junk_records_are_dropped(synthetic, streams):
    # ts==0 processed frame and ts==1 command are filtered (timestamp > 1 ns rule)
    assert (streams["commands"]["timestamp"] > 0).all()
    assert len(streams["commands"]) == synthetic[1]["commands"]
    raw = X.extract_raw_streams(synthetic[0])
    assert (raw["ball"]["timestamp"] > 1).all() and raw["ball"]["timestamp"].dtype == np.int64


def test_max_records(synthetic):
    s = X.extract_streams(synthetic[0], max_records=11)  # 1 junk + 10 frames
    assert len(s["ball"]) == 10


# ----------------------------------------------------------------------------- dataset + manifest
@pytest.fixture(scope="module")
def dataset_dir(tmp_path_factory, streams) -> Path:
    out = tmp_path_factory.mktemp("extracted") / DATASET
    X.write_dataset(streams, out, csv=True)
    return out


def test_write_dataset_files_and_manifest(dataset_dir, streams, synthetic):
    for name in X.STREAMS:
        assert (dataset_dir / f"{name}.parquet").is_file()
        assert (dataset_dir / f"{name}.csv").is_file()
    m = X.read_manifest(dataset_dir)
    assert m["log_file"] == str(synthetic[0]) and m["timeref_ns"] == streams.meta["timeref_ns"]
    assert set(m["tables"]) == set(X.STREAMS)
    for name in X.STREAMS:
        t = m["tables"][name]
        assert t["rows"] == len(streams[name]) and t["columns"] == list(X.COLUMNS[name])
        assert t["t_start"] == streams[name]["timestamp"].iloc[0]
        assert t["t_end"] == streams[name]["timestamp"].iloc[-1]
    assert m["extraction"]["n_records"] == streams.meta["n_records"]
    back = X.read_dataset(dataset_dir)
    for name in X.STREAMS:
        pd.testing.assert_frame_equal(back[name], streams[name])


def test_write_dataset_skips_empty_parquet(tmp_path, streams):
    s = X.Streams({k: v for k, v in streams.items()}, meta=streams.meta)
    s["telemetry"] = streams["telemetry"].iloc[0:0]
    X.write_dataset(s, tmp_path / "ds")
    assert not (tmp_path / "ds" / "telemetry.parquet").exists()
    assert X.read_manifest(tmp_path / "ds")["tables"]["telemetry"]["rows"] == 0
    assert X.read_dataset(tmp_path / "ds")["telemetry"].empty


# ----------------------------------------------------------------------------- chunking
def test_chunk_intervals_reproduces_notebook_example():
    iv = X.chunk_intervals(X.annotations_frame([("square", 30.225, 83.991)]), 10.0)
    assert len(iv) == 6 and list(iv["event_id"]) == [f"square_01_{k:02d}" for k in range(1, 7)]
    assert iv["t_start"].iloc[0] == 30.225 and iv["t_end"].iloc[-1] == pytest.approx(83.991)
    np.testing.assert_allclose(iv["duration"], 53.766 / 6)
    one = X.chunk_intervals(X.annotations_frame([("shoot", 1.0, 5.5)]), 10.0)
    assert len(one) == 1 and one["n_chunks"].iloc[0] == 1


def test_chunk_intervals_source_idx_is_per_label():
    ann = X.annotations_frame([("a", 0, 1), ("b", 2, 3), ("a", 4, 5), ("weird label!", 6, 7)])
    iv = X.chunk_intervals(ann, 10.0)
    assert list(iv["event_id"]) == ["a_01_01", "a_02_01", "b_01_01", "weird_label__01_01"]


@pytest.mark.requires_data
def test_chunk_intervals_match_frozen_labels_manifest():
    path = repo_root() / "data" / "extracted" / DATASET / "splits" / "labels_manifest.csv"
    if not path.is_file():
        pytest.skip("frozen labels_manifest.csv not available")
    frozen = pd.read_csv(path, float_precision="round_trip")
    iv = X.chunk_intervals(X.annotations_frame(None, DATASET), 10.0)
    iv["duration"] = iv["t_end"] - iv["t_start"]  # split_dataset writes duration = t1 - t0
    cols = ["event_id", "label", "source_idx", "chunk_idx", "n_chunks", "t_start", "t_end", "duration"]
    assert len(frozen) == len(iv) == 46
    for c in cols:  # bit-exact floats
        assert list(frozen[c]) == list(iv[c]), c


def test_annotations_frame_inputs(tmp_path):
    csv = tmp_path / "labels.csv"
    csv.write_text("label,t_start,t_end\nsquare,1.0,2.5\n")
    a = X.annotations_frame(csv)
    b = X.annotations_frame([{"label": "square", "t_start": 1.0, "t_end": 2.5}])
    pd.testing.assert_frame_equal(a, b)
    assert a["duration"].iloc[0] == 1.5
    with pytest.raises(KeyError):
        X.annotations_frame(None, "unknown-dataset")
    with pytest.raises(ValueError):
        X.annotations_frame(pd.DataFrame({"label": ["a"], "t_start": [0.0]}))


# ----------------------------------------------------------------------------- split
@pytest.fixture(scope="module")
def split_manifest(dataset_dir) -> pd.DataFrame:
    labels = dataset_dir / "labels.csv"
    labels.write_text("label,t_start,t_end\nsquare,0.2,1.0\nsquare,1.0,1.3\nfront_to_back,0.5,0.9\n")
    return X.split_by_labels(dataset_dir, labels, chunk_s=0.5)


def test_split_by_labels_layout(dataset_dir, split_manifest):
    splits = dataset_dir / "splits"
    # square #1: 0.8 s -> 2 chunks of 0.4 s; square #2: 0.3 s -> 1 chunk; front_to_back: 1 chunk
    assert list(split_manifest["event_id"]) == ["square_01_01", "square_01_02", "square_02_01", "front_to_back_01_01"]
    for ev in split_manifest["event_id"]:
        d = splits / ev.rsplit("_", 2)[0] / ev
        for name in X.STREAMS:
            assert (d / f"{name}.parquet").is_file(), (ev, name)
            assert not (d / f"{name}.csv").exists()
    assert (splits / "labels_manifest.csv").is_file()
    for name in X.STREAMS:
        assert (splits / f"all_{name}_labeled.parquet").is_file()
    m = pd.read_csv(splits / "labels_manifest.csv")
    assert list(m.columns) == ["event_id", "label", "source_idx", "chunk_idx", "n_chunks", "t_start", "t_end",
                               "duration"] + [f"{s}_rows" for s in X.STREAMS]


def test_split_timestamp_event_and_boundaries(dataset_dir, split_manifest, streams):
    d = dataset_dir / "splits" / "square" / "square_01_01"
    cmd = pd.read_parquet(d / "commands.parquet")
    assert list(cmd.columns) == list(X.COLUMNS["commands"]) + ["timestamp_event"]
    t0, t1 = 0.2, 0.2 + 0.8 / 2
    assert (cmd["timestamp"] >= t0).all() and (cmd["timestamp"] < t1).all()   # [t0, t1)
    np.testing.assert_array_equal(cmd["timestamp_event"], cmd["timestamp"] - t0)
    assert cmd["timestamp_event"].iloc[0] >= 0.0
    src = streams["commands"]
    expect = src[(src["timestamp"] >= t0) & (src["timestamp"] < t1)]
    assert len(cmd) == len(expect) == split_manifest.loc[0, "commands_rows"]
    # contiguous chunks do not double count at the boundary
    nxt = pd.read_parquet(dataset_dir / "splits" / "square" / "square_01_02" / "commands.parquet")
    assert set(cmd["timestamp"]).isdisjoint(set(nxt["timestamp"]))
    assert len(cmd) + len(nxt) == len(src[(src["timestamp"] >= 0.2) & (src["timestamp"] < 1.0)])


def test_split_concat_tables(dataset_dir, split_manifest):
    big = pd.read_parquet(dataset_dir / "splits" / "all_processed_robots_labeled.parquet")
    assert list(big.columns) == list(X.COLUMNS["processed_robots"]) + ["timestamp_event", "label", "event_id",
                                                                        "source_idx", "chunk_idx"]
    assert set(big["event_id"]) == set(split_manifest["event_id"])
    rows = big.groupby("event_id").size()
    for _, rec in split_manifest.iterrows():
        assert rows[rec["event_id"]] == rec["processed_robots_rows"]


def test_split_event_loads_in_dtssl_loader(dataset_dir, split_manifest):
    """The produced parquet pair is consumed by dtssl.data.loader (mm -> m, unwrap, 1/60 grid)."""
    d = dataset_dir / "splits" / "square" / "square_01_01"
    seg = load_event(d / "commands.parquet", d / "processed_robots.parquet", team="allies", robot_id=3,
                     meta={"event": "square_01_01"})
    assert seg.n > 10 and abs(seg.dt[1] - 1 / 60) < 1e-9
    assert np.all(np.abs(seg.pos_x) < 4.0) and np.all(np.abs(seg.pos_y) < 2.0)  # metres now
    assert np.allclose(seg.cmd_vx, 0.8) and np.allclose(seg.cmd_w, 0.8)
    with pytest.raises(ValueError):  # two allies in commands -> robot_id is mandatory
        load_event(d / "commands.parquet", d / "processed_robots.parquet", team="allies")


def test_split_by_labels_builtin_annotations_need_known_dataset(tmp_path, streams):
    out = tmp_path / "other-dataset"
    X.write_dataset(streams, out)
    with pytest.raises(KeyError):
        X.split_by_labels(out)


# ----------------------------------------------------------------------------- inspect
def test_inspect_log(synthetic):
    path, exp = synthetic
    info = X.inspect_log(path)
    assert info["records"] == exp["records"] - 1 and info["bad_records"] == 1
    for name in X.STREAMS:
        assert info["counts"][name] == exp[name], name
    assert info["counts"]["raw_referee"] == 4 and info["counts"]["raw_frames"] > N_FRAMES
    assert info["duration_s"] == pytest.approx((N_FRAMES - 1) / FS + 0.007, abs=2e-3)
    assert not info["gzip_wrapped"] and not info["truncated"]


# ----------------------------------------------------------------------------- real log (optional)
REAL_LOG = os.environ.get("DTSSL_TEST_LOG")


@pytest.mark.skipif(not REAL_LOG, reason="set DTSSL_TEST_LOG=<log.gz> to run against a real log")
def test_real_log_end_to_end(tmp_path):
    log = Path(REAL_LOG)
    assert log.is_file(), log
    streams = X.extract_streams(log)
    for name in X.STREAMS:
        assert list(streams[name].columns) == list(X.COLUMNS[name]), name
    assert len(streams["ball"]) > 0 and len(streams["commands"]) > 0
    manifest_path = os.environ.get("DTSSL_TEST_LOG_MANIFEST")
    if manifest_path:  # manifest.json written by notebook 01 for the same log
        with open(manifest_path, encoding="utf-8") as f:
            ref = json.load(f)
        assert streams.meta["timeref_ns"] == ref["timeref_ns"]
        for name, t in ref["tables"].items():
            df = streams[name]
            assert len(df) == t["rows"], name
            assert t["columns"] == list(df.columns), name
            if t["rows"]:
                assert df["timestamp"].iloc[0] == pytest.approx(t["t_start"], abs=1e-9), name
                assert df["timestamp"].iloc[-1] == pytest.approx(t["t_end"], abs=1e-9), name
    out = tmp_path / X.dataset_name_from_log(log)
    X.write_dataset(streams, out)
    if X.dataset_name_from_log(log) in X.ANNOTATIONS:
        manifest = X.split_by_labels(out)
        assert len(manifest) == 46
        frozen = repo_root() / "data" / "extracted" / X.dataset_name_from_log(log) / "splits"
        ev = frozen / "square" / "square_01_01" / "commands.parquet"
        if ev.is_file():  # golden comparison with the frozen dataset (DVC)
            mine = pd.read_parquet(out / "splits" / "square" / "square_01_01" / "commands.parquet")
            pd.testing.assert_frame_equal(mine, pd.read_parquet(ev))
