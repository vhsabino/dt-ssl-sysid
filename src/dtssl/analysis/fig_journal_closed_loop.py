"""Journal figure: commands the team's real strategy emits when it closes the loop on the twin (field
players of the recorded session) against the competition logs (pool of 46 events and the game label
``shoot_to_goal``): |v_cmd| and |w_cmd| distributions, with the body-rate equivalent of the firmware dead
zone on the yaw panel.

``source="artifact"`` (default, no dataset): the quantiles 10, 25, 50, 75, 90 and 99 % stored in
results/closed_loop_stats_20260907_2137.json (C4), drawn as points of the empirical CDF.
``source="data"``: the exact empirical CDFs, rebuilt with the loaders of ``closed_loop_stats`` from
``results/sessao_01`` and the competition splits (needs the dataset; same series as C4).
Output: results/figs/fig_journal_closed_loop_<stamp>.{pdf,png} and latex_journal/figures/fig_journal_closed_loop.pdf.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from dtssl.analysis import common as C
from dtssl.analysis import journal_artifacts as J

NAME = "fig_journal_closed_loop"
KIND = "fig"
CLAIM = "Journal Fig.: strategy commands in closed loop on the twin vs competition logs (C4)"
REQUIRES: tuple[str, ...] = ()
QLEVELS = (10, 25, 50, 75, 90, 99)
W_DEADZONE_BODY = 0.58
SESSION_DIR = "results/sessao_01"
POOL_LABELS = ("front_to_back", "side_to_side", "shoot_to_goal", "square")
SERIES = (("field", "Strategy on the twin (field players)", "#1f77b4", "-"),
          ("pool", "Competition logs (46 events)", "#d62728", "--"),
          ("shoot_to_goal", "Competition, game label", "#2ca02c", ":"))


def data_artifact(root: Path | None = None) -> dict:
    cl = J.closed_loop(root)
    src = dict(field=cl["field"], pool=cl["pool"], shoot_to_goal=cl["per_label"]["shoot_to_goal"])
    out = {}
    for key, s in src.items():
        out[key] = dict(v=[s["v_q"][f"p{q}"] for q in QLEVELS], w=[s["w_q"][f"p{q}"] for q in QLEVELS], n=s["n"])
    return dict(kind="quantiles", series=out, criteria=cl["criteria"])


def data_exact(ctx: C.Ctx) -> dict:
    from dtssl.analysis import closed_loop_stats as S

    sess = S.load_session(ctx.root / SESSION_DIR, ctx.ts)
    per_robot = {rid: S.series_stats([s], ctx.ts) for rid, s in sess["series"].items()}
    keeper = max(per_robot, key=lambda k: per_robot[k]["frac_idle"])          # same rule as C4
    field = [s for rid, s in sess["series"].items() if rid != keeper]
    comp = S.load_competition(ctx, POOL_LABELS, ctx.ts)
    pool = [s for lab in POOL_LABELS if lab in comp for s in comp[lab]["series"]]
    stg = comp["shoot_to_goal"]["series"]
    out = {}
    for key, ser in (("field", field), ("pool", pool), ("shoot_to_goal", stg)):
        out[key] = dict(v=np.concatenate([s.v for s in ser]), w=np.concatenate([np.abs(s.w) for s in ser]),
                        n=int(sum(s.n for s in ser)))
    return dict(kind="ecdf", series=out)


def make_figure(d: dict):
    J.figure_style()
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(190 * J.MM, 58 * J.MM))
    for ax, key, xl, xmax in ((axes[0], "v", r"$|v_{\mathrm{cmd}}|$ (m/s)", 3.2),
                              (axes[1], "w", r"$|\omega_{\mathrm{cmd}}|$ (rad/s)", 6.0)):
        for skey, label, color, ls in SERIES:
            s = d["series"][skey]
            if d["kind"] == "quantiles":
                ax.plot(s[key], [q / 100 for q in QLEVELS], color=color, ls=ls, marker="o", ms=2.6,
                        label=f"{label}, n = {s['n']}")
            else:
                x = np.sort(np.asarray(s[key], float))
                ax.step(x, np.arange(1, x.size + 1) / x.size, where="post", color=color, ls=ls,
                        label=f"{label}, n = {s['n']}")
        if key == "w":
            ax.axvline(W_DEADZONE_BODY, color="0.4", ls="-.", lw=0.8)
            ax.text(W_DEADZONE_BODY + 0.06, 0.04, "dead-zone equivalent\n0.58 rad/s", fontsize=6.5, color="0.3")
        ax.set_xlim(0.0, xmax)
        ax.set_ylim(0.0, 1.0)
        ax.set_xlabel(xl)
        ax.set_ylabel("cumulative fraction" + (" (quantiles)" if d["kind"] == "quantiles" else ""))
        ax.grid(alpha=0.35)
    axes[0].legend(loc="lower right", frameon=False)
    fig.tight_layout(w_pad=1.5)
    return fig


def run(root: Path | None = None, out: Path | None = None, *, source: str = "artifact", latex_copy: bool = True,
        quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out)
    if source == "artifact":
        d = data_artifact(ctx.root)
    elif source == "data":
        d = data_exact(ctx)
    else:
        raise ValueError("source must be 'artifact' or 'data'")
    fig = make_figure(d)
    paths = J.save_figure(fig, ctx, NAME, latex_copy=latex_copy)
    import matplotlib.pyplot as plt

    plt.close(fig)
    if not quiet:
        print(f"figura: {paths['pdf']} ({d['kind']})")
    return dict(path=paths["pdf"], paths=paths, kind=d["kind"])


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
