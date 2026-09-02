"""IdealKinematicPlant: K=1, tau=0, Td=0 baseline (moved from phase0_replay/plant.py)."""
from __future__ import annotations

import math

import numpy as np

from dtssl.models.base import DOFS, Plant, Pose, Vel, wrap_to_pi


class IdealKinematicPlant(Plant):
    """Cinematica ideal: velocidade de corpo atingida == comando (instantanea,
    sem ganho/lag/atraso); mesma integracao trapezoidal de pose."""

    def reset(self, pose0: Pose, velb0: Vel = (0.0, 0.0, 0.0)) -> None:
        self.x, self.y, self.th = (float(v) for v in pose0)
        vb = np.asarray(velb0, dtype=float).reshape(3)
        self._vbody = vb.copy()
        c, s = math.cos(self.th), math.sin(self.th)
        self._gx_prev = c * vb[0] - s * vb[1]
        self._gy_prev = s * vb[0] + c * vb[1]
        self._vw_prev = float(vb[2])

    def prime_delay(self, prev_cmds) -> None:
        pass  # sem atraso

    def step(self, cmd: Vel, dt: float) -> Pose:
        vbody_new = np.asarray(cmd, dtype=float).reshape(3)   # vel atingida == comando
        th_new = self.th + 0.5 * dt * (vbody_new[2] + self._vw_prev)
        c, s = math.cos(th_new), math.sin(th_new)
        gx_new = c * vbody_new[0] - s * vbody_new[1]
        gy_new = s * vbody_new[0] + c * vbody_new[1]
        x_new = self.x + 0.5 * dt * (gx_new + self._gx_prev)
        y_new = self.y + 0.5 * dt * (gy_new + self._gy_prev)
        self._vbody = vbody_new
        self.x, self.y, self.th = x_new, y_new, th_new
        self._gx_prev, self._gy_prev, self._vw_prev = gx_new, gy_new, float(vbody_new[2])
        return (self.x, self.y, self.th)
