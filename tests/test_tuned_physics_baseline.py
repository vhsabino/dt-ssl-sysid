"""tuned_physics_baseline (C3 / WP3): parameter space, Bayesian optimiser, decision rules, objective and
report, all without the dataset; the MuJoCo pieces (default point == untuned route b + delay, floor friction
in the MJCF) under ``requires_mujoco``.

Pre-registration: docs/PREREGISTRO_C3_BASELINE_SINTONIZADA_20261014.md. The run on real data is NOT part of
these tests (frozen until the advisor decides); what is pinned here is that the tuner recovers a generator of
its own model class from synthetic logs (an analytic family that costs nothing), that the untuned point is the
first evaluation, and that the pre-registered verdicts read as written.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pytest

from dtssl.analysis import common as C
from dtssl.analysis import tuned_physics_baseline as T
from dtssl.models import AnalyticFOPDTPlant, DofParam
from dtssl.paths import repo_root

DT = 1.0 / 60.0


def _steps(rng: np.random.Generator, n: int, amp: float) -> np.ndarray:
    u = np.zeros(n)
    k = 0
    while k < n:
        d = int(rng.integers(12, 50))
        u[k:k + d] = rng.uniform(-amp, amp)
        k += d
    return u


def _scaled_params(base: dict[str, DofParam], k_scale: float) -> dict[str, DofParam]:
    return {d: DofParam(K=p.K * k_scale, tau=p.tau, Td=p.Td, placeholder=p.placeholder) for d, p in base.items()}


# ------------------------------------------------------------------ parameter space
def test_param_space_round_trip_and_bounds():
    for p in T.SPACE:
        assert p.to_value(0.0) == pytest.approx(p.lo) and p.to_value(1.0) == pytest.approx(p.hi)
        for u in (0.0, 0.25, 0.5, 0.9, 1.0):
            assert p.to_unit(p.to_value(u)) == pytest.approx(u, abs=1e-12)
        assert p.to_value(-1.0) == pytest.approx(p.lo) and p.to_value(2.0) == pytest.approx(p.hi)   # clipped
    u = T.values_to_unit(T.DEFAULTS)
    assert u.shape == (len(T.SPACE),) and np.all((u > 0.0) & (u < 1.0))          # the untuned point is interior
    assert T.unit_to_values(u) == pytest.approx(T.DEFAULTS, rel=1e-12)
    with pytest.raises(ValueError):
        T.unit_to_values([0.5, 0.5])
    mu = T.Param("mu", 0.4, 1.6)
    assert math.isclose(mu.to_value(0.5), math.sqrt(0.4 * 1.6))                   # log scale: geometric midpoint


def test_world_opts_set_floor_and_roller_friction_to_the_same_mu():
    from dtssl.physics.mjcf import RouteBOptions, SolverOptions

    o = T.world_opts(dict(mu=0.55, impratio=7.0, kv_wheel=0.3, wheel_torque_max=0.8, gear_ratio=2.5))
    assert o["floor_friction"] == 0.55 and o["route_b"].roller_friction == 0.55
    assert o["route_b"].kv_wheel == 0.3 and o["route_b"].wheel_torque_max == 0.8 and o["route_b"].gear_ratio == 2.5
    assert o["solver"].impratio == 7.0 and o["solver"].timestep == SolverOptions().timestep
    assert o["route_b"].roller_damping == RouteBOptions().roller_damping      # everything else stays default
    d = T.world_opts(T.DEFAULTS)
    assert d["route_b"] == RouteBOptions() and d["solver"] == SolverOptions() and d["floor_friction"] == 1.0


# ------------------------------------------------------------------ optimiser
def test_bayes_opt_finds_the_minimum_of_a_quadratic_deterministically():
    pytest.importorskip("sklearn")
    target = np.array([0.3, 0.7])

    def f(u):
        return float(np.sum((np.asarray(u) - target) ** 2))

    r1 = T.bayes_opt(f, 2, n_init=8, n_iter=12, seed=3, n_candidates=512)
    r2 = T.bayes_opt(f, 2, n_init=8, n_iter=12, seed=3, n_candidates=512)
    assert r1["optimizer"] == "gp-ei" and r1["X"].shape == (20, 2) and r1["y"].shape == (20,)
    assert np.linalg.norm(r1["best_x"] - target) < 0.05 and r1["best_y"] < 0.0025
    assert np.array_equal(r1["X"], r2["X"]) and np.array_equal(r1["y"], r2["y"])           # seeded: bit-identical
    design_only = T.bayes_opt(f, 2, n_init=8, n_iter=0, seed=3)
    assert design_only["X"].shape == (8, 2) and design_only["best_y"] >= r1["best_y"]
    x0 = np.array([0.31, 0.69])
    r3 = T.bayes_opt(f, 2, n_init=4, n_iter=0, seed=3, x0=x0)
    assert np.array_equal(r3["X"][0], x0) and r3["best_index"] == 0


def test_near_optimal_spread_flags_what_the_objective_does_not_pin_down():
    X = np.array([[0.5, 0.1], [0.5, 0.9], [0.52, 0.5], [0.1, 0.5]])
    y = np.array([1.0, 1.01, 1.005, 3.0])                       # the second coordinate is free, the first is not
    s = T.near_optimal_spread(X, y, space=(T.Param("a", 1, 10), T.Param("b", 1, 10)), tol=0.02)
    assert s["n_points"] == 3
    assert s["params"]["a"]["identified"] and s["params"]["a"]["span"] == pytest.approx(0.02)
    assert not s["params"]["b"]["identified"] and s["params"]["b"]["span"] == pytest.approx(0.8)
    assert s["params"]["b"]["value_min"] == pytest.approx(10 ** 0.1) and s["params"]["b"]["value_max"] == pytest.approx(10 ** 0.9)


# ------------------------------------------------------------------ verdicts
def test_verdict_t1_reads_twin_tuned_and_tie():
    twin = np.array([0.040, 0.042, 0.038, 0.045, 0.041, 0.039, 0.043, 0.044, 0.040, 0.042])
    assert T.verdict_t1(twin, twin + 0.01)["reading"] == "twin"                 # twin better everywhere
    assert T.verdict_t1(twin, twin - 0.01)["reading"] == "tuned"                # tuned better everywhere
    mixed = twin + np.array([0.01, -0.01] * 5)
    v = T.verdict_t1(twin, mixed)
    assert v["reading"] == "tie" and v["twin_beats_tuned"]["wins"] == 5 and v["tuned_beats_twin"]["wins"] == 5
    seven = twin + np.array([0.01] * 7 + [-0.01] * 3)                           # 7/10 is below the gate
    assert T.verdict_t1(twin, seven)["reading"] == "tie"
    t2 = T.verdict_t2(0.0477, 0.0350)
    assert t2["passes"] and t2["gain"] == pytest.approx(1 - 0.0350 / 0.0477)
    assert not T.verdict_t2(0.0477, 0.0400)["passes"]
    t3 = T.verdict_t3(0.050, 0.030, 0.0477, 0.0400)                            # train gain 40 %, hold-out 16 %
    assert t3["overfitting"] and not t3["passes"] and t3["ratio"] == pytest.approx((1 - 0.04 / 0.0477) / 0.4)
    assert T.verdict_t3(0.050, 0.030, 0.0477, 0.0330)["passes"]
    assert T.verdict_t3(0.050, 0.050, 0.0477, 0.0477)["passes"] and math.isnan(T.verdict_t3(0.05, 0.05, 0.1, 0.1)["ratio"])


def test_validity_requires_reproducibility_and_interior_optimum():
    res = dict(best_x=np.array([0.5, 0.5, 0.5, 0.5, 0.5]), best_y=0.03)
    assert T.validity(res, 0.03)["passes"]
    assert not T.validity(res, 0.03 + 1e-3)["reproducible"]
    res2 = dict(best_x=np.array([0.0, 1.0, 0.5, 0.5, 0.5]), best_y=0.03)
    v = T.validity(res2, 0.03)
    assert v["at_bound"] == ["mu", "impratio"] and not v["passes"]
    assert T.validity(dict(best_x=np.array([0.0, 0.5, 0.5, 0.5, 0.5]), best_y=0.03), 0.03)["passes"]


# ------------------------------------------------------------------ objective + optimiser end to end (analytic family)
@pytest.fixture(scope="module")
def ctx():
    return C.make_context(repo_root(), seed=42)


def _synthetic_segments(ctx, k_scale: float, n_seg: int, seed: int) -> list:
    rng = np.random.default_rng(seed)
    truth = AnalyticFOPDTPlant(_scaled_params(ctx.params, k_scale))
    segs = []
    for i in range(n_seg):
        n = 480
        cmd = np.column_stack([_steps(rng, n, 1.2), _steps(rng, n, 1.2), _steps(rng, n, 2.0)])
        t = np.arange(n) * DT
        base = T.synthetic_segment("base", t, cmd, np.zeros((n, 3)), DT)
        segs.append(T.simulate_segment(truth, base, name=f"synthetic_{i}"))
    return segs


def test_synthetic_segment_is_loader_shaped(ctx):
    segs = _synthetic_segments(ctx, 1.0, 1, 0)
    s = segs[0]
    assert s.n == 480 and s.ts == DT and s.meta["event"] == "synthetic_0"
    assert s.pose0 == (0.0, 0.0, 0.0) and np.all(np.isfinite(s.velb_x)) and np.all(np.diff(s.t) > 0)
    assert np.hypot(s.pos_x[-1], s.pos_y[-1]) > 0.1                                 # it moved


def test_tuner_recovers_a_known_gain_from_synthetic_logs(ctx):
    """An analytic family (the twin's theta with every K scaled by one parameter) stands in for route b: the
    tuner has to recover the generator's scale from the harness objective on synthetic training logs, and the
    pre-registered verdicts have to read as expected when the model class contains the generator."""
    pytest.importorskip("sklearn")
    space = (T.Param("k_scale", 0.5, 2.0),)
    truth = 1.3
    train = _synthetic_segments(ctx, truth, 2, seed=1)
    test = _synthetic_segments(ctx, truth, 2, seed=2)
    factory = lambda values: AnalyticFOPDTPlant(_scaled_params(ctx.params, values["k_scale"]))   # noqa: E731
    r = T.compute_from_segments(ctx, train, test, factory, space=space, defaults=dict(k_scale=1.0),
                                n_init=8, n_iter=8, seed=5)
    assert r["optimizer"]["n_eval"] == 16 and r["history"][0]["values"]["k_scale"] == pytest.approx(1.0)
    assert abs(r["best_values"]["k_scale"] - truth) / truth < 0.05
    assert r["J_train"]["tuned"] < 0.25 * r["J_train"]["untuned"]
    h = r["holdout"]
    assert h["tuned"]["J"] < 0.25 * h["untuned"]["J"] and h["tuned"]["n_windows"] == h["untuned"]["n_windows"] > 0
    assert len(h["tuned"]["per_event_model"]) == 2 and r["t2"]["passes"] and r["t3"]["passes"]
    assert r["validity"]["reproducible"] and r["validity"]["passes"]
    assert r["near_optimal"]["params"]["k_scale"]["identified"]
    assert r["sanity_twin_event_median"] == pytest.approx(float(np.median(h["tuned"]["per_event_twin"])))
    lines = T.render(ctx, dict(r, control=None, labels=list(T.LABELS), dropped=[], load_s=0.0,
                              train_events=["a", "b"], test_events=["c", "d"]))
    text = "\n".join(lines)
    assert "k_scale" in text and "T1" in text and "VALIDO" in text and "Leitura" in text
    json.dumps(T._jsonable(r))


# ------------------------------------------------------------------ MuJoCo pieces
@pytest.mark.requires_mujoco
def test_default_point_reproduces_the_untuned_route_b_with_delay(ctx):
    from dtssl.sim.world_plant import make_harness_plant

    ref = make_harness_plant("mujoco-rollers-delay", ctx.params)
    tuned = T.make_tuned_plant(T.DEFAULTS, ctx.params)
    try:
        assert tuned.world.floor_friction == 1.0 and tuned.world.route_b.roller_friction == 1.0
        cmds = [(0.8, -0.3, 1.0)] * 20 + [(-0.5, 0.6, -2.0)] * 20
        poses = []
        for p in (ref, tuned):
            p.reset((0.0, 0.0, 0.3), (0.0, 0.0, 0.0))
            p.prime_delay([])
            poses.append(np.array([p.step(c, DT) for c in cmds]))
        np.testing.assert_allclose(poses[0], poses[1], atol=1e-9)
    finally:
        ref.close()
        tuned.close()


@pytest.mark.requires_mujoco
def test_tuned_values_reach_the_mjcf(ctx):
    import xml.etree.ElementTree as ET

    from dtssl.sim.entities import Scene

    vals = dict(mu=0.55, impratio=7.0, kv_wheel=0.3, wheel_torque_max=0.8, gear_ratio=2.5)
    plant = T.make_tuned_plant(vals, ctx.params)
    try:
        root = ET.fromstring(plant.world.build_xml(Scene.default(1, 0)))
        floor = next(g for g in root.iter("geom") if g.get("name") == "floor")
        assert floor.get("friction").startswith("0.55")
        assert float(root.find("option").get("impratio")) == 7.0
        rollers = [g for g in root.iter("geom") if (g.get("friction") or "").startswith("0.55") and g is not floor]
        assert rollers, "roller geoms carry mu too"
        act = next(a for a in root.iter("velocity") if a.get("name", "").endswith("act_wheel0"))
        assert float(act.get("kv")) == 0.3 and act.get("forcerange").startswith("-0.8")
    finally:
        plant.close()
