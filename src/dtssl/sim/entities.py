"""Shared entity types of the multi-robot twin world (SI units, world frame = ssl-vision frame).

Conventions (docs/SPEC_DTSSL.md §3): metres, seconds, radians; world x toward the right goal,
y "up" (CCW), theta CCW from +x; body frame x forward (dribbler), y left, w CCW.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Iterable

Team = str  # "blue" | "yellow"
TEAMS: tuple[Team, Team] = ("blue", "yellow")
MAX_ROBOTS = 16


@dataclass
class RobotCmd:
    """Body-frame velocity command + actuation, as received from the strategy (or joystick)."""

    vx: float = 0.0            # m/s, forward
    vy: float = 0.0            # m/s, left
    w: float = 0.0             # rad/s, CCW
    kick_speed: float = 0.0    # m/s (0 = no kick); consumed once by the world when the ball is in the dribbler
    kick_angle_deg: float = 0.0  # 0 = flat, >0 = chip (45 typical)
    dribbler_rpm: float = 0.0  # >0 = dribbler on
    t_recv: float = 0.0        # monotonic time of reception (watchdog)

    @staticmethod
    def zero() -> "RobotCmd":
        return RobotCmd()


@dataclass
class RobotState:
    team: Team
    id: int
    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0         # rad, wrapped to (-pi, pi] when published; internally may be unwrapped
    vx_b: float = 0.0          # body velocity (m/s)
    vy_b: float = 0.0
    w: float = 0.0             # rad/s
    has_ball: bool = False     # infrared/dribbler contact
    present: bool = True       # False = removed from the field (not published in vision)

    @property
    def key(self) -> tuple[Team, int]:
        return (self.team, self.id)

    def velocity_world(self) -> tuple[float, float]:
        import math
        c, s = math.cos(self.theta), math.sin(self.theta)
        return (c * self.vx_b - s * self.vy_b, s * self.vx_b + c * self.vy_b)


@dataclass
class BallState:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0             # height of the centre above the floor minus radius (0 on the ground)
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    rolling: bool = True       # two-phase model: sliding (after a kick) -> rolling


@dataclass
class WorldState:
    t: float                   # simulation time (s)
    frame: int                 # vision frame counter
    robots: dict[tuple[Team, int], RobotState]
    ball: BallState

    def robots_of(self, team: Team) -> list[RobotState]:
        return [r for (tm, _), r in sorted(self.robots.items()) if tm == team and r.present]

    def copy(self) -> "WorldState":
        return WorldState(self.t, self.frame, {k: replace(v) for k, v in self.robots.items()}, replace(self.ball))


@dataclass
class RobotSpawn:
    team: Team
    id: int
    x: float
    y: float
    theta: float = 0.0
    present: bool = True


@dataclass
class Scene:
    """Initial condition of a world: robots + ball (+ optional per-robot theta overrides)."""

    robots: list[RobotSpawn] = field(default_factory=list)
    ball: BallState = field(default_factory=BallState)

    @staticmethod
    def default(n_blue: int = 6, n_yellow: int = 6, field_length_m: float = 9.0, field_width_m: float = 6.0) -> "Scene":
        """Both teams on their own half, evenly spaced along y, facing the centre."""
        robots: list[RobotSpawn] = []
        for team, sign, n in (("blue", -1.0, n_blue), ("yellow", +1.0, n_yellow)):
            for i in range(n):
                y = (i - (n - 1) / 2.0) * (field_width_m * 0.8 / max(n, 1))
                robots.append(RobotSpawn(team, i, sign * field_length_m * 0.25, y, 0.0 if sign < 0 else 3.141592653589793))
        return Scene(robots=robots, ball=BallState())


def robot_keys(spawns: Iterable[RobotSpawn]) -> list[tuple[Team, int]]:
    return [(s.team, s.id) for s in spawns]
