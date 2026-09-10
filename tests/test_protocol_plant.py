"""ProtocolPlant (replay through the ssl-simulation-protocol): alignment maths (pure) + a real UDP round trip
against ``SimServer`` (``requires_net``): the twin replayed through its own protocol server must reproduce the
analytic plant on the same harness windows."""
from __future__ import annotations

import math
import socket
import sys
import time

import numpy as np
import pytest

from dtssl.models import AnalyticFOPDTPlant, DofParam, load_twin_params
from dtssl.sim import protocol_plant as PP
from dtssl.sim.protocol_plant import (
    Endpoint,
    Frame,
    ProtocolPlant,
    estimate_tau0,
    find_anchor,
    interpolate_poses,
)

TS = 1.0 / 60.0


def _frames(times, poses, t0_recv=100.0, cam=0):
    return [Frame(t_recv=t0_recv + t, t_capture=1000.0 + t, frame_number=i, camera_id=cam, pose=p)
            for i, (t, p) in enumerate(zip(times, poses, strict=True))]


# ---------------------------------------------------------------- pure
def test_unwrap_series_is_continuous_from_the_start_value():
    th = np.array([3.1, -3.1, -3.0, 3.05])                   # crosses +-pi twice
    out = PP.unwrap_series(th, 3.0)
    assert np.all(np.abs(np.diff(out)) < 0.5)
    assert out[0] == pytest.approx(3.1)
    np.testing.assert_allclose(np.arctan2(np.sin(out), np.cos(out)), np.arctan2(np.sin(th), np.cos(th)), atol=1e-12)


def test_find_anchor_skips_pre_teleport_frames_and_scales_tolerance_with_speed():
    pose0 = (1.0, 2.0, 0.5)
    old = (0.2, 0.1, 0.0)                                     # where the robot was before the teleport
    fr = _frames([0.0, TS, 2 * TS, 3 * TS], [old, old, None, (1.02, 2.0, 0.5)])
    assert find_anchor(fr, pose0, (0.0, 0.0, 0.0), TS) == 3
    # moving fast: the first visible frame is already 4 cm ahead, allowed by |v0| 2 period
    fr2 = _frames([0.0, TS], [old, (1.04, 2.0, 0.5)])
    assert find_anchor(fr2, pose0, (2.0, 0.0, 0.0), TS) == 1
    assert find_anchor(fr2, pose0, (0.0, 0.0, 0.0), TS, tol_pos=0.03) is None
    # heading tolerance
    fr3 = _frames([0.0], [(1.0, 2.0, 0.5 + 0.3)])
    assert find_anchor(fr3, pose0, (0.0, 0.0, 0.0), TS) is None
    assert find_anchor(fr3, pose0, (0.0, 0.0, 6.0), TS) == 0


def test_estimate_tau0_from_the_displacement_along_v0():
    pose0 = (0.0, 0.0, 0.0)
    assert estimate_tau0((0.01, 0.0, 0.0), pose0, (1.0, 0.0, 0.0), TS) == pytest.approx(0.01)
    assert estimate_tau0((0.05, 0.0, 0.0), pose0, (1.0, 0.0, 0.0), TS) == pytest.approx(TS)      # clamped
    assert estimate_tau0((-0.01, 0.0, 0.0), pose0, (1.0, 0.0, 0.0), TS) == 0.0
    assert estimate_tau0((0.01, 0.0, 0.0), pose0, (0.05, 0.0, 0.0), TS) is None                 # too slow
    # lateral displacement does not count
    assert estimate_tau0((0.0, 0.02, 0.0), pose0, (1.0, 0.0, 0.0), TS) == 0.0


def test_interpolate_poses_recovers_a_linear_motion_with_sub_frame_offset():
    v = np.array([1.2, -0.4])
    w = 0.8
    tau0 = 0.006
    H = 30
    pose0 = (0.5, -0.5, 3.0)                                   # heading crosses +pi during the window
    # frames captured at tau0 + j / 60 after the teleport, stamped in capture time
    times = tau0 + np.arange(40) * TS
    poses = [(pose0[0] + v[0] * t, pose0[1] + v[1] * t, math.atan2(math.sin(pose0[2] + w * t), math.cos(pose0[2] + w * t)))
             for t in times]
    single = _frames(times, poses)
    fr = single + _frames(times[:5], poses[:5], cam=1)         # a second camera seeing the same ticks
    fr.sort(key=lambda f: f.t_capture)
    ps, n_used = interpolate_poses(fr, 0, tau0, 1.0, TS, H, pose0)
    assert n_used == 40 and np.isfinite(ps).all()
    want = TS * np.arange(1, H + 1)
    np.testing.assert_allclose(ps[1:, 0], pose0[0] + v[0] * want, atol=1e-9)
    np.testing.assert_allclose(ps[1:, 1], pose0[1] + v[1] * want, atol=1e-9)
    np.testing.assert_allclose(ps[1:, 2], pose0[2] + w * want, atol=1e-9)     # unwrapped, continuous
    # capture stamps at a different scale (dtssl serve at speed 3: wall stamps 3x denser)
    fr3 = [Frame(f.t_recv, 1000.0 + (f.t_capture - 1000.0) / 3.0, f.frame_number, f.camera_id, f.pose) for f in fr]
    ps3, _ = interpolate_poses(fr3, 0, tau0, 3.0, TS, H, pose0)
    np.testing.assert_allclose(ps3, ps, atol=1e-9)
    # too few frames -> NaN beyond the coverage
    ps_short, _ = interpolate_poses(single[:10], 0, tau0, 1.0, TS, H, pose0)
    assert np.isfinite(ps_short[1:10]).all() and np.isnan(ps_short[10:]).all()


def test_sending_side_delay_tap_matches_the_analytic_plant_tap():
    theta = {"vx": DofParam(K=1.0, tau=0.05, Td=0.0691), "vy": DofParam(K=1.0, tau=0.05, Td=0.0565),
             "w": DofParam(K=1.0, tau=0.05, Td=0.0890)}
    p = ProtocolPlant(Endpoint(name="x"), delay="theta", params=theta, auto_open=False)
    rng = np.random.default_rng(0)
    prev = rng.normal(size=(15, 3))
    win = rng.normal(size=(20, 3))
    ud = p._delayed_stream(win, prev, TS)
    hist = np.vstack([prev, win])
    for i, dof in enumerate(("vx", "vy", "w")):
        m = math.ceil(theta[dof].Td / TS - 1e-9)
        assert m == {"vx": 5, "vy": 4, "w": 6}[dof]
        for j in range(20):
            assert ud[j, i] == hist[15 + j - m, i]
    # no delay: pass-through; no prev: zeros before the window
    q = ProtocolPlant(Endpoint(name="x"), delay=None, auto_open=False)
    np.testing.assert_array_equal(q._delayed_stream(win, prev, TS), win)
    ud0 = p._delayed_stream(win, None, TS)
    assert np.all(ud0[:4] == 0.0) and ud0[5, 0] == win[0, 0]


def test_endpoints_config_and_plant_names():
    eps = PP.load_endpoints()
    assert {"dtssl", "grsim", "erforce"} <= set(eps)
    assert eps["grsim"].vision_port == 10020 and eps["grsim"].control_port == 10301 and eps["grsim"].vision_rate is None
    assert eps["dtssl"].vision_port == 10006 and eps["dtssl"].vision_rate == 60.0
    e = Endpoint.from_dict("y", {"team": "yellow", "bogus": 1})
    assert e.control_port == 10302 and e.name == "y"
    with pytest.raises(KeyError):
        PP.load_endpoint("nope")


# ---------------------------------------------------------------- real UDP round trip
def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _synth_segment(plant, N: int):
    from dtssl.data.loader import body_velocity_series
    from dtssl.data.schema import Segment
    from dtssl.sim.rollout import free_run

    t = np.arange(N) * TS
    cmd = np.column_stack([0.8 + 0.6 * np.sin(2 * np.pi * 0.25 * t), 0.4 * np.sin(2 * np.pi * 0.17 * t + 0.5),
                           1.2 * np.sin(2 * np.pi * 0.11 * t)])
    traj = free_run(plant, cmd[:-1], pose0=(0.0, 0.0, 0.0), velb0=(0, 0, 0), dt=TS)
    vbx, vby, vw = body_velocity_series(t, traj[:, 0], traj[:, 1], traj[:, 2])
    return Segment(meta={"event": "synth", "label": "synth", "dataset": "synth"}, ts=TS, t=t, dt=np.full(N, TS),
                   cmd_vx=cmd[:, 0], cmd_vy=cmd[:, 1], cmd_w=cmd[:, 2], pos_x=traj[:, 0], pos_y=traj[:, 1],
                   theta=traj[:, 2], vel_x_world=np.zeros(N), vel_y_world=np.zeros(N), velb_x=vbx, velb_y=vby,
                   velb_w=vw, pose0=(0.0, 0.0, 0.0), velb0=(vbx[0], vby[0], vw[0]))


@pytest.mark.requires_net
def test_protocol_replay_of_the_twin_reproduces_the_analytic_plant():
    """dtssl serve (fopdt, Td = 0) + ProtocolPlant(delay='theta') == AnalyticFOPDTPlant(theta) on the same
    windows, up to the float32 of the protocol and the sub-frame alignment (mm level)."""
    from dtssl.bridge.config import BridgeConfig
    from dtssl.bridge.server import SimServer
    from dtssl.sim.backends import make_world
    from dtssl.sim.rollout import rollout_segment

    theta = load_twin_params()
    theta_nodelay = {d: DofParam(K=p.K, tau=p.tau, Td=0.0) for d, p in theta.items()}
    world = make_world("fopdt", n_blue=1, n_yellow=0, params=theta_nodelay, watchdog_clock="sim")
    vport = _free_port()
    cfg = BridgeConfig.load().with_overrides(vision_ip="127.0.0.1", vision_port=vport, blue_port=0, yellow_port=0,
                                             simcontrol_port=0, bind_ip="127.0.0.1")
    srv = SimServer(world, cfg)
    srv.start()
    th = srv.run_in_thread()
    plant = None
    try:
        ep = Endpoint(name="test", host="127.0.0.1", port_blue=srv.control.port("blue"),
                      port_simcontrol=srv.simcontrol.port, vision_ip="127.0.0.1", vision_port=vport, unicast=True,
                      team="blue", robot_id=0, vision_rate=60.0, clear_others=False)
        plant = ProtocolPlant(ep, delay="theta", params=theta, probe_s=0.5)
        st = plant.stats
        assert st.vision_period_wall == pytest.approx(TS, rel=0.25)
        assert st.teleport_latency_wall is not None and st.teleport_latency_wall < 0.06
        seg = _synth_segment(AnalyticFOPDTPlant(theta), N=200)
        h_max, stride = 30, 30
        ref = rollout_segment(seg, AnalyticFOPDTPlant(theta), h_max=h_max, stride=stride, horizons=[6, 12, 30])
        t0 = time.monotonic()
        ro = rollout_segment(seg, plant, h_max=h_max, stride=stride, horizons=[6, 12, 30])
        wall = time.monotonic() - t0
        assert ro.n_total == ref.n_total >= 4
        assert st.anchor_failures == 0 and st.short_windows == 0, st.as_dict()
        assert wall >= ro.n_total * h_max * TS * 0.9                      # real time by construction
        errs = []
        for wa, wb in zip(ro.windows, ref.windows, strict=True):
            assert np.isfinite(wa.pose_sim).all()
            d = np.hypot(wa.pose_sim[:, 0] - wb.pose_sim[:, 0], wa.pose_sim[:, 1] - wb.pose_sim[:, 1])
            dth = np.abs(np.arctan2(np.sin(wa.pose_sim[:, 2] - wb.pose_sim[:, 2]),
                                    np.cos(wa.pose_sim[:, 2] - wb.pose_sim[:, 2])))
            errs.append((d.max(), dth.max()))
        errs = np.array(errs)
        assert errs[:, 0].max() < 3e-3, errs                                  # mm-level agreement
        assert errs[:, 1].max() < 1e-2, errs
        # paced to the ms on Linux; the in-process server + receiver share the GIL, so Windows only gets a loose bound
        late_ok, mean_ok = (10, 0.005) if sys.platform == "win32" else (2, 0.002)
        assert st.send_jitter_mean < mean_ok and st.send_late <= late_ok, st.as_dict()
        assert st.anchor_late == 0, st.as_dict()
    finally:
        if plant is not None:
            plant.close()
        srv.stop()
        th.join(timeout=2.0)
