"""dtssl.paths / dtssl.config: repository root override and config loading WITHOUT the dataset."""
import json
import shutil
from pathlib import Path

import pytest

from dtssl import paths
from dtssl.config import (
    FIELD_PRESETS,
    FieldPreset,
    field_presets,
    load_bridge_config,
    load_field,
    load_field_preset,
    load_geometry,
    load_holdout_config,
    load_limits,
    load_metrics_config,
    load_twin_params,
    reload,
)
from dtssl.sim.world import FieldGeometry, RobotSpec

CONFIG_FILES = ("twin_params.json", "metrics.json", "holdout_events.json", "robot_geometry.json",
                "robot_limits.json", "field_divB.json", "field_divA.json", "bridge.json")


def test_repo_root_and_config_files_exist():
    root = paths.repo_root()
    assert (root / "config" / "twin_params.json").is_file()
    for name in CONFIG_FILES:
        assert paths.config_path(name).is_file(), name


def test_dtssl_root_override(tmp_path, monkeypatch):
    fake = tmp_path / "repo"
    (fake / "config").mkdir(parents=True)
    for name in CONFIG_FILES:
        shutil.copy(paths.config_path(name), fake / "config" / name)
    monkeypatch.setenv("DTSSL_ROOT", str(fake))
    monkeypatch.delenv("DTSSL_DATA", raising=False)          # default data root = <root>/data/extracted
    assert paths.repo_root() == fake.resolve()
    assert paths.config_path("metrics.json") == fake.resolve() / "config" / "metrics.json"
    assert paths.data_root() == fake.resolve() / "data" / "extracted"
    assert paths.has_dataset() is False                     # no data/ under the fake root
    # configs still load (data-free)
    reload()
    assert load_metrics_config()["horizons"] == [6, 12, 24, 42, 60, 90]
    assert set(load_twin_params()) == {"vx", "vy", "w"}
    # an invalid override is an explicit error, not a silent fallback
    monkeypatch.setenv("DTSSL_ROOT", str(tmp_path / "nowhere"))
    with pytest.raises(RuntimeError):
        paths.repo_root()


def test_dtssl_data_override(tmp_path, monkeypatch):
    monkeypatch.setenv("DTSSL_DATA", str(tmp_path / "nonexistent"))
    assert paths.data_root() == (tmp_path / "nonexistent").resolve()
    assert paths.has_dataset() is False
    # every loader works without the dataset
    assert load_twin_params()["vx"].K > 0
    assert load_metrics_config()["verdict"]["h_ref"] == 24
    assert load_holdout_config()["events"][0]["event"] == "front_to_back_01_01"


def test_typed_loaders():
    g = load_geometry()
    assert g.R_contact_m == pytest.approx(0.079601) and g.wheel_radius_m == pytest.approx(0.029492)
    assert g.wheel_angles_deg == (60.0, 135.0, 225.0, 300.0) and g.body_radius_m == pytest.approx(0.09)
    spec, ball, dz = load_limits()
    assert isinstance(spec, RobotSpec) and spec.v_max == 3.0 and spec.w_max == 10.0 and spec.a_max is None
    assert ball["radius"] == pytest.approx(0.0215) and ball["mass"] == pytest.approx(0.046)
    assert dz["enabled"] is False and dz["wheel_min_speed_rad_s"] == pytest.approx(1.567)
    f = load_field()
    assert isinstance(f, FieldGeometry) and f.length == 9.0 and f.width == 6.0 and f.goal_depth == 0.18
    assert f.to_mm()["length"] == 9000
    b = load_bridge_config()
    assert b["control"]["port_blue"] == 10301 and b["vision"]["ip"] == "224.5.23.2"


def test_cache_returns_copies_and_reload_sees_edits(tmp_path):
    m1 = load_metrics_config()
    m1["horizons"].append(999)
    assert 999 not in load_metrics_config()["horizons"]      # caller mutation does not leak
    p = tmp_path / "metrics.json"
    p.write_text(json.dumps({"horizons": [1, 2], "bootstrap": {"seed": 1}}), encoding="utf-8")
    assert load_metrics_config(p)["horizons"] == [1, 2]
    p.write_text(json.dumps({"horizons": [3], "bootstrap": {"seed": 1}}), encoding="utf-8")
    import os
    os.utime(p, (os.stat(p).st_atime, os.stat(p).st_mtime + 5))   # force a new mtime
    assert load_metrics_config(p)["horizons"] == [3]             # mtime-keyed cache
    reload()
    assert load_metrics_config(p)["horizons"] == [3]
    with pytest.raises(FileNotFoundError):
        load_metrics_config(tmp_path / "missing.json")


def test_config_path_is_absolute():
    assert Path(paths.config_path("metrics.json")).is_absolute()


def test_field_presets_follow_the_ssl_divisions(tmp_path):
    """Division B (default) and Division A presets: rulebook geometry plus the robots a team fields."""
    presets = field_presets()
    assert [p.name for p in presets] == list(FIELD_PRESETS) == ["divB", "divA"]
    b, a = presets
    assert isinstance(b, FieldPreset) and b.label == "Div B" and b.division == "B" and b.robots_per_team == 6
    assert (b.field.length, b.field.width, b.field.goal_width) == (9.0, 6.0, 1.0)
    assert b.field == load_field() == load_field_preset().field              # the default field is Division B
    assert a.label == "Div A" and a.division == "A" and a.robots_per_team == 11
    assert (a.field.length, a.field.width, a.field.goal_width, a.field.goal_depth) == (12.0, 9.0, 1.8, 0.18)
    assert (a.field.penalty_area_width, a.field.penalty_area_depth) == (3.6, 1.8)
    assert a.field.goal_center_to_penalty_mark == 8.0 and a.field.boundary_width == 0.3
    assert a.field.center_circle_radius == b.field.center_circle_radius == 0.5
    assert "robots_per_team" not in a.field.to_mm()                          # not a geometry field (vision packet)
    for alias in ("divA", "DIVA", "div-a", "A", "Division A", "div_a"):
        assert load_field_preset(alias) == a, alias
    # a custom field JSON (mm) is a preset too: named after the file, 6 robots per team unless the key is given
    p = tmp_path / "field_lab.json"
    p.write_text(json.dumps({"field_length": 4000, "field_width": 3000, "goal_width": 700, "goal_depth": 180,
                             "boundary_width": 200}), encoding="utf-8")
    c = load_field_preset(p)
    assert c.name == c.label == "field_lab" and c.division is None and c.robots_per_team == 6
    assert (c.field.length, c.field.width, c.field.goal_width, c.field.boundary_width) == (4.0, 3.0, 0.7, 0.2)
    assert c.field.penalty_area_depth == FieldGeometry().penalty_area_depth     # missing keys keep the defaults
    assert load_field_preset(str(p)) == c
    with pytest.raises(FileNotFoundError):
        load_field_preset(tmp_path / "missing.json")
