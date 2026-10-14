"""e_pos and e_ang of the THREE plants at the six horizons (paper Table II, Fig. 2a).

Translation bin, medians over dense windows: twin (FOPDT) vs ideal kinematics
(both re-simulated here) and vs rSim (ODE; rollouts read from the persisted
cache ``results/_cache_rsim_rollouts.{npz,pkl}``, same windows). Also prints the
leakage check between the fidelity hold-out (config/holdout_events.json) and
the identification hold-out (results/fit_holdout_vxvy_*.csv).

Legacy: scripts/epos_eang_three_models.py -> results/epos_eang_three_models_20260810_1022.md.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from dtssl.analysis import common as C
from dtssl.models import AnalyticFOPDTPlant, IdealKinematicPlant

NAME = "epos_eang_three_models"
KIND = "analysis"
CLAIM = "Position and heading error, three plants, six horizons (Table II, Fig. 2a)"
REQUIRES = ("data", "rsim_cache")


def compute(ctx: C.Ctx) -> dict:
    segs, _ = ctx.holdout()
    P, H = ctx.params, ctx.horizons
    tw = C.ros(segs, lambda: AnalyticFOPDTPlant(P), horizons=H)
    idl = C.ros(segs, lambda: IdealKinematicPlant(), horizons=H)
    rsl = C.load_rsim_cache(ctx, n_expected=len(segs))[:len(segs)]
    T1 = C.paired_table(ctx, tw, idl)
    T2 = C.paired_table(ctx, tw, rsl)
    m = C.trans_mask(T1)
    rows = []
    for k, h in enumerate(H):
        rows.append(dict(h_s=h * T1.ts,
                         epos_twin=float(np.median(T1.epos_twin[m, k])),
                         epos_ideal=float(np.median(T1.epos_def[m, k])),
                         epos_rsim=float(np.median(T2.epos_def[m, k])),
                         eang_twin=float(np.median(T1.eang_twin[m, k])),
                         eang_ideal=float(np.median(T1.eang_def[m, k])),
                         eang_rsim=float(np.median(T2.eang_def[m, k]))))
    return dict(rows=rows, n_trans=int(m.sum()))


def leakage_check(ctx: C.Ctx, id_holdout_csv: Path | str | None = None) -> dict:
    fid = {e["event"] for e in ctx.holdout_cfg["events"]}
    if id_holdout_csv is None:
        cands = sorted(ctx.results_dir.glob("fit_holdout_vxvy_*.csv"))
        if not cands:
            return dict(available=False)
        id_holdout_csv = cands[-1]
    idh = set()
    with open(id_holdout_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            idh.add(row["evento"])
    return dict(available=True, source=str(id_holdout_csv), fidelity=sorted(fid),
                identification=sorted(idh), id_subset_of_fid=idh <= fid,
                fid_not_in_id=sorted(fid - idh))


def render(ctx: C.Ctx, r: dict) -> list[str]:
    L = C.result_header("e_ang por horizonte e e_pos dos tres modelos", ctx,
                        generator=f"dtssl.analysis.{NAME}")
    L += ["Bin translacional, medianas sobre janelas densas.", "",
          "| h (s) | twin e_pos | ideal e_pos | rSim e_pos | twin e_ang | ideal e_ang | rSim e_ang |",
          "|---|---|---|---|---|---|---|"]
    for x in r["rows"]:
        L.append(f"| {x['h_s']:.2f} | {x['epos_twin']:.4f} | {x['epos_ideal']:.4f} | {x['epos_rsim']:.4f} "
                 f"| {x['eang_twin']:.4f} | {x['eang_ideal']:.4f} | {x['eang_rsim']:.4f} |")
    L += ["", "e_ang em rad. Fecha a objecao C6 (o artigo afirmava que o heading do twin",
          "excede o do rSim em horizontes longos sem nunca dar o numero do rSim)."]
    return L


def run(root: Path | None = None, out: Path | None = None, *, id_holdout_csv: str | None = None,
        quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out)
    r = compute(ctx)
    L = render(ctx, r)
    p = ctx.write_text(NAME, L)
    leak = leakage_check(ctx, id_holdout_csv)
    r.update(path=p, leakage=leak)
    if not quiet:
        print("\n".join(L))
        print("\n=== VAZAMENTO ===")
        if leak.get("available"):
            print("hold-out de fidelidade (%d):" % len(leak["fidelity"]), leak["fidelity"])
            print("hold-out de identificacao   :", leak["identification"])
            print("ID subset de FID?", leak["id_subset_of_fid"])
            print("eventos de fidelidade NAO usados na ID:", leak["fid_not_in_id"])
        else:
            print("(results/fit_holdout_vxvy_*.csv ausente; checagem pulada)")
        print(f"\nartefato: {p}")
    return r


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
