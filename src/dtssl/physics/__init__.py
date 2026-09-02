"""MuJoCo physics backends of the SSL twin (SPEC §4.6).

* :mod:`dtssl.physics.mjcf` — programmatic MJCF builder (field, ball, robots for routes a/b);
  pure Python, no MuJoCo needed to *generate* the XML.
* :mod:`dtssl.physics.mujoco_world` — ``MuJoCoWorld(World)`` for ``"mujoco-velocity"`` (route a:
  the behavioral plant drives the ego, MuJoCo adds contacts) and ``"mujoco-rollers"`` (route b:
  omni wheels with free rollers). Imports ``mujoco`` lazily (``pip install dtssl[mujoco]``).
* :mod:`dtssl.physics.cli` — ``dtssl mjcf --route a|b --out DIR`` (and ``--view``).

``import dtssl.physics`` never requires the ``mujoco`` package.
"""
from __future__ import annotations

__all__ = ["mujoco_available", "MuJoCoWorld"]


def mujoco_available() -> bool:
    import importlib.util

    return importlib.util.find_spec("mujoco") is not None


def __getattr__(name: str):
    if name == "MuJoCoWorld":  # lazy: only touches mujoco when actually used
        from dtssl.physics.mujoco_world import MuJoCoWorld

        return MuJoCoWorld
    raise AttributeError(name)
