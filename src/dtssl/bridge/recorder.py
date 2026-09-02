"""``SessionRecorder``: commands + robot states of a twin session in the **log contract**.

The two parquet files have exactly the columns of the extracted competition logs
(DESIGN.md §2.2/§2.3), so a recorded session loads through
``dtssl.data.loader.load_event(commands_path, robots_path)`` and is evaluated by the same
harness as the real logs:

``commands.parquet``: ``timestamp, timestamp_event, robot_id, move_x, move_y, move_w,
actuation_kick_strength, actuation_front, actuation_chip, actuation_charge,
actuation_dribbler, actuation_dribbler_velocity``

``processed_robots.parquet``: ``timestamp, timestamp_event, team ("allies"), robot_id,
position_x, position_y (mm), position_w (rad, wrapped), velocity_x, velocity_y (mm/s, world),
velocity_norm``

``timestamp_event`` is the simulation time (s); ``timestamp`` is ``t0_wall + timestamp_event``
(absolute, like the log clock). One row per tick and robot of the recorded team (default: both
teams; ``robot_ids`` restricts it). The command row of a tick carries the time at which the
command started to act (the *beginning* of the step, ZOH-forward like the logs) and the
robot row the time of the resulting pose (the end of the step); the first command is at 0 and
the first pose at ``Ts``. Commands are the ones applied by the world at that tick (post-watchdog),
so replaying ``commands.parquet`` through the same plant reproduces ``processed_robots.parquet``.
"""
from __future__ import annotations

import math
import time
from pathlib import Path

import numpy as np
import pandas as pd

from dtssl.sim.entities import TEAMS, RobotCmd, WorldState

M_TO_MM = 1000.0

COMMAND_COLUMNS = ["timestamp", "timestamp_event", "robot_id", "move_x", "move_y", "move_w",
                   "actuation_kick_strength", "actuation_front", "actuation_chip",
                   "actuation_charge", "actuation_dribbler", "actuation_dribbler_velocity"]
ROBOT_COLUMNS = ["timestamp", "timestamp_event", "team", "robot_id", "position_x", "position_y",
                 "position_w", "velocity_x", "velocity_y", "velocity_norm"]


class SessionRecorder:
    def __init__(self, teams: str | tuple[str, ...] | list[str] | None = None,
                 robot_ids: list[int] | None = None, team_label: str = "allies",
                 t0_wall: float | None = None):
        if teams is None:
            self.teams: tuple[str, ...] = tuple(TEAMS)
        elif isinstance(teams, str):
            self.teams = (teams,)
        else:
            self.teams = tuple(teams)
        self.robot_ids = None if robot_ids is None else {int(r) for r in robot_ids}
        self.team_label = team_label
        self.t0_wall = time.time() if t0_wall is None else float(t0_wall)
        self._t0_sim: float | None = None
        self._t_prev: float | None = None
        self.ts = 1.0 / 60.0
        self._cmd_rows: list[tuple] = []
        self._rob_rows: list[tuple] = []
        self.ticks = 0

    # ------------------------------------------------------------------ recording
    def _wanted(self, team: str, rid: int) -> bool:
        return team in self.teams and (self.robot_ids is None or rid in self.robot_ids)

    def record_initial(self, ws: WorldState) -> None:
        """Record the pose rows of the initial state (before the first step, no command rows), so
        the session starts at ``timestamp_event = 0`` from a known state (like the real logs)."""
        if self._t0_sim is not None:
            return
        self._t0_sim = float(ws.t)
        self._t_prev = float(ws.t)
        self._append_robot_rows(ws, 0.0)

    def _snap(self, t: float) -> float:
        """Snap ``t`` to the exact ``k * ts`` grid when within 1e-6 * ts (the world clock accumulates
        ``t += dt`` and drifts by ulps, which would shift ZOH commands by one sample in the loader)."""
        k = round(t / self.ts)
        tk = k * self.ts
        return tk if abs(t - tk) <= 1e-6 * self.ts else t

    def _append_robot_rows(self, ws: WorldState, t_ev: float) -> None:
        t_abs = self.t0_wall + t_ev
        for key in sorted(ws.robots):
            team, rid = key
            r = ws.robots[key]
            if not r.present or not self._wanted(team, rid):
                continue
            vxw, vyw = r.velocity_world()
            th = math.atan2(math.sin(r.theta), math.cos(r.theta))
            self._rob_rows.append((t_abs, t_ev, self.team_label, int(rid), r.x * M_TO_MM, r.y * M_TO_MM,
                                   th, vxw * M_TO_MM, vyw * M_TO_MM, math.hypot(vxw, vyw) * M_TO_MM))

    def record(self, ws: WorldState, commands: dict[tuple[str, int], RobotCmd] | None = None) -> None:
        """Append one row per recorded robot (present ones) for this world state."""
        t_now = float(ws.t)
        dt = self.ts if self._t_prev is None or t_now <= self._t_prev else t_now - self._t_prev
        if self._t0_sim is None:
            self._t0_sim = t_now - dt              # first command at 0, first pose at dt
        self._t_prev = t_now
        t_ev = self._snap(t_now - self._t0_sim)   # pose time (end of the step)
        t_cmd = self._snap(t_ev - dt)              # command time (start of the step)
        t_abs_cmd = self.t0_wall + t_cmd
        commands = commands or {}
        for key in sorted(ws.robots):
            team, rid = key
            r = ws.robots[key]
            if not r.present or not self._wanted(team, rid):
                continue
            c = commands.get(key, RobotCmd())
            self._cmd_rows.append((t_abs_cmd, t_cmd, int(rid), float(c.vx), float(c.vy), float(c.w),
                                   float(c.kick_speed), bool(c.kick_speed > 0 and c.kick_angle_deg <= 0),
                                   bool(c.kick_speed > 0 and c.kick_angle_deg > 0), False,
                                   bool(c.dribbler_rpm > 0), float(c.dribbler_rpm)))
        self._append_robot_rows(ws, t_ev)
        self.ticks += 1

    def clear(self) -> None:
        self._cmd_rows.clear()
        self._rob_rows.clear()
        self._t0_sim = None
        self._t_prev = None
        self.ticks = 0

    # ------------------------------------------------------------------ output
    def commands_df(self) -> pd.DataFrame:
        df = pd.DataFrame(self._cmd_rows, columns=COMMAND_COLUMNS)
        return df.astype({"timestamp": "float64", "timestamp_event": "float64", "robot_id": "int64",
                          "move_x": "float64", "move_y": "float64", "move_w": "float64",
                          "actuation_kick_strength": "float64", "actuation_front": "bool",
                          "actuation_chip": "bool", "actuation_charge": "bool",
                          "actuation_dribbler": "bool", "actuation_dribbler_velocity": "float64"})

    def robots_df(self) -> pd.DataFrame:
        df = pd.DataFrame(self._rob_rows, columns=ROBOT_COLUMNS)
        return df.astype({"timestamp": "float64", "timestamp_event": "float64",
                          "robot_id": "int64", "position_x": "float64", "position_y": "float64",
                          "position_w": "float64", "velocity_x": "float64", "velocity_y": "float64",
                          "velocity_norm": "float64"})

    def save(self, out_dir: str | Path) -> tuple[Path, Path]:
        """Write ``commands.parquet`` and ``processed_robots.parquet`` into ``out_dir``."""
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        cp = out / "commands.parquet"
        rp = out / "processed_robots.parquet"
        self.commands_df().to_parquet(cp, index=False)
        self.robots_df().to_parquet(rp, index=False)
        return cp, rp

    @property
    def duration_s(self) -> float:
        if not self._rob_rows:
            return 0.0
        return float(self._rob_rows[-1][1] - self._rob_rows[0][1])

    def __len__(self) -> int:
        return len(self._rob_rows)


def summary(rec: SessionRecorder) -> dict:
    R = rec.robots_df()
    if R.empty:
        return {"rows": 0}
    return {"rows": int(len(R)), "duration_s": rec.duration_s, "robots": sorted(map(int, R["robot_id"].unique())),
            "max_speed_mm_s": float(np.max(R["velocity_norm"]))}


__all__ = ["SessionRecorder", "COMMAND_COLUMNS", "ROBOT_COLUMNS", "summary"]
