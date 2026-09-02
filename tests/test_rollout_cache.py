"""Rollout serialisation (.npz + JSON meta) and legacy pickle conversion. No dataset needed."""
import dataclasses
import json

import numpy as np
import pytest

from dtssl.paths import repo_root
from dtssl.sim.rollout import (ROLLOUT_NPZ_FORMAT, Window, WindowRollout, convert_pickle_cache,
                               load_rollouts, save_rollouts)

TS = 1.0 / 60.0


def _synthetic_rollout(seed: int, n_windows: int, h_max: int = 12, event: str = "synth") -> WindowRollout:
    rng = np.random.default_rng(seed)
    wins = []
    for k in range(n_windows):
        t0 = 7 + 15 * k
        wins.append(Window(t0=t0, t0_time=t0 * TS,
                           pose_sim=rng.normal(size=(h_max + 1, 3)),
                           pose_real=rng.normal(size=(h_max + 1, 3)),
                           cmd=rng.normal(size=(h_max, 3)),
                           velb=rng.normal(size=(h_max + 1, 3)),
                           velb0=tuple(float(v) for v in rng.normal(size=3)),
                           trans_peak=float(rng.uniform()), trans_mean=float(rng.uniform()),
                           rot_peak=float(rng.uniform()), rot_mean=float(rng.uniform()),
                           idle=bool(k % 2)))
    meta = dict(event=event, label="lab", dataset="ds", ts=TS, n_samples=500, h_max=h_max,
                horizons=(6, 12), stride=15, lookback=16, max_delay=6, idx_min=7, t0_anchor=7,
                plant="AnalyticFOPDTPlant", trans_floor=0.05, rot_floor=0.1)
    return WindowRollout(meta=meta, windows=wins)


def _assert_same(a: WindowRollout, b: WindowRollout):
    assert a.meta == b.meta
    assert isinstance(b.meta["horizons"], tuple)
    assert len(a.windows) == len(b.windows)
    for wa, wb in zip(a.windows, b.windows):
        for f in dataclasses.fields(Window):
            va, vb = getattr(wa, f.name), getattr(wb, f.name)
            if isinstance(va, np.ndarray):
                assert np.array_equal(va, vb) and vb.dtype == np.float64, f.name
            else:
                assert va == vb and type(va) is type(vb), f.name


def test_npz_round_trip_list(tmp_path):
    ros = [_synthetic_rollout(1, 5), _synthetic_rollout(2, 3, event="other")]
    p = save_rollouts(tmp_path / "cache", ros)                  # suffix added
    assert p.suffix == ".npz" and p.with_suffix(".json").is_file()
    side = json.loads(p.with_suffix(".json").read_text(encoding="utf-8"))
    assert side["format"] == ROLLOUT_NPZ_FORMAT and side["n_rollouts"] == 2
    assert side["rollouts"][1]["event"] == "other"
    back = load_rollouts(p)
    assert isinstance(back, list) and len(back) == 2
    for a, b in zip(ros, back):
        _assert_same(a, b)


def test_npz_round_trip_dict_and_empty_rollout(tmp_path):
    ros = {"0": _synthetic_rollout(3, 4), "1": _synthetic_rollout(4, 0)}   # one rollout without windows
    p = save_rollouts(tmp_path / "d.npz", ros)
    back = load_rollouts(p, as_dict=True)
    assert list(back) == ["0", "1"]
    _assert_same(ros["0"], back["0"])
    assert back["1"].windows == [] and back["1"].meta["h_max"] == 12
    assert isinstance(load_rollouts(p), list)                 # as_dict=False -> plain list


def test_load_rejects_foreign_npz(tmp_path):
    np.savez(tmp_path / "x.npz", a=np.zeros(3))
    with pytest.raises(ValueError):
        load_rollouts(tmp_path / "x.npz")


def test_convert_legacy_pickle(tmp_path):
    pkl = repo_root() / "results" / "_cache_rsim_rollouts.pkl"
    if not pkl.is_file():
        pytest.skip("legacy pickle cache not present")
    p = convert_pickle_cache(pkl, tmp_path / "rsim.npz")
    ros = load_rollouts(p, as_dict=True)
    assert list(ros) == [str(i) for i in range(10)]
    assert ros["0"].meta["plant"] == "RSimReplay" and ros["0"].meta["event"] == "front_to_back_01_01"
    assert sum(r.n_total for r in ros.values()) == 265
    w = ros["0"].windows[0]
    assert w.pose_sim.shape == (91, 3) and w.cmd.shape == (90, 3) and w.t0 == 7
