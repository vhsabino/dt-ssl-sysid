"""``WorldPlant``: run a :class:`dtssl.sim.world.World` backend through the free-run harness.

The harness (:mod:`dtssl.sim.rollout`) only knows the :class:`dtssl.models.Plant` interface
(``reset`` -> ``prime_delay`` -> ``step``). This adapter wraps a **single-robot** world backend so
that the MuJoCo routes can be evaluated on the same re-anchored windows, horizons and metric as
the analytic plants (paper harness, ``dtssl replay`` / ``dtssl analysis run backends_holdout``)::

    plant = WorldPlant("mujoco-velocity")                 # route a: FOPDT plant drives the chassis
    plant = WorldPlant("mujoco-rollers")                  # route b: physical omni wheels, no delay
    plant = WorldPlant("mujoco-rollers", delay="theta")   # route b + identified per-DOF transport delay
    ro = rollout_segment(seg, plant)                      # exactly like AnalyticFOPDTPlant

Semantics per window (the harness invariant holds: nothing after t0 is read):

* ``reset(pose0, velb0)`` -> :meth:`MuJoCoWorld.set_robot_state`: chassis at the true pose with the
  true body velocity (route b also spins the wheels consistently, rollers at rest); the ball is
  parked far away and the field walls are off, so contacts never enter the comparison.
* ``prime_delay(prev)`` -> route a: the embedded ``AnalyticFOPDTPlant`` buffer (same tap as the
  analytic plant, ``ud[j] = u[j - ceil(Td/dt)]``); route b with ``delay="theta"``: the same tap
  applied by this adapter to the command stream before the physical model; ``delay=None``: no-op.
* ``step(cmd, dt)`` -> ``set_command`` + ``World.step(dt)``; the pose comes from MuJoCo.

Any backend registered in :mod:`dtssl.sim.backends` works (``fopdt`` and ``ideal`` too, which is
what the tests use to check the wiring against the analytic plants).
"""
from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from dtssl.models import DofParam, Plant, load_twin_params
from dtssl.models.base import Pose, Vel
from dtssl.sim.entities import RobotCmd
from dtssl.sim.world import World

__all__ = ["WorldPlant", "BACKEND_PLANTS", "make_harness_plant"]

_FAR = (-40.0, -40.0)          # ball parking spot (m), well outside any field


class WorldPlant(Plant):
    """Single-robot :class:`World` seen as a harness :class:`Plant` (see module docstring)."""

    def __init__(self, backend: str = "mujoco-velocity", *, params: dict[str, DofParam] | None = None,
                 delay: str | None = "auto", team: str = "blue", world_opts: dict | None = None):
        from dtssl.sim.backends import make_world

        self.backend = str(backend)
        self.key = (team, 0)
        opts = dict(n_blue=1 if team == "blue" else 0, n_yellow=1 if team == "yellow" else 0,
                    watchdog_clock="sim")
        if self.backend.startswith("mujoco"):
            opts["boundary"] = False
        if params is not None:
            opts["params"] = params
        opts.update(world_opts or {})
        self.world: World = make_world(self.backend, **opts)
        self._theta = params if params is not None else load_twin_params()
        route_b = self.backend == "mujoco-rollers"
        if delay == "auto":
            delay = None if route_b else "builtin"
        if delay not in (None, "theta", "builtin"):
            raise ValueError(f"delay must be None | 'theta' | 'builtin' | 'auto', got {delay!r}")
        self.delay = delay
        # the per-DOF transport delay is applied here only for route b + 'theta'
        self._own_delay = bool(route_b and delay == "theta")
        self._Td = np.array([self._theta[d].Td for d in ("vx", "vy", "w")], dtype=float)
        self._hist: list[np.ndarray] = []
        self._base = 0
        self._k = 0
        self.x = self.y = self.th = 0.0
        self._vbody = np.zeros(3)
        try:
            self.world.teleport_ball(*_FAR)
        except Exception:  # noqa: BLE001 - backends without a ball
            pass

    # ------------------------------------------------------------------ harness interface
    @property
    def params(self) -> dict[str, DofParam] | None:
        """theta seen by the harness (window grid / max delay): the world's theta for route a and
        for route b with the identified delay; None when the physical model runs undelayed."""
        if self.backend == "mujoco-rollers" and not self._own_delay:
            return None
        return self._theta

    def reset(self, pose0: Pose, velb0: Vel = (0.0, 0.0, 0.0)) -> None:
        x, y, th = (float(v) for v in pose0)
        vb = tuple(float(v) for v in velb0)
        w = self.world
        if hasattr(w, "set_robot_state"):
            w.set_robot_state(*self.key, x, y, th, *vb)
        else:                                   # TwinWorld and friends: world-frame teleport
            c, s = math.cos(th), math.sin(th)
            w.teleport_robot(*self.key, x, y, th, vx=c * vb[0] - s * vb[1], vy=s * vb[0] + c * vb[1], w=vb[2])
        self.x, self.y, self.th = x, y, th
        self._vbody = np.asarray(vb, dtype=float)
        self._hist, self._base, self._k = [], 0, 0

    def prime_delay(self, prev_cmds) -> None:
        prev = [np.asarray(c, dtype=float).reshape(3) for c in prev_cmds]
        if self._own_delay:
            self._hist, self._base = prev, len(prev)
        elif hasattr(self.world, "prime_robot_delay"):
            self.world.prime_robot_delay(*self.key, prev)
        elif hasattr(self.world, "prime_delay"):
            self.world.prime_delay(*self.key, prev)

    def _delayed(self, cmd: np.ndarray, dt: float) -> np.ndarray:
        """Same tap as AnalyticFOPDTPlant: ud[j] = u[j - ceil(Td/dt)] (0 before the start)."""
        j = self._k
        self._hist.append(cmd)
        ud = np.zeros(3)
        for i in range(3):
            src = j if self._Td[i] <= 0.0 else int(math.floor(j - self._Td[i] / dt + 1e-9))
            pos = src + self._base
            if 0 <= pos < len(self._hist):
                ud[i] = self._hist[pos][i]
        self._k = j + 1
        return ud

    def step(self, cmd: Vel, dt: float) -> Pose:
        u = np.asarray(cmd, dtype=float).reshape(3)
        if self._own_delay:
            u = self._delayed(u, dt)
        self.world.set_command(*self.key, RobotCmd(vx=float(u[0]), vy=float(u[1]), w=float(u[2])))
        ws = self.world.step(dt)
        r = ws.robots[self.key]
        if hasattr(self.world, "robot_pose"):
            x, y, th = self.world.robot_pose(*self.key)       # unwrapped where the backend allows it
        else:
            x, y, th = r.x, r.y, r.theta
        # keep theta continuous across the (-pi, pi] wrap of quaternion yaws (route b); backends that
        # already report an unwrapped angle (route a hinge, TwinWorld plant) pass through untouched
        if abs(th - self.th) > math.pi:
            th = self.th + math.atan2(math.sin(th - self.th), math.cos(th - self.th))
        self.x, self.y, self.th = float(x), float(y), float(th)
        self._vbody = np.array([r.vx_b, r.vy_b, r.w], dtype=float)
        return (self.x, self.y, self.th)

    def close(self) -> None:
        try:
            self.world.close()
        except Exception:  # noqa: BLE001
            pass


BACKEND_PLANTS: dict[str, tuple[str, str | None]] = {
    "mujoco-velocity": ("mujoco-velocity", "auto"),
    "mujoco-rollers": ("mujoco-rollers", None),
    "mujoco-rollers-delay": ("mujoco-rollers", "theta"),
}


def make_harness_plant(name: str, params: dict[str, DofParam] | None = None, **world_opts) -> Plant:
    """``fopdt`` / ``ideal`` -> analytic plants; ``mujoco-velocity`` / ``mujoco-rollers`` /
    ``mujoco-rollers-delay`` -> :class:`WorldPlant`; ``world:<backend>`` -> any registered backend;
    ``proto:<sim>`` / ``proto:<sim>+delay`` -> an external simulator of ``config/external_sims.json`` over the
    ssl-simulation-protocol (``dtssl.sim.protocol_plant``), raw or with the identified Td on the commands."""
    from dtssl.models import AnalyticFOPDTPlant, IdealKinematicPlant

    if name == "fopdt":
        return AnalyticFOPDTPlant(params or load_twin_params())
    if name == "ideal":
        return IdealKinematicPlant()
    if name in BACKEND_PLANTS:
        backend, delay = BACKEND_PLANTS[name]
        return WorldPlant(backend, params=params, delay=delay, world_opts=world_opts or None)
    if name.startswith("world:"):
        return WorldPlant(name[len("world:"):], params=params, world_opts=world_opts or None)
    if name.startswith("proto:"):        # external simulator over the ssl-simulation-protocol (C2b)
        from dtssl.sim.protocol_plant import ProtocolPlant

        sim, _, tag = name[len("proto:"):].partition("+")
        return ProtocolPlant(sim, delay="theta" if tag == "delay" else None, params=params, **world_opts)
    raise KeyError(f"unknown plant {name!r}; choose fopdt | ideal | {' | '.join(BACKEND_PLANTS)} | world:<backend> "
                   "| proto:<sim>[+delay]")


def plant_names() -> Sequence[str]:
    return ("fopdt", "ideal", *BACKEND_PLANTS)
