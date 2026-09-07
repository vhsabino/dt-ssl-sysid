"""C1 in-silico identifiability (``dtssl.analysis.identifiability_insilico``).

Data-free: the generator + measurement chain + profile estimator recovers the official theta
from the synthetic R3 commands (noise ``none``, deadzone ``off``); the deadzone helper masks the
expected samples; the decision rule; ``run()`` with tiny settings writes the md/csv/json
artefacts. The regimes that replay the dataset (R1/R2) are covered by one ``requires_data`` test.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from dtssl.analysis import common as C
from dtssl.analysis import identifiability_insilico as M
from dtssl.models import DOFS, DofParam

TS = 1.0 / 60.0


@pytest.fixture(scope="module")
def ctx():
    return C.make_context()


def test_synthetic_design_is_seeded_and_above_deadzone(ctx):
    a = M.synthetic_events(ctx.ts)
    b = M.synthetic_events(ctx.ts)
    assert len(a) == M.R3_DESIGN["n_events"] and a[0].n == 600
    assert all(np.array_equal(x.cmd, y.cmd) for x, y in zip(a, b, strict=True))   # fixed design seed
    cmd = np.concatenate([e.cmd for e in a])
    assert np.all(np.abs(cmd[:, :2]) >= 0.6) and np.all(np.abs(cmd[:, :2]) <= 1.5)
    assert np.all(np.abs(cmd[:, 2]) >= 1.5) and np.all(np.abs(cmd[:, 2]) <= 4.0)
    assert np.all(cmd[:, 0] != cmd[:, 1])        # independent sequences per DOF


def test_chain_recovers_theta_star_idealized_cell(ctx):
    """R3 commands, no noise, deadzone off, n_rep = 1: K/tau within 2 %, delay within 1 sample."""
    ex = M._Experiment(ctx, seed=M.SEED, threshold=M.DEADZONE_WHEEL_RAD_S, design=None, align="legacy",
                       m_max=M.M_MAX, nm_options=None)
    for dof in DOFS:
        r = ex.replicate("R3", dof, "none", "off", 0)
        t = ctx.params[dof]
        assert not r["degenerate"]
        assert abs(r["K"] / t.K - 1.0) <= 0.02, (dof, r["K"], t.K)
        assert abs(r["tau"] / t.tau - 1.0) <= 0.02, (dof, r["tau"], t.tau)
        assert abs(r["m_eff"] - t.Td / ctx.ts) <= 1.0, (dof, r["m_eff"], t.Td / ctx.ts)
        assert r["m_eff"] == M.plant_delay_samples(t.Td, ctx.ts)      # exact integer delay of the plant
        assert r["fit_holdout_mean"] > 95.0 and r["fit_train_median"] > 95.0


def test_profile_beats_or_matches_plain_nm3_on_noise_free_data(ctx):
    ex = M._Experiment(ctx, seed=M.SEED, threshold=M.DEADZONE_WHEEL_RAD_S, design=None, align="legacy",
                       m_max=M.M_MAX, nm_options=None)
    c = ex.paper_estimator_check("vx", "R3")
    assert c["profile"]["cost"] <= c["nm3"]["cost"] + 1e-9
    assert c["profile"]["m_eff"] == M.plant_delay_samples(ctx.params["vx"].Td, ctx.ts)


def test_deadzone_helper_masks_expected_fraction():
    thr = M.DEADZONE_WHEEL_RAD_S                       # 1.567 rad/s per wheel; R/r = 2.699
    cmd = np.array([
        [0.0, 0.0, 0.25],        # pure rotation 0.25 rad/s -> wheels 0.67 < thr: fully clamped
        [0.0, 0.0, 0.50],        # 1.35 < thr: fully clamped
        [0.0, 0.0, 1.00],        # 2.70 > thr: untouched
        [1.0, 0.0, 0.0],         # translation: wheels ~17-29 rad/s: untouched
        [1.0, 0.0, 0.30],        # small yaw while translating: every wheel above thr: untouched
        [0.0, 0.0, 0.0],         # zero command: nothing to mask
    ])
    out, changed = M.mask_deadzone(cmd, thr)
    assert np.allclose(out[0], 0.0) and np.allclose(out[1], 0.0)
    assert np.allclose(out[2:], cmd[2:])
    assert changed.any(axis=1).tolist() == [True, True, False, False, False, False]
    assert changed[:, 2].tolist() == [True, True, False, False, False, False]
    assert not changed[:, :2].any()
    assert changed.any(axis=1).mean() == pytest.approx(2 / 6)


def test_effective_delay_conventions():
    assert M.plant_delay_samples(0.06905, TS) == 5 and M.plant_delay_samples(0.056483333, TS) == 4
    assert M.plant_delay_samples(0.08895, TS) == 6 and M.plant_delay_samples(0.0, TS) == 0
    assert M.effective_delay_samples(6, "legacy") == 5 and M.effective_delay_samples(6, "plant") == 6
    for m in range(0, 13):
        assert C._delay_samples(M._td_of_m(m, TS), TS, "legacy") == m


def test_cell_summary_decision_rule():
    truth = DofParam(K=1.1192, tau=0.0718, Td=0.06905)
    base = dict(degenerate=False, n_events=12, n_train=8, n_holdout=4, fit_holdout_mean=95.0, fit_train_median=96.0)
    ok = pd.DataFrame([dict(base, K=1.12 + 0.01 * (i % 3), tau=0.072, m_eff=5) for i in range(6)])
    s = M.cell_summary(ok, truth, TS)
    assert s["recovered"] and s["score"] == 4 and s["m_plant"] == 5
    bad_K = ok.assign(K=1.40)
    s = M.cell_summary(bad_K, truth, TS)
    assert not s["crit"]["K"] and s["score"] == 3 and not s["recovered"]
    bad_Td = ok.assign(m_eff=7)                       # 7 - 4.14 = 2.86 samples
    assert not M.cell_summary(bad_Td, truth, TS)["crit"]["Td"]
    wide = ok.assign(K=[0.9, 1.0, 1.1, 1.2, 1.3, 1.4])   # IQR 0.25 / 1.1192 > 20 %
    assert not M.cell_summary(wide, truth, TS)["crit"]["iqr"]
    degenerate = ok.assign(K=np.nan, tau=np.nan, m_eff=np.nan, degenerate=True)
    s = M.cell_summary(degenerate, truth, TS)
    assert s["score"] == 0 and s["n_degenerate"] == 6 and not s["recovered"]


def test_fit_safe_nan_on_constant_output():
    y = np.zeros(50)
    assert np.isnan(M.fit_safe(y, np.ones(50)))
    y = np.arange(50, dtype=float)
    assert M.fit_safe(y, y) == pytest.approx(100.0)


def test_run_tiny_settings_writes_artefacts(tmp_path):
    r = M.run(root=None, out=tmp_path, regimes="R3", noises="none", deadzones="off", dofs="w", n_rep=1,
              paper_check=False, quiet=True)
    for key, ext in (("path", ".md"), ("csv", ".csv"), ("json", ".json")):
        p = r[key]
        assert p.parent == tmp_path and p.name.startswith("identifiability_insilico_") and p.suffix == ext
    text = r["path"].read_text(encoding="utf-8")
    assert text.startswith("# Identificabilidade in-silico (C1)")
    assert "_Proveniencia: commit" in text and "## DOF w" in text and "## Leitura" in text
    assert text.isascii()
    assert "n_rep = 1 (pre-registrado: 20)" in text          # reduced replicate count is declared
    df = pd.read_csv(r["csv"])
    assert len(df) == 1 and df.loc[0, "regime"] == "R3" and df.loc[0, "dof"] == "w"
    assert not df.loc[0, "degenerate"]
    with open(r["json"], encoding="utf-8") as f:
        j = json.load(f)
    assert j["design"]["n_rep"] == 1 and len(j["cells"]) == 1
    assert j["cells"][0]["recovered"] is True and j["cells"][0]["score"] == 4


@pytest.mark.requires_data
def test_dataset_regimes_replicate(ctx):
    """R2-rotate: w recovered from the dedicated events, vx/vy degenerate (no excitation)."""
    ex = M._Experiment(ctx, seed=M.SEED, threshold=M.DEADZONE_WHEEL_RAD_S, design=None, align="legacy",
                       m_max=M.M_MAX, nm_options=None)
    assert len(ex.events("rotate")) == 10
    rw = ex.replicate("R2-rotate", "w", "none", "off", 0)
    assert not rw["degenerate"] and abs(rw["K"] / ctx.params["w"].K - 1.0) <= 0.02
    assert rw["m_eff"] == M.plant_delay_samples(ctx.params["w"].Td, ctx.ts)
    rx = ex.replicate("R2-rotate", "vx", "none", "off", 0)
    assert rx["degenerate"] and np.isnan(rx["K"])
    m = ex.masked_fraction("rotate")
    assert m["vx"] == 0.0 and m["clamped"] == pytest.approx(0.4, abs=0.01)   # the 4 events at +-0.25/+-0.5 rad/s


# ---------------------------------------------------------------------------- C1b (physical generators)
def test_wonly_events_zero_translation_keep_yaw(ctx):
    evs = M.synthetic_events(ctx.ts, dict(n_events=2, duration_s=2.0))
    w = M.wonly_events(evs)
    assert len(w) == 2 and all(e.name.endswith(M.WONLY_SUFFIX) for e in w)
    for a, b in zip(evs, w, strict=True):
        assert np.all(b.cmd[:, :2] == 0.0) and np.array_equal(b.cmd[:, 2], a.cmd[:, 2])
        assert np.any(a.cmd[:, :2] != 0.0)                   # the original did have translation
        assert b.t is a.t and b.pose0 == a.pose0
    assert M.regime_label("R1-wonly", "w") == "shoot_to_goal" + M.WONLY_SUFFIX
    assert M.cell_applies("R1-wonly", "w") and not M.cell_applies("R1-wonly", "vx")
    assert M.cell_applies("R1", "vx")


@pytest.mark.requires_mujoco
def test_mujoco_velocity_generator_matches_fopdt_poses(ctx):
    """Route a embeds the FOPDT plant: with the actuator clips lifted the harness plant reproduces
    the analytic trajectory (< 1e-3 m; in fact ~1e-6); with the default 150 N / 3 N m clips the
    aggressive synthetic steps saturate the servo and the deviation stays below 1e-2 m."""
    pytest.importorskip("mujoco")
    ev = M.synthetic_events(ctx.ts, dict(n_events=1, duration_s=4.0))[0]
    ref = M.simulate_poses(ctx.params, ev, ctx.ts)
    exact = M.make_generator("mujoco-velocity", ctx.params, False, force_max=1e4, torque_max=1e3)
    try:
        pose = M.simulate_poses_plant(exact, ev, ctx.ts)
    finally:
        exact.close()
    assert np.max(np.abs(pose[:, :2] - ref[:, :2])) < 1e-3
    assert np.max(np.abs(pose[:, 2] - ref[:, 2])) < 1e-3
    default = M.make_generator("mujoco-velocity", ctx.params, False)
    try:
        pose = M.simulate_poses_plant(default, ev, ctx.ts)
    finally:
        default.close()
    assert np.max(np.abs(pose[:, :2] - ref[:, :2])) < 1e-2


@pytest.mark.requires_mujoco
def test_run_mujoco_generator_tiny(tmp_path):
    pytest.importorskip("mujoco")
    r = M.run(root=None, out=tmp_path, generator="mujoco-rollers", regimes="R3", noises="none", deadzones="off",
              dofs="w", n_rep=1, paper_check=False, quiet=True)
    assert r["path"].name.startswith("identifiability_insilico_mujoco-rollers_")
    text = r["path"].read_text(encoding="utf-8")
    assert text.isascii() and "gerador mujoco-rollers" in text and "regime_bias" in text
    df = pd.read_csv(r["csv"])
    assert df.loc[0, "generator"] == "mujoco-rollers" and not df.loc[0, "degenerate"]
    with open(r["json"], encoding="utf-8") as f:
        j = json.load(f)
    c = j["cells"][0]
    assert j["design"]["generator"] == "mujoco-rollers" and j["design"]["truth_known"] is False
    assert c["dev_K"] == 0.0 and c["regime_bias"] is False        # the reference cell itself


# ---------------------------------------------------------------------------- C1b-v2 (re-registration)
def test_r3_mild_design_respects_route_b_envelope(ctx):
    d = M.R3_MILD_DESIGN
    evs = M.synthetic_events(ctx.ts, d)
    assert len(evs) == 12 and all(e.n == 600 for e in evs)
    cmd = np.concatenate([e.cmd for e in evs])
    assert np.all(np.abs(cmd[:, :2]) >= d["amp_trans"][0]) and np.all(np.abs(cmd[:, :2]) <= d["amp_trans"][1])
    assert np.all(np.abs(cmd[:, 2]) >= d["amp_rot"][0]) and np.all(np.abs(cmd[:, 2]) <= d["amp_rot"][1])
    assert np.abs(cmd[:, :2]).max() <= 1.0 and np.abs(cmd[:, 2]).max() <= 2.0      # inside the envelope
    lo, hi = d["step_s"]
    for e in evs:                                   # step durations within [0.5, 1.5] s (last one may be cut)
        for k in range(3):
            edges = np.flatnonzero(np.diff(e.cmd[:, k]) != 0.0) + 1
            runs = np.diff(np.concatenate(([0], edges, [e.n]))) * ctx.ts
            assert np.all(runs[:-1] >= lo - 1e-9) and np.all(runs <= hi + ctx.ts + 1e-9)
    assert M.regime_label("R3-mild", "vx") == "R3-mild"
    assert not np.array_equal(evs[0].cmd, M.synthetic_events(ctx.ts)[0].cmd)     # distinct from the aggressive R3


def test_reference_presets_and_k_only_flag():
    v1 = M.normalize_reference(None)
    assert v1 == {d: ("R3", "none", "off") for d in DOFS}
    v2 = M.normalize_reference("v2")
    assert v2["w"] == ("R2-rotate", "none", "off") and v2["vx"] == v2["vy"] == ("R2-square", "none", "off")
    assert M.reference_kind(v1) == "v1" and M.reference_kind(v2) == "v2"
    custom = M.normalize_reference("R2-rotate,none,off")
    assert M.reference_kind(custom) == "custom" and custom["vx"] == ("R2-rotate", "none", "off")
    with pytest.raises(ValueError):
        M.normalize_reference("R3,loud,off")
    # K-only flag independent of tau
    base = dict(K_med=1.0, tau_med=0.03, m_eff_med=5.0)
    cells = [dict(base, regime="R2-rotate", dof="w", noise="none", deadzone="off"),
             dict(base, regime="R1", dof="w", noise="none", deadzone="off", K_med=1.05, tau_med=0.30),
             dict(base, regime="R1", dof="w", noise="vision", deadzone="on", K_med=1.25, tau_med=0.03)]
    M.reference_deviation(cells, ["w"], v2)
    assert cells[1]["regime_bias"] and not cells[1]["regime_bias_K"]          # tau only -> v1 flag only
    assert cells[2]["regime_bias_K"] and cells[2]["dev_K"] == pytest.approx(0.25)
    assert not cells[0]["regime_bias_K"] and cells[0]["dev_K"] == 0.0
