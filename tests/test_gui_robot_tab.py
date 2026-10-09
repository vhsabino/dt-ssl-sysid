"""Robot tab of dtssl.gui (offscreen, requires_gui): widgets build and paint, the tab follows the selection, the
twin record is drawn from the world state, and a real Feedback record shows up next to it."""
from __future__ import annotations

import math
import os
import time

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

import pyqtgraph as pg  # noqa: E402
from PySide6 import QtCore, QtWidgets  # noqa: E402

from dtssl.bridge.proto import RCFeedback  # noqa: E402
from dtssl.bridge.telemetry import RobotTelemetry, TelemetryReceiver  # noqa: E402
from dtssl.gui.app import MainWindow  # noqa: E402
from dtssl.gui.robot_tab import WHEEL_MAX_RAD_S, RobotSpotlight, RobotTab, WheelBars, WheelPlot  # noqa: E402
from dtssl.sim.entities import RobotCmd  # noqa: E402

pytestmark = pytest.mark.requires_gui

NET_CFG = {"vision": {"ip": "127.0.0.1", "port": 10996, "unicast_targets": []},
           "control": {"port_blue": 0, "port_yellow": 0, "port_simcontrol": 0}}


@pytest.fixture(scope="module")
def qapp():
    yield QtWidgets.QApplication.instance() or QtWidgets.QApplication(["dtssl-tests"])


def _twin(**kw) -> RobotTelemetry:
    base = dict(source="twin", team="yellow", id=2, t=1.0, vx=1.0, vy=0.2, w=0.5, cmd_vx=1.1, cmd_vy=0.1, cmd_w=0.4,
                wheel_cmd=(10.0, -20.0, 30.0, -40.0), wheel_meas=(9.0, -19.0, 29.0, -39.0), has_ball=True,
                dribbler_on=True, cmd_age_s=0.02, watchdog=False, kicks=3, battery=0.8, capacitor=0.5,
                hardware_illustrative=True, pose=(1.0, -0.5, math.pi / 4))
    base.update(kw)
    return RobotTelemetry(**base)


def test_widgets_build_and_paint(qapp):
    sp = RobotSpotlight()
    sp.resize(240, 240)
    sp.show()
    sp.set_record(None)
    img0 = sp.grab()
    sp.set_record(_twin())
    img1 = sp.grab()
    assert img0.width() == 240 and img1 != img0                        # the record changes the picture
    assert RobotSpotlight.wheel_color(0.0).red() == 60
    assert RobotSpotlight.wheel_color(WHEEL_MAX_RAD_S).red() == 255 and RobotSpotlight.wheel_color(-WHEEL_MAX_RAD_S).blue() == 255
    bars = WheelBars()
    bars.resize(300, 120)
    bars.show()
    bars.set_values((10.0, 20.0, 30.0, 40.0), (5.0, -5.0, 200.0, 0.0), (1.0, 1.0, 1.0, 1.0))
    assert bars.grab().width() == 300
    plot = WheelPlot(window_s=2.0)
    assert len(plot.plots) == 4 and [p.getAxis("left").labelText for p in plot.plots] == ["m1", "m2", "m3", "m4"]
    for k in range(200):
        plot.append(k / 60.0, (1.0, 2.0, 3.0, 4.0), (1.5, 2.5, 3.5, 4.5))
    plot.append(1.0, None, None)                                         # not monotonic: ignored
    assert len(plot.buf) == int(2.0 * 60) + 2                             # capped at window * rate (+2)
    plot.redraw()
    lo, hi = plot.plots[0].getViewBox().viewRange()[0]
    assert hi == pytest.approx(199 / 60.0) and lo == pytest.approx(199 / 60.0 - 2.0)
    for p in plot.plots[1:]:                                              # one time axis for the four motors
        assert p.getViewBox().linkedView(pg.ViewBox.XAxis) is plot.plots[0].getViewBox()
    assert plot.curves_meas[2].yData[-1] == 3.5 and plot.curves_cmd[2].yData[-1] == 3.0
    assert not any(c.isVisible() for c in plot.curves_real)              # no real robot: no pink curve
    plot.append(200 / 60.0, (1.0,) * 4, (1.5,) * 4, (9.0, 8.0, 7.0, 6.0))   # the radio reports
    plot.redraw()
    assert all(c.isVisible() for c in plot.curves_real) and plot.curves_real[3].yData[-1] == 6.0
    assert np.isnan(plot.curves_real[3].yData[-2])                       # a gap before the first real sample
    plot.clear_data()
    assert len(plot.buf) == 0 and not any(c.isVisible() for c in plot.curves_real)


def test_tab_renders_twin_and_real_records(qapp):
    tab = RobotTab(units={"battery": "V", "capacitor": "V"})
    tab.resize(1200, 700)
    tab.show()
    qapp.processEvents()
    tab.set_selected(("yellow", 2))
    assert tab.header.text() == "robo 2 (yellow)"
    tab.update_record(_twin(), None)
    L = tab.state_labels
    assert L["pose"].text().startswith("+1.000 m, -0.500 m, +45.0 deg")
    assert L["v_cmd"].text() == "1.100 m/s, 0.100 m/s, 0.400 rad/s"
    assert L["watchdog"].text() == "ok" and L["ball"].text() == "bola no dribbler" and L["kicks"].text() == "3"
    assert "ILUSTRATIVO" in tab.hw_note.text() and tab.battery.bar.value() == 800 and tab.capacitor.bar.format() == "50 %"
    assert "+10.0" in tab.wheel_values.text() and "-39.0" in tab.wheel_values.text()
    assert tab.real_table.item(0, 4).text() == "-"
    # a real record for the same robot: hardware block switches to the radio values, table filled
    real = RobotTelemetry(source="real", team="yellow", id=2, t=time.monotonic(), vx=0.9, vy=0.1, w=0.4,
                          wheel_cmd=(11.0, 0.0, 0.0, 0.0), wheel_meas=(10.5, 0.0, 0.0, 0.0), has_ball=False,
                          battery=16.2, capacitor=175.0, pwm=(0.3, 0.0, 0.0, 0.0), error=(0.0,) * 4,
                          current=(1.25, 0.0, 0.0, 0.0))
    tab.update_record(_twin(), real)
    assert tab.hw_note.text() == "valores do robo real (radio)"
    assert tab.battery.value.text() == "16.20 V" and tab.capacitor.value.text() == "175.00 V"
    assert tab.ir.text().endswith("(real)") and tab.real_table.item(0, 4).text() == "1.25"
    assert tab.real_body.text().startswith("v real: +0.900")
    # watchdog fired and nothing selected
    tab.update_record(_twin(watchdog=True, cmd_age_s=0.5), None)
    assert L["watchdog"].text().startswith("DISPARADO")
    tab.update_record(None, None)
    assert L["pose"].text() == "-" and tab.battery.bar.format() == "-"
    # hidden tab: records are buffered, nothing is drawn (cheap)
    tab.hide()
    tab.update_record(_twin(kicks=99), None)
    assert L["kicks"].text() == "-"
    tab.show()
    tab.redraw()
    assert L["kicks"].text() == "99"


def test_tab_selector_and_view_switch(qapp):
    tab = RobotTab()
    got: list = []
    tab.robot_requested.connect(got.append)
    keys = [("blue", 0), ("blue", 1), ("yellow", 0), ("yellow", 2)]
    tab.set_robots(keys)
    assert tab.robot_box.count() == 4 and tab.robot_box.itemText(3) == "yellow 2"
    tab.set_selected(("yellow", 0))
    assert tab.robot_box.currentIndex() == 2 and got == []                # syncing the box emits nothing
    tab.robot_box.setCurrentIndex(3)
    assert got == [("yellow", 2)]                                        # the box asks the GUI to select
    tab.set_selected(("yellow", 2))
    tab.next_btn.click()
    tab.prev_btn.click()
    assert got[1:] == [("blue", 0), ("yellow", 0)]                       # wraps around, both teams
    tab.set_robots(keys)                                                 # same list: no rebuild, index kept
    assert tab.robot_box.currentIndex() == 3
    # 3D by default when GL imports; the 2D spotlight one switch away
    assert tab.view3d is not None
    if tab.view3d.available:
        assert tab.view_mode == "3d" and tab.view_box.isEnabled()
        tab.set_view_mode("2d")
        assert tab.view_mode == "2d" and tab.view_box.currentIndex() == 1
        tab.view_box.setCurrentIndex(0)
        assert tab.view_mode == "3d"
    else:
        assert tab.view_mode == "2d" and not tab.view_box.isEnabled()
    tab2 = RobotTab(view3d=False)
    assert tab2.view3d is None and tab2.view_mode == "2d" and not tab2.view_box.isEnabled()


def _wheel_colour(v, i: int) -> np.ndarray:
    """RGB drawn on wheel ``i``: the mean of the tint (CAD meshes: per vertex when the mesh is smooth, per face
    otherwise) or the item colour (primitives)."""
    if v._wheel_mesh.colors is None:
        return np.asarray(v.wheels[i].opts["color"], dtype=float)[:3]
    md = v.wheels[i].opts["meshdata"]
    cols = md.vertexColors() if v._wheel_mesh.smooth else md.faceColors()
    return np.asarray(cols, dtype=float)[:, :3].mean(0)


def _expected_wheel_colour(v, omega: float) -> np.ndarray:
    from dtssl.gui.robot_view3d import wheel_face_colors, wheel_rgba

    wm = v._wheel_mesh
    if wm.colors is None:
        return np.asarray(wheel_rgba(omega))[:3]
    return wheel_face_colors(wm.vertex_colors if wm.smooth else wm.colors, omega)[:, :3].mean(0)


def test_robot_view3d_records_rotation_and_presets(qapp):
    from dtssl.gui import scene3d as S
    from dtssl.gui.robot_view3d import RobotView3D, wheel_face_colors, wheel_rgba

    v = RobotView3D(hq=False)
    if not v.available:
        pytest.skip(f"no PyOpenGL: {v.error}")
    v.resize(400, 300)
    v.show()
    qapp.processEvents()
    assert v.camera()["distance"] == S.ROBOT_VIEW_DISTANCE and v.frames == 1     # showEvent draws once
    v.set_record(_twin(t=1.0), None)
    v.set_record(_twin(t=1.1), None)
    assert v.frames == 3 and v._plate_key == ("yellow", 2) and v.plate is not None
    np.testing.assert_allclose(v._angles.angles, [0.9, 2 * math.pi - 1.9, 2.9, 2 * math.pi - 3.9], atol=1e-9)
    assert v.ball.visible()
    np.testing.assert_allclose(_wheel_colour(v, 0), _expected_wheel_colour(v, 9.0), atol=1e-6)
    assert not np.allclose(_wheel_colour(v, 0), _expected_wheel_colour(v, 0.0))      # tinted by the speed
    assert "gemeo" in v.info.text() and "+9" in v.info.text()
    # real wheel speeds when chosen and present; twin otherwise
    real = RobotTelemetry(source="real", team="yellow", id=2, t=5.0, wheel_meas=(100.0, 0.0, 0.0, 0.0))
    v.set_wheel_source("real")
    assert v.source_box.currentIndex() == 1
    v.set_record(_twin(t=1.2), real)
    assert "real" in v.info.text()
    np.testing.assert_allclose(_wheel_colour(v, 0), _expected_wheel_colour(v, 100.0), atol=1e-6)
    v.set_record(_twin(t=1.3), None)
    assert "gemeo" in v.info.text()
    # arcball drag turns the part, presets reset it, keyboard nudges it
    v.set_view("iso")
    np.testing.assert_allclose(v.arcball.R, np.eye(4))
    v.drag(200, 150, 260, 150)
    assert not np.allclose(v.arcball.R, np.eye(4))
    v.set_view("topo")
    assert v.camera()["elevation"] == S.ROBOT_VIEW_PRESETS["topo"][0] and np.allclose(v.arcball.R, np.eye(4))
    v.rotate((0, 0, 1), math.radians(10))
    assert v.arcball.R[0, 0] == pytest.approx(math.cos(math.radians(10)))
    v.reset_view()
    assert np.allclose(v.arcball.R, np.eye(4)) and v.camera()["azimuth"] == S.ROBOT_VIEW_PRESETS["iso"][1]
    v.set_auto_rotate(True)
    assert v.act_auto.isChecked() and v._timer.isActive()
    v._auto_step()
    assert not np.allclose(v.arcball.R, np.eye(4))
    v.set_auto_rotate(False)
    assert not v._timer.isActive()
    # no record: nothing drawn but the part; hidden: cheap
    v.set_record(None, None)
    assert not v.ball.visible() and v.info.text() == ""
    v.hide()
    qapp.processEvents()
    n = v.frames
    v.set_record(_twin(t=2.0), None)
    assert v.frames == n
    v.set_hq(True)
    assert v.hq and v._meshes is not None and not v._meshes.lod
    v.set_cad(False)
    assert not v.cad
    assert wheel_rgba(None) == (0.62, 0.62, 0.66, 1.0) and wheel_rgba(-1e9)[2] == pytest.approx(1.0)
    base = np.array([[0.1, 0.2, 0.3, 1.0], [0.5, 0.5, 0.5, 1.0]])
    np.testing.assert_array_equal(wheel_face_colors(base, 0.0), base)                # CAD colours at rest
    np.testing.assert_allclose(wheel_face_colors(base, 1e9)[:, :3], [wheel_rgba(1e9)[:3]] * 2)   # saturates red
    assert wheel_face_colors(base, -1e9)[0, 2] == pytest.approx(wheel_rgba(-1e9)[2])            # blue backward
    v.close()


def test_mainwindow_has_the_robot_tab_and_fills_it_from_the_world(qapp):
    win = MainWindow(mode="bridge", team="yellow", bridge_config=NET_CFG, use_pygame=False, autostart=False,
                     view3d=False, realtime=False)
    try:
        assert win.robot_tab is not None and win.tabs.indexOf(win.robot_tab) >= 0 and win.telemetry_rx is None
        win.show()
        win.tabs.setCurrentWidget(win.robot_tab)
        qapp.processEvents()
        c = win.controller
        key = c.selected
        assert win.robot_tab.header.text() == f"robo {key[1]} ({key[0]})"
        c.world.set_command(*key, RobotCmd(vx=1.0, vy=0.0, w=0.0, t_recv=time.monotonic()))
        c.tick(6)
        c._on_render()
        qapp.processEvents()
        tw = win.robot_tab.twin
        assert tw is not None and tw.source == "twin" and tw.team == key[0] and tw.id == key[1]
        assert tw.cmd_vx == 1.0 and tw.wheel_cmd is not None and tw.hardware_illustrative and tw.battery is not None
        assert win.robot_tab.state_labels["v_cmd"].text().startswith("1.000 m/s")
        # selection follows the controller, and the tab's own selector drives the controller (both teams)
        other = [k for k in c.robot_keys("yellow") if k != key][0]
        c.select(other)
        qapp.processEvents()
        assert win.robot_tab.header.text() == f"robo {other[1]} ({other[0]})"
        tab_keys = [win.robot_tab.robot_box.itemData(i) for i in range(win.robot_tab.robot_box.count())]
        assert tab_keys == c.robot_keys() and ("blue", 0) in tab_keys and other in tab_keys
        assert win.robot_tab.robot_box.currentIndex() == tab_keys.index(other)
        win.robot_tab.robot_box.setCurrentIndex(tab_keys.index(("blue", 0)))
        assert c.selected == ("blue", 0) and win.view3d is None
        assert win.robot_tab.header.text() == "robo 0 (blue)"
        win.robot_tab.next_btn.click()
        assert c.selected == ("blue", 1)
        c.select(other)
        # a receiver attached later feeds the real side of the tab
        rx = TelemetryReceiver(ip="127.0.0.1", port=0, team="yellow")
        win.telemetry_rx = rx
        rx.ingest(RCFeedback(id=other[1], vx=0.7, batteryCharge=15.5, capacitorCharge=190.0).SerializeToString())
        c._on_render()
        qapp.processEvents()
        assert win.robot_tab.real is not None and win.robot_tab.real.battery == 15.5
        win._on_stats(c.stats())
        assert "1 pacotes" in win.robot_tab.real_status.text()
        rx.stop()
        # backend change resets the illustrative hardware and the wheel plot
        win.robot_tab.wheel_plot.append(5.0, (1.0,) * 4, (1.0,) * 4)
        win._on_backend_changed(c.backend)
        assert len(win.robot_tab.wheel_plot.buf) == 0
    finally:
        win.close()


def test_mainwindow_without_the_robot_tab(qapp):
    win = MainWindow(mode="debug", team="blue", bridge_config=NET_CFG, use_pygame=False, autostart=False,
                     view3d=False, robot_tab=False)
    try:
        assert win.robot_tab is None and win.tabs.count() == 1
        win.controller.tick(2)
        win.controller._on_render()
        qapp.processEvents()
    finally:
        win.close()


def test_cli_flags_for_the_robot_tab():
    from dtssl.gui.cli import build_parser

    a = build_parser().parse_args(["--telemetry", "--no-robot-tab", "--telemetry-config", "x.json"])
    assert a.telemetry and a.no_robot_tab and str(a.telemetry_config) == "x.json"
    b = build_parser().parse_args([])
    assert not b.telemetry and not b.no_robot_tab and b.telemetry_config is None
    assert QtCore.QCoreApplication.instance() is not None or True
