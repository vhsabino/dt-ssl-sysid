"""Evaluation harness: SE(2) multi-horizon metric, statistics, verdict gates and reports.

    metrics.py  ErrorTable, build_error_table, classify_bin, bin_distribution, ...
    stats.py    rank_biserial, wilcoxon_less, moving-block bootstrap (explicit rng)
    verdict.py  evaluate (driver) + GO / NO-GO / INDETERMINADO / SEM PODER gates
    report.py   make_figures, markdown_report, replay_csv, replay_figure

``dtssl.eval.metrics`` keeps re-exporting everything (historical import path).
"""
from dtssl.eval.metrics import (  # noqa: F401
    BIN_LABEL, BIN_ORDER, ErrorTable, bin_distribution, build_error_table, classify_bin,
    format_bin_distribution, load_metrics_config, pose_errors,
)
from dtssl.eval.report import make_figures, markdown_report, replay_csv, replay_figure  # noqa: F401
from dtssl.eval.stats import (  # noqa: F401
    bootstrap_rng, moving_block_bootstrap, percentile_ci, rank_biserial, wilcoxon_less,
)
from dtssl.eval.verdict import (  # noqa: F401
    VERDICT_GO, VERDICT_INDETERMINATE, VERDICT_NO_GO, VERDICT_NO_POWER, evaluate, verdict_bin,
)

__all__ = [
    "BIN_LABEL", "BIN_ORDER", "ErrorTable", "bin_distribution", "build_error_table",
    "classify_bin", "format_bin_distribution", "load_metrics_config", "pose_errors",
    "make_figures", "markdown_report", "replay_csv", "replay_figure",
    "bootstrap_rng", "moving_block_bootstrap", "percentile_ci", "rank_biserial", "wilcoxon_less",
    "VERDICT_GO", "VERDICT_INDETERMINATE", "VERDICT_NO_GO", "VERDICT_NO_POWER",
    "evaluate", "verdict_bin",
]
