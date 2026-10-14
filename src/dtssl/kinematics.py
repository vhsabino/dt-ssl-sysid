"""Kinematics of the 4-wheel omnidirectional robot (body frame <-> wheel speeds <-> world frame).

Wheel ``i`` at angle ``phi_i`` (CCW from body +x, contact point) with the positive speed
direction along the CCW tangent satisfies

    omega_i * r = -sin(phi_i) * vx + cos(phi_i) * vy + R * w              (1)

so ``omega = K @ [vx, vy, w]`` with ``K[i] = [-sin phi_i, cos phi_i, R] / r`` (4x3, "body to
wheel"). With ``phi = (60, 135, 225, 300)`` deg, ``r = 0.029492 m`` and ``R = 0.079601 m`` this
is exactly the matrix of ``matlab/analytical/kinematicSolver.m``::

    K = [[-K1,  K2, K4],      K1 = sin60/r = 29.36475667
         [-K3, -K3, K4],      K2 = cos60/r = 16.95375017
         [ K3, -K3, K4],      K3 = sin45/r = 23.97622342
         [ K1,  K2, K4]]      K4 = R/r     =  2.699070934

The odometry direction (wheels -> body) is the Moore-Penrose pseudo-inverse ``pinv(K)``
(3x4), i.e. the least-squares body velocity for 4 measured wheel speeds. ``pinv(K) @ K = I``
exactly (full column rank). Its ``w`` row is NOT uniform across wheels (ratio wheel(2,3) /
wheel(1,4) = cos 45 deg): that is the correct consequence of the layout — the ``vy`` and ``w``
columns of ``K`` are not orthogonal because cos 60 != sin 45 — and not a modelling error
(``config/robot_geometry.json: corrections_2026-09-02``). Under uniform excitation (all four
wheels at the same speed) the recovered body ``w`` is exactly ``omega_wheel * r / R``.

Nothing here is used by the published behavioural plant (which is body-velocity based);
the functions serve the bridge (``wheel_velocity`` commands), the GUI and the MuJoCo
route (b) backend.
"""
from __future__ import annotations

import numpy as np

from dtssl.geometry import RobotGeometry

__all__ = [
    "LEGACY_K_2025", "body_to_wheel_matrix", "wheel_to_body_matrix", "body_to_wheels",
    "wheels_to_body", "local_to_global", "global_to_local", "apply_wheel_deadzone",
    "rotation_matrix",
]

#: Body-to-wheel matrix hard-coded in the 2025 Simulink/Isaac chain (``python/kinematics.py``,
#: Stateflow charts of ``simulink/*.slx``, commented-out K1..K12 of ``kinematicSolver.m``).
#: Provenance (verified 2026-09-02, see config/robot_geometry.json "corrections_2026-09-02"):
#: it is equation (1) with a THIRD geometry, **r = 24.75 mm** (``K2 = cos60/r = 20.2020`` exactly)
#: and **R = 82.28 mm** (``K4 = R/r = 3.324525``), NOT the firmware pair 0.088/0.0265
#: (``R/r = 3.3208``, which differs from 3.3245 by 0.11 %). Kept only for regression tests.
LEGACY_K_2025 = np.array([
    [-34.9909, 20.2020, 3.3245],
    [-28.5700, -28.5700, 3.3245],
    [28.5700, -28.5700, 3.3245],
    [34.9909, 20.2020, 3.3245],
], dtype=float)
LEGACY_K_2025.setflags(write=False)

#: Geometry that reproduces LEGACY_K_2025 (documentary; r = 0.5/20.2020 m, R = 3.3245*r).
LEGACY_GEOMETRY_2025 = RobotGeometry(R_contact_m=0.082282, wheel_radius_m=0.02475,
                                     provenance="legacy 2025 constants (K2=cos60/r, K4=R/r)")


def _geom(geom: RobotGeometry | None) -> RobotGeometry:
    if geom is None:
        from dtssl.config import load_geometry
        return load_geometry()
    return geom


def body_to_wheel_matrix(geom: RobotGeometry | None = None) -> np.ndarray:
    """``K`` (n_wheels x 3): ``omega_wheels = K @ [vx, vy, w]`` (rad/s from m/s, m/s, rad/s)."""
    g = _geom(geom)
    phi = np.asarray(g.wheel_angles_rad, dtype=float)
    K = np.column_stack([-np.sin(phi), np.cos(phi), np.full(phi.size, g.R_contact_m)])
    return K / g.wheel_radius_m


def wheel_to_body_matrix(geom: RobotGeometry | None = None) -> np.ndarray:
    """``pinv(K)`` (3 x n_wheels): least-squares body velocity from wheel speeds."""
    return np.linalg.pinv(body_to_wheel_matrix(geom))


def body_to_wheels(v, geom: RobotGeometry | None = None) -> np.ndarray:
    """Wheel angular speeds (rad/s) for body velocity ``v = (vx, vy, w)``.

    ``v`` may be shape (3,) or (N, 3); returns (n_wheels,) or (N, n_wheels).
    """
    K = body_to_wheel_matrix(geom)
    v = np.asarray(v, dtype=float)
    return v @ K.T


def wheels_to_body(w, geom: RobotGeometry | None = None) -> np.ndarray:
    """Body velocity ``(vx, vy, w)`` from wheel speeds (rad/s), least squares.

    ``w`` may be shape (n_wheels,) or (N, n_wheels); returns (3,) or (N, 3).
    """
    P = wheel_to_body_matrix(geom)
    w = np.asarray(w, dtype=float)
    return w @ P.T


def rotation_matrix(theta: float) -> np.ndarray:
    """``R(theta) = [[c, -s], [s, c]]`` (body -> world)."""
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s], [s, c]], dtype=float)


def local_to_global(vx, vy, theta):
    """Body-frame velocity -> world frame: ``v_world = R(theta) @ v_body`` (vectorised)."""
    vx = np.asarray(vx, dtype=float); vy = np.asarray(vy, dtype=float)
    c, s = np.cos(theta), np.sin(theta)
    return c * vx - s * vy, s * vx + c * vy


def global_to_local(vx_w, vy_w, theta):
    """World-frame velocity -> body frame: ``v_body = R(theta)^T @ v_world`` (vectorised)."""
    vx_w = np.asarray(vx_w, dtype=float); vy_w = np.asarray(vy_w, dtype=float)
    c, s = np.cos(theta), np.sin(theta)
    return c * vx_w + s * vy_w, -s * vx_w + c * vy_w


def apply_wheel_deadzone(wheel_speeds, min_speed: float) -> np.ndarray:
    """Firmware per-wheel deadzone: ``|omega| < min_speed`` (and non-zero) -> 0.

    Mirrors ssl-embedded ``PID_Controller.cpp`` (``MOTOR_MIN_SPEED_RAD_S = 1.567`` rad/s),
    applied to the desired wheel speed BEFORE the PI loop. ``min_speed <= 0`` disables it.
    """
    w = np.array(wheel_speeds, dtype=float, copy=True)
    if min_speed > 0.0:
        w[np.abs(w) < min_speed] = 0.0
    return w
