"""dtssl — behavioral digital twin of the RobôCIn SSL omnidirectional robot.

Public API (stable): the replay/evaluation harness that produced the SBR/LARS 2026
results, plus the multi-robot world, the ssl-simulation-protocol bridge, the GUI and
the MuJoCo physics backends (see docs/SPEC_DTSSL.md).
"""
from __future__ import annotations

__version__ = "1.0.0a1"

from dtssl.paths import repo_root, config_path, data_root, has_dataset  # noqa: E402
from dtssl.units import MM_TO_M, M_TO_MM, DEG2RAD, RAD2DEG, unwrap, unwrap_step  # noqa: E402
from dtssl.geometry import RobotGeometry  # noqa: E402
from dtssl.config import (load_geometry, load_limits, load_field, load_bridge_config,  # noqa: E402
                          load_holdout_config, reload as reload_config)
from dtssl.kinematics import (body_to_wheel_matrix, wheel_to_body_matrix, body_to_wheels,  # noqa: E402
                              wheels_to_body, local_to_global, global_to_local, apply_wheel_deadzone)
from dtssl.data.schema import Segment, TS_DEFAULT  # noqa: E402
from dtssl.data.loader import load_event, load_segment, event_dir, body_velocity_series  # noqa: E402
from dtssl.data.splits import load_holdout_list, load_holdout_segments  # noqa: E402
from dtssl.data.resample import matlab_colon, interp_previous, interp_linear_nan  # noqa: E402
from dtssl.models import (DofParam, load_twin_params, Plant, AnalyticFOPDTPlant,  # noqa: E402
                          IdealKinematicPlant, wrap_to_pi)
from dtssl.sim.rollout import (Window, WindowRollout, rollout_segment, free_run,  # noqa: E402
                               max_command_delay, DEFAULT_HMAX, DEFAULT_HORIZONS, DEFAULT_STRIDE,
                               save_rollouts, load_rollouts, convert_pickle_cache)
from dtssl.eval.metrics import (evaluate, build_error_table, classify_bin, bin_distribution,  # noqa: E402
                                format_bin_distribution, load_metrics_config, make_figures,
                                markdown_report, rank_biserial, ErrorTable)

__all__ = [
    "__version__", "repo_root", "config_path", "data_root", "has_dataset",
    "MM_TO_M", "M_TO_MM", "DEG2RAD", "RAD2DEG", "unwrap", "unwrap_step",
    "RobotGeometry", "load_geometry", "load_limits", "load_field", "load_bridge_config",
    "load_holdout_config", "reload_config",
    "body_to_wheel_matrix", "wheel_to_body_matrix", "body_to_wheels", "wheels_to_body",
    "local_to_global", "global_to_local", "apply_wheel_deadzone",
    "Segment", "TS_DEFAULT",
    "load_event", "load_segment", "event_dir", "body_velocity_series",
    "load_holdout_list", "load_holdout_segments",
    "matlab_colon", "interp_previous", "interp_linear_nan",
    "DofParam", "load_twin_params",
    "Plant", "AnalyticFOPDTPlant", "IdealKinematicPlant", "wrap_to_pi",
    "Window", "WindowRollout", "rollout_segment", "free_run", "max_command_delay",
    "DEFAULT_HMAX", "DEFAULT_HORIZONS", "DEFAULT_STRIDE",
    "save_rollouts", "load_rollouts", "convert_pickle_cache",
    "evaluate", "build_error_table", "classify_bin", "bin_distribution",
    "format_bin_distribution", "load_metrics_config", "make_figures",
    "markdown_report", "rank_biserial", "ErrorTable",
]
