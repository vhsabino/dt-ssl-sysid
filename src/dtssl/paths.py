"""Repository/config/data path resolution for dtssl.

Resolution order for the repository root:
1. ``DTSSL_ROOT`` environment variable (explicit override);
2. first ancestor of the current working directory that contains ``config/twin_params.json``;
3. first ancestor of this file (works for editable installs, where ``src/dtssl`` lives in the repo);
4. the packaged ``dtssl/_config`` fallback for ``config_dir()`` only (installed wheel without repo).

Unlike the old ``phase0_replay.io.repo_root`` this NEVER requires ``data/`` to exist:
configuration must be readable without the DVC dataset.
"""
from __future__ import annotations

import os
from pathlib import Path

_CONFIG_MARKER = Path("config") / "twin_params.json"


def _search_up(start: Path) -> Path | None:
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        if (p / _CONFIG_MARKER).is_file():
            return p
    return None


def repo_root(start: Path | None = None) -> Path:
    """Repository root (directory that contains ``config/twin_params.json``)."""
    env = os.environ.get("DTSSL_ROOT")
    if env:
        p = Path(env).expanduser().resolve()
        if (p / _CONFIG_MARKER).is_file():
            return p
        raise RuntimeError(f"DTSSL_ROOT={env} does not contain {_CONFIG_MARKER}")
    if start is not None:
        found = _search_up(Path(start))
        if found:
            return found
    for candidate in (Path.cwd(), Path(__file__).parent):
        found = _search_up(candidate)
        if found:
            return found
    raise RuntimeError(
        "dtssl repository root not found: set DTSSL_ROOT or run from inside the repo "
        f"(a directory containing {_CONFIG_MARKER})"
    )


def config_dir() -> Path:
    try:
        return repo_root() / "config"
    except RuntimeError:
        pkg = Path(__file__).parent / "_config"
        if pkg.is_dir():
            return pkg
        raise


def config_path(name: str) -> Path:
    """Path of a config file by name, e.g. ``config_path("twin_params.json")``."""
    return config_dir() / name


def data_root() -> Path:
    """``data/extracted`` (may not exist: the dataset is DVC-managed)."""
    env = os.environ.get("DTSSL_DATA")
    return Path(env).expanduser().resolve() if env else repo_root() / "data" / "extracted"


def models_dir() -> Path:
    return repo_root() / "models"


def results_dir() -> Path:
    p = repo_root() / "results"
    p.mkdir(parents=True, exist_ok=True)
    return p


def has_dataset(dataset: str = "2026-05-18_19-2-15") -> bool:
    return (data_root() / dataset / "splits").is_dir()
