"""Typed loaders for the JSON configs in ``config/`` (resolved through ``dtssl.paths``).

All loaders are cached (``functools.lru_cache`` keyed by resolved path + mtime, so an edited
file is re-read automatically) and return fresh copies, so callers may mutate the result
without poisoning the cache. ``reload()`` drops every cached entry.

    geom = load_geometry()                      # RobotGeometry (robot_geometry.json + robot_limits.json)
    spec, ball, deadzone = load_limits()        # RobotSpec, ball dict, deadzone dict (robot_limits.json)
    field = load_field()                        # FieldGeometry in metres (field_divB.json is in mm)
    preset = load_field_preset("divA")          # FieldPreset: geometry + robots per team of an SSL division
    bridge = load_bridge_config()               # dict (bridge.json)
    mcfg = load_metrics_config()                # dict (metrics.json)
    theta = load_twin_params()                  # dict[str, DofParam] (twin_params.json; re-export)
"""
from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

from dtssl.geometry import RobotGeometry
from dtssl.models.params import DofParam, load_twin_params  # noqa: F401  (re-export)
from dtssl.paths import config_path
from dtssl.sim.world import FieldGeometry, RobotSpec

__all__ = [
    "load_geometry", "load_limits", "load_field", "load_bridge_config", "load_metrics_config",
    "load_holdout_config", "load_twin_params", "load_json", "reload", "DofParam",
    "FieldPreset", "FIELD_PRESETS", "DEFAULT_FIELD", "field_presets", "load_field_preset",
]


# --- cached JSON reading ---------------------------------------------------------------
@lru_cache(maxsize=64)
def _read_json_cached(path: str, mtime_ns: int) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _resolve(path: str | Path | None, default_name: str) -> Path:
    return Path(path).expanduser() if path is not None else config_path(default_name)


def load_json(path: str | Path | None, default_name: str) -> dict:
    """Parsed JSON of ``path`` (or ``config/<default_name>``), as a deep copy of the cached object."""
    p = _resolve(path, default_name)
    try:
        mtime = os.stat(p).st_mtime_ns
    except FileNotFoundError as e:
        raise FileNotFoundError(f"config file not found: {p}") from e
    return copy.deepcopy(_read_json_cached(str(p), mtime))


def reload() -> None:
    """Forget every cached config (escape hatch for tests / GUI 'reload' actions)."""
    _read_json_cached.cache_clear()


# --- typed loaders ---------------------------------------------------------------------
def load_geometry(path: str | Path | None = None,
                  limits_path: str | Path | None = None) -> RobotGeometry:
    """``RobotGeometry`` from ``config/robot_geometry.json`` (section ``physical``); chassis
    radius/dribbler offset/height/mass come from ``config/robot_limits.json`` when present."""
    cfg = load_json(path, "robot_geometry.json")
    lp = _resolve(limits_path, "robot_limits.json")
    limits = load_json(lp, "robot_limits.json").get("robot") if lp.is_file() else None
    p = _resolve(path, "robot_geometry.json")
    return RobotGeometry.from_physical_section(
        cfg["physical"], limits, provenance=f"{p.name}: {cfg['physical'].get('provenance', '')}")


def load_limits(path: str | Path | None = None) -> tuple[RobotSpec, dict, dict]:
    """``(RobotSpec, ball, deadzone)`` from ``config/robot_limits.json``.

    ``ball`` and ``deadzone`` are plain dicts (radius/mass/decelerations/restitutions and
    ``enabled``/``wheel_min_speed_rad_s`` respectively).
    """
    cfg = load_json(path, "robot_limits.json")
    robot = dict(cfg.get("robot", {}))
    known = set(RobotSpec.__dataclass_fields__)
    spec = RobotSpec(**{k: v for k, v in robot.items() if k in known})
    ball = {k: v for k, v in cfg.get("ball", {}).items() if not k.startswith("_")}
    dz = {k: v for k, v in cfg.get("deadzone", {}).items() if not k.startswith("_")}
    return spec, ball, dz


def _field_from_json(cfg: dict) -> FieldGeometry:
    """mm JSON with ssl-vision key names (``field_length`` ...) -> FieldGeometry (m); extra keys are ignored."""
    return FieldGeometry.from_mm({k[len("field_"):] if k.startswith("field_") else k: v
                                  for k, v in cfg.items() if not k.startswith("_")})


def load_field(path: str | Path | None = None) -> FieldGeometry:
    """``FieldGeometry`` (metres) from ``config/field_divB.json`` (millimetres), or from ``path``."""
    return _field_from_json(load_json(path, "field_divB.json"))


# --- field presets (SSL divisions) ------------------------------------------------------
@dataclass(frozen=True)
class FieldPreset:
    """A field the GUI / CLI can switch to: the geometry of an SSL division plus how many robots a team fields in
    it (``robots_per_team`` key of the JSON, 6 when absent). ``name`` is the preset key (``divB``, ``divA``) or
    the stem of a custom JSON; ``label`` is what the GUI shows."""

    name: str
    label: str
    path: Path
    field: FieldGeometry
    robots_per_team: int

    @property
    def division(self) -> str | None:
        """``"A"`` / ``"B"`` for the built-in presets, None for a custom file."""
        return self.name[-1].upper() if self.name in FIELD_PRESETS else None


#: preset key -> (GUI label, file under config/). Division B first: it is the default and the RoboCIn division.
FIELD_PRESETS: dict[str, tuple[str, str]] = {"divB": ("Div B", "field_divB.json"),
                                             "divA": ("Div A", "field_divA.json")}
DEFAULT_FIELD = "divB"


def _preset_key(field: str) -> str | None:
    """``divB`` / ``div-b`` / ``B`` / ``Division B`` (any case) -> ``divB``; None when it is not a preset name."""
    norm = "".join(ch for ch in field.lower() if ch.isalnum())
    for key in FIELD_PRESETS:
        div = key[-1].lower()
        if norm in (key.lower(), div, "div" + div, "division" + div):
            return key
    return None


def load_field_preset(field: str | Path | None = None) -> FieldPreset:
    """``FieldPreset`` from a preset name (``divB`` / ``divA``, also ``A``/``B`` or ``Division A``, any case) or
    from the path of a field JSON in millimetres; ``None`` -> :data:`DEFAULT_FIELD`."""
    key = _preset_key(field) if isinstance(field, str) else (DEFAULT_FIELD if field is None else None)
    if key is not None:
        label, fname = FIELD_PRESETS[key]
        path = config_path(fname)
    else:
        path = Path(field).expanduser()
        key = label = path.stem
    cfg = load_json(path, path.name)
    return FieldPreset(key, label, path, _field_from_json(cfg), int(cfg.get("robots_per_team", 6)))


def field_presets() -> list[FieldPreset]:
    """The built-in presets whose JSON exists, in :data:`FIELD_PRESETS` order (Division B first)."""
    out = []
    for key in FIELD_PRESETS:
        try:
            out.append(load_field_preset(key))
        except FileNotFoundError:
            continue
    return out


def load_bridge_config(path: str | Path | None = None) -> dict:
    """``config/bridge.json`` as a dict (vision / control / sim sections)."""
    cfg = load_json(path, "bridge.json")
    return {k: v for k, v in cfg.items() if not k.startswith("_")}


def load_metrics_config(path: str | Path | None = None) -> dict:
    """``config/metrics.json`` (horizons, bins, verdict gates, bootstrap) as a dict."""
    return load_json(path, "metrics.json")


def load_holdout_config(path: str | Path | None = None) -> dict:
    """``config/holdout_events.json`` (frozen hold-out list) as a dict."""
    return load_json(path, "holdout_events.json")


def default_robot_spec() -> RobotSpec:
    """RobotSpec with the SPEC defaults (no file access)."""
    return replace(RobotSpec())
