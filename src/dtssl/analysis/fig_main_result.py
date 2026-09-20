"""Main figure of the paper (Fig. 2): (a) median e_pos vs horizon for ideal, rSim
and FOPDT twin; (b) per-event paired dot plot at h_ref (10 hold-out events).

Twin and ideal are re-simulated; rSim comes from the persisted cache
(``results/_cache_rsim_rollouts.{npz,pkl}``). Numbers are the ones of
``epos_eang_three_models`` / ``clustered_stats``. Output
``<out>/figs/main_result_en.png`` (+ ``latex/figures/main_result_en.png`` with
``latex_copy=True``).

Legacy: scripts/fig_main_result.py -> results/figs/main_result_en.png.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from dtssl.analysis import common as C
from dtssl.models import AnalyticFOPDTPlant, IdealKinematicPlant

NAME = "fig_main_result"
KIND = "fig"
CLAIM = "Main figure (Fig. 2): e_pos vs horizon for three plants + per-event dot plot"
REQUIRES = ("data", "rsim_cache")


def compute(ctx: C.Ctx, h_ref: int = 24) -> dict:
    segs, _ = ctx.holdout()
    P, H = ctx.params, ctx.horizons
    tw = C.ros(segs, lambda: AnalyticFOPDTPlant(P), horizons=H)
    idl = C.ros(segs, lambda: IdealKinematicPlant(), horizons=H)
    rsl = C.load_rsim_cache(ctx, n_expected=len(segs))[:len(segs)]
    T1 = C.paired_table(ctx, tw, idl)
    T2 = C.paired_table(ctx, tw, rsl)
    m = C.trans_mask(T1)
    k = H.index(h_ref)
    ev_t, ev_i, _ = C.per_event_medians(T1, k, m)
    return dict(hs=np.asarray(H) * T1.ts, h_ref_s=h_ref * T1.ts,
                twin=[float(np.median(T1.epos_twin[m, j])) for j in range(len(H))],
                ideal=[float(np.median(T1.epos_def[m, j])) for j in range(len(H))],
                rsim=[float(np.median(T2.epos_def[m, j])) for j in range(len(H))],
                events=list(zip(ev_t.tolist(), ev_i.tolist())))


def figure(ctx: C.Ctx, r: dict, name: str = "main_result_en.png") -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    hs = r["hs"]
    fig, ax = plt.subplots(1, 2, figsize=(7.0, 2.5), gridspec_kw={"width_ratios": [1.25, 1]})
    a = ax[0]
    a.plot(hs, r["ideal"], "o-", color="#1f77b4", lw=1.4, ms=3.5, label="ideal kinematics")
    a.plot(hs, r["rsim"], "s:", color="#ff7f0e", lw=1.4, ms=3.5, label="rSim (untuned ODE)")
    a.plot(hs, r["twin"], "^--", color="#d62728", lw=1.6, ms=4, label="FOPDT model")
    a.axvline(r["h_ref_s"], color="0.6", ls=":", lw=0.9)
    a.text(r["h_ref_s"] + 0.02, 0.012, r"$h_{ref}$", fontsize=7, color="0.4")
    a.set_xlabel("horizon (s)", fontsize=8); a.set_ylabel(r"median $e_{pos}$ (m)", fontsize=8)
    a.tick_params(labelsize=7); a.grid(alpha=.3, lw=.4); a.legend(fontsize=7, loc="upper left")
    a.set_title("(a) free-run position error", fontsize=8)
    b = ax[1]
    ev = r["events"]
    for t, d in ev:
        b.plot([0, 1], [d, t], "-", color="0.75", lw=0.8, zorder=1)
    b.scatter([0] * len(ev), [d for _, d in ev], s=22, color="#1f77b4", zorder=3, label="ideal")
    b.scatter([1] * len(ev), [t for t, _ in ev], s=22, color="#d62728", marker="^", zorder=3, label="model")
    b.set_xlim(-0.35, 1.35); b.set_xticks([0, 1]); b.set_xticklabels(["ideal", "model"], fontsize=8)
    b.set_ylabel(r"per-event median $e_{pos}$ (m)", fontsize=8)
    b.tick_params(labelsize=7); b.grid(alpha=.3, lw=.4, axis="y")
    b.set_title(rf"(b) {len(ev)} hold-out events, $h_{{ref}}$", fontsize=8)
    plt.tight_layout(pad=0.4)
    o = ctx.figs / name
    plt.savefig(o, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return o


def run(root: Path | None = None, out: Path | None = None, *, h_ref: int = 24,
        latex_copy: bool = False, quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out)
    r = compute(ctx, h_ref=h_ref)
    png = figure(ctx, r)
    copied = C.copy_figure(png, ctx, png.name, latex_copy)
    if not quiet:
        print("gerada.", png)
        print("twin ", [f"{v:.4f}" for v in r["twin"]])
        print("ideal", [f"{v:.4f}" for v in r["ideal"]])
        print("rsim ", [f"{v:.4f}" for v in r["rsim"]])
    return dict(path=png, latex=copied, **{k: r[k] for k in ("twin", "ideal", "rsim", "events")})


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
