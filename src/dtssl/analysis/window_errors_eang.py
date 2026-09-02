"""Numerical tabulation of e_ang (and e_pos) per window and per horizon.

``holdout_report`` only tabulates e_pos at h = {1.0, 1.5} s; here the harness is
reused as is (loader/rollout/plant/metrics — no dynamics or metric
re-implemented) to write a window table with e_ang columns for ALL horizons of
config/metrics.json, twin (official theta) vs ``IdealKinematicPlant`` (mode A
mirrored: Lw=15, stride=15, H_max=90; hold-out of config/holdout_events.json).

Legacy: scripts/window_errors_eang.py -> results/window_errors_eang_twin_vs_ideal_20260731_023856.csv
+ results/window_errors_eang_summary_20260731_023856.md.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from dtssl.analysis import common as C
from dtssl.eval.metrics import BIN_ORDER, bin_distribution
from dtssl.models import AnalyticFOPDTPlant, IdealKinematicPlant
from dtssl.sim.rollout import DEFAULT_HMAX, DEFAULT_STRIDE

NAME = "window_errors_eang"
KIND = "analysis"
CLAIM = "e_ang tabulated per window and horizon, twin vs ideal (item (a), session 2026-07-31)"
REQUIRES = ("data",)


def compute(ctx: C.Ctx) -> dict:
    segs, dropped = ctx.holdout()
    P, H = ctx.params, ctx.horizons
    twin_ros = C.ros(segs, lambda: AnalyticFOPDTPlant(P), horizons=H)
    ideal_ros = C.ros(segs, lambda: IdealKinematicPlant(), horizons=H)
    table = C.paired_table(ctx, twin_ros, ideal_ros)
    row_to_win = [(si, wi) for si, rt in enumerate(twin_ros) for wi in range(len(rt.windows))]
    assert len(row_to_win) == table.W
    return dict(table=table, twin_ros=twin_ros, row_to_win=row_to_win, n_segs=len(segs),
                n_dropped=len(dropped), horizons=H)


def write_csv(ctx: C.Ctx, r: dict) -> Path:
    table, H = r["table"], r["horizons"]
    hs = [h * table.ts for h in H]
    csvp = ctx.out_path("window_errors_eang_twin_vs_ideal", "csv")
    header = ["segmento", "t0_idx", "t0_s", "bin", "indep"]
    for hsec in hs:
        header += [f"e_pos_twin_{hsec:.1f}s_m", f"e_pos_ideal_{hsec:.1f}s_m",
                   f"e_ang_twin_{hsec:.1f}s_rad", f"e_ang_ideal_{hsec:.1f}s_rad"]
    with open(csvp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for row_i in range(table.W):
            si, wi = r["row_to_win"][row_i]
            win = r["twin_ros"][si].windows[wi]
            row = [table.seg_name[row_i], int(table.t0[row_i]), f"{win.t0_time:.4f}",
                   table.bin[row_i], int(table.indep[row_i])]
            for k in range(len(H)):
                row += [f"{table.epos_twin[row_i, k]:.4f}", f"{table.epos_def[row_i, k]:.4f}",
                        f"{table.eang_twin[row_i, k]:.4f}", f"{table.eang_def[row_i, k]:.4f}"]
            w.writerow(row)
    return csvp


def render(ctx: C.Ctx, r: dict) -> list[str]:
    table, H = r["table"], r["horizons"]
    hs = [h * table.ts for h in H]
    d = bin_distribution(table)
    P = ctx.params
    L = C.result_header("e_ang tabulado — twin (theta promovido) vs IdealKinematicPlant", ctx,
                        generator=f"dtssl.analysis.{NAME}")
    L += [f"theta twin = config/twin_params.json (K_w={P['w'].K:.4f}, tau_w={P['w'].tau:.4f}, "
          f"Td_w={P['w'].Td:.4f}; placeholder={P['w'].placeholder}).",
          f"Hold-out: {r['n_segs']} segmentos (idle dropped={r['n_dropped']}); janelas={table.W}; "
          f"modo A (Lw={C.LW}, stride={DEFAULT_STRIDE}, H_max={DEFAULT_HMAX}).",
          "Bins: " + ", ".join(f"{b}={d[b]['total']}" for b in BIN_ORDER) + ".", "",
          "NOTA: NAO e o run da Figura twin-vs-rSim 20260617_0030 (la: omega placeholder, "
          "default=rSim). Aqui: omega promovido, default=cinematica ideal.", ""]
    for scope, label in (("all", "TODAS as janelas"), ("trans", "bin trans-dominado")):
        m = table.mask(scope)
        L += [f"## Medianas (densas) — {label} (N={int(m.sum())})", "",
              "| h (s) | e_ang twin (rad) | e_ang ideal (rad) | e_pos twin (m) | e_pos ideal (m) |",
              "|---:|---:|---:|---:|---:|"]
        for k, hsec in enumerate(hs):
            L.append(f"| {hsec:.1f} | {np.median(table.eang_twin[m, k]):.4f} "
                     f"| {np.median(table.eang_def[m, k]):.4f} "
                     f"| {np.median(table.epos_twin[m, k]):.4f} "
                     f"| {np.median(table.epos_def[m, k]):.4f} |")
        L.append("")
    return L


def run(root: Path | None = None, out: Path | None = None, *, quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out, stamp_fmt=C.STAMP_FMT_S)
    r = compute(ctx)
    csvp = write_csv(ctx, r)
    L = render(ctx, r)
    mdp = ctx.write_text("window_errors_eang_summary", L, trailing_newline=True)
    if not quiet:
        print(f"CSV: {csvp}\nMD : {mdp}")
        print("\n".join(L))
    return dict(path=mdp, csv=csvp, table=r["table"])


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
