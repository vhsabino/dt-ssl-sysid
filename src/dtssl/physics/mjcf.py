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
the roller geoms themselves; ``"cad"`` adds the RobôCIn v2025 CAD meshes (``assets/ssl_chassis.obj``,
``assets/ssl_wheel.obj``, exported from ``usd/`` by ``tools/usd_to_mjcf_meshes.py``) as visual-only
geoms (``contype = conaffinity = 0``, ``mass = 0``) and moves the primitives to geom group 3 (hidden
in the viewer by default). The physics is identical in both modes (same bodies, joints, collision
geoms, inertias and actuators): the meshes only change what is drawn. Models with CAD meshes must be
compiled with the OBJ bytes attached (``load_model``) or from a directory holding the files
(``dtssl mjcf --out`` copies them next to the XML).
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
BIT_FLOOR, BIT_BALL, BIT_ROBOT, BIT_WALL, BIT_ROLLER = 1, 2, 4, 8, 16
FLOOR_CONTYPE, FLOOR_CONAFF = BIT_FLOOR, BIT_FLOOR | BIT_BALL | BIT_ROLLER
BALL_CONTYPE, BALL_CONAFF = BIT_BALL, BIT_FLOOR | BIT_ROBOT | BIT_WALL
ROBOT_CONTYPE, ROBOT_CONAFF = BIT_ROBOT, BIT_BALL | BIT_ROBOT | BIT_WALL   # chassis never touches the floor
WALL_CONTYPE, WALL_CONAFF = BIT_WALL, BIT_BALL | BIT_ROBOT
ROLLER_CONTYPE, ROLLER_CONAFF = BIT_ROLLER, BIT_FLOOR                      # rollers only touch the floor

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
# Visual modes and CAD mesh assets (src/dtssl/physics/assets, see tools/usd_to_mjcf_meshes.py)
# --------------------------------------------------------------------------------------
VISUAL_MODES = ("primitive", "cad")
ASSET_DIR = Path(__file__).resolve().parent / "assets"
CAD_CHASSIS_MESH, CAD_WHEEL_MESH = "ssl_cad_chassis", "ssl_cad_wheel"
CAD_FILES = ("ssl_chassis.obj", "ssl_wheel.obj", "ssl_chassis_lod.obj", "ssl_wheel_lod.obj", "meshes.json")
HIDDEN_GROUP = "3"        # geom group not drawn by the viewer by default (groups 0-2 are)
CAD_CHASSIS_RGBA = (0.16, 0.16, 0.18, 1.0)
CAD_WHEEL_RGBA = (0.62, 0.62, 0.66, 1.0)


def normalize_visual(visual: str | None) -> str:
    v = (visual or "primitive").lower()
    if v not in VISUAL_MODES:
        raise ValueError(f"unknown visual mode {visual!r}; expected one of {VISUAL_MODES}")
    return v


@lru_cache(maxsize=1)
def cad_meta() -> dict:
    """``assets/meshes.json``: provenance + derived constants of the CAD meshes (top of the cover
    above the wheel axle, wheel outer radius, face counts, source md5)."""
    return json.loads((ASSET_DIR / "meshes.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def mesh_assets() -> dict[str, bytes]:
    """``{file name: bytes}`` of the CAD meshes, in the form ``mujoco.MjModel.from_xml_string`` takes.
    The OBJ files are tracked with git LFS: a checkout without LFS holds pointer files, which is
    reported here instead of failing inside the MuJoCo OBJ parser."""
    out = {}
    for f in CAD_FILES:
        if not f.endswith(".obj"):
            continue
        data = (ASSET_DIR / f).read_bytes()
        if data.startswith(b"version https://git-lfs"):
            raise RuntimeError(f"{ASSET_DIR / f} is a git LFS pointer, not the mesh: run `git lfs pull` "
                               "(or regenerate with tools/usd_to_mjcf_meshes.py)")
        out[f] = data
    return out


def uses_cad(xml: str) -> bool:
    return f'name="{CAD_CHASSIS_MESH}"' in xml or f'name="{CAD_WHEEL_MESH}"' in xml


def load_model(xml: str):
    """``mujoco.MjModel`` from an XML string, attaching the CAD mesh files when it references them."""
    import mujoco  # noqa: WPS433 (optional dependency)

    if uses_cad(xml):
        return mujoco.MjModel.from_xml_string(xml, mesh_assets())
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


def ball_fragment(ball: BallSpec | None = None, pos: Sequence[float] = (0.0, 0.0)) -> MjcfFragment:
    ball = ball or BallSpec()
    fr = MjcfFragment()
    fr.asset.append(_el("material", name="mat_ball", rgba=(1.0, 0.45, 0.05, 1.0), specular="0.6", shininess="0.6"))
    b = _el("body", name=BALL_BODY, pos=(pos[0], pos[1], ball.radius))
    _sub(b, "freejoint", name=BALL_JOINT)
    _sub(b, "geom", name="ball_geom", type="sphere", size=ball.radius, mass=ball.mass, material="mat_ball",
         contype=str(BALL_CONTYPE), conaffinity=str(BALL_CONAFF), condim="6", priority="1",
         friction=(ball.mu_slide, ball.torsional_friction, ball.mu_roll),
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
    """``<mesh>`` assets of the CAD chassis and wheel (file references resolved by ``load_model`` or
    by the OBJ files copied next to the written XML)."""
    meta = cad_meta()
    return [_el("mesh", name=CAD_CHASSIS_MESH, file=meta["chassis"]["file"]),
            _el("mesh", name=CAD_WHEEL_MESH, file=meta["wheel"]["file"])]


def _cad_chassis(body: ET.Element, name: str, wheel: WheelGeometry, rgba: Sequence[float]) -> None:
    """Visual-only CAD chassis: the OBJ has its z origin on the wheel-axle plane, so it sits at
    ``z = wheel.r`` and the CAD wheels touch the floor where the physics wheels do."""
    _sub(body, "geom", name=f"{name}_cad_chassis", type="mesh", mesh=CAD_CHASSIS_MESH, pos=(0, 0, wheel.r),
         rgba=tuple(rgba), contype="0", conaffinity="0", mass="0", group="1")


def _cad_wheel(parent: ET.Element, name: str, i: int, phi: float, pos: Sequence[float]) -> None:
    """Visual-only CAD wheel ``i`` (hub + rollers, axle along the mesh +x): rotated by ``phi`` about z
    so its axle is the outward radial direction ``u_r`` of the wheel (hinge axis ``-u_r``)."""
    _sub(parent, "geom", name=f"{name}_cad_wheel{i}", type="mesh", mesh=CAD_WHEEL_MESH, pos=tuple(pos),
         euler=(0.0, 0.0, phi), rgba=CAD_WHEEL_RGBA, contype="0", conaffinity="0", mass="0", group="1")


def robot_fragment(team: Team, rid: int, route: str, spec: RobotSpec | None = None,
                   wheel: WheelGeometry | None = None, color: Sequence[float] | None = None,
                   pose: Sequence[float] = (0.0, 0.0, 0.0), route_a: RouteAOptions | None = None,
                   route_b: RouteBOptions | None = None, chassis: str = "mesh",
                   timestep: float = SolverOptions.timestep, visual: str = "primitive") -> MjcfFragment:
    """One robot. ``pose`` only sets the body's reference position (route b free joint start);
    MuJoCoWorld overwrites qpos at reset anyway. ``timestep`` (physics substep) sizes the
    dead-beat servo gains of route a. ``visual``: 'primitive' | 'cad' (module docstring)."""
    route = normalize_route(route)
    cad = normalize_visual(visual) == "cad"
    spec = spec or RobotSpec()
    wheel = wheel or WheelGeometry()
    route_a = route_a or RouteAOptions()
    route_b = route_b or RouteBOptions()
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
    _sub(d_ch, "geom", contype=str(ROBOT_CONTYPE), conaffinity=str(ROBOT_CONAFF), condim="3",
         friction=(0.4, 0.005, 0.0001), solref=(0.004, 1.0), solimp=(0.95, 0.99, 0.001),
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
    # ~5 mm behind the centre and couple the slides with the hinge)
    _sub(body, "inertial", pos=(0, 0, (z_bottom + z_top) / 2), mass=spec.mass, diaginertia=chassis_inertia(spec))
    if chassis == "mesh":
        _sub(body, "geom", name=f"{name}_chassis", class_="chassis", type="mesh", mesh=CHASSIS_MESH,
             mass=spec.mass, rgba=col)
    else:
        _sub(body, "geom", name=f"{name}_chassis", class_="chassis", type="cylinder",
             pos=(0, 0, (z_bottom + z_top) / 2), size=(spec.radius, (z_top - z_bottom) / 2), mass=spec.mass,
             rgba=col)
    if cad:
        _cad_chassis(body, name, wheel, CAD_CHASSIS_RGBA if color is None else col)
        z_top = wheel.r + float(cad_meta()["chassis"]["z_top_above_axle"])   # plate on the CAD cover
    _robot_visuals(body, name, team, rid, spec, z_top, cad=cad)
    # dribbler face (visual bar) + sites used by the world for kick / dribbler logic
    _sub(body, "geom", name=f"{name}_dribbler_bar", type="box", pos=(spec.dribbler_offset - 0.005, 0, 0.045),
         size=(0.005, 0.045, 0.006), rgba=(0.05, 0.05, 0.05, 1), contype="0", conaffinity="0", mass="0",
         group=HIDDEN_GROUP if cad else "1")
    _sub(body, "site", name=f"{name}_dribbler", pos=(spec.dribbler_offset, 0, 0.0215), size=0.006,
         rgba=(1, 0.2, 0.2, 0.6), group="2")
    _sub(body, "site", name=f"{name}_kicker", pos=(spec.dribbler_offset - 0.01, 0, 0.0215), size=0.006,
         rgba=(0.2, 0.2, 1, 0.6), group="2")

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
               chassis: str = "mesh", visual: str = "primitive") -> ET.Element:
    route = normalize_route(route)
    fld = fld or load_field_geometry()
    frs = [field_fragment(fld, boundary), ball_fragment(ball or BallSpec(), (scene.ball.x, scene.ball.y))]
    solver = solver or SolverOptions()
    for sp in scene.robots:
        frs.append(robot_fragment(sp.team, sp.id, route, spec, wheel, None, (sp.x, sp.y, sp.theta),
                                  route_a, route_b, chassis, timestep=solver.timestep, visual=visual))
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
        lines += ["## CAD meshes (visual only)", "", "| asset | file | faces | source |", "|---|---|---|---|"]
        for nm, f in meshes:
            part = next((v for v in (meta.get("chassis"), meta.get("wheel")) if v and v.get("file") == f), {})
            src = ", ".join(meta.get("sources", {}))
            lines.append(f"| {nm} | {f} | {part.get('faces', '?')} | {src} |")
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
    "chassis_inertia", "VISUAL_MODES", "normalize_visual", "cad_meta", "cad_assets", "mesh_assets",
    "uses_cad", "load_model", "ASSET_DIR", "CAD_FILES",
    "BALL_BODY", "BALL_JOINT", "CHASSIS_MESH", "CAD_CHASSIS_MESH", "CAD_WHEEL_MESH", "HIDDEN_GROUP",
]
