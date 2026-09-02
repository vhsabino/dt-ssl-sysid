"""Kinematics of the 4-wheel omni base (dtssl.kinematics) vs the MATLAB constants.

matlab/analytical/kinematicSolver.m (CAD geometry r=0.029492, R=0.079601):
    K1 = sin60/r = 29.36475667   K2 = cos60/r = 16.95375017
    K3 = sin45/r = 23.97622342   K4 = R/r     =  2.699070934
    K  = [[-K1, K2, K4], [-K3, -K3, K4], [K3, -K3, K4], [K1, K2, K4]]
matlab/analytical/inverse_kinematics_solver.m holds pinv(K) literally (15 digits).
No dataset needed.
"""
import math

import numpy as np
import pytest

from dtssl.config import load_geometry
from dtssl.geometry import RobotGeometry
from dtssl.kinematics import (LEGACY_GEOMETRY_2025, LEGACY_K_2025, apply_wheel_deadzone,
                              body_to_wheel_matrix, body_to_wheels, global_to_local,
                              local_to_global, wheel_to_body_matrix, wheels_to_body)

R_CAD, r_CAD = 0.079601, 0.029492
K1, K2, K3, K4 = 29.36475667, 16.95375017, 23.97622342, 2.699070934
K_MATLAB = np.array([[-K1, K2, K4], [-K3, -K3, K4], [K3, -K3, K4], [K1, K2, K4]])
K_INV_MATLAB = np.array([
    [-0.010216328484506, -0.008341597276945, 0.008341597276945, 0.010216328484506],
    [0.012215986382218, -0.012215986382218, -0.012215986382218, 0.012215986382218],
    [0.108516310225934, 0.076732618841300, 0.076732618841300, 0.108516310225934],
])


@pytest.fixture(scope="module")
def geom() -> RobotGeometry:
    g = load_geometry()
    assert g.R_contact_m == pytest.approx(R_CAD) and g.wheel_radius_m == pytest.approx(r_CAD)
    assert g.wheel_angles_deg == (60.0, 135.0, 225.0, 300.0)
    return g


def test_body_to_wheel_matrix_matches_matlab_constants(geom):
    K = body_to_wheel_matrix(geom)
    assert K.shape == (4, 3)
    np.testing.assert_allclose(K, K_MATLAB, rtol=0, atol=1e-6)
    # the individual constants, as in kinematicSolver.m
    assert K[0, 0] == pytest.approx(-math.sin(math.radians(60)) / r_CAD, abs=1e-9)
    assert K[0, 1] == pytest.approx(math.cos(math.radians(60)) / r_CAD, abs=1e-9)
    assert K[1, 0] == pytest.approx(-math.sin(math.radians(45)) / r_CAD, abs=1e-9)
    assert np.allclose(K[:, 2], R_CAD / r_CAD)               # omega column constant = R/r


def test_pinv_is_exact_left_inverse(geom):
    K = body_to_wheel_matrix(geom)
    P = wheel_to_body_matrix(geom)
    assert P.shape == (3, 4)
    np.testing.assert_allclose(P @ K, np.eye(3), rtol=0, atol=1e-12)
    # and it is the literal K_inv of inverse_kinematics_solver.m (15-digit rounding)
    np.testing.assert_allclose(P, K_INV_MATLAB, rtol=0, atol=1e-9)
    # the omega-row asymmetry is cos45 exactly (not a modelling error)
    assert P[2, 1] / P[2, 0] == pytest.approx(math.cos(math.radians(45)), abs=1e-12)


def test_uniform_excitation_gives_R_over_r(geom):
    w = wheels_to_body(np.ones(4), geom)
    assert w[0] == pytest.approx(0.0, abs=1e-12) and w[1] == pytest.approx(0.0, abs=1e-12)
    assert 1.0 / w[2] == pytest.approx(2.69907, abs=1e-5)
    assert 1.0 / w[2] == pytest.approx(geom.R_over_r, abs=1e-9)


def test_pure_rotation_gives_equal_wheel_speeds(geom):
    ws = body_to_wheels((0.0, 0.0, 1.0), geom)
    assert np.allclose(ws, ws[0]) and ws[0] == pytest.approx(R_CAD / r_CAD, abs=1e-9)
    ws = body_to_wheels((0.0, 0.0, -2.5), geom)
    assert np.allclose(ws, -2.5 * R_CAD / r_CAD)


def test_body_wheels_body_round_trip_and_batch(geom):
    v = np.array([[0.8, -0.3, 1.2], [0.0, 1.0, 0.0], [-1.5, 0.2, -3.0]])
    ws = body_to_wheels(v, geom)
    assert ws.shape == (3, 4)
    np.testing.assert_allclose(wheels_to_body(ws, geom), v, rtol=0, atol=1e-12)
    # pure forward motion: left wheels (60, 135 deg) spin backwards, right wheels forwards
    wf = body_to_wheels((1.0, 0.0, 0.0), geom)
    assert wf[0] < 0 and wf[1] < 0 and wf[2] > 0 and wf[3] > 0
    assert np.allclose(wf, [-K1, -K3, K3, K1], atol=1e-6)


def test_local_global_round_trip():
    rng = np.random.default_rng(0)
    vx, vy, th = rng.normal(size=50), rng.normal(size=50), rng.uniform(-4, 4, size=50)
    gx, gy = local_to_global(vx, vy, th)
    bx, by = global_to_local(gx, gy, th)
    np.testing.assert_allclose(bx, vx, atol=1e-12); np.testing.assert_allclose(by, vy, atol=1e-12)
    # heading +90 deg: forward (body x) becomes world +y
    gx, gy = local_to_global(1.0, 0.0, math.pi / 2)
    assert gx == pytest.approx(0.0, abs=1e-12) and gy == pytest.approx(1.0, abs=1e-12)


def test_apply_wheel_deadzone():
    w = np.array([0.5, -2.0, 1.566, 1.568, 0.0, -1.567])
    out = apply_wheel_deadzone(w, 1.567)
    np.testing.assert_array_equal(out, [0.0, -2.0, 0.0, 1.568, 0.0, -1.567])
    np.testing.assert_array_equal(apply_wheel_deadzone(w, 0.0), w)       # disabled
    assert out is not w                                                  # no aliasing


def test_legacy_constants_provenance():
    """LEGACY_K_2025 is the same model with r = 24.75 mm and R = 82.28 mm (a third geometry),
    NOT the firmware pair 0.088/0.0265 (R/r = 3.3208 != 3.3245)."""
    K_leg = body_to_wheel_matrix(LEGACY_GEOMETRY_2025)
    np.testing.assert_allclose(K_leg, LEGACY_K_2025, rtol=0, atol=2e-4)
    assert LEGACY_GEOMETRY_2025.wheel_radius_m == pytest.approx(0.5 / 20.2020202020202, abs=1e-6)
    assert LEGACY_GEOMETRY_2025.R_over_r == pytest.approx(3.324525, abs=1e-4)
    assert abs(0.088 / 0.0265 - 3.324525) > 3e-3            # firmware pair does NOT reproduce K4
    assert not LEGACY_K_2025.flags.writeable


def test_geometry_dataclass_validation():
    with pytest.raises(ValueError):
        RobotGeometry(R_contact_m=0.0)
    g = RobotGeometry(wheel_angles_deg=(0, 120, 240))
    assert g.n_wheels == 3 and body_to_wheel_matrix(g).shape == (3, 3)
    assert set(g.to_dict()) >= {"R_contact_m", "wheel_radius_m", "wheel_angles_deg", "R_over_r"}
