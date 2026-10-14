"""coupled_mimo_check: estimator, plant, decision rules and report, all without the dataset.

The module is pre-registered (docs/PREREGISTRO_MIMO_CHECK_20260923.md); these tests pin the pieces the
pre-registration relies on: the separable output-error estimator recovers known systems, the diagonal
arm is exactly the per-DOF FOPDT structure, the harness plant reproduces ``AnalyticFOPDTPlant`` and the
offline simulation, the omitted-variable mechanism behind M2 behaves as stated, and the paper's vision
chain does not invent coupling (negative control on synthetic logs).
"""
from __future__ import annotations

import json
import math

import numpy as np
import pytest

from dtssl.analysis import common as C
from dtssl.analysis import coupled_mimo_check as M
from dtssl.models import AnalyticFOPDTPlant, DofParam, load_twin_params
from dtssl.paths import repo_root
from dtssl.sim.rollout import free_run

DT = 1.0 / 60.0
SMALL_GRID = tuple(float(x) for x in np.geomspace(0.01, 0.6, 41))


def _steps(rng: np.random.Generator, n: int, amp: float = 1.5) -> np.ndarray:
    u = np.zeros(n)
    k = 0
    while k < n:
        d = int(rng.integers(10, 60))
        u[k:k + d] = rng.uniform(-amp, amp)
        k += d
    return u


def _events(model: M.MimoModel, n_events: int, seed: int = 0, corr: float = 0.0,
            noise: float = 0.0) -> list[dict]:
    """Synthetic (U, Y) from ``model``; ``corr`` makes u_w = corr * u_vy + independent steps."""
    rng = np.random.default_rng(seed)
    out = []
    for e in range(n_events):
        n = int(rng.integers(300, 600))
        U = np.column_stack([_steps(rng, n) for _ in range(3)])
        if corr:
            U[:, 2] = corr * U[:, 1] + 0.3 * _steps(rng, n)
        Y = M.simulate(model, U, rng.normal(size=3) * 0.2)
        if noise:
            Y = Y + noise * rng.standard_normal(Y.shape)
        out.append(dict(label="synthetic", event=f"ev{e:02d}", U=U, Y=Y, holdout=e >= n_events - 4))
    return out


def _truth(coupled: bool = True) -> M.MimoModel:
    B = np.array([[0.22, 0.02, 0.00], [0.00, 0.14, -0.03], [0.05, 0.08, 0.18]])
    if not coupled:
        B = np.diag(np.diag(B))
    return M.MimoModel(A=np.array([0.80, 0.87, 0.82]), B=B,
                       M=np.array([[5] * 3, [4] * 3, [6] * 3]), coupled=coupled, dt=DT)


@pytest.fixture(scope="module")
def theta():
    return load_twin_params(repo_root() / "config" / "twin_params.json")


# -------------------------------------------------------------------- estimator
def test_estimator_recovers_a_coupled_system_exactly():
    truth = _truth(True)
    ev = [(e["U"], e["Y"]) for e in _events(truth, 12)]
    fit = M.fit_model(ev, DT, truth.M, True)
    assert np.allclose(fit.A, truth.A, atol=1e-7)
    assert np.allclose(fit.B, truth.B, atol=1e-7)
    assert np.allclose(fit.G, truth.G, atol=1e-6)


def test_diagonal_truth_gives_no_cross_terms_and_m1_false():
    truth = _truth(False)
    items = _events(truth, 12, seed=1)
    train = [(e["U"], e["Y"]) for e in items if not e["holdout"]]
    test = [e for e in items if e["holdout"]]
    diag = M.fit_model(train, DT, truth.M, False)
    coup = M.fit_model(train, DT, truth.M, True)
    assert np.allclose(diag.B, truth.B, atol=1e-7)
    off = coup.B[~np.eye(3, dtype=bool)]
    assert np.abs(off).max() < 1e-7
    sc = M.score(dict(diagonal=diag, coupled=coup), test)
    ratios = M.contribution_ratios(coup, [(e["U"], e["Y"]) for e in test])
    v = M.verdict_m1(sc["pooled"], ratios)
    assert not v["coupling_matters"]
    assert all(abs(v["per_dof"][d]["fit_gain_pp"]) < 1e-6 for d in M.DOFS)


def test_pair_delay_search_finds_the_true_delays():
    truth = _truth(True)
    truth.B[0, 2] = 0.04                                   # every used cross term non-zero
    truth.B[1, 0] = 0.03
    truth.M = np.array([[5, 3, 7], [2, 4, 6], [8, 5, 6]])
    ev = [(e["U"], e["Y"]) for e in _events(truth, 10, seed=2)]
    fit = M.search_pair_delays(ev, DT, True, m_max=9, tau_grid=SMALL_GRID)
    assert fit.M.tolist() == truth.M.tolist()
    assert np.allclose(fit.B, truth.B, atol=1e-6)


def test_promoted_model_is_the_fopdt_on_the_plant_alignment(theta):
    pm = M.promoted_model(theta, DT)
    assert M.plant_delays(theta, DT) == [5, 4, 6]
    rng = np.random.default_rng(3)
    U = np.column_stack([_steps(rng, 400) for _ in range(3)])
    y0 = np.array([0.4, -0.2, 0.7])
    Y = M.simulate(pm, U, y0)
    for i, d in enumerate(M.DOFS):
        p = theta[d]
        ref = C.simulate_fopdt(U[:, i], DT, p.K, p.tau, p.Td, ic=y0[i] / p.K, align="plant")
        assert np.abs(Y[:, i] - ref).max() < 1e-12
    assert np.allclose(np.diag(pm.G), [theta[d].K for d in M.DOFS])


# -------------------------------------------------------------------- harness plant
def test_coupled_plant_reproduces_analytic_plant_when_diagonal(theta):
    pm = M.promoted_model(theta, DT)
    rng = np.random.default_rng(4)
    for _ in range(3):
        win = np.column_stack([_steps(rng, 90) for _ in range(3)])
        prev = np.column_stack([_steps(rng, 15) for _ in range(3)])
        pose0 = tuple(rng.normal(size=3))
        velb0 = tuple(rng.normal(size=3) * 0.5)
        a = free_run(AnalyticFOPDTPlant(theta), win, pose0, velb0, DT, prev_cmds=prev)
        b = free_run(M.CoupledFirstOrderPlant(pm, theta), win, pose0, velb0, DT, prev_cmds=prev)
        assert np.abs(a - b).max() < 1e-12


def test_coupled_plant_velocity_matches_offline_simulation():
    truth = _truth(True)
    rng = np.random.default_rng(5)
    U = np.column_stack([_steps(rng, 120) for _ in range(3)])
    y0 = np.array([0.3, -0.1, 0.5])
    plant = M.CoupledFirstOrderPlant(truth)
    plant.reset((0.0, 0.0, 0.0), tuple(y0))
    vel = [plant.body_velocity]
    for k in range(U.shape[0] - 1):
        plant.step(U[k], DT)
        vel.append(plant.body_velocity)
    assert np.abs(np.array(vel) - M.simulate(truth, U, y0)).max() < 1e-12


# -------------------------------------------------------------------- mechanism behind M2
def test_translation_to_yaw_coupling_biases_the_diagonal_yaw_gain_and_coupling_removes_it():
    truth = M.MimoModel(A=np.array([0.80, 0.87, 0.82]),
                        B=np.array([[0.22, 0.0, 0.0], [0.0, 0.14, 0.0], [0.0, 0.072, 0.18]]),
                        M=np.array([[5] * 3, [4] * 3, [6] * 3]), coupled=True, dt=DT)
    assert truth.G[2, 2] == pytest.approx(1.0)                 # direct yaw gain = 1
    items = _events(truth, 16, seed=6, corr=0.7)               # yaw command correlated with vy
    train = [(e["U"], e["Y"]) for e in items if not e["holdout"]]
    diag = M.fit_model(train, DT, truth.M, False)
    coup = M.fit_model(train, DT, truth.M, True)
    v = M.verdict_m2(float(diag.G[2, 2]), float(coup.G[2, 2]), 1.0)
    assert v["premise"] and v["inflation_diag"] > 0.10
    assert abs(v["inflation_coupled"]) < 1e-6
    assert v["status"] == "CORROBORADA"


# -------------------------------------------------------------------- decision rules
def test_verdict_rules():
    pooled = dict(diagonal=dict(vx=80.0, vy=80.0, w=40.0), coupled=dict(vx=80.5, vy=83.5, w=41.0))
    ratios = {d: dict(total=r) for d, r in (("vx", 0.5), ("vy", 0.05), ("w", 0.3))}
    v = M.verdict_m1(pooled, ratios)
    assert not v["coupling_matters"]                             # gain and ratio on different DOFs
    ratios["vy"]["total"] = 0.12
    assert M.verdict_m1(pooled, ratios)["coupling_matters"]
    assert M.verdict_m2(1.05, 1.0, 1.0)["status"].startswith("nao testavel")
    assert M.verdict_m2(1.40, 1.25, 1.0)["status"] == "FALSIFICADA"
    assert M.verdict_m2(1.40, 1.19, 1.0)["status"] == "CORROBORADA"
    assert M.verdict_m2(1.40, 0.81, 1.0)["status"] == "CORROBORADA"    # symmetric band
    good = M.verdict_m3(np.full(10, 0.03) + np.arange(10) * 1e-3, np.full(10, 0.05) + np.arange(10) * 1e-3)
    assert good["wins"] == 10 and good["improves"] and good["p"] < 0.01
    bad = M.verdict_m3(np.full(10, 0.05), np.full(10, 0.05))
    assert not bad["improves"] and bad["p"] == 1.0


# -------------------------------------------------------------------- paper chain: negative control
def test_vision_chain_does_not_invent_coupling(theta):
    from dtssl.analysis import identifiability_insilico as II

    evs = II.synthetic_events(DT)                                # R3: PRBS steps on the three DOFs
    plant = AnalyticFOPDTPlant(theta)
    items = []
    for n, ev in enumerate(evs):
        pose = II.simulate_poses_plant(plant, ev, DT)
        cmd_df, rob_df = II.measurement_tables(ev, pose, 0.0, 0.0, None)
        s = M.event_series(cmd_df, rob_df, DT)
        assert s is not None
        items.append(dict(label="R3", event=ev.name, U=s[0], Y=s[1], holdout=n >= len(evs) - 3))
    r = M.compute_from_series(items, theta, DT, pair_delays=False, n_boot=0, stg_sensitivity=False)
    Gd, Gc = r["models"]["diagonal"]["G"], r["models"]["coupled"]["G"]
    for i, d in enumerate(M.DOFS):
        assert abs(Gd[i][i] - theta[d].K) / theta[d].K < M.NEG_CONTROL_TOL
        assert abs(Gc[i][i] - theta[d].K) / theta[d].K < M.NEG_CONTROL_TOL
        assert r["ratios"][d]["total"] < M.CONTRIB_MIN
    assert not r["m1"]["coupling_matters"]
    assert r["m2"]["status"].startswith("nao testavel")


# -------------------------------------------------------------------- report
def test_run_writes_the_three_artefacts(tmp_path, monkeypatch, theta):
    truth = _truth(True)
    items = _events(truth, 10, seed=7, noise=0.01)
    for e in items:                                              # no training event of the game label:
        e["label"] = "shoot_to_goal" if e["holdout"] else e["label"]   # the M2 sensitivity is skipped
    monkeypatch.setattr(M, "load_events", lambda ctx, *a, **k: items)
    r = M.run(out=tmp_path, n_boot=3, pair_delays=True, harness=False, quiet=True)
    for key in ("path", "json", "csv"):
        assert r[key].parent == tmp_path and r[key].is_file()
    text = r["path"].read_text(encoding="utf-8")
    assert text.startswith("# Checagem MIMO") and "_Proveniencia: commit" in text
    assert "**M1:" in text and "M2 (mecanismo" in text and "atrasos por par" in text
    blob = json.loads(r["json"].read_text(encoding="utf-8"))
    assert blob["n_test"] == 4 and "bootstrap" in blob and "_models" not in blob
    assert math.isfinite(blob["m2"]["G_diag"])
    assert r["path"].name.startswith("coupled_mimo_check_")


def test_control_name_is_validated(monkeypatch, tmp_path):
    ctx = C.make_context(out=tmp_path)
    with pytest.raises(ValueError):
        M.compute(ctx, control="grsim")


def test_mimo_model_json_roundtrip_fields():
    js = _truth(True).to_json()
    assert set(js) >= {"A", "B", "M", "tau_s", "G", "coupled", "dt", "sse"}
    assert js["tau_s"][0] == pytest.approx(-DT / math.log(0.80))


def test_plant_delays_for_an_arbitrary_theta():
    th = {d: DofParam(K=1.0, tau=0.1, Td=0.05) for d in M.DOFS}
    assert M.plant_delays(th, DT) == [3, 3, 3]
