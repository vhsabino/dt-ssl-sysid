"""Visual SPECIFICATION of the main-result figure (not the figure itself).

A diagram with six numbered markers explaining what each element of Fig. 2 must
contain and why (three curves incl. rSim as context, rSim crossing the ideal at
h ~ 1.0 s, h_ref marker, English axes, all ten events paired, grey pairing
lines). Numbers are illustrative sketches taken from
results/epos_eang_three_models_*.md and clustered_stats_*.md; the real figure
is produced by ``fig_main_result``. Text is in PT-BR (internal review aid).

Legacy: scripts/fig_spec_main_result.py -> results/figs/SPEC_main_result.png.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from dtssl.analysis import common as C

NAME = "fig_spec_main_result"
KIND = "fig"
CLAIM = "Visual contract of Fig. 2 (internal aid, not in the paper)"
REQUIRES = ()

IDEAL = [.0264, .0501, .1005, .1516, .2165, .2910]
RSIM = [.0573, .0924, .1293, .1744, .2128, .2891]
MODEL = [.0079, .0178, .0388, .0617, .0920, .1193]
PER_EVENT_IDEAL = [.162, .138, .129, .121, .114, .108, .054, .053, .052, .051]
PER_EVENT_MODEL = [.058, .056, .054, .045, .042, .040, .023, .021, .019, .018]
REQS = [("1", "3 curvas obrigatórias:\nideal, rSim, modelo.\nrSim é contexto, não\ncomparador primário."),
        ("2", "rSim cruza a ideal em\nh≈1,0 s — NÃO esconder.\nÉ o que sustenta a\nressalva do artigo."),
        ("3", "Marcar h_ref = 0,4 s,\nonde os números do\nabstract são citados."),
        ("4", "Eixos em inglês, fonte\n≥7 pt em coluna única.\nSem título interno."),
        ("5", "Os 10 eventos, um par\ncada. Mostra que a\nvitória é 10/10, não\numa média."),
        ("6", "Linhas cinzas ligam o\nmesmo evento: deixa o\npareamento visível.")]


def figure(ctx: C.Ctx, name: str = "SPEC_main_result.png") -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.set_xlim(0, 100); ax.set_ylim(0, 62); ax.axis("off")

    def tag(x, y, n):
        ax.add_patch(plt.Circle((x, y), 1.5, fc="#d62728", ec="none", zorder=5))
        ax.text(x, y, str(n), ha="center", va="center", fontsize=7.5, color="w", fontweight="bold", zorder=6)

    ax.text(50, 59.5, "Fig. 2 — ESPECIFICAÇÃO  (o que a figura do resultado principal precisa conter)",
            ha="center", fontsize=11, fontweight="bold", color="#1a237e")
    ax.text(50, 56.3, "Ajuste qualquer item e me diga o número do marcador", ha="center", fontsize=8,
            color="#555", style="italic")
    # panel A
    ax.add_patch(FancyBboxPatch((3, 8), 44, 45, boxstyle="round,pad=0.6", fc="white", ec="#90a4ae", lw=1.4))
    ax.text(25, 50.5, "PAINEL (a) — erro × horizonte", ha="center", fontsize=9, fontweight="bold")
    ax.plot([10, 43], [13, 13], color="#37474f", lw=1.2); ax.plot([10, 10], [13, 46], color="#37474f", lw=1.2)
    h = np.array([.1, .2, .4, .7, 1., 1.5]); xs = 10 + (h / 1.5) * 32

    def curve(v, c, ls, mk):
        ys = 13 + np.array(v) / 0.30 * 31
        ax.plot(xs, ys, ls, color=c, marker=mk, ms=3.5, lw=1.5)

    curve(IDEAL, "#1f77b4", "-", "o"); curve(RSIM, "#ff7f0e", ":", "s"); curve(MODEL, "#d62728", "--", "^")
    xr = 10 + (0.4 / 1.5) * 32
    ax.plot([xr] * 2, [13, 46], color="#bbb", ls=":", lw=1)
    ax.text(xr + 0.6, 14.5, r"$h_{ref}$", fontsize=7, color="#777")
    ax.text(26, 10.6, "horizon (s)", ha="center", fontsize=7.5)
    ax.text(7.2, 30, "median $e_{pos}$ (m)", rotation=90, va="center", fontsize=7.5)
    tag(12, 44, 1); tag(38, 41, 2); tag(xr, 17, 3); tag(41, 20, 4)
    # panel B
    ax.add_patch(FancyBboxPatch((51, 8), 25, 45, boxstyle="round,pad=0.6", fc="white", ec="#90a4ae", lw=1.4))
    ax.text(63.5, 50.5, "PAINEL (b) — por evento", ha="center", fontsize=9, fontweight="bold")
    ax.plot([57, 57], [14, 46], color="#37474f", lw=1.2)
    for a_, b_ in zip(PER_EVENT_IDEAL, PER_EVENT_MODEL):
        ya = 14 + a_ / 0.18 * 30; yb = 14 + b_ / 0.18 * 30
        ax.plot([61, 71], [ya, yb], color="#ccc", lw=0.9)
        ax.plot(61, ya, "o", color="#1f77b4", ms=4); ax.plot(71, yb, "^", color="#d62728", ms=4)
    ax.text(61, 11.7, "ideal", ha="center", fontsize=7.5); ax.text(71, 11.7, "model", ha="center", fontsize=7.5)
    ax.text(54.3, 30, "per-event $e_{pos}$ (m)", rotation=90, va="center", fontsize=7.5)
    tag(66, 44, 5); tag(66, 17.5, 6)
    # marker legend
    ax.add_patch(FancyBboxPatch((79, 8), 18, 45, boxstyle="round,pad=0.6", fc="#fffde7", ec="#f9a825", lw=1.2))
    ax.text(88, 50.5, "REQUISITOS", ha="center", fontsize=9, fontweight="bold", color="#e65100")
    y = 46.5
    for n, t in REQS:
        tag(81.2, y, n); ax.text(83.4, y, t, fontsize=6.6, va="center", color="#333")
        y -= 6.9
    ax.text(50, 4.6, "Fonte dos números: results/epos_eang_three_models_*.md e clustered_stats_*.md  ·  "
            "gerador: dtssl.analysis.fig_main_result", ha="center", fontsize=6.8, color="#666")
    ax.text(50, 2.2, "NÃO é a figura final — é o contrato visual dela. A figura real está em "
            "latex/figures/main_result_en.png", ha="center", fontsize=7, color="#c62828", style="italic")
    plt.tight_layout()
    o = ctx.figs / name
    plt.savefig(o, dpi=190, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return o


def run(root: Path | None = None, out: Path | None = None, *, quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out)
    png = figure(ctx)
    if not quiet:
        print("spec gerado:", png)
    return dict(path=png)


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
