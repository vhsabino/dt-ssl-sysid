"""Shared entity types of the multi-robot twin world (SI units, world frame = ssl-vision frame).

Conventions (docs/SPEC_DTSSL.md §3): metres, seconds, radians; world x toward the right goal,
y "up" (CCW), theta CCW from +x; body frame x forward (dribbler), y left, w CCW.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field, replace

Team = str  # "blue" | "yellow"
TEAMS: tuple[Team, Team] = ("blue", "yellow")
MAX_ROBOTS = 16
ROSTER_SIZE = 11           # robots per team in a world (SSL roster), only ``ACTIVE_ROBOTS`` start on the field
ACTIVE_ROBOTS = 6          # Division B: robots per team on the field
PARK_GAP = 0.25            # m, outside the arena walls: wall -> parked robot centre, and spacing along the wall


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
    def zero() -> RobotCmd:
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

    def copy(self) -> WorldState:
        return WorldState(self.t, self.frame, {k: replace(v) for k, v in self.robots.items()}, replace(self.ball))


@dataclass
class RobotSpawn:
    team: Team
    id: int
    x: float
    y: float
    theta: float = 0.0
    present: bool = True


def park_spot(team: Team, rid: int, field_length_m: float = 9.0, field_width_m: float = 6.0,
              boundary_width_m: float = 0.3, gap: float = PARK_GAP) -> tuple[float, float, float]:
    """``(x, y, theta)`` where robot ``rid`` of ``team`` waits when it is not on the field: outside the arena,
    beyond the wall at ``-y`` (the team benches), each team on its own half (blue at ``x < 0``, yellow at
    ``x > 0``), ``gap`` apart along the wall in id order, facing the field. Parked robots never meet the
    ball, the walls or the robots in play."""
    sign = -1.0 if team == "blue" else 1.0
    x = sign * (gap + gap * int(rid))
    y = -(field_width_m / 2.0 + boundary_width_m + gap)
    return (x, y, 1.5707963267948966)


@dataclass
class Scene:
    """Initial condition of a world: robots + ball (+ optional per-robot theta overrides)."""

    robots: list[RobotSpawn] = field(default_factory=list)
    ball: BallState = field(default_factory=BallState)

    @staticmethod
    def default(n_blue: int = 6, n_yellow: int = 6, field_length_m: float = 9.0, field_width_m: float = 6.0,
                n_active: int | None = None, boundary_width_m: float = 0.3) -> Scene:
        """Both teams on their own half, evenly spaced along y, facing the centre. With ``n_active`` (per team)
        only the first ``n_active`` ids start on the field; the others are spawned ``present=False`` at their
        :func:`park_spot` outside the arena (the substitutes of a Division B game with an 11-robot roster)."""
        robots: list[RobotSpawn] = []
        for team, sign, n in (("blue", -1.0, n_blue), ("yellow", +1.0, n_yellow)):
            n_in = n if n_active is None else min(n, max(int(n_active), 0))
            for i in range(n):
                if i < n_in:
                    y = (i - (n_in - 1) / 2.0) * (field_width_m * 0.8 / max(n_in, 1))
                    robots.append(RobotSpawn(team, i, sign * field_length_m * 0.25, y,
                                             0.0 if sign < 0 else 3.141592653589793))
                else:
                    px, py, pth = park_spot(team, i, field_length_m, field_width_m, boundary_width_m)
                    robots.append(RobotSpawn(team, i, px, py, pth, present=False))
        return Scene(robots=robots, ball=BallState())


def robot_keys(spawns: Iterable[RobotSpawn]) -> list[tuple[Team, int]]:
    return [(s.team, s.id) for s in spawns]
