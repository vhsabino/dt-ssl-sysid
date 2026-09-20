"""WorldPlant: a World backend behind the harness Plant interface (reset / prime_delay / step)."""
from __future__ import annotations

import numpy as np
import pytest

from dtssl.models import AnalyticFOPDTPlant, load_twin_params
from dtssl.sim.rollout import free_run
from dtssl.sim.world_plant import BACKEND_PLANTS, WorldPlant, make_harness_plant

DT = 1.0 / 60.0
POSE0 = (1.0, -0.5, 0.7)
VELB0 = (0.3, -0.1, 0.5)


def _cmds(seed: int = 0, n: int = 90):
    rng = np.random.default_rng(seed)
    t = np.arange(n) * DT
    return (np.column_stack([1.2 * np.sin(2 * np.pi * 0.5 * t), 0.8 * np.cos(2 * np.pi * 0.3 * t),
                             2.0 * np.sin(2 * np.pi * 0.4 * t)]),
            rng.uniform(-1.0, 1.0, (16, 3)))


def test_twinworld_adapter_is_bit_identical_to_the_analytic_plant():
    """The wiring check without MuJoCo: TwinWorld's FOPDT plant through the adapter == AnalyticFOPDTPlant."""
    P = load_twin_params()
    cmds, prev = _cmds()
    ref = free_run(AnalyticFOPDTPlant(P), cmds, POSE0, VELB0, DT, prev_cmds=prev)
    plant = make_harness_plant("world:fopdt", P)
    assert plant.params is P
    got = free_run(plant, cmds, POSE0, VELB0, DT, prev_cmds=prev)
    assert np.array_equal(got, ref)
    # a second window re-anchors cleanly (no state leaking across windows)
    got2 = free_run(plant, cmds[::-1], (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), DT, prev_cmds=None)
    ref2 = free_run(AnalyticFOPDTPlant(P), cmds[::-1], (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), DT, prev_cmds=None)
    assert np.array_equal(got2, ref2)


def test_make_harness_plant_names():
    assert set(BACKEND_PLANTS) == {"mujoco-velocity", "mujoco-rollers", "mujoco-rollers-delay"}
    assert type(make_harness_plant("fopdt")).__name__ == "AnalyticFOPDTPlant"
    assert type(make_harness_plant("ideal")).__name__ == "IdealKinematicPlant"
    with pytest.raises(KeyError):
        make_harness_plant("nope")


def test_route_b_delay_tap_matches_the_fopdt_tap():
    """delay='theta' applies ud[j] = u[j - ceil(Td/dt)] with the primed history, exactly like the FOPDT plant."""
    P = load_twin_params()
    plant = WorldPlant.__new__(WorldPlant)           # only the delay machinery is exercised here
    plant._Td = np.array([P[d].Td for d in ("vx", "vy", "w")])
    plant._hist, plant._base, plant._k = [], 0, 0
    prev = [np.array([float(i), 10.0 + i, 20.0 + i]) for i in range(16)]
    plant._hist, plant._base = list(prev), len(prev)
    out = [plant._delayed(np.array([100.0 + j, 200.0 + j, 300.0 + j]), DT) for j in range(8)]
    for i, dof in enumerate(("vx", "vy", "w")):
        n = int(np.ceil(P[dof].Td / DT - 1e-9))
        for j in range(8):
            src = j - n
            expect = (prev[16 + src][i] if src < 0 else [100.0, 200.0, 300.0][i] + src)
            assert out[j][i] == pytest.approx(expect), (dof, j)


@pytest.mark.requires_mujoco
def test_mujoco_velocity_tracks_the_analytic_plant():
    pytest.importorskip("mujoco")
    P = load_twin_params()
    cmds, prev = _cmds()
    ref = free_run(AnalyticFOPDTPlant(P), cmds, POSE0, VELB0, DT, prev_cmds=prev)
    plant = make_harness_plant("mujoco-velocity", P)
    try:
        assert plant.params is P
        got = free_run(plant, cmds, POSE0, VELB0, DT, prev_cmds=prev)
        e = np.hypot(*(got[:, :2] - ref[:, :2]).T)
        assert e.max() < 1e-3                                    # embedding: sub-millimetre over 1.5 s
        assert np.abs(got[:, 2] - ref[:, 2]).max() < 1e-6      # heading: hinge angle, unwrapped
        assert np.array_equal(got[0], np.asarray(POSE0))
    finally:
        plant.close()


@pytest.mark.requires_mujoco
def test_mujoco_rollers_runs_and_is_finite_and_delay_variant_differs():
    pytest.importorskip("mujoco")
    P = load_twin_params()
    cmds, prev = _cmds()
    a = make_harness_plant("mujoco-rollers", P)
    b = make_harness_plant("mujoco-rollers-delay", P)
    try:
        assert a.params is None and b.params is P              # grid: config theta for both (harness rule)
        ga = free_run(a, cmds, POSE0, VELB0, DT, prev_cmds=prev)
        gb = free_run(b, cmds, POSE0, VELB0, DT, prev_cmds=prev)
        assert np.isfinite(ga).all() and np.isfinite(gb).all()
        assert np.array_equal(ga[0], np.asarray(POSE0)) and np.array_equal(gb[0], np.asarray(POSE0))
        assert np.abs(ga - gb).max() > 1e-4                    # the delay changes the trajectory
        # a straight command gives a straight, forward trajectory (sign conventions)
        a.reset((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
        for _ in range(60):
            x, y, th = a.step((1.0, 0.0, 0.0), DT)
        assert 0.8 < x < 1.05 and abs(y) < 0.05 and abs(th) < 0.05
    finally:
        a.close()
        b.close()
