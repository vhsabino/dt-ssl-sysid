"""theta reamostrado SEM saltos de fase (interpolacao apos unwrap)."""
import numpy as np
import pytest

from dtssl import load_segment, interp_linear_nan


@pytest.mark.requires_data
def test_real_event_theta_has_no_2pi_jumps():
    # evento com bastante rotacao
    seg = load_segment("shoot_to_goal", "shoot_to_goal_12_01")
    dtheta = np.abs(np.diff(seg.theta))
    # apos unwrap, diffs entre amostras adjacentes ficam muito abaixo de pi
    assert np.max(dtheta) < np.pi, f"salto de fase: max|dtheta|={np.max(dtheta):.3f}"


def test_unwrap_then_interp_is_continuous():
    # sinal que cruza +pi -> -pi (salto de ~2pi se NAO unwrap)
    x = np.array([0.0, 1.0])
    raw = np.array([3.10, -3.10])           # ~+pi para ~-pi
    # ERRADO: interpolar o angulo cru cria um valor proximo de 0 no meio
    naive_mid = interp_linear_nan(x, raw, np.array([0.5]))[0]
    # CERTO: unwrap primeiro -> sequencia monotona, meio ~ +pi
    uw = np.unwrap(raw)
    good_mid = interp_linear_nan(x, uw, np.array([0.5]))[0]
    assert abs(naive_mid) < 0.1                      # naive colapsa pra ~0 (errado)
    assert abs(good_mid - np.pi) < 0.1               # unwrap preserva a fase (~pi)
