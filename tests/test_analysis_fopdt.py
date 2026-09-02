"""``common.simulate_fopdt``: the plant alignment equals ``AnalyticFOPDTPlant`` step by step,
the legacy alignment equals the recurrence the 2026-08 scripts used, and the two differ by
exactly one sample of transport delay (no dataset needed)."""
from __future__ import annotations

import math

import numpy as np
import pytest

from dtssl.analysis import common as C

DT = 1.0 / 60.0


def _legacy_loop(u, dt, K, tau, Td):
    """Verbatim recurrence of scripts/loo_translational.py / r3_closedloop_omega_fit.py."""
    m = int(math.ceil(max(Td, 0.0) / dt))
    a = 1 - math.exp(-dt / max(tau, 1e-4))
    v, o = 0.0, np.empty(len(u))
    for k in range(len(u)):
        ud = u[k - m] if k - m >= 0 else 0.0
        v = v + a * (ud - v)
        o[k] = K * v
    return o


@pytest.fixture(scope="module")
def u():
    rng = np.random.default_rng(0)
    return np.cumsum(rng.normal(size=300)) * 0.02


@pytest.mark.parametrize("K,tau,Td", [(1.1192, 0.0718, 0.06905), (1.0016, 0.0828, 0.08895),
                                      (1.3, 0.03, 0.0), (1.0, 0.0, 0.05)])
def test_legacy_alignment_matches_legacy_loop(u, K, tau, Td):
    a = _legacy_loop(u, DT, K, tau, Td)
    b = C.simulate_fopdt(u, DT, K, tau, Td, align="legacy")
    assert np.max(np.abs(a - b)) < 1e-12


@pytest.mark.parametrize("K,tau,Td,ic", [(1.1192, 0.0718, 0.06905, 0.0), (1.0016, 0.0828, 0.08895, 0.3),
                                         (1.3, 0.03, 0.0, 0.1), (1.0, 0.0, 0.05, 0.0)])
def test_plant_alignment_matches_analytic_plant(u, K, tau, Td, ic):
    a = C.simulate_fopdt_plant(u, DT, K, tau, Td, ic=ic)
    b = C.simulate_fopdt(u, DT, K, tau, Td, ic=ic, align="plant")
    assert np.max(np.abs(a - b)) < 1e-12


def test_legacy_is_plant_with_one_sample_less_delay(u):
    K, tau = 1.1, 0.07
    leg = C.simulate_fopdt(u, DT, K, tau, 5 * DT - 1e-6, align="legacy")   # m = 5
    pl = C.simulate_fopdt(u, DT, K, tau, 4 * DT - 1e-6, align="plant")     # m = 4
    assert np.array_equal(leg, pl)
    # same Td -> plant lags the legacy output by exactly one sample
    a = C.simulate_fopdt(u, DT, K, tau, 0.06905, align="legacy")
    b = C.simulate_fopdt(u, DT, K, tau, 0.06905, align="plant")
    assert np.allclose(b[1:], a[:-1]) and b[0] == 0.0


def test_upsample_matches_fine_grid_reference(u):
    """fig_fit_holdout_vxvy fine-grid recurrence (Ts/20, fractional delay) == upsample=20."""
    K, tau, Td, x0, UP = 1.1192, 0.0718, 0.06905, 0.51, 20
    n = len(u); dtf = DT / UP; nf = (n - 1) * UP + 1
    uf = u[np.minimum(np.arange(nf) // UP, n - 1)]
    idx = np.floor(np.arange(nf) - Td / dtf + 1e-9).astype(int)
    ud = np.where(idx >= 0, uf[np.maximum(idx, 0)], 0.0)
    e = np.exp(-dtf / tau); v = np.empty(nf); v[0] = x0
    for j in range(1, nf):
        v[j] = e * v[j - 1] + (1.0 - e) * ud[j - 1]
    ref = K * v[::UP]
    out = C.simulate_fopdt(u, DT, K, tau, Td, ic=x0, align="plant", upsample=UP)
    assert out.shape == (n,)
    assert np.max(np.abs(out - ref)) < 1e-12


def test_bad_arguments():
    with pytest.raises(ValueError):
        C.simulate_fopdt(np.zeros(3), DT, 1, 0.1, 0.0, align="nope")
    with pytest.raises(ValueError):
        C.simulate_fopdt(np.zeros(3), DT, 1, 0.1, 0.0, upsample=0)
    assert C.simulate_fopdt(np.zeros(0), DT, 1, 0.1, 0.0).size == 0


def test_variant_params_and_theta_vector():
    from dtssl.models import DofParam
    base = {"vx": DofParam(1.1, 0.07, 0.069), "vy": DofParam(1.05, 0.13, 0.056), "w": DofParam(1.0, 0.08, 0.089)}
    v = C.variant_params(base, True, False, True)
    assert v["vx"] == DofParam(1.1, 0.0, 0.069) and v["w"].placeholder is False
    th = C.theta_from_vector([1, 2, 3, 4, 5, 6, 7, 8, 9])
    assert (th["vx"].K, th["vy"].tau, th["w"].Td) == (1.0, 5.0, 9.0)
    with pytest.raises(ValueError):
        C.theta_from_vector([1, 2, 3])


def test_fit_percent():
    y = np.array([1.0, 2.0, 3.0, 4.0])
    assert C.fit_percent(y, y) == pytest.approx(100.0)
    assert C.fit_percent(y, np.full(4, y.mean())) == pytest.approx(0.0)
