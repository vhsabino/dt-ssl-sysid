"""Leave-one-event-out per translational DOF (dispersion of the P1D fit).

Full refit at every fold (Nelder-Mead on [K, log tau, log Td], legacy FOPDT
alignment — see ``common.simulate_fopdt``), keeping the P1D structure and the
paper's Eq. (2) fit metric. Does NOT change the promoted model in
config/twin_params.json; answers the objection that the vx fit rests on a single
hold-out event. Data path: legacy resampling (``np.arange`` grid, linear command
interpolation, positions mm -> m), read from CSV when present else parquet.

Legacy: scripts/loo_translational.py -> results/loo_translational_20260810_1743.md
(results/_BROKEN_loo_translational_20260810_1742.md is the earlier run WITHOUT the
mm -> m conversion: K ~ 1000, negative tau/Td — never cite it).
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from dtssl.analysis import common as C

NAME = "loo_translational"
KIND = "analysis"
CLAIM = "Leave-one-event-out dispersion of the vx/vy P1D fits (Open item 3 of V3)"
REQUIRES = ("data",)
LABELS = {"vx": "front_to_back", "vy": "side_to_side"}
X0 = (1.1, math.log(0.08), math.log(0.06))
NM_OPTIONS = dict(maxiter=350, xatol=1e-4, fatol=1e-3)


def _sim(u: np.ndarray, dt: float, K: float, tau: float, Td: float, align: str) -> np.ndarray:
    # legacy clamps: tau >= 1e-3, Td >= 0
    return C.simulate_fopdt(u, dt, K, max(tau, 1e-3), max(Td, 0.0), align=align)


def compute(ctx: C.Ctx, labels: dict[str, str] | None = None, align: str = "legacy",
            min_len: int = 60) -> dict:
    labels = labels or LABELS
    dt = ctx.ts
    out = {}
    for dof, label in labels.items():
        D = []
        for ev in C.list_events(ctx.splits_dir, label):
            cmd, rob = C.read_event_csv(label, ev, dataset=ctx.dataset, data_root=ctx.data_root)
            s = C.legacy_uy_series(cmd, rob, dof, dt, min_len=min_len, pos_scale=1e-3)
            if s:
                D.append((ev,) + s)
        fits = []
        for i in range(len(D)):
            tr = [j for j in range(len(D)) if j != i]

            def f(q, tr=tr):
                return sum(np.sum((D[j][2] - _sim(D[j][1], dt, q[0], math.exp(q[1]),
                                                  math.exp(q[2]), align)) ** 2) for j in tr)

            r = minimize(f, list(X0), method="Nelder-Mead", options=NM_OPTIONS)
            pk = (float(r.x[0]), math.exp(r.x[1]), math.exp(r.x[2]))
            fits.append(dict(event=D[i][0], fit=C.fit_percent(D[i][2], _sim(D[i][1], dt, *pk, align)),
                             K=pk[0], tau=pk[1], Td=pk[2]))
        v = np.array([x["fit"] for x in fits]); K = np.array([x["K"] for x in fits])
        out[dof] = dict(label=label, n_events=len(D), fits=fits,
                        fit_mean=float(v.mean()), fit_std=float(v.std(ddof=1)) if len(v) > 1 else 0.0,
                        fit_min=float(v.min()), fit_max=float(v.max()),
                        K_mean=float(K.mean()), K_std=float(K.std(ddof=1)) if len(K) > 1 else 0.0,
                        K_promoted=ctx.params[dof].K)
    return dict(dofs=out, align=align)


def render(ctx: C.Ctx, r: dict) -> list[str]:
    L = C.result_header("Leave-one-event-out por DOF translacional", ctx,
                        generator=f"dtssl.analysis.{NAME}", extra=f"FOPDT align={r['align']}")
    L += ["Refit completo a cada dobra, mantendo a estrutura P1D e a metrica Eq.(2).",
          "NAO altera o modelo promovido em config/twin_params.json -- e analise de",
          "dispersao, nao re-identificacao. Responde a objecao recorrente de que o fit",
          "de vx repousa sobre UM unico evento de hold-out.", ""]
    for dof, d in r["dofs"].items():
        L += [f"## {dof} (`{d['label']}`, {d['n_events']} eventos, {d['n_events']} dobras)", "",
              "| evento retido | fit (%) | K | tau (s) | Td (s) |", "|---|---|---|---|---|"]
        for x in d["fits"]:
            L.append(f"| {x['event']} | {x['fit']:.1f} | {x['K']:.3f} | {x['tau']:.4f} | {x['Td']:.4f} |")
        L += ["", f"- fit medio **{d['fit_mean']:.1f} %**, desvio **{d['fit_std']:.1f} p.p.**, "
              f"faixa {d['fit_min']:.1f}-{d['fit_max']:.1f} %",
              f"- K medio {d['K_mean']:.3f}, desvio {d['K_std']:.3f} (promovido: {d['K_promoted']:.3f})", ""]
    return L


def run(root: Path | None = None, out: Path | None = None, *, align: str = "legacy",
        quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out)
    r = compute(ctx, align=align)
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
