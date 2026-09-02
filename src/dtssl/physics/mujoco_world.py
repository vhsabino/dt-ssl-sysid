"""``MuJoCoWorld``: :class:`dtssl.sim.world.World` backed by MuJoCo (SPEC §4.6).

Two routes share the same field / ball / API (registered in :mod:`dtssl.sim.backends`)::

    world = make_world("mujoco-velocity", n_blue=6, n_yellow=6)     # route a
    world = make_world("mujoco-rollers", n_blue=1, n_yellow=0)      # route b (experimental)
    world.set_command("blue", 0, RobotCmd(vx=1.0))
    ws = world.step()                                               # 1/60 s = n_sub MuJoCo steps

* **route a** (``mujoco-velocity``): each robot owns a behavioral plant (``AnalyticFOPDTPlant``
  with the published theta by default). Every step the plant is advanced with the commanded
  body velocity and the three ``velocity`` actuators (slide x, slide y, hinge z) are given the
  world-frame target ``R(theta) v_body`` — the *mean* of the plant's body velocity at the two
  ends of the interval, so that perfect tracking reproduces the plant's trapezoidal pose
  integration sample by sample. The servo is dead-beat (Euler integrator, ``kv = m / h``): the
  target is reached in one substep and the chassis reproduces the plant exactly while no force
  limit (150 N / 3 N m) is hit. MuJoCo only adds contacts (ball, robots, walls); the actual
  heading read from MuJoCo is used for the rotation, so a robot deflected by a collision keeps
  driving along its real heading. The plant pose itself is never used (it is not re-anchored).
* **route b** (``mujoco-rollers``): physical omni wheels with free rollers; wheel targets come
  from the inverse kinematics (``omega_i r = -sin phi_i vx + cos phi_i vy + R w``) with the
  optional firmware deadzone, sent to ``velocity`` actuators (default) or to ``motor``
  actuators through a Python PI loop in firmware units (``wheel_control="pi"``).

Common: kick (ball velocity set along the heading when the ball is in the dribbler zone,
chip adds a vertical component), dribbler (weak spring-damper pulling the ball to the dribbler
pocket through ``xfrc_applied``), watchdog (command zeroed after ``watchdog_s`` without a new
one; ``watchdog_clock`` = "wall" | "sim" | callable, as in ``TwinWorld``), teleports, hot-swap
of theta (route a). ``step(dt)`` runs ``n_sub = round(dt / timestep)`` substeps with
``model.opt.timestep = dt / n_sub`` so the simulated time is exact for any ``dt``.

MuJoCo is imported lazily (``import dtssl.physics`` never needs it); ``model``/``data`` are
exposed for viewers (``viewer()`` launches the passive viewer, ``close()`` closes it).
"""
from __future__ import annotations

import logging
import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
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
from dtssl.physics import mjcf
from dtssl.physics.mjcf import (
    BALL_BODY,
    BALL_JOINT,
    BallSpec,
    RouteAOptions,
    RouteBOptions,
    SolverOptions,
    WheelGeometry,
    normalize_route,
    robot_name,
)
from dtssl.sim.entities import BallState, RobotCmd, RobotState, Scene, Team, WorldState
from dtssl.sim.world import FieldGeometry, RobotSpec, World

Key = tuple[Team, int]
_log = logging.getLogger(__name__)


def _ball_in_front(bx: float, by: float, bz: float, rx: float, ry: float, rtheta: float,
                   contact_dist: float, half_angle: float, z_tol: float = 0.02) -> bool:
    """Ball inside the dribbler acceptance cone (same rule as ``dtssl.sim.collisions``)."""
    try:
        from dtssl.sim.collisions import ball_in_front

        return ball_in_front(bx, by, bz, rx, ry, rtheta, contact_dist, half_angle, z_tol)
    except ImportError:  # pragma: no cover - local copy
        if bz > z_tol:
            return False
        dx, dy = bx - rx, by - ry
        if math.hypot(dx, dy) > contact_dist:
            return False
        ang = math.atan2(dy, dx) - rtheta
        return abs(math.atan2(math.sin(ang), math.cos(ang))) <= half_angle


def quat_yaw(q) -> float:
    """Yaw (rad) of a MuJoCo quaternion ``(w, x, y, z)``."""
    w, x, y, z = (float(v) for v in q)
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


@dataclass
class PIGains:
    """Firmware per-wheel PI (ssl-embedded PID_Controller): output in PWM units. The PWM
    full scale is NOT documented; ``pwm_max`` (= integrator limit, assumed full scale) maps
    the output to torque as ``torque = u / pwm_max * torque_max``. Experimental."""

    kp: float = 0.3194
    ki: float = 6.434
    integrator_limit: float = 2527.1
    pwm_max: float = 2527.1


@dataclass
class _Robot:
    key: Key
    name: str
    present: bool = True
    body_id: int = -1
    # route a
    qadr: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=int))
    dofadr: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=int))
    act: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=int))
    plant: Plant | None = None
    # route b
    root_qadr: int = -1
    root_dofadr: int = -1
    wheel_dofadr: np.ndarray = field(default_factory=lambda: np.zeros(4, dtype=int))
    wheel_qadr: np.ndarray = field(default_factory=lambda: np.zeros(4, dtype=int))
    wheel_act: np.ndarray = field(default_factory=lambda: np.zeros(4, dtype=int))
    sub_dofs: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=int))   # wheel + roller dofs
    wheel_target: np.ndarray = field(default_factory=lambda: np.zeros(4))
    pi_integ: np.ndarray = field(default_factory=lambda: np.zeros(4))
    # commands
    cmd: RobotCmd = field(default_factory=RobotCmd)
    wd_armed: bool = False
    kick_ready: float = -math.inf
    dribbling: bool = False
    park: tuple[float, float] = (0.0, 0.0)


class MuJoCoWorld(World):
    """MuJoCo-backed world for routes a (``mujoco-velocity``) and b (``mujoco-rollers``)."""

    def __init__(self, route: str = "a", *, scene: Scene | None = None, n_blue: int = 6, n_yellow: int = 6,
                 params: dict[str, DofParam] | None = None, plant: str | Callable[[], Plant] = "fopdt",
                 field: FieldGeometry | str | Path | None = None, spec: RobotSpec | None = None,
                 ball: BallSpec | None = None, wheel: WheelGeometry | None = None,
                 solver: SolverOptions | None = None, route_a: RouteAOptions | None = None,
                 route_b: RouteBOptions | None = None, timestep: float | None = None,
                 n_rollers: int | None = None, wheel_control: str | None = None,
                 kv_slide: float | None = None, kv_hinge: float | None = None,
                 force_max: float | None = None, torque_max: float | None = None,
                 kv_wheel: float | None = None, wheel_torque_max: float | None = None,
                 pi_gains: PIGains | None = None, saturate: bool = False,
                 deadzone: bool | None = None, deadzone_wheel_rad_s: float | None = None,
                 watchdog_s: float | None = None, watchdog_clock: str | Callable[[], float] = "wall",
                 kick_cooldown_s: float = 0.1, dribbler_force_max: float = 1.0,
                 dribbler_stiffness: float = 40.0, dribbler_damping: float = 1.5,
                 dribbler_capture_dist: float = 0.16, dribbler_capture_half_angle: float = 0.6,
                 boundary: bool = True, chassis: str = "mesh",
                 limits_path: str | Path | None = None, twin_params_path: str | Path | None = None,
                 **unknown):
        if unknown:
            _log.warning("MuJoCoWorld: ignoring unknown options %s", sorted(unknown))
        self._mj = self._import_mujoco()
        self.route = normalize_route(route)
        self._lock = threading.RLock()
        # --- behavioral plant (route a) ------------------------------------------------
        self.plant_kind = plant if isinstance(plant, str) else "custom"
        self._plant_factory = self._make_factory(plant)
        self.params: dict[str, DofParam] | None = None
        if self.plant_kind == "fopdt":
            self.params = params or load_twin_params(twin_params_path)
        elif params is not None:
            self.params = params
        # --- geometry / limits -----------------------------------------------------------
        self._field = field if isinstance(field, FieldGeometry) else mjcf.load_field_geometry(field)
        self._spec = spec or mjcf.load_robot_spec(limits_path)
        self.ball_spec = ball or mjcf.load_ball_spec(limits_path)
        self.wheel = wheel or mjcf.load_wheel_geometry()
        if n_rollers is not None:
            self.wheel = replace(self.wheel, n_rollers=int(n_rollers))
        self.solver = solver or SolverOptions()
        if timestep is not None:
            self.solver = replace(self.solver, timestep=float(timestep))
        ra = route_a or RouteAOptions()
        for k, v in (("kv_slide", kv_slide), ("kv_hinge", kv_hinge), ("force_max", force_max),
                     ("torque_max", torque_max)):
            if v is not None:
                ra = replace(ra, **{k: float(v)})
        self.route_a = ra
        rb = route_b or RouteBOptions()
        if wheel_control is not None:
            rb = replace(rb, wheel_control=str(wheel_control))
        if kv_wheel is not None:
            rb = replace(rb, kv_wheel=float(kv_wheel))
        if wheel_torque_max is not None:
            rb = replace(rb, wheel_torque_max=float(wheel_torque_max))
        self.route_b = rb
        self.pi = pi_gains or PIGains()
        self.boundary = bool(boundary)
        self.chassis = chassis
        # --- command processing ----------------------------------------------------------
        self.saturate = bool(saturate)
        dz_enabled, dz_value = mjcf.load_deadzone(limits_path)
        self.deadzone = dz_enabled if deadzone is None else bool(deadzone)
        self.deadzone_wheel_rad_s = float(dz_value if deadzone_wheel_rad_s is None else deadzone_wheel_rad_s)
        self.watchdog_s = float(self._spec.watchdog_s if watchdog_s is None else watchdog_s)
        self.watchdog_clock = watchdog_clock
        self.kick_cooldown_s = float(kick_cooldown_s)
        self.dribbler_force_max = float(dribbler_force_max)
        self.dribbler_stiffness = float(dribbler_stiffness)
        self.dribbler_damping = float(dribbler_damping)
        self.dribbler_capture_dist = float(dribbler_capture_dist)
        self.dribbler_capture_half_angle = float(dribbler_capture_half_angle)
        self._ik = mjcf.ik_matrix(self.wheel)
        # --- state -----------------------------------------------------------------------
        self.model = None
        self.data = None
        self.xml: str = ""
        self.robots: dict[Key, _Robot] = {}
        self._ball_qadr = 0
        self._ball_dofadr = 0
        self._ball_body = 0
        self._chassis_geoms: set[int] = set()
        self._h_model = float(self.solver.timestep)
        self._gain_ref = None
        self._last_dt = self.ts
        self._viewer = None
        self.t = 0.0
        self.frame = 0
        self.watchdog_hits = 0
        self.kicks = 0
        self.contacts = 0
        self.reset(scene or Scene.default(n_blue, n_yellow, self._field.length, self._field.width))

    # ------------------------------------------------------------------ construction helpers
    @staticmethod
    def _import_mujoco():
        try:
            import mujoco
        except ImportError as e:  # pragma: no cover - exercised only without the extra
            raise ImportError("MuJoCoWorld needs the 'mujoco' package: pip install dtssl[mujoco]") from e
        return mujoco

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

    def build_xml(self, scene: Scene) -> str:
        """MJCF of ``scene`` with the current options (what ``reset`` compiles)."""
        return mjcf.build_world_xml(scene, self.route, fld=self._field, spec=self._spec, wheel=self.wheel,
                                    ball=self.ball_spec, solver=self.solver, route_a=self.route_a,
                                    route_b=self.route_b, boundary=self.boundary, chassis=self.chassis)

    # ------------------------------------------------------------------ World API
    @property
    def field(self) -> FieldGeometry:
        return self._field

    @property
    def spec(self) -> RobotSpec:
        return self._spec

    @property
    def name(self) -> str:
        return f"MuJoCoWorld[{'velocity' if self.route == 'a' else 'rollers'}]"

    @property
    def timestep(self) -> float:
        """Nominal physics substep (s); the effective one is ``dt / n_sub`` at each ``step``."""
        return self.solver.timestep

    def reset(self, scene: Scene) -> None:
        mj = self._mj
        with self._lock:
            spawns = []
            seen: set[Key] = set()
            for sp in scene.robots:
                key = (sp.team, int(sp.id))
                if key in seen:
                    _log.warning("MuJoCoWorld: duplicate robot %s ignored", key)
                    continue
                seen.add(key)
                spawns.append(sp)
            scene = Scene(robots=spawns, ball=scene.ball)
            self.xml = self.build_xml(scene)
            self.model = mj.MjModel.from_xml_string(self.xml)
            self.data = mj.MjData(self.model)
            m = self.model
            self.robots.clear()
            self._chassis_geoms.clear()
            jb = m.joint(BALL_JOINT)
            self._ball_qadr = int(jb.qposadr[0])
            self._ball_dofadr = int(jb.dofadr[0])
            self._ball_body = int(m.body(BALL_BODY).id)
            park_x0 = self._field.half_length + self._field.boundary_width + 0.6
            park_y = -(self._field.half_width + self._field.boundary_width + 0.6)
            for i, sp in enumerate(spawns):
                key = (sp.team, int(sp.id))
                name = robot_name(*key)
                rob = _Robot(key=key, name=name, present=bool(sp.present), body_id=int(m.body(name).id),
                             park=(park_x0 + 0.25 * i, park_y))
                self._chassis_geoms.add(int(m.geom(f"{name}_chassis").id))
                if self.route == "a":
                    for k, suf in enumerate(("x", "y", "yaw")):
                        j = m.joint(f"{name}_{suf}")
                        rob.qadr[k] = int(j.qposadr[0])
                        rob.dofadr[k] = int(j.dofadr[0])
                        rob.act[k] = int(m.actuator(f"{name}_act_{suf}").id)
                    rob.plant = self._new_plant(sp.x, sp.y, sp.theta)
                else:
                    j = m.joint(f"{name}_root")
                    rob.root_qadr = int(j.qposadr[0])
                    rob.root_dofadr = int(j.dofadr[0])
                    subs = []
                    for k in range(len(self.wheel.angles_deg)):
                        jw = m.joint(f"{name}_wheel{k}")
                        rob.wheel_qadr[k] = int(jw.qposadr[0])
                        rob.wheel_dofadr[k] = int(jw.dofadr[0])
                        rob.wheel_act[k] = int(m.actuator(f"{name}_act_wheel{k}").id)
                        subs.append(int(jw.dofadr[0]))
                        for r in range(self.wheel.n_rollers):
                            subs.append(int(m.joint(f"{name}_wheel{k}_roller{r}").dofadr[0]))
                    rob.sub_dofs = np.array(subs, dtype=int)
                self.robots[key] = rob
                if rob.present:
                    self._write_robot_pose(rob, sp.x, sp.y, sp.theta)
                else:
                    self._write_robot_pose(rob, rob.park[0], rob.park[1], 0.0)
            # route a: dead-beat gains are kv = m / h; remember the gain per unit 1/h to rescale on dt changes
            self._h_model = float(self.solver.timestep)
            self._gain_ref = np.array(m.actuator_gainprm[:, 0], dtype=float) if self.route == "a" else None
            b = scene.ball
            self._write_ball(b.x, b.y, b.vx, b.vy, b.z, b.vz)
            mj.mj_forward(self.model, self.data)
            self.t = 0.0
            self.frame = 0
            self.watchdog_hits = 0
            self.kicks = 0
            self.contacts = 0

    def set_command(self, team: Team, rid: int, cmd: RobotCmd) -> None:
        key = (team, int(rid))
        with self._lock:
            rob = self.robots.get(key)
            if rob is None:
                return
            c = replace(cmd)
            c.t_recv = self._clock()
            rob.cmd = c
            rob.wd_armed = True

    def step(self, dt: float | None = None) -> WorldState:
        mj = self._mj
        dt = self.ts if dt is None else float(dt)
        with self._lock:
            m, d = self.model, self.data
            n_sub = max(1, int(round(dt / self.solver.timestep)))
            h = dt / n_sub
            self._set_substep(h)
            now = self._clock()
            active: list[_Robot] = []
            for rob in self.robots.values():
                if not rob.present:
                    continue
                cmd = self._effective_cmd(rob, now)
                vx, vy, w = cmd.vx, cmd.vy, cmd.w
                if self.saturate:
                    vx, vy, w = self._saturate(vx, vy, w)
                if self.route == "a":
                    self._drive_route_a(rob, vx, vy, w, dt)
                else:
                    self._drive_route_b(rob, vx, vy, w)
                active.append(rob)
            self._ball_actions(active)
            d.xfrc_applied[self._ball_body, :] = 0.0
            for _ in range(n_sub):
                self._dribbler_forces(active)
                if self.route == "b" and self.route_b.wheel_control == "pi":
                    self._pi_torques(active, h)
                mj.mj_step(m, d)
            self._count_contacts()
            self._last_dt = dt
            self.t += dt
            self.frame += 1
            if self._viewer is not None:
                try:
                    self._viewer.sync()
                except Exception:  # pragma: no cover - viewer closed
                    self._viewer = None
            return self._state_locked()

    def state(self) -> WorldState:
        with self._lock:
            return self._state_locked()

    def teleport_robot(self, team: Team, rid: int, x: float, y: float, theta: float,
                       present: bool = True, vx: float = 0.0, vy: float = 0.0, w: float = 0.0) -> None:
        """Place a robot at ``(x, y, theta)`` with **world** velocity ``(vx, vy, w)``; the plant
        (route a) is re-created with the matching body velocity."""
        key = (team, int(rid))
        with self._lock:
            rob = self.robots.get(key)
            if rob is None:
                return
            rob.present = bool(present)
            if not present:
                x, y, theta, vx, vy, w = rob.park[0], rob.park[1], 0.0, 0.0, 0.0, 0.0
            self._write_robot_pose(rob, x, y, theta, vx, vy, w)
            if self.route == "a":
                c, s = math.cos(theta), math.sin(theta)
                rob.plant = self._new_plant(x, y, theta, (c * vx + s * vy, -s * vx + c * vy, w))
                self.data.ctrl[rob.act] = (vx, vy, w)
            else:
                rob.pi_integ[:] = 0.0
                self.data.ctrl[rob.wheel_act] = 0.0
            rob.dribbling = False
            self._mj.mj_forward(self.model, self.data)

    def set_present(self, team: Team, rid: int, present: bool) -> None:
        key = (team, int(rid))
        with self._lock:
            rob = self.robots.get(key)
            if rob is None or rob.present == bool(present):
                return
            if present:
                st = self._robot_pose(rob)
                self.teleport_robot(team, rid, st[0], st[1], st[2], present=True)
            else:
                self.teleport_robot(team, rid, 0.0, 0.0, 0.0, present=False)

    def is_present(self, team: Team, rid: int) -> bool:
        rob = self.robots.get((team, int(rid)))
        return bool(rob.present) if rob is not None else False

    def teleport_ball(self, x: float, y: float, vx: float = 0.0, vy: float = 0.0, z: float = 0.0,
                      vz: float = 0.0, rolling: bool = False) -> None:
        with self._lock:
            self._write_ball(x, y, vx, vy, z, vz, rolling)
            for rob in self.robots.values():
                rob.dribbling = False
            self._mj.mj_forward(self.model, self.data)

    def set_plant_params(self, params: dict[str, DofParam]) -> None:
        """Hot-swap theta (route a): parameters patched in place, delay buffers kept."""
        with self._lock:
            self.params = params
            for rob in self.robots.values():
                p = rob.plant
                if isinstance(p, AnalyticFOPDTPlant):
                    p.params = params
                    p.K = np.array([params[k].K for k in ("vx", "vy", "w")], dtype=float)
                    p.tau = np.array([params[k].tau for k in ("vx", "vy", "w")], dtype=float)
                    p.Td = np.array([params[k].Td for k in ("vx", "vy", "w")], dtype=float)
                elif p is not None and self.plant_kind == "fopdt":
                    new = self._plant_factory()
                    new.reset(p.pose, p.body_velocity)
                    new.prime_delay([])
                    rob.plant = new

    def close(self) -> None:
        v, self._viewer = self._viewer, None
        if v is not None:
            try:
                v.close()
            except Exception:  # pragma: no cover
                pass

    # ------------------------------------------------------------------ extras (GUI / bridge / tests)
    def robot_keys(self, present_only: bool = True) -> list[Key]:
        with self._lock:
            return [k for k in sorted(self.robots) if (self.robots[k].present or not present_only)]

    def has_ball(self, team: Team, rid: int) -> bool:
        with self._lock:
            rob = self.robots.get((team, int(rid)))
            return bool(rob is not None and rob.present and self._in_front(rob))

    def effective_command(self, team: Team, rid: int) -> RobotCmd:
        with self._lock:
            rob = self.robots.get((team, int(rid)))
            return replace(rob.cmd) if rob is not None else RobotCmd()

    def plant_pose(self, team: Team, rid: int) -> tuple[float, float, float] | None:
        """Free-running pose of the behavioral plant (route a, debugging; not the MuJoCo pose)."""
        rob = self.robots.get((team, int(rid)))
        return None if rob is None or rob.plant is None else tuple(float(v) for v in rob.plant.pose)

    def wheel_speeds(self, team: Team, rid: int) -> np.ndarray:
        """Route b: measured wheel angular speeds (rad/s); route a: IK of the body velocity."""
        with self._lock:
            rob = self.robots[(team, int(rid))]
            if self.route == "b":
                return np.array(self.data.qvel[rob.wheel_dofadr], dtype=float)
            st = self._state_locked().robots[rob.key]
            return self._ik @ np.array([st.vx_b, st.vy_b, st.w])

    def viewer(self):
        """Launch ``mujoco.viewer.launch_passive`` on the live model; ``step`` syncs it."""
        import mujoco.viewer  # noqa: WPS433 (lazy)

        with self._lock:
            if self._viewer is None:
                self._viewer = mujoco.viewer.launch_passive(self.model, self.data)
            return self._viewer

    def substeps(self, dt: float | None = None) -> int:
        dt = self.ts if dt is None else float(dt)
        return max(1, int(round(dt / self.solver.timestep)))

    # ------------------------------------------------------------------ internals: integration
    def _set_substep(self, h: float) -> None:
        """Set ``model.opt.timestep = h``; route a rescales its dead-beat servo gains (kv = m / h)
        so that the velocity target is reached in exactly one substep for any ``dt``."""
        m = self.model
        if abs(h - m.opt.timestep) < 1e-15:
            return
        m.opt.timestep = h
        if self._gain_ref is not None and self.route_a.kv_slide is None and self.route_a.kv_hinge is None:
            scale = self._h_model / h
            m.actuator_gainprm[:, 0] = self._gain_ref * scale
            m.actuator_biasprm[:, 2] = -self._gain_ref * scale

    # ------------------------------------------------------------------ internals: commands
    def _effective_cmd(self, rob: _Robot, now: float) -> RobotCmd:
        cmd = rob.cmd
        if self.watchdog_s > 0.0 and rob.wd_armed and now - cmd.t_recv > self.watchdog_s:
            cmd = RobotCmd(t_recv=cmd.t_recv)
            rob.cmd = cmd
            rob.wd_armed = False
            self.watchdog_hits += 1
        return cmd

    def _saturate(self, vx: float, vy: float, w: float) -> tuple[float, float, float]:
        v = math.hypot(vx, vy)
        if self._spec.v_max > 0.0 and v > self._spec.v_max:
            k = self._spec.v_max / v
            vx, vy = vx * k, vy * k
        if self._spec.w_max > 0.0:
            w = min(max(w, -self._spec.w_max), self._spec.w_max)
        return vx, vy, w

    def _drive_route_a(self, rob: _Robot, vx: float, vy: float, w: float, dt: float) -> None:
        """Advance the plant; command the servo with the interval-mean world velocity."""
        d = self.data
        plant = rob.plant
        if self.deadzone:
            vx, vy, w = self._body_deadzone(vx, vy, w)
        vb0 = np.asarray(plant.body_velocity, dtype=float)
        th0 = float(d.qpos[rob.qadr[2]])
        plant.step((vx, vy, w), dt)
        vb1 = np.asarray(plant.body_velocity, dtype=float)
        w_mean = 0.5 * (vb0[2] + vb1[2])
        th1 = th0 + dt * w_mean
        c0, s0 = math.cos(th0), math.sin(th0)
        c1, s1 = math.cos(th1), math.sin(th1)
        gx = 0.5 * ((c0 * vb0[0] - s0 * vb0[1]) + (c1 * vb1[0] - s1 * vb1[1]))
        gy = 0.5 * ((s0 * vb0[0] + c0 * vb0[1]) + (s1 * vb1[0] + c1 * vb1[1]))
        d.ctrl[rob.act] = (gx, gy, w_mean)

    def _body_deadzone(self, vx: float, vy: float, w: float) -> tuple[float, float, float]:
        wheels = self._ik @ np.array([vx, vy, w], dtype=float)
        mask = np.abs(wheels) < self.deadzone_wheel_rad_s
        if not mask.any():
            return vx, vy, w
        wheels[mask] = 0.0
        v = np.linalg.pinv(self._ik) @ wheels
        return float(v[0]), float(v[1]), float(v[2])

    def _drive_route_b(self, rob: _Robot, vx: float, vy: float, w: float) -> None:
        wheels = self._ik @ np.array([vx, vy, w], dtype=float)
        if self.deadzone and self.deadzone_wheel_rad_s > 0.0:
            wheels[np.abs(wheels) < self.deadzone_wheel_rad_s] = 0.0
        rob.wheel_target[:] = wheels
        if self.route_b.wheel_control != "pi":
            self.data.ctrl[rob.wheel_act] = wheels

    def _pi_torques(self, active: list[_Robot], h: float) -> None:
        d = self.data
        g = self.pi
        tmax = self.route_b.pi_torque_max
        scale = tmax / g.pwm_max
        for rob in active:
            err = rob.wheel_target - d.qvel[rob.wheel_dofadr]
            rob.pi_integ += err * h
            np.clip(rob.pi_integ, -g.integrator_limit / max(g.ki, 1e-12), g.integrator_limit / max(g.ki, 1e-12),
                    out=rob.pi_integ)
            u = g.kp * err + g.ki * rob.pi_integ
            d.ctrl[rob.wheel_act] = np.clip(u * scale, -tmax, tmax)

    # ------------------------------------------------------------------ internals: ball
    def _ball_actions(self, active: list[_Robot]) -> None:
        """Kick (consumed once, cooldown) and dribbler engagement, before the substeps."""
        spec = self._spec
        d = self.data
        bx, by, bz = (float(v) for v in d.qpos[self._ball_qadr:self._ball_qadr + 3])
        bz_floor = bz - self.ball_spec.radius
        for rob in active:
            cmd = rob.cmd
            x, y, th = self._robot_pose(rob)
            in_front = _ball_in_front(bx, by, bz_floor, x, y, th, spec.ball_contact_dist, spec.dribbler_half_angle)
            rob.dribbling = False
            if in_front and cmd.kick_speed > 0.0 and self.t >= rob.kick_ready:
                chip = cmd.kick_angle_deg > 0.0
                speed = min(cmd.kick_speed, spec.kick_chip_max if chip else spec.kick_flat_max)
                ang = math.radians(spec.chip_angle_deg if chip else 0.0)
                vel = d.qvel[self._ball_dofadr:self._ball_dofadr + 6]
                vel[0] = speed * math.cos(ang) * math.cos(th)
                vel[1] = speed * math.cos(ang) * math.sin(th)
                vel[2] = speed * math.sin(ang)
                vel[3:6] = 0.0
                rob.kick_ready = self.t + self.kick_cooldown_s
                self.kicks += 1
                cmd.kick_speed = 0.0                      # consumed once
                continue
            if cmd.dribbler_rpm > 0.0 and bz_floor < 0.02:
                dx, dy = bx - x, by - y
                ang = math.atan2(dy, dx) - th
                ang = math.atan2(math.sin(ang), math.cos(ang))
                if math.hypot(dx, dy) <= self.dribbler_capture_dist and abs(ang) <= self.dribbler_capture_half_angle:
                    rob.dribbling = True

    def _dribbler_forces(self, active: list[_Robot]) -> None:
        """Spring-damper pulling the ball to the dribbler pocket (``xfrc_applied`` on the ball)."""
        d = self.data
        f = d.xfrc_applied[self._ball_body]
        f[:] = 0.0
        holders = [r for r in active if r.dribbling]
        if not holders:
            return
        spec = self._spec
        bx, by = (float(v) for v in d.qpos[self._ball_qadr:self._ball_qadr + 2])
        bvx, bvy = (float(v) for v in d.qvel[self._ball_dofadr:self._ball_dofadr + 2])
        dist = spec.dribbler_offset + self.ball_spec.radius
        for rob in holders:
            x, y, th = self._robot_pose(rob)
            vxw, vyw, w = self._robot_world_velocity(rob)
            c, s = math.cos(th), math.sin(th)
            px, py = x + dist * c, y + dist * s
            pvx, pvy = vxw - w * dist * s, vyw + w * dist * c           # velocity of the pocket point
            frac = min(max(rob.cmd.dribbler_rpm / max(spec.dribbler_rpm_max, 1e-9), 0.0), 1.0)
            fx = self.dribbler_stiffness * (px - bx) - self.dribbler_damping * (bvx - pvx)
            fy = self.dribbler_stiffness * (py - by) - self.dribbler_damping * (bvy - pvy)
            mag = math.hypot(fx, fy)
            fmax = self.dribbler_force_max * (0.25 + 0.75 * frac)
            if mag > fmax:
                fx, fy = fx * fmax / mag, fy * fmax / mag
            f[0] += fx
            f[1] += fy

    def _write_ball(self, x: float, y: float, vx: float, vy: float, z: float, vz: float,
                    rolling: bool = False) -> None:
        d = self.data
        r = self.ball_spec.radius
        q = self._ball_qadr
        d.qpos[q:q + 7] = (x, y, max(z, 0.0) + r, 1.0, 0.0, 0.0, 0.0)
        v = self._ball_dofadr
        d.qvel[v:v + 6] = (vx, vy, vz, 0.0, 0.0, 0.0)
        if rolling:  # spin consistent with rolling without slip: omega = z_hat x v / r
            d.qvel[v + 3] = -vy / r
            d.qvel[v + 4] = vx / r
        d.qacc[:] = 0.0

    # ------------------------------------------------------------------ internals: robots
    def _write_robot_pose(self, rob: _Robot, x: float, y: float, theta: float,
                          vx: float = 0.0, vy: float = 0.0, w: float = 0.0) -> None:
        d = self.data
        if self.route == "a":
            d.qpos[rob.qadr] = (x, y, theta)
            d.qvel[rob.dofadr] = (vx, vy, w)
        else:
            q = rob.root_qadr
            d.qpos[q:q + 7] = (x, y, 0.0005, *mjcf.yaw_quat(theta))
            v = rob.root_dofadr
            d.qvel[v:v + 6] = (vx, vy, 0.0, 0.0, 0.0, w)
            d.qvel[rob.sub_dofs] = 0.0

    def _robot_pose(self, rob: _Robot) -> tuple[float, float, float]:
        d = self.data
        if self.route == "a":
            x, y, th = d.qpos[rob.qadr]
            return float(x), float(y), float(th)
        q = rob.root_qadr
        return float(d.qpos[q]), float(d.qpos[q + 1]), quat_yaw(d.qpos[q + 3:q + 7])

    def _robot_world_velocity(self, rob: _Robot) -> tuple[float, float, float]:
        d = self.data
        if self.route == "a":
            vx, vy, w = d.qvel[rob.dofadr]
            return float(vx), float(vy), float(w)
        v = rob.root_dofadr
        return float(d.qvel[v]), float(d.qvel[v + 1]), float(d.qvel[v + 5])   # angular z (body frame ~ world z)

    def _in_front(self, rob: _Robot) -> bool:
        d = self.data
        bx, by, bz = (float(v) for v in d.qpos[self._ball_qadr:self._ball_qadr + 3])
        x, y, th = self._robot_pose(rob)
        return _ball_in_front(bx, by, bz - self.ball_spec.radius, x, y, th, self._spec.ball_contact_dist,
                              self._spec.dribbler_half_angle)

    def _count_contacts(self) -> None:
        d = self.data
        if d.ncon == 0:
            return
        g1 = d.contact.geom1[:d.ncon]
        g2 = d.contact.geom2[:d.ncon]
        n = sum(1 for a, b in zip(g1, g2, strict=True) if (int(a) in self._chassis_geoms or int(b) in self._chassis_geoms))
        self.contacts += int(n)

    def _state_locked(self) -> WorldState:
        d = self.data
        robots: dict[Key, RobotState] = {}
        for key, rob in self.robots.items():
            x, y, th = self._robot_pose(rob)
            vxw, vyw, w = self._robot_world_velocity(rob)
            # route a holds the interval-mean world velocity (ZOH of the plant's trapezoid): the body
            # velocity it represents is the one at the mid-interval heading
            th_v = th - 0.5 * self._last_dt * w if self.route == "a" else th
            c, s = math.cos(th_v), math.sin(th_v)
            robots[key] = RobotState(team=key[0], id=key[1], x=x, y=y, theta=wrap_to_pi(th),
                                     vx_b=c * vxw + s * vyw, vy_b=-s * vxw + c * vyw, w=w,
                                     has_ball=bool(rob.present and self._in_front(rob)), present=rob.present)
        q, v = self._ball_qadr, self._ball_dofadr
        bx, by, bz = (float(u) for u in d.qpos[q:q + 3])
        bvx, bvy, bvz = (float(u) for u in d.qvel[v:v + 3])
        wx, wy = float(d.qvel[v + 3]), float(d.qvel[v + 4])
        r = self.ball_spec.radius
        speed = math.hypot(bvx, bvy)
        slip = math.hypot(bvx - wy * r, bvy + wx * r)      # contact-point velocity for a rolling sphere
        rolling = speed < 1e-3 or slip < 0.1 * speed
        ball = BallState(x=bx, y=by, z=max(bz - r, 0.0), vx=bvx, vy=bvy, vz=bvz, rolling=rolling)
        return WorldState(t=self.t, frame=self.frame, robots=robots, ball=ball)


__all__ = ["MuJoCoWorld", "PIGains", "quat_yaw"]
