"""Carrega um evento real e confere shapes/dtypes/SI/grade 1/60 + sanity de unidade."""
import numpy as np
import pytest

from dtssl import load_segment, TS_DEFAULT, event_dir
from dtssl.data.schema import validate_segment
from dtssl.data.validate import check_velocity_units

pytestmark = pytest.mark.requires_data   # every test here loads a real event

LABEL, EVENT = "side_to_side", "side_to_side_01_05"


@pytest.fixture(scope="module")
def seg():
    return load_segment(LABEL, EVENT)


def test_shapes_and_dtypes(seg):
    n = seg.n
    for name in ["t", "dt", "cmd_vx", "cmd_vy", "cmd_w", "pos_x", "pos_y", "theta",
                 "vel_x_world", "vel_y_world"]:
        arr = getattr(seg, name)
        assert arr.shape == (n,), f"{name}: shape {arr.shape} != ({n},)"
        assert arr.dtype == np.float64, f"{name}: dtype {arr.dtype}"
    assert len(seg.pose0) == 3 and len(seg.velb0) == 3


def test_grid_is_uniform_1_60(seg):
    d = np.diff(seg.t)
    assert np.all(d > 0), "t nao crescente"
    assert np.max(np.abs(d - TS_DEFAULT)) < 1e-9, "grade nao e 1/60 uniforme"
    assert abs(seg.dt[0] - TS_DEFAULT) < 1e-12


def test_si_units_not_mm(seg):
    # posicao em METROS (se fosse mm seria ~milhares)
    assert np.nanmax(np.abs(seg.pos_x)) < 7.0
    assert np.nanmax(np.abs(seg.pos_y)) < 7.0
    # comandos em faixa fisica (m/s, rad/s)
    assert np.nanmax(np.abs(seg.cmd_vx)) < 5.0
    assert np.nanmax(np.abs(seg.cmd_vy)) < 5.0
    assert np.nanmax(np.abs(seg.cmd_w)) < 30.0
    # validacao completa nao acusa nada
    assert validate_segment(seg, raise_on_error=False) == []


def test_pose0_matches_first_sample(seg):
    assert seg.pose0 == (seg.pos_x[0], seg.pos_y[0], seg.theta[0])


def test_velocity_unit_is_mm_per_s():
    d = event_dir(LABEL, EVENT)
    info = check_velocity_units(d / "processed_robots.parquet")
    assert info["unit_is_mm_per_s"], info
