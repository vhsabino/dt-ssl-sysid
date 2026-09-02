"""dtssl.eval after the split (metrics / stats / verdict / report): API compatibility, defects
fixed in the 2026-09 refactor and the window-pairing rules. Synthetic data only."""
import copy
import importlib
import math
import warnings

import numpy as np
import pytest

from dtssl import AnalyticFOPDTPlant, DofParam, IdealKinematicPlant, load_twin_params
from dtssl.data.schema import Segment
from dtssl.eval import stats
from dtssl.sim.rollout import WindowRollout, free_run, rollout_segment

TS = 1.0 / 60.0


# ---- API compatibility ---------------------------------------------------------------
def test_metrics_module_reexports_everything():
    m = importlib.import_module("dtssl.eval.metrics")
    from dtssl.eval.metrics import (BIN_LABEL, BIN_ORDER, ErrorTable, _ci, _get_robot_radius,  # noqa: F401
                                    _mbb, _verdict_bin, _wilcoxon_less, _window_activity,
                                    bin_distribution, build_error_table, classify_bin, evaluate,
                                    format_bin_distribution, load_metrics_config, make_figures,
                                    markdown_report, rank_biserial)
    assert evaluate.__module__ == "dtssl.eval.verdict"
    assert make_figures.__module__ == "dtssl.eval.report"
    assert rank_biserial.__module__ == "dtssl.eval.stats"
    assert load_metrics_config.__module__ == "dtssl.config"
    with pytest.raises(AttributeError):
        m.no_such_name  # noqa: B018
    from dtssl.eval import evaluate as e2, VERDICT_GO  # noqa: F401
    assert e2 is evaluate


def test_verdict_import_first_in_fresh_interpreter():
    """Importing the low-level modules first must not trip the lazy re-export (no cycle)."""
    import subprocess, sys
    code = ("import dtssl.eval.verdict, dtssl.eval.report; "
            "from dtssl.eval.metrics import evaluate, make_figures; print(evaluate.__module__)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "dtssl.eval.verdict"


# ---- fixed defects -------------------------------------------------------------------
def test_build_error_table_empty_input_raises_value_error():
    from dtssl.eval.metrics import build_error_table
    with pytest.raises(ValueError, match="no rollouts"):
        build_error_table([], [])
    meta = dict(event="e", ts=TS, h_max=90, stride=15, horizons=(6,))
    with pytest.raises(ValueError, match="no windows"):
        build_error_table([WindowRollout(meta=meta, windows=[])], [WindowRollout(meta=meta, windows=[])])
    ro = WindowRollout(meta=meta, windows=[])
    with pytest.raises(ValueError, match="different lengths"):
        build_error_table([ro], [ro, ro])


def test_bootstrap_rng_is_deterministic_per_key():
    a = stats.bootstrap_rng(42, 0, 1).integers(10**9, size=5)
    b = stats.bootstrap_rng(42, 0, 1).integers(10**9, size=5)
    c = stats.bootstrap_rng(42, 0, 2).integers(10**9, size=5)
    assert np.array_equal(a, b) and not np.array_equal(a, c)
    # no key -> plain default_rng(seed)
    assert np.array_equal(stats.bootstrap_rng(7).integers(100, size=4), np.random.default_rng(7).integers(100, size=4))


def test_moving_block_bootstrap_explicit_rng():
    rows = np.arange(20); seg_id = np.repeat([0, 1], 10)
    pool = stats.block_pool(rows, seg_id, 4)
    assert len(pool) == 2 * (10 - 4 + 1)
    assert all(np.all(np.diff(b) == 1) for b in pool)             # blocks never cross segments
    d1 = stats.moving_block_bootstrap(rows, seg_id, 4, 20, 50, np.random.default_rng(3), lambda ix: ix.mean())
    d2 = stats.moving_block_bootstrap(rows, seg_id, 4, 20, 50, np.random.default_rng(3), lambda ix: ix.mean())
    assert np.array_equal(d1, d2) and d1.shape == (50,)
    ci = stats.percentile_ci(np.column_stack([d1, d1 + 1]), 0.9)
    assert ci.shape == (2, 2) and np.all(ci[:, 0] <= ci[:, 1])


def test_rank_biserial_and_wilcoxon_edge_cases():
    assert stats.rank_biserial(np.array([1.0, 2.0]), np.array([1.0, 2.0])) == 0.0
    assert stats.rank_biserial(np.array([2.0, 3.0]), np.array([1.0, 1.0])) == 1.0
    assert stats.wilcoxon_less(np.ones(5), np.ones(5)) == 1.0
    p = stats.wilcoxon_less(np.arange(10) * 0.1, np.arange(10) * 0.1 + 1.0)
    assert 0.0 < p < 0.01


# ---- window pairing / idx_min from the plant -----------------------------------------
def _synth_segment(plant, N=1400):
    t = np.arange(N) * TS
    cmd = np.column_stack([0.9 + 0.5 * np.sin(2 * np.pi * 0.2 * t),
                           0.3 * np.sin(2 * np.pi * 0.13 * t + 0.5), np.zeros(N)])
    traj = free_run(plant, cmd[:-1], pose0=(0.0, 0.0, 0.0), velb0=(0, 0, 0), dt=TS)
    from dtssl.data.loader import body_velocity_series
    vbx, vby, vw = body_velocity_series(t, traj[:, 0], traj[:, 1], traj[:, 2])
    return Segment(meta={"event": "synth"}, ts=TS, t=t, dt=np.full(N, TS),
                   cmd_vx=cmd[:, 0], cmd_vy=cmd[:, 1], cmd_w=cmd[:, 2],
                   pos_x=traj[:, 0], pos_y=traj[:, 1], theta=traj[:, 2],
                   vel_x_world=np.zeros(N), vel_y_world=np.zeros(N), velb_x=vbx, velb_y=vby, velb_w=vw,
                   pose0=(0.0, 0.0, 0.0), velb0=(vbx[0], vby[0], vw[0]))


def test_idx_min_from_plant_params_and_fixed_grid():
    from dtssl.sim.rollout import max_command_delay
    base = load_twin_params()
    seg = _synth_segment(AnalyticFOPDTPlant(base))
    anchor = max_command_delay(TS) + 1                          # official grid (config theta)
    ro_cfg = rollout_segment(seg, AnalyticFOPDTPlant(base))
    assert ro_cfg.meta["idx_min"] == anchor == ro_cfg.meta["t0_anchor"]
    assert ro_cfg.windows[0].t0 == anchor
    # smaller dead time: admissible earlier, but the grid stays the official one
    small = dict(base); small["w"] = DofParam(K=1.0, tau=0.08, Td=0.0)
    ro_small = rollout_segment(seg, AnalyticFOPDTPlant(small))
    assert ro_small.meta["idx_min"] < anchor and ro_small.windows[0].t0 == anchor
    # larger dead time: first grid point inadmissible -> skipped, grid preserved
    big = dict(base); big["w"] = DofParam(K=1.0, tau=0.08, Td=0.30)
    ro_big = rollout_segment(seg, AnalyticFOPDTPlant(big))
    assert ro_big.meta["idx_min"] == math.ceil(0.30 / TS - 1e-9) + 1 > anchor
    assert ro_big.windows[0].t0 == anchor + 15 * math.ceil((ro_big.meta["idx_min"] - anchor) / 15)
    assert ro_big.windows[0].t0 in {w.t0 for w in ro_cfg.windows}
    # explicit params override the plant's own theta; ideal plant falls back to the config
    assert rollout_segment(seg, AnalyticFOPDTPlant(small), params=base).meta["idx_min"] == anchor
    assert rollout_segment(seg, IdealKinematicPlant()).meta["idx_min"] == anchor


def test_pairing_by_t0_drops_unmatched_and_warns():
    from dtssl.eval.metrics import build_error_table
    base = load_twin_params()
    seg = _synth_segment(AnalyticFOPDTPlant(base))
    big = dict(base); big["w"] = DofParam(K=1.0, tau=0.08, Td=0.30)
    ro_t = rollout_segment(seg, AnalyticFOPDTPlant(big))
    ro_d = rollout_segment(seg, IdealKinematicPlant())
    assert len(ro_t.windows) == len(ro_d.windows) - 1
    with pytest.warns(RuntimeWarning, match="paired by t0"):
        table = build_error_table([ro_t], [ro_d])
    assert table.W == len(ro_t.windows)
    # identical grids: no warning at all
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        t2 = build_error_table([rollout_segment(seg, AnalyticFOPDTPlant(base))], [ro_d])
    assert t2.W == len(ro_d.windows)
    # disjoint grids: explicit error
    ro_shift = rollout_segment(seg, IdealKinematicPlant(), t0_anchor=ro_d.meta["t0_anchor"] + 1)
    with pytest.raises(ValueError, match="no t0 in common"):
        build_error_table([ro_shift], [ro_d])


def test_evaluate_is_reproducible_and_scope_independent():
    """Per-(scope, curve) generators: the CI of a scope does not depend on evaluation order."""
    from dtssl.config import load_metrics_config
    from dtssl.eval import evaluate
    base = load_twin_params()
    seg = _synth_segment(AnalyticFOPDTPlant(base))
    ro_t = rollout_segment(seg, AnalyticFOPDTPlant(base))
    ro_d = rollout_segment(seg, IdealKinematicPlant())
    mcfg = copy.deepcopy(load_metrics_config()); mcfg["bootstrap"]["n_boot"] = 50
    r1 = evaluate([ro_t], [ro_d], params=base, mcfg=mcfg)
    r2 = evaluate([ro_t], [ro_d], params=base, mcfg=mcfg)
    for k in ("epos_twin_ci", "gap_epos_ci", "eang_def_ci"):
        assert np.array_equal(r1["scopes"]["all"][k], r2["scopes"]["all"][k])
        assert np.array_equal(r1["scopes"]["trans"][k], r2["scopes"]["trans"][k])
    assert r1["verdicts"]["trans"]["verdict"] in ("GO", "NO-GO")
    assert "criteria" in r1["verdicts"]["trans"]


def test_pose_errors_wraps_angle():
    from dtssl.eval.metrics import pose_errors
    ps = np.zeros((3, 3)); pr = np.zeros((3, 3))
    ps[:, 2] = math.radians(179.0); pr[:, 2] = math.radians(-179.0); ps[1, 0] = 3.0; pr[1, 1] = 4.0
    epos, eang = pose_errors(ps, pr)
    assert epos[1] == pytest.approx(5.0) and np.allclose(eang, math.radians(2.0))
