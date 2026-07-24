"""Testes do motor de rollout free-run (driver fino)."""
import math

import numpy as np
import pandas as pd
import pytest

from conftest import FIXTURES
from phase0_replay import (load_segment, load_holdout_segments, AnalyticFOPDTPlant,
                           IdealKinematicPlant, rollout_segment, free_run,
                           max_command_delay, load_twin_params)

TS = 1.0 / 60.0


def _cmd_matrix(seg):
    return np.column_stack([seg.cmd_vx, seg.cmd_vy, seg.cmd_w])


# ---- PORTAO: transparencia (o driver nao injeta erro de dinamica) ----
@pytest.mark.parametrize("label,event", [
    ("shoot_to_goal", "shoot_to_goal_12_01"),
    ("side_to_side", "side_to_side_01_05"),
])
def test_transparency_matches_golden(label, event, capsys):
    ref_path = FIXTURES / f"plant_golden_{event}.parquet"
    if not ref_path.exists():
        pytest.skip("fixture ausente")
    ref = pd.read_parquet(ref_path)
    seg = load_segment(label, event)
    N = seg.n
    # free-run do segmento INTEIRO a partir da CI do deadreckoning: velb0=0, sem prime
    win_cmds = _cmd_matrix(seg)[0:N - 1]
    plant = AnalyticFOPDTPlant.from_config()
    pose_sim = free_run(plant, win_cmds, pose0=seg.pose0, velb0=(0.0, 0.0, 0.0),
                        dt=seg.ts, prev_cmds=None)
    err = max(np.max(np.abs(pose_sim[:, 0] - ref["xs"].to_numpy(float))),
              np.max(np.abs(pose_sim[:, 1] - ref["ys"].to_numpy(float))),
              np.max(np.abs(pose_sim[:, 2] - ref["ths"].to_numpy(float))))
    with capsys.disabled():
        print(f"\n  transparencia {event}: max|erro| vs golden = {err:.3e}")
    assert err <= 1e-12


# ---- GUARDA ANTI-TEACHER-FORCING ----
def test_anti_teacher_forcing_finite_output():
    seg = load_segment("side_to_side", "side_to_side_01_05")
    md = max_command_delay(seg.ts)
    t0 = md + 1                               # = idx_min, primeira janela
    # envenena a pose real em TODOS os indices > t0 (velb_series ja foi calculada
    # na carga, fica intacta; a pose0 em t0 nao e tocada)
    seg.pos_x[t0 + 1:] = np.nan
    seg.pos_y[t0 + 1:] = np.nan
    seg.theta[t0 + 1:] = np.nan
    plant = AnalyticFOPDTPlant.from_config()
    ro = rollout_segment(seg, plant, h_max=30, horizons=(6, 12, 24), stride=10**6)  # 1 janela
    assert ro.n_total == 1
    w = ro.windows[0]
    assert w.t0 == t0
    assert np.isfinite(w.pose_sim).all(), "pose_sim contaminada => leu pose real apos t0"
    assert np.isnan(w.pose_real[1:]).any(), "sanity: a pose real foi de fato envenenada"


# ---- CI / PRIMING ----
def test_reset_honors_velb0():
    v = (0.7, -0.3, 0.5)
    plant = AnalyticFOPDTPlant.from_config()
    plant.reset(pose0=(0.0, 0.0, 0.0), velb0=v)
    assert plant.body_velocity == pytest.approx(v)


def test_priming_removes_transient():
    p = load_twin_params()
    Kvx = p["vx"].K
    c = 0.5
    win = np.tile([c, 0.0, 0.0], (40, 1)).astype(float)
    prev = np.tile([c, 0.0, 0.0], (16, 1)).astype(float)
    velb0 = (Kvx * c, 0.0, 0.0)             # estacionario (vlag_vx = c)

    # COM prime: estacionario imediato => espacamento de x constante (sem transiente)
    plant = AnalyticFOPDTPlant(p)
    ps = free_run(plant, win, pose0=(0, 0, 0), velb0=velb0, dt=TS, prev_cmds=prev)
    dx = np.diff(ps[:, 0])
    assert np.std(dx) < 1e-12
    assert np.allclose(dx, Kvx * c * TS, atol=1e-9)

    # SEM prime: taps de vx vazios => transiente nos primeiros passos
    plant2 = AnalyticFOPDTPlant(p)
    ps2 = free_run(plant2, win, pose0=(0, 0, 0), velb0=velb0, dt=TS, prev_cmds=None)
    dx2 = np.diff(ps2[:, 0])
    assert np.std(dx2) > 1e-6


# ---- alinhamento (off-by-one) ----
def test_offbyone_alignment():
    seg = load_segment("shoot_to_goal", "shoot_to_goal_12_01")
    pos = np.column_stack([seg.pos_x, seg.pos_y, seg.theta])
    plant = AnalyticFOPDTPlant.from_config()
    ro = rollout_segment(seg, plant)
    w = ro.windows[0]
    t0 = w.t0
    # pose_real[h] == pose real em t0+h ; pose_sim[0] == pose0 == pos[t0]
    for h in (0, 1, 5, ro.meta["h_max"]):
        assert np.allclose(w.pose_real[h], pos[t0 + h])
    assert np.allclose(w.pose_sim[0], pos[t0])


# ---- contagem de janelas / invariante de janelamento ----
def test_window_indexing():
    seg = load_segment("side_to_side", "side_to_side_01_05")
    plant = AnalyticFOPDTPlant.from_config()
    ro = rollout_segment(seg, plant)
    assert ro.meta["idx_min"] == max_command_delay(seg.ts) + 1
    assert ro.n_total > 0
    last = ro.windows[-1]
    assert last.t0 + ro.meta["h_max"] < seg.n          # nunca sai do segmento
    assert all(w.pose_sim.shape == (ro.meta["h_max"] + 1, 3) for w in ro.windows)


def test_idle_flagging_marks_not_drops():
    seg = load_segment("side_to_side", "side_to_side_01_05")
    plant = AnalyticFOPDTPlant.from_config()
    base = rollout_segment(seg, plant)                       # floors default -> 0 idle
    high = rollout_segment(seg, plant, trans_floor=1e9, rot_floor=1e9)  # tudo "parado"
    assert base.n_total == high.n_total                     # nada e apagado
    assert base.n_idle == 0
    assert high.n_idle == high.n_total                      # todos sinalizados
    assert all(w.idle for w in high.windows)


def test_ideal_plant_also_rolls():
    seg = load_segment("front_to_back", "front_to_back_01_01")
    ro = rollout_segment(seg, IdealKinematicPlant())
    assert ro.n_total > 0
    assert np.isfinite(ro.windows[0].pose_sim).all()
