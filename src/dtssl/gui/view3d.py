"""3D view of the world for ``dtssl gui`` (``pyqtgraph.opengl``): field, ball and robots drawn with the
RobôCIn v2025 CAD meshes of ``dtssl.physics.assets`` (the same OBJ files as MuJoCo's ``visual="cad"``).

The view is built from :class:`~dtssl.sim.entities.WorldState` only, so it works with every backend
(``fopdt``, ``ideal``, ``mujoco-*``) and in Replay; geometry and transforms come from
:mod:`dtssl.gui.scene3d`. Mouse: left drag orbits, middle drag (or Shift) pans, wheel zooms
(``GLViewWidget`` defaults). Toolbar: camera presets (``iso``/``top``/``side``/``goal``), *Follow*
(camera centre tracks the selected robot), *Chase* (``3``: third-person camera behind the selected robot, as
in a video game; drag orbits around it, wheel zooms) and *FPV* (``1``: first-person camera on the robot's
cover above the dribbler; drag turns the head), both :class:`dtssl.gui.scene3d.RobotCamera`, *CAD* (meshes
vs the primitive shapes), *HQ* (full-resolution meshes instead of the light LOD pair: ~3x more triangles),
*Wheels* (spin the wheels from the body velocity through the inverse kinematics), *Fit* (``F``, back to the
free camera).

Each robot is two GL items (body + the four wheels as instances of one item, :mod:`dtssl.gui.glmesh`) plus
the selection ring: with 22 robots the Python cost per item in ``pyqtgraph`` is what caps the frame rate, not
the triangles. The meshes are smooth-shaded (:func:`dtssl.gui.scene3d.smooth_mesh`).

``pyqtgraph.opengl`` needs ``PyOpenGL`` (extra ``dtssl[gui]``) and a GL-capable Qt platform; when either
is missing the widget shows a label with the reason instead of failing (the 2D field view is unaffected).
"""
from __future__ import annotations

import logging

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, Signal

from dtssl.gui import scene3d as S
from dtssl.gui.glmesh import InstancedMeshItem, instancing_available, mesh_item
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


class _RobotItems:
    """GL items of one robot: the body (chassis + kicker + dribbler + id plate as one mesh, chassis frame,
    :func:`scene3d.body_mesh`), the four wheels (one :class:`InstancedMeshItem` when pyqtgraph allows it, else
    four items) and the selection ring. Few items per robot on purpose: see :mod:`dtssl.gui.glmesh`."""

    def __init__(self, view, key: tuple[str, int], meshes: S.RobotMeshes, spec: RobotSpec, shader="shaded"):
        team, rid = key
        self.key = key
        col = S.CHASSIS_RGBA if meshes.cad else S.PRIMITIVE_RGBA
        self.body = mesh_item(S.body_mesh(meshes, team, rid), col, shader)
        if instancing_available():
            self.wheel_item = mesh_item(meshes.wheel, S.WHEEL_RGBA, shader, cls=InstancedMeshItem)
            self.wheels = [self.wheel_item]
        else:
            self.wheel_item = None
            self.wheels = [mesh_item(meshes.wheel, S.WHEEL_RGBA, shader) for _ in range(4)]
        ring = S.circle_points(0.0, 0.0, spec.radius + 0.012, 48, 0.004)
        self.ring = gl.GLLinePlotItem(pos=ring, color=S.SELECT_RGBA, width=2.0, antialias=True, mode="line_strip")
        self.ring.setVisible(False)
        self.items = [self.body, *self.wheels, self.ring]
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
        self.body.setTransform(_qmatrix(chassis_T))
        if self.wheel_item is not None:
            self.wheel_item.set_instances([_qmatrix(T) for T in wheel_Ts])
        else:
            for it, T in zip(self.wheels, wheel_Ts, strict=True):
                it.setTransform(_qmatrix(T))
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
        self.camera_mode: str | None = None               # None (free orbit), "chase" or "fpv"
        self._camera: S.RobotCamera | None = None
        self._cam_applied: tuple[float, float, float] | None = None   # (azimuth, elevation, distance) last written
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
        self._orbit_fov = 45
        self.view.opts["fov"] = self._orbit_fov
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
        self.camera_group = QtGui.QActionGroup(self)
        self.camera_group.setExclusionPolicy(QtGui.QActionGroup.ExclusionPolicy.ExclusiveOptional)
        self.act_chase = tb.addAction("Chase")
        self.act_chase.setCheckable(True)
        self.act_chase.setToolTip("third-person camera behind the selected robot (3): drag to orbit around it, "
                                  "wheel to zoom; a preset or Fit leaves it")
        self.act_fpv = tb.addAction("FPV")
        self.act_fpv.setCheckable(True)
        self.act_fpv.setToolTip("first-person camera on the selected robot, above the dribbler (1): drag to look "
                                "around; a preset or Fit leaves it")
        for act, mode in ((self.act_chase, "chase"), (self.act_fpv, "fpv")):
            self.camera_group.addAction(act)
            act.toggled.connect(lambda on, m=mode: self._on_camera_action(m, on))
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
        if key != self.selected and self._camera is not None:
            self._camera.reset(keep_user=True)            # a new robot: take its heading at once
        self.selected = key

    def set_ball_visible(self, on: bool) -> None:
        if self.view is not None:
            self.ball.setVisible(bool(on))

    # ------------------------------------------------------------------ camera
    def set_preset(self, name: str) -> None:
        if self.view is None:
            return
        self.set_camera_mode(None)
        el, az, dist = S.CAMERA_PRESETS[name]
        centre = self._follow_centre() if self.follow else QtGui.QVector3D(0.0, 0.0, 0.0)
        self.view.setCameraPosition(pos=centre, distance=dist, elevation=el, azimuth=az)
        self.preset_changed.emit(name)
        self.view.update()

    def set_camera_mode(self, mode: str | None) -> None:
        """``"chase"`` / ``"fpv"``: ride the selected robot (:class:`scene3d.RobotCamera`); ``None``: the free
        orbit camera of the presets. The camera moves at once when a state is known."""
        if self.view is None or mode == self.camera_mode:
            return
        self.camera_mode = mode
        self._camera = S.RobotCamera(mode) if mode is not None else None
        self._cam_applied = None
        self.view.opts["fov"] = S.FPV_FOV if mode == "fpv" else self._orbit_fov
        for act, m in ((self.act_chase, "chase"), (self.act_fpv, "fpv")):
            if act.isChecked() != (mode == m):
                act.setChecked(mode == m)
        if mode is not None:
            self.preset_changed.emit(mode)
            if self._last_ws is not None:
                self.update_state(self._last_ws, self.selected, self._last_t, force=True)
        self.view.update()

    def _on_camera_action(self, mode: str, on: bool) -> None:
        if on:
            self.set_camera_mode(mode)
        elif self.camera_mode == mode:
            self.set_camera_mode(None)

    def _ride_robot(self, p: S.RobotPose, dt: float) -> None:
        """Chase / FPV: fold the mouse input since the last frame into the camera offsets, then put the camera
        on the robot for this frame."""
        o = self.view.opts
        if self._cam_applied is not None:
            az0, el0, d0 = self._cam_applied
            self._camera.nudge(o["azimuth"] - az0, o["elevation"] - el0,
                               None if o["distance"] == d0 else float(o["distance"]))
        cp = self._camera.update(p.x, p.y, p.theta, dt)
        o["center"] = QtGui.QVector3D(*cp.center)
        o["azimuth"], o["elevation"], o["distance"] = cp.azimuth, cp.elevation, cp.distance
        self._cam_applied = (cp.azimuth, cp.elevation, cp.distance)

    def fit(self) -> None:
        if self.view is None:
            return
        self.set_follow(False)
        self.set_camera_mode(None)
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
        self.set_selected(selected)
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
        if self._camera is not None and selected in poses and poses[selected].present:
            self._ride_robot(poses[selected], dt)
        elif self.follow:
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
        if ev.key() in (Qt.Key_1, Qt.Key_3):                    # toggle the first / third person camera
            mode = "fpv" if ev.key() == Qt.Key_1 else "chase"
            self.set_camera_mode(None if self.camera_mode == mode else mode)
            ev.accept()
            return
        ev.ignore()

    def showEvent(self, ev) -> None:
        super().showEvent(ev)
        if self._last_ws is not None and self.view is not None:
            self.update_state(self._last_ws, self.selected, self._last_t, force=True)


__all__ = ["View3D", "GL_IMPORT_ERROR"]
