"""3D view of the world for ``dtssl gui`` (``pyqtgraph.opengl``): field, ball and robots drawn with the
RobôCIn v2025 CAD meshes of ``dtssl.physics.assets`` (the same OBJ files as MuJoCo's ``visual="cad"``).

The view is built from :class:`~dtssl.sim.entities.WorldState` only, so it works with every backend
(``fopdt``, ``ideal``, ``mujoco-*``) and in Replay; geometry and transforms come from
:mod:`dtssl.gui.scene3d`. Mouse: left drag orbits, middle drag (or Shift) pans, wheel zooms
(``GLViewWidget`` defaults). Toolbar: camera presets (``iso``/``top``/``side``/``goal``), *Follow*
(camera centre tracks the selected robot), *CAD* (meshes vs the primitive shapes), *HQ* (full-resolution
meshes instead of the light LOD pair: ~5x more triangles), *Wheels* (spin the wheels from the body velocity
through the inverse kinematics), *Fit* (``F``).

``pyqtgraph.opengl`` needs ``PyOpenGL`` (extra ``dtssl[gui]``) and a GL-capable Qt platform; when either
is missing the widget shows a label with the reason instead of failing (the 2D field view is unaffected).
"""
from __future__ import annotations

import logging

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, Signal

from dtssl.gui import scene3d as S
from dtssl.gui.glshading import headlight_shader
from dtssl.physics.mjcf import WheelGeometry, load_ball_spec, load_wheel_geometry
from dtssl.sim.entities import WorldState
from dtssl.sim.world import FieldGeometry, RobotSpec

log = logging.getLogger(__name__)

try:  # optional: PyOpenGL
    import pyqtgraph.opengl as gl

    GL_IMPORT_ERROR: str | None = None
except Exception as _e:  # noqa: BLE001 - ImportError or a GL loader failure
    gl = None
    GL_IMPORT_ERROR = f"{type(_e).__name__}: {_e}"


def _qmatrix(m: np.ndarray) -> QtGui.QMatrix4x4:
    """numpy 4x4 (row-major) -> ``QMatrix4x4``."""
    return QtGui.QMatrix4x4(*[float(v) for v in np.asarray(m, dtype=float).reshape(16)])


def _mesh_kwargs(mesh: S.Mesh, color) -> dict:
    """``GLMeshItem`` geometry arguments: the per-face CAD colours when the mesh has them, else one ``color``."""
    kw = dict(vertexes=mesh.vertices, faces=mesh.faces)
    if mesh.colors is not None:
        kw["faceColors"] = mesh.colors
    else:
        kw["color"] = color
    return kw


class _RobotItems:
    """GL items of one robot: chassis, 4 wheels, kicker and dribbler (CAD only, fixed to the chassis), id plate
    (+ selection ring)."""

    def __init__(self, view, key: tuple[str, int], meshes: S.RobotMeshes, spec: RobotSpec, shader="shaded"):
        team, rid = key
        self.key = key
        opts = dict(smooth=False, computeNormals=True, shader=shader, drawEdges=False, glOptions="opaque")
        col = S.CHASSIS_RGBA if meshes.cad else S.PRIMITIVE_RGBA
        self.chassis = gl.GLMeshItem(**_mesh_kwargs(meshes.chassis, col), **opts)
        self.wheels = [gl.GLMeshItem(**_mesh_kwargs(meshes.wheel, S.WHEEL_RGBA), **opts) for _ in range(4)]
        # kicker and dribbler (CAD only): fixed to the chassis, drawn with its transform and their CAD colours
        self.mechanisms = [gl.GLMeshItem(**_mesh_kwargs(m, S.CHASSIS_RGBA), **opts)
                           for m in meshes.mechanisms.values()]
        plate = S.id_plate_mesh(team, rid, meshes.z_top + S.PLATE_Z_OVER_TOP)
        self.plate = gl.GLMeshItem(vertexes=plate.vertices, faces=plate.faces, faceColors=plate.colors, **opts)
        ring = S.circle_points(0.0, 0.0, spec.radius + 0.012, 48, 0.004)
        self.ring = gl.GLLinePlotItem(pos=ring, color=S.SELECT_RGBA, width=2.0, antialias=True, mode="line_strip")
        self.ring.setVisible(False)
        self.items = [self.chassis, *self.wheels, *self.mechanisms, self.plate, self.ring]
        for it in self.items:
            view.addItem(it)
        self._visible = True

    def set_visible(self, on: bool) -> None:
        if on != self._visible:
            self._visible = on
            for it in self.items[:-1]:
                it.setVisible(on)
            if not on:
                self.ring.setVisible(False)

    def apply(self, chassis_T: np.ndarray, wheel_Ts: list[np.ndarray], body_T: np.ndarray, selected: bool) -> None:
        qc = _qmatrix(chassis_T)
        self.chassis.setTransform(qc)
        for it in self.mechanisms:
            it.setTransform(qc)
        for it, T in zip(self.wheels, wheel_Ts, strict=True):
            it.setTransform(_qmatrix(T))
        self.plate.setTransform(_qmatrix(body_T))
        self.ring.setTransform(_qmatrix(body_T))
        self.ring.setVisible(selected and self._visible)


class View3D(QtWidgets.QWidget):
    """Toolbar + ``GLViewWidget``; call :meth:`update_state` at the display rate."""

    preset_changed = Signal(str)

    def __init__(self, field: FieldGeometry | None = None, spec: RobotSpec | None = None,
                 wheel: WheelGeometry | None = None, cad: bool = True, hq: bool = False, parent=None):
        super().__init__(parent)
        self.field = field or FieldGeometry()
        self.spec = spec or RobotSpec()
        self.wheel = wheel or load_wheel_geometry()
        self.ball_radius = load_ball_spec().radius
        self.cad = bool(cad)
        self.hq = bool(hq)
        self.follow = False
        self.spin_wheels = True
        self.selected: tuple[str, int] | None = None
        self.frames = 0
        self.available = gl is not None
        self.error = GL_IMPORT_ERROR
        self._robots: dict[tuple[str, int], _RobotItems] = {}
        self._field_items: list = []
        self._meshes: S.RobotMeshes | None = None
        self._spin = S.WheelSpin(self.wheel)
        self._last_t: float | None = None
        self._last_ws: WorldState | None = None

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.toolbar = QtWidgets.QToolBar("3D")
        self.toolbar.setIconSize(QtCore.QSize(16, 16))
        lay.addWidget(self.toolbar)
        if not self.available:
            self.view = None
            self.label = QtWidgets.QLabel(f"3D view unavailable: {self.error}\n\npip install PyOpenGL   "
                                          "(extra dtssl[gui])")
            self.label.setAlignment(Qt.AlignCenter)
            self.label.setWordWrap(True)
            lay.addWidget(self.label, 1)
            self.toolbar.setEnabled(False)
            return
        self.view = gl.GLViewWidget()
        self.view.setBackgroundColor((22, 22, 26, 255))
        self.view.opts["fov"] = 45
        lay.addWidget(self.view, 1)
        self._shader = headlight_shader()           # CAD-style light (shared with the Robot tab), see glshading
        self._build_toolbar()
        self._build_static()
        self.set_preset("iso")

    # ------------------------------------------------------------------ construction
    def _build_toolbar(self) -> None:
        tb = self.toolbar
        self.preset_actions: dict[str, QtGui.QAction] = {}
        for name in S.CAMERA_PRESETS:
            a = tb.addAction(name)
            a.triggered.connect(lambda _=False, n=name: self.set_preset(n))
            self.preset_actions[name] = a
        tb.addSeparator()
        self.act_follow = tb.addAction("Follow")
        self.act_follow.setCheckable(True)
        self.act_follow.setToolTip("keep the camera centred on the selected robot")
        self.act_follow.toggled.connect(self.set_follow)
        self.act_cad = tb.addAction("CAD")
        self.act_cad.setCheckable(True)
        self.act_cad.setChecked(self.cad)
        self.act_cad.setToolTip("draw the RobôCIn v2025 CAD meshes (off = primitive shapes)")
        self.act_cad.toggled.connect(self.set_cad)
        self.act_hq = tb.addAction("HQ")
        self.act_hq.setCheckable(True)
        self.act_hq.setChecked(self.hq)
        self.act_hq.setToolTip("full-resolution CAD meshes (37k + 4x8k faces per robot) instead of the LOD pair")
        self.act_hq.toggled.connect(self.set_hq)
        self.act_wheels = tb.addAction("Wheels")
        self.act_wheels.setCheckable(True)
        self.act_wheels.setChecked(True)
        self.act_wheels.setToolTip("spin the wheels from the body velocity (inverse kinematics)")
        self.act_wheels.toggled.connect(self.set_spin_wheels)
        tb.addSeparator()
        a = tb.addAction("Fit (F)")
        a.triggered.connect(self.fit)
        self.info = QtWidgets.QLabel("")
        tb.addWidget(self.info)

    def _build_static(self) -> None:
        for it in self._field_items:
            self.view.removeItem(it)
        self._field_items = []
        outer, inner = S.floor_quads(self.field)
        apron = S.apron_quads(self.field, S.APRON_WIDTH)          # where the parked substitutes stand
        for corners, rgba in ((apron, S.APRON_RGBA), (outer, S.BOUNDARY_RGBA), (inner, S.FLOOR_RGBA)):
            q = S.quad_mesh(corners, rgba)
            it = gl.GLMeshItem(vertexes=q.vertices, faces=q.faces, faceColors=q.colors, smooth=False,
                               computeNormals=False, shader=None, glOptions="opaque")
            self.view.addItem(it)
            self._field_items.append(it)
        lines = gl.GLLinePlotItem(pos=S.field_segments(self.field), color=S.LINE_RGBA, width=1.5, antialias=True,
                                  mode="lines")
        goals = gl.GLLinePlotItem(pos=S.goal_frames(self.field), color=(0.9, 0.9, 0.9, 1.0), width=2.0,
                                  antialias=True, mode="lines")
        self.view.addItem(lines)
        self.view.addItem(goals)
        self._field_items += [lines, goals]
        md = gl.MeshData.sphere(rows=10, cols=16, radius=self.ball_radius)
        self.ball = gl.GLMeshItem(meshdata=md, smooth=True, color=S.BALL_RGBA, shader=self._shader,
                                  glOptions="opaque")
        self.view.addItem(self.ball)
        self._field_items.append(self.ball)
        self._meshes = None
        self._rebuild_robots()

    def _robot_meshes(self) -> S.RobotMeshes:
        if self._meshes is None:
            try:
                self._meshes = S.RobotMeshes.build(self.wheel, self.spec, cad=self.cad, lod=not self.hq)
            except Exception as e:  # noqa: BLE001 - e.g. LFS pointer instead of the OBJ
                log.warning("3D view: CAD meshes unavailable (%s); drawing primitives", e)
                self.cad = False
                self._meshes = S.RobotMeshes.build(self.wheel, self.spec, cad=False)
        return self._meshes

    def _rebuild_robots(self) -> None:
        for r in self._robots.values():
            for it in r.items:
                self.view.removeItem(it)
        self._robots.clear()
        self._spin.reset()
        if self._last_ws is not None:
            self.update_state(self._last_ws, self.selected, self._last_t, force=True)

    # ------------------------------------------------------------------ settings
    def set_field(self, field: FieldGeometry) -> None:
        self.field = field
        if self.view is not None:
            self._build_static()
            self.fit()

    def set_cad(self, on: bool) -> None:
        on = bool(on)
        if on == self.cad:
            return
        self.cad = on
        self._meshes = None
        if self.view is not None:
            self._rebuild_robots()

    def set_hq(self, on: bool) -> None:
        on = bool(on)
        if on == self.hq:
            return
        self.hq = on
        self._meshes = None
        if self.view is not None:
            self._rebuild_robots()

    def set_follow(self, on: bool) -> None:
        self.follow = bool(on)
        if self.act_follow.isChecked() != self.follow:
            self.act_follow.setChecked(self.follow)

    def set_spin_wheels(self, on: bool) -> None:
        self.spin_wheels = bool(on)

    def set_selected(self, key: tuple[str, int] | None) -> None:
        self.selected = key

    def set_ball_visible(self, on: bool) -> None:
        if self.view is not None:
            self.ball.setVisible(bool(on))

    # ------------------------------------------------------------------ camera
    def set_preset(self, name: str) -> None:
        if self.view is None:
            return
        el, az, dist = S.CAMERA_PRESETS[name]
        centre = self._follow_centre() if self.follow else QtGui.QVector3D(0.0, 0.0, 0.0)
        self.view.setCameraPosition(pos=centre, distance=dist, elevation=el, azimuth=az)
        self.preset_changed.emit(name)
        self.view.update()

    def fit(self) -> None:
        if self.view is None:
            return
        self.set_follow(False)
        el, az, dist = S.CAMERA_PRESETS["iso"]
        dist *= (self.field.length + 2 * self.field.boundary_width) / 9.6          # preset tuned for Div B
        self.view.setCameraPosition(pos=QtGui.QVector3D(0.0, 0.0, 0.0), distance=dist, elevation=el, azimuth=az)
        self.view.update()

    def camera(self) -> dict:
        o = self.view.opts if self.view is not None else {}
        return {k: o.get(k) for k in ("center", "distance", "elevation", "azimuth")}

    def _follow_centre(self) -> QtGui.QVector3D:
        ws = self._last_ws
        if ws is not None and self.selected in ws.robots and ws.robots[self.selected].present:
            r = ws.robots[self.selected]
            return QtGui.QVector3D(float(r.x), float(r.y), 0.05)
        return QtGui.QVector3D(0.0, 0.0, 0.0)

    # ------------------------------------------------------------------ per frame
    def update_state(self, ws: WorldState, selected: tuple[str, int] | None = None, t: float | None = None,
                     force: bool = False) -> None:
        """Move every item to ``ws``; skipped while the widget is hidden (inactive tab) unless ``force``."""
        self.selected = selected
        self._last_ws = ws
        tt = float(ws.t if t is None else t)
        dt = 0.0 if self._last_t is None else max(0.0, min(tt - self._last_t, 0.5))
        self._last_t = tt
        if self.view is None or (not force and not self.isVisible()):
            return
        meshes = self._robot_meshes()
        poses = {key: S.RobotPose(r.x, r.y, r.theta, r.vx_b, r.vy_b, r.w, r.present) for key, r in ws.robots.items()}
        # robots out of play are drawn too, parked outside the walls by the world (no ring, wheels still)
        fr = S.compute_frame(poses, (ws.ball.x, ws.ball.y, ws.ball.z), meshes, self.wheel,
                             self._spin if self.spin_wheels else None, dt)
        for key in poses:
            items = self._robots.get(key)
            if items is None:
                items = _RobotItems(self.view, key, meshes, self.spec, self._shader)
                self._robots[key] = items
            if key in fr.hidden:
                items.set_visible(False)
                continue
            items.set_visible(True)
            p = poses[key]
            items.apply(fr.chassis[key], fr.wheels[key], S.robot_transform(p.x, p.y, p.theta),
                        key == selected and p.present)
        for key, items in self._robots.items():
            if key not in poses:
                items.set_visible(False)
        bx, by, bz = fr.ball
        self.ball.setTransform(_qmatrix(S.translate(bx, by, bz + self.ball_radius)))
        if self.follow:
            self.view.opts["center"] = self._follow_centre()
        self.frames += 1
        self.view.update()

    # ------------------------------------------------------------------ misc
    def grab_image(self) -> QtGui.QImage | None:
        """Rendered frame (``None`` when there is no GL context, e.g. the offscreen platform)."""
        if self.view is None:
            return None
        img = self.view.grabFramebuffer()
        return None if img.isNull() else img

    def keyPressEvent(self, ev: QtGui.QKeyEvent) -> None:
        if ev.key() == Qt.Key_F:
            self.fit()
            ev.accept()
            return
        ev.ignore()

    def showEvent(self, ev) -> None:
        super().showEvent(ev)
        if self._last_ws is not None and self.view is not None:
            self.update_state(self._last_ws, self.selected, self._last_t, force=True)


__all__ = ["View3D", "GL_IMPORT_ERROR"]
