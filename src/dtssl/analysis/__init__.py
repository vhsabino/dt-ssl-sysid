"""Paper analyses and figure generators (SBR/LARS 2026), one module per claim.

Every module exposes ``run(root: Path | None = None, out: Path | None = None, **kwargs)
-> dict`` (``dict["path"]`` = main artefact) and an argparse ``main(argv=None)``;
``NAME``, ``KIND`` (``analysis`` | ``fig`` | ``report``), ``CLAIM`` (the paper
claim it supports) and ``REQUIRES`` (``data``, ``rsim_cache``, ``rsim``, ``mat``, ``mujoco``).
Modules that need ``robosim`` import it lazily inside ``run`` so that the whole
registry imports on any machine. Shared helpers live in ``dtssl.analysis.common``.

Mapping analysis -> paper claim (source: open-source/README.md "One command per
claim" table, results/CHANGELOG.md, docs/PLANO_V2_EXECUTADO.md, docs/PLANO_V3_EXECUTADO.md):

| name | paper claim / artefact | legacy script |
|---|---|---|
| epos_eang_three_models | Table II, Fig. 2a: e_pos/e_ang, three plants, six horizons | scripts/epos_eang_three_models.py |
| clustered_stats | Fig. 2b: per-event statistics, 10/10 events, 73.5 s | scripts/clustered_stats.py |
| ablation_orderfree | Shapley ablation (tau 55 % / Td 43 % / K 2 %) + IC arms | scripts/ablation_orderfree.py |
| gap_decomposition | cumulative ablation (superseded by ablation_orderfree) | scripts/gap_decomposition.py |
| causal_ic_check | robustness to a strictly causal v0 (B5) | scripts/causal_ic_check.py |
| gate_window_vs_event | pre-registered window gate vs per-event analysis (C4) | scripts/gate_window_vs_event.py |
| excitation_per_dof | screening: corr / explained variance per DOF (94-96 % vs 56 %) | scripts/excitation_per_dof.py |
| analyze_omega_excitation | dilution analysis, threshold sensitivity, wheel-angle sweep (B4/C9) | scripts/analyze_omega_excitation.py |
| r3_closedloop_omega_fit | closed-loop yaw fit under the hold-out criterion (44.8 %) | scripts/r3_closedloop_omega_fit.py |
| loo_translational | leave-one-event-out dispersion of the vx/vy fits | scripts/loo_translational.py |
| negcontrol_perevent | negative control (Bayesian calibration), per event (C3) | scripts/negcontrol_perevent.py |
| eval_rsim_delay_ablation | matched-delay ablation on rSim (B5/B6) | scripts/eval_rsim_delay_ablation.py |
| eval_twin_vs_rsim | twin vs rSim gate, modes A/B (Sec. V; needs robosim) | phase0_replay/eval_twin_vs_rsim.py |
| metrics_report | twin vs ideal SE(2) gate on the hold-out (trans GO) | phase0_replay/metrics_report.py |
| window_errors_eang | e_ang per window/horizon, twin vs ideal | scripts/window_errors_eang.py |
| backends_holdout | twin vs MuJoCo routes a/b vs ideal on the hold-out (2026-09) | new |
| identifiability_insilico | C1: in-silico identifiability, regime x noise x deadzone, known theta (2026-09) | new |
| regenerate_bin_distribution | bin distribution with the CAD radius (D9) | scripts/regenerate_bin_distribution.py |
| holdout_report | honest hold-out report, twin vs rSim (needs robosim) | phase0_replay/holdout_report.py |
| loader_report | loader sanity + duration distribution (H_max) | phase0_replay/report.py |
| session_report | recorded twin session: contract, command stats vs competition, harness round trip (2026-09) | new |
| fig_main_result | Fig. 2 (main figure) | scripts/fig_main_result.py |
| fig_omega_stepresponse_en | Fig. 1 (yaw step response) | scripts/fig_omega_stepresponse_en.py |
| fig_fit_holdout_vxvy | hold-out fit figure of vx/vy (+ CSV vs MATLAB) | scripts/fig_fit_holdout_vxvy.py |
| fig_trajectory_holdout | median-window trajectory overlay | scripts/fig_trajectory_holdout.py |
| fig_trajectory_by_label | best-case trajectory overlay per label | scripts/fig_trajectory_by_label.py |
| fig_twin_vs_rsim_epos_en | twin vs rSim e_pos panel (transcribed numbers) | scripts/fig_twin_vs_rsim_epos_en.py |
| fig_spec_main_result | visual contract of Fig. 2 (internal) | scripts/fig_spec_main_result.py |
| meeting_overlay | meeting overlay real/twin/rSim (internal; needs robosim) | phase0_replay/meeting_overlay.py |
| percurso_completo | whole-segment free-run overlays (needs robosim) | phase0_replay/percurso_completo.py |
| percurso_square | whole-segment free-run of the square events (needs robosim) | phase0_replay/percurso_square.py |

The MATLAB identification (Table I) lives in ``matlab/dtssl`` and the rotate
split builder (``scripts/build_rotate_splits.py`` / ``build_rotate_qc.py``) in
``dtssl.data`` (ETL).
"""
from __future__ import annotations

import importlib
import importlib.util
from types import ModuleType

__all__ = ["REGISTRY", "ANALYSES", "FIGURES", "REPORTS", "load", "names", "info"]

#: name -> dotted module path (imported lazily by ``load``). Entries whose module file is
#: absent (e.g. internal figures stripped by ``tools/make_release.py``) are dropped.
_ALL: dict[str, str] = {
    # analyses (numbers cited in the paper)
    "epos_eang_three_models": "dtssl.analysis.epos_eang_three_models",
    "clustered_stats": "dtssl.analysis.clustered_stats",
    "ablation_orderfree": "dtssl.analysis.ablation_orderfree",
    "gap_decomposition": "dtssl.analysis.gap_decomposition",
    "causal_ic_check": "dtssl.analysis.causal_ic_check",
    "gate_window_vs_event": "dtssl.analysis.gate_window_vs_event",
    "excitation_per_dof": "dtssl.analysis.excitation_per_dof",
    "analyze_omega_excitation": "dtssl.analysis.analyze_omega_excitation",
    "r3_closedloop_omega_fit": "dtssl.analysis.r3_closedloop_omega_fit",
    "loo_translational": "dtssl.analysis.loo_translational",
    "negcontrol_perevent": "dtssl.analysis.negcontrol_perevent",
    "eval_rsim_delay_ablation": "dtssl.analysis.eval_rsim_delay_ablation",
    "eval_twin_vs_rsim": "dtssl.analysis.eval_twin_vs_rsim",
    "window_errors_eang": "dtssl.analysis.window_errors_eang",
    "regenerate_bin_distribution": "dtssl.analysis.regenerate_bin_distribution",
    "backends_holdout": "dtssl.analysis.backends_holdout",
    "session_report": "dtssl.analysis.session_report",
    "identifiability_insilico": "dtssl.analysis.identifiability_insilico",
    # reports
    "metrics_report": "dtssl.analysis.metrics_report",
    "holdout_report": "dtssl.analysis.holdout_report",
    "loader_report": "dtssl.analysis.loader_report",
    # figures
    "fig_main_result": "dtssl.analysis.fig_main_result",
    "fig_omega_stepresponse_en": "dtssl.analysis.fig_omega_stepresponse_en",
    "fig_fit_holdout_vxvy": "dtssl.analysis.fig_fit_holdout_vxvy",
    "fig_trajectory_holdout": "dtssl.analysis.fig_trajectory_holdout",
    "fig_trajectory_by_label": "dtssl.analysis.fig_trajectory_by_label",
    "fig_twin_vs_rsim_epos_en": "dtssl.analysis.fig_twin_vs_rsim_epos_en",
    "fig_spec_main_result": "dtssl.analysis.fig_spec_main_result",
    "meeting_overlay": "dtssl.analysis.meeting_overlay",
    "percurso_completo": "dtssl.analysis.percurso_completo",
    "percurso_square": "dtssl.analysis.percurso_square",
}

REGISTRY: dict[str, str] = {n: m for n, m in _ALL.items() if importlib.util.find_spec(m) is not None}

#: names by kind (``dtssl analysis`` runs analyses + reports; ``dtssl fig`` the figures).
_FIG_EXTRA = ("meeting_overlay", "percurso_completo", "percurso_square")
_REPORT = ("metrics_report", "holdout_report", "loader_report", "session_report")
FIGURES: tuple[str, ...] = tuple(n for n in REGISTRY if n.startswith("fig_") or n in _FIG_EXTRA)
REPORTS: tuple[str, ...] = tuple(n for n in REGISTRY if n in _REPORT)
ANALYSES: tuple[str, ...] = tuple(n for n in REGISTRY if n not in FIGURES and n not in REPORTS)


def load(name: str) -> ModuleType:
    """Import and return the registered module ``name`` (KeyError if unknown)."""
    try:
        return importlib.import_module(REGISTRY[name])
    except KeyError:
        raise KeyError(f"unknown analysis {name!r}; known: {', '.join(REGISTRY)}") from None


def names(kind: str | None = None) -> list[str]:
    if kind == "fig":
        return list(FIGURES)
    if kind == "report":
        return list(REPORTS)
    if kind == "analysis":
        return list(ANALYSES)
    return list(REGISTRY)


def info(name: str) -> dict:
    """Metadata of one entry without running it: kind, claim, requirements, docstring."""
    m = load(name)
    return dict(name=name, module=REGISTRY[name], kind=getattr(m, "KIND", "analysis"),
                claim=getattr(m, "CLAIM", ""), requires=tuple(getattr(m, "REQUIRES", ())),
                doc=(m.__doc__ or "").strip().split("\n", 1)[0])
