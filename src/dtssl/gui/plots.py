"""Time-series plots (pyqtgraph): commanded vs body velocity per DOF (+ ``e_pos(t)`` in Replay).

Rows ``vx``, ``vy``, ``w`` share the x axis. Two operating modes:

* **sliding** (Debug/Bridge): :meth:`VelocityPlots.append` at 60 Hz into a ring buffer, the
  view shows the last ``window_s`` seconds; the widget redraws itself at 30 Hz (own ``QTimer``,
  :meth:`start` / :meth:`stop`) or on demand (:meth:`redraw`).
* **fixed** (Replay): :meth:`set_series` with the whole event (commands, simulated and truth
  body velocities, ``e_pos(t)``), horizon markers from ``config/metrics.json`` and a playhead
  (:meth:`set_playhead`).
"""
from __future__ import annotations

import math

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

pg.setConfigOptions(antialias=False, background="k", foreground="w")

DOF_LABELS = (("vx", "m/s"), ("vy", "m/s"), ("w", "rad/s"))
# Smallest view spans the ViewBox may show (pyqtgraph enforces them in updateViewRange). Below ~1e-320 of
# span, pyqtgraph 0.14's tickSpacing() underflows to a 0 spacing and AxisItem.tickValues() divides by zero.
MIN_X_RANGE_S = 0.25
MIN_Y_RANGE = 1e-3
# Velocities below this (m/s, rad/s) are shown as exactly 0: a FOPDT state decays as v*exp(-Ts/tau) forever
# and reaches the subnormal range (~1e-308 .. 5e-324) a few minutes after the last command, which is
# physically meaningless and is what produced the subnormal-width y range (see MIN_Y_RANGE).
DISPLAY_FLUSH = 1e-9


class SafeAxisItem(pg.AxisItem):
    """``AxisItem`` whose tick levels never carry a zero/non-finite spacing (pyqtgraph 0.14 underflow)."""

    def tickSpacing(self, minVal, maxVal, size):  # noqa: N802 - pyqtgraph API
        try:
            levels = super().tickSpacing(minVal, maxVal, size)
        except (ZeroDivisionError, ValueError, OverflowError):
            return []
        return [(s, o) for s, o in levels if math.isfinite(s) and s > 0.0 and math.isfinite(o)]

    def tickValues(self, minVal, maxVal, size):  # noqa: N802 - pyqtgraph API
        if not (math.isfinite(minVal) and math.isfinite(maxVal)) or maxVal == minVal:
            return []
        try:
            return super().tickValues(minVal, maxVal, size)
        except (ZeroDivisionError, ValueError, OverflowError):
            return []


def _safe_axes() -> dict[str, pg.AxisItem]:
    return {"left": SafeAxisItem("left"), "bottom": SafeAxisItem("bottom")}


def _flush(v: float) -> float:
    """Display-only: |v| < DISPLAY_FLUSH -> 0.0 (NaN passes through)."""
    v = float(v)
    return 0.0 if abs(v) < DISPLAY_FLUSH else v


CMD_PEN = pg.mkPen((180, 180, 180), width=1, style=QtCore.Qt.DashLine)
SIM_PEN = pg.mkPen((0, 229, 255), width=2)
TRUTH_PEN = pg.mkPen((255, 64, 129), width=2)
EPOS_PEN = pg.mkPen((255, 193, 7), width=2)
PLAYHEAD_PEN = pg.mkPen((255, 255, 255, 160), width=1)
HORIZON_PEN = pg.mkPen((120, 200, 120, 160), width=1, style=QtCore.Qt.DotLine)


class RingBuffer:
    """Fixed-size (n, k) float ring buffer with chronological read-out."""

    def __init__(self, n: int, k: int):
        self.buf = np.zeros((int(n), int(k)), dtype=float)
        self.n = int(n)
        self.i = 0
        self.count = 0

    def append(self, row) -> None:
        self.buf[self.i] = row
        self.i = (self.i + 1) % self.n
        self.count = min(self.count + 1, self.n)

    def data(self) -> np.ndarray:
        if self.count < self.n:
            return self.buf[: self.count]
        return np.concatenate([self.buf[self.i:], self.buf[: self.i]], axis=0)

    def clear(self) -> None:
        self.i = 0
        self.count = 0

    def __len__(self) -> int:
        return self.count


class VelocityPlots(QtWidgets.QWidget):
    def __init__(self, window_s: float = 10.0, rate_hz: float = 60.0, redraw_hz: float = 30.0, parent=None):
        super().__init__(parent)
        self.window_s = float(window_s)
        self.rate_hz = float(rate_hz)
        self.mode = "sliding"
        self.samples = 0
        self.redraws = 0
        self._dirty = False
        self._buf = RingBuffer(int(self.window_s * self.rate_hz * 1.5) + 8, 10)   # t, cmd3, sim3, truth3
        self._series: dict[str, np.ndarray] | None = None
        self._playhead_t = 0.0
        self._horizon_items: list = []

        self.glw = pg.GraphicsLayoutWidget()
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.glw)

        self.plots: list[pg.PlotItem] = []
        self.cmd_curves: list[pg.PlotDataItem] = []
        self.sim_curves: list[pg.PlotDataItem] = []
        self.truth_curves: list[pg.PlotDataItem] = []
        self.playheads: list[pg.InfiniteLine] = []
        for i, (name, unit) in enumerate(DOF_LABELS):
            p = self.glw.addPlot(row=i, col=0, axisItems=_safe_axes())
            p.getViewBox().setLimits(minXRange=MIN_X_RANGE_S, minYRange=MIN_Y_RANGE)
            p.setLabel("left", name, units=unit)
            p.getAxis("left").enableAutoSIPrefix(False)
            p.showGrid(x=True, y=True, alpha=0.25)
            p.setMenuEnabled(False)
            p.hideButtons()
            p.setDownsampling(auto=True, mode="peak")
            p.setClipToView(True)
            if i > 0:
                p.setXLink(self.plots[0])
            if i == 0:
                self.legend = p.addLegend(offset=(10, 2))
                self.legend.setBrush(pg.mkBrush(0, 0, 0, 120))
            self.cmd_curves.append(p.plot(pen=CMD_PEN, name="cmd" if i == 0 else None))
            self.sim_curves.append(p.plot(pen=SIM_PEN, name="sim" if i == 0 else None))
            tc = p.plot(pen=TRUTH_PEN)
            tc.setVisible(False)
            self.truth_curves.append(tc)
            ph = pg.InfiniteLine(angle=90, movable=False, pen=PLAYHEAD_PEN)
            ph.setVisible(False)
            p.addItem(ph)
            self.playheads.append(ph)
            self.plots.append(p)
        self.plots[-1].setLabel("bottom", "t", units="s")

        self.epos_plot = self.glw.addPlot(row=len(DOF_LABELS), col=0, axisItems=_safe_axes())
        self.epos_plot.getViewBox().setLimits(minXRange=MIN_X_RANGE_S, minYRange=MIN_Y_RANGE)
        self.epos_plot.setLabel("left", "e_pos", units="m")
        self.epos_plot.getAxis("left").enableAutoSIPrefix(False)
        self.epos_plot.setLabel("bottom", "t", units="s")
        self.epos_plot.showGrid(x=True, y=True, alpha=0.25)
        self.epos_plot.setMenuEnabled(False)
        self.epos_plot.hideButtons()
        self.epos_plot.setXLink(self.plots[0])
        self.epos_curve = self.epos_plot.plot(pen=EPOS_PEN)
        self.epos_markers = pg.ScatterPlotItem(size=8, pen=pg.mkPen("w"), brush=pg.mkBrush(255, 193, 7))
        self.epos_plot.addItem(self.epos_markers)
        self.epos_playhead = pg.InfiniteLine(angle=90, movable=False, pen=PLAYHEAD_PEN)
        self.epos_plot.addItem(self.epos_playhead)
        self.epos_plot.setVisible(False)
        for row in range(len(DOF_LABELS) + 1):
            self.glw.ci.layout.setRowStretchFactor(row, 1)

        self._timer = QtCore.QTimer(self)
        self._timer.setTimerType(QtCore.Qt.CoarseTimer)
        self._timer.setInterval(int(round(1000.0 / redraw_hz)))
        self._timer.timeout.connect(self.redraw)

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def clear(self) -> None:
        self._buf.clear()
        self._series = None
        self.samples = 0
        for c in (*self.cmd_curves, *self.sim_curves, *self.truth_curves, self.epos_curve):
            c.setData([], [])
        self.epos_markers.setData([], [])
        self._clear_horizons()
        for p in (*self.plots, self.epos_plot):
            p.setYRange(-1.0, 1.0, padding=0.0)
            p.enableAutoRange(axis="y", enable=True)
        self._dirty = True

    def set_mode(self, mode: str) -> None:
        """``"sliding"`` (live) or ``"fixed"`` (replay: full series + playhead)."""
        if mode not in ("sliding", "fixed"):
            raise ValueError(mode)
        if mode != self.mode:
            self.mode = mode
            self.clear()
        fixed = mode == "fixed"
        self.epos_plot.setVisible(fixed)
        self.plots[-1].setLabel("bottom", None if fixed else "t", units=None if fixed else "s")
        for tc in self.truth_curves:
            tc.setVisible(fixed)
        self.legend.removeItem(self.truth_curves[0])
        if fixed:
            self.legend.addItem(self.truth_curves[0], "truth")
        for ph in self.playheads:
            ph.setVisible(fixed)
        self.epos_playhead.setVisible(fixed)
        self._dirty = True

    # ------------------------------------------------------------------ data in
    def append(self, t: float, cmd, sim, truth=None) -> None:
        """One 60 Hz sample: ``cmd``/``sim``/``truth`` are ``(vx, vy, w)`` in the body frame."""
        tr = truth if truth is not None else (np.nan, np.nan, np.nan)
        self._buf.append((t, _flush(cmd[0]), _flush(cmd[1]), _flush(cmd[2]),
                          _flush(sim[0]), _flush(sim[1]), _flush(sim[2]), _flush(tr[0]), _flush(tr[1]), _flush(tr[2])))
        self.samples += 1
        self._dirty = True

    def set_series(self, t, cmd, sim, truth=None, epos=None, horizons_s=None, horizons_labels=None) -> None:
        """Whole-event series (Replay). Arrays: ``t (N,)``, ``cmd/sim/truth (N, 3)``, ``epos (N,)``."""
        t = np.asarray(t, dtype=float)
        self._series = {"t": t, "cmd": np.asarray(cmd, dtype=float).reshape(-1, 3),
                        "sim": np.asarray(sim, dtype=float).reshape(-1, 3),
                        "truth": None if truth is None else np.asarray(truth, dtype=float).reshape(-1, 3),
                        "epos": None if epos is None else np.asarray(epos, dtype=float).reshape(-1)}
        self.samples = int(t.size)
        self._clear_horizons()
        if epos is not None and horizons_s:
            hx, hy = [], []
            for k, hs in enumerate(horizons_s):
                idx = int(np.argmin(np.abs(t - hs)))
                if idx < t.size:
                    hx.append(float(t[idx]))
                    hy.append(float(self._series["epos"][idx]))
                lbl = horizons_labels[k] if horizons_labels and k < len(horizons_labels) else f"{hs:.2f}s"
                line = pg.InfiniteLine(pos=float(hs), angle=90, movable=False, pen=HORIZON_PEN, label=lbl,
                                       labelOpts={"position": 0.92 - 0.14 * (k % 4), "color": (120, 200, 120),
                                                  "movable": False, "anchors": [(0.0, 0.5), (0.0, 0.5)]})
                self.epos_plot.addItem(line)
                self._horizon_items.append(line)
            self.epos_markers.setData(hx, hy)
        else:
            self.epos_markers.setData([], [])
        if t.size:
            self.plots[0].setXRange(float(t[0]), float(t[-1]), padding=0.01)
        self._dirty = True
        self.redraw()

    def set_playhead(self, t: float) -> None:
        self._playhead_t = float(t)
        self._dirty = True

    def _clear_horizons(self) -> None:
        for it in self._horizon_items:
            self.epos_plot.removeItem(it)
        self._horizon_items = []

    # ------------------------------------------------------------------ redraw (30 Hz)
    def redraw(self) -> None:
        if not self._dirty:
            return
        self._dirty = False
        self.redraws += 1
        if self.mode == "fixed":
            s = self._series
            if s is None:
                return
            t = s["t"]
            for i in range(3):
                self.cmd_curves[i].setData(t, s["cmd"][:, i])
                self.sim_curves[i].setData(t, s["sim"][:, i])
                if s["truth"] is not None:
                    self.truth_curves[i].setData(t, s["truth"][:, i])
                self.playheads[i].setPos(self._playhead_t)
            if s["epos"] is not None:
                self.epos_curve.setData(t, s["epos"])
            self.epos_playhead.setPos(self._playhead_t)
            return
        d = self._buf.data()
        if d.shape[0] == 0:
            return
        t = d[:, 0]
        t_end = float(t[-1])
        t0 = t_end - self.window_s
        m = t >= t0
        for i in range(3):
            self.cmd_curves[i].setData(t[m], d[m, 1 + i])
            self.sim_curves[i].setData(t[m], d[m, 4 + i])
            if self.truth_curves[i].isVisible():
                self.truth_curves[i].setData(t[m], d[m, 7 + i])
        # fixed-width window: [t_first, t_first + W] while the buffer is short (start-up / after clear()),
        # [t_end - W, t_end] once it covers more than W seconds -- never a degenerate span
        x0 = max(float(t[0]), t0)
        self.plots[0].setXRange(x0, x0 + self.window_s, padding=0.0)

    def sample_count(self) -> int:
        return self.samples


__all__ = ["VelocityPlots", "RingBuffer", "SafeAxisItem", "MIN_X_RANGE_S", "MIN_Y_RANGE", "DISPLAY_FLUSH"]
