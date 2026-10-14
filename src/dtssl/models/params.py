"""Twin parameters (K, tau, Td per DOF) read from config/twin_params.json.

The JSON mirrors the promoted MATLAB models: vx/vy from models/sysid_vxvy_v2.mat
(2026-06-14) and w from models/sysid_omega_rotate_v1.mat (2026-07-24, dedicated
open-loop rotation data). Fixed SLDD order in 'order'. ``placeholder`` marks a DOF
whose parameters were NOT identified (none since 2026-07-24).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from dtssl.paths import config_path

DOFS = ("vx", "vy", "w")


@dataclass(frozen=True)
class DofParam:
    K: float
    tau: float
    Td: float
    placeholder: bool = False


def twin_params_path() -> Path:
    return config_path("twin_params.json")


def load_twin_params(path: Path | None = None) -> dict[str, DofParam]:
    """Le config/twin_params.json -> {'vx':DofParam, 'vy':DofParam, 'w':DofParam}."""
    p = path or twin_params_path()
    with open(p, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    dof = cfg["dof"]
    return {d: DofParam(K=float(dof[d]["K"]), tau=float(dof[d]["tau"]),
                        Td=float(dof[d]["Td"]), placeholder=bool(dof[d].get("placeholder", False)))
            for d in DOFS}
