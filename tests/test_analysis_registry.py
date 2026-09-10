"""Every registered analysis imports cleanly (robosim lazily), exposes run/main and metadata,
and the CLI registers ``analysis``/``fig`` (no dataset needed)."""
from __future__ import annotations

import argparse
import inspect

import pytest

from dtssl import analysis
from dtssl.analysis import REGISTRY, load, names
from dtssl.analysis import cli as acli
from dtssl.analysis.common import parse_kv


@pytest.mark.parametrize("name", sorted(REGISTRY))
def test_registered_module_contract(name):
    m = load(name)                                      # must import without robosim/h5py
    assert callable(getattr(m, "run", None)), f"{name}: no run()"
    assert callable(getattr(m, "main", None)), f"{name}: no main()"
    sig = inspect.signature(m.run)
    params = sig.parameters
    assert "root" in params and "out" in params, f"{name}: run(root, out, ...) expected"
    assert any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()), f"{name}: run needs **kwargs"
    assert getattr(m, "NAME", None) == name
    assert getattr(m, "KIND", None) in ("analysis", "fig", "report")
    assert isinstance(getattr(m, "CLAIM", ""), str) and m.CLAIM
    assert set(getattr(m, "REQUIRES", ())) <= {"data", "rsim", "rsim_cache", "mat", "mujoco", "net"}
    assert (m.__doc__ or "").strip(), f"{name}: docstring required (claim mapping)"


def test_registry_partition_and_docstring_table():
    figs, reps, ana = set(names("fig")), set(names("report")), set(names("analysis"))
    assert figs | reps | ana == set(REGISTRY)
    assert not (figs & reps) and not (figs & ana) and not (reps & ana)
    for n in REGISTRY:                                  # every entry is documented in the package docstring
        assert f"| {n} |" in analysis.__doc__, f"{n} missing from dtssl.analysis docstring table"


def test_no_hardcoded_paths_or_legacy_imports():
    import pathlib
    pkg = pathlib.Path(analysis.__file__).parent
    bad = ("/sessions/happy-modest-euler", "miniforge3", "py -3 scripts", "from phase0_replay",
           "import phase0_replay.", "C:\\\\Users")
    for f in pkg.glob("*.py"):
        text = f.read_text(encoding="utf-8")
        for token in bad:
            assert token not in text, f"{f.name} still contains {token!r}"


def test_cli_register_and_list(capsys):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command")
    acli.register(sub)
    args = ap.parse_args(["analysis", "list", "--kind", "all"])
    assert args.func(args) == 0
    out = capsys.readouterr().out
    for n in REGISTRY:
        assert n in out
    args = ap.parse_args(["fig", "list"])
    assert args.func(args) == 0
    args = ap.parse_args(["analysis", "info", "clustered_stats"])
    assert args.func(args) == 0
    assert "Fig. 2b" in capsys.readouterr().out


def test_cli_rejects_non_figure_and_unknown(capsys):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command")
    acli.register(sub)
    args = ap.parse_args(["fig", "clustered_stats"])
    assert args.func(args) == 2
    assert acli.run_entry("does_not_exist") == 2


def test_parse_kv():
    kv = parse_kv(["mode=B", "h_ref=24", "latex_copy=true", "label=front_to_back", "x=1.5"])
    assert kv == {"mode": "B", "h_ref": 24, "latex_copy": True, "label": "front_to_back", "x": 1.5}
    with pytest.raises(ValueError):
        parse_kv(["novalue"])


def test_top_level_cli_discovers_analysis():
    from dtssl.cli import build_parser
    ap, status = build_parser()
    assert status.get("dtssl.analysis.cli") is None
    args = ap.parse_args(["analysis", "list"])
    assert callable(args.func)
