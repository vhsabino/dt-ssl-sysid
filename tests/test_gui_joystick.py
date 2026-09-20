"""dtssl.gui.joystick / keyboard: mapping with a fake provider (no Qt, no pygame needed)."""
from __future__ import annotations

import importlib.util
import json
import math

import pytest

from dtssl.gui.joystick import (
    DEFAULT_AXES,
    DEFAULT_BUTTONS,
    EVENT_DRIBBLER_OFF,
    EVENT_DRIBBLER_ON,
    EVENT_KICK_CHIP,
    EVENT_KICK_FLAT,
    EVENT_NEXT_ROBOT,
    EVENT_PREV_ROBOT,
    EVENT_STOP,
    EVENT_TELEPORT_CENTER,
    CmdLimits,
    FakeProvider,
    JoyMap,
    JoystickReader,
    apply_deadzone_expo,
    apply_deadzone_expo_1d,
    expo_curve,
    map_state,
    read_state,
)
from dtssl.gui.keyboard import KEY_BINDINGS, KeyboardProvider
from dtssl.sim.world import RobotSpec

LIM = CmdLimits(v_max=3.0, w_max=10.0, kick_flat_max=6.5, kick_chip_max=6.0, chip_angle_deg=45.0,
                dribbler_rpm_max=6000.0)


def _reader(provider: FakeProvider, joy_map: JoyMap | None = None) -> JoystickReader:
    return JoystickReader(LIM, joy_map, provider=provider)


# --------------------------------------------------------------------------- curves
def test_deadzone_and_expo_curve():
    assert expo_curve(1.0, 0.3) == pytest.approx(1.0)
    assert expo_curve(-1.0, 0.3) == pytest.approx(-1.0)
    assert expo_curve(0.5, 0.3) == pytest.approx(0.7 * 0.5 + 0.3 * 0.125)
    assert apply_deadzone_expo(0.05, 0.03, 0.08, 0.3) == (0.0, 0.0)          # inside the radial deadzone
    x, y = apply_deadzone_expo(1.0, 0.0, 0.08, 0.3)
    assert x == pytest.approx(1.0) and y == pytest.approx(0.0)              # full deflection reaches 1
    x, y = apply_deadzone_expo(0.6, 0.8, 0.08, 0.3)                          # magnitude 1 on a diagonal
    assert math.hypot(x, y) == pytest.approx(1.0)
    assert x / y == pytest.approx(0.75)                                      # direction preserved
    assert apply_deadzone_expo_1d(0.07, 0.08, 0.3) == 0.0
    assert apply_deadzone_expo_1d(-1.0, 0.08, 0.3) == pytest.approx(-1.0)
    # monotone
    vals = [apply_deadzone_expo_1d(v / 20.0, 0.08, 0.3) for v in range(21)]
    assert all(b >= a for a, b in zip(vals[:-1], vals[1:], strict=True))


# --------------------------------------------------------------------------- sticks -> RobotCmd
def test_sticks_map_to_body_velocity_with_scale_and_turbo():
    fp = FakeProvider()
    rd = _reader(fp)
    fp.set_axis(DEFAULT_AXES["ly"], -1.0)                    # stick forward
    cmd, ev = rd.read()
    assert cmd.vx == pytest.approx(3.0 * 0.5) and cmd.vy == 0.0 and cmd.w == 0.0
    assert not rd.turbo and cmd.kick_speed == 0.0 and cmd.dribbler_rpm == 0.0
    fp.set_axis(DEFAULT_AXES["r2"], 1.0)                     # turbo
    cmd, _ = rd.read()
    assert rd.turbo and cmd.vx == pytest.approx(3.0)
    fp.set_axis(DEFAULT_AXES["ly"], 0.0)
    fp.set_axis(DEFAULT_AXES["lx"], 1.0)                     # stick right -> vy negative (body y = left)
    cmd, _ = rd.read()
    assert cmd.vy == pytest.approx(-3.0) and cmd.vx == pytest.approx(0.0)
    fp.set_axis(DEFAULT_AXES["lx"], 0.0)
    fp.set_axis(DEFAULT_AXES["rx"], 1.0)                     # right stick right -> clockwise (w < 0)
    cmd, _ = rd.read()
    assert cmd.w == pytest.approx(-10.0)
    fp.set_axis(DEFAULT_AXES["rx"], -0.5)
    fp.set_axis(DEFAULT_AXES["r2"], 0.0)
    cmd, _ = rd.read()
    assert 0.0 < cmd.w < 5.0                                 # expo below linear, half scale


def test_deadzone_zeroes_small_inputs():
    fp = FakeProvider()
    rd = _reader(fp)
    fp.set_axis(DEFAULT_AXES["ly"], -0.05)
    fp.set_axis(DEFAULT_AXES["lx"], 0.04)
    fp.set_axis(DEFAULT_AXES["rx"], 0.07)
    cmd, _ = rd.read()
    assert cmd.vx == 0.0 and cmd.vy == 0.0 and cmd.w == 0.0


# --------------------------------------------------------------------------- buttons / events
def test_buttons_kicks_dribbler_and_events():
    fp = FakeProvider()
    rd = _reader(fp)
    rd.read()
    fp.set_button(DEFAULT_BUTTONS["cross"], True)
    cmd, ev = rd.read()
    assert cmd.kick_speed == 6.5 and cmd.kick_angle_deg == 0.0 and EVENT_KICK_FLAT in ev
    cmd, ev = rd.read()                                      # held: still armed, no new edge event
    assert cmd.kick_speed == 6.5 and EVENT_KICK_FLAT not in ev
    fp.set_button(DEFAULT_BUTTONS["cross"], False)
    fp.set_button(DEFAULT_BUTTONS["circle"], True)
    cmd, ev = rd.read()
    assert cmd.kick_speed == 6.0 and cmd.kick_angle_deg == 45.0 and EVENT_KICK_CHIP in ev
    fp.set_button(DEFAULT_BUTTONS["circle"], False)
    fp.set_button(DEFAULT_BUTTONS["r1"], True)
    cmd, ev = rd.read()
    assert EVENT_DRIBBLER_ON in ev and rd.dribbler_on and cmd.dribbler_rpm == pytest.approx(3000.0)
    fp.set_button(DEFAULT_BUTTONS["r1"], False)
    cmd, ev = rd.read()
    assert cmd.dribbler_rpm == pytest.approx(3000.0) and not ev   # toggle: stays on after release
    fp.set_button(DEFAULT_BUTTONS["r1"], True)
    cmd, ev = rd.read()
    assert EVENT_DRIBBLER_OFF in ev and cmd.dribbler_rpm == 0.0
    fp.set_button(DEFAULT_BUTTONS["r1"], False)
    fp.set_button(DEFAULT_BUTTONS["options"], True)
    _, ev = rd.read()
    assert ev == [EVENT_TELEPORT_CENTER]
    fp.set_button(DEFAULT_BUTTONS["options"], False)
    fp.set_button(DEFAULT_BUTTONS["r1"], True)
    rd.read()                                                # dribbler on again
    fp.set_button(DEFAULT_BUTTONS["ps"], True)
    fp.set_axis(DEFAULT_AXES["ly"], -1.0)
    cmd, ev = rd.read()
    assert EVENT_STOP in ev and cmd.vx == 0.0 and cmd.dribbler_rpm == 0.0 and not rd.dribbler_on


def test_dpad_from_buttons_and_hat_selects_robots():
    fp = FakeProvider()
    rd = _reader(fp)
    rd.read()
    fp.set_button(DEFAULT_BUTTONS["dpad_right"], True)
    _, ev = rd.read()
    assert ev == [EVENT_NEXT_ROBOT]
    _, ev = rd.read()
    assert ev == []                                          # edge only
    fp.set_button(DEFAULT_BUTTONS["dpad_right"], False)
    fp.set_button(DEFAULT_BUTTONS["dpad_left"], True)
    _, ev = rd.read()
    assert ev == [EVENT_PREV_ROBOT]
    fp.set_button(DEFAULT_BUTTONS["dpad_left"], False)
    rd.read()
    # raw joystick with a hat (no dpad buttons)
    raw = FakeProvider(name="Wireless Controller", n_buttons=13, gamecontroller=False)
    rd2 = _reader(raw, JoyMap.dualsense_raw_linux())
    rd2.read()
    raw.set_hat(1, 0)
    _, ev = rd2.read()
    assert ev == [EVENT_NEXT_ROBOT]
    raw.set_hat(-1, 0)
    _, ev = rd2.read()
    assert ev == [EVENT_PREV_ROBOT]


def test_raw_trigger_range_signed_vs_unit():
    gc = FakeProvider(gamecontroller=True)
    st = read_state(gc, JoyMap.default())
    assert st.r2 == 0.0
    gc.set_axis(DEFAULT_AXES["r2"], 0.6)
    assert read_state(gc, JoyMap.default()).r2 == pytest.approx(0.6)
    raw = FakeProvider(name="Wireless Controller", gamecontroller=False)
    m = JoyMap.dualsense_raw_linux()
    raw.set_axis(m.axes["r2"], -1.0)                         # rest position on the raw API
    assert read_state(raw, m).r2 == 0.0
    raw.set_axis(m.axes["r2"], 1.0)
    assert read_state(raw, m).r2 == pytest.approx(1.0)
    raw.set_axis(m.axes["r2"], 0.2)                          # 60 % pressed
    cmd, _, _ = map_state(read_state(raw, m), None, LIM, m, False)
    assert cmd.vx == 0.0                                     # no stick input, but turbo threshold crossed
    raw.set_axis(m.axes["ly"], -1.0)
    cmd, _, _ = map_state(read_state(raw, m), None, LIM, m, False)
    assert cmd.vx == pytest.approx(3.0)


def test_disconnected_provider_gives_zero_command():
    fp = FakeProvider()
    rd = _reader(fp)
    fp.set_axis(DEFAULT_AXES["ly"], -1.0)
    assert rd.read()[0].vx > 0
    fp.disconnect()
    cmd, _ = rd.read()
    assert cmd.vx == 0.0 and not rd.connected


# --------------------------------------------------------------------------- JoyMap JSON
def test_joymap_json_roundtrip_and_partial_override(tmp_path):
    m = JoyMap.dualsense_raw_linux()
    p = m.save(tmp_path / "map.json")
    back = JoyMap.load(p)
    assert back == m
    partial = {"base": "gamecontroller", "buttons": {"r1": 5}, "axes": {"rx": 3}, "deadzone": 0.1, "name": "custom"}
    (tmp_path / "partial.json").write_text(json.dumps(partial), encoding="utf-8")
    m2 = JoyMap.load(tmp_path / "partial.json")
    assert m2.buttons["r1"] == 5 and m2.buttons["cross"] == 0 and m2.axes["rx"] == 3 and m2.axes["lx"] == 0
    assert m2.deadzone == 0.1 and m2.name == "custom"
    assert JoyMap.load("dualsense-raw-windows").buttons["cross"] == 1
    with pytest.raises(KeyError):
        JoyMap.preset("nope")


def test_cmdlimits_from_robot_spec():
    lim = CmdLimits.from_spec(RobotSpec())
    assert lim.v_max == 3.0 and lim.w_max == 10.0 and lim.kick_flat_max == 6.5 and lim.dribbler_on_rpm == 3000.0


# --------------------------------------------------------------------------- keyboard fallback
def test_keyboard_provider_ramps_and_maps_like_a_pad():
    clock = {"t": 0.0}
    kb = KeyboardProvider(ramp_s=0.2, clock=lambda: clock["t"])
    rd = JoystickReader(LIM, provider=kb)
    assert set(KEY_BINDINGS) >= {"w", "a", "s", "d", "q", "e", "space", "c", "r", "shift"}
    assert kb.press("W") and not kb.press("z")
    clock["t"] = 0.1
    cmd, _ = rd.read()
    assert 0.0 < cmd.vx < 1.5                                # ramping up (half way, minus expo)
    clock["t"] = 0.5
    cmd, _ = rd.read()
    assert cmd.vx == pytest.approx(1.5)                      # full deflection, normal scale
    kb.press("shift")
    clock["t"] = 0.6
    cmd, _ = rd.read()
    assert cmd.vx == pytest.approx(3.0) and rd.turbo
    kb.release("w")
    kb.press("s")
    kb.press("w")                                            # opposite keys cancel
    clock["t"] = 1.5
    cmd, _ = rd.read()
    assert cmd.vx == pytest.approx(0.0)
    kb.release_all()
    kb.press("q")                                            # CCW
    clock["t"] = 2.5
    cmd, _ = rd.read()
    assert cmd.w == pytest.approx(5.0)
    kb.release_all()
    kb.press("space")
    cmd, ev = rd.read()
    assert cmd.kick_speed == 6.5 and EVENT_KICK_FLAT in ev
    kb.release_all()
    kb.press(".")
    _, ev = rd.read()
    assert ev == [EVENT_NEXT_ROBOT]
    kb.release_all()
    kb.press("r")
    cmd, ev = rd.read()
    assert EVENT_DRIBBLER_ON in ev and cmd.dribbler_rpm > 0


def test_reader_falls_back_to_keyboard_without_pygame():
    kb = KeyboardProvider(ramp_s=0.0)
    rd = JoystickReader(LIM, fallback=kb, use_pygame=False)
    assert not rd.connected and rd.name == "keyboard"
    kb.press("d")
    cmd, _ = rd.read()
    assert cmd.vy < 0.0


@pytest.mark.skipif(importlib.util.find_spec("pygame") is None, reason="pygame not installed")
def test_pygame_backend_headless_scan():
    """pygame initialises without a display; with no pad the reader uses the keyboard fallback."""
    from dtssl.gui.joystick import PygameBackend

    be = PygameBackend()
    assert be.ok
    names = be.device_names()
    assert isinstance(names, list)
    rd = JoystickReader(LIM, fallback=KeyboardProvider(), use_pygame=True)
    cmd, _ = rd.read()
    assert isinstance(cmd.vx, float)
    if not names:
        assert rd.name == "keyboard"
    rd.close()


def test_hotplug_rescan_switches_between_pad_and_keyboard():
    class Backend:
        def __init__(self):
            self.dev = None

        def open_best(self):
            return self.dev

    kb = KeyboardProvider(ramp_s=0.0)
    rd = JoystickReader(LIM, fallback=kb, use_pygame=False, rescan_s=0.0)
    be = Backend()
    rd.backend = be
    assert rd.name == "keyboard" and not rd.connected
    pad = FakeProvider(name="Sony DualSense Wireless Controller")
    be.dev = pad
    _, ev = rd.read()
    assert rd.connected and rd.name == pad.name and any(e.startswith("connected:") for e in ev)
    pad.set_axis(DEFAULT_AXES["ly"], -1.0)
    assert rd.read()[0].vx > 0.0
    pad.disconnect()
    be.dev = None
    _, ev = rd.read()
    assert "disconnected" in ev and not rd.connected and rd.name == "keyboard"
    kb.press("w")
    assert rd.read()[0].vx > 0.0                              # keyboard took over
