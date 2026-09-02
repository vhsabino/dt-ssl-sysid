"""Plant interface (one robot, body-frame commands -> world pose) and helpers.

Moved verbatim from phase0_replay/plant.py (2026-09-02 refactor).
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod

import numpy as np

from dtssl.models.params import DofParam, load_twin_params

DOFS = ("vx", "vy", "w")
Pose = tuple[float, float, float]
Vel = tuple[float, float, float]


def wrap_to_pi(a: float) -> float:
    """Envolve um angulo (rad) em (-pi, pi]. atan2(sin,cos) e robusto a multiplos
    de 2*pi (erro entre +179 e -179 graus = 2 graus, nao 358)."""
    return math.atan2(math.sin(a), math.cos(a))


class Plant(ABC):
    """Gemeo free-run: parte do estado verdadeiro e avanca por comando (CORPO)."""

    @abstractmethod
    def reset(self, pose0: Pose, velb0: Vel = (0.0, 0.0, 0.0)) -> None:
        """Zera o estado: pose = pose0; velocidade de corpo inicial = velb0."""

    @abstractmethod
    def prime_delay(self, prev_cmds) -> None:
        """Enche o buffer de atraso com comandos ANTERIORES a t0 (mais antigo->mais
        recente) SEM avancar o estado do lag/pose."""

    @abstractmethod
    def step(self, cmd: Vel, dt: float) -> Pose:
        """Avanca dt s sob o comando de CORPO cmd=(vx,vy,w); devolve a nova pose."""

    @property
    def pose(self) -> Pose:
        return (self.x, self.y, self.th)

    @property
    def body_velocity(self) -> Vel:
        return (float(self._vbody[0]), float(self._vbody[1]), float(self._vbody[2]))


