"""Unit conversion constants and angle helpers (docs/SPEC_DTSSL.md §3).

Internal units are strictly SI (m, s, rad, kg). Conversion to/from mm and degrees
happens only at the boundaries (ssl-vision packets, the competition logs, Notion).
``wrap_to_pi`` is the single canonical implementation (defined in
``dtssl.models.base`` for the plants; re-exported here).
"""
from __future__ import annotations

import math

import numpy as np

from dtssl.models.base import wrap_to_pi

MM_TO_M = 1.0e-3
M_TO_MM = 1.0e3
DEG2RAD = math.pi / 180.0
RAD2DEG = 180.0 / math.pi
RPM_TO_RAD_S = 2.0 * math.pi / 60.0
RAD_S_TO_RPM = 60.0 / (2.0 * math.pi)

__all__ = [
    "MM_TO_M", "M_TO_MM", "DEG2RAD", "RAD2DEG", "RPM_TO_RAD_S", "RAD_S_TO_RPM",
    "wrap_to_pi", "wrap_to_pi_array", "unwrap", "unwrap_step", "mm_to_m", "m_to_mm",
    "deg_to_rad", "rad_to_deg",
]


def wrap_to_pi_array(a) -> np.ndarray:
    """Vectorised ``wrap_to_pi``: ``atan2(sin a, cos a)`` element-wise (result in (-pi, pi])."""
    a = np.asarray(a, dtype=float)
    return np.arctan2(np.sin(a), np.cos(a))


def unwrap(a) -> np.ndarray:
    """Unwrap a sequence of wrapped angles (rad) so consecutive samples never jump by ~2*pi.

    Thin wrapper over ``numpy.unwrap`` (the same operation the loader applies to
    ``position_w`` BEFORE interpolating on the 1/60 s grid).
    """
    return np.unwrap(np.asarray(a, dtype=float))


def unwrap_step(prev_unwrapped: float, new_wrapped: float) -> float:
    """Streaming unwrap: continue an unwrapped angle series with one new wrapped sample.

    ``prev + wrap_to_pi(new - prev)`` — the same rule used by ``RSimReplay`` to keep the
    engine heading continuous. Works for any ``prev`` (not necessarily in (-pi, pi]).
    """
    return float(prev_unwrapped) + wrap_to_pi(float(new_wrapped) - float(prev_unwrapped))


def mm_to_m(x):
    return np.asarray(x, dtype=float) * MM_TO_M


def m_to_mm(x):
    return np.asarray(x, dtype=float) * M_TO_MM


def deg_to_rad(x):
    return np.asarray(x, dtype=float) * DEG2RAD


def rad_to_deg(x):
    return np.asarray(x, dtype=float) * RAD2DEG
