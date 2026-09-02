"""R3 — hold-out fit of the CLOSED-LOOP yaw model under the paper's criterion.

Same criterion as the open-loop line (Eq. 2): event-wise split of the
``shoot_to_goal`` events (seeded permutation, 2/3 train / 1/3 hold-out), single
P1D fit on the training events (Nelder-Mead on [K, tau, Td], legacy FOPDT
alignment), mean fit over the hold-out events. Closes the gap that left the
closed-loop line without a comparable number (C5 of the 1st review).

Data path: legacy resampling (``np.arange`` grid, linear command interpolation)
read from CSV when present else parquet.

Legacy: scripts/r3_closedloop_omega_fit.py -> results/r3_closedloop_omega_fit_20260810_1036.md.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from dtssl.analysis import common as C

NAME = "r3_closedloop_omega_fit"
KIND = "analysis"
CLAIM = "Closed-loop yaw fit under the paper's hold-out criterion (44.8 % vs 71.1 % open loop)"
REQUIRES = ("data",)
SEED = 42
LABEL = "shoot_to_goal"
X0 = (1.3, 0.03, 0.10)
NM_OPTIONS = dict(maxiter=400, xatol=1e-4, fatol=1e-3)
OPEN_LOOP_REF = dict(K=1.002, tau=0.0828, Td=0.0890, fit=71.1)   # results/identificacao_omega_20260724.md


def _sim(u, dt, K, tau, Td, align):
    # legacy clamps: Td >= 0, tau >= 1e-4
    return C.simulate_fopdt(u, dt, K, max(tau, 1e-4), max(Td, 0.0), align=align)


def compute(ctx: C.Ctx, label: str = LABEL, align: str = "legacy", seed: int = SEED,
            min_len: int = 60) -> dict:
    dt = ctx.ts
    D = []
    for ev in C.list_events(ctx.splits_dir, label):
        cmd, rob = C.read_event_csv(label, ev, dataset=ctx.dataset, data_root=ctx.data_root)
        s = C.legacy_uy_series(cmd, rob, "w", dt, min_len=min_len)
        if s is not None:
            D.append((ev,) + s)
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(D))
    nho = max(1, round(len(D) / 3))
    ho, tr = sorted(idx[:nho]), sorted(idx[nho:])

    def cost(p, ids):
        K, tau, Td = p
        return sum(np.sum((D[i][2] - _sim(D[i][1], dt, K, tau, Td, align)) ** 2) for i in ids)

    res = minimize(cost, list(X0), args=(tr,), method="Nelder-Mead", options=NM_OPTIONS)
    K, tau, Td = (float(x) for x in res.x)
    f_tr = [C.fit_percent(D[i][2], _sim(D[i][1], dt, K, tau, Td, align)) for i in tr]
    f_ho = [C.fit_percent(D[i][2], _sim(D[i][1], dt, K, tau, Td, align)) for i in ho]
    return dict(n_events=len(D), n_train=len(tr), n_holdout=len(ho), K=K, tau=tau, Td=Td,
                fit_train=f_tr, fit_holdout=f_ho, fit_holdout_mean=float(np.mean(f_ho)),
                fit_train_median=float(np.median(f_tr)), holdout_events=[D[i][0] for i in ho],
                align=align, label=label)


def render(ctx: C.Ctx, r: dict) -> list[str]:
    o = OPEN_LOOP_REF
    L = C.result_header("R3 - fit hold-out do ajuste de omega em MALHA FECHADA", ctx,
                        generator=f"dtssl.analysis.{NAME}", seed=SEED, extra=f"FOPDT align={r['align']}")
    L += ["Mesmo criterio da linha open-loop (Eq. 2 do artigo): split event-wise, media",
          "sobre os eventos de hold-out. Fecha a lacuna que deixava a linha closed-loop",
          "sem um numero comparavel (objecao C5 da 1a revisao independente).", "",
          f"- Eventos `{r['label']}` usados: {r['n_events']} ({r['n_train']} treino / {r['n_holdout']} hold-out)",
          f"- Parametros: K = {r['K']:.4f}, tau = {r['tau']:.4f} s, Td = {r['Td']:.4f} s",
          f"- **fit hold-out = {r['fit_holdout_mean']:.1f} %** (por evento: "
          f"{', '.join(f'{v:.1f}' for v in r['fit_holdout'])})",
          f"- fit treino (mediana) = {r['fit_train_median']:.1f} %", "",
          "Comparacao direta, agora sob o MESMO criterio:", "",
          "| regime | K | tau (s) | Td (s) | fit hold-out |", "|---|---|---|---|---|",
          f"| closed-loop (competicao) | {r['K']:.3f} | {r['tau']:.4f} | {r['Td']:.4f} | **{r['fit_holdout_mean']:.1f} %** |",
          f"| open-loop (dedicado) | {o['K']:.3f} | {o['tau']:.4f} | {o['Td']:.4f} | **{o['fit']:.1f} %** |", "",
          "Gate pre-registrado: fit hold-out >= 60 %."]
    return L


def run(root: Path | None = None, out: Path | None = None, *, align: str = "legacy",
        seed: int = SEED, quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out, seed=seed)
    r = compute(ctx, align=align, seed=seed)
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
