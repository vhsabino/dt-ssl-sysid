"""Single trajectory overlay of the MEDIAN hold-out window (representative, not
cherry-picked): measured vs twin (FOPDT) vs ideal kinematics vs rSim (ODE, from
the persisted cache), anchored at t0, h = 1.5 s.

The window is the one whose twin e_pos at h=90 is the median over all windows
of all hold-out segments. Output ``<out>/figs/trajectory_holdout_en.png``.

Legacy: scripts/fig_trajectory_holdout.py -> results/figs/trajectory_holdout_en.png.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from dtssl.analysis import common as C
from dtssl.models import AnalyticFOPDTPlant, IdealKinematicPlant

NAME = "fig_trajectory_holdout"
KIND = "fig"
CLAIM = "Median-window trajectory overlay (measured / twin / ideal / rSim)"
REQUIRES = ("data", "rsim_cache")
H_SHOW = 90


def compute(ctx: C.Ctx) -> dict:
    segs, _ = ctx.holdout()
    P, H = ctx.params, ctx.horizons
    tw = C.ros(segs, lambda: AnalyticFOPDTPlant(P), horizons=H)
    idl = C.ros(segs, lambda: IdealKinematicPlant(), horizons=H)
    rs = C.load_rsim_cache(ctx, n_expected=len(segs))
    cand = []
    for si in range(len(segs)):
        for wi, w in enumerate(tw[si].windows):
            e = float(np.hypot(*(w.pose_sim[H_SHOW][:2] - w.pose_real[H_SHOW][:2])))
            cand.append((e, si, wi))
    cand.sort()
    e, si, wi = cand[len(cand) // 2]
    return dict(e=e, si=si, wi=wi, event=segs[si].meta.get("event"), wa=tw[si].windows[wi],
                wb=idl[si].windows[wi], wc=rs[si].windows[wi])


def figure(ctx: C.Ctx, r: dict, name: str = "trajectory_holdout_en.png") -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def anch(Pz):
        return Pz[:, 0] - Pz[0, 0], Pz[:, 1] - Pz[0, 1]

    real = r["wa"].pose_real
    fig, ax = plt.subplots(figsize=(2.5, 3.0))
    for Pz, st, lab, lw_ in [(real, "k-", "measured", 1.8), (r["wa"].pose_sim, "r--", "twin (FOPDT)", 1.5),
                             (r["wb"].pose_sim, "-.", "ideal kinematics", 1.2),
                             (r["wc"].pose_sim, ":", "rSim (ODE)", 1.4)]:
        x, y = anch(np.asarray(Pz)); ax.plot(x, y, st, lw=lw_, label=lab)
    x, y = anch(real); ax.plot(x[0], y[0], "ko", ms=4)
    ax.set_xlabel("x displacement from anchor (m)", fontsize=8)
    ax.set_ylabel("y displacement (m)", fontsize=8)
    ax.tick_params(labelsize=7); ax.grid(alpha=.3, lw=.4); ax.axis("equal")
    ax.legend(fontsize=6.5, loc="upper left", framealpha=.9)
    plt.tight_layout(pad=0.3)
    o = ctx.figs / name
    plt.savefig(o, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return o


def run(root: Path | None = None, out: Path | None = None, *, latex_copy: bool = False,
        quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out)
    r = compute(ctx)
    if not quiet:
        print(f"janela mediana: seg={r['si']} ({r['event']}) win={r['wi']} e_pos(1.5s)={r['e']:.4f} m")
    png = figure(ctx, r)
    copied = C.copy_figure(png, ctx, png.name, latex_copy)
    if not quiet:
        print("gerada", png)
    return dict(path=png, latex=copied, e_pos=r["e"], seg=r["si"], event=r["event"], window=r["wi"])


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
