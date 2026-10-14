"""Regenerate the hold-out bin distribution with the corrected robot radius (D9).

Same CSV/MD/figure as ``holdout_report._bin_distribution`` (now reused directly,
the legacy script duplicated it because importing ``holdout_report`` pulled in
``robosim``), with the pairing twin vs ``IdealKinematicPlant`` instead of twin vs
rSim. The pairing does NOT affect the bin distribution: ``classify_bin`` only
depends on ``win.cmd`` (the real hold-out commands), identical for any pairing.

Legacy: scripts/regenerate_bin_distribution.py -> results/bin_distribution_20260724_155551.{csv,md}.
"""
from __future__ import annotations

from pathlib import Path

from dtssl.analysis import common as C
from dtssl.analysis.holdout_report import _bin_distribution
from dtssl.eval.metrics import _get_robot_radius
from dtssl.models import AnalyticFOPDTPlant, IdealKinematicPlant

NAME = "regenerate_bin_distribution"
KIND = "analysis"
CLAIM = "Bin distribution of the hold-out with the CAD robot radius (D9): 264/265 translation-dominated"
REQUIRES = ("data",)
EXPECTED_RADIUS = 0.079601   # D9 / CAD (config/twin_params.json)

COMPARATOR_NOTE = (
    "**Pareamento twin vs IdealKinematicPlant** (nao vs RSimReplay/grSim como "
    "o `bin_distribution_20260619_000422.md` original -- a classificacao de bin "
    "so depende de `win.cmd`, identico em qualquer pareamento, entao isso nao "
    "afeta a distribuicao reportada aqui).")


def run(root: Path | None = None, out: Path | None = None, *, check_radius: bool = True,
        quiet: bool = False, **kw) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    ctx = C.make_context(root, out, stamp_fmt=C.STAMP_FMT_S)
    rr = float(ctx.twin_json.get("robot_radius", _get_robot_radius()))
    if not quiet:
        print(f"[{NAME}] robot_radius lido de config/twin_params.json = {rr}")
    if check_radius and abs(rr - EXPECTED_RADIUS) > 1e-9:
        raise RuntimeError(f"esperado robot_radius={EXPECTED_RADIUS} (D9/CAD), leu {rr}")

    segs, dropped = ctx.holdout()
    P = ctx.params
    twin_ros = C.ros(segs, lambda: AnalyticFOPDTPlant(P))
    ideal_ros = C.ros(segs, lambda: IdealKinematicPlant())
    table = C.paired_table(ctx, twin_ros, ideal_ros)
    bin_csv, bin_md, png, svg, d, rows = _bin_distribution(
        table, ctx.out, ctx.figs, ctx.stamp, robot_radius=rr, comparator_note=COMPARATOR_NOTE)
    if not quiet:
        print(bin_md.read_text(encoding="utf-8"))
        print(f"\nArquivos novos: {bin_csv}, {bin_md}, {png}, {svg}")
    return dict(path=bin_md, csv=bin_csv, png=png, svg=svg, distribution=d, rows=rows,
                robot_radius=rr)


def main(argv=None):
    return C.cli_main(run, __doc__, argv)


if __name__ == "__main__":
    main()
