"""dtssl.bridge.telemetry: twin-side records (IK wheel speeds, watchdog, illustrative hardware), the
rc_communication Feedback parser, the config loader, and the multicast/unicast receiver (loopback, requires_net)."""
from __future__ import annotations

import json
import math
import socket
import time

import numpy as np
import pytest

from dtssl.bridge.proto import RCFeedback, RCWrapperMessage
from dtssl.bridge.telemetry import (
    DEFAULT_CONFIG,
    RobotTelemetry,
    SyntheticHardware,
    TelemetryReceiver,
    load_telemetry_config,
    parse_feedback,
    twin_telemetry,
)
from dtssl.kinematics import body_to_wheels, wheels_to_body
from dtssl.sim.entities import BallState, RobotCmd, RobotState, WorldState


def _ws(t=1.0, **robot) -> WorldState:
    r = RobotState(team="yellow", id=3, **robot)
    return WorldState(t=t, frame=int(60 * t), robots={("yellow", 3): r}, ball=BallState())


def _fb(**kw) -> bytes:
    return RCFeedback(**kw).SerializeToString()


# ---------------------------------------------------------------- twin side
def test_twin_record_wheels_are_the_inverse_kinematics_of_the_body_velocities():
    ws = _ws(vx_b=1.0, vy_b=0.2, w=0.5, has_ball=True, x=0.4, y=-0.2, theta=0.3)
    cmd = RobotCmd(vx=1.1, vy=0.1, w=0.4, dribbler_rpm=100.0, t_recv=10.0)
    rec = twin_telemetry(ws, ("yellow", 3), cmd, watchdog_s=0.3, now=10.1, kicks=7)
    assert rec is not None and rec.source == "twin" and rec.team == "yellow" and rec.id == 3
    np.testing.assert_allclose(rec.wheel_meas, body_to_wheels([1.0, 0.2, 0.5]))
    np.testing.assert_allclose(rec.wheel_cmd, body_to_wheels([1.1, 0.1, 0.4]))
    np.testing.assert_allclose(wheels_to_body(rec.wheel_meas), [1.0, 0.2, 0.5], atol=1e-12)   # round trip
    assert rec.has_ball and rec.dribbler_on and rec.kicks == 7 and rec.pose == (0.4, -0.2, 0.3)
    assert rec.cmd_age_s == pytest.approx(0.1) and rec.watchdog is False
    assert rec.battery is None and rec.capacitor is None and not rec.hardware_illustrative
    d = rec.as_dict()
    assert isinstance(d["wheel_meas"], list) and json.dumps(d)                          # JSON-able
    # watchdog: the command is older than watchdog_s
    late = twin_telemetry(ws, ("yellow", 3), cmd, watchdog_s=0.3, now=10.5)
    assert late is not None and late.watchdog is True
    # no command yet (t_recv == 0): age and watchdog unknown
    fresh = twin_telemetry(ws, ("yellow", 3), RobotCmd(), watchdog_s=0.3, now=10.5)
    assert fresh is not None and fresh.cmd_age_s is None and fresh.watchdog is None
    assert twin_telemetry(ws, ("blue", 9), cmd) is None                                 # absent robot


def test_twin_record_applies_the_firmware_deadzone_to_the_commanded_wheels_only():
    ws = _ws(vx_b=0.02, vy_b=0.0, w=0.0)
    cmd = RobotCmd(vx=0.02)                                   # ~0.7 rad/s per wheel: under the 1.567 deadzone
    rec = twin_telemetry(ws, ("yellow", 3), cmd, deadzone_rad_s=1.567)
    assert rec is not None
    assert all(v == 0.0 for v in rec.wheel_cmd)               # commanded wheels zeroed by the deadzone
    assert any(abs(v) > 0.0 for v in rec.wheel_meas)          # the resulting motion is what it is
    plain = twin_telemetry(ws, ("yellow", 3), cmd)
    assert any(abs(v) > 0.0 for v in plain.wheel_cmd)


def test_synthetic_hardware_capacitor_empties_on_a_kick_and_battery_drains_with_wheel_usage():
    hw = SyntheticHardware({"synthetic": {"illustrative": True, "capacitor_tau_s": 2.0, "battery_full": 1.0,
                                          "battery_drain_per_rad": 1e-3}})
    key = ("yellow", 3)
    r_ball = RobotState("yellow", 3, has_ball=True)
    r_free = RobotState("yellow", 3, has_ball=False)
    wheels = (10.0, 10.0, 10.0, 10.0)
    b0, c0 = hw.update(key, 0.0, r_ball, RobotCmd(), wheels)
    assert b0 == 1.0 and c0 == 1.0
    b1, c1 = hw.update(key, 1.0, r_ball, RobotCmd(), wheels)          # 1 s at 40 rad/s total -> -0.04
    assert b1 == pytest.approx(0.96) and c1 == 1.0
    b2, c2 = hw.update(key, 1.0 + 1e-3, r_free, RobotCmd(kick_speed=5.0), wheels)   # ball leaves while kicking
    assert c2 == pytest.approx(0.0, abs=1e-3)
    b3, c3 = hw.update(key, 3.0 + 1e-3, r_free, RobotCmd(), wheels)  # one time constant later
    assert c3 == pytest.approx(1.0 - math.exp(-1.0), abs=1e-3) and b3 < b2
    b4, c4 = hw.update(key, 30.0, r_free, RobotCmd(), (0.0,) * 4)   # no motion: battery holds, capacitor full
    assert b4 == pytest.approx(b3) and c4 == pytest.approx(1.0, abs=1e-5)
    # losing the ball without a kick command is not a kick
    hw.update(key, 31.0, r_ball, RobotCmd(), (0.0,) * 4)
    _, c5 = hw.update(key, 32.0, r_free, RobotCmd(), (0.0,) * 4)
    assert c5 == pytest.approx(1.0, abs=1e-5)
    # through twin_telemetry the record is flagged illustrative
    rec = twin_telemetry(_ws(t=40.0), key, RobotCmd(), hardware=hw)
    assert rec is not None and rec.hardware_illustrative and 0.0 <= rec.battery <= 1.0 and rec.capacitor == pytest.approx(1.0, abs=1e-4)
    hw.reset()
    assert hw.update(key, 50.0, r_free, RobotCmd(), (0.0,) * 4)[0] == 1.0


# ---------------------------------------------------------------- radio side
def test_parse_feedback_bare_wrapped_command_and_garbage():
    data = _fb(id=3, vx=0.5, vy=-0.1, w=0.2, batteryCharge=15.9, capacitorCharge=180.0, hasBall=True,
               c_speed_m1=10.0, c_speed_m2=11.0, c_speed_m3=12.0, c_speed_m4=13.0, d_speed_m1=9.5,
               pwm_m3=0.25, error_m4=-0.5, current_m2=1.5)
    r = parse_feedback(data, team="yellow", t=1.0)
    assert isinstance(r, RobotTelemetry) and r.source == "real" and r.team == "yellow" and r.id == 3 and r.t == 1.0
    assert (r.vx, r.vy, r.w) == (0.5, -0.1, 0.2)
    assert r.wheel_meas == (10.0, 11.0, 12.0, 13.0) and r.wheel_cmd == (9.5, 0.0, 0.0, 0.0)
    assert r.battery == 15.9 and r.capacitor == 180.0 and r.has_ball and not r.hardware_illustrative
    assert r.pwm == (0.0, 0.0, 0.25, 0.0) and r.error == (0.0, 0.0, 0.0, -0.5) and r.current == (0.0, 1.5, 0.0, 0.0)
    assert r.cmd_vx is None and r.pose is None
    # the field mapping can be swapped in config/telemetry.json
    s = parse_feedback(data, fields={"wheel_meas": "d_speed", "wheel_cmd": "c_speed"})
    assert s.wheel_cmd == (10.0, 11.0, 12.0, 13.0) and s.wheel_meas == (9.5, 0.0, 0.0, 0.0)
    # a Feedback inside a WrapperMessage is accepted too
    wm = RCWrapperMessage()
    wm.feedback.ParseFromString(data)
    w = parse_feedback(wm.SerializeToString(), t=2.0)
    assert w is not None and w.id == 3 and w.wheel_meas == (10.0, 11.0, 12.0, 13.0)
    # a command list (what the strategy sends to the robots) and garbage are not telemetry
    cl = RCWrapperMessage()
    cl.command.speed.add(id=1, vx=1.0)
    assert parse_feedback(cl.SerializeToString()) is None
    assert parse_feedback(b"\xff\xff\x01") is None


def test_receiver_ingests_and_expires_records():
    rx = TelemetryReceiver(ip="127.0.0.1", port=0, team="blue", history=3)       # unicast socket, never started
    try:
        assert rx.latest(1) is None and rx.ids() == [] and rx.rate_hz == 0.0
        for k in range(5):
            rx.ingest(_fb(id=1, vx=0.1 * k), t=100.0 + 0.1 * k)
        rx.ingest(_fb(id=4, vx=2.0), t=100.4)
        assert rx.packets == 6 and rx.ids() == [1, 4]
        rec = rx.latest(1, now=100.9)
        assert rec is not None and rec.team == "blue" and rec.vx == pytest.approx(0.4)
        assert rx.latest(1, now=101.6) is None                                   # older than stale_s (1.0)
        assert len(rx.history(1)) == 3 and [h.vx for h in rx.history(1)] == pytest.approx([0.2, 0.3, 0.4])
        assert rx.rate_hz == pytest.approx(5 / 0.4)
        assert rx.ingest(b"\xff\xff\x01") is None and rx.decode_errors == 1
    finally:
        rx.stop()


@pytest.mark.requires_net
def test_receiver_thread_reads_datagrams_from_the_socket():
    rx = TelemetryReceiver(ip="127.0.0.1", port=0, team="yellow")
    port = rx.sock.getsockname()[1]
    rx.start()
    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for k in range(3):
            tx.sendto(_fb(id=2, w=1.0 + k, batteryCharge=16.0), ("127.0.0.1", port))
            time.sleep(0.02)
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and rx.packets < 3:
            time.sleep(0.01)
        rec = rx.latest(2)
        assert rx.packets == 3 and rec is not None and rec.w == 3.0 and rec.battery == 16.0
        assert rx.endpoint == f"127.0.0.1:{port}"
    finally:
        tx.close()
        rx.stop()
        rx.join(timeout=2.0)


# ---------------------------------------------------------------- config
def test_telemetry_config_defaults_and_merge(tmp_path):
    cfg = load_telemetry_config(tmp_path / "missing.json")
    assert cfg == DEFAULT_CONFIG and cfg is not DEFAULT_CONFIG
    p = tmp_path / "telemetry.json"
    p.write_text(json.dumps({"real": {"enabled": True, "port": 20000, "units": {"battery": "V"}},
                             "synthetic": {"capacitor_tau_s": 4.0}}), encoding="utf-8")
    cfg = load_telemetry_config(p)
    assert cfg["real"]["enabled"] is True and cfg["real"]["port"] == 20000 and cfg["real"]["ip"] == "224.0.1.99"
    assert cfg["real"]["units"]["battery"] == "V" and "capacitor" in cfg["real"]["units"]   # merged, not replaced
    assert cfg["synthetic"]["capacitor_tau_s"] == 4.0 and cfg["synthetic"]["illustrative"] is True
    repo_cfg = load_telemetry_config()                                        # the committed config/telemetry.json
    assert repo_cfg["real"]["enabled"] is False and repo_cfg["real"]["port"] == 19903
