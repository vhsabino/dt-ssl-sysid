"""Robot tab of dtssl.gui (offscreen, requires_gui): widgets build and paint, the tab follows the selection, the
twin record is drawn from the world state, and a real Feedback record shows up next to it."""
from __future__ import annotations

import math
import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

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
    for k in range(200):
        plot.append(k / 60.0, (1.0, 2.0, 3.0, 4.0), (1.5, 2.5, 3.5, 4.5))
    plot.append(1.0, None, None)                                         # not monotonic: ignored
    assert len(plot.buf) == int(2.0 * 60) + 2                             # capped at window * rate (+2)
    plot.redraw()
    lo, hi = plot.getViewBox().viewRange()[0]
    assert hi == pytest.approx(199 / 60.0) and lo == pytest.approx(199 / 60.0 - 2.0)
    plot.clear_data()
    assert len(plot.buf) == 0


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
        # selection follows the controller
        other = [k for k in c.robot_keys("yellow") if k != key][0]
        c.select(other)
        qapp.processEvents()
        assert win.robot_tab.header.text() == f"robo {other[1]} ({other[0]})"
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
