"""End-to-end smoke of the two cheapest paper analyses into ``tmp_path`` (needs the dataset).

``clustered_stats`` and ``gate_window_vs_event`` (twin vs ideal on the hold-out, ~2 s each)
must write a stamped Markdown with the provenance header and reproduce the published key
numbers (results/clustered_stats_20260809_2309.md, results/gate_window_vs_event_20260810_1743.md).
Also exercises the ``.npz`` rSim-cache round trip and the CSV/parquet reader (no rollouts).
"""
from __future__ import annotations

import numpy as np
import pytest

from dtssl.analysis import clustered_stats, gate_window_vs_event
from dtssl.analysis import common as C

pytestmark = pytest.mark.requires_data


def test_clustered_stats_end_to_end(tmp_path):
    r = clustered_stats.run(out=tmp_path, quiet=True)
    p = r["path"]
    assert p.parent == tmp_path and p.name.startswith("clustered_stats_") and p.suffix == ".md"
    text = p.read_text(encoding="utf-8")
    assert text.startswith("# Estatistica agrupada por EVENTO")
    assert "_Proveniencia: commit" in text and "dataset `2026-05-18_19-2-15`" in text
    # published numbers (results/clustered_stats_20260809_2309.md)
    assert len(r["rows"]) == 10 and r["wins"] == 10 and r["losses"] == 0
    assert r["gap"] == pytest.approx(0.0689, abs=5e-5)
    assert r["p"] == pytest.approx(0.0009766, rel=1e-3)
    assert r["n_trans"] == 264 and r["n_indep"] == 49
    assert r["seconds"] == pytest.approx(73.5, abs=1e-6)
    assert r["ci"][0] == pytest.approx(0.0375, abs=5e-5) and r["ci"][1] == pytest.approx(0.0969, abs=5e-5)
    assert "| 0 | 0.0172 | 0.0547 | +0.0375 | 27 |" in text


def test_gate_window_vs_event_end_to_end(tmp_path):
    r = gate_window_vs_event.run(out=tmp_path, quiet=True)
    assert r["path"].parent == tmp_path
    w, e = r["window"], r["event"]
    assert w["n"] == 49 and e["n"] == 10
    assert w["gap"] == pytest.approx(0.0541, abs=5e-5) and e["gap"] == pytest.approx(0.0689, abs=5e-5)
    assert w["rb"] == pytest.approx(0.633, abs=5e-4) and e["rb"] == pytest.approx(1.0)
    assert w["p"] == pytest.approx(1.15e-8, rel=5e-2) and e["p"] == pytest.approx(0.000977, rel=1e-2)
    assert w["ci"] == pytest.approx((0.0251, 0.0830), abs=5e-5)
    assert "| GO |" in r["path"].read_text(encoding="utf-8")


def test_rsim_cache_npz_roundtrip(tmp_path):
    ctx = C.make_context(out=tmp_path)
    if C.rsim_cache_path(ctx) is None:
        pytest.skip("results/_cache_rsim_rollouts.{npz,pkl} not present")
    ros = C.load_rsim_cache(ctx)
    assert len(ros) == 10 and ros[0].meta["plant"] == "RSimReplay"
    npz = C.save_rsim_cache_npz(ros, tmp_path / "_cache_rsim_rollouts.npz")
    assert C.rsim_cache_path(ctx) == npz                    # <out> takes precedence over results/
    back = C.load_rsim_cache(ctx, n_expected=10)
    for a, b in zip(ros, back):
        assert a.meta["event"] == b.meta["event"] and len(a.windows) == len(b.windows)
        for wa, wb in zip(a.windows, b.windows):
            assert wa.t0 == wb.t0 and np.array_equal(wa.pose_sim, wb.pose_sim)
            assert np.array_equal(wa.cmd, wb.cmd) and wa.idle == wb.idle


def test_read_event_csv_and_legacy_series():
    ctx = C.make_context()
    cmd, rob = C.read_event_csv("front_to_back", "front_to_back_01_01", dataset=ctx.dataset,
                                data_root=ctx.data_root)
    assert {"timestamp", "timestamp_event", "move_x", "move_y", "move_w"} <= set(cmd.columns)
    assert {"timestamp", "position_x", "position_y", "position_w"} <= set(rob.columns)
    u, y = C.legacy_uy_series(cmd, rob, "vx", ctx.ts, min_len=40, pos_scale=1e-3)
    assert u.shape == y.shape and u.size > 400
    assert np.corrcoef(u[:-5], y[5:])[0, 1] > 0.9      # vx is well excited in front_to_back
    assert C.legacy_uy_series(cmd, rob, "vx", ctx.ts, min_len=10**6) is None
