"""Sanidade das plantas (alem do golden)."""
import math

import numpy as np
import pytest

from dtssl import (AnalyticFOPDTPlant, IdealKinematicPlant,
                           load_twin_params, wrap_to_pi)

TS = 1.0 / 60.0


def _const_drive(plant, cmd, nsteps, pose0=(0.0, 0.0, 0.0), velb0=(0.0, 0.0, 0.0)):
    plant.reset(pose0=pose0, velb0=velb0)
    poses = [pose0]
    for _ in range(nsteps):
        poses.append(plant.step(cmd, TS))
    return np.array(poses)


# ----- AnalyticFOPDT: resposta ao degrau do lag (DOF w, Td=0) -----
def test_step_response_reaches_63pct_at_tau():
    """After the dead time (ceil(Td/Ts) samples) the ZOH-exact lag reaches
    K*u*(1-exp(-k*Ts/tau)) at step k of the response; checked at k = round(tau/Ts)."""
    p = load_twin_params()
    plant = AnalyticFOPDTPlant(p)
    plant.reset(pose0=(0, 0, 0), velb0=(0, 0, 0))
    u = 1.0
    m = 0 if p["w"].Td <= 0 else math.ceil(p["w"].Td / TS - 1e-9)   # dead-time samples
    k_tau = round(p["w"].tau / TS)
    for _ in range(m + k_tau):
        plant.step((0.0, 0.0, u), TS)
    vw = plant.body_velocity[2]
    expected = p["w"].K * u * (1.0 - math.exp(-k_tau * TS / p["w"].tau))
    assert abs(vw - expected) < 1e-6, (vw, expected)


def test_step_response_steady_state_is_K_times_u():
    p = load_twin_params()
    plant = AnalyticFOPDTPlant(p)
    poses = _const_drive(plant, (1.0, 0.0, 1.0), 1200)   # 20 s, >> tau e Td
    vx, vy, vw = plant.body_velocity
    assert abs(vx - p["vx"].K * 1.0) < 1e-3
    assert abs(vw - p["w"].K * 1.0) < 1e-3


def test_dead_time_vx_zero_during_Td():
    p = load_twin_params()
    plant = AnalyticFOPDTPlant(p)
    plant.reset(pose0=(0, 0, 0), velb0=(0, 0, 0))
    m = math.ceil(p["vx"].Td / TS)          # = 5 amostras (ceil, NAO round=4)
    assert m == 5
    for _ in range(m):                      # durante o atraso, vx do corpo ~ 0
        plant.step((1.0, 0.0, 0.0), TS)
        assert abs(plant.body_velocity[0]) < 1e-12
    plant.step((1.0, 0.0, 0.0), TS)         # passo seguinte ja responde
    assert plant.body_velocity[0] > 0.0


# ----- IdealKinematic -----
def test_ideal_velocity_equals_command():
    plant = IdealKinematicPlant()
    plant.reset(pose0=(0, 0, 0), velb0=(0, 0, 0))
    plant.step((0.7, -0.3, 0.5), TS)
    assert plant.body_velocity == pytest.approx((0.7, -0.3, 0.5))


def test_ideal_straight_line_when_w_zero():
    v = 1.3
    plant = IdealKinematicPlant()
    poses = _const_drive(plant, (v, 0.0, 0.0), 120, velb0=(v, 0.0, 0.0))
    t = np.arange(poses.shape[0]) * TS
    assert np.allclose(poses[:, 1], 0.0, atol=1e-12)      # y == 0
    assert np.allclose(poses[:, 2], 0.0, atol=1e-12)      # theta == 0
    assert np.allclose(poses[:, 0], v * t, atol=1e-9)     # x = v*t


def test_ideal_circle_radius():
    v, w = 1.0, 2.0
    r = v / abs(w)                                        # raio esperado = 0.5 m
    plant = IdealKinematicPlant()
    n = round((2 * math.pi / abs(w)) / TS)                # uma volta
    poses = _const_drive(plant, (v, 0.0, w), n, velb0=(v, 0.0, w))
    center = np.array([0.0, r])                           # CCW, heading 0, start (0,0)
    radii = np.hypot(poses[:, 0] - center[0], poses[:, 1] - center[1])
    assert np.allclose(radii, r, rtol=5e-3), (radii.min(), radii.max())
    # fecha o circulo perto do inicio
    assert np.hypot(poses[-1, 0], poses[-1, 1]) < 0.02


# ----- wrap de angulo -----
def test_angle_wrap_179_to_minus_179_is_2deg():
    err = wrap_to_pi(math.radians(179) - math.radians(-179))
    assert abs(math.degrees(err)) == pytest.approx(2.0, abs=1e-9)
    assert wrap_to_pi(math.radians(358)) == pytest.approx(math.radians(-2.0), abs=1e-9)
