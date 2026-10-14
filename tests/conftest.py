"""Shared pytest configuration: fixtures directory and dataset-dependent skips.

Markers (see pyproject.toml): requires_data, requires_mujoco, requires_gui, requires_net, requires_rsim.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from dtssl.paths import has_dataset

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _has(mod: str) -> bool:
    return importlib.util.find_spec(mod) is not None


def pytest_collection_modifyitems(config, items):
    skip_data = pytest.mark.skip(reason="dataset data/extracted/<dataset>/splits not available (DVC)")
    skip_mj = pytest.mark.skip(reason="mujoco not installed (pip install dtssl[mujoco])")
    skip_gui = pytest.mark.skip(reason="PySide6/pyqtgraph not installed (pip install dtssl[gui])")
    skip_rsim = pytest.mark.skip(reason="robosim not installed")
    have_data = has_dataset()
    have_mj = _has("mujoco")
    have_gui = _has("PySide6") and _has("pyqtgraph")
    have_rsim = _has("robosim")
    for item in items:
        if "requires_data" in item.keywords and not have_data:
            item.add_marker(skip_data)
        if "requires_mujoco" in item.keywords and not have_mj:
            item.add_marker(skip_mj)
        if "requires_gui" in item.keywords and not have_gui:
            item.add_marker(skip_gui)
        if "requires_rsim" in item.keywords and not have_rsim:
            item.add_marker(skip_rsim)


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES
