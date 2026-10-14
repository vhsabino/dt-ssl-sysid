"""*Robot* tab of ``dtssl gui``: one robot in the spotlight, with its telemetry.

Header: the robot selector (every present robot of both teams, with previous / next), which drives the GUI
selection (``robot_requested``) exactly like the field click or ``,``/``.``. Left: the selected robot in 3D
(:class:`dtssl.gui.robot_view3d.RobotView3D`: CAD meshes turned freely with the mouse, wheels spinning at
the record's speeds) or, at the flip of a switch and whenever GL is unavailable, the 2D top-view spotlight
(chassis, dribbler face, the four wheels coloured by their speed, commanded and resulting body-velocity arrows,
the ball when the sensor sees it); below it the state table
(pose, body velocities commanded / resulting, command age, watchdog, dribbler, ball sensor, kicks). Middle:
the four wheel speeds as bars (commanded vs resulting, rad/s) and their last seconds as curves, one plot per
motor sharing the time axis (like the body-velocity plots of the main window). Right: the
"hardware" block: battery and capacitor, ball sensor, and, when a real robot is reporting over the radio
(:class:`dtssl.bridge.telemetry.TelemetryReceiver`), its per-motor PWM / error / current table.

Every value carries its provenance. What the twin knows is drawn from the world state and the inverse
kinematics (``source: twin``); battery and capacitor of the twin come from an **illustrative** model and are
labelled so; a real robot's record (``source: real``) is shown next to the twin's for the same id whenever it
is fresh, with the units of ``config/telemetry.json``. The tab only redraws while it is visible.
"""
from __future__ import annotations

import math

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Signal

from dtssl.bridge.telemetry import N_WHEELS, RobotTelemetry
from dtssl.gui.plots import MIN_X_RANGE_S, MIN_Y_RANGE, RingBuffer, _flush, _safe_axes
from dtssl.gui.robot_view3d import RobotView3D

TEAM_COLORS = {"blue": QtGui.QColor(41, 121, 255), "yellow": QtGui.QColor(255, 214, 0)}
CMD_COLOR = QtGui.QColor(255, 170, 0)
MEAS_COLOR = QtGui.QColor(0, 229, 255)
REAL_COLOR = QtGui.QColor(255, 64, 129)
WHEEL_COLORS = [(0, 229, 255), (255, 193, 7), (129, 199, 132), (255, 64, 129)]
WHEEL_MAX_RAD_S = 120.0           # colour / bar scale (about 3.5 m/s of body speed)
DEFAULT_WHEEL_ANGLES_DEG = (60.0, 135.0, 225.0, 300.0)


def _fmt(v, unit: str = "", nd: int = 3) -> str:
    if v is None:
        return "-"
    if isinstance(v, bool):
        return "sim" if v else "nao"
    if isinstance(v, (int, np.integer)):
        return f"{int(v)}{unit}"
    return f"{float(v):.{nd}f}{unit}"


class RobotSpotlight(QtWidgets.QWidget):
    """Top view of one robot: chassis, dribbler, wheels (coloured by speed), velocity arrows, ball."""

    def __init__(self, wheel_angles_deg=DEFAULT_WHEEL_ANGLES_DEG, parent=None):
        super().__init__(parent)
        self.wheel_angles = tuple(math.radians(a) for a in wheel_angles_deg)
        self.rec: RobotTelemetry | None = None
        self.setMinimumSize(220, 220)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

    def set_record(self, rec: RobotTelemetry | None) -> None:
        self.rec = rec
        self.update()

    def sizeHint(self) -> QtCore.QSize:  # noqa: N802
        return QtCore.QSize(260, 260)

    @staticmethod
    def wheel_color(omega: float) -> QtGui.QColor:
        a = min(1.0, abs(float(omega)) / WHEEL_MAX_RAD_S)
        base = QtGui.QColor(60, 60, 60)
        hot = QtGui.QColor(255, 82, 82) if omega >= 0 else QtGui.QColor(64, 156, 255)
        r = base.red() + (hot.red() - base.red()) * a
        g = base.green() + (hot.green() - base.green()) * a
        b = base.blue() + (hot.blue() - base.blue()) * a
        return QtGui.QColor(int(r), int(g), int(b))

    def paintEvent(self, ev: QtGui.QPaintEvent) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.fillRect(self.rect(), QtGui.QColor(20, 20, 20))
        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0
        R = 0.36 * min(w, h)                     # chassis radius in px
        rec = self.rec
        p.translate(cx, cy)
        p.scale(1.0, -1.0)                       # body y up, like the field
        # chassis: circle with a flat dribbler face at +x (body frame: x forward)
        team = rec.team if rec is not None else None
        color = TEAM_COLORS.get(team or "", QtGui.QColor(120, 120, 120))
        flat = 0.83 * R
        path = QtGui.QPainterPath()
        ang = math.degrees(math.acos(flat / R))
        rect = QtCore.QRectF(-R, -R, 2 * R, 2 * R)
        path.arcMoveTo(rect, ang)
        path.arcTo(rect, ang, 360.0 - 2 * ang)
        path.closeSubpath()
        p.setPen(QtGui.QPen(color, 3))
        p.setBrush(QtGui.QColor(35, 35, 35))
        p.drawPath(path)
        # wheels
        wc = rec.wheel_meas if rec is not None else None
        for i, phi in enumerate(self.wheel_angles):
            om = float(wc[i]) if wc is not None and i < len(wc) else 0.0
            p.save()
            p.rotate(math.degrees(phi))
            p.translate(0.94 * R, 0.0)
            p.setPen(QtGui.QPen(QtGui.QColor(200, 200, 200), 1))
            p.setBrush(self.wheel_color(om))
            p.drawRoundedRect(QtCore.QRectF(-0.07 * R, -0.16 * R, 0.14 * R, 0.32 * R), 2, 2)
            p.restore()
            # wheel number label (unflipped text)
            p.save()
            p.scale(1.0, -1.0)
            lx, ly = 0.70 * R * math.cos(phi), -0.70 * R * math.sin(phi)
            p.setPen(QtGui.QColor(230, 230, 230))
            p.drawText(QtCore.QRectF(lx - 10, ly - 8, 20, 16), QtCore.Qt.AlignCenter, f"{i + 1}")
            p.restore()
        # heading tick on the dribbler face
        p.setPen(QtGui.QPen(QtGui.QColor(230, 230, 230), 2))
        p.drawLine(QtCore.QPointF(0.5 * R, 0.0), QtCore.QPointF(flat, 0.0))
        if rec is not None:
            self._arrow(p, rec.cmd_vx, rec.cmd_vy, R, CMD_COLOR, dashed=True)
            self._arrow(p, rec.vx, rec.vy, R, MEAS_COLOR, dashed=False)
            self._omega_arc(p, rec.cmd_w, R * 1.18, CMD_COLOR, dashed=True)
            self._omega_arc(p, rec.w, R * 1.10, MEAS_COLOR, dashed=False)
            if rec.has_ball:
                p.setPen(QtCore.Qt.NoPen)
                p.setBrush(QtGui.QColor(255, 120, 0))
                p.drawEllipse(QtCore.QPointF(flat + 0.12 * R, 0.0), 0.10 * R, 0.10 * R)
        p.end()

    @staticmethod
    def _arrow(p: QtGui.QPainter, vx, vy, R: float, color: QtGui.QColor, dashed: bool) -> None:
        if vx is None or vy is None:
            return
        vx, vy = _flush(vx), _flush(vy)
        n = math.hypot(vx, vy)
        if n < 1e-3:
            return
        scale = 0.9 * R / 2.0                    # 2 m/s = 0.9 R
        ex, ey = vx * scale, vy * scale
        pen = QtGui.QPen(color, 3)
        if dashed:
            pen.setStyle(QtCore.Qt.DashLine)
        p.setPen(pen)
        p.drawLine(QtCore.QPointF(0, 0), QtCore.QPointF(ex, ey))
        a = math.atan2(ey, ex)
        for da in (math.pi * 0.8, -math.pi * 0.8):
            p.drawLine(QtCore.QPointF(ex, ey), QtCore.QPointF(ex + 9 * math.cos(a + da), ey + 9 * math.sin(a + da)))

    @staticmethod
    def _omega_arc(p: QtGui.QPainter, w, r: float, color: QtGui.QColor, dashed: bool) -> None:
        if w is None:
            return
        w = _flush(w)
        if abs(w) < 1e-3:
            return
        span = max(-150.0, min(150.0, float(w) * 30.0))   # 5 rad/s = 150 degrees
        pen = QtGui.QPen(color, 2)
        if dashed:
            pen.setStyle(QtCore.Qt.DashLine)
        p.setPen(pen)
        p.setBrush(QtCore.Qt.NoBrush)
        rect = QtCore.QRectF(-r, -r, 2 * r, 2 * r)
        p.drawArc(rect, int(90 * 16), int(span * 16))


class WheelBars(QtWidgets.QWidget):
    """Four symmetric bars (rad/s): commanded (thin, orange) over resulting (thick, cyan) per wheel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cmd: tuple | None = None
        self.meas: tuple | None = None
        self.real: tuple | None = None
        self.setMinimumHeight(110)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)

    def set_values(self, cmd, meas, real=None) -> None:
        self.cmd, self.meas, self.real = cmd, meas, real
        self.update()

    def paintEvent(self, ev: QtGui.QPaintEvent) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.fillRect(self.rect(), QtGui.QColor(20, 20, 20))
        w, h = self.width(), self.height()
        left, right = 34, w - 8
        row = h / N_WHEELS
        mid = (left + right) / 2.0
        half = (right - left) / 2.0
        p.setPen(QtGui.QPen(QtGui.QColor(90, 90, 90), 1))
        p.drawLine(QtCore.QPointF(mid, 0), QtCore.QPointF(mid, h))
        for i in range(N_WHEELS):
            y0 = i * row + 4
            p.setPen(QtGui.QColor(220, 220, 220))
            p.drawText(QtCore.QRectF(0, y0, left - 4, row - 8), QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight, f"m{i + 1}")
            for vals, color, thick, off in ((self.meas, MEAS_COLOR, 0.55, 0.0), (self.real, REAL_COLOR, 0.25, 0.30),
                                            (self.cmd, CMD_COLOR, 0.18, -0.30)):
                if vals is None or i >= len(vals):
                    continue
                v = max(-WHEEL_MAX_RAD_S, min(WHEEL_MAX_RAD_S, _flush(vals[i])))
                x = v / WHEEL_MAX_RAD_S * half
                hh = thick * (row - 8)
                yc = y0 + (row - 8) / 2.0 + off * (row - 8) / 2.0
                r = QtCore.QRectF(mid + min(0.0, x), yc - hh / 2.0, abs(x), hh)
                p.fillRect(r, color)
        p.end()


class WheelPlot(pg.GraphicsLayoutWidget):
    """Last ``window_s`` seconds of the four wheel speeds, one plot per motor (rows ``m1``..``m4`` sharing the
    time axis, like the body-velocity plots): resulting solid in the wheel's colour, commanded dashed, and the
    real robot's wheel (radio) in pink while it reports."""

    def __init__(self, window_s: float = 10.0, rate_hz: float = 60.0, parent=None):
        super().__init__(parent)
        self.window_s = float(window_s)
        self.buf = RingBuffer(int(window_s * rate_hz) + 2, 1 + 3 * N_WHEELS)     # t, meas x4, cmd x4, real x4
        self.plots: list[pg.PlotItem] = []
        self.curves_meas: list[pg.PlotDataItem] = []
        self.curves_cmd: list[pg.PlotDataItem] = []
        self.curves_real: list[pg.PlotDataItem] = []
        for i, c in enumerate(WHEEL_COLORS):
            p = self.addPlot(row=i, col=0, axisItems=_safe_axes())
            p.getViewBox().setLimits(minXRange=MIN_X_RANGE_S, minYRange=MIN_Y_RANGE)
            p.setLabel("left", f"m{i + 1}", units="rad/s")
            p.getAxis("left").enableAutoSIPrefix(False)
            p.showGrid(x=True, y=True, alpha=0.25)
            p.setMenuEnabled(False)
            p.hideButtons()
            p.setDownsampling(auto=True, mode="peak")
            p.setClipToView(True)
            if i > 0:
                p.setXLink(self.plots[0])
            self.curves_cmd.append(p.plot(pen=pg.mkPen(c, width=1, style=QtCore.Qt.DashLine)))
            self.curves_meas.append(p.plot(pen=pg.mkPen(c, width=2)))
            rc = p.plot(pen=pg.mkPen(REAL_COLOR, width=2), connect="finite")
            rc.setVisible(False)
            self.curves_real.append(rc)
            self.plots.append(p)
            self.ci.layout.setRowStretchFactor(i, 1)
        self.plots[-1].setLabel("bottom", "t", units="s")
        self._last_t: float | None = None

    def append(self, t: float, cmd, meas, real=None) -> None:
        """One sample: commanded and resulting wheel speeds of the twin (rad/s), and the real robot's when it
        reports (``None`` leaves a gap in the pink curve)."""
        if self._last_t is not None and t <= self._last_t:
            return
        self._last_t = t
        row = ([t] + [_flush(v) for v in (meas or (0.0,) * N_WHEELS)] + [_flush(v) for v in (cmd or (0.0,) * N_WHEELS)]
               + [_flush(v) for v in (real if real is not None else (np.nan,) * N_WHEELS)])
        self.buf.append(row)

    def clear_data(self) -> None:
        self.buf.clear()
        self._last_t = None
        for c in self.curves_meas + self.curves_cmd + self.curves_real:
            c.setData([], [])
        for c in self.curves_real:
            c.setVisible(False)

    def redraw(self) -> None:
        d = self.buf.data()
        if len(d) == 0:
            return
        t = d[:, 0]
        for i in range(N_WHEELS):
            self.curves_meas[i].setData(t, d[:, 1 + i])
            self.curves_cmd[i].setData(t, d[:, 1 + N_WHEELS + i])
            real = d[:, 1 + 2 * N_WHEELS + i]
            has_real = bool(np.isfinite(real).any())
            self.curves_real[i].setVisible(has_real)
            if has_real:
                self.curves_real[i].setData(t, real)
        t_end = float(t[-1])
        self.plots[0].setXRange(t_end - self.window_s, t_end, padding=0.0)


class _Gauge(QtWidgets.QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.title = QtWidgets.QLabel(title)
        self.bar = QtWidgets.QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(True)
        self.value = QtWidgets.QLabel("-")
        lay.addWidget(self.title)
        lay.addWidget(self.bar)
        lay.addWidget(self.value)

    def set_fraction(self, frac: float | None, text: str) -> None:
        if frac is None:
            self.bar.setValue(0)
            self.bar.setFormat("-")
        else:
            self.bar.setValue(int(round(1000 * max(0.0, min(1.0, frac)))))
            self.bar.setFormat(f"{100 * frac:.0f} %")
        self.value.setText(text)


class RobotTab(QtWidgets.QWidget):
    """The tab. Feed it with :meth:`update_record` at the display rate; it redraws only while visible."""

    robot_requested = Signal(object)          # (team, id) chosen in the tab's selector

    def __init__(self, wheel_angles_deg=DEFAULT_WHEEL_ANGLES_DEG, units: dict | None = None, view3d: bool = True,
                 spec=None, wheel=None, cad: bool = True, hq: bool = True, parent=None):
        super().__init__(parent)
        self.units = dict(units or {})
        self.twin: RobotTelemetry | None = None
        self.real: RobotTelemetry | None = None
        self._key: tuple[str, int] | None = None
        self._keys: list[tuple[str, int]] = []
        root = QtWidgets.QHBoxLayout(self)
        # ---- left: selector, 3D / 2D view + state
        left = QtWidgets.QVBoxLayout()
        head = QtWidgets.QHBoxLayout()
        self.header = QtWidgets.QLabel("nenhum robo selecionado")
        f = self.header.font()
        f.setPointSize(f.pointSize() + 3)
        f.setBold(True)
        self.header.setFont(f)
        self.prev_btn = QtWidgets.QToolButton()
        self.prev_btn.setText("<")
        self.prev_btn.setToolTip("robo anterior (,)")
        self.next_btn = QtWidgets.QToolButton()
        self.next_btn.setText(">")
        self.next_btn.setToolTip("proximo robo (.)")
        self.robot_box = QtWidgets.QComboBox()
        self.robot_box.setToolTip("robo mostrado nesta aba (a selecao vale para toda a GUI)")
        self.robot_box.setMinimumWidth(110)
        self.prev_btn.clicked.connect(lambda: self._cycle(-1))
        self.next_btn.clicked.connect(lambda: self._cycle(+1))
        self.robot_box.currentIndexChanged.connect(self._on_box)
        head.addWidget(self.header, 1)
        head.addWidget(self.prev_btn)
        head.addWidget(self.robot_box)
        head.addWidget(self.next_btn)
        self.view_box = QtWidgets.QComboBox()
        self.view_box.addItems(["3D", "2D"])
        self.view_box.setToolTip("vista do robo: 3D (CAD, girar com o mouse) ou 2D (vista de cima)")
        head.addWidget(self.view_box)
        left.addLayout(head)
        self.source = QtWidgets.QLabel("fonte: gemeo (calculado do estado do mundo e da cinematica inversa)")
        self.source.setWordWrap(True)
        self.spotlight = RobotSpotlight(wheel_angles_deg)
        self.view3d: RobotView3D | None = RobotView3D(spec=spec, wheel=wheel, cad=cad, hq=hq) if view3d else None
        self.stack = QtWidgets.QStackedWidget()
        if self.view3d is not None and self.view3d.available:
            self.stack.addWidget(self.view3d)
            self.stack.addWidget(self.spotlight)
        else:
            self.stack.addWidget(self.spotlight)
            if self.view3d is not None:
                self.stack.addWidget(self.view3d)
            self.view_box.setCurrentIndex(1)
            self.view_box.setEnabled(False)
            self.view_box.setToolTip("vista 3D indisponivel" + (f": {self.view3d.error}" if self.view3d else " (--no-3d)"))
        self.view_box.currentIndexChanged.connect(self.set_view_mode)
        left.addWidget(self.source)
        left.addWidget(self.stack, 1)
        self.state_form = QtWidgets.QFormLayout()
        self.state_labels: dict[str, QtWidgets.QLabel] = {}
        for key, title in (("pose", "pose x, y, theta"), ("v_cmd", "v comando (vx, vy, w)"),
                           ("v_meas", "v resultante (vx, vy, w)"), ("age", "idade do comando"),
                           ("watchdog", "watchdog"), ("dribbler", "dribbler"), ("ball", "sensor de bola (IR)"),
                           ("kicks", "chutes (mundo)")):
            lab = QtWidgets.QLabel("-")
            lab.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            self.state_labels[key] = lab
            self.state_form.addRow(title, lab)
        box = QtWidgets.QGroupBox("estado (gemeo)")
        box.setLayout(self.state_form)
        left.addWidget(box)
        root.addLayout(left, 3)
        # ---- middle: wheels
        mid = QtWidgets.QVBoxLayout()
        wb = QtWidgets.QGroupBox("rodas (rad/s): comando tracejado, resultante cheio, real em rosa")
        wl = QtWidgets.QVBoxLayout(wb)
        self.bars = WheelBars()
        self.wheel_plot = WheelPlot()
        wl.addWidget(self.bars)
        wl.addWidget(self.wheel_plot, 1)
        self.wheel_values = QtWidgets.QLabel("-")
        self.wheel_values.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        wl.addWidget(self.wheel_values)
        mid.addWidget(wb, 1)
        root.addLayout(mid, 4)
        # ---- right: hardware
        right = QtWidgets.QVBoxLayout()
        hw = QtWidgets.QGroupBox("hardware")
        hl = QtWidgets.QVBoxLayout(hw)
        self.hw_note = QtWidgets.QLabel("")
        self.hw_note.setWordWrap(True)
        self.hw_note.setStyleSheet("color: #ffb74d;")
        self.battery = _Gauge("bateria")
        self.capacitor = _Gauge("capacitor")
        self.ir = QtWidgets.QLabel("IR: -")
        hl.addWidget(self.hw_note)
        hl.addWidget(self.battery)
        hl.addWidget(self.capacitor)
        hl.addWidget(self.ir)
        right.addWidget(hw)
        rb = QtWidgets.QGroupBox("radio (rc_communication Feedback)")
        rl = QtWidgets.QVBoxLayout(rb)
        self.real_status = QtWidgets.QLabel("sem telemetria real (receptor desligado)")
        self.real_status.setWordWrap(True)
        self.real_table = QtWidgets.QTableWidget(N_WHEELS, 5)
        self.real_table.setHorizontalHeaderLabels(["motor", "cmd", "medido", "pwm", "corrente"])
        self.real_table.verticalHeader().setVisible(False)
        self.real_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.real_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        for i in range(N_WHEELS):
            for j in range(5):
                self.real_table.setItem(i, j, QtWidgets.QTableWidgetItem(f"m{i + 1}" if j == 0 else "-"))
        self.real_body = QtWidgets.QLabel("-")
        rl.addWidget(self.real_status)
        rl.addWidget(self.real_body)
        rl.addWidget(self.real_table)
        right.addWidget(rb, 1)
        root.addLayout(right, 3)

    # ------------------------------------------------------------------ selection
    @property
    def view_mode(self) -> str:
        """``"3d"`` or ``"2d"``: which view the stack shows."""
        return "3d" if self.view3d is not None and self.stack.currentWidget() is self.view3d else "2d"

    def set_view_mode(self, mode) -> None:
        mode = ("2d" if mode == 1 else "3d") if isinstance(mode, int) else str(mode).lower()
        if mode == "3d" and self.view3d is not None and self.view3d.available:
            self.stack.setCurrentWidget(self.view3d)
        else:
            self.stack.setCurrentWidget(self.spotlight)
        want = 0 if self.view_mode == "3d" else 1
        if self.view_box.currentIndex() != want:
            self.view_box.blockSignals(True)
            self.view_box.setCurrentIndex(want)
            self.view_box.blockSignals(False)
        self.redraw()

    def set_robots(self, keys) -> None:
        """The robots offered by the selector (every present robot, both teams)."""
        keys = [(str(k[0]), int(k[1])) for k in keys]
        if keys == self._keys:
            return
        self._keys = keys
        self.robot_box.blockSignals(True)
        self.robot_box.clear()
        for k in keys:
            self.robot_box.addItem(f"{k[0]} {k[1]}", k)
        if self._key in keys:
            self.robot_box.setCurrentIndex(keys.index(self._key))
        self.robot_box.blockSignals(False)

    def _on_box(self, i: int) -> None:
        key = self.robot_box.itemData(i)
        if key is not None and tuple(key) != self._key:
            self.robot_requested.emit(tuple(key))

    def _cycle(self, step: int) -> None:
        if not self._keys:
            return
        i = (self._keys.index(self._key) + step) % len(self._keys) if self._key in self._keys else 0
        self.robot_requested.emit(self._keys[i])

    # ------------------------------------------------------------------ data in
    def set_selected(self, key: tuple[str, int] | None) -> None:
        if key != self._key:
            self._key = key
            self.wheel_plot.clear_data()
            if self.view3d is not None:
                self.view3d.reset_motion()
            self.header.setText(f"robo {key[1]} ({key[0]})" if key is not None else "nenhum robo selecionado")
        if key in self._keys and self.robot_box.currentIndex() != self._keys.index(key):
            self.robot_box.blockSignals(True)
            self.robot_box.setCurrentIndex(self._keys.index(key))
            self.robot_box.blockSignals(False)

    def reset_motion(self) -> None:
        """Backend change / new session: wheel curve and integrated wheel angles start over."""
        self.wheel_plot.clear_data()
        if self.view3d is not None:
            self.view3d.reset_motion()

    def set_receiver_state(self, text: str) -> None:
        self.real_status.setText(text)

    def update_record(self, twin: RobotTelemetry | None, real: RobotTelemetry | None = None) -> None:
        """New records for the selected robot (call at the display rate; cheap when hidden)."""
        self.twin, self.real = twin, real
        if twin is not None:
            self.wheel_plot.append(twin.t, twin.wheel_cmd, twin.wheel_meas,
                                   real.wheel_meas if real is not None else None)
        if self.view3d is not None:
            self.view3d.set_record(twin, real)              # integrates the wheel angles; draws only if visible
        if not self.isVisible():
            return
        self.redraw(skip_3d=True)

    def redraw(self, skip_3d: bool = False) -> None:
        tw, rl = self.twin, self.real
        if self.view_mode == "2d":
            self.spotlight.set_record(tw)
        elif self.view3d is not None and not skip_3d:
            self.view3d.redraw()
        L = self.state_labels
        if tw is None:
            for lab in L.values():
                lab.setText("-")
            self.bars.set_values(None, None, None)
            self.wheel_values.setText("-")
        else:
            L["pose"].setText("-" if tw.pose is None else
                              f"{tw.pose[0]:+.3f} m, {tw.pose[1]:+.3f} m, {math.degrees(tw.pose[2]):+.1f} deg")
            L["v_cmd"].setText(f"{_fmt(tw.cmd_vx)} m/s, {_fmt(tw.cmd_vy)} m/s, {_fmt(tw.cmd_w)} rad/s")
            L["v_meas"].setText(f"{_fmt(_flush(tw.vx))} m/s, {_fmt(_flush(tw.vy))} m/s, {_fmt(_flush(tw.w))} rad/s")
            L["age"].setText("-" if tw.cmd_age_s is None else f"{1e3 * tw.cmd_age_s:.0f} ms")
            L["watchdog"].setText("-" if tw.watchdog is None else ("DISPARADO (sem comando)" if tw.watchdog else "ok"))
            L["dribbler"].setText(_fmt(tw.dribbler_on))
            L["ball"].setText("bola no dribbler" if tw.has_ball else "livre")
            L["kicks"].setText(_fmt(tw.kicks))
            self.bars.set_values(tw.wheel_cmd, tw.wheel_meas, rl.wheel_meas if rl is not None else None)
            self.wheel_plot.redraw()
            wc = " ".join(f"{_flush(v):+6.1f}" for v in (tw.wheel_cmd or ()))
            wm = " ".join(f"{_flush(v):+6.1f}" for v in (tw.wheel_meas or ()))
            self.wheel_values.setText(f"comando  [{wc}] rad/s\nresultante [{wm}] rad/s")
        # hardware: the real robot when it reports, else the twin's illustrative model
        if rl is not None:
            ub, uc = self.units.get("battery", ""), self.units.get("capacitor", "")
            self.hw_note.setText("valores do robo real (radio)")
            self.battery.set_fraction(None, f"{rl.battery:.2f} {ub}".strip())
            self.capacitor.set_fraction(None, f"{rl.capacitor:.2f} {uc}".strip())
            self.ir.setText("IR: " + ("bola detectada" if rl.has_ball else "livre") + " (real)")
        elif tw is not None and tw.battery is not None:
            self.hw_note.setText("modelo ILUSTRATIVO: bateria e capacitor nao foram identificados"
                                 if tw.hardware_illustrative else "")
            self.battery.set_fraction(tw.battery, f"{100 * tw.battery:.1f} % (modelo)")
            self.capacitor.set_fraction(tw.capacitor, f"{100 * (tw.capacitor or 0.0):.0f} % (modelo)")
            self.ir.setText("IR: " + ("bola detectada" if tw.has_ball else "livre") + " (gemeo)")
        else:
            self.hw_note.setText("")
            self.battery.set_fraction(None, "-")
            self.capacitor.set_fraction(None, "-")
            self.ir.setText("IR: -")
        # radio block
        if rl is None:
            self.real_body.setText("-")
            for i in range(N_WHEELS):
                for j in range(1, 5):
                    self.real_table.item(i, j).setText("-")
        else:
            self.real_body.setText(f"v real: {rl.vx:+.3f} m/s, {rl.vy:+.3f} m/s, {rl.w:+.3f} rad/s")
            for i in range(N_WHEELS):
                vals = (rl.wheel_cmd, rl.wheel_meas, rl.pwm, rl.current)
                for j, arr in enumerate(vals, start=1):
                    self.real_table.item(i, j).setText("-" if arr is None else f"{arr[i]:.2f}")


__all__ = ["RobotTab", "RobotSpotlight", "RobotView3D", "WheelBars", "WheelPlot", "WHEEL_MAX_RAD_S"]
