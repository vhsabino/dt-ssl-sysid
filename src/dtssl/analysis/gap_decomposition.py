"""Cumulative gap decomposition: ideal -> +K -> +tau -> +Td (one fixed order).

Median e_pos (translation bin) per horizon for the four nested variants and the
incremental reduction between consecutive steps. NOTE: this is the ORDER-DEPENDENT
decomposition that review V2 criticised; the order-free version is
``ablation_orderfree``. Kept because results/gap_decomposition_20260809_2308.md
was cited before that correction.

Legacy: scripts/gap_decomposition.py -> results/gap_decomposition_20260809_2308.md.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from dtssl.analysis import common as C
from dtssl.eval.metrics import evaluate
from dtssl.models import AnalyticFOPDTPlant

NAME = "gap_decomposition"
KIND = "analysis"
CLAIM = "Cumulative (order-dependent) gap decomposition ideal -> K -> tau -> Td (superseded by ablation_orderfree)"
REQUIRES = ("data",)


def compute(ctx: C.Ctx) -> dict:
    segs, _ = ctx.holdout()
    P, H = ctx.params, ctx.horizons
    VAR = [("ideal (K=1, tau=0, Td=0)", C.variant_params(P, False, False, False)),
           ("+ gain K", C.variant_params(P, True, False, False)),
           ("+ time constant tau", C.variant_params(P, True, True, False)),
           ("full twin (+ dead time)", C.variant_params(P, True, True, True))]
    base = C.ros(segs, lambda: AnalyticFOPDTPlant(VAR[0][1]), horizons=H)
    rows = []
    for name, par in VAR:
        r = evaluate(C.ros(segs, lambda par=par: AnalyticFOPDTPlant(par), horizons=H), base,
                     params=P, mcfg=ctx.mcfg)["scopes"]["trans"]
        rows.append((name, np.asarray(r["epos_twin_med"], float)))
    return dict(rows=rows, horizons=H, ts=ctx.ts)


def render(ctx: C.Ctx, r: dict) -> list[str]:
    H, rows = r["horizons"], r["rows"]
    hs = " | ".join(f"h={h * r['ts']:.2f}s" for h in H)
    L = C.result_header("Decomposicao do gap", ctx, generator=f"dtssl.analysis.{NAME}")
    L += ["Mediana de e_pos (m) no bin translacional, mesmas janelas/horizontes.", "",
          "| variante | " + hs + " |", "|---|" + "---|" * len(H)]
    for n, m in rows:
        L.append(f"| {n} | " + " | ".join(f"{v:.4f}" for v in m) + " |")
    L += ["", "## Contribuicao incremental (reducao de e_pos vs a variante anterior)",
          "| passo | " + hs + " |", "|---|" + "---|" * len(H)]
    for i in range(1, len(rows)):
        d = rows[i - 1][1] - rows[i][1]
        L.append(f"| {rows[i][0]} | " + " | ".join(f"{v:+.4f}" for v in d) + " |")
    return L


def run(root: Path | None = None, out: Path | None = None, *, quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out)
    r = compute(ctx)
    L = render(ctx, r)
    p = ctx.write_text(NAME, L)
    if not quiet:
        print("\n".join(L)); print(f"\nartefato: {p.name}")
    r["path"] = p
    return r


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
