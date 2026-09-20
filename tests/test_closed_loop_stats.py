"""C4 ``dtssl.analysis.closed_loop_stats``: Cliff's delta, window cutting, grid resampling, the
pre-registered P1-P5 rule on synthetic distributions (data-free) and one end-to-end run on
``results/sessao_01`` when the session and the dataset are present."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from dtssl.analysis import closed_loop_stats as M
from dtssl.paths import repo_root

TS = 1.0 / 60.0


def _series(n: int, vx=0.5, vy=0.0, w=0.2, name="s", t0=0.0, front=False) -> M.CmdSeries:
    t = t0 + np.arange(n) * TS
    return M.CmdSeries(name=name, t=t, vx=np.full(n, vx), vy=np.full(n, vy), w=np.full(n, w),
                       front=np.full(n, front), chip=np.zeros(n, bool), group="g", unit=name)


def test_cliffs_delta_known_values():
    assert M.cliffs_delta([1, 2, 3], [1, 2, 3]) == pytest.approx(0.0)
    assert M.cliffs_delta([4, 5, 6], [1, 2, 3]) == pytest.approx(1.0)
    assert M.cliffs_delta([1, 2, 3], [4, 5, 6]) == pytest.approx(-1.0)
    # x = {1, 2}, y = {1.5}: one pair larger, one smaller -> 0; x = {1, 2, 3}, y = {2}: (1 - 1) / 3 = 0
    assert M.cliffs_delta([1, 2], [1.5]) == pytest.approx(0.0)
    # x = {3, 4}, y = {1, 2, 3.5}: pairs > : 3>1,3>2,4>1,4>2,4>3.5 = 5; < : 3<3.5 = 1 -> (5-1)/6
    assert M.cliffs_delta([3, 4], [1, 2, 3.5]) == pytest.approx(4 / 6)
    assert np.isnan(M.cliffs_delta([], [1.0]))


def test_window_cutting_and_event_medians():
    s = _series(int(round(35.0 / TS)) + 1, vx=1.0, w=0.3)          # 35 s -> 3 full windows + one of 5 s
    mv, mw, meta = M.window_medians([s], window_s=10.0, ts=TS, min_fill=0.5)
    assert len(meta) == 4 and [m["window"] for m in meta] == [0, 1, 2, 3]   # 5 s = 50 % -> kept
    mv, mw, meta = M.window_medians([s], window_s=10.0, ts=TS, min_fill=0.6)
    assert len(meta) == 3                                            # the 5 s tail is dropped
    assert np.allclose(mv, 1.0) and np.allclose(mw, 0.3)
    # two series with a time offset are cut from their own first sample
    s2 = _series(int(round(20.0 / TS)) + 1, vx=0.0, vy=2.0, w=-1.0, name="s2", t0=100.0)
    mv, mw, meta = M.window_medians([s, s2], window_s=10.0, ts=TS)
    assert len(meta) == 4 + 2 and set(mv.round(6)) <= {1.0, 2.0} and set(mw.round(6)) <= {0.3, 1.0}  # s2: 1-sample tail dropped
    ev, ew = M.event_medians([s, s2])
    assert np.allclose(ev, [1.0, 2.0]) and np.allclose(ew, [0.3, 1.0])


def test_to_grid_zoh_and_duplicates():
    t = np.array([0.0, 0.004, 0.004, 0.030, 0.100])                 # bursty log with a duplicate timestamp
    cmd = pd.DataFrame(dict(timestamp=t, move_x=[0.0, 1.0, 2.0, 3.0, 4.0], move_y=0.0, move_w=[0, 0, 0, 1, 1],
                            actuation_front=[False, False, True, True, False], actuation_chip=False))
    s = M.to_grid(cmd, name="e", group="g", unit="e", ts=TS)
    assert s.n == 7                                                  # 0, 1/60, ..., 6/60 = 0.1 s
    assert s.vx[0] == 0.0 and s.vx[1] == 2.0 and s.vx[2] == 3.0 and s.vx[-1] == 4.0   # last row wins the duplicate
    assert s.front.tolist()[:3] == [False, True, True] and not s.front[-1]
    assert M.to_grid(cmd.iloc[:1], name="e", group="g", unit="e") is None


def test_series_stats_and_deadzone_flags():
    still = _series(60, vx=0.0, w=0.0)
    slow_turn = _series(60, vx=0.0, w=0.3)                            # pure rotation below the body deadzone
    fast = _series(60, vx=3.0, w=1.0)
    st = M.series_stats([still, slow_turn, fast], ts=TS)
    assert st["n"] == 180 and st["frac_idle"] == pytest.approx(1 / 3)
    assert st["frac_w_below_dz"] == pytest.approx(2 / 3)
    assert st["frac_dz_clamped"] == pytest.approx(1 / 3) and st["frac_dz_altered"] == pytest.approx(1 / 3)
    assert st["frac_v_sat"] == pytest.approx(1 / 3) and st["dv_med"] == 0.0
    assert st["v_q"]["p99"] == pytest.approx(3.0) and st["w_max"] == pytest.approx(1.0)


def test_criteria_rule_on_synthetic_distributions():
    rng = np.random.default_rng(0)
    v_c = rng.gamma(2.0, 0.4, 20000)
    w_c = rng.gamma(1.5, 0.3, 20000)

    def stats(v, w, dv=0.02):
        return dict(frac_w_below_dz=float((w < 0.58).mean()), frac_v_sat=float((v > 2.9).mean()), dv_med=dv, dv_mean=dv)

    same = M.criteria(stats(v_c, w_c), stats(v_c, w_c), M.distances(v_c, v_c), M.distances(w_c, w_c),
                      M.compare_medians(np.full(100, 0.7), np.full(50, 0.7)),
                      M.compare_medians(np.full(100, 0.3), np.full(50, 0.3)))
    assert same["score"] == 5 and same["verdict"] == "plausivel"
    # shifted session: |v| + 0.5 m/s, w x 3, saturation 10 %, rough commands
    v_s, w_s = v_c + 0.5, w_c * 3.0
    v_s[:2000] = 3.5
    shifted = M.criteria(stats(v_s, w_s, dv=0.2), stats(v_c, w_c), M.distances(v_s, v_c), M.distances(w_s, w_c),
                         M.compare_medians(np.full(100, 1.2), np.full(50, 0.7)),
                         M.compare_medians(np.full(100, 0.9), np.full(50, 0.3)))
    assert not shifted["P1"]["ok"] and not shifted["P2"]["ok"] and not shifted["P3"]["ok"]
    assert not shifted["P4"]["ok"] and not shifted["P5"]["ok"]
    assert shifted["score"] == 0 and shifted["verdict"] == "nao plausivel"
    # P5 fallback to the mean when a median is zero (declared in the pre-registration)
    z = M.criteria(dict(stats(v_c, w_c), dv_med=0.0, dv_mean=0.01), dict(stats(v_c, w_c), dv_med=0.0, dv_mean=0.015),
                   M.distances(v_c, v_c), M.distances(w_c, w_c),
                   M.compare_medians(np.full(10, 0.7), np.full(5, 0.7)), M.compare_medians(np.full(10, 0.3), np.full(5, 0.3)))
    assert z["P5"]["stat"] == "dv_mean" and z["P5"]["ok"]


@pytest.mark.requires_data
def test_run_on_sessao_01(tmp_path):
    root = repo_root()
    if not (root / "results" / "sessao_01" / "commands.parquet").is_file():
        pytest.skip("results/sessao_01 not present")
    r = M.run(out=tmp_path, quiet=True)
    assert r["path"].parent == tmp_path and r["path"].name.startswith("closed_loop_stats_")
    assert Path(r["figure"]).is_file() and Path(r["figure"]).parent == tmp_path / "figs"
    text = r["path"].read_text(encoding="utf-8")
    assert text.isascii() and "Veredito" in text and "P1 W1" in text
    with open(r["json"], encoding="utf-8") as f:
        j = json.load(f)
    assert j["competition"]["n_events"] == 46 and 0 <= j["criteria"]["score"] <= 5
    assert j["sessions"][0]["keeper"] == 0 and len(j["windows"]["v"]) >= 100
