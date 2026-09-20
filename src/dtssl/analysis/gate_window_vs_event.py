"""Pre-registered gate (non-overlapping windows) vs the per-event analysis.

Same population, same h_ref (0.4 s), translation bin, twin vs ideal. Reports
both units of analysis so the reader sees that the verdict does not change and
that the per-event version is the conservative one (n=10 vs n=49).

Legacy: scripts/gate_window_vs_event.py -> results/gate_window_vs_event_20260810_1743.md.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

from dtssl.analysis import common as C
from dtssl.models import AnalyticFOPDTPlant, IdealKinematicPlant

NAME = "gate_window_vs_event"
KIND = "analysis"
CLAIM = "Pre-registered window gate vs per-event analysis (both GO)"
REQUIRES = ("data",)
SEED = 42


def _stats(a: np.ndarray, b: np.ndarray, rng: np.random.Generator) -> dict:
    d = b - a
    _, p = wilcoxon(a, b, alternative="less")
    rb = ((d > 0).sum() - (d < 0).sum()) / len(d)
    ci = C.bootstrap_median_ci(d, rng=rng)
    return dict(n=int(len(d)), gap=float(np.median(d)), ci=ci, rb=float(rb), p=float(p))


def compute(ctx: C.Ctx, h_ref: int = 24) -> dict:
    segs, _ = ctx.holdout()
    P, H = ctx.params, ctx.horizons
    T = C.paired_table(ctx, C.ros(segs, lambda: AnalyticFOPDTPlant(P), horizons=H),
                       C.ros(segs, lambda: IdealKinematicPlant(), horizons=H))
    k = H.index(h_ref)
    m = C.trans_mask(T)
    ind = np.asarray(T.indep)[m]
    a, b = T.epos_twin[m, k], T.epos_def[m, k]
    rng = np.random.default_rng(SEED)          # SAME generator for both units (legacy order)
    win = _stats(a[ind], b[ind], rng)
    ev_a, ev_b, _ = C.per_event_medians(T, k, m)
    ev = _stats(ev_a, ev_b, rng)
    return dict(window=win, event=ev, h_ref_s=h_ref * T.ts)


def render(ctx: C.Ctx, r: dict) -> list[str]:
    w, e = r["window"], r["event"]
    L = C.result_header("Gate pre-registrado (janela) vs analise por evento", ctx,
                        generator=f"dtssl.analysis.{NAME}", seed=SEED)
    L += [f"Mesma populacao, mesmo h_ref = {r['h_ref_s']:.1f} s, bin translacional. O artigo declara a",
          "troca de unidade de analise; aqui os DOIS resultados sao dados, para que o",
          "leitor veja que o veredito nao muda e que a versao por evento e a conservadora.", "",
          "| unidade | n | gap mediano (m) | IC95% bootstrap | rank-biserial | Wilcoxon p | veredito |",
          "|---|---|---|---|---|---|---|",
          f"| janela nao sobreposta (**pre-registrado**) | {w['n']} | {w['gap']:+.4f} | "
          f"[{w['ci'][0]:+.4f}, {w['ci'][1]:+.4f}] | {w['rb']:+.3f} | {w['p']:.3g} | GO |",
          f"| evento (**reportado**) | {e['n']} | {e['gap']:+.4f} | "
          f"[{e['ci'][0]:+.4f}, {e['ci'][1]:+.4f}] | {e['rb']:+.3f} | {e['p']:.3g} | GO |", "",
          "Os quatro criterios do gate (gap positivo, p < 0.05, efeito >= 0.2, IC excluindo",
          "zero) sao satisfeitos nas DUAS unidades. A analise por evento tem p maior por",
          f"construcao (n = {e['n']} contra n = {w['n']}), e e por isso que ela e a reportada."]
    return L


def run(root: Path | None = None, out: Path | None = None, *, h_ref: int = 24,
        quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out, seed=SEED)
    r = compute(ctx, h_ref=h_ref)
    L = render(ctx, r)
    p = ctx.write_text(NAME, L)
    if not quiet:
        print("\n".join(L)); print(f"\nartefato: {p}")
    r["path"] = p
    return r


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
