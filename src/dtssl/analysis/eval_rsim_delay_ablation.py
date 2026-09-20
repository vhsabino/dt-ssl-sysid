"""Ablation "rSim + matched transport delay" (reviewer B5/B6).

The twin-vs-rSim comparison has ONE structural asymmetry: only the twin carries
an explicit transport delay. This ablation bounds that share: the twin's Td is
applied to the OUTPUT of rSim as a pure shift (``pose_out[h] = pose_rsim[max(0, h-m)]``)
without re-simulating, with ``m = ceil(Td_trans/dt)`` and ``Td_trans`` = mean
of ``Td_vx`` and ``Td_vy`` (the pose is a joint object, so one translational
delay is used).

Two modes:

* ``mode="cache"`` — roll rSim (``RSimReplay(warmup=True, sub_ms=1)``, mode A)
  segment by segment within a time budget and PERSIST the rollouts in
  ``<out>/_cache_rsim_rollouts.npz`` (``dtssl.sim.rollout.save_rollouts``).
  Requires robosim; repeat until "COMPLETO".
* ``mode="finalize"`` (default) — read the cache (``.npz`` or the legacy ``.pkl``),
  roll the twin, evaluate twin vs rSim and twin vs rSim+Td on the same windows
  and write ``eval_rsim_delay_ablation_<stamp>.md``.

Legacy: scripts/eval_rsim_delay_ablation.py -> results/eval_rsim_delay_ablation_20260809_2154.md.
"""
from __future__ import annotations

import copy
import math
import time
from pathlib import Path

import numpy as np

from dtssl.analysis import common as C
from dtssl.eval.metrics import evaluate
from dtssl.models import AnalyticFOPDTPlant

NAME = "eval_rsim_delay_ablation"
KIND = "analysis"
CLAIM = "Matched-delay ablation on rSim (delay term does not explain the gap; B5/B6)"
REQUIRES = ("data", "rsim_cache")     # mode=cache additionally needs robosim


def do_cache(ctx: C.Ctx, budget_s: float = 32.0, sub_ms: int = C.SUB_MS, quiet: bool = False) -> dict:
    """Roll rSim segment by segment until the budget is exhausted; extends an existing cache."""
    from dtssl.analysis.eval_twin_vs_rsim import _silence_engine_stdout
    from dtssl.models.rsim import RSimReplay

    segs, _ = ctx.holdout()
    H = ctx.horizons
    try:
        cache = C.load_rsim_cache(ctx)
    except FileNotFoundError:
        cache = []
    t_start = time.time()
    done_now = 0
    for i, s in enumerate(segs):
        if i < len(cache):
            continue
        if time.time() - t_start > budget_s:
            break
        with _silence_engine_stdout():
            ro = C.ros([s], lambda: RSimReplay(warmup=True, sub_ms=sub_ms), horizons=H)[0]
        cache.append(ro)
        done_now += 1
        C.save_rsim_cache_npz(cache, ctx.out / f"{C.RSIM_CACHE_STEM}.npz")
    complete = len(cache) >= len(segs)
    if not quiet:
        print(f"cache: {len(cache)}/{len(segs)} segmentos (+{done_now} nesta chamada)")
        if complete:
            print("COMPLETO — rode com mode=finalize")
    return dict(path=ctx.out / f"{C.RSIM_CACHE_STEM}.npz", n_cached=len(cache), n_total=len(segs),
                complete=complete)


def shift_rollout(ro, m: int):
    """Pure delay of ``m`` samples applied to the OUTPUT (pose_sim) of every window."""
    out = copy.deepcopy(ro)
    for w in out.windows:
        ps = w.pose_sim
        idx = np.maximum(np.arange(ps.shape[0]) - m, 0)
        w.pose_sim = ps[idx].copy()
    return out


def compute(ctx: C.Ctx) -> dict:
    segs, _ = ctx.holdout()
    P, H = ctx.params, ctx.horizons
    rsim_ros = C.load_rsim_cache(ctx, n_expected=len(segs))[:len(segs)]
    dt = ctx.ts
    td_tr = 0.5 * (P["vx"].Td + P["vy"].Td)
    m = math.ceil(td_tr / dt)
    twin_ros = C.ros(segs, lambda: AnalyticFOPDTPlant(P), horizons=H)
    abl_ros = [shift_rollout(r, m) for r in rsim_ros]
    res_raw = evaluate(twin_ros, rsim_ros, params=P, mcfg=ctx.mcfg)
    res_abl = evaluate(twin_ros, abl_ros, params=P, mcfg=ctx.mcfg)
    a, b = res_raw["scopes"]["trans"], res_abl["scopes"]["trans"]
    ts = res_raw["table"].ts
    rows = [dict(h_s=h * ts, twin=float(a["epos_twin_med"][k]), rsim=float(a["epos_def_med"][k]),
                 gap=float(a["gap_epos"][k]), rsim_td=float(b["epos_def_med"][k]),
                 gap_td=float(b["gap_epos"][k]), delta=float(a["gap_epos"][k] - b["gap_epos"][k]))
            for k, h in enumerate(a["horizons"])]
    return dict(rows=rows, m=m, dt=dt, td_trans=td_tr, n_indep=int(a["n_indep"]))


def render(ctx: C.Ctx, r: dict) -> list[str]:
    m, dt = r["m"], r["dt"]
    L = C.result_header("Ablação rSim + atraso casado", ctx, generator=f"dtssl.analysis.{NAME}")
    L += [f"Atraso aplicado: m = {m} amostras ({m * dt * 1000:.1f} ms), "
          f"Td_trans medio = {r['td_trans'] * 1000:.1f} ms.", "",
          "| h (s) | twin | rSim | gap rSim | rSim+Td | gap rSim+Td | delta |",
          "|---|---|---|---|---|---|---|"]
    for x in r["rows"]:
        L.append(f"| {x['h_s']:.2f} | {x['twin']:.4f} | {x['rsim']:.4f} | {x['gap']:+.4f} | "
                 f"{x['rsim_td']:.4f} | {x['gap_td']:+.4f} | {x['delta']:+.4f} |")
    L += ["", f"N_indep = {r['n_indep']}", "",
          "`delta` = quanto do gap do rSim é explicado pelo termo de atraso."]
    return L


def run(root: Path | None = None, out: Path | None = None, *, mode: str = "finalize",
        budget: float = 32.0, sub_ms: int = C.SUB_MS, quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out)
    if mode == "cache":
        return do_cache(ctx, budget_s=budget, sub_ms=sub_ms, quiet=quiet)
    if mode != "finalize":
        raise ValueError("mode must be 'cache' or 'finalize'")
    r = compute(ctx)
    L = render(ctx, r)
    if not quiet:
        print(f"Td_trans medio = {r['td_trans']:.5f} s ; dt = {r['dt']:.5f} s ; m = {r['m']} amostras "
              f"({r['m'] * r['dt'] * 1000:.1f} ms aplicados)")
    p = ctx.write_text(NAME, L)
    if not quiet:
        print("\n".join(L)); print(f"\nartefato: {p}")
    r["path"] = p
    return r


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
