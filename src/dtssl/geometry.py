"""Robot geometry (single source of truth: ``config/robot_geometry.json``, section ``physical``).

Conventions (docs/SPEC_DTSSL.md §3): body frame x forward (dribbler), y left, w CCW.
Wheel ``i`` touches the floor at angle ``phi_i`` measured CCW from the body +x axis; a
positive wheel speed drives the contact point along the CCW tangent, so

    omega_i * r = -sin(phi_i) * vx + cos(phi_i) * vy + R * w

with ``R`` the centre-to-contact radius and ``r`` the wheel radius (see ``dtssl.kinematics``).
The RobôCIn v2025 robot has ``phi = (60, 135, 225, 300)`` deg, ``R = 0.079601 m``,
``r = 0.029492 m`` (CAD, measured 2026-07-24).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, replace
from pathlib import Path

from dtssl.paths import config_path

DEFAULT_WHEEL_ANGLES_DEG: tuple[float, float, float, float] = (60.0, 135.0, 225.0, 300.0)
WHEEL_ANGLE_CONVENTION = ("angle of the wheel contact point measured CCW from the body +x "
                          "(forward) axis; positive wheel speed = CCW tangent")


@dataclass(frozen=True)
class RobotGeometry:
    """Geometry of the omnidirectional robot (SI)."""

    R_contact_m: float = 0.079601                       # centre -> wheel/floor contact point
    wheel_radius_m: float = 0.029492                    # wheel (roller surface) radius
    wheel_angles_deg: tuple[float, ...] = DEFAULT_WHEEL_ANGLES_DEG
    body_radius_m: float = 0.09                         # chassis radius (ssl-unification Env.h)
    dribbler_offset_m: float = 0.075                    # centre -> dribbler face
    height_m: float = 0.15
    mass_kg: float = 2.4
    provenance: str = field(default="defaults (dtssl.geometry)", compare=False)

    def __post_init__(self) -> None:
        if self.R_contact_m <= 0.0 or self.wheel_radius_m <= 0.0:
            raise ValueError("R_contact_m and wheel_radius_m must be > 0")
        if len(self.wheel_angles_deg) < 3:
            raise ValueError("at least 3 wheels are needed for a holonomic base")
        object.__setattr__(self, "wheel_angles_deg", tuple(float(a) for a in self.wheel_angles_deg))

    # --- derived quantities ---------------------------------------------------------
    @property
    def n_wheels(self) -> int:
        return len(self.wheel_angles_deg)

    @property
    def R_over_r(self) -> float:
        """Body angular velocity -> wheel angular velocity ratio (2.6991 for v2025)."""
        return self.R_contact_m / self.wheel_radius_m

    @property
    def wheel_angles_rad(self) -> tuple[float, ...]:
        return tuple(math.radians(a) for a in self.wheel_angles_deg)

    def to_dict(self) -> dict:
        return {
            "R_contact_m": self.R_contact_m,
            "wheel_radius_m": self.wheel_radius_m,
            "wheel_angles_deg": list(self.wheel_angles_deg),
            "body_radius_m": self.body_radius_m,
            "dribbler_offset_m": self.dribbler_offset_m,
            "height_m": self.height_m,
            "mass_kg": self.mass_kg,
            "R_over_r": self.R_over_r,
            "provenance": self.provenance,
        }

    def with_(self, **changes) -> "RobotGeometry":
        return replace(self, **changes)

    # --- construction from the JSON configs -----------------------------------------
    @classmethod
    def from_physical_section(cls, physical: dict, robot_limits: dict | None = None,
                              provenance: str | None = None) -> "RobotGeometry":
        """Build from the ``physical`` dict of robot_geometry.json (+ optional ``robot`` dict of
        robot_limits.json for chassis radius/dribbler/height/mass)."""
        kw = dict(
            R_contact_m=float(physical["R_contact_m"]),
            wheel_radius_m=float(physical["wheel_radius_m"]),
            wheel_angles_deg=tuple(float(a) for a in physical.get("wheel_angles_deg", DEFAULT_WHEEL_ANGLES_DEG)),
        )
        if "body_radius_m" in physical:
            kw["body_radius_m"] = float(physical["body_radius_m"])
        if robot_limits:
            for src, dst in (("radius", "body_radius_m"), ("dribbler_offset", "dribbler_offset_m"),
                             ("height", "height_m"), ("mass", "mass_kg")):
                if robot_limits.get(src) is not None:
                    kw[dst] = float(robot_limits[src])
        kw["provenance"] = provenance or str(physical.get("provenance", "config/robot_geometry.json"))
        return cls(**kw)

    @classmethod
    def from_json(cls, path: str | Path | None = None,
                  limits_path: str | Path | None = None) -> "RobotGeometry":
        """Read ``config/robot_geometry.json`` (and, if available, ``config/robot_limits.json``)."""
        p = Path(path) if path is not None else config_path("robot_geometry.json")
        with open(p, encoding="utf-8") as f:
            cfg = json.load(f)
        limits = None
        lp = Path(limits_path) if limits_path is not None else config_path("robot_limits.json")
        if lp.is_file():
            with open(lp, encoding="utf-8") as f:
                limits = json.load(f).get("robot")
        return cls.from_physical_section(cfg["physical"], limits, provenance=f"{p.name}: {cfg['physical'].get('provenance', '')}")


__all__ = ["RobotGeometry", "DEFAULT_WHEEL_ANGLES_DEG", "WHEEL_ANGLE_CONVENTION"]
