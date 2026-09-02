"""dtssl.gui: MainWindow / Controller / FieldView / ParamsPanel / plots, offscreen (requires_gui)."""
from __future__ import annotations

import json
import math
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from PySide6 import QtCore, QtWidgets  # noqa: E402
from PySide6.QtCore import QPointF  # noqa: E402

from dtssl.gui.controller import Controller, Frame, commanded  # noqa: E402
from dtssl.gui.field_view import MM, FieldView, RobotItem  # noqa: E402
from dtssl.gui.params_panel import BOUNDS, ORDER, ParamsPanel, params_from_dict, params_to_dict  # noqa: E402
from dtssl.gui.plots import RingBuffer, VelocityPlots  # noqa: E402
from dtssl.models import DofParam, load_twin_params  # noqa: E402
from dtssl.sim.entities import RobotCmd  # noqa: E402
from dtssl.sim.twin_world import TwinWorld  # noqa: E402

pytestmark = pytest.mark.requires_gui

NET_CFG = {"vision": {"ip": "127.0.0.1", "port": 10997, "unicast_targets": []},   # unicast, no listener
           "control": {"port_blue": 0, "port_yellow": 0, "port_simcontrol": 0}}       # ephemeral ports


@pytest.fixture(scope="module")
def qapp():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(["dtssl-tests"])
    yield app


def _spin(app, ms: int) -> None:
    t = QtCore.QElapsedTimer()
    t.start()
    while t.elapsed() < ms:
        app.processEvents()


# --------------------------------------------------------------------------- FieldView
def test_fieldview_coordinate_roundtrip(qapp):
    v = FieldView()
    v.resize(900, 600)
    v.show()
    qapp.processEvents()
    pt = v.scene_from_mm(1234.0, -567.0)
    assert v.mm_from_scene(pt) == (1234.0, -567.0)
    assert v.m_from_scene(v.scene_from_m(1.234, -0.567)) == pytest.approx((1.234, -0.567))
    px = v.px_from_m(1.234, -0.567)
    assert v.m_from_px(px) == pytest.approx((1.234, -0.567), abs=1e-9)
    up = v.px_from_m(1.234, 0.5)
    assert up.y() < px.y()                                     # +y is drawn upwards
    right = v.px_from_m(2.0, -0.567)
    assert right.x() > px.x()
    assert v.px_per_mm() > 0.0
    # zoom keeps the flip and the round trip
    v.scale(2.0, 2.0)
    assert v.m_from_px(v.px_from_m(-3.0, 2.0)) == pytest.approx((-3.0, 2.0), abs=1e-9)
    assert v.px_from_m(0.0, 1.0).y() < v.px_from_m(0.0, 0.0).y()
    v.close()


def test_fieldview_items_reused_and_trails(qapp):
    world = TwinWorld("fopdt", n_blue=2, n_yellow=1)
    v = FieldView(world.field)
    v.resize(800, 500)
    v.show()
    ws = world.step()
    v.update_state(ws, selected=("blue", 1))
    assert set(v.robots) == {("blue", 0), ("blue", 1), ("yellow", 0)}
    items = dict(v.robots)
    assert v.robots[("blue", 1)].selected_ and not v.robots[("blue", 0)].selected_
    world.teleport_robot("blue", 1, 1.5, -0.5, 0.5)
    world.teleport_ball(2.0, 1.0)
    ws = world.step()
    v.update_state(ws, selected=("blue", 1), truth_pose=(1.0, 1.0, 0.0))
    assert dict(v.robots) == items                              # no re-creation
    it = v.robots[("blue", 1)]
    assert it.pos().x() == pytest.approx(ws.robots[("blue", 1)].x * MM)
    assert it.rotation() == pytest.approx(math.degrees(ws.robots[("blue", 1)].theta))
    assert v.ball.pos().x() == pytest.approx(2.0 * MM) and v.ball.pos().y() == pytest.approx(1.0 * MM)
    assert len(v.sim_trail.points) == 2 and len(v.truth_trail.points) == 1
    assert v.truth_robot is not None and v.truth_robot.isVisible()
    world.set_present("yellow", 0, False)
    v.update_state(world.step(), selected=("blue", 1))
    assert not v.robots[("yellow", 0)].isVisible() and not v.truth_robot.isVisible()
    assert v.robot_at(QPointF(1.5 * MM + 50.0, -0.5 * MM)) == ("blue", 1)
    v.set_selected(None)
    assert not it.selected_ and len(v.sim_trail.points) == 0
    v.close()


def test_fieldview_click_signals(qapp):
    v = FieldView()
    v.resize(900, 600)
    v.show()
    qapp.processEvents()
    got = {}
    v.robot_teleport_requested.connect(lambda x, y: got.__setitem__("robot", (x, y)))
    v.ball_teleport_requested.connect(lambda x, y: got.__setitem__("ball", (x, y)))
    from PySide6.QtTest import QTest

    target = v.px_from_m(1.0, 0.5).toPoint()
    QTest.mouseClick(v.viewport(), QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, target)
    assert got["robot"] == pytest.approx((1.0, 0.5), abs=0.02)
    target = v.px_from_m(-2.0, -1.0).toPoint()
    QTest.mouseClick(v.viewport(), QtCore.Qt.RightButton, QtCore.Qt.NoModifier, target)
    assert got["ball"] == pytest.approx((-2.0, -1.0), abs=0.02)
    v.close()


def test_robot_item_flat_front_shape(qapp):
    it = RobotItem("blue", 3, radius_mm=90.0, front_mm=75.0)
    sh = it.shape()
    assert sh.contains(QPointF(0.0, 0.0)) and sh.contains(QPointF(-85.0, 0.0))
    assert not sh.contains(QPointF(85.0, 0.0))                  # cut by the dribbler face at 75 mm
    assert sh.contains(QPointF(70.0, 0.0))


# --------------------------------------------------------------------------- plots
def test_ring_buffer_and_plots_modes(qapp):
    rb = RingBuffer(4, 2)
    for k in range(6):
        rb.append((k, -k))
    assert rb.data()[:, 0].tolist() == [2, 3, 4, 5] and len(rb) == 4
    p = VelocityPlots(window_s=2.0)
    p.resize(400, 600)
    p.show()
    for k in range(200):
        p.append(k / 60.0, (1.0, 0.0, 0.0), (0.5, 0.1, 0.2))
    p.redraw()
    assert p.samples == 200 and p.redraws == 1
    x = p.sim_curves[0].xData
    assert x is not None and x[-1] == pytest.approx(199 / 60.0) and x[0] >= 199 / 60.0 - 2.0 - 1e-9
    assert not p.epos_plot.isVisible()
    p.set_mode("fixed")
    import numpy as np

    t = np.arange(0, 3, 1 / 60)
    z = np.zeros((t.size, 3))
    p.set_series(t, z, z, z, epos=0.1 * t, horizons_s=[0.1, 0.4], horizons_labels=["h=6", "h=24"])
    assert p.epos_plot.isVisible() and len(p.epos_curve.xData) == t.size
    assert len(p._horizon_items) == 2 and len(p.epos_markers.data) == 2
    p.set_playhead(1.5)
    p.redraw()
    assert p.playheads[0].value() == pytest.approx(1.5) and p.epos_playhead.value() == pytest.approx(1.5)
    p.set_mode("sliding")
    assert p.samples == 0 and not p.epos_plot.isVisible()
    p.close()


# --------------------------------------------------------------------------- params panel
def test_params_panel_json_roundtrip_and_presets(qapp, tmp_path):
    panel = ParamsPanel()
    official = load_twin_params()
    for d in ("vx", "vy", "w"):
        for name in ("K", "tau", "Td"):
            assert getattr(panel.params()[d], name) == pytest.approx(getattr(official[d], name), abs=5e-5)
    d = panel.to_dict(note="test")
    assert d["order"] == list(ORDER) and set(d["dof"]) == {"vx", "vy", "w"} and d["ts"] == pytest.approx(1 / 60)
    assert params_from_dict(d)["w"].Td == pytest.approx(official["w"].Td, abs=5e-5)
    path = panel.save_json(tmp_path / "theta.json", note="rt")
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["order"] == list(ORDER) and saved["note"] == "rt"
    # a foreign theta round-trips through the panel (values inside the bounds)
    custom = {"vx": DofParam(0.9, 0.05, 0.02), "vy": DofParam(1.3, 0.2, 0.0), "w": DofParam(1.0, 0.1, 0.0, True)}
    (tmp_path / "custom.json").write_text(json.dumps(params_to_dict(custom)), encoding="utf-8")
    loaded = panel.load_json(tmp_path / "custom.json")
    assert loaded == custom and panel.params() == custom
    assert panel.placeholders["w"].isChecked()
    applied = {}
    panel.apply_requested.connect(lambda p: applied.update(p))
    assert panel.apply() == custom and applied == custom
    # presets
    p = panel.apply_preset("ideal")
    assert all(p[d] == DofParam(1.0, 0.01, 0.0) for d in ("vx", "vy", "w"))
    p = panel.apply_preset("ω placeholder")
    assert p["w"] == DofParam(1.0, 0.1, 0.0, True) and p["vx"].K == pytest.approx(official["vx"].K)
    p = panel.apply_preset("oficial")
    assert p["w"].K == pytest.approx(official["w"].K) and not p["w"].placeholder
    # bounds are enforced (out-of-range values are clipped and reported)
    panel.set_params({"vx": DofParam(5.0, 0.0, 1.0), "vy": official["vy"], "w": official["w"]})
    assert panel.params()["vx"] == DofParam(BOUNDS["K"][1], BOUNDS["tau"][0], BOUNDS["Td"][1])
    assert "clipped" in panel.status.text()
    with pytest.raises(KeyError):
        panel.apply_preset("nope")


# --------------------------------------------------------------------------- controller + window
def test_window_constructs_and_one_tick_updates_views(qapp):
    from dtssl.gui.app import MainWindow

    win = MainWindow(backend="fopdt", mode="debug", team="yellow", n_blue=2, n_yellow=2, use_pygame=False,
                     autostart=False)
    win.show()
    qapp.processEvents()
    c = win.controller
    assert isinstance(c.world, TwinWorld) and c.mode == "debug" and c.selected == ("yellow", 0)
    assert c.joystick.name == "keyboard" and not c.server_running
    assert win.backend_box.currentText() == "fopdt" and win.robot_box.count() == 2
    frames0, samples0 = win.field_view.frames, win.plots.samples
    c.kb.press("w")                                            # keyboard fallback drives the robot
    c._on_joy_tick()
    assert c.joy_cmd.vx >= 0.0
    ws = c.tick(3)                                             # three world steps at 60 Hz
    c._on_render()
    win.plots.redraw()
    assert ws.frame == 3 and win.field_view.frames == frames0 + 1 and win.plots.samples == samples0 + 3
    assert len(win.plots.sim_curves[0].xData) == 3
    it = win.field_view.robots[("yellow", 0)]
    r = ws.robots[("yellow", 0)]
    assert it.pos().x() == pytest.approx(r.x * MM) and it.pos().y() == pytest.approx(r.y * MM)
    assert commanded(c.world, ("yellow", 0)).vx == pytest.approx(c.joy_cmd.vx)
    c.kb.release_all()
    # teleports through the field-view signals
    win.field_view.robot_teleport_requested.emit(1.0, -1.0)
    win.field_view.ball_teleport_requested.emit(0.5, 0.5)
    st = c.latest_state()
    assert st.robots[("yellow", 0)].x == pytest.approx(1.0) and st.ball.x == pytest.approx(0.5)
    # robot selection (D-pad / combo)
    c.select_next()
    assert c.selected == ("yellow", 1) and win.robot_box.currentIndex() == 1
    c.select_prev()
    assert c.selected == ("yellow", 0)
    win.team_box.setCurrentText("blue")
    assert c.selected == ("blue", 0)
    # parameter hot-swap without resetting the pose
    x_before = c.latest_state().robots[("blue", 0)].x
    new = dict(load_twin_params())
    new["vx"] = DofParam(1.5, 0.2, 0.1)
    win.params_panel.set_params(new)
    win.params_panel.apply()
    assert c.world.plants[("blue", 0)].K[0] == pytest.approx(1.5)
    assert c.latest_state().robots[("blue", 0)].x == pytest.approx(x_before)
    # stats + status bar
    win._on_stats(c.stats())
    assert "keyboard" in win.status_labels["joystick"].text()
    win.close()


def test_controller_timers_run_at_60hz(qapp):
    c = Controller(backend="fopdt", mode="debug", team="blue", n_blue=1, n_yellow=1, use_pygame=False)
    frames = []
    samples = []
    c.frame_ready.connect(frames.append)
    c.sample_ready.connect(lambda t, cmd, sim, truth: samples.append(t))
    c.start()
    _spin(qapp, 700)
    c.stop()
    st = c.stats()
    assert 40 <= len(samples) <= 60 and 15 <= len(frames) <= 30
    assert 50.0 <= st["hz"] <= 70.0 and st["sim_time"] == pytest.approx(len(samples) / 60.0, abs=0.05)
    assert isinstance(frames[-1], Frame) and frames[-1].selected == ("blue", 0)
    c.shutdown()


def test_controller_backend_switch_and_reset(qapp):
    c = Controller(backend="fopdt", mode="debug", team="blue", n_blue=1, n_yellow=1, use_pygame=False)
    c.set_backend("ideal")
    assert c.backend == "ideal" and c.world.name == "TwinWorld[ideal]"
    c.world.set_command("blue", 0, RobotCmd(vx=1.0))
    c.world.step()
    assert c.world.robot("blue", 0).vx_b == pytest.approx(1.0)
    with pytest.raises(KeyError):
        c.set_backend("no-such-backend")
    c.set_backend("fopdt")
    assert c.backend == "fopdt"
    c.teleport_selected(2.0, 1.0)
    c.reset_scene()
    assert c.latest_state().robots[("blue", 0)].x == pytest.approx(-2.25)
    c.shutdown()


@pytest.mark.requires_net
def test_controller_bridge_mode_thread_and_step(qapp):
    c = Controller(backend="fopdt", mode="bridge", team="blue", n_blue=1, n_yellow=1, bridge_config=NET_CFG,
                   use_pygame=False)
    assert c.server_running and not c.server.step_mode and c._server_thread is not None
    samples = []
    c.sample_ready.connect(lambda t, cmd, sim, truth: samples.append(t))
    c.start()
    _spin(qapp, 600)
    assert len(samples) >= 20 and c.stats()["packets"]["vision"] > 10
    assert c.teleport_selected(1.0, 1.0) and c.teleport_ball(0.3, 0.3)
    _spin(qapp, 100)
    assert c.latest_state().robots[("blue", 0)].x == pytest.approx(1.0, abs=1e-6)
    c.set_realtime(False)
    assert c.server_running and c.server.step_mode and c._server_thread is None
    n0 = c.server.ticks
    _spin(qapp, 300)
    assert c.server.ticks > n0 + 10
    c.set_mode("debug")
    assert not c.server_running
    c.set_publish(True)
    assert c.server_running and c.server.step_mode
    c.stop()
    c.shutdown()
    assert c.server is None


@pytest.mark.requires_data
def test_window_replay_mode_real_event(qapp):
    from dtssl.gui.app import MainWindow

    win = MainWindow(backend="fopdt", mode="replay", team="blue", n_blue=1, n_yellow=1, use_pygame=False,
                     autostart=False)
    win.show()
    qapp.processEvents()
    assert win.replay_toolbar.isVisible() and win.dataset_box.count() >= 1
    sess = win.load_replay("side_to_side", "side_to_side_01_05")
    assert sess is not None and win.event_box.currentText() == "side_to_side_01_05"
    assert win.slider.maximum() == sess.n - 1 and win.plots.mode == "fixed"
    assert len(win.plots.truth_curves[0].xData) == sess.n and len(win.plots._horizon_items) == 6
    c = win.controller
    assert c.selected == ("blue", int(sess.seg.meta["robot_id"]))
    c.tick(5)
    c._on_render()
    assert sess.index == 5 and win.slider.value() == 5
    fv = win.field_view
    assert fv.truth_robot is not None and fv.truth_robot.isVisible() and not fv.ball.isVisible()
    assert fv.robots[c.selected].pos().x() == pytest.approx(sess.pose_sim[5, 0] * MM)
    assert fv.truth_robot.pos().x() == pytest.approx(sess.truth[5, 0] * MM)
    assert not c.teleport_selected(0.0, 0.0)                    # no teleports in replay
    e_before = sess.epos_at_horizons()
    win.params_panel.apply_preset("ideal")
    win.params_panel.apply()
    assert sess.epos_at_horizons() != e_before
    win.speed_box.setCurrentIndex(2)
    assert sess.speed == 2.0
    c.replay_play()
    c.start()
    _spin(qapp, 400)
    c.stop()
    assert sess.index > 20
    win.close()


def test_cli_registers_gui_command():
    from dtssl.cli import build_parser
    from dtssl.gui.cli import build_parser as gui_parser

    ap, status = build_parser()
    assert status.get("dtssl.gui.cli") is None
    sub = next(a for a in ap._actions if hasattr(a, "choices") and a.choices and "gui" in a.choices)
    assert "gui" in sub.choices
    args = gui_parser().parse_args(["--backend", "ideal", "--mode", "bridge", "--team", "blue",
                                    "--joy-map", "dualsense-raw-linux"])
    assert (args.backend, args.mode, args.team, args.joy_map) == ("ideal", "bridge", "blue", "dualsense-raw-linux")
