"""PORTAO DE CORRECAO: AnalyticFOPDTPlant reproduz deadreckoning_p1d (MATLAB).

O golden vem de matlab/dtssl/export_plant_golden.m (deadreckoning_p1d na grade 1/60)
com o theta gravado em tests/fixtures/plant_golden_theta.json (vx/vy v2 + omega placeholder,
2026-06-16). O teste usa ESSE theta, nao o config/twin_params.json corrente, para que a
promocao de novos parametros nao invalide o portao de correcao do porte. O plant e dirigido pelos MESMOS comandos (do loader,
identicos ao golden) a partir da MESMA pose0, com estado inicial nulo (velb0=0,
como deadreckoning) e SEM prime_delay (buffer 0, como o fill 0 do interp1).
"""
import re

import numpy as np
import pandas as pd
import pytest

from conftest import FIXTURES
from dtssl import AnalyticFOPDTPlant, load_segment, load_twin_params

pytestmark = pytest.mark.requires_data
GOLDEN_THETA = FIXTURES / "plant_golden_theta.json"   # theta that generated the fixtures

CASES = [
    ("shoot_to_goal", "shoot_to_goal_12_01"),   # rotacao + translacao (exercita w, vx, vy)
    ("side_to_side", "side_to_side_01_05"),      # translacao lateral (vy)
]
ATOL = 1e-6   # alvo do enunciado; esquema identico deve aproximar 1e-9


def _rollout(plant, seg):
    """Dirige o plant pela grade do segmento; pose[0]=pose0, depois N-1 steps.
    (rollout vive NO TESTE, nao em plant.py.)"""
    plant.reset(pose0=seg.pose0, velb0=(0.0, 0.0, 0.0))
    xs, ys, ths = np.empty(seg.n), np.empty(seg.n), np.empty(seg.n)
    xs[0], ys[0], ths[0] = seg.pose0
    for k in range(1, seg.n):
        cmd = (seg.cmd_vx[k - 1], seg.cmd_vy[k - 1], seg.cmd_w[k - 1])
        xs[k], ys[k], ths[k] = plant.step(cmd, seg.ts)
    return xs, ys, ths


@pytest.mark.parametrize("label,event", CASES)
def test_analytic_plant_matches_deadreckoning_golden(label, event):
    ref_path = FIXTURES / f"plant_golden_{event}.parquet"
    if not ref_path.exists():
        pytest.skip(f"fixture ausente: {ref_path} (rode export_plant_golden.m)")
    ref = pd.read_parquet(ref_path)

    seg = load_segment(label, event)
    assert seg.n == len(ref), f"N Python={seg.n} vs MATLAB={len(ref)}"

    plant = AnalyticFOPDTPlant(load_twin_params(GOLDEN_THETA))
    xs, ys, ths = _rollout(plant, seg)

    for name, got in (("xs", xs), ("ys", ys), ("ths", ths)):
        err = float(np.max(np.abs(got - ref[name].to_numpy(float))))
        assert err <= ATOL, f"{name}: max|erro|={err:.3e} > atol={ATOL:.0e} em {event}"


def test_report_achieved_atol(capsys):
    """Imprime o atol efetivo atingido (para o relatorio)."""
    worst = 0.0
    for label, event in CASES:
        ref_path = FIXTURES / f"plant_golden_{event}.parquet"
        if not ref_path.exists():
            pytest.skip("fixtures ausentes")
        ref = pd.read_parquet(ref_path)
        seg = load_segment(label, event)
        plant = AnalyticFOPDTPlant(load_twin_params(GOLDEN_THETA))
        xs, ys, ths = _rollout(plant, seg)
        e = max(np.max(np.abs(xs - ref["xs"].to_numpy(float))),
                np.max(np.abs(ys - ref["ys"].to_numpy(float))),
                np.max(np.abs(ths - ref["ths"].to_numpy(float))))
        worst = max(worst, float(e))
        with capsys.disabled():
            print(f"\n  golden {event}: max|erro| = {e:.3e} m/rad")
    with capsys.disabled():
        print(f"  >>> atol efetivo do golden (pior dos casos) = {worst:.3e}")
    assert worst <= 1e-6


# ---- goldens com tag (plant_golden_<tag>_<event>.parquet + plant_golden_<tag>_theta.json) --------
# export_plant_golden(ev_dir, 'theta', 'promoted', 'tag', 'v2') grava o par acima; cada tag e testada
# contra o SEU sidecar de theta, entao promover um theta novo nao invalida os goldens antigos.
_EVENT_RE = re.compile(r"^(?P<label>[a-z_]+?)_\d+_\d+$")


def _tagged_cases():
    cases = []
    for sidecar in sorted(FIXTURES.glob("plant_golden_*_theta.json")):
        tag = sidecar.name[len("plant_golden_"):-len("_theta.json")]
        for pq in sorted(FIXTURES.glob(f"plant_golden_{tag}_*.parquet")):
            event = pq.name[len(f"plant_golden_{tag}_"):-len(".parquet")]
            m = _EVENT_RE.match(event)
            if m is None:
                continue
            cases.append(pytest.param(tag, m.group("label"), event, id=f"{tag}-{event}"))
    return cases


@pytest.mark.parametrize("tag,label,event", _tagged_cases())
def test_tagged_golden_matches_its_theta_sidecar(tag, label, event):
    ref = pd.read_parquet(FIXTURES / f"plant_golden_{tag}_{event}.parquet")
    seg = load_segment(label, event)
    assert seg.n == len(ref), f"N Python={seg.n} vs MATLAB={len(ref)}"
    plant = AnalyticFOPDTPlant(load_twin_params(FIXTURES / f"plant_golden_{tag}_theta.json"))
    xs, ys, ths = _rollout(plant, seg)
    for name, got in (("xs", xs), ("ys", ys), ("ths", ths)):
        err = float(np.max(np.abs(got - ref[name].to_numpy(float))))
        assert err <= ATOL, f"[{tag}] {name}: max|erro|={err:.3e} > atol={ATOL:.0e} em {event}"
