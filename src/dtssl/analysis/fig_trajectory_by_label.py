"""Trajectory overlay by LABEL: 2x2 (front_to_back, shoot_to_goal, side_to_side,
square), free-run, same harness/metric as the other figures.

SELECTION (declared in the caption): per label, the window that MAXIMISES the
twin margin over the BEST competitor, ``min(e_ideal, e_rsim) - e_twin`` at
h = 1.5 s. A per-label BEST CASE (author's request) — unlike
``fig_trajectory_holdout`` which picks the MEDIAN window.

CAVEAT: the frozen hold-out has 1 front_to_back, 4 side_to_side and 5
shoot_to_goal events and NO ``square``; the square panel uses up to three
events OUTSIDE the hold-out, marked in the panel and in the report. rSim for
hold-out events comes from the persisted cache; for the square candidates it
is simulated (``RSimReplay``, needs robosim). With ``allow_missing_rsim=True``
and no robosim, the square panel drops the rSim curve and its margin is
``e_ideal - e_twin`` (declared in the report).

Legacy: scripts/fig_trajectory_by_label.py -> results/figs/trajectory_by_label_en.png,
results/trajectory_by_label_20260811_0238.md.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

from dtssl.analysis import common as C
from dtssl.models import AnalyticFOPDTPlant, IdealKinematicPlant

NAME = "fig_trajectory_by_label"
KIND = "fig"
CLAIM = "Trajectory overlay by label, best-case window per label (declared in caption)"
REQUIRES = ("data", "rsim_cache")
OPTIONAL = ("rsim",)      # robosim only for the square (non hold-out) panel; see allow_missing_rsim
LABELS = ("front_to_back", "shoot_to_goal", "side_to_side", "square")
H_SHOW = 90
N_SQUARE = 3


def _err(w):
    return float(np.hypot(*(w.pose_sim[H_SHOW][:2] - w.pose_real[H_SHOW][:2])))


def compute(ctx: C.Ctx, allow_missing_rsim: bool = False, n_square: int = N_SQUARE) -> dict:
    P, H = ctx.params, ctx.horizons
    ho, _ = ctx.holdout()
    rs_cache = C.load_rsim_cache(ctx, n_expected=len(ho))
    have_rsim = importlib.util.find_spec("robosim") is not None
    if not have_rsim and not allow_missing_rsim:
        raise ImportError("robosim is required for the square panel (pip install dtssl[rsim]); "
                          "pass allow_missing_rsim=True to draw it without the rSim curve")

    cands = {L: [] for L in LABELS}
    for i, s in enumerate(ho):
        if s.meta["label"] in cands:
            cands[s.meta["label"]].append(("holdout", i, s.meta["event"], s))
    for ev in C.list_events(ctx.splits_dir, "square")[:n_square]:
        cands["square"].append(("extra", None, ev, ctx.segment("square", ev)))

    def roll_rsim(seg):
        from dtssl.analysis.eval_twin_vs_rsim import _silence_engine_stdout
        from dtssl.models.rsim import RSimReplay
        with _silence_engine_stdout():
            return C.ros([seg], lambda: RSimReplay(), horizons=H)[0]

    picked = {}
    for L in LABELS:
        best = None
        for kind, hidx, ev, seg in cands[L]:
            tw = C.ros([seg], lambda: AnalyticFOPDTPlant(P), horizons=H)[0]
            idl = C.ros([seg], lambda: IdealKinematicPlant(), horizons=H)[0]
            if kind == "holdout":
                rsr = rs_cache[hidx]
            elif have_rsim:
                rsr = roll_rsim(seg)
            else:
                rsr = None
            n = min(len(tw.windows), len(idl.windows), len(rsr.windows) if rsr else len(tw.windows))
            for wi in range(n):
                wa, wb = tw.windows[wi], idl.windows[wi]
                wc = rsr.windows[wi] if rsr else None
                shapes = [wa.pose_sim.shape[0], wb.pose_sim.shape[0]] + ([wc.pose_sim.shape[0]] if wc else [])
                if min(shapes) <= H_SHOW or getattr(wa, "idle", False):
                    continue
                et, ei = _err(wa), _err(wb)
                er = _err(wc) if wc else float("nan")
                m = (min(ei, er) if wc else ei) - et
                if best is None or m > best["m"]:
                    best = dict(m=m, kind=kind, event=ev, wi=wi, e_twin=et, e_ideal=ei, e_rsim=er,
                                wa=wa, wb=wb, wc=wc)
        picked[L] = best
    return dict(picked=picked, have_rsim=have_rsim)


def figure(ctx: C.Ctx, picked: dict, name: str = "trajectory_by_label_en.png") -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def anch(Pz):
        return Pz[:, 0] - Pz[0, 0], Pz[:, 1] - Pz[0, 1]

    fig, axes = plt.subplots(2, 2, figsize=(7.16, 4.6))
    for ax, L in zip(axes.ravel(), LABELS):
        b = picked[L]
        if b is None:
            ax.axis("off"); ax.set_title(f"{L}: no candidate", fontsize=7.2)
            continue
        real = b["wa"].pose_real
        series = [(real, "k-", "measured", 1.9), (b["wa"].pose_sim, "r--", "twin (FOPDT)", 1.6),
                  (b["wb"].pose_sim, "-.", "ideal kinematics", 1.3)]
        if b["wc"] is not None:
            series.append((b["wc"].pose_sim, ":", "rSim (ODE)", 1.5))
        for Pz, st, lab, lw_ in series:
            x, y = anch(np.asarray(Pz)); ax.plot(x, y, st, lw=lw_, label=lab)
        x, y = anch(real); ax.plot(x[0], y[0], "ko", ms=4)
        extra = "" if b["kind"] == "holdout" else "  [not hold-out]"
        rs_txt = f"rSim {b['e_rsim']:.3f} m" if b["wc"] is not None else "rSim n/a"
        ax.set_title(f"{b['event']}{extra}\ntwin {b['e_twin']:.3f} m  |  ideal {b['e_ideal']:.3f} m  |  {rs_txt}",
                     fontsize=7.2, linespacing=1.5)
        ax.set_xlabel("x displacement from anchor (m)", fontsize=7)
        ax.set_ylabel("y displacement (m)", fontsize=7)
        ax.tick_params(labelsize=6.5); ax.grid(alpha=.3, lw=.4); ax.axis("equal")
    axes.ravel()[0].legend(fontsize=6.2, loc="best", framealpha=.9)
    plt.tight_layout(pad=0.4, w_pad=1.4, h_pad=1.3)
    o = ctx.figs / name
    plt.savefig(o, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return o


def render(ctx: C.Ctx, picked: dict, have_rsim: bool) -> list[str]:
    L = C.result_header("Trajectory overlay by label", ctx, generator=f"dtssl.analysis.{NAME}")
    L += ["Window selection: per label, argmax( min(e_ideal, e_rsim) - e_twin ) at h = 1.5 s,",
          "i.e. the window with the largest twin margin over the BEST competing plant.",
          "This is a per-label BEST CASE, not the median window. Declared in the caption.", "",
          "| label | event | window | in hold-out | twin (m) | ideal (m) | rSim (m) |",
          "|---|---|---|---|---|---|---|"]
    for lab in LABELS:
        b = picked[lab]
        if b is None:
            L.append(f"| {lab} | - | - | - | - | - | - |"); continue
        rs = f"{b['e_rsim']:.4f}" if b["wc"] is not None else "n/a"
        L.append(f"| {lab} | `{b['event']}` | {b['wi']} | {'yes' if b['kind'] == 'holdout' else '**no**'} "
                 f"| {b['e_twin']:.4f} | {b['e_ideal']:.4f} | {rs} |")
    L += ["", "The frozen hold-out (config/holdout_events.json) contains no `square` event",
          "(1 front_to_back, 4 side_to_side, 5 shoot_to_goal), so the square panel is drawn",
          "from an event outside the hold-out and is marked as such in the figure."]
    if not have_rsim:
        L += ["", "NOTE: robosim unavailable in this run — the square panel has no rSim curve and its",
              "margin is e_ideal - e_twin (hold-out panels use the persisted rSim cache)."]
    return L


def run(root: Path | None = None, out: Path | None = None, *, allow_missing_rsim: bool = False,
        latex_copy: bool = False, quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out)
    r = compute(ctx, allow_missing_rsim=allow_missing_rsim)
    picked = r["picked"]
    if not quiet:
        for lab in LABELS:
            b = picked[lab]
            if b is None:
                print(f"{lab:15s} (no candidate)"); continue
            print(f"{lab:15s} {b['event']:22s} win={b['wi']:3d} twin={b['e_twin']:.4f} "
                  f"ideal={b['e_ideal']:.4f} rSim={b['e_rsim']:.4f} margin={b['m']:+.4f} [{b['kind']}]", flush=True)
    png = figure(ctx, picked)
    copied = C.copy_figure(png, ctx, png.name, latex_copy)
    L = render(ctx, picked, r["have_rsim"])
    md = ctx.write_text("trajectory_by_label", L, trailing_newline=True)
    if not quiet:
        print("\n".join(L[6:]))
        print(f"\nfigura: {png}\nrelatorio: {md}")
    return dict(path=png, report=md, latex=copied,
                picked={k: ({kk: v[kk] for kk in ("kind", "event", "wi", "e_twin", "e_ideal", "e_rsim", "m")}
                            if v else None) for k, v in picked.items()})


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
