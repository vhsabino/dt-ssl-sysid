"""3D view of **one** robot for the *Robot* tab (``pyqtgraph.opengl``): the selected robot drawn with the
RobôCIn v2025 CAD meshes at the origin of its body frame, turned freely with the mouse like a part in a CAD
viewer, with its wheels spinning at the speeds of the telemetry record.

* **Rotation** (left drag): an arcball (:class:`dtssl.gui.scene3d.Arcball`), so the part turns about the axis
  the mouse describes on the screen, any axis, no gimbal limit; the camera itself stays put. Wheel zooms,
  middle/right drag pans (``GLViewWidget`` defaults), double click or ``R`` resets the view, ``F`` refits the
  distance, arrow keys nudge the rotation, ``Auto`` spins the part like a turntable.
* **Wheels**: their angles are integrated from ``wheel_meas`` of the record (rad/s; the twin's come from the
  inverse kinematics of the body velocity, a real robot's from the radio when *real* is chosen) and each wheel
  is coloured by its speed (red forward, blue backward, like the 2D spotlight). The ball is drawn at the
  dribbler when the sensor sees it; the commanded (orange) and resulting (cyan) body velocities are arrows
  above the cover; a small axis triad marks the body frame (x red = dribbler, y green, z blue).
* Presets: ``iso``, ``frente`` (dribbler towards the viewer), ``lado``, ``topo``, ``baixo`` (wheels).

Without PyOpenGL or a GL-capable platform the widget shows a label with the reason (``available`` False) and
the tab falls back to the 2D spotlight. The widget only draws while visible.
"""
from __future__ import annotations

import logging
import math

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, Signal

from dtssl.bridge.telemetry import RobotTelemetry
from dtssl.gui import scene3d as S
from dtssl.physics.mjcf import WheelGeometry, load_ball_spec, load_wheel_geometry
from dtssl.sim.world import RobotSpec

log = logging.getLogger(__name__)

try:  # optional: PyOpenGL
    import pyqtgraph.opengl as gl

    GL_IMPORT_ERROR: str | None = None
except Exception as _e:  # noqa: BLE001 - ImportError or a GL loader failure
    gl = None
    GL_IMPORT_ERROR = f"{type(_e).__name__}: {_e}"

CMD_RGBA = (1.0, 0.67, 0.0, 1.0)
MEAS_RGBA = (0.0, 0.90, 1.0, 1.0)
CHASSIS_RGBA = (0.46, 0.47, 0.52, 1.0)     # lighter than the field view: one part under a CAD-style headlight
PRIMITIVE_RGBA = (0.40, 0.40, 0.45, 1.0)
ARROW_M_PER_MPS = 0.09              # 2 m/s = 0.18 m arrow (one robot diameter)
WHEEL_HOT_FWD = (1.0, 0.32, 0.32)
WHEEL_HOT_BACK = (0.25, 0.61, 1.0)
WHEEL_COLD = (0.62, 0.62, 0.66)
WHEEL_MAX_RAD_S = 120.0
HEADLIGHT_SHADER = "dtssl_headlight"


def _qmatrix(m: np.ndarray) -> QtGui.QMatrix4x4:
    return QtGui.QMatrix4x4(*[float(v) for v in np.asarray(m, dtype=float).reshape(16)])


def _headlight_shader():
    """CAD-style lighting: a light above and to the right of the viewer, both faces lit, 35 % ambient
    (pyqtgraph's ``shaded`` lights from behind the part, which leaves a single part almost black). Built from
    the vertex shader of pyqtgraph's own ``shaded`` program (so it follows the pyqtgraph version) plus this
    fragment shader; registered once under :data:`HEADLIGHT_SHADER`. Returns ``"shaded"`` when anything is
    off, so drawing never depends on it."""
    try:
        from pyqtgraph.opengl import shaders as sh

        prog = sh.ShaderProgram.names.get(HEADLIGHT_SHADER)
        if prog is None:
            base = sh.ShaderProgram.names["shaded"]
            vert = [s for s in base.shaders if isinstance(s, sh.VertexShader)][0]
            frag = sh.FragmentShader("""
                #ifdef GL_ES
                precision mediump float;
                #endif
                varying vec4 v_color;
                varying vec3 v_normal;
                void main() {
                    float p = abs(dot(v_normal, normalize(vec3(0.35, 0.5, 0.8))));
                    vec3 rgb = v_color.rgb * (0.35 + 0.7 * p);
                    gl_FragColor = vec4(rgb, v_color.a);
                }
            """)
            prog = sh.ShaderProgram(HEADLIGHT_SHADER, [vert, frag])
        return prog
    except Exception as e:  # noqa: BLE001 - unexpected pyqtgraph internals: keep the stock shader
        log.warning("robot 3D view: headlight shader unavailable (%s); using 'shaded'", e)
        return "shaded"


def wheel_rgba(omega: float | None) -> tuple[float, float, float, float]:
    """Wheel colour from its speed (rad/s): grey at rest, red forward, blue backward, saturating at
    ``WHEEL_MAX_RAD_S``."""
    if omega is None:
        return (*WHEEL_COLD, 1.0)
    a = min(1.0, abs(float(omega)) / WHEEL_MAX_RAD_S)
    hot = WHEEL_HOT_FWD if omega >= 0 else WHEEL_HOT_BACK
    return tuple(c + (h - c) * a for c, h in zip(WHEEL_COLD, hot, strict=True)) + (1.0,)


class _ArcballView(gl.GLViewWidget if gl is not None else object):
    """``GLViewWidget`` whose left drag turns the part (arcball) instead of orbiting the camera."""

    rotated = Signal()
    reset_requested = Signal()

    def __init__(self, arcball: S.Arcball, parent=None):
        super().__init__(parent)
        self.arcball = arcball
        self.setMouseTracking(False)

    def screen_axes(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Camera ``right``, ``up`` and ``toward the viewer`` unit vectors in world coordinates."""
        M = np.array(self.viewMatrix().data(), dtype=float).reshape(4, 4).T
        return M[0, :3], M[1, :3], M[2, :3]

    def mousePressEvent(self, ev):  # noqa: N802
        if ev.button() == Qt.MouseButton.LeftButton and not (ev.modifiers() & Qt.KeyboardModifier.ControlModifier):
            p = ev.position()
            self.arcball.begin(p.x(), p.y(), self.width(), self.height())
            ev.accept()
            return
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):  # noqa: N802
        if self.arcball.dragging:
            p = ev.position()
            if self.arcball.drag(p.x(), p.y(), self.width(), self.height(), *self.screen_axes()):
                self.rotated.emit()
            ev.accept()
            return
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):  # noqa: N802
        if self.arcball.dragging and ev.button() == Qt.MouseButton.LeftButton:
            self.arcball.end()
            ev.accept()
            return
        super().mouseReleaseEvent(ev)

    def mouseDoubleClickEvent(self, ev):  # noqa: N802
        self.reset_requested.emit()
        ev.accept()


class RobotView3D(QtWidgets.QWidget):
    """Toolbar + arcball GL view of one robot; feed :meth:`set_record` at the display rate."""

    view_changed = Signal(str)

    def __init__(self, spec: RobotSpec | None = None, wheel: WheelGeometry | None = None, cad: bool = True,
                 hq: bool = True, parent=None):
        super().__init__(parent)
        self.spec = spec or RobotSpec()
        self.wheel = wheel or load_wheel_geometry()
        self.ball_radius = load_ball_spec().radius
        self.cad = bool(cad)
        self.hq = bool(hq)
        self.wheel_source = "twin"            # "twin" | "real"
        self.auto_rotate = False
        self.frames = 0
        self.twin: RobotTelemetry | None = None
        self.real: RobotTelemetry | None = None
        self.available = gl is not None
        self.error = GL_IMPORT_ERROR
        self._meshes: S.RobotMeshes | None = None
        self._angles = S.WheelAngles(len(self.wheel.angles))
        self._items: list = []
        self.arcball = S.Arcball(centre=(0.0, 0.0, 0.07))

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.toolbar = QtWidgets.QToolBar("robot 3D")
        self.toolbar.setIconSize(QtCore.QSize(14, 14))
        lay.addWidget(self.toolbar)
        if not self.available:
            self.view = None
            self.label = QtWidgets.QLabel(f"vista 3D indisponivel: {self.error}\n\npip install PyOpenGL (extra dtssl[gui])")
            self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.label.setWordWrap(True)
            lay.addWidget(self.label, 1)
            self.toolbar.setEnabled(False)
            return
        self.view = _ArcballView(self.arcball)
        self.view.setBackgroundColor((22, 22, 26, 255))
        self.view.opts["fov"] = 40
        self.view.setMinimumSize(200, 200)
        self.view.rotated.connect(self._on_rotated)
        self.view.reset_requested.connect(self.reset_view)
        lay.addWidget(self.view, 1)
        self.hint = QtWidgets.QLabel("arraste para girar em qualquer eixo, roda do mouse aproxima, botao do meio "
                                     "arrasta, duplo clique ou R reinicia")
        self.hint.setStyleSheet("color: #9e9e9e; font-size: 10px;")
        self.hint.setWordWrap(True)
        lay.addWidget(self.hint)
        self._build_toolbar()
        self._build_items()
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._auto_step)
        self.set_view("iso")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ------------------------------------------------------------------ construction
    def _build_toolbar(self) -> None:
        tb = self.toolbar
        self.view_actions: dict[str, QtGui.QAction] = {}
        for name in S.ROBOT_VIEW_PRESETS:
            a = tb.addAction(name)
            a.triggered.connect(lambda _=False, n=name: self.set_view(n))
            self.view_actions[name] = a
        tb.addSeparator()
        self.act_auto = tb.addAction("Auto")
        self.act_auto.setCheckable(True)
        self.act_auto.setToolTip("gira o robo continuamente (mesa giratoria)")
        self.act_auto.toggled.connect(self.set_auto_rotate)
        self.act_hq = tb.addAction("HQ")
        self.act_hq.setCheckable(True)
        self.act_hq.setChecked(self.hq)
        self.act_hq.setToolTip("malhas CAD em resolucao cheia (37k + 4x8k faces); desligue se pesar")
        self.act_hq.toggled.connect(self.set_hq)
        self.act_cad = tb.addAction("CAD")
        self.act_cad.setCheckable(True)
        self.act_cad.setChecked(self.cad)
        self.act_cad.setToolTip("malhas CAD do RoboCIn v2025 (desligado = formas primitivas)")
        self.act_cad.toggled.connect(self.set_cad)
        tb.addSeparator()
        self.source_box = QtWidgets.QComboBox()
        self.source_box.addItems(["rodas: gemeo", "rodas: real"])
        self.source_box.setToolTip("de onde vem a velocidade das rodas desenhadas: cinematica inversa do gemeo "
                                   "ou o Feedback do radio (quando ha robo real reportando)")
        self.source_box.currentIndexChanged.connect(lambda i: self.set_wheel_source("real" if i == 1 else "twin"))
        tb.addWidget(self.source_box)
        self.info = QtWidgets.QLabel("")
        self.info.setStyleSheet("padding-left: 6px;")
        tb.addWidget(self.info)

    def _robot_meshes(self) -> S.RobotMeshes:
        if self._meshes is None:
            try:
                self._meshes = S.RobotMeshes.build(self.wheel, self.spec, cad=self.cad, lod=not self.hq)
            except Exception as e:  # noqa: BLE001 - e.g. LFS pointer instead of the OBJ
                log.warning("robot 3D view: CAD meshes unavailable (%s); drawing primitives", e)
                self.cad = False
                self._meshes = S.RobotMeshes.build(self.wheel, self.spec, cad=False)
        return self._meshes

    def _build_items(self) -> None:
        for it in self._items:
            self.view.removeItem(it)
        self._items = []
        meshes = self._robot_meshes()
        self._shader = _headlight_shader()
        opts = dict(smooth=False, computeNormals=True, shader=self._shader, drawEdges=False, glOptions="opaque")
        col = CHASSIS_RGBA if meshes.cad else PRIMITIVE_RGBA
        self.chassis = gl.GLMeshItem(vertexes=meshes.chassis.vertices, faces=meshes.chassis.faces, color=col, **opts)
        self.wheels = [gl.GLMeshItem(vertexes=meshes.wheel.vertices, faces=meshes.wheel.faces, color=S.WHEEL_RGBA,
                                     **opts) for _ in self.wheel.angles]
        # kicker and dribbler (CAD only): fixed to the chassis, drawn with its transform
        self.mechanisms = [gl.GLMeshItem(vertexes=m.vertices, faces=m.faces, color=S.MECHANISM_RGBA[k], **opts)
                           for k, m in meshes.mechanisms.items()]
        self.plate = None
        self._plate_key: tuple[str, int] | None = None
        md = gl.MeshData.sphere(rows=10, cols=16, radius=self.ball_radius)
        self.ball = gl.GLMeshItem(meshdata=md, smooth=True, color=S.BALL_RGBA, shader=self._shader, glOptions="opaque")
        self.ball.setVisible(False)
        self.grid = gl.GLGridItem()
        self.grid.setSize(0.5, 0.5, 0.0)
        self.grid.setSpacing(0.05, 0.05, 0.0)
        self.grid.setColor((120, 120, 130, 90))
        L = 0.13
        self.axes = [gl.GLLinePlotItem(pos=np.array([[0.0, 0.0, 0.0], v]), color=S.AXIS_RGBA[k], width=3.0,
                                       antialias=True, mode="lines")
                     for k, v in (("x", [L, 0.0, 0.0]), ("y", [0.0, L, 0.0]), ("z", [0.0, 0.0, L]))]
        self.arrow_cmd = gl.GLLinePlotItem(pos=np.zeros((0, 3)), color=CMD_RGBA, width=3.0, antialias=True, mode="lines")
        self.arrow_meas = gl.GLLinePlotItem(pos=np.zeros((0, 3)), color=MEAS_RGBA, width=3.0, antialias=True,
                                            mode="lines")
        self._items = [self.grid, *self.axes, self.chassis, *self.wheels, *self.mechanisms, self.ball, self.arrow_cmd,
                       self.arrow_meas]
        for it in self._items:
            self.view.addItem(it)
        self._angles.reset()
        self._apply_transforms()

    def _ensure_plate(self, key: tuple[str, int] | None) -> None:
        if key == self._plate_key:
            return
        if self.plate is not None:
            self.view.removeItem(self.plate)
            self._items.remove(self.plate)
            self.plate = None
        self._plate_key = key
        if key is None:
            return
        meshes = self._robot_meshes()
        pm = S.id_plate_mesh(key[0], key[1], meshes.z_top + S.PLATE_Z_OVER_TOP)
        self.plate = gl.GLMeshItem(vertexes=pm.vertices, faces=pm.faces, faceColors=pm.colors, smooth=False,
                                   computeNormals=True, shader=self._shader, drawEdges=False, glOptions="opaque")
        self.view.addItem(self.plate)
        self._items.append(self.plate)

    # ------------------------------------------------------------------ settings
    def set_cad(self, on: bool) -> None:
        on = bool(on)
        if on == self.cad:
            return
        self.cad = on
        self._meshes = None
        if self.view is not None:
            self._ensure_plate(None)
            self._build_items()
            self.redraw(force=True)

    def set_hq(self, on: bool) -> None:
        on = bool(on)
        if on == self.hq:
            return
        self.hq = on
        self._meshes = None
        if self.view is not None:
            self._ensure_plate(None)
            self._build_items()
            self.redraw(force=True)

    def set_wheel_source(self, source: str) -> None:
        source = "real" if source == "real" else "twin"
        if source != self.wheel_source:
            self.wheel_source = source
            if self.view is not None and self.source_box.currentIndex() != (1 if source == "real" else 0):
                self.source_box.setCurrentIndex(1 if source == "real" else 0)

    def set_auto_rotate(self, on: bool) -> None:
        self.auto_rotate = bool(on)
        if self.view is None:
            return
        if self.act_auto.isChecked() != self.auto_rotate:
            self.act_auto.setChecked(self.auto_rotate)
        if self.auto_rotate and self.isVisible():
            self._timer.start()
        else:
            self._timer.stop()

    def reset_motion(self) -> None:
        """Forget the integrated wheel angles (backend change, new session)."""
        self._angles.reset()

    # ------------------------------------------------------------------ camera / rotation
    def set_view(self, name: str) -> None:
        """Camera preset; the part rotation is reset so the preset means what it says."""
        if self.view is None:
            return
        el, az = S.ROBOT_VIEW_PRESETS[name]
        self.arcball.reset()
        c = self.arcball.centre
        self.view.setCameraPosition(pos=QtGui.QVector3D(float(c[0]), float(c[1]), float(c[2])),
                                    distance=S.ROBOT_VIEW_DISTANCE, elevation=el, azimuth=az)
        self._apply_transforms()
        self.view_changed.emit(name)
        self.view.update()

    def reset_view(self) -> None:
        self.set_view("iso")

    def rotate(self, axis, angle_rad: float) -> None:
        """Turn the part about a world ``axis`` (keyboard, tests)."""
        self.arcball.spin(axis, angle_rad)
        self._apply_transforms()
        if self.view is not None:
            self.view.update()

    def drag(self, x0: float, y0: float, x1: float, y1: float) -> None:
        """Programmatic left drag from pixel ``(x0, y0)`` to ``(x1, y1)`` (what the mouse does)."""
        if self.view is None:
            return
        w, h = self.view.width(), self.view.height()
        self.arcball.begin(x0, y0, w, h)
        self.arcball.drag(x1, y1, w, h, *self.view.screen_axes())
        self.arcball.end()
        self._on_rotated()

    def camera(self) -> dict:
        o = self.view.opts if self.view is not None else {}
        return {k: o.get(k) for k in ("center", "distance", "elevation", "azimuth")}

    def _on_rotated(self) -> None:
        self._apply_transforms()
        self.view.update()

    def _auto_step(self) -> None:
        self.rotate((0.0, 0.0, 1.0), math.radians(0.8))

    # ------------------------------------------------------------------ per frame
    def set_record(self, twin: RobotTelemetry | None, real: RobotTelemetry | None = None) -> None:
        """New records of the selected robot (call at the display rate; cheap while hidden)."""
        self.twin, self.real = twin, real
        src = self._speeds_source()
        if src is not None:
            self._angles.advance(float(src.t), src.wheel_meas)
        if self.view is None or not self.isVisible():
            return
        self.redraw()

    def _speeds_source(self) -> RobotTelemetry | None:
        if self.wheel_source == "real" and self.real is not None:
            return self.real
        return self.twin

    def redraw(self, force: bool = False) -> None:
        if self.view is None or (not force and not self.isVisible()):
            return
        tw = self.twin
        src = self._speeds_source()
        self._ensure_plate((tw.team, tw.id) if tw is not None and tw.team is not None else None)
        speeds = src.wheel_meas if src is not None else None
        for i, it in enumerate(self.wheels):
            it.setColor(wheel_rgba(None if speeds is None or i >= len(speeds) else speeds[i]))
        self.ball.setVisible(bool(tw is not None and tw.has_ball))
        if tw is not None:
            self.arrow_cmd.setData(pos=S.arrow_segments(tw.cmd_vx or 0.0, tw.cmd_vy or 0.0, self._top_z() + 0.03,
                                                        ARROW_M_PER_MPS))
            self.arrow_meas.setData(pos=S.arrow_segments(tw.vx, tw.vy, self._top_z() + 0.02, ARROW_M_PER_MPS))
            fonte = "real (radio)" if src is not None and src.source == "real" else "gemeo (cin. inversa)"
            self.info.setText(f"rodas {fonte}: " + " ".join(f"{float(v):+.0f}" for v in (speeds or ())) + " rad/s")
        else:
            self.arrow_cmd.setData(pos=np.zeros((0, 3)))
            self.arrow_meas.setData(pos=np.zeros((0, 3)))
            self.info.setText("")
        self._apply_transforms()
        self.frames += 1
        self.view.update()

    def _top_z(self) -> float:
        return float(self._robot_meshes().z_top)

    def _apply_transforms(self) -> None:
        if self.view is None:
            return
        meshes = self._robot_meshes()
        T = self.arcball.transform()
        chassis_T, wheel_Ts, body_T = S.robot_part_transforms(T, meshes, self.wheel, self._angles.angles)
        qc = _qmatrix(chassis_T)
        self.chassis.setTransform(qc)
        for it in self.mechanisms:
            it.setTransform(qc)
        for it, wt in zip(self.wheels, wheel_Ts, strict=True):
            it.setTransform(_qmatrix(wt))
        qb = _qmatrix(body_T)
        for it in (self.grid, *self.axes, self.arrow_cmd, self.arrow_meas):
            it.setTransform(qb)
        if self.plate is not None:
            self.plate.setTransform(qb)
        self.ball.setTransform(_qmatrix(body_T @ S.translate(self.spec.dribbler_offset + self.ball_radius * 0.9, 0.0,
                                                             self.ball_radius)))

    # ------------------------------------------------------------------ misc
    def grab_image(self) -> QtGui.QImage | None:
        if self.view is None:
            return None
        img = self.view.grabFramebuffer()
        return None if img.isNull() else img

    def keyPressEvent(self, ev: QtGui.QKeyEvent) -> None:  # noqa: N802
        k = ev.key()
        step = math.radians(5.0)
        if k == Qt.Key.Key_R:
            self.reset_view()
        elif k == Qt.Key.Key_F and self.view is not None:
            self.view.opts["distance"] = S.ROBOT_VIEW_DISTANCE
            self.view.update()
        elif k == Qt.Key.Key_Left:
            self.rotate((0.0, 0.0, 1.0), -step)
        elif k == Qt.Key.Key_Right:
            self.rotate((0.0, 0.0, 1.0), step)
        elif k in (Qt.Key.Key_Up, Qt.Key.Key_Down) and self.view is not None:
            right = self.view.screen_axes()[0]
            self.rotate(right, step if k == Qt.Key.Key_Up else -step)
        else:
            ev.ignore()
            return
        ev.accept()

    def showEvent(self, ev) -> None:  # noqa: N802
        super().showEvent(ev)
        if self.view is not None:
            self.redraw(force=True)
            if self.auto_rotate:
                self._timer.start()

    def hideEvent(self, ev) -> None:  # noqa: N802
        super().hideEvent(ev)
        if self.view is not None:
            self._timer.stop()


__all__ = ["RobotView3D", "wheel_rgba", "GL_IMPORT_ERROR"]
