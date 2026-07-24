"""Testes da metrica SE(2) multi-horizonte, estratificacao e vereditos por bin."""
import copy
import math

import numpy as np
import pytest

from phase0_replay import (AnalyticFOPDTPlant, IdealKinematicPlant, rollout_segment,
                           free_run, build_error_table, evaluate, load_metrics_config,
                           load_twin_params, body_velocity_series)
from phase0_replay.schema import Segment
from phase0_replay.rollout import Window, WindowRollout

TS = 1.0 / 60.0


def _fast_cfg(**over):
    c = load_metrics_config()
    c = copy.deepcopy(c)
    c["bootstrap"]["n_boot"] = 300
    for k, v in over.items():
        c["verdict"][k] = v
    return c


def _synth_segment(plant, N=1400, rot=False, seed=0):
    """Segmento sintetico cuja pose REAL e gerada PELA propria planta (free-run)."""
    t = np.arange(N) * TS
    cmd_vx = 0.9 + 0.5 * np.sin(2 * np.pi * 0.20 * t)
    cmd_vy = 0.3 * np.sin(2 * np.pi * 0.13 * t + 0.5)
    cmd_w = 1.5 * np.sin(2 * np.pi * 0.17 * t) if rot else np.zeros(N)
    cmd = np.column_stack([cmd_vx, cmd_vy, cmd_w])
    traj = free_run(plant, cmd[:-1], pose0=(0.0, 0.0, 0.0), velb0=(0, 0, 0),
                    dt=TS, prev_cmds=None)              # (N,3) gerado pela planta
    px, py, th = traj[:, 0], traj[:, 1], traj[:, 2]
    vbx, vby, vw = body_velocity_series(t, px, py, th)
    return Segment(meta={"event": "synth", "label": "synth", "dataset": "synth"}, ts=TS,
                   t=t, dt=np.full(N, TS), cmd_vx=cmd_vx, cmd_vy=cmd_vy, cmd_w=cmd_w,
                   pos_x=px, pos_y=py, theta=th,
                   vel_x_world=np.zeros(N), vel_y_world=np.zeros(N),
                   velb_x=vbx, velb_y=vby, velb_w=vw,
                   pose0=(px[0], py[0], th[0]), velb0=(vbx[0], vby[0], vw[0]))


# ---- 1) GO quando o twin gerou a verdade; NO-GO quando default==twin ----
def test_trans_bin_GO_when_twin_generates_truth():
    params = load_twin_params()
    twin = AnalyticFOPDTPlant(params)
    seg = _synth_segment(twin)
    ro_t = rollout_segment(seg, twin)
    ro_d = rollout_segment(seg, IdealKinematicPlant())
    res = evaluate([ro_t], [ro_d], params=params, mcfg=_fast_cfg())
    tr = res["scopes"]["trans"]
    assert np.max(tr["epos_twin_med"]) < 0.02            # twin reproduz ~0
    assert tr["gap_epos"][-1] > 0.02                     # ideal claramente pior
    assert res["verdicts"]["trans"]["verdict"] == "GO"


def test_no_go_when_default_equals_twin():
    params = load_twin_params()
    twin = AnalyticFOPDTPlant(params)
    seg = _synth_segment(twin)
    ro_t = rollout_segment(seg, twin)
    ro_d = rollout_segment(seg, AnalyticFOPDTPlant(params))   # default == twin
    res = evaluate([ro_t], [ro_d], params=params, mcfg=_fast_cfg())
    tr = res["scopes"]["trans"]
    assert np.allclose(tr["gap_epos"], 0.0, atol=1e-9)
    assert res["verdicts"]["trans"]["verdict"] == "NO-GO"


# ---- 2) wrap no erro angular (179 vs -179 => 2 graus) ----
def _craft_single_window_ro(theta_sim_deg, theta_real_deg, h_max=90):
    N = h_max + 1
    ps = np.zeros((N, 3)); ps[:, 2] = math.radians(theta_sim_deg)
    pr = np.zeros((N, 3)); pr[:, 2] = math.radians(theta_real_deg)
    w = Window(t0=10, t0_time=10 * TS, pose_sim=ps, pose_real=pr,
               cmd=np.full((h_max, 3), 0.5), velb=np.zeros((N, 3)), velb0=(0, 0, 0),
               trans_peak=0.5, trans_mean=0.5, rot_peak=0.5, rot_mean=0.5, idle=False)
    meta = dict(event="wrap", label="x", dataset="d", ts=TS, n_samples=N, h_max=h_max,
                horizons=(6, 12, 24, 42, 60, 90), stride=15, lookback=16, max_delay=5,
                idx_min=6, plant="X", trans_floor=0.05, rot_floor=0.1)
    return WindowRollout(meta=meta, windows=[w])


def test_angular_error_wraps():
    ro = _craft_single_window_ro(179.0, -179.0)
    table = build_error_table([ro], [ro])
    assert np.allclose(table.eang_twin, math.radians(2.0), atol=1e-9)
    assert np.allclose(table.epos_twin, 0.0, atol=1e-12)


# ---- 3) N efetivo: inferencia usa contagem nao-sobreposta, nao a densa ----
def test_effective_N_is_nonoverlapping():
    params = load_twin_params()
    twin = AnalyticFOPDTPlant(params)
    seg = _synth_segment(twin)
    ro_t = rollout_segment(seg, twin)
    ro_d = rollout_segment(seg, IdealKinematicPlant())
    table = build_error_table([ro_t], [ro_d])
    nwin = len(ro_t.windows)
    step = math.ceil(ro_t.meta["h_max"] / ro_t.meta["stride"])   # = 6
    expected_indep = (nwin - 1) // step + 1
    assert int(table.indep.sum()) == expected_indep
    assert int(table.indep.sum()) < table.W                      # nao infla N


# ---- 4) gate de placeholder: misto/rot => INDETERMINADO ----
def test_placeholder_gate_marks_rot_and_misto():
    params = load_twin_params()
    assert params["w"].placeholder is True
    twin = AnalyticFOPDTPlant(params)
    seg = _synth_segment(twin)
    res = evaluate([rollout_segment(seg, twin)],
                   [rollout_segment(seg, IdealKinematicPlant())],
                   params=params, mcfg=_fast_cfg())
    assert res["verdicts"]["rot"]["verdict"].startswith("INDETERMINADO")
    assert res["verdicts"]["misto"]["verdict"].startswith("INDETERMINADO")


# ---- 5) gate de populacao: N < N_min => SEM PODER ----
def test_population_gate_sem_poder():
    params = load_twin_params()
    twin = AnalyticFOPDTPlant(params)
    seg = _synth_segment(twin)
    res = evaluate([rollout_segment(seg, twin)],
                   [rollout_segment(seg, IdealKinematicPlant())],
                   params=params, mcfg=_fast_cfg(n_min_independent=10**6))
    assert res["verdicts"]["trans"]["verdict"].startswith("SEM PODER")
