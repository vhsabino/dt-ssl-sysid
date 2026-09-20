"""Hold-out metric report: twin (AnalyticFOPDTPlant) vs default (IdealKinematic),
same paired windows. Prints the BIN DISTRIBUTION first, then the verdict per bin;
saves figures (PNG/SVG) and a Markdown report
(``phase0_metrics_report_<stamp>.md``; the name is kept for continuity with
results/phase0_metrics_report_20260724_1729.md).

Legacy: phase0_replay/metrics_report.py -> results/phase0_metrics_report_20260724_1729.md.
"""
from __future__ import annotations

from pathlib import Path

from dtssl.analysis import common as C
from dtssl.eval.metrics import (BIN_LABEL, evaluate, format_bin_distribution, make_figures,
                                markdown_report)
from dtssl.models import AnalyticFOPDTPlant, IdealKinematicPlant
from dtssl.sim.rollout import DEFAULT_HMAX, DEFAULT_STRIDE, rollout_segment

NAME = "metrics_report"
KIND = "report"
CLAIM = "Twin vs ideal SE(2) multi-horizon gate on the hold-out (trans GO, gap@h_ref +0.0617 m)"
REQUIRES = ("data",)


def run(root: Path | None = None, out: Path | None = None, *, stride: int = DEFAULT_STRIDE,
        h_max: int = DEFAULT_HMAX, quiet: bool = False, **kw) -> dict:
    ctx = C.make_context(root, out)
    params, mcfg = ctx.params, ctx.mcfg
    segs, dropped = ctx.holdout()

    twin = AnalyticFOPDTPlant(params)
    ideal = IdealKinematicPlant()
    twin_ros, def_ros = [], []
    for s in segs:
        twin_ros.append(rollout_segment(s, twin, h_max=h_max, stride=stride, horizons=mcfg["horizons"]))
        def_ros.append(rollout_segment(s, ideal, h_max=h_max, stride=stride, horizons=mcfg["horizons"]))

    result = evaluate(twin_ros, def_ros, params=params, mcfg=mcfg)

    if not quiet:
        print("=" * 70)
        print(format_bin_distribution(result["table"]))
        print("=" * 70)
        print("\nVereditos por bin (gates: placeholder de omega + populacao N_min):")
        for b in ("trans", "misto", "rot"):
            v = result["verdicts"][b]
            extra = ""
            if v.get("gap_at_href") is not None:
                extra = (f" | gap@h_ref={v['gap_at_href']:+.4f} m, p={v['p_at_href']:.3g}, "
                         f"effect={v['effect_at_href']:+.3f}")
            print(f"  {BIN_LABEL[b]:14s}: {v['verdict']:34s} (N_indep={v['n_indep']}){extra}")

    figs = make_figures(result, ctx.figs, ctx.stamp)
    header = C.result_header("Relatorio — metrica SE(2) multi-horizonte (twin vs ideal)", ctx,
                             generator=f"dtssl.analysis.{NAME}")
    body = markdown_report(result, fig_files=[Path(f).name for f in figs]).split("\n", 1)[1]
    rep = ctx.out / f"phase0_metrics_report_{ctx.stamp}.md"
    rep.write_text("\n".join(header) + body, encoding="utf-8")
    if not quiet:
        print(f"\nFiguras: {len(figs)} salvas em {ctx.figs} (M1_metrics_*_{ctx.stamp}.png/.svg)")
        print(f"Relatorio: {rep}")
    result["path"] = rep
    return result


def _extra_args(ap):
    ap.add_argument("--stride", type=int, default=None)
    ap.add_argument("--h-max", type=int, default=None, dest="h_max")


def main(argv=None):
    return C.cli_main(run, __doc__, argv, extra=_extra_args)


if __name__ == "__main__":
    main()
