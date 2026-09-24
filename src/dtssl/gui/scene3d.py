"""Geometry of the 3D view (no Qt/OpenGL here): meshes, transforms, wheel spin, field lines, camera presets.

Everything the :mod:`dtssl.gui.view3d` widget draws is prepared by this module from plain numpy so it
can be unit-tested without a GL context:

* :func:`parse_obj` reads the CAD meshes shipped in ``dtssl.physics.assets`` (the same OBJ files the
  MuJoCo ``visual="cad"`` mode uses, see ``tools/usd_to_mjcf_meshes.py``); :class:`RobotMeshes` also
  offers the primitive fallback (D-shaped prism + wheel cylinders) when the CAD is not wanted.
* :func:`robot_transform` / :func:`wheel_transform` give the 4x4 matrices of the chassis and of each
  wheel for a pose ``(x, y, theta)`` and the wheel spin angles; :class:`WheelSpin` integrates the spin
  from the body velocity through the inverse kinematics ``omega_i r = -sin(phi_i) vx + cos(phi_i) vy + R w``
  (cosmetic: the physics backends integrate their own wheel angles but the ``WorldState`` API does not
  expose them, so the 3D view rolls the wheels consistently with the body motion for every backend).
* :func:`field_segments` returns the field markings as line segments (metres, z = ``LINE_Z``),
  :func:`floor_quads` the floor rectangles (boundary frame + playing field, non-overlapping),
  :func:`id_plate_mesh` the SSL id plate (team disc + 4 dots) as a coloured mesh.
* :data:`CAMERA_PRESETS` are the (elevation, azimuth, distance) tuples of the toolbar presets.

Frames: world = ssl-vision (x to the right goal, y up, z up); robot body frame as in the MJCF (dribbler at
+x, wheels at ``phi = 60/135/225/300`` deg). The chassis OBJ has its z origin on the wheel-axle plane, so the
chassis sits at ``z = wheel.r`` above the floor (same convention as ``dtssl.physics.mjcf``).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from dtssl.physics.mjcf import (
    GREEN_RGBA,
    ID_DOT_POS,
    ID_PATTERN,
    PINK_RGBA,
    TEAM_RGBA,
    WheelGeometry,
    cad_meta,
    mesh_assets,
)
from dtssl.sim.world import FieldGeometry, RobotSpec

CAMERA_PRESETS: dict[str, tuple[float, float, float]] = {   # elevation (deg), azimuth (deg), distance (m)
    "iso": (42.0, -60.0, 12.5),
    "top": (90.0, -90.0, 10.5),
    "side": (12.0, -90.0, 10.0),
    "goal": (18.0, 180.0, 11.0),
}
LINE_Z = 0.003                     # field markings above the floor (avoids z-fighting at grazing angles)
PLATE_Z_OVER_TOP = 0.0015          # id plate thickness above the cover (m)
PLATE_RADIUS = 0.025
DOT_RADIUS = 0.02
CHASSIS_RGBA = (0.26, 0.26, 0.29, 1.0)
WHEEL_RGBA = (0.62, 0.62, 0.66, 1.0)
PRIMITIVE_RGBA = (0.24, 0.24, 0.27, 1.0)
FLOOR_RGBA = (0.13, 0.47, 0.20, 1.0)
BOUNDARY_RGBA = (0.10, 0.36, 0.16, 1.0)
LINE_RGBA = (0.96, 0.96, 0.96, 1.0)
BALL_RGBA = (1.0, 0.55, 0.0, 1.0)
SELECT_RGBA = (1.0, 1.0, 1.0, 0.9)


# --------------------------------------------------------------------------------------
# Meshes
# --------------------------------------------------------------------------------------
@dataclass
class Mesh:
    vertices: np.ndarray            # (n, 3) float
    faces: np.ndarray               # (m, 3) int
    colors: np.ndarray | None = None    # (m, 4) per-face RGBA or None

    @property
    def n_faces(self) -> int:
        return int(len(self.faces))

    def bbox(self) -> tuple[np.ndarray, np.ndarray]:
        return self.vertices.min(0), self.vertices.max(0)


def parse_obj(data: bytes | str) -> Mesh:
    """Minimal Wavefront OBJ reader (``v`` and triangular ``f`` lines; ``f a/b/c`` forms accepted)."""
    text = data.decode("utf-8") if isinstance(data, bytes) else data
    verts: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    for line in text.splitlines():
        if line.startswith("v "):
            p = line.split()
            verts.append((float(p[1]), float(p[2]), float(p[3])))
        elif line.startswith("f "):
            idx = [int(tok.split("/")[0]) for tok in line.split()[1:]]
            for j in range(1, len(idx) - 1):           # fan-triangulate polygons
                faces.append((idx[0] - 1, idx[j] - 1, idx[j + 1] - 1))
    return Mesh(np.asarray(verts, dtype=float).reshape(-1, 3), np.asarray(faces, dtype=np.int32).reshape(-1, 3))


def cad_meshes(lod: bool = False) -> tuple[Mesh, Mesh, dict]:
    """``(chassis, wheel, meta)`` from ``dtssl.physics.assets`` (chassis z origin on the wheel-axle plane,
    wheel centred on its axle with the axle along +x). ``lod=True`` picks the light pair exported for the
    GUI (``ssl_*_lod.obj``, ~5x fewer triangles) when the assets have it."""
    meta = cad_meta()
    assets = mesh_assets()
    ck, wk = ("chassis_lod", "wheel_lod") if lod and "chassis_lod" in meta else ("chassis", "wheel")
    return parse_obj(assets[meta[ck]["file"]]), parse_obj(assets[meta[wk]["file"]]), meta


def d_prism_mesh(radius: float, front: float, z0: float, z1: float, n_arc: int = 40) -> Mesh:
    """Primitive chassis: D-shaped prism (cylinder cut flat at x = ``front``), closed top and bottom."""
    alpha = math.acos(min(front / radius, 1.0))
    angs = np.linspace(alpha, 2 * math.pi - alpha, n_arc)
    ring = np.c_[radius * np.cos(angs), radius * np.sin(angs)]
    n = len(ring)
    bottom = np.c_[ring, np.full(n, z0)]
    top = np.c_[ring, np.full(n, z1)]
    verts = np.vstack([bottom, top, [[0.0, 0.0, z0]], [[0.0, 0.0, z1]]])
    cb, ct = 2 * n, 2 * n + 1
    faces = []
    for i in range(n):                                   # side quads (closing edge = the flat face)
        j = (i + 1) % n
        faces += [(i, j, n + j), (i, n + j, n + i)]
        faces += [(cb, j, i), (ct, n + i, n + j)]        # caps
    return Mesh(verts, np.asarray(faces, dtype=np.int32))


def cylinder_mesh(radius: float, half_width: float, n: int = 24) -> Mesh:
    """Primitive wheel: cylinder with its axis along +x, centred at the origin."""
    angs = np.linspace(0, 2 * math.pi, n, endpoint=False)
    ring = np.c_[radius * np.cos(angs), radius * np.sin(angs)]
    left = np.c_[np.full(n, -half_width), ring]
    right = np.c_[np.full(n, half_width), ring]
    verts = np.vstack([left, right, [[-half_width, 0, 0]], [[half_width, 0, 0]]])
    cl, cr = 2 * n, 2 * n + 1
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces += [(i, n + i, n + j), (i, n + j, j), (cl, j, i), (cr, n + i, n + j)]
    return Mesh(verts, np.asarray(faces, dtype=np.int32))


def disc_mesh(radius: float, z: float, cx: float = 0.0, cy: float = 0.0, n: int = 24, thickness: float = 0.0015):
    """Flat cylinder (a plate or a dot) with its top face at ``z + thickness``."""
    return _translate(cylinder_mesh_z(radius, thickness / 2.0, n), (cx, cy, z + thickness / 2.0))


def cylinder_mesh_z(radius: float, half_height: float, n: int = 24) -> Mesh:
    m = cylinder_mesh(radius, half_height, n)
    # rotate the x-axis cylinder onto z: (x, y, z) -> (y, z, x)
    v = m.vertices[:, [1, 2, 0]]
    return Mesh(v, m.faces)


def _translate(m: Mesh, d) -> Mesh:
    return Mesh(m.vertices + np.asarray(d, dtype=float), m.faces, m.colors)


def merge_meshes(parts: list[Mesh]) -> Mesh:
    verts, faces, cols, off = [], [], [], 0
    has_col = any(p.colors is not None for p in parts)
    for p in parts:
        verts.append(p.vertices)
        faces.append(p.faces + off)
        if has_col:
            cols.append(p.colors if p.colors is not None else np.tile((0.5, 0.5, 0.5, 1.0), (p.n_faces, 1)))
        off += len(p.vertices)
    return Mesh(np.vstack(verts), np.vstack(faces), np.vstack(cols) if has_col else None)


def id_plate_mesh(team: str, rid: int, z_top: float) -> Mesh:
    """SSL id plate on top of the robot: central team-colour disc + 4 pink/green dots (rulebook pattern
    ``ID_PATTERN``), as one mesh with per-face colours."""
    plate = disc_mesh(PLATE_RADIUS, z_top)
    plate.colors = np.tile(TEAM_RGBA.get(team, (0.6, 0.6, 0.6, 1.0)), (plate.n_faces, 1))
    parts = [plate]
    for (x, y), c in zip(ID_DOT_POS, ID_PATTERN[int(rid) % 16], strict=True):
        dot = disc_mesh(DOT_RADIUS, z_top, x, y)
        dot.colors = np.tile(PINK_RGBA if c == "p" else GREEN_RGBA, (dot.n_faces, 1))
        parts.append(dot)
    return merge_meshes(parts)


@dataclass
class RobotMeshes:
    """The meshes a robot is drawn with (shared by every robot of the scene)."""

    chassis: Mesh
    wheel: Mesh
    z_top: float                    # top of the cover above the floor (plate goes here)
    z_chassis: float                # z offset of the chassis mesh (0 for primitives, wheel.r for the CAD)
    cad: bool
    lod: bool = False

    @classmethod
    def build(cls, wheel: WheelGeometry, spec: RobotSpec, cad: bool = True, lod: bool = True) -> RobotMeshes:
        if cad:
            chassis, wh, meta = cad_meshes(lod=lod)
            # the plate sits on the full-resolution cover height (the LOD bbox differs by a few mm)
            return cls(chassis, wh, wheel.r + float(meta["chassis"]["z_top_above_axle"]), wheel.r, True,
                       lod and "chassis_lod" in meta)
        chassis = d_prism_mesh(spec.radius, spec.dribbler_offset, 0.008, spec.height)
        wh = cylinder_mesh(wheel.r * 0.92, wheel.hub_half_width)
        return cls(chassis, wh, spec.height, 0.0, False)


# --------------------------------------------------------------------------------------
# Transforms
# --------------------------------------------------------------------------------------
def rot_z(theta: float) -> np.ndarray:
    c, s = math.cos(theta), math.sin(theta)
    return np.array([[c, -s, 0.0, 0.0], [s, c, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]])


def rot_x(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[1.0, 0.0, 0.0, 0.0], [0.0, c, -s, 0.0], [0.0, s, c, 0.0], [0.0, 0.0, 0.0, 1.0]])


def translate(x: float, y: float, z: float) -> np.ndarray:
    t = np.eye(4)
    t[:3, 3] = (x, y, z)
    return t


def robot_transform(x: float, y: float, theta: float, z: float = 0.0) -> np.ndarray:
    """World-from-body 4x4 for a pose (the chassis mesh is offset by ``z`` = ``RobotMeshes.z_chassis``)."""
    return translate(x, y, 0.0) @ rot_z(theta) @ translate(0.0, 0.0, z)


def wheel_transform(x: float, y: float, theta: float, wheel: WheelGeometry, i: int, spin: float = 0.0) -> np.ndarray:
    """World 4x4 of wheel ``i``: at ``R (cos phi, sin phi)`` and height ``r`` in the body frame, mesh axle
    (+x) turned onto the outward radial direction ``u_r`` by ``rot_z(phi)``, then spun by ``spin`` about
    ``-u_r`` (the hinge axis of the MJCF, positive = CCW-tangent motion of the rim)."""
    phi = float(wheel.angles[i])
    p = translate(wheel.R * math.cos(phi), wheel.R * math.sin(phi), wheel.r)
    return translate(x, y, 0.0) @ rot_z(theta) @ p @ rot_z(phi) @ rot_x(-spin)


class WheelSpin:
    """Integrates the wheel spin angles of every robot from the body velocity (inverse kinematics)."""

    def __init__(self, wheel: WheelGeometry):
        self.wheel = wheel
        self._ik = self._ik_matrix(wheel)
        self.angles: dict[tuple[str, int], np.ndarray] = {}

    @staticmethod
    def _ik_matrix(wheel: WheelGeometry) -> np.ndarray:
        rows = [(-math.sin(p), math.cos(p), wheel.R) for p in wheel.angles]
        return np.asarray(rows, dtype=float) / wheel.r

    def wheel_speeds(self, vx: float, vy: float, w: float) -> np.ndarray:
        return self._ik @ np.array([vx, vy, w], dtype=float)

    def advance(self, key: tuple[str, int], vx: float, vy: float, w: float, dt: float) -> np.ndarray:
        a = self.angles.get(key)
        if a is None:
            a = np.zeros(len(self.wheel.angles))
        if dt > 0.0:
            a = (a + self.wheel_speeds(vx, vy, w) * dt) % (2.0 * math.pi)
        self.angles[key] = a
        return a

    def reset(self) -> None:
        self.angles.clear()


# --------------------------------------------------------------------------------------
# Field
# --------------------------------------------------------------------------------------
def floor_quads(f: FieldGeometry) -> tuple[np.ndarray, np.ndarray]:
    """Floor as non-overlapping rectangles at z = 0 (no coplanar overlap -> no z-fighting): the boundary
    area as a frame of 4 quads ``(16, 3)`` and the playing field ``(4, 3)``."""
    L, W, b = f.half_length, f.half_width, f.boundary_width
    Lb, Wb = L + b, W + b
    frame = np.array([
        [-Lb, -Wb, 0.0], [Lb, -Wb, 0.0], [Lb, -W, 0.0], [-Lb, -W, 0.0],       # bottom strip
        [-Lb, W, 0.0], [Lb, W, 0.0], [Lb, Wb, 0.0], [-Lb, Wb, 0.0],           # top strip
        [-Lb, -W, 0.0], [-L, -W, 0.0], [-L, W, 0.0], [-Lb, W, 0.0],           # left strip
        [L, -W, 0.0], [Lb, -W, 0.0], [Lb, W, 0.0], [L, W, 0.0],               # right strip
    ])
    inner = np.array([[-L, -W, 0.0], [L, -W, 0.0], [L, W, 0.0], [-L, W, 0.0]])
    return frame, inner


def quad_mesh(corners: np.ndarray, rgba) -> Mesh:
    """Mesh of one or more quads given as consecutive groups of 4 corners (CCW seen from above)."""
    c = np.asarray(corners, dtype=float).reshape(-1, 4, 3)
    faces = []
    for q in range(len(c)):
        o = 4 * q
        faces += [(o, o + 1, o + 2), (o, o + 2, o + 3)]
    m = Mesh(c.reshape(-1, 3), np.asarray(faces, dtype=np.int32))
    m.colors = np.tile(rgba, (len(faces), 1))
    return m


def circle_points(cx: float, cy: float, r: float, n: int = 48, z: float = 0.0) -> np.ndarray:
    a = np.linspace(0, 2 * math.pi, n + 1)
    return np.c_[cx + r * np.cos(a), cy + r * np.sin(a), np.full(n + 1, z)]


def field_segments(f: FieldGeometry, z: float = LINE_Z) -> np.ndarray:
    """Field markings as an ``(2k, 3)`` array of segment end points (``mode='lines'``): touch/goal lines,
    halfway line, centre circle, penalty areas, goals (as boxes behind the goal lines)."""
    L, W = f.half_length, f.half_width
    pd, pw = f.penalty_area_depth, f.penalty_area_width / 2.0
    gd, gw = f.goal_depth, f.goal_width / 2.0
    polys: list[np.ndarray] = [
        np.array([[-L, -W], [L, -W], [L, W], [-L, W], [-L, -W]]),
        np.array([[0.0, -W], [0.0, W]]),
        np.array([[-L, -pw], [-L + pd, -pw], [-L + pd, pw], [-L, pw]]),
        np.array([[L, -pw], [L - pd, -pw], [L - pd, pw], [L, pw]]),
        np.array([[-L, -gw], [-L - gd, -gw], [-L - gd, gw], [-L, gw]]),
        np.array([[L, -gw], [L + gd, -gw], [L + gd, gw], [L, gw]]),
        circle_points(0.0, 0.0, f.center_circle_radius)[:, :2],
    ]
    segs = []
    for poly in polys:
        p = np.c_[poly, np.full(len(poly), z)] if poly.shape[1] == 2 else poly
        for a, b in zip(p[:-1], p[1:], strict=True):
            segs += [a, b]
    return np.asarray(segs, dtype=float)


def goal_frames(f: FieldGeometry, height: float = 0.16) -> np.ndarray:
    """Goal posts and crossbars as vertical/horizontal segments (``mode='lines'``)."""
    L, gd, gw = f.half_length, f.goal_depth, f.goal_width / 2.0
    segs = []
    for sx in (-1.0, 1.0):
        x0, x1 = sx * L, sx * (L + gd)
        for y in (-gw, gw):
            segs += [[x0, y, 0.0], [x0, y, height], [x1, y, 0.0], [x1, y, height], [x0, y, height], [x1, y, height]]
        segs += [[x0, -gw, height], [x0, gw, height], [x1, -gw, height], [x1, gw, height]]
    return np.asarray(segs, dtype=float)


# --------------------------------------------------------------------------------------
# Single-robot view (Robot tab): arcball rotation of the part, wheel angles from wheel speeds
# --------------------------------------------------------------------------------------
ROBOT_VIEW_PRESETS: dict[str, tuple[float, float]] = {   # (elevation, azimuth) of the camera, degrees
    "iso": (24.0, -50.0),
    "frente": (8.0, 0.0),
    "lado": (8.0, 90.0),
    "topo": (89.0, -90.0),
    "baixo": (-89.0, -90.0),
}
ROBOT_VIEW_DISTANCE = 0.46          # camera distance (m) for a 0.18 m robot
AXIS_RGBA = {"x": (0.95, 0.30, 0.30, 1.0), "y": (0.35, 0.85, 0.35, 1.0), "z": (0.35, 0.55, 1.0, 1.0)}


def arcball_point(x: float, y: float, w: float, h: float) -> np.ndarray:
    """Widget pixel ``(x, y)`` (y down) -> unit vector on Shoemake's arcball sphere, in screen axes
    ``(right, up, toward the viewer)``; points outside the sphere are projected onto its rim."""
    s = min(w, h) / 2.0
    px = (x - w / 2.0) / s
    py = (h / 2.0 - y) / s
    r2 = px * px + py * py
    if r2 > 1.0:
        n = math.sqrt(r2)
        return np.array([px / n, py / n, 0.0])
    return np.array([px, py, math.sqrt(1.0 - r2)])


def axis_angle(axis, angle: float) -> np.ndarray:
    """4x4 rotation of ``angle`` rad about ``axis`` (Rodrigues); identity for a null axis."""
    a = np.asarray(axis, dtype=float)
    n = float(np.linalg.norm(a))
    T = np.eye(4)
    if n < 1e-12 or abs(angle) < 1e-12:
        return T
    a = a / n
    K = np.array([[0.0, -a[2], a[1]], [a[2], 0.0, -a[0]], [-a[1], a[0], 0.0]])
    T[:3, :3] = np.eye(3) + math.sin(angle) * K + (1.0 - math.cos(angle)) * (K @ K)
    return T


def rotation_between(v0, v1) -> np.ndarray:
    """4x4 rotation taking unit vector ``v0`` onto ``v1`` (the arcball step)."""
    v0 = np.asarray(v0, dtype=float)
    v1 = np.asarray(v1, dtype=float)
    axis = np.cross(v0, v1)
    dot = float(np.clip(np.dot(v0, v1), -1.0, 1.0))
    return axis_angle(axis, math.acos(dot))


class Arcball:
    """Free rotation of the part (CAD style): ``R`` is the world-from-part 4x4 the drawn items are
    premultiplied by, about ``centre``. :meth:`begin` on mouse press, :meth:`drag` on every move; the drag
    is mapped from screen axes to world axes with the camera's ``right/up/toward`` unit vectors so the part
    turns about the axis the mouse describes on the screen, whatever the camera orientation."""

    def __init__(self, centre=(0.0, 0.0, 0.0)):
        self.centre = np.asarray(centre, dtype=float)
        self.R = np.eye(4)
        self._p0: np.ndarray | None = None

    def reset(self) -> None:
        self.R = np.eye(4)
        self._p0 = None

    def begin(self, x: float, y: float, w: float, h: float) -> None:
        self._p0 = arcball_point(x, y, w, h)

    def end(self) -> None:
        self._p0 = None

    @property
    def dragging(self) -> bool:
        return self._p0 is not None

    def drag(self, x: float, y: float, w: float, h: float, right, up, toward) -> bool:
        """Apply the rotation between the pressed point and ``(x, y)``; returns False when not dragging."""
        if self._p0 is None:
            return False
        p1 = arcball_point(x, y, w, h)
        B = np.column_stack([np.asarray(right, float), np.asarray(up, float), np.asarray(toward, float)])
        v0, v1 = B @ self._p0, B @ p1
        self.R = rotation_between(v0, v1) @ self.R
        self._p0 = p1
        return True

    def spin(self, axis, angle: float) -> None:
        """Turn the part by ``angle`` about a world ``axis`` (auto-rotate / keyboard)."""
        self.R = axis_angle(axis, angle) @ self.R

    def transform(self) -> np.ndarray:
        """World-from-part 4x4 including the rotation centre."""
        c = self.centre
        return translate(*c) @ self.R @ translate(*(-c))


class WheelAngles:
    """Integrates the four wheel angles from the wheel speeds of the telemetry record (rad/s)."""

    def __init__(self, n: int = 4):
        self.angles = np.zeros(n)
        self._t: float | None = None

    def reset(self) -> None:
        self.angles[:] = 0.0
        self._t = None

    def advance(self, t: float, speeds) -> np.ndarray:
        if self._t is not None and speeds is not None and t > self._t:
            dt = min(t - self._t, 0.5)
            self.angles = (self.angles + np.asarray(speeds, dtype=float)[: len(self.angles)] * dt) % (2.0 * math.pi)
        if self._t is None or t >= self._t:
            self._t = t
        return self.angles


def robot_part_transforms(model_T: np.ndarray, meshes: RobotMeshes, wheel: WheelGeometry,
                          angles) -> tuple[np.ndarray, list[np.ndarray], np.ndarray]:
    """``(chassis_T, wheel_Ts, body_T)`` of one robot drawn at the origin of its body frame and turned by
    ``model_T`` (the :class:`Arcball` transform)."""
    body_T = model_T @ robot_transform(0.0, 0.0, 0.0)
    chassis_T = model_T @ robot_transform(0.0, 0.0, 0.0, meshes.z_chassis)
    wheel_Ts = [model_T @ wheel_transform(0.0, 0.0, 0.0, wheel, i, float(angles[i])) for i in range(len(wheel.angles))]
    return chassis_T, wheel_Ts, body_T


def arrow_segments(vx: float, vy: float, z: float, scale: float, head: float = 0.02) -> np.ndarray:
    """A planar arrow from the origin along ``(vx, vy) * scale`` at height ``z`` as ``mode='lines'``
    segments (shaft + two head strokes); empty array for a null vector."""
    ex, ey = vx * scale, vy * scale
    n = math.hypot(ex, ey)
    if n < 1e-4:
        return np.zeros((0, 3))
    a = math.atan2(ey, ex)
    segs = [[0.0, 0.0, z], [ex, ey, z]]
    for da in (math.pi * 0.8, -math.pi * 0.8):
        segs += [[ex, ey, z], [ex + head * math.cos(a + da), ey + head * math.sin(a + da), z]]
    return np.asarray(segs, dtype=float)


# --------------------------------------------------------------------------------------
# Scene bookkeeping (what the widget updates each frame)
# --------------------------------------------------------------------------------------
@dataclass
class RobotPose:
    x: float
    y: float
    theta: float
    vx: float = 0.0
    vy: float = 0.0
    w: float = 0.0
    present: bool = True


@dataclass
class SceneFrame:
    """Per-frame transforms of every drawn robot (computed by :func:`compute_frame`, applied by the widget)."""

    chassis: dict[tuple[str, int], np.ndarray] = field(default_factory=dict)
    wheels: dict[tuple[str, int], list[np.ndarray]] = field(default_factory=dict)
    hidden: set[tuple[str, int]] = field(default_factory=set)
    ball: tuple[float, float, float] = (0.0, 0.0, 0.0)


def compute_frame(poses: dict[tuple[str, int], RobotPose], ball_xyz: tuple[float, float, float],
                  meshes: RobotMeshes, wheel: WheelGeometry, spin: WheelSpin | None, dt: float) -> SceneFrame:
    fr = SceneFrame(ball=ball_xyz)
    for key, p in poses.items():
        if not p.present:
            fr.hidden.add(key)
            continue
        fr.chassis[key] = robot_transform(p.x, p.y, p.theta, meshes.z_chassis)
        angles = spin.advance(key, p.vx, p.vy, p.w, dt) if spin is not None else np.zeros(len(wheel.angles))
        fr.wheels[key] = [wheel_transform(p.x, p.y, p.theta, wheel, i, float(angles[i]))
                          for i in range(len(wheel.angles))]
    return fr


__all__ = [
    "Mesh", "parse_obj", "cad_meshes", "d_prism_mesh", "cylinder_mesh", "disc_mesh", "merge_meshes",
    "id_plate_mesh", "RobotMeshes", "rot_z", "rot_x", "translate", "robot_transform", "wheel_transform",
    "WheelSpin", "floor_quads", "quad_mesh", "circle_points", "field_segments", "goal_frames", "RobotPose",
    "SceneFrame", "compute_frame", "CAMERA_PRESETS", "CHASSIS_RGBA", "WHEEL_RGBA", "PRIMITIVE_RGBA",
    "FLOOR_RGBA", "BOUNDARY_RGBA", "LINE_RGBA", "BALL_RGBA", "SELECT_RGBA", "PLATE_Z_OVER_TOP", "LINE_Z",
    "ROBOT_VIEW_PRESETS", "ROBOT_VIEW_DISTANCE", "AXIS_RGBA", "arcball_point", "axis_angle", "rotation_between",
    "Arcball", "WheelAngles", "robot_part_transforms", "arrow_segments",
]
