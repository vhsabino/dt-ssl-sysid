"""Backends on the hold-out: behavioral twin vs MuJoCo routes (a, b) vs ideal, same harness metric.

Runs the fidelity hold-out (``config/holdout_events.json``, moving events only) through the free-run
harness (re-anchored SE(2) windows, stride 15, H_max 90, horizons of ``config/metrics.json``) for:

* ``fopdt``                 -- ``AnalyticFOPDTPlant`` with the official theta (the paper's twin);
* ``mujoco-velocity``       -- route a: the same plant driving a MuJoCo chassis (contacts, force limits);
* ``mujoco-rollers``        -- route b: physical omni wheels + free rollers, untuned, **no** command delay;
* ``mujoco-rollers-delay``  -- route b + the identified per-DOF transport delay ``Td`` on the commands
                                (the analogue of the rSim delay ablation of the paper);
* ``ideal``                 -- ideal kinematics (K=1, tau=0, Td=0), the paper's lower baseline.

Every model is evaluated on exactly the same windows (grid of the official theta). Per horizon:
window-level medians of ``e_pos`` / ``e_ang`` in the translation bin; per event (n = hold-out
events): medians at ``h_ref``, wins vs the twin, one-sided paired Wilcoxon (twin < model) and
rank-biserial effect. Also reports the *embedding check* (route a vs the analytic plant on the same
windows: max |e_pos| gap) and wall-clock cost per model.

Fairness note printed with the result: routes b are **not** calibrated (nominal geometry, contact
recipe of Wan et al. 2026) -- this is the "physical model as shipped" baseline, not a tuned twin.

Output: ``results/backends_holdout_<stamp>.md`` (+ ``.csv`` with the per-horizon medians).
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from dtssl.analysis import common as C
from dtssl.eval.stats import rank_biserial, wilcoxon_less
from dtssl.models import AnalyticFOPDTPlant

NAME = "backends_holdout"
KIND = "analysis"
CLAIM = "Behavioral twin vs MuJoCo routes a/b vs ideal on the hold-out, same windows and metric"
REQUIRES = ("data", "mujoco")
DEFAULT_MODELS = ("mujoco-velocity", "mujoco-rollers", "mujoco-rollers-delay", "ideal")


def _per_event(table, k: int, mask: np.ndarray):
    sid = np.asarray(table.seg_id)[mask]
    a, b = table.epos_twin[mask, k], table.epos_def[mask, k]
    ids = sorted(set(int(s) for s in sid))
    return (np.array([np.median(a[sid == s]) for s in ids]),
            np.array([np.median(b[sid == s]) for s in ids]), ids)


def compute(ctx: C.Ctx, models=DEFAULT_MODELS, h_ref: int | None = None) -> dict:
    from dtssl.sim.world_plant import make_harness_plant

    segs, dropped = ctx.holdout()
    P, H = ctx.params, ctx.horizons
    h_ref = int(ctx.mcfg["verdict"]["h_ref"] if h_ref is None else h_ref)
    kref = H.index(h_ref)
    t0 = time.perf_counter()
    tw = C.ros(segs, lambda: AnalyticFOPDTPlant(P), horizons=H)
    cost = {"fopdt": time.perf_counter() - t0}
    out_models = {}
    n_win = sum(r.n_total for r in tw)
    for name in models:
        t0 = time.perf_counter()
        ro = C.ros(segs, lambda name=name: make_harness_plant(name, P), horizons=H)
        cost[name] = time.perf_counter() - t0
        T = C.paired_table(ctx, tw, ro)
        m = C.trans_mask(T)
        allm = np.ones(T.W, dtype=bool)
        rows = []
        for k, h in enumerate(H):
            ev_t, ev_m, ids = _per_event(T, k, m)
            rows.append(dict(
                h=int(h), h_s=float(h * T.ts),
                epos_twin_trans=float(np.median(T.epos_twin[m, k])),
                epos_model_trans=float(np.median(T.epos_def[m, k])),
                epos_twin_all=float(np.median(T.epos_twin[allm, k])),
                epos_model_all=float(np.median(T.epos_def[allm, k])),
                eang_twin_trans=float(np.median(T.eang_twin[m, k])),
                eang_model_trans=float(np.median(T.eang_def[m, k])),
                p_wilcoxon=wilcoxon_less(ev_t, ev_m), rank_biserial=rank_biserial(ev_m, ev_t),
                wins=int((ev_t < ev_m).sum()), n_events=len(ids)))
        ev_t, ev_m, ids = _per_event(T, kref, m)
        gap = np.abs(T.epos_def[:, kref] - T.epos_twin[:, kref])
        out_models[name] = dict(
            rows=rows, per_event=[(int(i), float(a), float(b)) for i, a, b in zip(ids, ev_t, ev_m, strict=True)],
            gap_vs_twin_med=float(np.median(gap)), gap_vs_twin_max=float(gap.max()),
            n_windows=int(T.W), n_trans=int(m.sum()))
    return dict(models=out_models, order=list(models), horizons=list(H), h_ref=h_ref,
                h_ref_s=float(h_ref * tw[0].meta["ts"]), n_events=len(segs), n_windows=n_win,
                dropped=[d.get("event") if isinstance(d, dict) else str(d) for d in dropped],
                cost_s=cost, events=[s.meta.get("event") for s in segs])


def render(ctx: C.Ctx, r: dict) -> list[str]:
    L = C.result_header("Backends no hold-out: gemeo comportamental x MuJoCo (rotas a/b) x ideal", ctx,
                        generator=f"dtssl.analysis.{NAME}",
                        extra="mesmas janelas (grade do theta oficial), stride 15, H_max 90")
    L += [f"Hold-out: {r['n_events']} eventos ({', '.join(r['events'])}); "
          f"{r['n_windows']} janelas; h_ref = {r['h_ref']} amostras = {r['h_ref_s']:.2f} s.", "",
          "Modelos: `fopdt` = AnalyticFOPDTPlant (theta oficial); `mujoco-velocity` = rota (a), a mesma planta "
          "dirigindo o chassi no MuJoCo; `mujoco-rollers` = rota (b), rodas omni + roletes livres, **sem sintonia e "
          "sem atraso**; `mujoco-rollers-delay` = rota (b) + atraso de transporte Td por DOF do theta oficial; "
          "`ideal` = cinematica ideal.", "",
          "## e_pos mediano por horizonte (bin translacional, janelas densas)", "",
          "| h (s) | fopdt | " + " | ".join(r["order"]) + " |",
          "|---|---|" + "---|" * len(r["order"])]
    first = r["models"][r["order"][0]]["rows"]
    for k, row in enumerate(first):
        cells = [f"{row['h_s']:.2f}", f"{row['epos_twin_trans']:.4f}"]
        cells += [f"{r['models'][n]['rows'][k]['epos_model_trans']:.4f}" for n in r["order"]]
        L.append("| " + " | ".join(cells) + " |")
    L += ["", "## e_ang mediano por horizonte (rad, bin translacional)", "",
          "| h (s) | fopdt | " + " | ".join(r["order"]) + " |",
          "|---|---|" + "---|" * len(r["order"])]
    for k, row in enumerate(first):
        cells = [f"{row['h_s']:.2f}", f"{row['eang_twin_trans']:.4f}"]
        cells += [f"{r['models'][n]['rows'][k]['eang_model_trans']:.4f}" for n in r["order"]]
        L.append("| " + " | ".join(cells) + " |")
    L += ["", f"## Por evento em h_ref = {r['h_ref_s']:.2f} s (medianas por evento, n = {r['n_events']})", "",
          "| modelo | e_pos mediano (eventos) | gemeo vence | Wilcoxon p (gemeo < modelo) | rank-biserial | "
          "|Δe_pos| vs gemeo (mediana / max, todas as janelas) |",
          "|---|---|---|---|---|---|"]
    kref = r["horizons"].index(r["h_ref"])
    for n in r["order"]:
        M = r["models"][n]
        row = M["rows"][kref]
        med_ev = float(np.median([b for _, _, b in M["per_event"]]))
        L.append(f"| {n} | {med_ev:.4f} | {row['wins']}/{row['n_events']} | {row['p_wilcoxon']:.3g} | "
                 f"{row['rank_biserial']:+.2f} | {M['gap_vs_twin_med']:.4f} / {M['gap_vs_twin_max']:.4f} |")
    tw_ev = float(np.median([a for _, a, _ in r["models"][r["order"][0]]["per_event"]]))
    L += ["", f"Gemeo (`fopdt`) em h_ref: e_pos mediano dos eventos = {tw_ev:.4f} m.", "",
          "## Custo (segundos de parede para os rollouts do hold-out)", "",
          "| modelo | s |", "|---|---|"]
    for n, s in r["cost_s"].items():
        L.append(f"| {n} | {s:.1f} |")
    L += ["", "## Leitura", "",
          "- `mujoco-velocity` x `fopdt`: |Δe_pos| e a fidelidade do *embedding* — o quanto o chassi MuJoCo "
          "(servo dead-beat + limites de forca) reproduz a planta comportamental nas mesmas janelas.",
          "- `mujoco-rollers` e a rota fisica **como sai da caixa** (geometria nominal, contato da receita de Wan "
          "et al. 2026): nao foi calibrada contra dados — e a baseline 'simulador fisico nao sintonizado', "
          "comparavel ao rSim do artigo; `-delay` isola o efeito do atraso identificado.",
          "- Estatistica por evento (n pequeno): Wilcoxon unilateral pareado e rank-biserial, como em "
          "`clustered_stats`; nao ha bootstrap por blocos aqui."]
    if r["dropped"]:
        L += ["", f"Eventos parados descartados do hold-out: {r['dropped']}"]
    return L


def csv_rows(r: dict) -> list[dict]:
    out = []
    for n in r["order"]:
        for row in r["models"][n]["rows"]:
            out.append(dict(model=n, **row))
    return out


def run(root: Path | None = None, out: Path | None = None, *, models: str | None = None,
        quiet: bool = False, **kw) -> dict:
    import csv

    ctx = C.make_context(root, out)
    mods = tuple(m.strip() for m in models.split(",")) if models else DEFAULT_MODELS
    r = compute(ctx, models=mods)
    L = render(ctx, r)
    p = ctx.write_text(NAME, L)
    pc = ctx.out_path(NAME, "csv")
    rows = csv_rows(r)
    with open(pc, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    r.update(path=p, csv=pc)
    if not quiet:
        print("\n".join(L))
        print(f"\nartefato: {p}\ncsv: {pc}")
    return r


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
