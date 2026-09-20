"""Per-EVENT statistics of the main result (paper Fig. 2b; 10/10 events, 73.5 s).

Unit of analysis = hold-out event (n=10) instead of window (n=49): per-event
median of e_pos at h_ref (0.4 s) in the translation bin, twin (FOPDT) vs ideal
kinematics on the same windows; paired one-sided Wilcoxon, bootstrap CI of the
median gap (10000 draws, seed 42) and paired rank-biserial.

Legacy: scripts/clustered_stats.py -> results/clustered_stats_20260809_2309.md.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.stats import wilcoxon

from dtssl.analysis import common as C
from dtssl.models import AnalyticFOPDTPlant, IdealKinematicPlant
from dtssl.sim.rollout import DEFAULT_HMAX

NAME = "clustered_stats"
KIND = "analysis"
CLAIM = "Per-event statistics, 10/10 events, 73.5 s scored (Fig. 2b)"
REQUIRES = ("data",)
SEED = 42


def compute(ctx: C.Ctx, h_ref: int = 24) -> dict:
    segs, _ = ctx.holdout()
    P, H = ctx.params, ctx.horizons
    T = C.paired_table(ctx, C.ros(segs, lambda: AnalyticFOPDTPlant(P), horizons=H),
                       C.ros(segs, lambda: IdealKinematicPlant(), horizons=H))
    k = H.index(h_ref)
    m = C.trans_mask(T)
    sid = np.asarray(T.seg_id)[m]
    et, ed = T.epos_twin[m, k], T.epos_def[m, k]
    indep = np.asarray(T.indep)[m]
    rows = [(int(s), float(np.median(et[sid == s])), float(np.median(ed[sid == s])),
             int((sid == s).sum())) for s in sorted(set(sid))]
    tw = np.array([r[1] for r in rows]); idl = np.array([r[2] for r in rows]); d = idl - tw
    _, pv = wilcoxon(tw, idl, alternative="less")
    ci = C.bootstrap_median_ci(d, seed=SEED)
    pos, neg = int((d > 0).sum()), int((d < 0).sum())
    n_indep = int(indep.sum())
    return dict(rows=rows, p=float(pv), gap=float(np.median(d)), ci=ci,
                rank_biserial=(pos - neg) / len(d), wins=pos, losses=neg,
                n_trans=int(m.sum()), n_indep=n_indep, seconds=n_indep * DEFAULT_HMAX * T.ts,
                ts=T.ts, h_ref_s=h_ref * T.ts)


def render(ctx: C.Ctx, r: dict) -> list[str]:
    L = C.result_header("Estatistica agrupada por EVENTO", ctx, generator=f"dtssl.analysis.{NAME}",
                        seed=SEED)
    L += [f"Unidade de analise = evento de hold-out. n = **{len(r['rows'])} eventos** "
          f"(contra n={r['n_indep']} janelas na analise por janela).", "",
          f"Janelas translacionais densas: {r['n_trans']}; nao-sobrepostas: {r['n_indep']}; "
          f"movimento pontuado = {r['n_indep']} x {DEFAULT_HMAX * r['ts']:.1f} s = "
          f"**{r['seconds']:.1f} s**.", "",
          "| evento (idx) | twin e_pos (m) | ideal e_pos (m) | gap (m) | janelas |",
          "|---|---|---|---|---|"]
    for s, t, i, n in r["rows"]:
        L.append(f"| {s} | {t:.4f} | {i:.4f} | {i - t:+.4f} | {n} |")
    L += ["", f"- Wilcoxon pareado **por evento** (one-sided twin<ideal): **p = {r['p']:.4g}**",
          f"- Gap mediano por evento: **{r['gap']:+.4f} m**; IC95% bootstrap por evento "
          f"[{r['ci'][0]:+.4f}, {r['ci'][1]:+.4f}]",
          f"- Rank-biserial pareado por evento: **{r['rank_biserial']:+.3f}** "
          f"({r['wins']} a favor / {r['losses']} contra)",
          "", f"Todos em h_ref = {r['h_ref_s']:.1f} s, bin translacional, twin vs cinematica ideal."]
    return L


def run(root: Path | None = None, out: Path | None = None, *, h_ref: int = 24,
        quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out, seed=SEED)
    r = compute(ctx, h_ref=h_ref)
    L = render(ctx, r)
    p = ctx.write_text(NAME, L)
    if not quiet:
        print("\n".join(L))
        print(f"\nartefato: {p}")
    r["path"] = p
    return r


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
