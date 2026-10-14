"""World interface: multi-robot twin (robots + ball + field) stepped on the 1/60 s grid.

Concrete backends: ``dtssl.sim.twin_world.TwinWorld`` (behavioral plant per robot, analytic
ball/collisions) and ``dtssl.physics.mujoco_world.MuJoCoWorld`` (routes a/b). Both are created
through ``dtssl.sim.backends.make_world``.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from dtssl.sim.entities import BallState, RobotCmd, RobotState, Scene, Team, WorldState


@dataclass(frozen=True)
class FieldGeometry:
    """SSL field geometry in metres (loaded from config/field_divB.json, which is in mm)."""

    length: float = 9.0
    width: float = 6.0
    goal_width: float = 1.0
    goal_depth: float = 0.18
    boundary_width: float = 0.3
    penalty_area_depth: float = 1.0
    penalty_area_width: float = 2.0
    goal_center_to_penalty_mark: float = 6.0
    center_circle_radius: float = 0.5
    line_thickness: float = 0.01

    @property
    def half_length(self) -> float:
        return self.length / 2.0

    @property
    def half_width(self) -> float:
        return self.width / 2.0

    def to_mm(self) -> dict[str, int]:
        return {k: int(round(getattr(self, k) * 1000.0)) for k in self.__dataclass_fields__}

    @staticmethod
    def from_mm(d: dict) -> FieldGeometry:
        keys = FieldGeometry.__dataclass_fields__
        return FieldGeometry(**{k: float(d[k]) / 1000.0 for k in keys if k in d})


@dataclass
class RobotSpec:
    """Body geometry / actuation limits shared by all backends (from config/robot_limits.json)."""

    radius: float = 0.09
    height: float = 0.15
    mass: float = 2.4
    dribbler_offset: float = 0.075       # centre -> dribbler face (m)
    dribbler_half_angle: float = 0.31    # rad, ball-in-dribbler acceptance
    ball_contact_dist: float = 0.11      # centre -> ball centre max for has_ball
    v_max: float = 3.0                   # m/s (SLDD sat_v)
    w_max: float = 10.0                  # rad/s (SLDD sat_w)
    a_max: float | None = None           # m/s^2, None = unlimited (behavioral plant has none)
    kick_flat_max: float = 6.5
    kick_chip_max: float = 6.0
    chip_angle_deg: float = 45.0
    dribbler_rpm_max: float = 6000.0
    watchdog_s: float = 0.3


class World(ABC):
    """Abstract multi-entity simulation world (see docs/SPEC_DTSSL.md §4.2)."""

    ts: float = 1.0 / 60.0

    @abstractmethod
    def reset(self, scene: Scene) -> None: ...

    @abstractmethod
    def set_command(self, team: Team, rid: int, cmd: RobotCmd) -> None:
        """Latest command for a robot (kept until replaced; watchdog zeroes it after ``watchdog_s``)."""

    @abstractmethod
    def step(self, dt: float | None = None) -> WorldState:
        """Advance the world by ``dt`` seconds (default ``ts``) and return the new state."""

    @abstractmethod
    def state(self) -> WorldState: ...

    @abstractmethod
    def teleport_robot(self, team: Team, rid: int, x: float, y: float, theta: float, present: bool = True) -> None: ...

    @abstractmethod
    def teleport_ball(self, x: float, y: float, vx: float = 0.0, vy: float = 0.0, z: float = 0.0, vz: float = 0.0) -> None: ...

    @property
    @abstractmethod
    def field(self) -> FieldGeometry: ...

    @property
    @abstractmethod
    def spec(self) -> RobotSpec: ...

    # --- optional hooks with default implementations -------------------------------------
    @property
    def name(self) -> str:
        return type(self).__name__

    def robot(self, team: Team, rid: int) -> RobotState:
        return self.state().robots[(team, rid)]

    def ball(self) -> BallState:
        return self.state().ball

    def set_plant_params(self, params) -> None:  # noqa: B027 - optional
        """Hot-swap the behavioral parameters (theta) if the backend supports it."""

    def close(self) -> None:  # noqa: B027 - optional
        """Release resources (viewers, sockets)."""
