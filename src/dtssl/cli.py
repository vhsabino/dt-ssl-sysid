"""``dtssl`` command-line entry point (``pyproject.toml: [project.scripts] dtssl = dtssl.cli:main``).

Built-in subcommands (core dependencies only):

    dtssl info                                   version, repo root, dataset, backends, extras
    dtssl replay <label> <event> [--theta P] [--plant fopdt|ideal|mujoco-velocity|mujoco-rollers[-delay]|proto:<sim>[+delay]][+preroll] [--out DIR]
    dtssl gate twin-vs-ideal [--stride S] [--h-max H]      hold-out gate (SE(2) multi-horizon)
    dtssl gate twin-vs-rsim  [--mode A|B] ...              (needs robosim)
    dtssl cache-convert <pkl> <npz>              legacy pickle rollout cache -> .npz

Optional subcommand groups are discovered from a fixed list of modules, each exposing
``register(subparsers) -> None`` (``dtssl.analysis.cli``, ``dtssl.data.cli``,
``dtssl.bridge.cli``, ``dtssl.gui.cli``, ``dtssl.physics.cli``). A module that cannot be
imported (missing extra) is skipped and ``dtssl info`` / an attempt to use one of its commands
prints the install hint.
"""
from __future__ import annotations

import argparse
import importlib
import importlib.util
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

__all__ = ["main", "build_parser", "OPTIONAL_CLI_MODULES"]

#: (module, extra / install hint) — order = order of the subcommands in --help.
OPTIONAL_CLI_MODULES: tuple[tuple[str, str], ...] = (
    ("dtssl.analysis.cli", "core install (pip install -e .)"),
    ("dtssl.data.cli", "pip install dtssl[etl]"),
    ("dtssl.bridge.cli", "core install (protobuf)"),
    ("dtssl.gui.cli", "pip install dtssl[gui]"),
    ("dtssl.physics.cli", "pip install dtssl[mujoco]"),
)

#: Subcommand names expected from the optional modules (for a helpful message when absent).
_EXTRA_COMMANDS = {
    "analysis": "dtssl.analysis.cli", "fig": "dtssl.analysis.cli",
    "etl": "dtssl.data.cli",
    "serve": "dtssl.bridge.cli", "proto-build": "dtssl.bridge.cli",
    "gui": "dtssl.gui.cli",
    "mjcf": "dtssl.physics.cli",
}

_OPTIONAL_DEPS = ("mujoco", "PySide6", "pyqtgraph", "pygame", "robosim", "betterproto", "h5py")


# =========================================================================
# parser
def _load_optional(subparsers) -> dict[str, str | None]:
    """Import every optional CLI module and let it register; returns {module: error or None}."""
    status: dict[str, str | None] = {}
    for mod_name, _hint in OPTIONAL_CLI_MODULES:
        try:
            mod = importlib.import_module(mod_name)
        except ImportError as e:
            status[mod_name] = f"{type(e).__name__}: {e}"
            continue
        reg = getattr(mod, "register", None)
        if reg is None:
            status[mod_name] = "module has no register(subparsers)"
            continue
        reg(subparsers)
        status[mod_name] = None
    return status


def build_parser(with_optional: bool = True) -> tuple[argparse.ArgumentParser, dict[str, str | None]]:
    from dtssl import __version__

    ap = argparse.ArgumentParser(prog="dtssl",
                                 description="Behavioral digital twin of the RobôCIn SSL robot.")
    ap.add_argument("--version", action="version", version=f"dtssl {__version__}")
    sub = ap.add_subparsers(dest="command", metavar="<command>")

    p = sub.add_parser("info", help="version, repository root, dataset/backends/extras availability")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("replay", help="free-run of one dataset event vs truth (e_pos per horizon, CSV + PNG)")
    p.add_argument("label", help="split label, e.g. side_to_side")
    p.add_argument("event", help="event id, e.g. side_to_side_01_05")
    p.add_argument("--theta", type=Path, default=None, help="theta JSON (default config/twin_params.json)")
    p.add_argument("--plant", default="fopdt",
                   help="fopdt | ideal | mujoco-velocity | mujoco-rollers | mujoco-rollers-delay | world:<backend> | "
                        "proto:<sim>[+delay] (external simulator of config/external_sims.json, real time); any of them "
                        "+preroll (recorded prefix driven before each window, re-anchored at t0; dtssl.sim.preroll)")
    p.add_argument("--dataset", default=None, help="dataset id under data/extracted (default: canonical)")
    p.add_argument("--h-max", type=int, default=None, help="rollout horizon in samples (default 90)")
    p.add_argument("--stride", type=int, default=None, help="window stride in samples (default 15)")
    p.add_argument("--out", type=Path, default=None, help="output directory (default results/replay)")
    p.add_argument("--no-fig", action="store_true", help="skip the PNG")
    p.set_defaults(func=cmd_replay)

    p = sub.add_parser("gate", help="hold-out statistical gate (twin vs baseline)")
    p.add_argument("which", choices=("twin-vs-ideal", "twin-vs-rsim"))
    p.add_argument("--stride", type=int, default=None)
    p.add_argument("--h-max", type=int, default=None)
    p.add_argument("--mode", choices=("A", "B"), default="A", help="twin-vs-rsim: IC fairness mode")
    p.add_argument("--out", type=Path, default=None, help="output directory (default results/)")
    p.set_defaults(func=cmd_gate)

    p = sub.add_parser("cache-convert", help="convert a legacy pickle rollout cache to .npz (+ .json meta)")
    p.add_argument("pkl", type=Path)
    p.add_argument("npz", type=Path)
    p.set_defaults(func=cmd_cache_convert)

    status = _load_optional(sub) if with_optional else {}
    return ap, status


# =========================================================================
# built-in commands
def _yes(b: bool) -> str:
    return "yes" if b else "no"


def cmd_info(args) -> int:
    from dtssl import __version__
    from dtssl.paths import config_dir, data_root, has_dataset, repo_root

    print(f"dtssl {__version__}  (python {sys.version.split()[0]})")
    try:
        root = repo_root()
        print(f"repo root : {root}")
    except RuntimeError as e:
        print(f"repo root : not found ({e})")
    try:
        print(f"config dir: {config_dir()}")
    except RuntimeError:
        print("config dir: not found")
    try:
        dr = data_root()
        print(f"dataset   : {dr}  present={_yes(has_dataset())}")
    except RuntimeError:
        print("dataset   : (no repo root)")
    try:
        from dtssl.config import load_twin_params
        theta = load_twin_params()
        dofs = ", ".join(f"{d}: K={p.K:.4f} tau={p.tau:.4f} Td={p.Td:.4f}{' (placeholder)' if p.placeholder else ''}"
                         for d, p in theta.items())
        print(f"theta     : {dofs}")
    except Exception as e:  # noqa: BLE001 - informational
        print(f"theta     : unavailable ({type(e).__name__}: {e})")
    try:
        from dtssl.sim.backends import available
        print(f"backends  : {', '.join(available())}")
    except Exception as e:  # noqa: BLE001 - twin_world/mujoco may be missing or broken
        print(f"backends  : unavailable ({type(e).__name__}: {e})")
    deps = ", ".join(f"{m}={_yes(importlib.util.find_spec(m) is not None)}" for m in _OPTIONAL_DEPS)
    print(f"extras    : {deps}")
    status = getattr(args, "_optional_status", {})
    for mod_name, hint in OPTIONAL_CLI_MODULES:
        err = status.get(mod_name, "not probed")
        print(f"cli module: {mod_name:22s} {'ok' if err is None else f'missing ({err}; {hint})'}")
    return 0


def cmd_replay(args) -> int:
    import numpy as np

    from dtssl.config import load_metrics_config, load_twin_params
    from dtssl.data.loader import DATASET_DEFAULT, load_segment
    from dtssl.eval.metrics import _window_errors, pose_errors
    from dtssl.eval.report import replay_csv, replay_figure
    from dtssl.models import AnalyticFOPDTPlant, IdealKinematicPlant
    from dtssl.paths import results_dir
    from dtssl.sim.rollout import DEFAULT_HMAX, DEFAULT_STRIDE, free_run, rollout_segment

    seg = load_segment(args.label, args.event, dataset=args.dataset or DATASET_DEFAULT)
    if args.plant == "fopdt":
        theta = load_twin_params(args.theta)
        plant = AnalyticFOPDTPlant(theta)
        theta_src = str(args.theta) if args.theta else "config/twin_params.json"
    elif args.plant == "ideal":
        plant, theta_src = IdealKinematicPlant(), "-"
    else:
        from dtssl.sim.world_plant import make_harness_plant

        theta = load_twin_params(args.theta)
        plant = make_harness_plant(args.plant, theta)
        theta_src = str(args.theta) if args.theta else "config/twin_params.json"
    mcfg = load_metrics_config()
    h_max = args.h_max or DEFAULT_HMAX
    stride = args.stride or DEFAULT_STRIDE
    horizons = [h for h in mcfg["horizons"] if h <= h_max] or [h_max]

    # 1) whole-event free-run from the logged initial condition (no commands before t0)
    cmd = np.column_stack([seg.cmd_vx, seg.cmd_vy, seg.cmd_w])
    pose_sim = free_run(plant, cmd[:-1], pose0=seg.pose0, velb0=seg.velb0, dt=seg.ts, prev_cmds=None)
    pose_real = np.column_stack([seg.pos_x, seg.pos_y, seg.theta])
    epos_full, eang_full = pose_errors(pose_sim, pose_real)

    # 2) windowed multi-horizon errors (the harness metric)
    ro = rollout_segment(seg, plant, h_max=h_max, stride=stride, horizons=tuple(horizons))
    H = np.asarray(horizons, int)
    if ro.n_total:
        E = np.array([_window_errors(w, H) for w in ro.windows])       # (nw, 2, nh)
        with np.errstate(all="ignore"):                                # proto: plants: lost windows are NaN
            epos_med, epos_p90 = np.nanmedian(E[:, 0], 0), np.nanpercentile(E[:, 0], 90, axis=0)
            eang_med = np.nanmedian(E[:, 1], 0)
    else:
        epos_med = epos_p90 = eang_med = np.full(H.size, np.nan)

    print(f"replay {args.label}/{args.event}: N={seg.n} samples ({seg.duration_s:.2f} s), "
          f"plant={type(plant).__name__}, theta={theta_src}")
    print(f"windows: {ro.n_total} (stride={stride}, h_max={h_max}, idle={ro.n_idle})")
    print(f"{'h (smp)':>8s} {'h (s)':>7s} {'e_pos med':>10s} {'e_pos p90':>10s} {'e_ang med':>10s} {'e_pos full':>11s}")
    horizon_table = {}
    for k, h in enumerate(H):
        full = float(epos_full[h]) if h < epos_full.size else float("nan")
        print(f"{int(h):8d} {h * seg.ts:7.3f} {epos_med[k]:10.4f} {epos_p90[k]:10.4f} {eang_med[k]:10.4f} {full:11.4f}")
        horizon_table[float(h * seg.ts)] = float(epos_med[k])
    print(f"whole-event free-run: final e_pos={epos_full[-1]:.3f} m, max e_pos={epos_full.max():.3f} m, "
          f"max e_ang={eang_full.max():.3f} rad")

    out = args.out or (results_dir() / "replay")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"replay_{args.event}_{args.plant}_{stamp}"
    csv = replay_csv(seg, pose_sim, Path(out) / f"{base}.csv")
    print(f"csv: {csv}")
    if not args.no_fig:
        png = replay_figure(seg, pose_sim, Path(out) / f"{base}.png",
                            title=f"replay {args.event} — {type(plant).__name__}",
                            horizon_table=horizon_table)
        print(f"png: {png}")
    return 0


def _gate_twin_vs_ideal_minimal(stride: int | None, h_max: int | None, out: Path | None) -> dict:
    """Fallback of ``dtssl gate twin-vs-ideal`` when ``dtssl.analysis.metrics_report`` is absent."""
    from dtssl.config import load_metrics_config, load_twin_params
    from dtssl.data.splits import load_holdout_segments
    from dtssl.eval import evaluate, format_bin_distribution, make_figures, markdown_report
    from dtssl.eval.metrics import BIN_LABEL, BIN_ORDER
    from dtssl.models import AnalyticFOPDTPlant, IdealKinematicPlant
    from dtssl.paths import results_dir
    from dtssl.sim.rollout import DEFAULT_HMAX, DEFAULT_STRIDE, rollout_segment

    stride = stride or DEFAULT_STRIDE
    h_max = h_max or DEFAULT_HMAX
    params = load_twin_params()
    mcfg = load_metrics_config()
    segs, dropped = load_holdout_segments(min_displacement_m=0.1)
    twin, ideal = AnalyticFOPDTPlant(params), IdealKinematicPlant()
    kw = dict(h_max=h_max, stride=stride, horizons=mcfg["horizons"])
    twin_ros = [rollout_segment(s, twin, **kw) for s in segs]
    def_ros = [rollout_segment(s, ideal, **kw) for s in segs]
    result = evaluate(twin_ros, def_ros, params=params, mcfg=mcfg)
    print("=" * 70)
    print(format_bin_distribution(result["table"]))
    print("=" * 70)
    print("\nVereditos por bin:")
    for b in BIN_ORDER:
        v = result["verdicts"][b]
        extra = ""
        if v.get("gap_at_href") is not None:
            extra = (f" | gap@h_ref={v['gap_at_href']:+.4f} m, p={v['p_at_href']:.3g}, "
                     f"effect={v['effect_at_href']:+.3f}")
        print(f"  {BIN_LABEL[b]:14s}: {v['verdict']:34s} (N_indep={v['n_indep']}){extra}")
    out = Path(out) if out else results_dir()
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    figs = make_figures(result, out / "figs", stamp)
    rep = out / f"phase0_metrics_report_{stamp}.md"
    rep.write_text(markdown_report(result, fig_files=[Path(f).name for f in figs]), encoding="utf-8")
    print(f"\nFiguras: {len(figs)} em {out / 'figs'}\nRelatorio: {rep}")
    return result


def cmd_gate(args) -> int:
    if args.which == "twin-vs-ideal":
        try:
            from dtssl.analysis.metrics_report import run
        except ImportError:
            run = None
        if run is not None and args.out is None:
            kw = {}
            if args.stride is not None:
                kw["stride"] = args.stride
            if args.h_max is not None:
                kw["h_max"] = args.h_max
            run(**kw)
        else:
            _gate_twin_vs_ideal_minimal(args.stride, args.h_max, args.out)
        return 0
    # twin-vs-rsim: needs robosim (dtssl[rsim]) and the analysis module
    try:
        from dtssl.analysis.eval_twin_vs_rsim import run as run_rsim
    except ImportError as e:
        print(f"dtssl gate twin-vs-rsim needs robosim and dtssl.analysis ({e}); "
              "pip install dtssl[rsim]", file=sys.stderr)
        return 2
    kw = {"mode": args.mode}
    if args.stride is not None:
        kw["stride"] = args.stride
    if args.h_max is not None:
        kw["h_max"] = args.h_max
    run_rsim(**kw)
    return 0


def cmd_cache_convert(args) -> int:
    from dtssl.sim.rollout import convert_pickle_cache, load_rollouts

    npz = convert_pickle_cache(args.pkl, args.npz)
    ros = load_rollouts(npz)
    n_win = sum(r.n_total for r in ros)
    print(f"{args.pkl} -> {npz} (+ {npz.with_suffix('.json').name}): {len(ros)} rollouts, {n_win} windows")
    return 0


# =========================================================================
def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    ap, status = build_parser()
    if argv and argv[0] in _EXTRA_COMMANDS and status.get(_EXTRA_COMMANDS[argv[0]]) is not None:
        mod = _EXTRA_COMMANDS[argv[0]]
        hint = dict(OPTIONAL_CLI_MODULES).get(mod, "")
        print(f"dtssl {argv[0]}: provided by {mod}, which is not available "
              f"({status.get(mod)}). Hint: {hint}", file=sys.stderr)
        return 2
    args = ap.parse_args(argv)
    if not getattr(args, "command", None):
        ap.print_help()
        return 0
    args._optional_status = status
    return int(args.func(args) or 0)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
