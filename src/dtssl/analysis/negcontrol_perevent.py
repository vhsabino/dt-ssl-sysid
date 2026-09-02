"""Negative control (joint Bayesian calibration) with PER-EVENT statistics.

Same pattern as the main result: per-event median at h_ref (0.4 s), translation
bin, n = 10 hold-out events. Three paired comparisons: per-DOF twin vs ideal,
bayesopt (theta_opt of models/sysid_bayesopt_v2_candidate.mat) vs ideal, and
per-DOF vs bayesopt.

Legacy: scripts/negcontrol_perevent.py -> results/negcontrol_perevent_20260810_1035.md.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

from dtssl.analysis import common as C
from dtssl.models import AnalyticFOPDTPlant, IdealKinematicPlant

NAME = "negcontrol_perevent"
KIND = "analysis"
CLAIM = "Negative control (joint Bayesian calibration), per event (C3 of review V2)"
REQUIRES = ("data", "mat")
BAYESOPT_MAT = "sysid_bayesopt_v2_candidate.mat"


def _rep(x, y, la, lb) -> dict:
    d = y - x
    _, p = wilcoxon(x, y, alternative="less")
    pos, neg = int((d > 0).sum()), int((d < 0).sum())
    return dict(a=la, b=lb, med_a=float(np.median(x)), med_b=float(np.median(y)),
                gap=float(np.median(d)), p=float(p), wins=pos, losses=neg, n=int(len(d)),
                rb=(pos - neg) / len(d))


def compute(ctx: C.Ctx, mat: str = BAYESOPT_MAT, h_ref: int = 24) -> dict:
    segs, _ = ctx.holdout()
    P, H = ctx.params, ctx.horizons
    BO = C.load_theta_mat(ctx.models_dir / mat, "theta_opt")
    k = H.index(h_ref)
    tw = C.ros(segs, lambda: AnalyticFOPDTPlant(P), horizons=H)
    bo = C.ros(segs, lambda: AnalyticFOPDTPlant(BO), horizons=H)
    idl = C.ros(segs, lambda: IdealKinematicPlant(), horizons=H)

    def perev(A, B):
        T = C.paired_table(ctx, A, B)
        a, b, _ = C.per_event_medians(T, k)
        return a, b

    tw_e, bo_e = perev(tw, bo)
    _, id_e = perev(tw, idl)
    r1 = _rep(tw_e, bo_e, "per-DOF", "bayesopt")
    r2 = _rep(bo_e, id_e, "bayesopt", "ideal")
    r3 = _rep(tw_e, id_e, "per-DOF", "ideal")
    return dict(theta_bo=BO, r1=r1, r2=r2, r3=r3, h_ref_s=h_ref * ctx.ts)


def render(ctx: C.Ctx, r: dict) -> list[str]:
    r1, r2, r3 = r["r1"], r["r2"], r["r3"]
    L = C.result_header("Controle negativo (bayesopt) com estatistica POR EVENTO", ctx,
                        generator=f"dtssl.analysis.{NAME}",
                        extra=f"theta bayesopt ({C.theta_summary(r['theta_bo'])})")
    L += [f"Mesmo padrao do resultado principal: mediana por evento, n={r3['n']}, h_ref={r['h_ref_s']:.1f} s,",
          "bin translacional. Substitui os numeros por janela que nao eram comparaveis.", "",
          "| comparacao | mediana A | mediana B | gap mediano | vitorias A | Wilcoxon p | rank-biserial |",
          "|---|---|---|---|---|---|---|"]
    for x in (r3, r2, r1):
        L.append(f"| {x['a']} vs {x['b']} | {x['med_a']:.4f} | {x['med_b']:.4f} | {x['gap']:+.4f} | "
                 f"{x['wins']}/{x['n']} | {x['p']:.4g} | {x['rb']:+.3f} |")
    L += ["", "## Leitura", "",
          f"- per-DOF vs ideal: gap {r3['gap']:+.4f} m, {r3['wins']}/{r3['n']}, p={r3['p']:.3g} -> resultado principal, robusto.",
          f"- bayesopt vs ideal: gap {r2['gap']:+.4f} m, {r2['wins']}/{r2['n']}, p={r2['p']:.3g}.",
          f"- **per-DOF vs bayesopt: gap {r1['gap']:+.4f} m, {r1['wins']}/{r1['n']} eventos, p={r1['p']:.3g}, "
          f"efeito {r1['rb']:+.3f}**.", "",
          "Se o gate do artigo (efeito >= 0.2 E p < 0.05) for aplicado a per-DOF vs bayesopt,",
          "o veredito e o que aparece na ultima linha -- e e ELE que deve ser reportado, nao",
          "o p por janela de 0.040 usado antes (objecao C3 da revisao V2)."]
    return L


def run(root: Path | None = None, out: Path | None = None, *, mat: str = BAYESOPT_MAT,
        h_ref: int = 24, quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out)
    r = compute(ctx, mat=mat, h_ref=h_ref)
    L = render(ctx, r)
    p = ctx.write_text(NAME, L)
    if not quiet:
        print("theta bayesopt:", {d: (round(v.K, 4), round(v.tau, 4), round(v.Td, 4))
                                  for d, v in r["theta_bo"].items()})
        print("\n".join(L)); print(f"\nartefato: {p}")
    r["path"] = p
    return r


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
