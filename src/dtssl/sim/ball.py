"""Analytic SSL ball: two-phase deceleration, flat/chip kicks, floor and wall bounces.

Model (docs/SPEC_DTSSL.md §3, ER-Force 2016 TDP "straight two-phase"): after a kick with
speed ``v0`` the ball *slides* with deceleration ``sliding_decel`` until its speed drops to
``k * v0`` (``k = sliding_to_rolling_speed_ratio``, 0.6), then *rolls* with deceleration
``rolling_decel`` until it stops. Everything is integrated **exactly** inside each substep
(piecewise constant deceleration, event times solved analytically), so the stopping distance
is the closed form ``(v0^2 - vs^2) / (2 a_s) + vs^2 / (2 a_r)`` up to floating point.

Chip kicks are ballistic (``g = 9.81``): no horizontal deceleration while airborne, floor
bounce with ``restitution_floor`` on the vertical velocity, settling when the rebound is
below ``settle_vz``; the horizontal velocity is kept (no xy loss per hop), after which the
ground two-phase model restarts from the landing speed.

Walls: the arena boundary is at ``field/2 + boundary_width`` on each side; the ball is
reflected (normal component scaled by ``restitution_wall``) regardless of its height.

Units: SI (m, s). ``BallState.z`` is the height of the ball's *bottom* above the floor
(0 on the ground), as declared in :mod:`dtssl.sim.entities`.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, replace
from pathlib import Path

from dtssl.sim.entities import BallState

G_DEFAULT = 9.81


@dataclass(frozen=True)
class BallParams:
    """Ball model constants (``config/robot_limits.json: ball``)."""

    radius: float = 0.0215
    mass: float = 0.046
    sliding_decel: float = 1.82135          # m/s^2 (positive magnitude)
    rolling_decel: float = 0.3025           # m/s^2
    sliding_to_rolling_speed_ratio: float = 0.6
    restitution_floor: float = 0.5
    restitution_wall: float = 0.6
    restitution_robot: float = 0.5
    g: float = G_DEFAULT
    settle_vz: float = 0.05                 # m/s: rebounds slower than this settle on the floor

    @staticmethod
    def from_config(path: str | Path | None = None) -> BallParams:
        from dtssl.paths import config_path

        p = Path(path) if path else config_path("robot_limits.json")
        with open(p, encoding="utf-8") as f:
            cfg = json.load(f)
        d = cfg.get("ball", {})
        known = {k: v for k, v in d.items() if k in BallParams.__dataclass_fields__ and not k.startswith("_")}
        return BallParams(**known)

    @staticmethod
    def from_dict(d: dict) -> BallParams:
        known = {k: v for k, v in d.items() if k in BallParams.__dataclass_fields__}
        return BallParams(**known)


@dataclass(frozen=True)
class Walls:
    """Axis-aligned arena limits for the ball *centre* (already reduced by the ball radius)."""

    x_max: float
    y_max: float

    @staticmethod
    def from_field(field, ball_radius: float) -> Walls:
        return Walls(x_max=field.half_length + field.boundary_width - ball_radius,
                     y_max=field.half_width + field.boundary_width - ball_radius)


def stopping_distance(v0: float, params: BallParams) -> float:
    """Closed-form travel distance of a ball kicked flat at ``v0`` (two-phase model)."""
    v0 = abs(float(v0))
    vs = params.sliding_to_rolling_speed_ratio * v0
    return (v0 * v0 - vs * vs) / (2.0 * params.sliding_decel) + vs * vs / (2.0 * params.rolling_decel)


def stopping_time(v0: float, params: BallParams) -> float:
    v0 = abs(float(v0))
    vs = params.sliding_to_rolling_speed_ratio * v0
    return (v0 - vs) / params.sliding_decel + vs / params.rolling_decel


class Ball:
    """Analytic ball with an explicit :class:`BallState` and the two-phase bookkeeping."""

    def __init__(self, params: BallParams | None = None, state: BallState | None = None):
        self.params = params or BallParams()
        self.state = replace(state) if state is not None else BallState()
        self.v_switch = 0.0            # sliding -> rolling threshold (k * launch speed)
        self.captured_by: tuple[str, int] | None = None   # dribbler that holds the ball
        self.bounces = 0               # floor bounces since the last chip (diagnostics)
        if not self.state.rolling:
            self.v_switch = self.params.sliding_to_rolling_speed_ratio * self.speed()

    # ------------------------------------------------------------------ state helpers
    @property
    def radius(self) -> float:
        return self.params.radius

    def speed(self) -> float:
        return math.hypot(self.state.vx, self.state.vy)

    @property
    def airborne(self) -> bool:
        return self.state.z > 0.0 or self.state.vz > 0.0

    def set(self, x: float, y: float, vx: float = 0.0, vy: float = 0.0, z: float = 0.0,
            vz: float = 0.0, rolling: bool = False) -> None:
        """Teleport: place the ball and (re)start the deceleration phase.

        ``rolling=False`` (default) starts the sliding phase from the given speed, like a
        kick; ``rolling=True`` starts directly in the rolling phase (``TeleportBall.roll``).
        """
        self.state = BallState(x=float(x), y=float(y), z=max(0.0, float(z)),
                               vx=float(vx), vy=float(vy), vz=float(vz), rolling=bool(rolling))
        self.captured_by = None
        self.bounces = 0
        self.v_switch = 0.0 if rolling else self.params.sliding_to_rolling_speed_ratio * self.speed()

    def set_velocity(self, vx: float, vy: float, rolling: bool = False) -> None:
        self.state.vx, self.state.vy = float(vx), float(vy)
        self.state.rolling = bool(rolling)
        self.v_switch = 0.0 if rolling else self.params.sliding_to_rolling_speed_ratio * self.speed()

    def kick(self, speed: float, heading: float, chip: bool = False,
             chip_angle_deg: float = 45.0) -> None:
        """Impulse along ``heading`` (rad, world frame). ``speed`` is the absolute launch speed.

        Flat: horizontal velocity = speed along the heading; sliding phase restarts.
        Chip: the launch vector is tilted by ``chip_angle_deg`` above the floor.
        """
        speed = max(0.0, float(speed))
        c, s = math.cos(heading), math.sin(heading)
        self.captured_by = None
        self.bounces = 0
        if chip and speed > 0.0:
            ang = math.radians(chip_angle_deg)
            vh = speed * math.cos(ang)
            self.state.vx, self.state.vy = vh * c, vh * s
            self.state.vz = speed * math.sin(ang)
            self.state.z = 0.0
            self.state.rolling = False
            self.v_switch = self.params.sliding_to_rolling_speed_ratio * vh
        else:
            self.state.vx, self.state.vy = speed * c, speed * s
            self.state.vz = 0.0
            self.state.z = 0.0
            self.state.rolling = False
            self.v_switch = self.params.sliding_to_rolling_speed_ratio * speed

    # ------------------------------------------------------------------ integration
    def step(self, dt: float, walls: Walls | None = None) -> None:
        """Advance one substep (exact piecewise integration) and apply wall bounces."""
        if dt <= 0.0 or self.captured_by is not None:
            return
        if self.airborne:
            self._advance_air(dt)
        else:
            self._advance_ground(dt)
        if walls is not None:
            self._bounce_walls(walls)

    def _advance_ground(self, dt: float) -> None:
        st = self.state
        p = self.params
        v = math.hypot(st.vx, st.vy)
        if v <= 0.0:
            st.vx = st.vy = 0.0
            return
        ux, uy = st.vx / v, st.vy / v
        remaining = dt
        while remaining > 0.0 and v > 0.0:
            if not st.rolling and v <= self.v_switch:
                st.rolling = True
            if st.rolling:
                a, v_event = p.rolling_decel, 0.0
            else:
                a, v_event = p.sliding_decel, self.v_switch
            if a <= 0.0:                                   # frictionless: uniform motion
                st.x += ux * v * remaining
                st.y += uy * v * remaining
                remaining = 0.0
                break
            t_event = (v - v_event) / a
            if t_event <= remaining:                       # phase switch / stop inside the substep
                s = v * t_event - 0.5 * a * t_event * t_event
                st.x += ux * s
                st.y += uy * s
                remaining -= t_event
                v = v_event
                if st.rolling:                             # stopped
                    v = 0.0
                    break
                st.rolling = True
            else:
                s = v * remaining - 0.5 * a * remaining * remaining
                st.x += ux * s
                st.y += uy * s
                v -= a * remaining
                remaining = 0.0
        st.vx, st.vy = ux * v, uy * v
        if v <= 0.0:
            st.vx = st.vy = 0.0

    def _advance_air(self, dt: float) -> None:
        st = self.state
        p = self.params
        remaining = dt
        while remaining > 0.0:
            g = p.g
            # time to touch the floor from (z, vz): z + vz t - g t^2 / 2 = 0, positive root
            disc = st.vz * st.vz + 2.0 * g * st.z
            t_hit = (st.vz + math.sqrt(max(disc, 0.0))) / g if g > 0.0 else math.inf
            if t_hit > remaining:
                st.x += st.vx * remaining
                st.y += st.vy * remaining
                st.z = st.z + st.vz * remaining - 0.5 * g * remaining * remaining
                st.vz -= g * remaining
                remaining = 0.0
                break
            # impact inside the substep
            st.x += st.vx * t_hit
            st.y += st.vy * t_hit
            vz_impact = st.vz - g * t_hit
            remaining -= t_hit
            st.z = 0.0
            vz_after = -p.restitution_floor * vz_impact
            self.bounces += 1
            if vz_after < p.settle_vz:
                st.vz = 0.0
                st.rolling = False
                self.v_switch = p.sliding_to_rolling_speed_ratio * math.hypot(st.vx, st.vy)
                if remaining > 0.0:
                    self._advance_ground(remaining)
                return
            st.vz = vz_after
        if st.z < 0.0:
            st.z = 0.0

    def _bounce_walls(self, walls: Walls) -> None:
        st = self.state
        e = self.params.restitution_wall
        if st.x > walls.x_max:
            st.x = 2.0 * walls.x_max - st.x
            if st.vx > 0.0:
                st.vx = -e * st.vx
        elif st.x < -walls.x_max:
            st.x = -2.0 * walls.x_max - st.x
            if st.vx < 0.0:
                st.vx = -e * st.vx
        if st.y > walls.y_max:
            st.y = 2.0 * walls.y_max - st.y
            if st.vy > 0.0:
                st.vy = -e * st.vy
        elif st.y < -walls.y_max:
            st.y = -2.0 * walls.y_max - st.y
            if st.vy < 0.0:
                st.vy = -e * st.vy
        # clamp (very fast balls could still overshoot with a single reflection)
        st.x = min(max(st.x, -walls.x_max), walls.x_max)
        st.y = min(max(st.y, -walls.y_max), walls.y_max)

    # ------------------------------------------------------------------ contacts
    def reflect(self, nx: float, ny: float, surface_vx: float = 0.0, surface_vy: float = 0.0,
                restitution: float | None = None) -> bool:
        """Reflect the velocity on a surface with outward normal ``(nx, ny)`` moving at
        ``surface_v``. Only applied when the ball approaches the surface; returns True then."""
        e = self.params.restitution_robot if restitution is None else restitution
        st = self.state
        rvx, rvy = st.vx - surface_vx, st.vy - surface_vy
        vn = rvx * nx + rvy * ny
        if vn >= 0.0:
            return False
        st.vx -= (1.0 + e) * vn * nx
        st.vy -= (1.0 + e) * vn * ny
        # a contact restarts the sliding phase from the new speed
        st.rolling = False
        self.v_switch = self.params.sliding_to_rolling_speed_ratio * math.hypot(st.vx, st.vy)
        return True

    def copy_state(self) -> BallState:
        return replace(self.state)
