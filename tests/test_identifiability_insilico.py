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
