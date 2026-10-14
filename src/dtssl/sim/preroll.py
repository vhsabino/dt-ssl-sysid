"""Pre-roll: give a simulator its own dynamic state at ``t0`` instead of imposing the initial velocity.

The harness starts every re-anchored window at the true pose ``pose0`` with the true body velocity ``velb0``
(``Plant.reset``).  A simulator that cannot honour the velocity part of a ``TeleportRobot`` (grSim resets the
robot and turns the velocity into a motor setpoint; ER-Force drops the yaw rate) therefore starts every window
from the wrong state, and the harness measures that handicap together with its physics (C2b, 10/09/2026:
``fopdt_v0=0`` puts the initial condition at ~37 % of the grSim gap).

Pre-roll removes the handicap without touching the simulator: the robot is teleported ``P`` samples *before*
``t0`` and driven with the **recorded commands of the prefix** ``cmd[t0 - P : t0]`` (the same ``prev_cmds`` the
delay tap already receives), so at ``t0`` its velocity and internal actuator state are the simulator's own
response to the real command history; the window commands follow without any discontinuity.  The pose the
simulator has reached at ``t0`` is not ``pose0`` (it depends on its dynamics during the prefix), so the
simulated trajectory is **re-anchored in SE(2)** at ``t0``: the rigid transform that maps the simulated pose at
``t0`` onto ``pose0`` is applied to every later pose.  This is the re-anchoring the paper's metric already
assumes (every plant starts at ``pose0``), now applied to a trajectory that starts earlier.

Two implementations share this module:

* :class:`PreRollPlant` wraps any step-wise :class:`~dtssl.models.base.Plant` (in process, deterministic): the
  reference for the protocol tests and the twin's own control column (``fopdt+preroll``: what the pre-roll
  does to the twin, whose exact initial condition the harness *can* impose);
* :class:`~dtssl.sim.protocol_plant.ProtocolPlant` (``pre_roll`` > 0) does the same over the
  ssl-simulation-protocol, in real time, with the poses read back from the simulator's vision.

Conventions (identical in both, declared in ``docs/PREREGISTRO_C2B2_PREROLAGEM_20260916.md``):

* ``P = min(round(pre_roll / dt), len(prev_cmds))``: windows with a shorter recorded prefix (the first windows of
  an event) get a shorter pre-roll, and the number of samples actually used is kept in the plant statistics;
* teleport pose = ``pose0`` back-extrapolated with the window's initial world velocity for ``P dt`` seconds
  (straight line, constant yaw rate); teleport velocity = the body velocity that the first prefix command
  requests (``prev_cmds[-P]``): whether the simulator honours it is, again, its business, and after ``P dt``
  of its own dynamics it hardly matters;
* the delay tap (``+delay``) is applied to the concatenated stream ``[prefix, window]`` and primed with the
  commands before the prefix, so the window part of the delayed stream is the same as without pre-roll;
* ``pre_roll = 0`` is the previous behaviour, bit for bit.
"""
from __future__ import annotations

import math

import numpy as np

from dtssl.models.base import Plant, Pose, Vel

__all__ = ["preroll_samples", "body_to_world", "back_extrapolate", "reanchor_se2", "PreRollPlant"]


def preroll_samples(pre_roll_s: float, dt: float, n_prev: int) -> int:
    """Number of prefix samples the pre-roll uses: ``min(round(pre_roll / dt), n_prev)`` (0 when disabled)."""
    if pre_roll_s <= 0.0 or n_prev <= 0:
        return 0
    return int(min(int(round(pre_roll_s / dt)), n_prev))


def body_to_world(pose: Pose, velb: Vel) -> tuple[float, float, float]:
    c, s = math.cos(pose[2]), math.sin(pose[2])
    return (c * velb[0] - s * velb[1], s * velb[0] + c * velb[1], float(velb[2]))


def back_extrapolate(pose0: Pose, velw0: tuple[float, float, float], T: float) -> Pose:
    """Pose ``T`` seconds before ``pose0`` under a constant world velocity ``velw0`` (straight line, constant
    yaw rate).  Only the start of the pre-roll: the trajectory is re-anchored at ``t0`` afterwards."""
    x0, y0, th0 = (float(v) for v in pose0)
    return (x0 - velw0[0] * T, y0 - velw0[1] * T, th0 - velw0[2] * T)


def reanchor_se2(raw: np.ndarray, pose0: Pose) -> np.ndarray:
    """Apply to every row of ``raw`` (M, 3; x, y, unwrapped theta) the rigid transform that maps ``raw[0]`` onto
    ``pose0``: the displacement from the pose at ``t0``, expressed in that pose's frame, re-attached to the true
    pose.  Rows with NaN stay NaN; ``raw[0]`` must be finite."""
    raw = np.asarray(raw, dtype=float)
    if raw.ndim != 2 or raw.shape[1] != 3 or not np.isfinite(raw[0]).all():
        raise ValueError("reanchor_se2: raw must be (M, 3) with a finite first row")
    xa, ya, tha = raw[0]
    x0, y0, th0 = (float(v) for v in pose0)
    dth = th0 - tha
    c, s = math.cos(dth), math.sin(dth)
    dx, dy = raw[:, 0] - xa, raw[:, 1] - ya
    out = np.empty_like(raw)
    out[:, 0] = x0 + c * dx - s * dy
    out[:, 1] = y0 + s * dx + c * dy
    out[:, 2] = raw[:, 2] + dth
    out[0] = (x0, y0, th0)
    return out


class PreRollPlant:
    """Any step-wise ``Plant`` driven through the recorded prefix before each window (see the module doc).

    Exposes ``free_run_window`` (the batch hook of :func:`dtssl.sim.rollout.free_run`), so the harness hands
    it the prefix (``prev_cmds``); ``params`` is the inner plant's (same window grid).  ``pre_roll = 0`` returns
    exactly what the inner plant returns on the step-wise path."""

    def __init__(self, inner: Plant, pre_roll: float):
        if pre_roll < 0.0:
            raise ValueError("pre_roll must be >= 0 (seconds)")
        self.inner = inner
        self.pre_roll = float(pre_roll)
        self.params = getattr(inner, "params", None)
        self.samples_used: list[int] = []        # P per window (0 = no pre-roll on that window)
        self.x = self.y = self.th = 0.0
        self._vbody = np.zeros(3)

    # step-wise API, delegated (used only if somebody bypasses free_run)
    def reset(self, pose0: Pose, velb0: Vel = (0.0, 0.0, 0.0)) -> None:
        self.inner.reset(pose0, velb0)

    def prime_delay(self, prev_cmds) -> None:
        self.inner.prime_delay(prev_cmds)

    def step(self, cmd: Vel, dt: float) -> Pose:
        return self.inner.step(cmd, dt)

    def free_run_window(self, win_cmds, pose0: Pose, velb0: Vel, dt: float, prev_cmds=None) -> np.ndarray:
        u = np.asarray(win_cmds, dtype=float).reshape(-1, 3)
        prev = (np.asarray(prev_cmds, dtype=float).reshape(-1, 3) if prev_cmds is not None
                else np.zeros((0, 3)))
        H = len(u)
        P = preroll_samples(self.pre_roll, float(dt), len(prev))
        self.samples_used.append(P)
        pose_sim = np.empty((H + 1, 3), dtype=float)
        pose_sim[0] = pose0
        if P == 0:                                   # the plain step-wise path
            self.inner.reset(pose0, velb0)
            if len(prev):
                self.inner.prime_delay(prev)
            for h in range(H):
                pose_sim[h + 1] = self.inner.step(u[h], dt)
            self._track(pose_sim[-1], velb0)
            return pose_sim
        prefix, before = prev[-P:], prev[:-P]
        velw0 = body_to_world(pose0, velb0)
        pose_pre = back_extrapolate(pose0, velw0, P * float(dt))
        velb_pre = (float(prefix[0, 0]), float(prefix[0, 1]), float(prefix[0, 2]))
        self.inner.reset(pose_pre, velb_pre)
        if len(before):
            self.inner.prime_delay(before)
        raw = np.empty((P + H + 1, 3), dtype=float)
        raw[0] = pose_pre
        for k in range(P):
            raw[k + 1] = self.inner.step(prefix[k], dt)
        for h in range(H):
            raw[P + h + 1] = self.inner.step(u[h], dt)
        raw[:, 2] = np.unwrap(raw[:, 2])
        pose_sim = reanchor_se2(raw[P:], pose0)
        self._track(pose_sim[-1], velb0)
        return pose_sim

    def _track(self, last, velb0) -> None:
        self.x, self.y, self.th = (float(v) for v in last)
        self._vbody = np.asarray(velb0, dtype=float)

    @property
    def pose(self) -> Pose:
        return (self.x, self.y, self.th)
