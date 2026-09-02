"""``MainWindow`` of ``dtssl gui`` and the ``main(argv)`` entry point.

Layout: toolbar (mode Debug/Bridge/Replay, backend, team/robot, publish, real-time, speed,
reset, fit), a second toolbar for Replay (dataset/label/event, load, play/pause, scrub),
the :class:`~dtssl.gui.field_view.FieldView` in the centre, docks with the
:class:`~dtssl.gui.plots.VelocityPlots`, the :class:`~dtssl.gui.params_panel.ParamsPanel` and a
message log, and a status bar (actual Hz, backend, joystick, packets/s per port, watchdog).

Keyboard fallback (no gamepad): WASD / QE move, Shift turbo, Space kick, C chip, R dribbler,
``,``/``.`` previous/next robot, Home teleport to centre, Esc stop (handled by an application
event filter unless a text field has the focus). In Replay, Space toggles play/pause.
"""
from __future__ import annotations

import logging
import sys
from collections.abc import Sequence

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

from dtssl.gui.controller import MODES, Controller, Frame
from dtssl.gui.field_view import FieldView
from dtssl.gui.params_panel import ParamsPanel
from dtssl.gui.plots import VelocityPlots
from dtssl.gui.replay import SPEEDS, ReplaySession, list_datasets, list_events, list_labels

log = logging.getLogger(__name__)

QT_KEY_NAMES: dict[int, str] = {
    Qt.Key_W: "w", Qt.Key_A: "a", Qt.Key_S: "s", Qt.Key_D: "d", Qt.Key_Q: "q", Qt.Key_E: "e",
    Qt.Key_Up: "up", Qt.Key_Down: "down", Qt.Key_Left: "left", Qt.Key_Right: "right",
    Qt.Key_Space: "space", Qt.Key_C: "c", Qt.Key_R: "r", Qt.Key_Shift: "shift",
    Qt.Key_Comma: ",", Qt.Key_Period: ".", Qt.Key_BracketLeft: "[", Qt.Key_BracketRight: "]",
    Qt.Key_Home: "home", Qt.Key_T: "t", Qt.Key_Escape: "escape", Qt.Key_X: "x",
}
_TEXT_WIDGETS = (QtWidgets.QAbstractSpinBox, QtWidgets.QLineEdit, QtWidgets.QTextEdit,
                 QtWidgets.QPlainTextEdit, QtWidgets.QComboBox)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, backend: str = "fopdt", mode: str = "debug", team: str = "yellow", *,
                 bridge_config=None, joy_map=None, n_blue: int = 6, n_yellow: int = 6, publish: bool = False,
                 realtime: bool | None = None, params=None, world_opts: dict | None = None,
                 use_pygame: bool | None = None, autostart: bool = True, parent=None):
        super().__init__(parent)
        self.setWindowTitle("dtssl gui — SSL digital twin")
        self.controller = Controller(backend=backend, mode=mode, team=team, bridge_config=bridge_config,
                                     joy_map=joy_map, n_blue=n_blue, n_yellow=n_yellow, publish=publish,
                                     realtime=realtime, params=params, world_opts=world_opts,
                                     use_pygame=use_pygame, parent=self)
        c = self.controller
        w = c.world
        self.field_view = FieldView(w.field, robot_radius_m=w.spec.radius, dribbler_offset_m=w.spec.dribbler_offset)
        self.setCentralWidget(self.field_view)
        self.plots = VelocityPlots()
        self.params_panel = ParamsPanel(c.params)
        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(500)
        self._build_docks()
        self._build_toolbar()
        self._build_replay_toolbar()
        self._build_statusbar()
        self._connect()
        for msg in c.drain_messages():
            self.log(msg)
        self._sync_mode_ui(c.mode)
        self._refresh_robot_combo()
        QtWidgets.QApplication.instance().installEventFilter(self)
        self.resize(1400, 860)
        if autostart:
            self.start()

    # ------------------------------------------------------------------ UI construction
    def _build_docks(self) -> None:
        d1 = QtWidgets.QDockWidget("Velocities (cmd vs body)", self)
        d1.setObjectName("dock_plots")
        d1.setWidget(self.plots)
        self.addDockWidget(Qt.RightDockWidgetArea, d1)
        d2 = QtWidgets.QDockWidget("Twin parameters (θ)", self)
        d2.setObjectName("dock_params")
        d2.setWidget(self.params_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, d2)
        d3 = QtWidgets.QDockWidget("Log", self)
        d3.setObjectName("dock_log")
        d3.setWidget(self.log_view)
        self.addDockWidget(Qt.BottomDockWidgetArea, d3)
        d3.setMaximumHeight(140)
        self.resizeDocks([d1, d2], [560, 260], Qt.Vertical)
        self.resizeDocks([d1], [460], Qt.Horizontal)

    def _build_toolbar(self) -> None:
        tb = QtWidgets.QToolBar("Main")
        tb.setObjectName("tb_main")
        tb.setMovable(False)
        self.addToolBar(tb)
        self.mode_actions: dict[str, QtGui.QAction] = {}
        grp = QtGui.QActionGroup(self)
        grp.setExclusive(True)
        for m in MODES:
            a = QtGui.QAction(m.capitalize(), self)
            a.setCheckable(True)
            a.setData(m)
            grp.addAction(a)
            tb.addAction(a)
            self.mode_actions[m] = a
        grp.triggered.connect(lambda a: self.set_mode(a.data()))
        tb.addSeparator()
        tb.addWidget(QtWidgets.QLabel(" backend "))
        self.backend_box = QtWidgets.QComboBox()
        self.backend_box.addItems(self.controller.backends())
        self.backend_box.setCurrentText(self.controller.backend)
        self.backend_box.currentTextChanged.connect(self._on_backend_box)
        tb.addWidget(self.backend_box)
        tb.addWidget(QtWidgets.QLabel(" team "))
        self.team_box = QtWidgets.QComboBox()
        self.team_box.addItems(["blue", "yellow"])
        self.team_box.setCurrentText(self.controller.team)
        self.team_box.currentTextChanged.connect(self._on_team_box)
        tb.addWidget(self.team_box)
        tb.addWidget(QtWidgets.QLabel(" robot "))
        self.robot_box = QtWidgets.QComboBox()
        self.robot_box.currentIndexChanged.connect(self._on_robot_box)
        tb.addWidget(self.robot_box)
        tb.addSeparator()
        self.publish_cb = QtWidgets.QCheckBox("publish vision")
        self.publish_cb.setToolTip("Debug: run a step-mode SimServer so external tools receive vision/geometry")
        self.publish_cb.setChecked(self.controller.publish)
        self.publish_cb.toggled.connect(self.controller.set_publish)
        tb.addWidget(self.publish_cb)
        self.realtime_cb = QtWidgets.QCheckBox("real-time thread")
        self.realtime_cb.setToolTip("Bridge: SimServer.run() in a thread (off = GUI timer ticks the server)")
        self.realtime_cb.setChecked(self.controller.realtime)
        self.realtime_cb.toggled.connect(self.controller.set_realtime)
        tb.addWidget(self.realtime_cb)
        tb.addWidget(QtWidgets.QLabel(" speed "))
        self.speed_box = QtWidgets.QComboBox()
        for s in SPEEDS:
            self.speed_box.addItem(f"{s:g}×", s)
        self.speed_box.setCurrentIndex(list(SPEEDS).index(1.0))
        self.speed_box.currentIndexChanged.connect(lambda i: self.controller.set_speed(self.speed_box.itemData(i)))
        tb.addWidget(self.speed_box)
        tb.addSeparator()
        a = tb.addAction("Reset scene")
        a.triggered.connect(self.controller.reset_scene)
        a = tb.addAction("Fit (F)")
        a.triggered.connect(self.field_view.fit_field)
        self.act_run = tb.addAction("Pause")
        self.act_run.setCheckable(True)
        self.act_run.setChecked(False)
        self.act_run.toggled.connect(self._on_pause_toggled)

    def _build_replay_toolbar(self) -> None:
        tb = QtWidgets.QToolBar("Replay")
        tb.setObjectName("tb_replay")
        tb.setMovable(False)
        self.addToolBarBreak()
        self.addToolBar(tb)
        self.replay_toolbar = tb
        tb.addWidget(QtWidgets.QLabel(" dataset "))
        self.dataset_box = QtWidgets.QComboBox()
        self.dataset_box.setMinimumWidth(170)
        tb.addWidget(self.dataset_box)
        tb.addWidget(QtWidgets.QLabel(" label "))
        self.label_box = QtWidgets.QComboBox()
        self.label_box.setMinimumWidth(130)
        tb.addWidget(self.label_box)
        tb.addWidget(QtWidgets.QLabel(" event "))
        self.event_box = QtWidgets.QComboBox()
        self.event_box.setMinimumWidth(190)
        tb.addWidget(self.event_box)
        self.btn_load = QtWidgets.QPushButton("Load")
        self.btn_load.clicked.connect(self._on_load_replay)
        tb.addWidget(self.btn_load)
        tb.addSeparator()
        self.btn_play = QtWidgets.QPushButton("Play")
        self.btn_play.clicked.connect(self._on_play)
        tb.addWidget(self.btn_play)
        self.slider = QtWidgets.QSlider(Qt.Horizontal)
        self.slider.setMinimumWidth(300)
        self.slider.setRange(0, 0)
        self.slider.valueChanged.connect(self._on_slider)
        tb.addWidget(self.slider)
        self.replay_time = QtWidgets.QLabel(" 0.000 s ")
        tb.addWidget(self.replay_time)
        self.epos_label = QtWidgets.QLabel("")
        tb.addWidget(self.epos_label)
        self.dataset_box.currentTextChanged.connect(self._on_dataset_box)
        self.label_box.currentTextChanged.connect(self._on_label_box)
        self._fill_datasets()

    def _build_statusbar(self) -> None:
        sb = self.statusBar()
        self.status_labels: dict[str, QtWidgets.QLabel] = {}
        for name in ("mode", "hz", "joystick", "packets", "watchdog", "selected", "time"):
            lab = QtWidgets.QLabel("")
            lab.setFrameShape(QtWidgets.QFrame.StyledPanel)
            sb.addPermanentWidget(lab)
            self.status_labels[name] = lab

    def _connect(self) -> None:
        c = self.controller
        c.frame_ready.connect(self._on_frame)
        c.sample_ready.connect(self._on_sample)
        c.stats_ready.connect(self._on_stats)
        c.mode_changed.connect(self._sync_mode_ui)
        c.backend_changed.connect(self._on_backend_changed)
        c.selection_changed.connect(self._on_selection_changed)
        c.replay_loaded.connect(self._on_replay_loaded)
        c.replay_changed.connect(self._on_replay_changed)
        c.message.connect(self.log)
        c.joystick_event.connect(lambda ev: self.log(f"joystick: {ev}"))
        c.server_changed.connect(lambda on: self.log("SimServer " + ("running" if on else "stopped")))
        self.field_view.robot_teleport_requested.connect(self._on_teleport_robot)
        self.field_view.ball_teleport_requested.connect(self._on_teleport_ball)
        self.field_view.robot_selected.connect(lambda team, rid: c.select((team, rid)))
        self.params_panel.apply_requested.connect(c.apply_params)

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        self.controller.start()
        self.plots.start()

    def stop(self) -> None:
        self.plots.stop()
        self.controller.stop()

    def closeEvent(self, ev: QtGui.QCloseEvent) -> None:
        self.stop()
        self.controller.shutdown()
        try:
            QtWidgets.QApplication.instance().removeEventFilter(self)
        except Exception:  # noqa: BLE001
            pass
        super().closeEvent(ev)

    def log(self, msg: str) -> None:
        self.log_view.appendPlainText(msg)
        self.statusBar().showMessage(msg, 4000)
        log.info(msg)

    # ------------------------------------------------------------------ modes
    def set_mode(self, mode: str) -> None:
        try:
            self.controller.set_mode(mode)
        except Exception as e:  # noqa: BLE001
            self.log(f"mode {mode} failed: {e}")

    def _sync_mode_ui(self, mode: str) -> None:
        for m, a in self.mode_actions.items():
            a.setChecked(m == mode)
        replay = mode == "replay"
        self.replay_toolbar.setVisible(replay)
        self.publish_cb.setEnabled(mode == "debug")
        self.realtime_cb.setEnabled(mode == "bridge")
        self.plots.set_mode("fixed" if replay else "sliding")
        self.field_view.clear_trails()
        self.field_view.set_ball_visible(not replay)
        if replay and self.controller.replay is not None:
            self._on_replay_loaded(self.controller.replay)
        self.log(f"mode: {mode}")

    def _on_backend_box(self, name: str) -> None:
        if name and name != self.controller.backend:
            self.controller.set_backend(name)
            self.backend_box.setCurrentText(self.controller.backend)

    def _on_backend_changed(self, name: str) -> None:
        w = self.controller.world
        self.field_view.set_field(w.field)
        self.plots.clear()
        self._refresh_robot_combo()
        self.log(f"backend: {name} ({getattr(w, 'name', type(w).__name__)})")

    def _on_team_box(self, team: str) -> None:
        self.controller.select_team(team)
        self._refresh_robot_combo()

    def _refresh_robot_combo(self) -> None:
        c = self.controller
        keys = c.robot_keys(c.team)
        self.robot_box.blockSignals(True)
        self.robot_box.clear()
        for k in keys:
            self.robot_box.addItem(f"{k[0]} {k[1]}", k)
        if c.selected in keys:
            self.robot_box.setCurrentIndex(keys.index(c.selected))
        self.robot_box.blockSignals(False)

    def _on_robot_box(self, i: int) -> None:
        key = self.robot_box.itemData(i)
        if key is not None:
            self.controller.select(tuple(key))

    def _on_selection_changed(self, key) -> None:
        self._refresh_robot_combo()
        self.field_view.set_selected(tuple(key) if key is not None else None)
        if self.plots.mode == "sliding":
            self.plots.clear()

    def _on_pause_toggled(self, paused: bool) -> None:
        if paused:
            self.controller.stop()
            self.act_run.setText("Resume")
        else:
            self.controller.start()
            self.act_run.setText("Pause")

    # ------------------------------------------------------------------ field interaction
    def _on_teleport_robot(self, x: float, y: float) -> None:
        if self.controller.teleport_selected(x, y):
            self.field_view.clear_trails()
            self.log(f"teleport {self.controller.selected} -> ({x:.2f}, {y:.2f}) m")

    def _on_teleport_ball(self, x: float, y: float) -> None:
        if self.controller.teleport_ball(x, y):
            self.log(f"teleport ball -> ({x:.2f}, {y:.2f}) m")

    # ------------------------------------------------------------------ replay UI
    def _fill_datasets(self) -> None:
        self.dataset_box.blockSignals(True)
        self.dataset_box.clear()
        ds = list_datasets()
        self.dataset_box.addItems(ds)
        self.dataset_box.blockSignals(False)
        self._on_dataset_box(self.dataset_box.currentText())
        if not ds:
            self.btn_load.setEnabled(False)
            self.btn_load.setToolTip("no dataset under data/extracted (DVC)")

    def _on_dataset_box(self, ds: str) -> None:
        self.label_box.blockSignals(True)
        self.label_box.clear()
        if ds:
            self.label_box.addItems(list_labels(ds))
        self.label_box.blockSignals(False)
        self._on_label_box(self.label_box.currentText())

    def _on_label_box(self, label: str) -> None:
        self.event_box.clear()
        ds = self.dataset_box.currentText()
        if ds and label:
            self.event_box.addItems(list_events(ds, label))

    def select_replay(self, dataset: str | None, label: str | None, event: str | None) -> None:
        if dataset:
            self.dataset_box.setCurrentText(dataset)
        if label:
            self.label_box.setCurrentText(label)
        if event:
            self.event_box.setCurrentText(event)

    def _on_load_replay(self) -> None:
        ds, label, event = self.dataset_box.currentText(), self.label_box.currentText(), self.event_box.currentText()
        if not (ds and label and event):
            self.log("replay: choose dataset/label/event")
            return
        self.load_replay(label, event, ds)

    def load_replay(self, label: str, event: str, dataset: str | None = None) -> ReplaySession | None:
        try:
            sess = self.controller.load_replay(label, event, dataset)
        except Exception as e:  # noqa: BLE001
            self.log(f"replay load failed: {e}")
            return None
        self.select_replay(sess.dataset, sess.label, sess.event)
        if self.controller.mode != "replay":
            self.set_mode("replay")
        return sess

    def _on_replay_loaded(self, sess: ReplaySession) -> None:
        self.slider.blockSignals(True)
        self.slider.setRange(0, max(0, sess.n - 1))
        self.slider.setValue(sess.index)
        self.slider.blockSignals(False)
        self._push_replay_series(sess)
        self.field_view.clear_trails()
        self.field_view.fit_field()
        self.btn_play.setText("Pause" if sess.playing else "Play")

    def _on_replay_changed(self, sess: ReplaySession) -> None:
        self._push_replay_series(sess)

    def _push_replay_series(self, sess: ReplaySession) -> None:
        self.plots.set_mode("fixed")
        labels = [f"h={h}" for h in sess.horizons]
        self.plots.set_series(sess.t, sess.cmd, sess.velb_sim, sess.velb_truth, sess.epos,
                              sess.horizon_times(), labels)
        self.plots.set_playhead(float(sess.t[sess.index]))
        eh = sess.epos_at_horizons()
        self.epos_label.setText("  e_pos@h: " + "  ".join(f"{h}:{v:.3f}" for h, v in eh.items()))

    def _on_play(self) -> None:
        playing = self.controller.replay_toggle()
        self.btn_play.setText("Pause" if playing else "Play")

    def _on_slider(self, i: int) -> None:
        rp = self.controller.replay
        if rp is not None and i != rp.index:
            rp.seek(i)
            self.plots.set_playhead(float(rp.t[rp.index]))
            self.field_view.clear_trails()

    # ------------------------------------------------------------------ data in
    def _on_frame(self, fr: Frame) -> None:
        self.field_view.update_state(fr.ws, fr.selected, fr.truth_pose, fr.t)
        if fr.mode == "replay" and fr.replay_index is not None:
            rp = self.controller.replay
            if rp is not None:
                if self.slider.value() != fr.replay_index:
                    self.slider.blockSignals(True)
                    self.slider.setValue(fr.replay_index)
                    self.slider.blockSignals(False)
                self.plots.set_playhead(fr.t)
                self.replay_time.setText(f" {fr.t:7.3f} s  e_pos={rp.epos[fr.replay_index]:.3f} m ")
                self.btn_play.setText("Pause" if rp.playing else "Play")

    def _on_sample(self, t: float, cmd, sim, truth) -> None:
        if self.plots.mode == "sliding":
            self.plots.append(t, cmd, sim, truth)

    def _on_stats(self, st: dict) -> None:
        L = self.status_labels
        L["mode"].setText(f" {st['mode']} · {st['world']} ")
        L["hz"].setText(f" {st['hz']:5.1f} Hz ×{st['speed']:g} ")
        joy = st["joystick"] + (" ✓" if st["joystick_connected"] else "")
        extras = []
        if st.get("dribbler"):
            extras.append("dribbler")
        if st.get("turbo"):
            extras.append("turbo")
        L["joystick"].setText(f" {joy}{(' [' + ', '.join(extras) + ']') if extras else ''} ")
        if st.get("server"):
            pr = st.get("packets_per_s", {})
            L["packets"].setText(" " + "  ".join(f"{k} {pr.get(k, 0.0):.0f}/s" for k in ("vision", "blue", "yellow",
                                                                                       "simcontrol")) + " ")
        else:
            L["packets"].setText(" no server ")
        L["watchdog"].setText(f" watchdog {st['watchdog_hits']}  kicks {st['kicks']} ")
        sel = st.get("selected")
        L["selected"].setText(f" sel {sel[0]} {sel[1]} " if sel else " sel — ")
        rp = st.get("replay")
        if rp:
            L["time"].setText(f" {rp['label']}/{rp['event']} {rp['index']}/{rp['n']} ")
        else:
            L["time"].setText(f" t={st['sim_time']:.1f} s ")

    # ------------------------------------------------------------------ keyboard fallback
    def eventFilter(self, obj, ev) -> bool:
        et = ev.type()
        if et in (QtCore.QEvent.KeyPress, QtCore.QEvent.KeyRelease) and isinstance(ev, QtGui.QKeyEvent):
            if ev.isAutoRepeat():
                return False
            fw = QtWidgets.QApplication.focusWidget()
            if isinstance(fw, _TEXT_WIDGETS):
                return False
            name = QT_KEY_NAMES.get(ev.key())
            if name is None:
                return False
            if et == QtCore.QEvent.KeyPress:
                if name == "space" and self.controller.mode == "replay":
                    self._on_play()
                    return True
                self.controller.kb.press(name)
            else:
                self.controller.kb.release(name)
            return True
        return super().eventFilter(obj, ev)


# =========================================================================== entry points
def run(args) -> int:
    """Run the GUI from parsed ``dtssl gui`` arguments (see :mod:`dtssl.gui.cli`)."""
    logging.basicConfig(level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
    world_opts = {}
    if getattr(args, "saturate", False):
        world_opts["saturate"] = True
    if getattr(args, "deadzone", False):
        world_opts["deadzone"] = True
    params = None
    if getattr(args, "theta", None):
        from dtssl.models.params import load_twin_params

        params = load_twin_params(args.theta)
    win = MainWindow(backend=args.backend, mode=args.mode, team=args.team, bridge_config=args.config,
                     joy_map=args.joy_map, n_blue=args.n_blue, n_yellow=args.n_yellow, publish=args.publish,
                     realtime=(False if getattr(args, "no_realtime", False) else None), params=params,
                     world_opts=world_opts, use_pygame=(False if getattr(args, "no_joystick", False) else None))
    if getattr(args, "event", None) and getattr(args, "label", None):
        win.select_replay(getattr(args, "dataset", None), args.label, args.event)
        win.load_replay(args.label, args.event, getattr(args, "dataset", None))
    win.show()
    return int(app.exec())


def main(argv: Sequence[str] | None = None) -> int:
    from dtssl.gui.cli import build_parser

    args = build_parser().parse_args(list(sys.argv[1:] if argv is None else argv))
    return run(args)


__all__ = ["MainWindow", "run", "main", "QT_KEY_NAMES"]
