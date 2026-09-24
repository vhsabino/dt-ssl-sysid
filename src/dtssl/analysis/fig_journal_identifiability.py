"""Journal figure: yaw gain identified from synthetic logs with a known generator, by excitation regime
(C1 linear twin; C1b MuJoCo route b with and without the identified delay), against the real robot's
closed-loop and dedicated open-loop estimates.

Numbers only from the artefacts (``journal_artifacts``): results/identifiability_insilico_20260907_1552.json
(C1), results/identifiability_insilico_mujoco-rollers_v2_20260907_2048.json and
results/identifiability_insilico_mujoco-rollers-delay_v2_20260907_2044.json (C1b v2), the real-robot lines
from results/r3_closedloop_omega_fit_20260810_1036.md (closed loop) and config/twin_params.json
(dedicated open loop). Output: results/figs/fig_journal_identifiability_<stamp>.{pdf,png} and
latex_journal/figures/fig_journal_identifiability.pdf.
"""
from __future__ import annotations

from pathlib import Path

from dtssl.analysis import common as C
from dtssl.analysis import journal_artifacts as J

NAME = "fig_journal_identifiability"
KIND = "fig"
CLAIM = "Journal Fig.: yaw-gain bias follows the excitation regime and translation (C1/C1b)"
REQUIRES: tuple[str, ...] = ()
REGIMES = (("R1", "Competition\ncommands"), ("R1-wonly", "Same, translation\nzeroed"),
           ("R2-rotate", "Dedicated\nrotation"), ("R2-square", "Square\nmaneuvers"))
GENERATORS = (("linear twin", "Linear FOPDT twin", "#4d4d4d"), ("route b", "MuJoCo rollers, untuned", "#1f77b4"),
              ("route b + delay", "MuJoCo rollers + identified delay", "#d62728"))
CELLS = ((("none", "off"), "idealized", "o", True), (("vision", "on"), "vision noise + dead zone", "s", False))


def data(root: Path | None = None) -> dict:
    y = J.yaw_insilico(root)
    r3 = J.r3(root)
    ctx = C.make_context(root)
    return dict(cells=y, closed_loop_K=r3["closed_loop"]["K"], open_loop_K=float(ctx.params["w"].K))


def make_figure(d: dict):
    J.figure_style()
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(140 * J.MM, 62 * J.MM))
    width = 0.13
    offsets = {}
    k = 0
    for gi, _ in enumerate(GENERATORS):
        for ci, _ in enumerate(CELLS):
            offsets[(gi, ci)] = (k - 2.5) * width
            k += 1
    for gi, (gkey, glabel, color) in enumerate(GENERATORS):
        for ci, (cell, clabel, marker, filled) in enumerate(CELLS):
            xs, ys, lo, hi = [], [], [], []
            for ri, (regime, _) in enumerate(REGIMES):
                c = d["cells"][gkey].get((regime, *cell))
                if c is None:
                    continue
                xs.append(ri + offsets[(gi, ci)])
                ys.append(c["med"])
                lo.append(c["med"] - c["p25"])
                hi.append(c["p75"] - c["med"])
            ax.errorbar(xs, ys, yerr=[lo, hi], fmt=marker, ms=3.6, color=color, mfc=color if filled else "white",
                        mew=0.9, elinewidth=0.8, capsize=1.5, label=f"{glabel}, {clabel}", zorder=3)
    ax.axhline(d["closed_loop_K"], color="0.25", ls=":", lw=1.0, zorder=1)
    ax.axhline(d["open_loop_K"], color="0.25", ls="--", lw=0.9, zorder=1)
    ax.text(-0.5, d["closed_loop_K"], f"real robot, closed-loop logs ({d['closed_loop_K']:.3f})", va="bottom",
            ha="left", fontsize=6.5, color="0.25")
    ax.text(-0.5, d["open_loop_K"] + 0.004, f"real robot, dedicated collection ({d['open_loop_K']:.3f})",
            va="bottom", ha="left", fontsize=6.5, color="0.25")
    ax.set_xticks(range(len(REGIMES)))
    ax.set_xticklabels([lab for _, lab in REGIMES])
    ax.set_xlim(-0.55, len(REGIMES) - 0.35)
    ax.set_ylabel(r"identified yaw gain $K_\omega$")
    ax.grid(axis="y", alpha=0.35)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=3, frameon=False, handletextpad=0.3,
              columnspacing=1.0)
    return fig


def run(root: Path | None = None, out: Path | None = None, *, latex_copy: bool = True, quiet: bool = False,
        **kw) -> dict:
    ctx = C.make_context(root, out)
    d = data(ctx.root)
    fig = make_figure(d)
    paths = J.save_figure(fig, ctx, NAME, latex_copy=latex_copy)
    import matplotlib.pyplot as plt

    plt.close(fig)
    if not quiet:
        print(f"figura: {paths['pdf']}")
    return dict(path=paths["pdf"], paths=paths, data=d)


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
