"""``dtssl.analysis.protocol_holdout`` (C2b): variants, NaN-aware summary and rendering without any
simulator; end-to-end ``compute`` against an in-process ``dtssl serve`` (``requires_net``)."""
from __future__ import annotations

import json
import socket
import sys

import numpy as np
import pytest

from dtssl.analysis import REGISTRY
from dtssl.analysis import common as C
from dtssl.analysis import protocol_holdout as PH
from dtssl.models import AnalyticFOPDTPlant, DofParam, load_twin_params
from dtssl.paths import repo_root
from dtssl.sim.protocol_plant import ProtocolStats
from dtssl.sim.rollout import free_run

TS = 1.0 / 60.0


def _synth_segment(plant, N: int, seed: int = 0):
    from dtssl.data.loader import body_velocity_series
    from dtssl.data.schema import Segment

    t = np.arange(N) * TS
    cmd = np.column_stack([0.8 + 0.6 * np.sin(2 * np.pi * 0.25 * t), 0.4 * np.sin(2 * np.pi * 0.17 * t + 0.5),
                           1.2 * np.sin(2 * np.pi * 0.11 * t)])
    traj = free_run(plant, cmd[:-1], pose0=(0.0, 0.0, 0.0), velb0=(0, 0, 0), dt=TS)
    traj[:, :2] += 0.002 * np.random.default_rng(seed).standard_normal((N, 2))   # "measurement" noise
    vbx, vby, vw = body_velocity_series(t, traj[:, 0], traj[:, 1], traj[:, 2])
    return Segment(meta={"event": f"synth{seed}", "label": "synth", "dataset": "synth"}, ts=TS, t=t,
                   dt=np.full(N, TS), cmd_vx=cmd[:, 0], cmd_vy=cmd[:, 1], cmd_w=cmd[:, 2], pos_x=traj[:, 0],
                   pos_y=traj[:, 1], theta=traj[:, 2], vel_x_world=np.zeros(N), vel_y_world=np.zeros(N),
                   velb_x=vbx, velb_y=vby, velb_w=vw, pose0=(0.0, 0.0, 0.0), velb0=(vbx[0], vby[0], vw[0]))


class _FlakyPlant:
    """Batch plant (``free_run_window``) = analytic twin with a bias, that loses every ``fail_every``-th window
    (all-NaN after pose0) like a protocol replay whose teleport was not seen."""

    def __init__(self, params, fail_every: int = 3):
        self.inner = AnalyticFOPDTPlant(params)
        self.fail_every = fail_every
        self.calls = 0
        self.params = None

    def free_run_window(self, win_cmds, pose0, velb0, dt, prev_cmds=None):
        self.calls += 1
        pose = free_run(self.inner, np.asarray(win_cmds) * 1.15, pose0, velb0, dt, prev_cmds=prev_cmds)
        if self.calls % self.fail_every == 0:
            pose[1:] = np.nan
        return pose


def test_registered_with_the_net_requirement():
    assert REGISTRY["protocol_holdout"] == "dtssl.analysis.protocol_holdout"
    assert PH.NAME == "protocol_holdout" and PH.KIND == "analysis" and set(PH.REQUIRES) == {"data", "net"}


def test_cache_names_round_trip():
    assert PH.parse_cache_name(PH.cache_stem("grsim", "20260910_1200") + ".npz") == ("grsim", "20260910_1200", 0)
    assert PH.parse_cache_name("results/" + PH.cache_stem("erforce+delay", "20260910_120000", 1) + ".npz") == (
        "erforce+delay", "20260910_120000", 1)
    with pytest.raises(KeyError):
        PH.parse_cache_name("results/_cache_rsim_rollouts.npz")


def test_zero_ic_twin_equals_the_twin_only_when_the_window_starts_at_rest():
    P = load_twin_params()
    cmd = np.tile([0.6, 0.2, 0.3], (30, 1))
    a = free_run(AnalyticFOPDTPlant(P), cmd, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), TS)
    b = free_run(PH._ZeroICPlant(P), cmd, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), TS)
    np.testing.assert_allclose(a, b)
    a = free_run(AnalyticFOPDTPlant(P), cmd, (0.0, 0.0, 0.0), (0.6, 0.2, 0.3), TS)
    b = free_run(PH._ZeroICPlant(P), cmd, (0.0, 0.0, 0.0), (0.6, 0.2, 0.3), TS)
    assert np.hypot(*(a[-1, :2] - b[-1, :2])) > 1e-3                # the moving IC is dropped


def test_variants_follow_the_delay_option():
    assert PH._variants(["grsim"], "none") == [("grsim", "grsim", None)]
    assert PH._variants(["grsim"], "theta") == [("grsim+delay", "grsim", "theta")]
    assert PH._variants(["grsim", "erforce"], "both") == [
        ("grsim", "grsim", None), ("grsim+delay", "grsim", "theta"),
        ("erforce", "erforce", None), ("erforce+delay", "erforce", "theta")]


def test_summary_excludes_lost_windows_and_counts_them(tmp_path):
    ctx = C.make_context(repo_root(), tmp_path)
    P, H = ctx.params, ctx.horizons
    segs = [_synth_segment(AnalyticFOPDTPlant(P), N=260, seed=s) for s in range(3)]
    tw = C.ros(segs, lambda: AnalyticFOPDTPlant(P), horizons=H)
    flaky = _FlakyPlant(P, fail_every=3)
    ro = C.ros(segs, lambda: flaky, horizons=H)
    n_win = sum(r.n_total for r in tw)
    assert n_win >= 9 and flaky.calls == n_win
    kref = H.index(int(ctx.mcfg["verdict"]["h_ref"]))
    with np.errstate(all="ignore"):
        S = PH._summarise(ctx, tw, ro, H, kref)
    assert S["n_windows"] == n_win and S["n_failed"] == n_win // 3
    assert len(S["rows"]) == len(H) and all(r["h"] == h for r, h in zip(S["rows"], H, strict=True))
    for r in S["rows"]:
        assert np.isfinite(r["epos_model_trans"]) and np.isfinite(r["epos_twin_trans"])
        assert 0.0 <= r["p_wilcoxon"] <= 1.0 and r["n_events"] == 3
    # the biased plant is worse than the twin on every event and the gap is positive
    assert S["rows"][kref]["wins"] == 3 and S["gap_vs_twin_med"] > 0.0
    assert len(S["per_event"]) == 3 and len(S["epos_href"]) == n_win
    assert sum(1 for v in S["epos_href"] if not np.isfinite(v)) == n_win // 3


def test_instrument_validity_flags_lost_windows_and_missing_diagnostics():
    good = dict(n_windows=265, n_failed=3, diagnostics=dict(send_jitter_max=0.03, send_jitter_mean=0.0005, send_late=3,
                                                            controls_sent=265 * 89, teleport_latency_spread=0.005,
                                                            vision_period_wall=1 / 60, tau0_estimated=200, windows=265))
    assert PH.instrument_validity(good)[0]
    bad = dict(good, n_failed=20)
    ok, text = PH.instrument_validity(bad)
    assert not ok and "janelas perdidas FALHA" in text
    stalls = dict(good, diagnostics=dict(good["diagnostics"], send_late=400))
    ok, text = PH.instrument_validity(stalls)
    assert not ok and "jitter de envio FALHA" in text
    assert not PH.instrument_validity(dict(n_windows=10, n_failed=0, diagnostics={}))[0]


def test_render_lists_every_variant_and_the_diagnostics(tmp_path):
    ctx = C.make_context(repo_root(), tmp_path)
    P, H = ctx.params, ctx.horizons
    segs = [_synth_segment(AnalyticFOPDTPlant(P), N=200, seed=s) for s in range(2)]
    tw = C.ros(segs, lambda: AnalyticFOPDTPlant(P), horizons=H)
    ro = C.ros(segs, lambda: _FlakyPlant(P, fail_every=10 ** 6), horizons=H)
    h_ref = int(ctx.mcfg["verdict"]["h_ref"])
    kref = H.index(h_ref)
    models, order = {}, []
    for label in ("grsim", "grsim+delay"):
        S = PH._summarise(ctx, tw, ro, H, kref)
        S.pop("epos_href")
        S["diagnostics"] = ProtocolStats().as_dict()
        S["endpoint"] = dict(name="grsim", host="127.0.0.1", vision="224.5.23.2:10020", control_port=10301,
                             team="blue", robot_id=0)
        S["repeat"] = dict(n=2, abs_diff_med=0.001, abs_diff_p90=0.003, medians=[0.05, 0.051])
        models[label] = S
        order.append(label)
    r = dict(models=models, order=order, horizons=list(H), h_ref=h_ref, h_ref_s=h_ref * TS, n_events=2,
             n_windows=sum(x.n_total for x in tw), events=["synth0", "synth1"], dropped=[],
             cost_s={"fopdt": 0.1, "grsim": 12.0, "grsim+delay": 12.5},
             caches={"grsim": str(tmp_path / "_cache_protocol_grsim_x.npz")}, delay="both", repeat=2)
    text = "\n".join(PH.render(ctx, r))
    assert "| grsim | " in text and "| grsim+delay | " in text
    assert "## Diagnostico do replay via protocolo" in text and "## Repetibilidade" in text
    assert "_cache_protocol_grsim_x.npz" in text and "## Leitura" in text
    json.dumps(r, default=str)                                   # what run() writes


# ---------------------------------------------------------------- end to end against dtssl serve
def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.mark.requires_net
def test_compute_against_an_in_process_twin_server(tmp_path, monkeypatch):
    """``compute`` with ``sims=[test]`` (dtssl serve, fopdt, Td = 0) and ``delay=theta``: the protocol replay
    reproduces the twin, caches are written, diagnostics and repeatability are filled."""
    from dtssl.bridge.config import BridgeConfig
    from dtssl.bridge.server import SimServer
    from dtssl.sim.backends import make_world

    theta = load_twin_params()
    theta_nodelay = {d: DofParam(K=p.K, tau=p.tau, Td=0.0) for d, p in theta.items()}
    world = make_world("fopdt", n_blue=1, n_yellow=0, params=theta_nodelay, watchdog_clock="sim")
    vport = _free_port()
    cfg = BridgeConfig.load().with_overrides(vision_ip="127.0.0.1", vision_port=vport, blue_port=0, yellow_port=0,
                                             simcontrol_port=0, bind_ip="127.0.0.1")
    srv = SimServer(world, cfg)
    srv.start()
    th = srv.run_in_thread()
    try:
        eps = tmp_path / "external_sims.json"
        eps.write_text(json.dumps({"test": dict(
            host="127.0.0.1", port_blue=srv.control.port("blue"), port_simcontrol=srv.simcontrol.port,
            vision_ip="127.0.0.1", vision_port=vport, unicast=True, team="blue", robot_id=0, vision_rate=60.0,
            clear_others=False)}), encoding="utf-8")
        ctx = C.make_context(repo_root(), tmp_path / "out")
        seg = _synth_segment(AnalyticFOPDTPlant(theta), N=120, seed=1)      # 2 windows of H_max = 90
        monkeypatch.setattr(ctx, "holdout", lambda *a, **k: ([seg], []))
        r = PH.compute(ctx, ["test"], delay="theta", repeat=2, save_cache=True, endpoints_path=eps)
    finally:
        srv.stop()
        th.join(timeout=2.0)
    assert r["order"] == ["test+delay"] and r["n_events"] == 1 and r["n_windows"] == 2
    M = r["models"]["test+delay"]
    assert M["n_failed"] == 0 and M["diagnostics"]["anchor_failures"] == 0
    assert M["diagnostics"]["windows"] == 2 and M["diagnostics"]["teleports"] >= 2 + 3
    assert M["gap_vs_twin_max"] < 3e-3, M                        # mm-level agreement with the analytic twin
    assert M["repeat"]["n"] == 2 and M["repeat"]["abs_diff_p90"] < 3e-3
    assert set(r["caches"]) == {"test+delay#0", "test+delay#1"}
    for p in r["caches"].values():
        assert p.endswith(".npz") and (tmp_path / "out" / p.split("/")[-1].split("\\")[-1]).is_file()
    text = "\n".join(PH.render(ctx, r))
    assert "| test+delay | " in text and "## Repetibilidade" in text and "fopdt_v0=0" in text
    ok, verdict = PH.instrument_validity(M)
    if sys.platform == "win32" and not ok:                         # in-process server + GIL: jitter only, on Windows
        assert "janelas perdidas ok" in verdict and "tau0 estimado ok" in verdict, verdict
    else:
        assert ok, verdict
        assert "- test+delay: VALIDO" in text
    assert M["diagnostics"]["anchor_late"] == 0, M["diagnostics"]
    assert len(r["twin_v0zero"]["rows"]) == len(r["horizons"])
    # offline re-analysis of the caches reproduces the numbers (labels/repeats from the file names)
    ctx2 = C.make_context(repo_root(), tmp_path / "out2")
    monkeypatch.setattr(ctx2, "holdout", lambda *a, **k: ([seg], []))
    r2 = PH.compute_from_caches(ctx2, [str(tmp_path / "out" / "_cache_protocol_test_delay_*.npz")])
    assert r2["order"] == ["test+delay"] and r2["repeat"] == 2 and r2["delay"] == "theta"
    M2 = r2["models"]["test+delay"]
    assert json.dumps(M2["rows"]) == json.dumps(M["rows"])          # NaN-safe equality (1 event: p = NaN)
    assert M2["repeat"] == M["repeat"] and M2["diagnostics"] == M["diagnostics"]
    assert M2["endpoint"]["teleport_omega"] is True
    with pytest.raises(ValueError):                                  # a cache of another hold-out is refused
        other = _synth_segment(AnalyticFOPDTPlant(theta), N=120, seed=2)
        monkeypatch.setattr(ctx2, "holdout", lambda *a, **k: ([other], []))
        PH.compute_from_caches(ctx2, list(r["caches"].values()))
