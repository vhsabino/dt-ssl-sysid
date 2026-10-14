"""dtssl.cli: built-in subcommands (info always; replay/cache-convert with the dataset)."""
import io
from contextlib import redirect_stderr, redirect_stdout

import pytest

from dtssl import __version__
from dtssl.cli import OPTIONAL_CLI_MODULES, build_parser, main
from dtssl.paths import repo_root


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = main(argv)
    return rc, out.getvalue(), err.getvalue()


def test_info_runs():
    rc, out, _ = _run(["info"])
    assert rc == 0
    assert f"dtssl {__version__}" in out
    assert str(repo_root()) in out
    assert "dataset" in out and "backends" in out and "extras" in out
    for mod, _hint in OPTIONAL_CLI_MODULES:
        assert mod in out                    # every optional module is reported (ok or missing)


def test_help_and_version():
    rc, out, _ = _run([])
    assert rc == 0 and "usage: dtssl" in out
    with pytest.raises(SystemExit) as e:
        _run(["--version"])
    assert e.value.code == 0


def test_parser_has_builtin_commands():
    ap, status = build_parser(with_optional=False)
    sub = next(a for a in ap._actions if hasattr(a, "choices") and a.choices and "info" in a.choices)
    assert {"info", "replay", "gate", "cache-convert"} <= set(sub.choices)
    assert status == {}


def test_missing_extra_gives_hint(monkeypatch):
    """A command of an optional module that cannot be imported yields a hint, not a traceback."""
    import dtssl.cli as cli
    monkeypatch.setattr(cli, "OPTIONAL_CLI_MODULES", (("dtssl._no_such_cli", "pip install dtssl[x]"),))
    monkeypatch.setattr(cli, "_EXTRA_COMMANDS", {"zzz": "dtssl._no_such_cli"})
    rc, _, err = _run(["zzz"])
    assert rc == 2 and "dtssl[x]" in err and "dtssl._no_such_cli" in err


def test_cache_convert_roundtrip(tmp_path):
    pkl = repo_root() / "results" / "_cache_rsim_rollouts.pkl"
    if not pkl.is_file():
        pytest.skip("legacy pickle cache not present")
    rc, out, _ = _run(["cache-convert", str(pkl), str(tmp_path / "cache.npz")])
    assert rc == 0 and "10 rollouts" in out
    assert (tmp_path / "cache.npz").is_file() and (tmp_path / "cache.json").is_file()


@pytest.mark.requires_data
def test_replay_real_event(tmp_path):
    rc, out, _ = _run(["replay", "side_to_side", "side_to_side_01_05", "--out", str(tmp_path),
                       "--h-max", "30", "--stride", "30"])
    assert rc == 0
    assert "AnalyticFOPDTPlant" in out and "e_pos med" in out
    files = sorted(tmp_path.iterdir())
    assert any(f.suffix == ".csv" for f in files) and any(f.suffix == ".png" for f in files)
    csv = next(f for f in files if f.suffix == ".csv")
    header = csv.read_text(encoding="utf-8").splitlines()[0]
    assert header.startswith("t,cmd_vx,cmd_vy,cmd_w,x_real")
    # ideal plant with a custom theta path ignored, no figure
    rc, out, _ = _run(["replay", "side_to_side", "side_to_side_01_05", "--plant", "ideal",
                       "--out", str(tmp_path / "ideal"), "--no-fig", "--h-max", "30", "--stride", "30"])
    assert rc == 0 and "IdealKinematicPlant" in out
    assert not any(f.suffix == ".png" for f in (tmp_path / "ideal").iterdir())


@pytest.mark.requires_data
def test_replay_custom_theta(tmp_path):
    import json
    from dtssl.paths import config_path
    theta = json.loads(config_path("twin_params.json").read_text(encoding="utf-8"))
    theta["dof"]["w"]["Td"] = 0.0
    p = tmp_path / "theta.json"
    p.write_text(json.dumps(theta), encoding="utf-8")
    rc, out, _ = _run(["replay", "shoot_to_goal", "shoot_to_goal_12_01", "--theta", str(p),
                       "--out", str(tmp_path), "--no-fig", "--h-max", "24", "--stride", "60"])
    assert rc == 0 and str(p) in out
