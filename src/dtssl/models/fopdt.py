"""Plantas do replay: interface Plant + AnalyticFOPDTPlant (PORTE FIEL de
automation/deadreckoning_p1d.m) e IdealKinematicPlant.

A AnalyticFOPDTPlant reproduz deadreckoning_p1d EXATAMENTE na grade uniforme 1/60:
  - atraso por DOF = interp1(t, u, t-Td, 'previous', 0); na grade uniforme isso e
    um shift inteiro de m = ceil(Td/dt) amostras (= floor(k - Td/dt)). NOTA: e
    ceil, NAO round (Td_vx/dt = 4.15 -> 5 amostras). O golden test e o arbitro.
  - lag de 1a ordem ZOH-exato: v[k] = v[k-1] + (1-e^{-dt/tau})*(u_d[k-1] - v[k-1]);
    estado inicial v[0] = velb0/K (0 no golden, como deadreckoning).
  - ganho: v_corpo = K * v.
  - integracao de pose TRAPEZOIDAL (cumtrapz), corpo->mundo:
      th[k] = th[k-1] + 0.5*dt*(w[k]+w[k-1])
      x[k]  = x[k-1]  + 0.5*dt*( (cos th*vx - sin th*vy)[k] + [k-1] )
      y[k]  = y[k-1]  + 0.5*dt*( (sin th*vx + cos th*vy)[k] + [k-1] )

NAO contem rollout nem metrica (vivem fora). A grade e a comprometida na Fase 0.
"""
from __future__ import annotations

import math

import numpy as np

from dtssl.models.base import DOFS, Plant, Pose, Vel, wrap_to_pi
from dtssl.models.params import DofParam, load_twin_params


# =========================================================================
class AnalyticFOPDTPlant(Plant):
    """Porte fiel de deadreckoning_p1d (modelo promovido)."""

    def __init__(self, params: dict[str, DofParam]):
        self.params = params
        self.K = np.array([params[d].K for d in DOFS], dtype=float)
        self.tau = np.array([params[d].tau for d in DOFS], dtype=float)
        self.Td = np.array([params[d].Td for d in DOFS], dtype=float)

    @classmethod
    def from_config(cls, path=None) -> "AnalyticFOPDTPlant":
        return cls(load_twin_params(path))

    def reset(self, pose0: Pose, velb0: Vel = (0.0, 0.0, 0.0)) -> None:
        self.x, self.y, self.th = (float(v) for v in pose0)
        vb = np.asarray(velb0, dtype=float).reshape(3)
        # estado do lag tal que K*vlag = velb0 (vlag = velb0/K). No golden velb0=0.
        self._vlag = np.where(self.K != 0.0, vb / np.where(self.K == 0.0, 1.0, self.K), 0.0)
        self._vbody = vb.copy()
        c, s = math.cos(self.th), math.sin(self.th)
        self._gx_prev = c * vb[0] - s * vb[1]      # integrando de x em k=0
        self._gy_prev = s * vb[0] + c * vb[1]      # integrando de y em k=0
        self._vw_prev = float(vb[2])               # integrando de theta em k=0
        self._hist: list[np.ndarray] = []          # comandos crus (abs idx -base..k-1)
        self._base = 0                             # n de comandos pre-t0 (offset)
        self._k = 0                                # indice do estado atual

    def prime_delay(self, prev_cmds) -> None:
        self._hist = [np.asarray(c, dtype=float).reshape(3) for c in prev_cmds]
        self._base = len(self._hist)

    def step(self, cmd: Vel, dt: float) -> Pose:
        cmd = np.asarray(cmd, dtype=float).reshape(3)
        j = self._k
        self._hist.append(cmd)                      # comando cru no indice abs j

        # comando atrasado por DOF: ud[j] = ucmd[floor(j - Td/dt)] (0 antes do inicio)
        ud = np.zeros(3)
        for i in range(3):
            if self.Td[i] <= 0.0:
                src = j                              # sem atraso
            else:
                src = int(math.floor(j - self.Td[i] / dt + 1e-9))   # = j - ceil(Td/dt)
            pos = src + self._base
            if 0 <= pos < len(self._hist):
                ud[i] = self._hist[pos][i]

        # lag 1a ordem ZOH-exato (tau=0 -> instantaneo)
        vlag_new = np.empty(3)
        for i in range(3):
            if self.tau[i] > 0.0:
                a = 1.0 - math.exp(-dt / self.tau[i])
                vlag_new[i] = self._vlag[i] + a * (ud[i] - self._vlag[i])
            else:
                vlag_new[i] = ud[i]
        vbody_new = self.K * vlag_new

        # integracao de pose trapezoidal (corpo->mundo)
        th_new = self.th + 0.5 * dt * (vbody_new[2] + self._vw_prev)
        c, s = math.cos(th_new), math.sin(th_new)
        gx_new = c * vbody_new[0] - s * vbody_new[1]
        gy_new = s * vbody_new[0] + c * vbody_new[1]
        x_new = self.x + 0.5 * dt * (gx_new + self._gx_prev)
        y_new = self.y + 0.5 * dt * (gy_new + self._gy_prev)

        # commit
        self._vlag = vlag_new
        self._vbody = vbody_new
        self.x, self.y, self.th = x_new, y_new, th_new
        self._gx_prev, self._gy_prev, self._vw_prev = gx_new, gy_new, float(vbody_new[2])
        self._k = j + 1
        return (self.x, self.y, self.th)
