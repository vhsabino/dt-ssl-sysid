"""Twin-vs-rSim fidelity figure in ENGLISH, e_pos panel only (transcribed numbers).

The original figure (results/figs/rsim_twin_all_20260617_0030.png) had Portuguese
axis labels, an internal pipeline marker in the title and an e_ang panel produced
with the yaw PLACEHOLDER (before omega was promoted, 2026-07-24). This rebuilds
ONLY the e_pos panel, whose numbers are tabulated in
results/eval_twin_vs_rsim_modeA_20260617_0030.md ("trans-dominado").

NO data are recomputed: medians and bootstrap CIs are transcribed verbatim from
that report (``ROWS``). To regenerate from data use ``eval_twin_vs_rsim`` (needs
robosim) or ``epos_eang_three_models`` (cache).

Legacy: scripts/fig_twin_vs_rsim_epos_en.py -> results/figs/twin_vs_rsim_epos_en_<stamp>.{png,pdf}.
"""
from __future__ import annotations

from pathlib import Path

from dtssl.analysis import common as C

NAME = "fig_twin_vs_rsim_epos_en"
KIND = "fig"
CLAIM = "Twin vs rSim e_pos panel (transcribed from eval_twin_vs_rsim_modeA_20260617_0030.md)"
REQUIRES = ()

# --- Source: results/eval_twin_vs_rsim_modeA_20260617_0030.md, "trans-dominado"
# h (s), twin e_pos (m), rSim e_pos (m), gap (m), gap CI95 lo, gap CI95 hi
ROWS = [
    (0.10, 0.0077, 0.0572, 0.0495, 0.0451, 0.0524),
    (0.20, 0.0177, 0.0935, 0.0758, 0.0665, 0.0811),
    (0.40, 0.0382, 0.1312, 0.0930, 0.0790, 0.1029),
    (0.70, 0.0644, 0.1731, 0.1087, 0.0877, 0.1341),
    (1.00, 0.0919, 0.2144, 0.1225, 0.1045, 0.1452),
    (1.50, 0.1229, 0.2927, 0.1699, 0.1188, 0.2101),
]
N_TOTAL, N_INDEP, H_REF = 264, 49, 0.40


def figure(ctx: C.Ctx, rows=ROWS) -> tuple[Path, Path]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    h = [r[0] for r in rows]; twin = [r[1] for r in rows]; rsim = [r[2] for r in rows]
    gap = [r[3] for r in rows]; lo = [r[3] - r[4] for r in rows]; hi = [r[5] - r[3] for r in rows]

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(3.4, 1.85), dpi=400, gridspec_kw={"wspace": 0.42})
    ax.plot(h, twin, "-o", color="black", lw=1.2, ms=3.2, label="twin (FOPDT)")
    ax.plot(h, rsim, "--s", color="0.45", lw=1.2, ms=3.2, label="rSim (ODE)")
    ax.axvline(H_REF, color="0.75", lw=0.7, ls=":", zorder=0)
    ax.set_xlabel("horizon $h$ (s)", fontsize=6)
    ax.set_ylabel("median $e_{\\mathrm{pos}}$ (m)", fontsize=6)
    ax.tick_params(labelsize=5.5, length=2)
    ax.legend(fontsize=5, frameon=False, loc="upper left")
    ax.grid(alpha=0.25, lw=0.4)
    ax2.errorbar(h, gap, yerr=[lo, hi], fmt="-o", color="black", lw=1.2, ms=3.2, capsize=2, elinewidth=0.8)
    ax2.axhline(0.0, color="0.6", lw=0.7)
    ax2.axvline(H_REF, color="0.75", lw=0.7, ls=":", zorder=0)
    ax2.set_xlabel("horizon $h$ (s)", fontsize=6)
    ax2.set_ylabel("gap (m), rSim $-$ twin", fontsize=6)
    ax2.tick_params(labelsize=5.5, length=2)
    ax2.grid(alpha=0.25, lw=0.4)
    for a in (ax, ax2):
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
    base = ctx.figs / f"twin_vs_rsim_epos_en_{ctx.stamp}"
    png, pdf = Path(f"{base}.png"), Path(f"{base}.pdf")
    fig.savefig(png, bbox_inches="tight"); fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    return png, pdf


def run(root: Path | None = None, out: Path | None = None, *, latex_copy: bool = False,
        quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out, stamp_fmt=C.STAMP_FMT_S)
    png, pdf = figure(ctx)
    copied = C.copy_figure(png, ctx, "twin_vs_rsim_epos_en.png", latex_copy)
    if not quiet:
        print(f"wrote {png}\nwrote {pdf}")
        if copied:
            print(f"wrote {copied}")
        print(f"N_total={N_TOTAL} N_indep={N_INDEP} h_ref={H_REF}")
    return dict(path=png, pdf=pdf, latex=copied)


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
