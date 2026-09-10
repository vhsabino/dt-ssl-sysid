"""``dtssl analysis`` / ``dtssl fig`` subcommands (registered into ``dtssl.cli``).

    dtssl analysis list [--kind analysis|report|fig|all]
    dtssl analysis run <name> [--root DIR] [--out DIR] [--kw k=v ...]
    dtssl analysis info <name>
    dtssl fig <name> [--root DIR] [--out DIR] [--kw k=v ...]

``--kw`` values are JSON-decoded (``mode=B``, ``h_ref=24``, ``latex_copy=true``)
and forwarded to the module's ``run(root, out, **kwargs)``. Also runnable as
``python -m dtssl.analysis.cli ...``.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from collections.abc import Sequence

from dtssl.analysis import ANALYSES, FIGURES, REGISTRY, REPORTS, info, load
from dtssl.analysis.common import parse_kv

__all__ = ["register", "main", "run_entry", "requirements_missing"]


def requirements_missing(requires: Sequence[str]) -> list[str]:
    """Which of a module's ``REQUIRES`` are not satisfied on this machine."""
    from dtssl.analysis.common import RSIM_CACHE_STEM
    from dtssl.paths import has_dataset, repo_root

    missing = []
    for r in requires:
        if r == "data" and not has_dataset():
            missing.append("data (data/extracted/<dataset>/splits)")
        elif r == "rsim" and importlib.util.find_spec("robosim") is None:
            missing.append("rsim (pip install dtssl[rsim])")
        elif r == "mat" and importlib.util.find_spec("h5py") is None:
            missing.append("mat (pip install dtssl[mat])")
        elif r == "mujoco" and importlib.util.find_spec("mujoco") is None:
            missing.append("mujoco (pip install dtssl[mujoco])")
        elif r == "net":
            # an external simulator listening on the ssl-simulation-protocol ports; only the
            # module itself can tell (ProtocolPlant.open() probes the vision stream and fails
            # with a clear message), so it is never reported as missing here
            continue
        elif r == "rsim_cache":
            try:
                res = repo_root() / "results"
                if not any((res / f"{RSIM_CACHE_STEM}{ext}").is_file() for ext in (".npz", ".pkl")):
                    missing.append("rsim_cache (results/_cache_rsim_rollouts.{npz,pkl})")
            except RuntimeError:
                missing.append("rsim_cache (no repo root)")
    return missing


def _print_list(kind: str) -> None:
    groups = {"analysis": ANALYSES, "report": REPORTS, "fig": FIGURES}
    sel = groups.items() if kind == "all" else [(kind, groups[kind])]
    for k, names in sel:
        print(f"[{k}]")
        for n in names:
            meta = info(n)
            missing = requirements_missing(meta["requires"])
            flag = "" if not missing else f"  [missing: {', '.join(missing)}]"
            req = f" (requires {', '.join(meta['requires'])})" if meta["requires"] else ""
            print(f"  {n:28s} {meta['claim']}{req}{flag}")


def run_entry(name: str, root=None, out=None, kv: Sequence[str] | None = None, **extra) -> int:
    if name not in REGISTRY:
        print(f"unknown analysis {name!r}; run `dtssl analysis list`", file=sys.stderr)
        return 2
    mod = load(name)
    missing = requirements_missing(getattr(mod, "REQUIRES", ()))
    if missing:
        print(f"{name}: missing requirements: {', '.join(missing)}", file=sys.stderr)
        return 3
    kwargs = parse_kv(kv)
    kwargs.update(extra)
    res = mod.run(root=root, out=out, **kwargs)
    path = res.get("path") if isinstance(res, dict) else res
    if path is not None:
        print(f"[{name}] artefact: {path}")
    return 0


# --------------------------------------------------------------------------
def cmd_analysis(args) -> int:
    if args.analysis_cmd == "list":
        _print_list(args.kind)
        return 0
    if args.analysis_cmd == "info":
        meta = info(args.name)
        for k, v in meta.items():
            print(f"{k:9s}: {v}")
        missing = requirements_missing(meta["requires"])
        print(f"missing  : {', '.join(missing) if missing else '-'}")
        print("\n" + (load(args.name).__doc__ or "").strip())
        return 0
    if args.analysis_cmd == "run":
        return run_entry(args.name, args.root, args.out, args.kw)
    print("usage: dtssl analysis {list,run,info} ...", file=sys.stderr)
    return 2


def cmd_fig(args) -> int:
    if args.name == "list":
        _print_list("fig")
        return 0
    if args.name not in FIGURES:
        print(f"{args.name!r} is not a figure generator; figures: {', '.join(FIGURES)}", file=sys.stderr)
        return 2
    return run_entry(args.name, args.root, args.out, args.kw)


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--root", default=None, help="repository root (default: auto-detect)")
    p.add_argument("--out", default=None, help="output directory (default: <root>/results)")
    p.add_argument("--kw", nargs="*", default=[], metavar="k=v",
                   help="extra keyword arguments for run() (JSON-decoded values)")


def register(subparsers) -> None:
    """Register ``analysis`` and ``fig`` into an existing ``add_subparsers()`` object."""
    p = subparsers.add_parser("analysis", help="paper analyses (one command per claim)")
    sp = p.add_subparsers(dest="analysis_cmd", metavar="{list,run,info}")
    pl = sp.add_parser("list", help="list registered analyses")
    pl.add_argument("--kind", choices=("analysis", "report", "fig", "all"), default="all")
    pr = sp.add_parser("run", help="run one analysis")
    pr.add_argument("name", choices=sorted(REGISTRY))
    _add_common(pr)
    pi = sp.add_parser("info", help="show metadata and docstring of one analysis")
    pi.add_argument("name", choices=sorted(REGISTRY))
    p.set_defaults(func=cmd_analysis)

    f = subparsers.add_parser("fig", help="figure generators")
    f.add_argument("name", help="figure name or 'list'")
    _add_common(f)
    f.set_defaults(func=cmd_fig)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="dtssl", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", metavar="<command>")
    register(sub)
    args = ap.parse_args(argv)
    if not getattr(args, "command", None):
        ap.print_help()
        return 0
    return int(args.func(args) or 0)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
