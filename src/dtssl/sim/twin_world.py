"""``TwinWorld``: multi-robot world driven by one behavioral :class:`Plant` per robot.

Backends ``"fopdt"`` (``AnalyticFOPDTPlant`` with the published theta, or ``params=``) and
``"ideal"`` (``IdealKinematicPlant``) are registered in :mod:`dtssl.sim.backends`::

    world = make_world("fopdt", n_blue=6, n_yellow=6)
    world.set_command("blue", 0, RobotCmd(vx=1.0))
    ws = world.step()            # 1/60 s: plants -> robot/robot + wall contacts -> ball substeps

Per step (``dt = Ts = 1/60`` by default):

1. every *present* robot advances its plant with the latest command (watchdog-zeroed after
   ``watchdog_s`` without a new command; optional saturation to ``v_max``/``w_max`` and the
   optional firmware per-wheel deadzone, both **off** by default because the published model
   has neither);
2. robot-robot disc overlaps are resolved by a symmetric positional push-out and robot
   centres are clamped to the arena walls (``boundary``) and pushed out of the goal walls, posts, sides and
   back (``goals``; the plant pose is patched; its internal lag/delay state is untouched, so a robot without
   contacts reproduces the plant bit for bit);
3. kick / dribbler logic and the analytic ball (:mod:`dtssl.sim.ball`) in substeps of at most
   ``dt_sub`` (1/600 s), including robot-ball contacts, wall bounces and goal-wall bounces.

Robots that are not *present* (substitutes, ``RobotSpawn.present=False``, ``set_present(False)``, a teleport
with ``present=False``) wait at their :func:`dtssl.sim.entities.park_spot` outside the arena walls: they are
not stepped, meet nothing and are not published in vision, but their pose is reported so the GUI can draw
them beside the field. ``set_present(True)`` brings a robot back where it is, clamped into the arena.

Thread-safety: all public methods take the world lock; the bridge calls ``set_command`` /
``teleport_*`` from network threads while the server thread calls ``step``.
"""
from __future__ import annotations

import json
import logging
import math
import threading
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import numpy as np

from dtssl.models import (
    AnalyticFOPDTPlant,
    DofParam,
    IdealKinematicPlant,
    Plant,
    load_twin_params,
    wrap_to_pi,
)
from dtssl.sim.ball import Ball, BallParams, Walls
from dtssl.sim.collisions import (
    ball_in_front,
    clamp_to_goals,
    clamp_to_walls,
    dribbler_hold_pose,
    goal_ball_contact,
    goal_segments,
    resolve_robot_robot,
    robot_ball_contact,
)
from dtssl.sim.entities import RobotCmd, RobotState, Scene, Team, WorldState, park_spot
from dtssl.sim.world import FieldGeometry, RobotSpec, World

Key = tuple[Team, int]

# --------------------------------------------------------------------------- geometry (spec §3)
WHEEL_ANGLES_DEG: tuple[float, float, float, float] = (60.0, 135.0, 225.0, 300.0)
R_CONTACT = 0.079601      # m, centre -> wheel contact point
WHEEL_RADIUS = 0.029492   # m
DEADZONE_WHEEL_RAD_S = 1.567


def wheel_matrix(angles_deg=WHEEL_ANGLES_DEG, R: float = R_CONTACT, r: float = WHEEL_RADIUS) -> np.ndarray:
    """(4, 3) matrix ``M`` with ``omega_wheel [rad/s] = M @ [vx, vy, w]`` (positive = CCW tangent)."""
    phi = np.radians(np.asarray(angles_deg, dtype=float))
    return np.column_stack([-np.sin(phi), np.cos(phi), np.full(phi.shape, R)]) / r


_M = wheel_matrix()
_M_PINV = np.linalg.pinv(_M)


def _local_body_to_wheels(vx: float, vy: float, w: float) -> np.ndarray:
    return _M @ np.array([vx, vy, w], dtype=float)


def _local_wheels_to_body(wheels_rad_s) -> tuple[float, float, float]:
    v = _M_PINV @ np.asarray(wheels_rad_s, dtype=float).reshape(4)
    return (float(v[0]), float(v[1]), float(v[2]))


_KIN_CACHE: tuple[Callable, Callable] | None = None


def kinematics_functions() -> tuple[Callable[[float, float, float], np.ndarray],
                                    Callable[[object], tuple[float, float, float]]]:
    """``(body_to_wheels, wheels_to_body)`` in wheel rad/s.

    Uses :mod:`dtssl.kinematics` when it is importable *and* follows the same convention
    (pure rotation ``w = 1`` gives ``R / r`` rad/s on every wheel); otherwise the local
    implementation of ``omega_i r = -sin(phi_i) vx + cos(phi_i) vy + R w``.
    """
    global _KIN_CACHE
    if _KIN_CACHE is not None:
        return _KIN_CACHE
    b2w, w2b = _local_body_to_wheels, _local_wheels_to_body
    try:
        import dtssl.kinematics as kin  # lazy: written by the core agent

        cand_b2w = kin.body_to_wheels          # body_to_wheels(v=(vx, vy, w)) -> (4,) rad/s
        cand_w2b = kin.wheels_to_body          # wheels_to_body(omega[4]) -> (3,)
        probe = np.asarray(cand_b2w((0.0, 0.0, 1.0)), dtype=float).reshape(4)
        back = np.asarray(cand_w2b(probe), dtype=float).reshape(3)
        if np.allclose(probe, R_CONTACT / WHEEL_RADIUS, rtol=1e-3) and np.allclose(back, [0.0, 0.0, 1.0], atol=1e-6):
            b2w = lambda vx, vy, w: np.asarray(cand_b2w((vx, vy, w)), dtype=float).reshape(4)  # noqa: E731
            w2b = lambda ws: tuple(float(v) for v in np.asarray(cand_w2b(ws), dtype=float).reshape(3))  # noqa: E731
    except Exception:  # ImportError, AttributeError, TypeError, ValueError -> local fallback
        pass
    _KIN_CACHE = (b2w, w2b)
    return _KIN_CACHE


def body_to_wheels(vx: float, vy: float, w: float) -> np.ndarray:
    """Body velocity -> wheel angular speeds (rad/s), order ``WHEEL_ANGLES_DEG``."""
    return kinematics_functions()[0](vx, vy, w)


def wheels_to_body(wheels_rad_s) -> tuple[float, float, float]:
    """Wheel angular speeds (rad/s, order ``WHEEL_ANGLES_DEG``) -> least-squares body velocity."""
    return kinematics_functions()[1](wheels_rad_s)


def apply_body_deadzone(vx: float, vy: float, w: float,
                        threshold_rad_s: float = DEADZONE_WHEEL_RAD_S) -> tuple[float, float, float]:
    """Firmware deadzone: wheels commanded below ``threshold`` (rad/s) are zeroed, body velocity
    is recovered by the pseudo-inverse. Identity when every wheel is above the threshold."""
    wheels = np.array(body_to_wheels(vx, vy, w), dtype=float)
    mask = np.abs(wheels) < threshold_rad_s
    if not mask.any():
        return (vx, vy, w)
    wheels[mask] = 0.0
    return wheels_to_body(wheels)


def saturate_body(vx: float, vy: float, w: float, v_max: float, w_max: float) -> tuple[float, float, float]:
    v = math.hypot(vx, vy)
    if v_max > 0.0 and v > v_max:
        k = v_max / v
        vx, vy = vx * k, vy * k
    if w_max > 0.0:
        w = min(max(w, -w_max), w_max)
    return (vx, vy, w)


# --------------------------------------------------------------------------- config loaders
def load_field_geometry(path: str | Path | None = None) -> FieldGeometry:
    """``config/field_divB.json`` (mm, ssl-vision key names) -> :class:`FieldGeometry` (m)."""
    try:
        from dtssl.config import load_field

        return load_field(path)
    except ImportError:  # pragma: no cover - dtssl.config absent
        pass
    from dtssl.paths import config_path

    p = Path(path) if path else config_path("field_divB.json")
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    mm = {}
    for k, v in d.items():
        if k.startswith("_"):
            continue
        key = {"field_length": "length", "field_width": "width"}.get(k, k)
        if key in FieldGeometry.__dataclass_fields__:
            mm[key] = v
    return FieldGeometry.from_mm(mm)


def load_robot_spec(path: str | Path | None = None) -> RobotSpec:
    """``config/robot_limits.json: robot`` -> :class:`RobotSpec`."""
    try:
        from dtssl.config import load_limits

        return load_limits(path)[0]
    except ImportError:  # pragma: no cover - dtssl.config absent
        pass
    from dtssl.paths import config_path

    p = Path(path) if path else config_path("robot_limits.json")
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    robot = {k: v for k, v in d.get("robot", {}).items() if k in RobotSpec.__dataclass_fields__}
    return RobotSpec(**robot)


def load_deadzone(path: str | Path | None = None) -> tuple[bool, float]:
    from dtssl.paths import config_path

    p = Path(path) if path else config_path("robot_limits.json")
    with open(p, encoding="utf-8") as f:
        d = json.load(f).get("deadzone", {})
    return bool(d.get("enabled", False)), float(d.get("wheel_min_speed_rad_s", DEADZONE_WHEEL_RAD_S))


# --------------------------------------------------------------------------- world
class TwinWorld(World):
    """Behavioral multi-robot world (see module docstring)."""

    def __init__(self, plant: str | Callable[[], Plant] = "fopdt", *,
                 params: dict[str, DofParam] | None = None,
                 scene: Scene | None = None, n_blue: int = 6, n_yellow: int = 6,
                 field: FieldGeometry | str | Path | None = None,
                 spec: RobotSpec | None = None, ball_params: BallParams | None = None,
                 saturate: bool = False, deadzone: bool = False,
                 deadzone_wheel_rad_s: float = DEADZONE_WHEEL_RAD_S,
                 watchdog_s: float | None = None, watchdog_clock: str | Callable[[], float] = "wall",
                 dt_sub: float = 1.0 / 600.0, kick_cooldown_s: float = 0.1,
                 limits_path: str | Path | None = None, twin_params_path: str | Path | None = None,
                 boundary: bool = True, goals: bool = True, n_active: int | None = None,
                 **unknown):
        if unknown:  # options meant for other backends (e.g. mujoco ``route``) are tolerated but reported
            logging.getLogger(__name__).warning("TwinWorld: ignoring unknown options %s", sorted(unknown))
        self._lock = threading.RLock()
        self.plant_kind = plant if isinstance(plant, str) else "custom"
        self._plant_factory = self._make_factory(plant)
        self.params: dict[str, DofParam] | None = None
        if self.plant_kind == "fopdt":
            self.params = params or load_twin_params(twin_params_path)
        elif params is not None:
            self.params = params
        self._field = field if isinstance(field, FieldGeometry) else load_field_geometry(field)
        self._spec = spec or load_robot_spec(limits_path)
        self.ball_params = ball_params or BallParams.from_config(limits_path)
        self.saturate = bool(saturate)
        self.deadzone = bool(deadzone)
        self.deadzone_wheel_rad_s = float(deadzone_wheel_rad_s)
        self.watchdog_s = float(self._spec.watchdog_s if watchdog_s is None else watchdog_s)
        self.watchdog_clock = watchdog_clock
        self.dt_sub = float(dt_sub)
        self.kick_cooldown_s = float(kick_cooldown_s)
        self.boundary = bool(boundary)                 # arena walls: robots clamped, ball bounces
        self.goals = bool(goals)                       # goal walls (posts, sides, back) for robots and ball
        self.walls = Walls.from_field(self._field, self.ball_params.radius)
        self.goal_segs = goal_segments(self._field) if self.goals else ()

        self.plants: dict[Key, Plant] = {}
        self.commands: dict[Key, RobotCmd] = {}
        self._present: dict[Key, bool] = {}
        self._wd_armed: dict[Key, bool] = {}       # command received and not yet watchdog-zeroed
        self._kick_ready: dict[Key, float] = {}
        self.ball_obj = Ball(self.ball_params)
        self.t = 0.0
        self.frame = 0
        self.watchdog_hits = 0
        self.kicks = 0
        self.contacts = 0
        self.reset(scene or Scene.default(n_blue, n_yellow, self._field.length, self._field.width,
                                          n_active=n_active, boundary_width_m=self._field.boundary_width))

    # ------------------------------------------------------------------ construction helpers
    def _make_factory(self, plant) -> Callable[[], Plant]:
        if callable(plant) and not isinstance(plant, str):
            return plant  # type: ignore[return-value]
        if plant == "fopdt":
            return lambda: AnalyticFOPDTPlant(self.params)
        if plant == "ideal":
            return lambda: IdealKinematicPlant()
        raise ValueError(f"unknown plant kind {plant!r} (expected 'fopdt', 'ideal' or a factory)")

    def _clock(self) -> float:
        c = self.watchdog_clock
        if c == "wall":
            return time.monotonic()
        if c == "sim":
            return self.t
        return float(c())  # type: ignore[operator]

    def _new_plant(self, x: float, y: float, theta: float, velb0=(0.0, 0.0, 0.0)) -> Plant:
        p = self._plant_factory()
        p.reset((float(x), float(y), float(theta)), tuple(float(v) for v in velb0))
        p.prime_delay([])
        return p

    def park_spot(self, team: Team, rid: int) -> tuple[float, float, float]:
        """Where robot ``rid`` of ``team`` waits outside the arena when it is not present."""
        return park_spot(team, rid, self._field.length, self._field.width, self._field.boundary_width)

    # ------------------------------------------------------------------ World API
    @property
    def field(self) -> FieldGeometry:
        return self._field

    @property
    def spec(self) -> RobotSpec:
        return self._spec

    @property
    def name(self) -> str:
        return f"TwinWorld[{self.plant_kind}]"

    def reset(self, scene: Scene) -> None:
        with self._lock:
            self.plants.clear()
            self.commands.clear()
            self._present.clear()
            self._wd_armed.clear()
            self._kick_ready.clear()
            for sp in scene.robots:
                key = (sp.team, int(sp.id))
                pose = (sp.x, sp.y, sp.theta) if sp.present else self.park_spot(*key)
                self.plants[key] = self._new_plant(*pose)
                self._present[key] = bool(sp.present)
                self.commands[key] = RobotCmd()
            b = scene.ball
            self.ball_obj = Ball(self.ball_params)
            self.ball_obj.set(b.x, b.y, b.vx, b.vy, b.z, b.vz, rolling=b.rolling and (b.vx != 0 or b.vy != 0))
            self.t = 0.0
            self.frame = 0
            self.watchdog_hits = 0
            self.kicks = 0
            self.contacts = 0

    def set_command(self, team: Team, rid: int, cmd: RobotCmd) -> None:
        key = (team, int(rid))
        with self._lock:
            if key not in self.plants:
                return
            c = replace(cmd)
            c.t_recv = self._clock()
            self.commands[key] = c
            self._wd_armed[key] = True

    def step(self, dt: float | None = None) -> WorldState:
        dt = self.ts if dt is None else float(dt)
        with self._lock:
            now = self._clock()
            applied: dict[Key, RobotCmd] = {}
            prev_poses: dict[Key, tuple[float, float, float]] = {}
            for key, plant in self.plants.items():
                if not self._present.get(key, True):
                    continue
                prev_poses[key] = tuple(float(v) for v in plant.pose)  # type: ignore[assignment]
                cmd = self.commands.get(key)
                if cmd is None:
                    cmd = self.commands[key] = RobotCmd()
                if (self.watchdog_s > 0.0 and self._wd_armed.get(key, False)
                        and now - cmd.t_recv > self.watchdog_s):
                    cmd = RobotCmd(t_recv=cmd.t_recv)
                    self.commands[key] = cmd
                    self._wd_armed[key] = False
                    self.watchdog_hits += 1
                vx, vy, w = cmd.vx, cmd.vy, cmd.w
                if self.saturate:
                    vx, vy, w = saturate_body(vx, vy, w, self._spec.v_max, self._spec.w_max)
                if self.deadzone:
                    vx, vy, w = apply_body_deadzone(vx, vy, w, self.deadzone_wheel_rad_s)
                plant.step((vx, vy, w), dt)
                applied[key] = cmd
            self._resolve_robot_contacts(applied)
            self._ball_frame(dt, applied, prev_poses)
            self.t += dt
            self.frame += 1
            return self._state_locked()

    def state(self) -> WorldState:
        with self._lock:
            return self._state_locked()

    def teleport_robot(self, team: Team, rid: int, x: float, y: float, theta: float,
                       present: bool = True, vx: float = 0.0, vy: float = 0.0, w: float = 0.0) -> None:
        """Reset a robot's plant to ``(x, y, theta)`` with **world** velocity ``(vx, vy, w)``."""
        key = (team, int(rid))
        if not present:                                # removed from the field: parked outside, at rest
            x, y, theta = self.park_spot(*key)
            vx = vy = w = 0.0
        c, s = math.cos(theta), math.sin(theta)
        velb0 = (c * vx + s * vy, -s * vx + c * vy, w)
        with self._lock:
            self.plants[key] = self._new_plant(x, y, theta, velb0)
            self._present[key] = bool(present)
            self.commands.setdefault(key, RobotCmd())
            if self.ball_obj.captured_by == key:
                self.ball_obj.captured_by = None

    def set_robot_state(self, team: Team, rid: int, x: float, y: float, theta: float,
                        vx_b: float = 0.0, vy_b: float = 0.0, w: float = 0.0) -> None:
        """Harness initial condition: pose + **body** velocity (see ``WorldPlant``)."""
        key = (team, int(rid))
        with self._lock:
            self.plants[key] = self._new_plant(x, y, theta, (float(vx_b), float(vy_b), float(w)))
            self._present[key] = True
            self.commands.setdefault(key, RobotCmd())
            if self.ball_obj.captured_by == key:
                self.ball_obj.captured_by = None

    def prime_robot_delay(self, team: Team, rid: int, prev_cmds) -> None:
        """Fill the plant's delay buffer with the commands before t0 (harness ``prime_delay``)."""
        key = (team, int(rid))
        with self._lock:
            plant = self.plants.get(key)
            if plant is not None and hasattr(plant, "prime_delay"):
                plant.prime_delay(prev_cmds)

    def robot_pose(self, team: Team, rid: int) -> tuple[float, float, float]:
        with self._lock:
            return tuple(float(v) for v in self.plants[(team, int(rid))].pose)

    def set_present(self, team: Team, rid: int, present: bool) -> None:
        """Remove a robot from play (parked outside the arena) or bring it back where it is (clamped into
        the arena, i.e. just inside the wall nearest to its parking spot when it was parked)."""
        key = (team, int(rid))
        with self._lock:
            plant = self.plants.get(key)
            if plant is None or self._present.get(key, True) == bool(present):
                return
            self._present[key] = bool(present)
            if not present:
                if self.ball_obj.captured_by == key:
                    self.ball_obj.captured_by = None
                self.plants[key] = self._new_plant(*self.park_spot(*key))
            elif self.boundary:
                x, y, th = (float(v) for v in plant.pose)
                cx, cy = clamp_to_walls(x, y, self._spec.radius, self._field)
                if (cx, cy) != (x, y):
                    self.plants[key] = self._new_plant(cx, cy, th)

    def is_present(self, team: Team, rid: int) -> bool:
        return self._present.get((team, int(rid)), False)

    def teleport_ball(self, x: float, y: float, vx: float = 0.0, vy: float = 0.0, z: float = 0.0,
                      vz: float = 0.0, rolling: bool = False) -> None:
        with self._lock:
            self.ball_obj.set(x, y, vx, vy, z, vz, rolling=rolling)

    def set_plant_params(self, params: dict[str, DofParam]) -> None:
        """Hot-swap theta for every robot, keeping pose, body velocity and delay buffers when the
        plant is an ``AnalyticFOPDTPlant`` (parameters are patched in place)."""
        with self._lock:
            self.params = params
            for key, plant in list(self.plants.items()):
                if isinstance(plant, AnalyticFOPDTPlant):
                    plant.params = params
                    plant.K = np.array([params[d].K for d in ("vx", "vy", "w")], dtype=float)
                    plant.tau = np.array([params[d].tau for d in ("vx", "vy", "w")], dtype=float)
                    plant.Td = np.array([params[d].Td for d in ("vx", "vy", "w")], dtype=float)
                elif self.plant_kind == "fopdt":
                    new = self._plant_factory()
                    new.reset(plant.pose, plant.body_velocity)
                    new.prime_delay([])
                    self.plants[key] = new

    def close(self) -> None:
        pass

    # ------------------------------------------------------------------ extras used by GUI/bridge
    def robot_keys(self, present_only: bool = True) -> list[Key]:
        with self._lock:
            return [k for k in sorted(self.plants) if (self._present.get(k, True) or not present_only)]

    def has_ball(self, team: Team, rid: int) -> bool:
        with self._lock:
            key = (team, int(rid))
            plant = self.plants.get(key)
            if plant is None or not self._present.get(key, True):
                return False
            return self._in_front(key, plant)

    def effective_command(self, team: Team, rid: int) -> RobotCmd:
        with self._lock:
            return replace(self.commands.get((team, int(rid)), RobotCmd()))

    # ------------------------------------------------------------------ internals
    def _state_locked(self) -> WorldState:
        robots: dict[Key, RobotState] = {}
        for key, plant in self.plants.items():
            x, y, th = plant.pose
            vb = plant.body_velocity
            present = self._present.get(key, True)
            robots[key] = RobotState(team=key[0], id=key[1], x=float(x), y=float(y),
                                     theta=wrap_to_pi(float(th)),
                                     vx_b=float(vb[0]), vy_b=float(vb[1]), w=float(vb[2]),
                                     has_ball=present and self._in_front(key, plant),
                                     present=present)
        ball = self.ball_obj.copy_state()
        if self.ball_obj.captured_by is not None:
            holder = self.plants.get(self.ball_obj.captured_by)
            if holder is not None:
                vxw, vyw = self._world_velocity(holder)
                ball.vx, ball.vy = vxw, vyw
        return WorldState(t=self.t, frame=self.frame, robots=robots, ball=ball)

    def _in_front(self, key: Key, plant: Plant) -> bool:
        if self.ball_obj.captured_by == key:
            return True
        b = self.ball_obj.state
        x, y, th = plant.pose
        return ball_in_front(b.x, b.y, b.z, x, y, th, self._spec.ball_contact_dist,
                             self._spec.dribbler_half_angle)

    @staticmethod
    def _world_velocity(plant: Plant) -> tuple[float, float]:
        th = plant.pose[2]
        vb = plant.body_velocity
        c, s = math.cos(th), math.sin(th)
        return (c * vb[0] - s * vb[1], s * vb[0] + c * vb[1])

    def _resolve_robot_contacts(self, applied: dict[Key, RobotCmd]) -> None:
        keys = list(applied)
        if not keys:
            return
        positions = [[self.plants[k].x, self.plants[k].y] for k in keys]
        if len(keys) > 1 and resolve_robot_robot(positions, self._spec.radius):
            self.contacts += 1
        for k, (px, py) in zip(keys, positions, strict=True):
            plant = self.plants[k]
            cx, cy = clamp_to_walls(px, py, self._spec.radius, self._field) if self.boundary else (px, py)
            if self.goal_segs:
                cx, cy = clamp_to_goals(cx, cy, self._spec.radius, self._field, self.goal_segs)
            if cx != plant.x or cy != plant.y:
                plant.x, plant.y = cx, cy   # patch pose only; lag/delay state untouched

    def _ball_frame(self, dt: float, applied: dict[Key, RobotCmd],
                    prev_poses: dict[Key, tuple[float, float, float]] | None = None) -> None:
        """Kick/dribbler logic then ball substeps. Inside the substeps each robot pose is
        interpolated linearly from its pose before the plant step to the new one, and the
        contact velocity is the finite difference over the frame (consistent with the
        interpolation), so a robot pushing the ball keeps it on its face."""
        ball = self.ball_obj
        spec = self._spec
        for key, cmd in applied.items():
            plant = self.plants[key]
            x, y, th = plant.pose
            if ball.captured_by == key:
                in_front = True
            else:
                b = ball.state
                in_front = ball_in_front(b.x, b.y, b.z, x, y, th, spec.ball_contact_dist,
                                         spec.dribbler_half_angle)
            if not in_front:
                continue
            if cmd.kick_speed > 0.0 and self.t >= self._kick_ready.get(key, -math.inf):
                chip = cmd.kick_angle_deg > 0.0
                speed = min(cmd.kick_speed, spec.kick_chip_max if chip else spec.kick_flat_max)
                if ball.captured_by == key:
                    bx, by = dribbler_hold_pose(x, y, th, spec.dribbler_offset, ball.radius)
                    ball.state.x, ball.state.y = bx, by
                ball.kick(speed, th, chip=chip, chip_angle_deg=spec.chip_angle_deg)
                self._kick_ready[key] = self.t + self.kick_cooldown_s
                self.kicks += 1
                cmd.kick_speed = 0.0          # consumed once
                continue
            if cmd.dribbler_rpm > 0.0 and not ball.airborne:
                ball.captured_by = key
                bx, by = dribbler_hold_pose(x, y, th, spec.dribbler_offset, ball.radius)
                vxw, vyw = self._world_velocity(plant)
                ball.state.x, ball.state.y, ball.state.z, ball.state.vz = bx, by, 0.0, 0.0
                ball.state.vx, ball.state.vy = vxw, vyw
            elif ball.captured_by == key:      # dribbler switched off: release with robot velocity
                vxw, vyw = self._world_velocity(plant)
                ball.captured_by = None
                ball.set_velocity(vxw, vyw, rolling=False)
        if ball.captured_by is not None and ball.captured_by not in applied:
            ball.captured_by = None            # holder removed / not present
        if ball.captured_by is not None:
            return
        n_sub = max(1, int(math.ceil(dt / self.dt_sub - 1e-9)))
        h = dt / n_sub
        robots = []
        for key in applied:
            plant = self.plants[key]
            x1, y1, th1 = (float(v) for v in plant.pose)
            x0, y0, th0 = prev_poses.get(key, (x1, y1, th1)) if prev_poses else (x1, y1, th1)
            if dt > 0.0:
                vxw, vyw, w = (x1 - x0) / dt, (y1 - y0) / dt, (th1 - th0) / dt
            else:
                vxw, vyw = self._world_velocity(plant)
                w = float(plant.body_velocity[2])
            robots.append((x0, y0, th0, x1, y1, th1, vxw, vyw, w))
        e = self.ball_params.restitution_robot
        walls = self.walls if self.boundary else None
        for i in range(1, n_sub + 1):
            ball.step(h, walls)
            if self.goal_segs:
                goal_ball_contact(ball, self._field, segments=self.goal_segs)
            a = i / n_sub
            for (x0, y0, th0, x1, y1, th1, vxw, vyw, w) in robots:
                robot_ball_contact(ball, x0 + a * (x1 - x0), y0 + a * (y1 - y0), th0 + a * (th1 - th0),
                                   vxw, vyw, w, spec.radius, spec.dribbler_offset, spec.height, e)


__all__ = [
    "TwinWorld", "load_field_geometry", "load_robot_spec", "load_deadzone",
    "wheel_matrix", "body_to_wheels", "wheels_to_body", "apply_body_deadzone", "saturate_body",
    "WHEEL_ANGLES_DEG", "R_CONTACT", "WHEEL_RADIUS", "DEADZONE_WHEEL_RAD_S", "kinematics_functions",
]
