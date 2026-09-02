"""Teste CROSS-LINGUAGEM: o loader Python reproduz a reamostragem do MATLAB.

A grade golden vem de automation/export_resample_reference.m (mesmas operacoes de
build_idData_per_dof: colon 1/60, ZOH nos comandos, linear+unwrap na pose). O
loader deve reproduzir t/cmd/pose/theta a tolerancia apertada.
"""
import numpy as np
import pandas as pd
import pytest

from conftest import FIXTURES
from dtssl import load_segment

pytestmark = pytest.mark.requires_data   # every test here loads a real event

CASES = [
    ("side_to_side", "side_to_side_01_05"),
    ("shoot_to_goal", "shoot_to_goal_12_01"),
]
COLS = ["t", "cmd_vx", "cmd_vy", "cmd_w", "pos_x", "pos_y", "theta",
        "vel_x_world", "vel_y_world"]


@pytest.mark.parametrize("label,event", CASES)
def test_loader_matches_matlab_grid(label, event):
    ref_path = FIXTURES / f"resample_ref_{event}.parquet"
    if not ref_path.exists():
        pytest.skip(f"fixture ausente: {ref_path} (rode export_resample_reference.m)")
    ref = pd.read_parquet(ref_path)

    seg = load_segment(label, event)

    # mesmo numero de amostras (pega off-by-one de grade na hora)
    assert seg.n == len(ref), f"N Python={seg.n} vs MATLAB={len(ref)}"

    got = {
        "t": seg.t, "cmd_vx": seg.cmd_vx, "cmd_vy": seg.cmd_vy, "cmd_w": seg.cmd_w,
        "pos_x": seg.pos_x, "pos_y": seg.pos_y, "theta": seg.theta,
        "vel_x_world": seg.vel_x_world, "vel_y_world": seg.vel_y_world,
    }
    for c in COLS:
        np.testing.assert_allclose(
            got[c], ref[c].to_numpy(float), rtol=0, atol=1e-9,
            err_msg=f"coluna {c} difere do golden MATLAB em {event}")
