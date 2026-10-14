"""DEPRECATED compatibility shim: ``phase0_replay`` -> ``dtssl`` (refactor of 2026-09-02).

Keeps old imports (``from phase0_replay.plant import AnalyticFOPDTPlant``) and the
unpickling of ``results/_cache_rsim_rollouts.pkl`` (pickled ``phase0_replay.rollout.Window``)
working for one release. New code must import from ``dtssl``. Remove in v2.
"""
from __future__ import annotations

import importlib
import sys
import warnings

_MAP = {
    "schema": "dtssl.data.schema",
    "resample": "dtssl.data.resample",
    "io": "dtssl.data.loader",
    "validate": "dtssl.data.validate",
    "splits": "dtssl.data.splits",
    "params": "dtssl.models.params",
    "plant": "dtssl.models",
    "rsim_plant": "dtssl.models.rsim",
    "rollout": "dtssl.sim.rollout",
    "metrics": "dtssl.eval.metrics",
    "report": "dtssl.analysis.loader_report",
    "holdout_report": "dtssl.analysis.holdout_report",
    "meeting_overlay": "dtssl.analysis.meeting_overlay",
    "percurso_completo": "dtssl.analysis.percurso_completo",
    "percurso_square": "dtssl.analysis.percurso_square",
    "metrics_report": "dtssl.analysis.metrics_report",
    "eval_twin_vs_rsim": "dtssl.analysis.eval_twin_vs_rsim",
}

warnings.warn("phase0_replay is deprecated; import from dtssl instead", DeprecationWarning, stacklevel=2)

for _old, _new in _MAP.items():
    try:
        sys.modules[f"{__name__}.{_old}"] = importlib.import_module(_new)
    except Exception:  # optional deps (robosim) may be missing
        pass


def __getattr__(name):
    if name in _MAP:
        return importlib.import_module(_MAP[name])
    raise AttributeError(name)
