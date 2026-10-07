"""Programmatic MJCF (MuJoCo XML) builder for the dtssl physics backends (SPEC §4.6).

Everything is generated from the shared config (``config/field_divB.json``,
``config/robot_limits.json``, ``config/robot_geometry.json``) with ``xml.etree``; no
hand-written XML is needed and no MuJoCo import happens here (the strings can be
inspected/written without the ``mujoco`` package; ``describe_xml`` only uses it when
available).

Two robot routes share the same field and ball:

* route **a** (``mujoco-velocity``): chassis on a ``slide x + slide y + hinge z`` joint stack
  driven by three ``velocity`` actuators. The target velocity is set by the world every
  step from the behavioral plant (``AnalyticFOPDTPlant``); MuJoCo only imposes contacts.
* route **b** (``mujoco-rollers``): free-floating chassis + 4 omni wheels (hinge about the
  radial axis) each carrying ``n_rollers`` free-hinge rollers (Wan et al. 2026 recipe:
  Newton solver, elliptic cone, ``impratio=10``, ``noslip_iterations=1``,
  timestep ~2 ms). Wheel actuators: ``velocity`` (default) or ``motor`` (PI in Python).

Conventions (SPEC §3): SI units, world frame = ssl-vision frame, body x forward (dribbler),
wheel angles ``phi = (60, 135, 225, 300)`` deg CCW from body +x, positive wheel speed =
CCW tangent so that ``omega_i * r = -sin(phi_i) vx + cos(phi_i) vy + R w``.

Visuals (``visual=``): ``"primitive"`` (default) draws the D-shaped collision shell, the hubs and
the roller geoms themselves; ``"cad"`` adds the RobôCIn v2025 CAD meshes of ``assets/`` (chassis, wheel, kicker
and dribbler, tessellated with their Inventor colours out of the assembly ``robot_v2025_v3.iam`` by
``tools/inventor_export_cad.m`` and registered in ``meshes.json`` by ``tools/register_cad_meshes.py``) as
visual-only geoms (``contype = conaffinity = 0``, ``mass = 0``), one geom per colour (MuJoCo meshes carry a single
``rgba``, so every OBJ is split in memory into its ``usemtl`` groups, see ``cad_submeshes``), and moves the
primitives to geom group 3 (hidden in the viewer by default). The physics is identical in both modes (same bodies,
joints, collision geoms, inertias and actuators): the meshes only change what is drawn. Models with CAD meshes must
be compiled with the mesh bytes attached (``load_model``) or from a directory holding the files (``dtssl mjcf
--out`` writes them next to the XML).

Dribbler (``dribbler=``): ``"spring"`` (default) keeps the historical behaviour, a weak spring-damper applied by
``MuJoCoWorld`` to a ball inside the dribbler zone (no extra geometry); ``"bar"`` builds the physical mechanism of
the CAD (:class:`DribblerOptions`, :func:`dribbler_fragment`): the rubber bar as a capsule on a hinge driven by a
velocity actuator, mounted on a sprung slide (the module dampers) inside a mouth whose walls, chip plate and bar
are the only robot geoms the ball collides with. The ball is then held the way a real dribbler holds it: the bar
spins it backwards (positive hinge rate about body y drags the top of the ball towards the robot), the back-spin
makes the floor friction pull the ball into the mouth and the bar presses it on the floor; nothing but friction
holds it, so it is lost when the robot brakes, reverses or spins harder than the friction allows (``mu_slide``
of the identified ball, SPEC §3). The chassis D-shell keeps colliding with robots and walls, so the rest of the
model is untouched; ``"bar"`` adds 2 bodies, 2 joints, 5 geoms and 1 actuator per robot.
"""
from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np

from dtssl.paths import config_path
from dtssl.sim.entities import Scene, Team
from dtssl.sim.world import FieldGeometry, RobotSpec

# --------------------------------------------------------------------------------------
# Routes, contact bitmasks and colours
# --------------------------------------------------------------------------------------
ROUTE_ALIASES = {
    "a": "a", "velocity": "a", "mujoco-velocity": "a",
    "b": "b", "rollers": "b", "mujoco-rollers": "b",
}

# contype/conaffinity bits: a pair collides iff (contype1 & conaffinity2) or (contype2 & conaffinity1)
BIT_FLOOR, BIT_BALL, BIT_ROBOT, BIT_WALL, BIT_ROLLER, BIT_MOUTH = 1, 2, 4, 8, 16, 32
FLOOR_CONTYPE, FLOOR_CONAFF = BIT_FLOOR, BIT_FLOOR | BIT_BALL | BIT_ROLLER
BALL_CONTYPE, BALL_CONAFF = BIT_BALL, BIT_FLOOR | BIT_ROBOT | BIT_WALL
ROBOT_CONTYPE, ROBOT_CONAFF = BIT_ROBOT, BIT_BALL | BIT_ROBOT | BIT_WALL   # chassis never touches the floor
WALL_CONTYPE, WALL_CONAFF = BIT_WALL, BIT_BALL | BIT_ROBOT
ROLLER_CONTYPE, ROLLER_CONAFF = BIT_ROLLER, BIT_FLOOR                      # rollers only touch the floor
# dribbler="bar": the ball meets the robot through the mouth geoms (rear shell, cheeks, chip plate, bar), which
# touch nothing else; the D-shell then collides with robots and walls only
MOUTH_CONTYPE, MOUTH_CONAFF = BIT_MOUTH, 0
BALL_CONAFF_MOUTH = BIT_FLOOR | BIT_WALL | BIT_MOUTH
ROBOT_CONAFF_MOUTH = BIT_ROBOT | BIT_WALL

TEAM_RGBA = {"blue": (0.10, 0.35, 0.95, 1.0), "yellow": (0.95, 0.85, 0.10, 1.0)}
PINK_RGBA = (1.0, 0.25, 0.75, 1.0)
GREEN_RGBA = (0.20, 0.95, 0.35, 1.0)
# SSL standard ID pattern (rulebook table): dot colours in the order
# (front-left, front-right, back-right, back-left); 'p' = pink, 'g' = green. Cosmetic only.
ID_PATTERN = [
    "ppgp", "gpgp", "gggp", "pggp", "pppg", "gppg", "ggpg", "pgpg",
    "gggg", "pppp", "ppgg", "ggpp", "pggg", "pgpp", "gpgg", "gppp",
]
ID_DOT_POS = ((0.035, 0.054772), (0.035, -0.054772), (-0.054772, -0.035), (-0.054772, 0.035))

# --------------------------------------------------------------------------------------
# Visual modes and CAD mesh assets (src/dtssl/physics/assets, see tools/inventor_export_cad.m)
# --------------------------------------------------------------------------------------
VISUAL_MODES = ("primitive", "cad")
DRIBBLER_MODES = ("spring", "bar")
ASSET_DIR = Path(__file__).resolve().parent / "assets"
CAD_KEYS = ("chassis", "wheel", "kicker", "dribbler")            # meshes.json entries (+ "_lod" twins)
CAD_FILES = tuple(f"ssl_{k}{s}.obj" for k in CAD_KEYS for s in ("", "_lod")) + \
    tuple(f"ssl_{k}.mtl" for k in CAD_KEYS) + ("meshes.json",)
CAD_MESH_PREFIX = "ssl_cad_"                                     # <mesh name="ssl_cad_<key>_<label>">
CAD_BAR_PART = "Dribblerschnecke"                                # dribbler part drawn on the spinning bar body
CAD_BAR_LABEL = "bar"
HIDDEN_GROUP = "3"        # geom group not drawn by the viewer by default (groups 0-2 are)


def normalize_visual(visual: str | None) -> str:
    v = (visual or "primitive").lower()
    if v not in VISUAL_MODES:
        raise ValueError(f"unknown visual mode {visual!r}; expected one of {VISUAL_MODES}")
    return v


def normalize_dribbler(dribbler: str | None) -> str:
    d = (dribbler or "spring").lower()
    if d not in DRIBBLER_MODES:
        raise ValueError(f"unknown dribbler mode {dribbler!r}; expected one of {DRIBBLER_MODES}")
    return d


@lru_cache(maxsize=1)
def cad_meta() -> dict:
    """``assets/meshes.json``: provenance + derived constants of the CAD meshes (cover and id-plate heights
    above the wheel axle, wheel outer radius, materials, face counts, md5, dribbler/kicker features)."""
    return json.loads((ASSET_DIR / "meshes.json").read_text(encoding="utf-8"))


def cad_plate_z(meta: dict | None = None) -> float:
    """Height above the wheel axle (m) where the SSL id plate sits on the CAD chassis: the decal plane of the
    pattern in the CAD (``z_id_plate_above_axle``), else the cover top (``z_cover_above_axle``), else the bbox top."""
    c = (meta or cad_meta())["chassis"]
    return float(c.get("z_id_plate_above_axle", c.get("z_cover_above_axle", c["z_top_above_axle"])))


@lru_cache(maxsize=1)
def mesh_assets() -> dict[str, bytes]:
    """``{file name: bytes}`` of the CAD mesh files on disk (OBJ + MTL). The OBJ files are tracked with git LFS:
    a checkout without LFS holds pointer files, which is reported here instead of failing in an OBJ parser."""
    out = {}
    for f in CAD_FILES:
        if not f.endswith((".obj", ".mtl")):
            continue
        p = ASSET_DIR / f
        if not p.is_file():
            continue
        data = p.read_bytes()
        if data.startswith(b"version https://git-lfs"):
            raise RuntimeError(f"{p} is a git LFS pointer, not the mesh: run `git lfs pull` "
                               "(or regenerate with tools/inventor_export_cad.m)")
        out[f] = data
    return out


@dataclass(frozen=True)
class ObjData:
    """A parsed exporter OBJ: vertices ``(n, 3)``, triangles ``(m, 3)``, ``groups`` = ``(part name, material,
    face start, face end)`` in file order and ``materials`` = ``{name: (r, g, b)}`` from the MTL."""

    vertices: np.ndarray
    faces: np.ndarray
    groups: tuple[tuple[str, str, int, int], ...]
    materials: dict[str, tuple[float, float, float]]


def read_mtl(data: bytes | str) -> dict[str, tuple[float, float, float]]:
    text = data.decode("utf-8") if isinstance(data, bytes) else data
    out, cur = {}, None
    for line in text.splitlines():
        if line.startswith("newmtl "):
            cur = line[7:].strip()
            out[cur] = (0.5, 0.5, 0.5)
        elif cur and line.startswith("Kd "):
            r, g, b = (float(v) for v in line.split()[1:4])
            out[cur] = (r, g, b)
    return out


def read_obj(data: bytes | str, materials: dict[str, tuple[float, float, float]] | None = None) -> ObjData:
    """Minimal Wavefront OBJ reader (``v``, triangular/polygonal ``f`` with ``a/b/c`` forms, ``g``, ``usemtl``)."""
    text = data.decode("utf-8") if isinstance(data, bytes) else data
    verts: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    groups: list[tuple[str, str, int, int]] = []
    name, mtl, start = "", "", 0
    for line in text.splitlines():
        if line.startswith("v "):
            p = line.split()
            verts.append((float(p[1]), float(p[2]), float(p[3])))
        elif line.startswith("f "):
            idx = [int(tok.split("/")[0]) for tok in line.split()[1:]]
            for j in range(1, len(idx) - 1):           # fan-triangulate polygons
                faces.append((idx[0] - 1, idx[j] - 1, idx[j + 1] - 1))
        elif line.startswith("g "):
            if len(faces) > start:
                groups.append((name, mtl, start, len(faces)))
            name, start = line[2:].strip(), len(faces)
        elif line.startswith("usemtl "):
            if len(faces) > start:                     # colour change inside a group
                groups.append((name, mtl, start, len(faces)))
                start = len(faces)
            mtl = line[7:].strip()
    if len(faces) > start:
        groups.append((name, mtl, start, len(faces)))
    return ObjData(np.asarray(verts, dtype=float).reshape(-1, 3), np.asarray(faces, dtype=np.int32).reshape(-1, 3),
                   tuple(groups), dict(materials or {}))


@dataclass(frozen=True)
class SubMesh:
    """One single-colour piece of a CAD mesh, as MuJoCo takes it: ``file`` (virtual asset name), ``mesh`` (asset
    name in the XML), ``key`` (meshes.json entry), ``label`` (material name or ``bar``), ``rgba``, OBJ ``data``."""

    file: str
    mesh: str
    key: str
    label: str
    rgba: tuple[float, float, float, float]
    faces: int
    data: bytes


def _obj_bytes(verts: np.ndarray, faces: np.ndarray) -> bytes:
    used, inv = np.unique(faces, return_inverse=True)
    v = verts[used]
    f = inv.reshape(-1, 3) + 1
    lines = [f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in v] + [f"f {a} {b} {c}" for a, b, c in f]
    return ("\n".join(lines) + "\n").encode("utf-8")


def split_obj(obj: ObjData, key: str, bar_part: str | None = None) -> list[SubMesh]:
    """Split a parsed CAD mesh into one sub-mesh per material (plus the ``bar`` part on its own when
    ``bar_part`` names it): what the MJCF draws as one ``<geom type="mesh">`` per colour."""
    by_mtl: dict[str, list[np.ndarray]] = {}
    bar: list[np.ndarray] = []
    bar_mtl = ""
    for name, mtl, a, b in obj.groups:
        if bar_part and bar_part in name:
            bar.append(obj.faces[a:b])
            bar_mtl = mtl
        else:
            by_mtl.setdefault(mtl, []).append(obj.faces[a:b])
    out = []
    for mtl, chunks in by_mtl.items():
        faces = np.vstack(chunks)
        rgb = obj.materials.get(mtl, (0.5, 0.5, 0.5))
        label = mtl or "default"
        out.append(SubMesh(f"ssl_{key}__{label}.obj", f"{CAD_MESH_PREFIX}{key}_{label}", key, label,
                           (rgb[0], rgb[1], rgb[2], 1.0), int(len(faces)), _obj_bytes(obj.vertices, faces)))
    if bar:
        faces = np.vstack(bar)
        rgb = obj.materials.get(bar_mtl, (0.5, 0.5, 0.5))
        out.append(SubMesh(f"ssl_{key}__{CAD_BAR_LABEL}.obj", f"{CAD_MESH_PREFIX}{key}_{CAD_BAR_LABEL}", key,
                           CAD_BAR_LABEL, (rgb[0], rgb[1], rgb[2], 1.0), int(len(faces)), _obj_bytes(obj.vertices, faces)))
    return out


def cad_obj(key: str, lod: bool = False) -> ObjData:
    """Parsed CAD mesh ``key`` (``chassis``/``wheel``/``kicker``/``dribbler``), LOD twin when asked and present."""
    meta = cad_meta()
    assets = mesh_assets()
    k = f"{key}_lod" if lod and f"{key}_lod" in meta else key
    entry = meta[k]
    mtl = read_mtl(assets[entry["mtl"]]) if entry.get("mtl") in assets else {}
    return read_obj(assets[entry["file"]], mtl)


@lru_cache(maxsize=1)
def cad_submeshes() -> dict[str, tuple[SubMesh, ...]]:
    """``{key: sub-meshes}`` of the full-resolution CAD meshes present in ``meshes.json`` (one per colour; the
    dribbler bar part apart, so that it can sit on the spinning bar body)."""
    meta = cad_meta()
    return {key: tuple(split_obj(cad_obj(key), key, CAD_BAR_PART if key == "dribbler" else None))
            for key in CAD_KEYS if key in meta}


def cad_mesh_files() -> dict[str, bytes]:
    """``{virtual file: bytes}`` of every sub-mesh the MJCF can reference (what ``load_model`` attaches)."""
    return {sm.file: sm.data for subs in cad_submeshes().values() for sm in subs}


def uses_cad(xml: str) -> bool:
    return f'name="{CAD_MESH_PREFIX}' in xml


def load_model(xml: str):
    """``mujoco.MjModel`` from an XML string, attaching the CAD sub-meshes when it references them."""
    import mujoco  # noqa: WPS433 (optional dependency)

    if uses_cad(xml):
        return mujoco.MjModel.from_xml_string(xml, cad_mesh_files())
    return mujoco.MjModel.from_xml_string(xml)


def normalize_route(route: str) -> str:
    try:
        return ROUTE_ALIASES[str(route).lower()]
    except KeyError as e:
        raise ValueError(f"unknown route {route!r}; use 'a' (mujoco-velocity) or 'b' (mujoco-rollers)") from e


def robot_name(team: Team, rid: int) -> str:
    return f"{team}_{int(rid)}"


# --------------------------------------------------------------------------------------
# Parameter containers (defaults = config files / SPEC §3)
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class WheelGeometry:
    """Omni-wheel geometry (config/robot_geometry.json ``physical`` + SPEC §3)."""

    R: float = 0.079601                      # centre -> wheel/floor contact point (m)
    r: float = 0.029492                      # wheel outer radius, roller surface (m)
    angles_deg: tuple[float, ...] = (60.0, 135.0, 225.0, 300.0)
    n_rollers: int = 12
    roller_radius: float = 0.006             # roller radius at its middle = r - rim_radius
    roller_half_length: float = 0.004        # capsule rollers only (half length of the axis segment)
    roller_shape: str = "ellipsoid"          # "ellipsoid" (barrel, envelope ~ circle) | "capsule"
    wheel_mass: float = 0.15
    roller_mass: float = 0.002
    hub_half_width: float = 0.009            # visual hub half thickness along the axle

    @property
    def angles(self) -> np.ndarray:
        return np.radians(np.asarray(self.angles_deg, dtype=float))

    @property
    def rim_radius(self) -> float:
        """Radius of the circle on which the roller *axes* lie."""
        return self.r - self.roller_radius

    @property
    def roller_semi_axis(self) -> float:
        """Ellipsoid rollers: semi-axis ``a`` along the roller axis such that the barrel profile
        matches the wheel circle at half the chord to the neighbouring roller, i.e. the ideal
        roller profile ``q(s) = sqrt(r^2 - s^2) - rho`` (surface of revolution of the wheel arc)."""
        rho, r, b = self.rim_radius, self.r, self.roller_radius
        s_half = rho * math.sin(math.pi / max(int(self.n_rollers), 3))       # half chord to neighbour
        q = math.sqrt(max(r * r - s_half * s_half, 0.0)) - rho              # ideal profile radius there
        ratio = min(max(q / b, 0.05), 0.999)
        return s_half / math.sqrt(1.0 - ratio * ratio)

    @classmethod
    def from_robot_geometry(cls, geom, **overrides) -> WheelGeometry:
        """From a ``dtssl.geometry.RobotGeometry`` (R_contact_m, wheel_radius_m, wheel_angles_deg)."""
        kw = dict(R=float(geom.R_contact_m), r=float(geom.wheel_radius_m),
                  angles_deg=tuple(float(a) for a in geom.wheel_angles_deg))
        kw.update(overrides)
        return cls(**kw)

    def to_robot_geometry(self):
        """``dtssl.geometry.RobotGeometry`` with this wheel layout (lazy import; None if absent)."""
        try:
            from dtssl.geometry import RobotGeometry
        except ImportError:  # pragma: no cover
            return None
        return RobotGeometry(R_contact_m=self.R, wheel_radius_m=self.r, wheel_angles_deg=self.angles_deg,
                             provenance="dtssl.physics.mjcf.WheelGeometry")


@dataclass(frozen=True)
class BallSpec:
    """Ball (config/robot_limits.json ``ball``). Friction coefficients are derived from the
    ssl-unification two-phase deceleration model so that MuJoCo reproduces it:
    ``mu_slide = sliding_decel / g`` and ``mu_roll = rolling_decel * 1.4 * radius / g``
    (rolling sphere: a = mu_roll * g / (1.4 r))."""

    radius: float = 0.0215
    mass: float = 0.046
    sliding_decel: float = 1.82135
    rolling_decel: float = 0.3025
    torsional_friction: float = 0.005
    solref: tuple[float, float] = (0.01, 0.6)     # soft floor contact (some bounce for chips)
    solimp: tuple[float, float, float] = (0.9, 0.95, 0.001)

    @property
    def mu_slide(self) -> float:
        return self.sliding_decel / 9.81

    @property
    def mu_roll(self) -> float:
        return self.rolling_decel * 1.4 * self.radius / 9.81


@dataclass(frozen=True)
class SolverOptions:
    """``<option>`` block. Same recipe for both routes (Wan et al. 2026 for the rollers);
    ``timestep`` is a nominal value: MuJoCoWorld sets ``dt / n_sub`` exactly at every step."""

    timestep: float = 1.0 / 480.0            # 8 substeps per 1/60 s (~0.002 s recipe)
    integrator: str = "Euler"                # explicit actuator force -> forcerange clamps are exact
    solver: str = "Newton"
    cone: str = "elliptic"
    impratio: float = 10.0
    noslip_iterations: int = 1
    iterations: int = 100
    gravity: tuple[float, float, float] = (0.0, 0.0, -9.81)


@dataclass(frozen=True)
class RouteAOptions:
    """Route a servo. The ``velocity`` actuator applies ``kv * (ctrl - qvel)``; with the explicit
    Euler integrator and ``kv = m / h`` (slides) / ``I_z / h`` (hinge), where ``h`` is the physics
    substep, the servo is *dead-beat*: ``qvel`` equals the target after one substep, so the
    chassis reproduces the plant's trapezoidal pose integration exactly (measured max error
    over 3 s: < 0.1 mm / < 1e-4 rad, tests). ``kv_slide``/``kv_hinge`` = None selects these
    dead-beat gains (MuJoCoWorld rescales them when ``dt`` changes the substep).

    ``force_max`` / ``torque_max`` are written as MJCF ``forcerange`` and bound the push against
    walls/robots. They must stay above the plant's peak demand ``m K u / tau`` (~113 N for a
    3 m/s step, ~1.2 N m for a 10 rad/s step) or the transient lags the plant. Do NOT combine
    forcerange with the implicit integrators: MuJoCo applies the actuator velocity derivative
    even while the force is saturated, which over-damps those substeps (measured: 60 N clamp ->
    6 mm error, 20 N m on the hinge -> the heading diverges)."""

    kv_slide: float | None = None            # N s/m (None = m / h, dead-beat)
    kv_hinge: float | None = None            # N m s/rad (None = I_z / h, dead-beat)
    force_max: float | None = 150.0          # N per slide (None = unbounded)
    torque_max: float | None = 3.0           # N m on the hinge (None = unbounded)

    def gains(self, spec: RobotSpec, timestep: float) -> tuple[float, float]:
        """``(kv_slide, kv_hinge)`` for a chassis of ``spec`` at physics substep ``timestep``."""
        kv_s = spec.mass / timestep if self.kv_slide is None else float(self.kv_slide)
        kv_h = chassis_inertia(spec)[2] / timestep if self.kv_hinge is None else float(self.kv_hinge)
        return kv_s, kv_h


def chassis_inertia(spec: RobotSpec) -> tuple[float, float, float]:
    """Diagonal inertia (kg m^2) of a uniform cylinder r = radius, H = height, mass m, about its
    centre: ``Ixx = Iyy = m (3 r^2 + H^2) / 12``, ``Izz = m r^2 / 2``. Used as the explicit
    ``<inertial>`` of the chassis so the CoM sits on the joint axis (no slide/hinge coupling)."""
    m, r, H = spec.mass, spec.radius, spec.height
    return (m * (3 * r * r + H * H) / 12.0, m * (3 * r * r + H * H) / 12.0, 0.5 * m * r * r)


@dataclass(frozen=True)
class RouteBOptions:
    """Route b actuation. ``wheel_control``: 'velocity' (MuJoCo velocity servo per wheel, gain
    ``kv_wheel`` in N m s/rad — a DC drive with a speed loop behaves like this; kv_wheel = 0.1
    gives 1.5 N m at a 15 rad/s error, i.e. a ~0.5 m/s step) or 'pi' (``motor`` actuator +
    Python PI in firmware units, torque clamped to ``wheel_torque_max``). The wheel hinge carries
    the reflected rotor inertia as ``armature`` (``N^2 J_rotor``), which also keeps the explicit
    Euler servo stable when a wheel spins freely (``h kv / I_wheel < 2``). Motor
    data (Maxon EC-45 flat
    50 W: 0.084 N m nominal, ~523 rad/s no-load at 24 V) and the unknown gear ratio are kept
    as parameters for a future motor-level model."""

    wheel_control: str = "velocity"
    kv_wheel: float = 0.1                    # N m s/rad at the wheel (~ I_wheel_total / h: dead-beat when free)
    wheel_torque_max: float | None = 1.5     # N m at the wheel (forcerange / ctrlrange)
    gear_ratio: float = 4.0                  # unknown on the real robot -> parameter
    motor_nominal_torque: float = 0.084      # Maxon EC-45 flat 50 W (N m, motor side)
    motor_no_load_speed: float = 523.0       # rad/s at 24 V (motor side)
    motor_rotor_inertia: float = 9.25e-6     # kg m^2 (EC-45 flat 50 W datasheet: 92.5 g cm^2)
    roller_friction: float = 1.0
    roller_damping: float = 1e-6
    roller_armature: float = 1e-7
    wheel_damping: float = 1e-4

    @property
    def wheel_armature(self) -> float:
        """Rotor inertia reflected to the wheel through the gearbox: ``N^2 J_rotor``."""
        return self.gear_ratio ** 2 * self.motor_rotor_inertia

    @property
    def pi_torque_max(self) -> float:
        return 1.5 if self.wheel_torque_max is None else float(self.wheel_torque_max)


@dataclass(frozen=True)
class MouthGeometry:
    """Where the ball can go in front of the chassis when ``dribbler="bar"`` (metres, body frame with the z
    origin on the wheel-axle plane, i.e. the frame of the CAD meshes; ``robot_fragment`` adds ``wheel.r``).
    Defaults = ``meshes.json: dribbler.features`` of the RobôCIn v2025 CAD (``MouthGeometry.from_cad``):

    * ``y_min``/``y_max``: inner faces of the side plates and chip holders (mouth width 56.5 mm);
    * ``x_back``: rear of the chip plate (the ball never gets behind it); ``x_front``: front edge of the side
      plates (the cheeks reach it, 5 mm ahead of the D-face);
    * ``plate_centre``/``plate_axes``/``plate_half``: oriented box fitted to the chip plate vertices, the ramp the
      ball rests on (its front face leans back 16 deg from vertical);
    * ``n_arc``: vertices per arc of the rear/cheek prisms (the D-shell outline is reused)."""

    y_min: float = -0.02775
    y_max: float = 0.02875
    x_back: float = 0.05913
    x_front: float = 0.0799
    plate_centre: tuple[float, float, float] = (0.067575, 0.0, -0.017293)
    plate_axes: tuple[tuple[float, float, float], ...] = ((0.0, 1.0, 0.0), (0.279271, 0.0, -0.960212),
                                                          (-0.960212, 0.0, -0.279271))
    plate_half: tuple[float, float, float] = (0.03625, 0.011808, 0.007334)
    n_arc: int = 24

    @classmethod
    def from_cad(cls, meta: dict | None = None) -> MouthGeometry:
        try:
            feats = (meta or cad_meta())["dribbler"]["features"]
            m, obb = feats["mouth"], feats["chip_plate"]["obb"]
        except (KeyError, FileNotFoundError, OSError):
            return cls()
        return cls(y_min=float(m["y_min"]), y_max=float(m["y_max"]), x_back=float(m["x_back"]),
                   x_front=float(m.get("x_front", cls.x_front)), plate_centre=tuple(float(v) for v in obb["centre"]),
                   plate_axes=tuple(tuple(float(v) for v in ax) for ax in obb["axes"]),
                   plate_half=tuple(float(v) for v in obb["half"]))

    def plate_front(self) -> tuple[np.ndarray, np.ndarray]:
        """``(point, outward unit normal)`` of the plate face the ball rests on (the face whose normal has the
        largest +x component), mesh frame."""
        c, axes, half = np.asarray(self.plate_centre), np.asarray(self.plate_axes), np.asarray(self.plate_half)
        best = None
        for i in range(3):
            for sgn in (1.0, -1.0):
                n = sgn * axes[i]
                if best is None or n[0] > best[1][0]:
                    best = (c + half[i] * n, n)
        return best

    def resting_ball(self, ball_radius: float, floor_z: float) -> np.ndarray:
        """Centre (mesh frame) of a ball of ``ball_radius`` lying on the floor (``floor_z`` = floor height in the
        mesh frame, ``-wheel.r``) and touching the plate front face, in the robot's symmetry plane ``y = 0``."""
        p0, n = self.plate_front()
        zc = floor_z + ball_radius
        xc = p0[0] + (ball_radius - (zc - p0[2]) * n[2]) / n[0]
        return np.array([xc, 0.0, zc])


@dataclass(frozen=True)
class DribblerOptions:
    """Physical dribbler (``dribbler="bar"``). Geometry from the CAD (``meshes.json: dribbler.features``,
    ``DribblerOptions.from_cad``): the rubber bar (``Dribblerschnecke``, radius 6.47 mm, 72 mm long) has its axis
    along body y at ``bar_centre`` (72.9 mm ahead of the centre, 13.75 mm above the wheel axle = 43.2 mm above the
    floor). The CAD pose leaves ``~3 mm`` between the bar and a ball resting on the chip plate (a bar fixed there
    would never touch a ball on the floor), so the bar is carried by a sprung **slide** along the bar-to-ball
    direction (the module dampers ``AmortecedorCad`` of the CAD) whose forward stop sits ``engage`` beyond the
    contact position: the module rests at that stop with the spring relaxed, a ball resting on the plate pushes it
    back by ``engage`` and is pressed with ``stiffness * engage`` (0.3 N by default), and the bar follows a ball up
    to ``engage`` ahead of the plate; ``engage = None`` leaves the bar at the CAD pose. The pre-load is
    deliberately light: the bar sits 45 deg behind and above the ball, so its normal force pushes the ball forward
    and only the friction of the spinning bar and of the back-spinning ball on the floor (the identified
    ``mu_slide``) pull it back. With the defaults a held ball floats ~6 mm ahead of the plate, pressed with
    ~0.25 N, and stays in the mouth through ramped manoeuvres (captures up to ~0.8 m/s, braking/reversing up to
    ~1 m/s^2 after a 0.8 m/s capture and ~3 m/s^2 after a 0.5 m/s one, 1.5 rad/s turns, 0.3 m/s side steps);
    harder braking or a 2 m/s pass bounce it out, as on the real robots. The bar spins on a hinge driven by
    a ``velocity`` actuator (speed loop of the BLDC drive): ``ctrl`` = bar speed in rad/s, clamped to
    ``speed_max_rpm`` (``None`` = ``RobotSpec.dribbler_rpm_max``, config/robot_limits.json: 6000 rpm; the CAD gear
    train 18:26:18 is 1:1, ``gear_ratio``) and the torque to ``torque_max``. The bar-ball contact has priority 2,
    so its own friction (rubber on the ball) and softness apply; the ball-floor and ball-plate contacts keep the
    ball's identified parameters.

    The real bar is a screw (``Dribblerschnecke``: two opposite helices meeting at the centre), whose surface
    velocity has an axial component that drags an off-centre ball back to the middle; a cylinder cannot do that
    in MuJoCo, so the world applies that centring action as a lateral force ``-helix * N * clip(y / helix_width)``
    on the ball while the bar touches it (``N`` = bar normal force, ``y`` = ball offset in the robot frame).

    Placeholders, not datasheet values (the dribbler motor and damper data is not in the repo sources):
    ``engage``, ``travel_back``, ``stiffness``, ``damping``, ``module_mass``, ``bar_mass``, ``armature``,
    ``torque_max``, ``friction``, ``mouth_*``, ``helix``, ``helix_width``."""

    bar_radius: float = 0.00647
    bar_half_length: float = 0.036
    bar_centre: tuple[float, float, float] = (0.0729, -0.00025, 0.01375)   # mesh frame (z above the axle)
    engage: float | None = 0.008           # m, stop travel beyond the resting-ball contact (None = CAD pose)
    travel_back: float = 0.006             # m, slide range behind the CAD pose
    stiffness: float = 37.5                # N/m of the sprung module (0.3 N on a ball resting on the plate)
    damping: float = 2.0                   # N s/m (slightly overdamped with module_mass: no rebound on impacts)
    module_mass: float = 0.02              # kg carried by the slide (taken out of the chassis inertial mass)
    bar_mass: float = 0.003                # kg of the bar body
    armature: float = 1.5e-6               # kg m^2 reflected rotor + bar inertia on the hinge
    bar_damping: float = 1e-6              # N m s/rad
    gear_ratio: float = 1.0                # motor turns per bar turn (CAD: 18:26:18 -> 1)
    speed_max_rpm: float | None = None     # bar rpm; None = RobotSpec.dribbler_rpm_max
    torque_max: float = 0.02               # N m at the bar
    kv: float | None = None                # N m s/rad; None = (armature + I_bar) / (2 h)
    friction: tuple[float, float, float] = (1.0, 0.005, 0.0001)        # rubber bar on the ball
    solref: tuple[float, float] = (0.02, 2.0)                            # compliant, overdamped rubber contact
    solimp: tuple[float, float, float] = (0.9, 0.95, 0.001)
    mouth: MouthGeometry = field(default_factory=MouthGeometry)
    mouth_friction: tuple[float, float, float] = (0.2, 0.005, 0.0001)   # plate / cheeks on the ball
    mouth_solref: tuple[float, float] = (0.01, 1.0)                      # critically damped (inelastic) plate
    mouth_solimp: tuple[float, float, float] = (0.95, 0.99, 0.001)
    helix: float = 0.3                     # centring force of the helical bar / bar normal force (0 = plain bar)
    helix_width: float = 0.005             # m, lateral offset at which the centring force saturates

    @classmethod
    def from_cad(cls, meta: dict | None = None, **overrides) -> DribblerOptions:
        """Bar geometry and mouth from ``meshes.json`` (defaults when the features are missing)."""
        kw: dict = {}
        try:
            bar = (meta or cad_meta())["dribbler"]["features"]["dribbler_bar"]
            kw = dict(bar_radius=float(bar["radius"]), bar_half_length=float(bar["length"]) / 2.0,
                      bar_centre=tuple(float(v) for v in bar["centre"]))
        except (KeyError, FileNotFoundError, OSError):
            pass
        kw["mouth"] = MouthGeometry.from_cad(meta)
        kw.update(overrides)
        return cls(**kw)

    @property
    def bar_inertia(self) -> float:
        """Hinge inertia of the bar (uniform cylinder, ``m r^2 / 2``) plus the reflected rotor (``armature``)."""
        return self.armature + 0.5 * self.bar_mass * self.bar_radius ** 2

    def speed_max(self, spec: RobotSpec) -> float:
        rpm = spec.dribbler_rpm_max if self.speed_max_rpm is None else self.speed_max_rpm
        return float(rpm) * 2.0 * math.pi / 60.0

    def gain(self, timestep: float) -> float:
        """Velocity-servo gain: half the dead-beat value ``I / h`` (explicit Euler stays stable for any load)."""
        return self.bar_inertia / (2.0 * timestep) if self.kv is None else float(self.kv)

    def engagement(self, ball_radius: float, wheel_r: float) -> tuple[np.ndarray, float]:
        """``(unit slide axis, gap)``: direction from the bar axis to the centre of a ball resting on the chip
        plate (mesh frame, in the x-z plane) and the free distance between the two surfaces along it."""
        ball = self.mouth.resting_ball(ball_radius, -wheel_r)
        d = ball - np.asarray(self.bar_centre)
        d[1] = 0.0
        dist = float(np.linalg.norm(d))
        return d / dist, dist - ball_radius - self.bar_radius


# --------------------------------------------------------------------------------------
# Config loaders (tolerant: missing keys keep the dataclass defaults)
# --------------------------------------------------------------------------------------
def _read_json(path: Path | str | None, default_name: str) -> dict:
    p = Path(path) if path is not None else config_path(default_name)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_field_geometry(path: Path | str | None = None) -> FieldGeometry:
    """``config/field_divB.json`` (mm, keys ``field_length``/``field_width``) -> FieldGeometry (m).
    Uses ``dtssl.config.load_field`` when available (cached), else reads the JSON directly."""
    try:
        from dtssl.config import load_field

        return load_field(path)
    except ImportError:  # pragma: no cover - dtssl.config absent
        pass
    d = _read_json(path, "field_divB.json")
    mm = {k[6:] if k.startswith("field_") else k: v for k, v in d.items() if not k.startswith("_")}
    return FieldGeometry.from_mm(mm)


def load_robot_spec(path: Path | str | None = None) -> RobotSpec:
    """``config/robot_limits.json: robot`` -> RobotSpec (``dtssl.config.load_limits`` when available)."""
    try:
        from dtssl.config import load_limits

        return load_limits(path)[0]
    except ImportError:  # pragma: no cover
        pass
    d = _read_json(path, "robot_limits.json").get("robot", {})
    keys = RobotSpec.__dataclass_fields__
    return RobotSpec(**{k: (None if v is None else float(v)) for k, v in d.items() if k in keys})


def load_ball_spec(path: Path | str | None = None) -> BallSpec:
    """``config/robot_limits.json: ball`` -> BallSpec (radius, mass, two-phase decelerations)."""
    try:
        from dtssl.config import load_limits

        d = load_limits(path)[1]
    except ImportError:  # pragma: no cover
        d = _read_json(path, "robot_limits.json").get("ball", {})
    keys = {"radius", "mass", "sliding_decel", "rolling_decel"}
    return BallSpec(**{k: float(v) for k, v in d.items() if k in keys})


def load_wheel_geometry(path: Path | str | None = None, **overrides) -> WheelGeometry:
    """``config/robot_geometry.json: physical`` -> WheelGeometry (``dtssl.config.load_geometry`` first)."""
    try:
        from dtssl.config import load_geometry

        return WheelGeometry.from_robot_geometry(load_geometry(path), **overrides)
    except ImportError:  # pragma: no cover
        pass
    d = _read_json(path, "robot_geometry.json").get("physical", {})
    kw = {}
    if "R_contact_m" in d:
        kw["R"] = float(d["R_contact_m"])
    if "wheel_radius_m" in d:
        kw["r"] = float(d["wheel_radius_m"])
    if "wheel_angles_deg" in d:
        kw["angles_deg"] = tuple(float(a) for a in d["wheel_angles_deg"])
    kw.update(overrides)
    return WheelGeometry(**kw)


def load_deadzone(path: Path | str | None = None) -> tuple[bool, float]:
    """``(enabled, wheel_min_speed_rad_s)`` from ``config/robot_limits.json: deadzone``."""
    try:
        from dtssl.config import load_limits

        d = load_limits(path)[2]
    except ImportError:  # pragma: no cover
        d = _read_json(path, "robot_limits.json").get("deadzone", {})
    return bool(d.get("enabled", False)), float(d.get("wheel_min_speed_rad_s", 1.567))


# --------------------------------------------------------------------------------------
# Inverse kinematics (body -> wheels). Prefer dtssl.kinematics when it exists.
# --------------------------------------------------------------------------------------
def _local_ik_matrix(wheel: WheelGeometry) -> np.ndarray:
    phi = wheel.angles
    return np.column_stack([-np.sin(phi), np.cos(phi), np.full_like(phi, wheel.R)]) / wheel.r


def ik_matrix(wheel: WheelGeometry | None = None) -> np.ndarray:
    """4x3 matrix M with ``omega_wheels = M @ [vx, vy, w]`` (rad/s; positive = CCW tangent).

    Taken from ``dtssl.kinematics.body_to_wheel_matrix`` (lazy import) when it exists and agrees
    with the local convention (probe: pure rotation ``w = 1`` gives ``R / r`` on every wheel);
    otherwise the local rows ``[-sin phi_i, cos phi_i, R] / r``."""
    wheel = wheel or WheelGeometry()
    local = _local_ik_matrix(wheel)
    try:
        from dtssl import kinematics as _kin

        geom = wheel.to_robot_geometry()
        K = np.asarray(_kin.body_to_wheel_matrix(geom), dtype=float)
        if K.shape == local.shape and np.allclose(K, local, rtol=1e-6, atol=1e-9):
            return K
    except Exception:  # pragma: no cover - ImportError / signature mismatch -> local
        pass
    return local


def body_to_wheels(vx: float, vy: float, w: float, wheel: WheelGeometry | None = None) -> np.ndarray:
    """Wheel angular speeds (rad/s, positive = CCW tangent) for a body command."""
    return ik_matrix(wheel) @ np.array([vx, vy, w], dtype=float)


# --------------------------------------------------------------------------------------
# XML helpers
# --------------------------------------------------------------------------------------
def _f(x: float) -> str:
    return f"{float(x):.6g}"


def _v(*xs: float) -> str:
    return " ".join(_f(x) for x in xs)


def _el(tag: str, **attrs) -> ET.Element:
    e = ET.Element(tag)
    for k, v in attrs.items():
        if v is None:
            continue
        e.set(k.rstrip("_"), v if isinstance(v, str) else _v(*v) if isinstance(v, (tuple, list)) else _f(v)
              if isinstance(v, float) else str(v))
    return e


def _sub(parent: ET.Element, tag: str, **attrs) -> ET.Element:
    e = _el(tag, **attrs)
    parent.append(e)
    return e


def yaw_quat(theta: float) -> tuple[float, float, float, float]:
    return (math.cos(theta / 2.0), 0.0, 0.0, math.sin(theta / 2.0))


@dataclass
class MjcfFragment:
    """Pieces of a model that must land in different top-level MJCF sections."""

    worldbody: list[ET.Element] = field(default_factory=list)
    actuator: list[ET.Element] = field(default_factory=list)
    sensor: list[ET.Element] = field(default_factory=list)
    asset: list[ET.Element] = field(default_factory=list)
    default: list[ET.Element] = field(default_factory=list)
    contact: list[ET.Element] = field(default_factory=list)

    def extend(self, other: MjcfFragment) -> MjcfFragment:
        for sec in ("worldbody", "actuator", "sensor", "asset", "default", "contact"):
            mine: list[ET.Element] = getattr(self, sec)
            if sec in ("asset", "default"):  # dedupe shared assets/classes by name
                names = {e.get("name") or e.get("class") for e in mine}
                for e in getattr(other, sec):
                    key = e.get("name") or e.get("class")
                    if key not in names:
                        mine.append(e)
                        names.add(key)
            else:
                mine.extend(getattr(other, sec))
        return self


def compose(fragments: Iterable[MjcfFragment], model_name: str = "dtssl",
            solver: SolverOptions | None = None) -> ET.Element:
    """Assemble fragments into a full ``<mujoco>`` element."""
    solver = solver or SolverOptions()
    root = _el("mujoco", model=model_name)
    _sub(root, "compiler", angle="radian", inertiafromgeom="auto", autolimits="true")
    _sub(root, "option", timestep=solver.timestep, integrator=solver.integrator, solver=solver.solver,
         cone=solver.cone, impratio=solver.impratio, noslip_iterations=str(solver.noslip_iterations),
         iterations=str(solver.iterations), gravity=solver.gravity)
    vis = _sub(root, "visual")
    _sub(vis, "headlight", ambient=(0.4, 0.4, 0.4), diffuse=(0.6, 0.6, 0.6), specular=(0.1, 0.1, 0.1))
    _sub(vis, "map", znear="0.01", zfar="60")
    _sub(vis, "quality", shadowsize="4096")
    asset = _sub(root, "asset")
    _sub(asset, "texture", type="skybox", builtin="gradient", rgb1=(0.55, 0.7, 0.9), rgb2=(0.2, 0.3, 0.45),
         width="256", height="256")
    default = _sub(root, "default")
    _sub(default, "geom", solref=(0.01, 1.0))
    worldbody = _sub(root, "worldbody")
    _sub(worldbody, "light", name="sun", directional="true", pos=(0, 0, 6), dir=(0, 0, -1),
         diffuse=(0.8, 0.8, 0.8), castshadow="true")
    actuator = _sub(root, "actuator")
    sensor = _sub(root, "sensor")
    contact = _sub(root, "contact")
    merged = MjcfFragment()
    for fr in fragments:
        merged.extend(fr)
    asset.extend(merged.asset)
    default.extend(merged.default)
    worldbody.extend(merged.worldbody)
    actuator.extend(merged.actuator)
    sensor.extend(merged.sensor)
    contact.extend(merged.contact)
    for sec in (actuator, sensor, contact):
        if len(sec) == 0:
            root.remove(sec)
    return root


def to_xml_string(root: ET.Element) -> str:
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode")


# --------------------------------------------------------------------------------------
# Field
# --------------------------------------------------------------------------------------
def field_fragment(fld: FieldGeometry, boundary: bool = True, wall_height: float = 0.12,
                   wall_thickness: float = 0.02, floor_friction: float = 0.9) -> MjcfFragment:
    fr = MjcfFragment()
    fr.asset.append(_el("material", name="mat_floor", rgba=(0.05, 0.45, 0.12, 1.0), reflectance="0.05"))
    fr.asset.append(_el("material", name="mat_wall", rgba=(0.15, 0.15, 0.15, 1.0)))
    fr.asset.append(_el("material", name="mat_goal", rgba=(0.85, 0.85, 0.85, 1.0)))
    d_line = _el("default", class_="field_line")
    _sub(d_line, "geom", type="box", contype="0", conaffinity="0", group="1", rgba=(1, 1, 1, 1))
    fr.default.append(d_line)
    d_wall = _el("default", class_="wall")
    _sub(d_wall, "geom", type="box", contype=str(WALL_CONTYPE), conaffinity=str(WALL_CONAFF), condim="3",
         friction=(0.5, 0.005, 0.0001), material="mat_wall", solref=(0.004, 1.0), solimp=(0.95, 0.99, 0.001))
    fr.default.append(d_wall)

    hl, hw = fld.half_length, fld.half_width
    lt = fld.line_thickness
    zl = 0.0005  # lines sit on the floor as 1 mm thick boxes (visual only)

    # floor: infinite plane, condim 3, mu 0.9 (rollers/ball/robots use their own friction via priority)
    fr.worldbody.append(_el("geom", name="floor", type="plane", pos=(0, 0, 0), size=(hl + 1.0, hw + 1.0, 0.05),
                            material="mat_floor", contype=str(FLOOR_CONTYPE), conaffinity=str(FLOOR_CONAFF),
                            condim="3", friction=(floor_friction, 0.005, 0.0001)))
    # lines: outer rectangle, halfway line, centre circle (polygon), penalty areas, goal lines
    lines = _el("body", name="field_lines", pos=(0, 0, 0))

    def hline(name, x0, x1, y):
        _sub(lines, "geom", name=name, class_="field_line", pos=((x0 + x1) / 2, y, zl),
             size=(abs(x1 - x0) / 2 + lt / 2, lt / 2, zl))

    def vline(name, x, y0, y1):
        _sub(lines, "geom", name=name, class_="field_line", pos=(x, (y0 + y1) / 2, zl),
             size=(lt / 2, abs(y1 - y0) / 2 + lt / 2, zl))

    hline("line_top", -hl, hl, hw)
    hline("line_bottom", -hl, hl, -hw)
    vline("line_left", -hl, -hw, hw)
    vline("line_right", hl, -hw, hw)
    vline("line_half", 0.0, -hw, hw)
    pw, pd = fld.penalty_area_width / 2, fld.penalty_area_depth
    for sgn, tag in ((-1, "left"), (1, "right")):
        vline(f"pen_{tag}_front", sgn * (hl - pd), -pw, pw)
        hline(f"pen_{tag}_top", sgn * hl, sgn * (hl - pd), pw)
        hline(f"pen_{tag}_bottom", sgn * hl, sgn * (hl - pd), -pw)
    n_seg = 36
    rc = fld.center_circle_radius
    for i in range(n_seg):
        a0, a1 = 2 * math.pi * i / n_seg, 2 * math.pi * (i + 1) / n_seg
        am = (a0 + a1) / 2
        seg = 2 * rc * math.sin((a1 - a0) / 2)
        _sub(lines, "geom", name=f"circle_{i}", class_="field_line",
             pos=(rc * math.cos(am), rc * math.sin(am), zl), size=(lt / 2, seg / 2 + lt / 2, zl),
             axisangle=(0, 0, 1, am))
    fr.worldbody.append(lines)
    # centre mark + penalty marks (visual sites)
    fr.worldbody.append(_el("site", name="centre_mark", pos=(0, 0, zl), size=0.01, rgba=(1, 1, 1, 1), group="1"))

    # goals: back + two posts/sides, outside the goal line, depth goal_depth, collide with ball & robots
    gw, gd = fld.goal_width / 2, fld.goal_depth
    for sgn, tag in ((-1, "left"), (1, "right")):
        g = _el("body", name=f"goal_{tag}", pos=(sgn * (hl + gd / 2), 0, 0))
        _sub(g, "geom", name=f"goal_{tag}_back", class_="wall", material="mat_goal",
             pos=(sgn * (gd / 2 - wall_thickness / 2), 0, wall_height / 2),
             size=(wall_thickness / 2, gw + wall_thickness, wall_height / 2))
        for ys, ytag in ((1, "top"), (-1, "bottom")):
            _sub(g, "geom", name=f"goal_{tag}_{ytag}", class_="wall", material="mat_goal",
                 pos=(0, ys * (gw + wall_thickness / 2), wall_height / 2),
                 size=(gd / 2, wall_thickness / 2, wall_height / 2))
        fr.worldbody.append(g)

    if boundary:
        bx, by = hl + fld.boundary_width, hw + fld.boundary_width
        b = _el("body", name="boundary", pos=(0, 0, 0))
        _sub(b, "geom", name="wall_xpos", class_="wall", pos=(bx + wall_thickness / 2, 0, wall_height / 2),
             size=(wall_thickness / 2, by + wall_thickness, wall_height / 2))
        _sub(b, "geom", name="wall_xneg", class_="wall", pos=(-bx - wall_thickness / 2, 0, wall_height / 2),
             size=(wall_thickness / 2, by + wall_thickness, wall_height / 2))
        _sub(b, "geom", name="wall_ypos", class_="wall", pos=(0, by + wall_thickness / 2, wall_height / 2),
             size=(bx + wall_thickness, wall_thickness / 2, wall_height / 2))
        _sub(b, "geom", name="wall_yneg", class_="wall", pos=(0, -by - wall_thickness / 2, wall_height / 2),
             size=(bx + wall_thickness, wall_thickness / 2, wall_height / 2))
        fr.worldbody.append(b)
    return fr


# --------------------------------------------------------------------------------------
# Ball
# --------------------------------------------------------------------------------------
BALL_BODY = "ball"
BALL_JOINT = "ball_root"


def ball_fragment(ball: BallSpec | None = None, pos: Sequence[float] = (0.0, 0.0), mouth: bool = False) -> MjcfFragment:
    """The ball. ``mouth=True`` (``dribbler="bar"`` worlds) makes it collide with the robots' mouth geoms instead
    of their D-shells (see the contact bits)."""
    ball = ball or BallSpec()
    fr = MjcfFragment()
    fr.asset.append(_el("material", name="mat_ball", rgba=(1.0, 0.45, 0.05, 1.0), specular="0.6", shininess="0.6"))
    b = _el("body", name=BALL_BODY, pos=(pos[0], pos[1], ball.radius))
    _sub(b, "freejoint", name=BALL_JOINT)
    _sub(b, "geom", name="ball_geom", type="sphere", size=ball.radius, mass=ball.mass, material="mat_ball",
         contype=str(BALL_CONTYPE), conaffinity=str(BALL_CONAFF_MOUTH if mouth else BALL_CONAFF), condim="6",
         priority="1", friction=(ball.mu_slide, ball.torsional_friction, ball.mu_roll),
         solref=ball.solref, solimp=ball.solimp)
    fr.worldbody.append(b)
    return fr


# --------------------------------------------------------------------------------------
# Robot
# --------------------------------------------------------------------------------------
CHASSIS_MESH = "chassis_shell"


def _chassis_mesh_vertices(radius: float, front: float, z0: float, z1: float, n_arc: int = 32) -> str:
    """Vertices of a D-shaped prism: cylinder of ``radius`` cut flat at x = ``front`` (dribbler face)."""
    alpha = math.acos(min(front / radius, 1.0))
    angs = np.linspace(alpha, 2 * math.pi - alpha, n_arc)
    pts = []
    for z in (z0, z1):
        for a in angs:
            pts.append((radius * math.cos(a), radius * math.sin(a), z))
    return " ".join(_v(*p) for p in pts)


def _clip(poly: list[tuple[float, float]], a: float, b: float, c: float) -> list[tuple[float, float]]:
    """Sutherland-Hodgman: keep the part of ``poly`` with ``a x + b y <= c``."""
    out: list[tuple[float, float]] = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        fp, fq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
        if fp <= 0:
            out.append(p)
        if (fp < 0 < fq) or (fq < 0 < fp):
            t = fp / (fp - fq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def _prism_vertices(radius: float, z0: float, z1: float, halfplanes: Sequence[tuple[float, float, float]],
                    n_arc: int = 48) -> str:
    """Vertices of a convex prism: the disc of ``radius`` clipped by ``halfplanes`` (``a x + b y <= c``), extruded
    from ``z0`` to ``z1``. MuJoCo takes the convex hull, so only the outline vertices are listed."""
    angs = np.linspace(0.0, 2 * math.pi, n_arc, endpoint=False)
    poly = [(radius * math.cos(a), radius * math.sin(a)) for a in angs]
    for a, b, c in halfplanes:
        poly = _clip(poly, a, b, c)
    if len(poly) < 3:
        raise ValueError("prism outline is empty")
    return " ".join(_v(x, y, z) for z in (z0, z1) for x, y in poly)


def _quat_from_axes(axes: Sequence[Sequence[float]]) -> tuple[float, float, float, float]:
    """MuJoCo quaternion ``(w, x, y, z)`` of the rotation whose columns are the given unit axes (rows input)."""
    R = np.asarray(axes, dtype=float).T
    tr = float(np.trace(R))
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2.0
        w, x, y, z = 0.25 * s, (R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2.0
        w, x, y, z = (R[2, 1] - R[1, 2]) / s, 0.25 * s, (R[0, 1] + R[1, 0]) / s, (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2.0
        w, x, y, z = (R[0, 2] - R[2, 0]) / s, (R[0, 1] + R[1, 0]) / s, 0.25 * s, (R[1, 2] + R[2, 1]) / s
    else:
        s = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2.0
        w, x, y, z = (R[1, 0] - R[0, 1]) / s, (R[0, 2] + R[2, 0]) / s, (R[1, 2] + R[2, 1]) / s, 0.25 * s
    return (w, x, y, z)


def _robot_visuals(body: ET.Element, name: str, team: Team, rid: int, spec: RobotSpec, z_top: float,
                   cad: bool = False) -> None:
    """Top plate (team colour) + SSL id pattern dots + front marker (all visual only). With the CAD
    meshes the plate sits on the CAD cover and the front marker is hidden (the mesh has the dribbler)."""
    col = TEAM_RGBA.get(team, (0.6, 0.6, 0.6, 1.0))
    _sub(body, "geom", name=f"{name}_top", type="cylinder", pos=(0, 0, z_top + 0.0015), size=(0.025, 0.0015),
         rgba=col, contype="0", conaffinity="0", mass="0", group="1")
    pat = ID_PATTERN[int(rid) % 16]
    for (x, y), c in zip(ID_DOT_POS, pat, strict=True):
        _sub(body, "geom", type="cylinder", pos=(x, y, z_top + 0.0015), size=(0.02, 0.0015),
             rgba=PINK_RGBA if c == "p" else GREEN_RGBA, contype="0", conaffinity="0", mass="0", group="1")
    _sub(body, "geom", name=f"{name}_front_mark", type="box", pos=(spec.dribbler_offset - 0.004, 0, z_top + 0.001),
         size=(0.003, 0.03, 0.001), rgba=(0.1, 0.1, 0.1, 1), contype="0", conaffinity="0", mass="0",
         group=HIDDEN_GROUP if cad else "1")


def cad_assets() -> list[ET.Element]:
    """``<mesh>`` assets of every CAD sub-mesh (chassis, wheel, kicker, dribbler, one per colour; virtual files
    resolved by ``load_model`` or written next to the XML by ``dtssl mjcf --out``)."""
    return [_el("mesh", name=sm.mesh, file=sm.file) for subs in cad_submeshes().values() for sm in subs]


def _cad_geoms(parent: ET.Element, name: str, key: str, pos: Sequence[float], euler=None,
               skip: Sequence[str] = (), only: Sequence[str] | None = None) -> int:
    """One visual-only ``<geom type="mesh">`` per sub-mesh of CAD mesh ``key`` (label filters: ``skip``/``only``).
    Returns the number of geoms written."""
    n = 0
    for sm in cad_submeshes().get(key, ()):
        if sm.label in skip or (only is not None and sm.label not in only):
            continue
        _sub(parent, "geom", name=f"{name}_cad_{key}_{sm.label}", type="mesh", mesh=sm.mesh, pos=tuple(pos),
             euler=euler, rgba=sm.rgba, contype="0", conaffinity="0", mass="0", group="1")
        n += 1
    return n


def _cad_chassis(body: ET.Element, name: str, wheel: WheelGeometry, bar_body: bool = False) -> None:
    """Visual-only CAD chassis + the kicker and dribbler assemblies fixed to it: the OBJ files have their z
    origin on the wheel-axle plane, so they sit at ``z = wheel.r`` and the CAD wheels touch the floor where the
    physics wheels do. With ``bar_body`` (``dribbler="bar"``) the bar part of the dribbler is left out here and
    drawn on the spinning bar body instead."""
    pos = (0.0, 0.0, wheel.r)
    _cad_geoms(body, name, "chassis", pos)
    _cad_geoms(body, name, "kicker", pos)
    _cad_geoms(body, name, "dribbler", pos, skip=(CAD_BAR_LABEL,) if bar_body else ())


def _cad_wheel(parent: ET.Element, name: str, i: int, phi: float, pos: Sequence[float]) -> None:
    """Visual-only CAD wheel ``i`` (hub + rollers, axle along the mesh +x): rotated by ``phi`` about z
    so its axle is the outward radial direction ``u_r`` of the wheel (hinge axis ``-u_r``)."""
    for sm in cad_submeshes().get("wheel", ()):
        _sub(parent, "geom", name=f"{name}_cad_wheel{i}_{sm.label}", type="mesh", mesh=sm.mesh, pos=tuple(pos),
             euler=(0.0, 0.0, phi), rgba=sm.rgba, contype="0", conaffinity="0", mass="0", group="1")


def cad_geom_count() -> int:
    """Visual CAD geoms per robot in ``visual="cad"``: chassis + kicker + dribbler sub-meshes (the bar part sits
    on the chassis or on the bar body, one geom either way) + 4 wheels."""
    subs = cad_submeshes()
    return sum(len(subs.get(k, ())) for k in ("chassis", "kicker", "dribbler")) + 4 * len(subs.get("wheel", ()))


MOUTH_SHELL_MESH, MOUTH_CHEEK_MESH = "mouth_shell", "mouth_cheek"


def mouth_fragment(body: ET.Element, fr: MjcfFragment, name: str, spec: RobotSpec, wheel: WheelGeometry,
                   opt: DribblerOptions, z_bottom: float, z_top: float) -> None:
    """Static geoms the ball meets in front of a robot with ``dribbler="bar"`` (collision bits ``MOUTH``, no
    mass): the rear of the D-shell cut at the chip plate (``mouth_shell``), the two cheeks between the mouth walls
    and the D-face (``mouth_cheek_l/r``, their inner faces are the side plates) and the chip plate as a box
    (``_mouth_plate``). Shared mesh assets (one outline per robot spec); the D-shell itself stops touching the ball."""
    R, mouth = spec.radius, opt.mouth
    front = max(mouth.x_front, spec.dribbler_offset)   # the side plates stick out of the D-face
    if not any(e.get("name") == MOUTH_SHELL_MESH for e in fr.asset):
        fr.asset.append(_el("mesh", name=MOUTH_SHELL_MESH,
                            vertex=_prism_vertices(R, z_bottom, z_top, [(1.0, 0.0, mouth.x_back)])))
        fr.asset.append(_el("mesh", name=f"{MOUTH_CHEEK_MESH}_l",
                            vertex=_prism_vertices(R, z_bottom, z_top, [(-1.0, 0.0, -mouth.x_back), (1.0, 0.0, front),
                                                                      (0.0, -1.0, -mouth.y_max)])))
        fr.asset.append(_el("mesh", name=f"{MOUTH_CHEEK_MESH}_r",
                            vertex=_prism_vertices(R, z_bottom, z_top, [(-1.0, 0.0, -mouth.x_back), (1.0, 0.0, front),
                                                                      (0.0, 1.0, mouth.y_min)])))
    # priority 2 (> the ball's 1): the ball meets the plate and the walls with these parameters, i.e. a
    # critically damped, inelastic contact (a ball hitting the plate stops instead of bouncing off at the
    # restitution of the ball-floor contact) and plastic-on-ball friction
    d_m = _el("default", class_="mouth")
    _sub(d_m, "geom", contype=str(MOUTH_CONTYPE), conaffinity=str(MOUTH_CONAFF), condim="3", priority="2",
         friction=opt.mouth_friction, solref=opt.mouth_solref, solimp=opt.mouth_solimp, mass="0",
         rgba=(0.55, 0.55, 0.6, 0.35), group="2")
    if not any(e.get("class") == "mouth" for e in fr.default):
        fr.default.append(d_m)
    _sub(body, "geom", name=f"{name}_mouth_shell", class_="mouth", type="mesh", mesh=MOUTH_SHELL_MESH)
    _sub(body, "geom", name=f"{name}_mouth_cheek_l", class_="mouth", type="mesh", mesh=f"{MOUTH_CHEEK_MESH}_l")
    _sub(body, "geom", name=f"{name}_mouth_cheek_r", class_="mouth", type="mesh", mesh=f"{MOUTH_CHEEK_MESH}_r")
    c = np.asarray(mouth.plate_centre) + np.array([0.0, 0.0, wheel.r])
    _sub(body, "geom", name=f"{name}_mouth_plate", class_="mouth", type="box", pos=tuple(c),
         quat=_quat_from_axes(mouth.plate_axes), size=tuple(mouth.plate_half))


def dribbler_fragment(body: ET.Element, fr: MjcfFragment, name: str, spec: RobotSpec, wheel: WheelGeometry,
                      ball_radius: float, opt: DribblerOptions, timestep: float, cad: bool = False) -> None:
    """The sprung, spinning bar of ``dribbler="bar"`` (see :class:`DribblerOptions`): body ``<name>_dribbler_module``
    on a slide joint ``<name>_dribbler_slide`` (axis = bar-to-ball direction; 0 = at the forward stop, where the
    body rests and the spring is relaxed; negative = pushed back by the ball, up to ``travel_back`` behind the CAD
    pose), child
    body ``<name>_dribbler_bar`` on the hinge ``<name>_dribbler`` (axis body y) carrying the capsule
    ``<name>_dribbler_bar_geom`` (collision bits ``MOUTH``, priority 2) and, in CAD mode, the bar mesh; actuator
    ``<name>_act_dribbler`` (velocity servo, ``ctrlrange`` 0..speed_max, ``forcerange`` +-torque_max)."""
    axis, gap = opt.engagement(ball_radius, wheel.r)
    stop = 0.0 if opt.engage is None else gap + float(opt.engage)
    # the module body rests AT its forward stop (qpos = 0, no spring force): a ball in the mouth pushes it back
    # (qpos < 0) and the slide range reaches travel_back behind the CAD pose; the bar is drawn where it sits
    offset = stop * axis
    pos = np.asarray(opt.bar_centre) + np.array([0.0, 0.0, wheel.r]) + offset
    module = _sub(body, "body", name=f"{name}_dribbler_module", pos=tuple(pos))
    _sub(module, "joint", name=f"{name}_dribbler_slide", type="slide", axis=tuple(axis),
         range=(-(float(opt.travel_back) + stop), 0.0), stiffness=opt.stiffness, springref=0.0,
         damping=opt.damping, limited="true")
    _sub(module, "inertial", pos=(0, 0, 0), mass=opt.module_mass, diaginertia=(1e-6, 1e-6, 1e-6))
    bar = _sub(module, "body", name=f"{name}_dribbler_bar", pos=(0, 0, 0))
    _sub(bar, "joint", name=f"{name}_dribbler", type="hinge", axis=(0, 1, 0), damping=opt.bar_damping,
         armature=opt.armature, limited="false")
    hl = max(opt.bar_half_length - opt.bar_radius, 0.005)
    _sub(bar, "geom", name=f"{name}_dribbler_bar_geom", type="capsule", fromto=(0, -hl, 0, 0, hl, 0),
         size=opt.bar_radius, mass=opt.bar_mass, contype=str(MOUTH_CONTYPE), conaffinity=str(MOUTH_CONAFF),
         condim="3", priority="2", friction=opt.friction, solref=opt.solref, solimp=opt.solimp,
         rgba=(0.12, 0.12, 0.12, 1.0), group=HIDDEN_GROUP if cad else "0")
    if cad:   # the CAD bar mesh (mesh frame, z above the axle) drawn on the bar body: shift by -(bar_centre+offset)
        _cad_geoms(bar, name, "dribbler", tuple(-np.asarray(opt.bar_centre) - offset), only=(CAD_BAR_LABEL,))
    fr.actuator.append(_el("velocity", name=f"{name}_act_dribbler", joint=f"{name}_dribbler", kv=opt.gain(timestep),
                           ctrlrange=(0.0, opt.speed_max(spec)), forcerange=(-opt.torque_max, opt.torque_max)))


def robot_fragment(team: Team, rid: int, route: str, spec: RobotSpec | None = None,
                   wheel: WheelGeometry | None = None, color: Sequence[float] | None = None,
                   pose: Sequence[float] = (0.0, 0.0, 0.0), route_a: RouteAOptions | None = None,
                   route_b: RouteBOptions | None = None, chassis: str = "mesh",
                   timestep: float = SolverOptions.timestep, visual: str = "primitive",
                   dribbler: str = "spring", dribbler_opt: DribblerOptions | None = None,
                   ball_radius: float = BallSpec.radius) -> MjcfFragment:
    """One robot. ``pose`` only sets the body's reference position (route b free joint start);
    MuJoCoWorld overwrites qpos at reset anyway. ``timestep`` (physics substep) sizes the
    dead-beat servo gains of route a. ``visual``: 'primitive' | 'cad'; ``dribbler``: 'spring' | 'bar' (module
    docstring; the ball of a 'bar' world must be built with ``ball_fragment(..., mouth=True)``)."""
    route = normalize_route(route)
    cad = normalize_visual(visual) == "cad"
    bar = normalize_dribbler(dribbler) == "bar"
    spec = spec or RobotSpec()
    wheel = wheel or WheelGeometry()
    route_a = route_a or RouteAOptions()
    route_b = route_b or RouteBOptions()
    dopt = dribbler_opt or (DribblerOptions.from_cad() if bar else None)
    name = robot_name(team, rid)
    col = tuple(color) if color is not None else (0.22, 0.22, 0.24, 1.0)
    fr = MjcfFragment()

    # --- shared assets / classes -------------------------------------------------------
    z_bottom = 0.008 if route == "b" else 0.0          # ground clearance (route b rides on the wheels)
    z_top = spec.height
    if chassis == "mesh":
        fr.asset.append(_el("mesh", name=CHASSIS_MESH,
                            vertex=_chassis_mesh_vertices(spec.radius, spec.dribbler_offset, z_bottom, z_top)))
    if cad:
        fr.asset.extend(cad_assets())
    d_ch = _el("default", class_="chassis")
    _sub(d_ch, "geom", contype=str(ROBOT_CONTYPE), conaffinity=str(ROBOT_CONAFF_MOUTH if bar else ROBOT_CONAFF),
         condim="3", friction=(0.4, 0.005, 0.0001), solref=(0.004, 1.0), solimp=(0.95, 0.99, 0.001),
         group=HIDDEN_GROUP if cad else "0")
    fr.default.append(d_ch)

    x0, y0, th0 = (float(v) for v in pose)
    if route == "a":
        # the body frame MUST coincide with the world frame: the slide axes are expressed in the
        # body frame and qpos = (x, y, yaw) is then the absolute pose (set by MuJoCoWorld)
        body = _el("body", name=name, pos=(0.0, 0.0, 0.0))
    else:
        body = _el("body", name=name, pos=(x0, y0, 0.0), quat=yaw_quat(th0))

    if route == "a":
        _sub(body, "joint", name=f"{name}_x", type="slide", axis=(1, 0, 0), damping="0")
        _sub(body, "joint", name=f"{name}_y", type="slide", axis=(0, 1, 0), damping="0")
        _sub(body, "joint", name=f"{name}_yaw", type="hinge", axis=(0, 0, 1), damping="0")
    else:
        _sub(body, "freejoint", name=f"{name}_root")

    # explicit inertial: uniform cylinder, CoM on the joint axis (the D-shaped mesh would put it
    # ~5 mm behind the centre and couple the slides with the hinge); the sprung dribbler module and its bar
    # take their mass out of it, so the robot still weighs spec.mass
    moving = (dopt.module_mass + dopt.bar_mass) if bar else 0.0
    _sub(body, "inertial", pos=(0, 0, (z_bottom + z_top) / 2), mass=spec.mass - moving,
         diaginertia=chassis_inertia(spec))
    if chassis == "mesh":
        _sub(body, "geom", name=f"{name}_chassis", class_="chassis", type="mesh", mesh=CHASSIS_MESH,
             mass=spec.mass, rgba=col)
    else:
        _sub(body, "geom", name=f"{name}_chassis", class_="chassis", type="cylinder",
             pos=(0, 0, (z_bottom + z_top) / 2), size=(spec.radius, (z_top - z_bottom) / 2), mass=spec.mass,
             rgba=col)
    if cad:
        _cad_chassis(body, name, wheel, bar_body=bar)
        z_top = wheel.r + cad_plate_z()                     # id plate on the CAD cover (decal plane)
    _robot_visuals(body, name, team, rid, spec, z_top, cad=cad)
    # dribbler face (visual bar) + sites used by the world for kick / dribbler logic
    _sub(body, "geom", name=f"{name}_dribbler_bar", type="box", pos=(spec.dribbler_offset - 0.005, 0, 0.045),
         size=(0.005, 0.045, 0.006), rgba=(0.05, 0.05, 0.05, 1), contype="0", conaffinity="0", mass="0",
         group=HIDDEN_GROUP if (cad or bar) else "1")
    _sub(body, "site", name=f"{name}_dribbler", pos=(spec.dribbler_offset, 0, 0.0215), size=0.006,
         rgba=(1, 0.2, 0.2, 0.6), group="2")
    _sub(body, "site", name=f"{name}_kicker", pos=(spec.dribbler_offset - 0.01, 0, 0.0215), size=0.006,
         rgba=(0.2, 0.2, 1, 0.6), group="2")
    if bar:
        mouth_fragment(body, fr, name, spec, wheel, dopt, z_bottom, spec.height)
        dribbler_fragment(body, fr, name, spec, wheel, ball_radius, dopt, timestep, cad=cad)

    if route == "a":
        kv_s, kv_h = route_a.gains(spec, timestep)
        fmax, tmax = route_a.force_max, route_a.torque_max
        f_lim = None if fmax is None else (-fmax, fmax)
        t_lim = None if tmax is None else (-tmax, tmax)
        fr.actuator.append(_el("velocity", name=f"{name}_act_x", joint=f"{name}_x", kv=kv_s, forcerange=f_lim))
        fr.actuator.append(_el("velocity", name=f"{name}_act_y", joint=f"{name}_y", kv=kv_s, forcerange=f_lim))
        fr.actuator.append(_el("velocity", name=f"{name}_act_yaw", joint=f"{name}_yaw", kv=kv_h,
                               forcerange=t_lim))
        if cad:   # route a has no wheel bodies: static CAD wheels on the chassis
            for i, phi in enumerate(wheel.angles):
                _cad_wheel(body, name, i, float(phi), (wheel.R * math.cos(phi), wheel.R * math.sin(phi), wheel.r))
    else:
        _wheels(body, fr, name, wheel, route_b, cad=cad)
    fr.worldbody.append(body)
    return fr


def _wheels(body: ET.Element, fr: MjcfFragment, name: str, wheel: WheelGeometry, opt: RouteBOptions,
            cad: bool = False) -> None:
    """4 omni wheels with discrete free rollers (ETH/omni wheel with 0 deg rollers).

    Wheel i sits at ``R (cos phi, sin phi)`` at height ``r``; its hinge axis is the *inward* radial
    direction ``-(cos phi, sin phi, 0)`` so that a positive wheel speed moves the wheel centre along
    the CCW tangent ``t = (-sin phi, cos phi, 0)`` (rolling without slip: v_centre = omega * r * t).
    Rollers lie on the rim circle of radius ``r - roller_radius`` in the plane spanned by ``t`` and
    ``z``; each roller hinge axis is tangent to that circle (perpendicular to both the axle and
    the local radial direction), which lets the wheel slide freely along the axle."""
    d_r = _el("default", class_="roller")
    _sub(d_r, "geom", contype=str(ROLLER_CONTYPE), conaffinity=str(ROLLER_CONAFF), condim="3",
         friction=(opt.roller_friction, 0.005, 0.0001), rgba=(0.35, 0.35, 0.38, 1), solref=(0.01, 1.0),
         solimp=(0.95, 0.99, 0.001), group=HIDDEN_GROUP if cad else "0")
    _sub(d_r, "joint", type="hinge", damping=opt.roller_damping, armature=opt.roller_armature, limited="false")
    if not any(e.get("class") == "roller" for e in fr.default):
        fr.default.append(d_r)
    rho = wheel.rim_radius
    n = int(wheel.n_rollers)
    for i, phi in enumerate(wheel.angles):
        ur = np.array([math.cos(phi), math.sin(phi), 0.0])
        t = np.array([-math.sin(phi), math.cos(phi), 0.0])
        z = np.array([0.0, 0.0, 1.0])
        wb = _sub(body, "body", name=f"{name}_wheel{i}", pos=(wheel.R * ur[0], wheel.R * ur[1], wheel.r))
        _sub(wb, "joint", name=f"{name}_wheel{i}", type="hinge", axis=tuple(-ur), damping=opt.wheel_damping,
             armature=opt.wheel_armature, limited="false")
        hw = wheel.hub_half_width
        _sub(wb, "geom", name=f"{name}_wheel{i}_hub", type="cylinder", fromto=tuple(np.r_[-hw * ur, hw * ur]),
             size=max(rho - wheel.roller_radius * 0.5, 0.005), mass=wheel.wheel_mass, rgba=(0.6, 0.6, 0.62, 1),
             contype="0", conaffinity="0", group=HIDDEN_GROUP if cad else "0")
        if cad:   # spins with the wheel body (the CAD rollers are part of the wheel mesh)
            _cad_wheel(wb, name, i, float(phi), (0.0, 0.0, 0.0))
        for j in range(n):
            psi = 2 * math.pi * j / n
            p = rho * (math.cos(psi) * t + math.sin(psi) * z)
            ax = -math.sin(psi) * t + math.cos(psi) * z          # tangent of the rim circle
            rb = _sub(wb, "body", name=f"{name}_wheel{i}_roller{j}", pos=tuple(p))
            _sub(rb, "joint", name=f"{name}_wheel{i}_roller{j}", class_="roller", axis=tuple(ax))
            if wheel.roller_shape == "capsule":
                hl = wheel.roller_half_length
                _sub(rb, "geom", name=f"{name}_wheel{i}_roller{j}_geom", class_="roller", type="capsule",
                     fromto=tuple(np.r_[-hl * ax, hl * ax]), size=wheel.roller_radius, mass=wheel.roller_mass)
            else:  # barrel roller: ellipsoid with its long semi-axis along the roller axis
                _sub(rb, "geom", name=f"{name}_wheel{i}_roller{j}_geom", class_="roller", type="ellipsoid",
                     zaxis=tuple(ax), size=(wheel.roller_radius, wheel.roller_radius, wheel.roller_semi_axis),
                     mass=wheel.roller_mass)
        tmax = opt.wheel_torque_max
        lim = None if tmax is None else (-tmax, tmax)
        if opt.wheel_control == "pi":
            fr.actuator.append(_el("motor", name=f"{name}_act_wheel{i}", joint=f"{name}_wheel{i}", gear="1",
                                   ctrlrange=lim if lim is not None else (-100.0, 100.0)))
        else:
            fr.actuator.append(_el("velocity", name=f"{name}_act_wheel{i}", joint=f"{name}_wheel{i}",
                                   kv=opt.kv_wheel, forcerange=lim))


# --------------------------------------------------------------------------------------
# Public builders (standalone documents) + world composition
# --------------------------------------------------------------------------------------
def build_field_xml(fld: FieldGeometry | None = None, boundary: bool = True,
                    solver: SolverOptions | None = None) -> str:
    """Standalone MJCF of the field (floor, lines, goals, boundary walls)."""
    fld = fld or load_field_geometry()
    return to_xml_string(compose([field_fragment(fld, boundary)], "dtssl-field", solver))


def build_ball_xml(ball: BallSpec | None = None, with_floor: bool = True,
                   solver: SolverOptions | None = None) -> str:
    """Standalone MJCF of the ball (free joint sphere, condim 6) on a floor plane."""
    frs = [ball_fragment(ball or BallSpec())]
    if with_floor:
        frs.insert(0, field_fragment(FieldGeometry(), boundary=False))
    return to_xml_string(compose(frs, "dtssl-ball", solver))


def build_robot_xml(team: Team, rid: int, route: str, spec: RobotSpec | None = None,
                    wheel: WheelGeometry | None = None, color: Sequence[float] | None = None,
                    with_floor: bool = True, solver: SolverOptions | None = None, **kw) -> str:
    """Standalone MJCF of one robot (route a or b) on a floor plane."""
    frs = [robot_fragment(team, rid, route, spec, wheel, color, **kw)]
    if with_floor:
        frs.insert(0, field_fragment(FieldGeometry(), boundary=False))
    return to_xml_string(compose(frs, f"dtssl-robot-{normalize_route(route)}", solver))


def world_root(scene: Scene, route: str, fld: FieldGeometry | None = None, spec: RobotSpec | None = None,
               wheel: WheelGeometry | None = None, ball: BallSpec | None = None,
               solver: SolverOptions | None = None, route_a: RouteAOptions | None = None,
               route_b: RouteBOptions | None = None, boundary: bool = True,
               chassis: str = "mesh", visual: str = "primitive", dribbler: str = "spring",
               dribbler_opt: DribblerOptions | None = None) -> ET.Element:
    route = normalize_route(route)
    bar = normalize_dribbler(dribbler) == "bar"
    fld = fld or load_field_geometry()
    ball = ball or BallSpec()
    frs = [field_fragment(fld, boundary), ball_fragment(ball, (scene.ball.x, scene.ball.y), mouth=bar)]
    solver = solver or SolverOptions()
    if bar and dribbler_opt is None:
        dribbler_opt = DribblerOptions.from_cad()
    for sp in scene.robots:
        frs.append(robot_fragment(sp.team, sp.id, route, spec, wheel, None, (sp.x, sp.y, sp.theta),
                                  route_a, route_b, chassis, timestep=solver.timestep, visual=visual,
                                  dribbler=dribbler, dribbler_opt=dribbler_opt, ball_radius=ball.radius))
    return compose(frs, f"dtssl-route-{route}", solver)


def build_world_xml(scene: Scene | None = None, route: str = "a", **kw) -> str:
    """Full scene (field + ball + all robots of ``scene``) for ``route`` ('a' or 'b')."""
    scene = scene or Scene.default()
    return to_xml_string(world_root(scene, route, **kw))


# --------------------------------------------------------------------------------------
# Description (markdown) for `dtssl mjcf`
# --------------------------------------------------------------------------------------
def describe_xml(xml: str, title: str = "MJCF model") -> str:
    """Markdown summary of bodies / joints / actuators / sites from the XML tree (no mujoco
    needed; sizes from ``mujoco.MjModel`` are appended when the package is importable)."""
    root = ET.fromstring(xml)
    lines = [f"# {title}", "", f"model: `{root.get('model')}`", ""]
    opt = root.find("option")
    if opt is not None:
        lines += ["## option", "", "| key | value |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in sorted(opt.attrib.items())]
        lines.append("")
    bodies = root.iter("body")
    rows = []
    for b in bodies:
        joints = [(j.get("name") or "?", j.get("type") or j.tag) for j in b.findall("joint")]
        joints += [(j.get("name") or "?", "free") for j in b.findall("freejoint")]
        geoms = [g for g in b.findall("geom")]
        mass = sum(float(g.get("mass")) for g in geoms if g.get("mass"))
        rows.append((b.get("name"), len(geoms), f"{mass:.3g}", ", ".join(f"{n} ({t})" for n, t in joints)))
    top = [r for r in rows if "_roller" not in (r[0] or "")]
    n_roller = len(rows) - len(top)
    lines += ["## bodies (rollers collapsed)", "", "| body | geoms | mass (kg) | joints |", "|---|---|---|---|"]
    lines += [f"| {n} | {g} | {m} | {j} |" for n, g, m, j in top]
    if n_roller:
        shape = next((g.get("type") for g in root.iter("geom") if "_roller" in (g.get("name") or "")), "geom")
        lines.append(f"| … {n_roller} roller bodies (`*_roller<j>`, free hinge, {shape}) | | | |")
    lines.append("")
    act = root.find("actuator")
    if act is not None:
        lines += ["## actuators", "", "| name | type | joint | gain/range |", "|---|---|---|---|"]
        for a in act:
            gain = a.get("kv") or a.get("kp") or a.get("gear") or ""
            rng = a.get("forcerange") or a.get("ctrlrange") or ""
            lines.append(f"| {a.get('name')} | {a.tag} | {a.get('joint')} | {gain} {rng} |")
        lines.append("")
    sites = [s.get("name") for s in root.iter("site") if s.get("name")]
    lines += ["## sites", "", ", ".join(f"`{s}`" for s in sites) or "(none)", ""]
    meshes = [(g.get("name"), g.get("file")) for g in root.iter("mesh") if g.get("file")]
    if meshes:
        meta = cad_meta()
        by_file = {sm.file: sm for subs in cad_submeshes().values() for sm in subs}
        lines += ["## CAD meshes (visual only, one asset per colour)", "",
                  "| mesh | colours | faces | source |", "|---|---|---|---|"]
        for key in CAD_KEYS:
            subs = [by_file[f] for _, f in meshes if f in by_file and by_file[f].key == key]
            if not subs:
                continue
            part = meta.get(key, {})
            src = part["source"][1] if "source" in part else ", ".join(meta.get("sources", {}))
            lines.append(f"| {part.get('file', key)} | {len(subs)} | {part.get('faces', '?')} | {src} |")
        lines.append("")
    try:
        m = load_model(xml)
        lines += ["## compiled sizes", "", f"nbody={m.nbody} njnt={m.njnt} nq={m.nq} nv={m.nv} nu={m.nu} "
                  f"ngeom={m.ngeom} nsite={m.nsite} timestep={m.opt.timestep:.6g}", ""]
    except Exception as e:  # pragma: no cover - mujoco absent or load error
        lines += ["## compiled sizes", "", f"(mujoco not available: {type(e).__name__})", ""]
    return "\n".join(lines)


__all__ = [
    "ROUTE_ALIASES", "normalize_route", "robot_name", "WheelGeometry", "BallSpec", "SolverOptions",
    "RouteAOptions", "RouteBOptions", "load_field_geometry", "load_robot_spec", "load_ball_spec",
    "load_wheel_geometry", "load_deadzone", "ik_matrix", "body_to_wheels", "MjcfFragment", "compose",
    "to_xml_string", "field_fragment", "ball_fragment", "robot_fragment", "build_field_xml",
    "build_ball_xml", "build_robot_xml", "build_world_xml", "world_root", "describe_xml", "yaw_quat",
    "chassis_inertia", "VISUAL_MODES", "normalize_visual", "DRIBBLER_MODES", "normalize_dribbler", "cad_meta",
    "cad_plate_z", "cad_assets", "mesh_assets", "cad_mesh_files", "cad_submeshes", "cad_obj", "cad_geom_count",
    "read_obj", "read_mtl", "split_obj", "ObjData", "SubMesh", "uses_cad", "load_model", "ASSET_DIR", "CAD_FILES",
    "CAD_KEYS", "CAD_MESH_PREFIX", "CAD_BAR_PART", "CAD_BAR_LABEL", "MouthGeometry", "DribblerOptions",
    "mouth_fragment", "dribbler_fragment", "BIT_MOUTH", "MOUTH_CONTYPE", "MOUTH_CONAFF", "BALL_CONAFF_MOUTH",
    "ROBOT_CONAFF_MOUTH", "BALL_BODY", "BALL_JOINT", "CHASSIS_MESH", "HIDDEN_GROUP",
]
