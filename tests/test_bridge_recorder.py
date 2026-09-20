"""A recorded twin session must load through the dataset loader (log contract) and validate."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from dtssl.bridge.config import BridgeConfig
from dtssl.bridge.recorder import SessionRecorder, summary
from dtssl.bridge.server import SimServer
from dtssl.data.loader import load_event, segment_is_moving
from dtssl.data.schema import validate_segment
from dtssl.models import AnalyticFOPDTPlant, load_twin_params
from dtssl.sim.backends import make_world
from dtssl.sim.entities import RobotCmd
from dtssl.sim.rollout import free_run


def _drive(world, rec, seconds: float, rng: np.random.Generator) -> None:
    """Piecewise-constant random body commands (hold 0.5 s) for ``seconds`` of simulation."""
    n = int(round(seconds * 60))
    cmd = RobotCmd()
    rec.record_initial(world.state())
    for k in range(n):
        if k % 30 == 0:
            cmd = RobotCmd(vx=float(rng.uniform(-1.5, 1.5)), vy=float(rng.uniform(-1.0, 1.0)),
                           w=float(rng.uniform(-3.0, 3.0)))
            for key in world.robot_keys():
                world.set_command(key[0], key[1], cmd)
        rec.record(world.step(), world.commands)


def test_recorded_session_loads_and_validates(tmp_path):
    world = make_world("fopdt", n_blue=2, n_yellow=0, watchdog_clock="sim")
    rec = SessionRecorder(teams="blue", robot_ids=[0])
    _drive(world, rec, 4.0, np.random.default_rng(7))
    assert rec.duration_s >= 3.0 and len(rec) == 241
    cp, rp = rec.save(tmp_path / "session")
    assert cp.name == "commands.parquet" and rp.name == "processed_robots.parquet"
    C = pd.read_parquet(cp)
    R = pd.read_parquet(rp)
    assert list(C.columns) == ["timestamp", "timestamp_event", "robot_id", "move_x", "move_y", "move_w",
                               "actuation_kick_strength", "actuation_front", "actuation_chip",
                               "actuation_charge", "actuation_dribbler", "actuation_dribbler_velocity"]
    assert list(R.columns) == ["timestamp", "timestamp_event", "team", "robot_id", "position_x", "position_y",
                               "position_w", "velocity_x", "velocity_y", "velocity_norm"]
    assert (R["team"] == "allies").all()
    seg = load_event(cp, rp)                       # single robot -> robot_id inferred
    assert validate_segment(seg, raise_on_error=False) == []
    assert seg.n >= 3 * 60 and seg.duration_s >= 3.0 - 1e-9
    assert segment_is_moving(seg)
    assert np.max(np.abs(seg.pos_x)) < 5.0 and seg.meta["robot_id"] == 0
    # mm -> m and world velocity consistency: logged velocity ~ derivative of the position
    assert np.median(np.abs(seg.vel_x_world - np.gradient(seg.pos_x, seg.t))) < 0.05
    print(summary(rec))


def test_recorded_session_is_reproduced_by_free_run(tmp_path):
    """Replaying the recorded commands through the same plant reproduces the recorded pose."""
    params = load_twin_params()
    world = make_world("fopdt", n_blue=1, n_yellow=0, watchdog_clock="sim", params=params)
    rec = SessionRecorder(teams="blue")
    _drive(world, rec, 3.5, np.random.default_rng(3))
    cp, rp = rec.save(tmp_path / "s")
    seg = load_event(cp, rp)
    plant = AnalyticFOPDTPlant(params)
    h = 120
    cmds = np.column_stack([seg.cmd_vx, seg.cmd_vy, seg.cmd_w])[:h]
    sim = free_run(plant, cmds, seg.pose0, (0.0, 0.0, 0.0), seg.ts)   # session started at rest
    err = np.hypot(sim[:, 0] - seg.pos_x[: h + 1], sim[:, 1] - seg.pos_y[: h + 1])
    assert np.max(err) < 1e-6                      # loader grid == recorder grid (1/60), ZOH commands
    assert np.max(np.abs(sim[:, 2] - seg.theta[: h + 1])) < 1e-6


def test_multi_robot_recording_needs_explicit_robot_id(tmp_path):
    world = make_world("ideal", n_blue=2, n_yellow=1, watchdog_clock="sim")
    rec = SessionRecorder()                        # both teams, every robot
    _drive(world, rec, 3.2, np.random.default_rng(1))
    cp, rp = rec.save(tmp_path / "m")
    with pytest.raises(ValueError):
        load_event(cp, rp)
    seg = load_event(cp, rp, robot_id=1)
    assert validate_segment(seg, raise_on_error=False) == [] and seg.duration_s >= 3.0 - 1e-9


def test_server_records_when_recorder_attached():
    world = make_world("ideal", n_blue=1, n_yellow=0, watchdog_clock="sim")
    rec = SessionRecorder(teams="blue")
    cfg = BridgeConfig.load().with_overrides(vision_ip="127.0.0.1", vision_port=1, blue_port=0, yellow_port=0,
                                             simcontrol_port=0, bind_ip="127.0.0.1")
    srv = SimServer(world, cfg, step_mode=True, recorder=rec)
    world.set_command("blue", 0, RobotCmd(vx=1.0, w=math.pi))
    with srv:                                              # start() records the initial pose
        for _ in range(200):
            srv.tick()
    assert len(rec) == 201 and rec.duration_s == pytest.approx(200 / 60)
    C = rec.commands_df()
    assert len(C) == 200 and C["timestamp_event"].iloc[0] == 0.0
    R = rec.robots_df()
    assert np.all(np.abs(R["position_w"]) <= math.pi)     # wrapped like the logs
