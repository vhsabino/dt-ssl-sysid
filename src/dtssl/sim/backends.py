"""Backend registry: name -> World factory.

    world = make_world("fopdt")               # behavioral twin (default, published theta)
    world = make_world("ideal")               # ideal kinematics (K=1, tau=0, Td=0)
    world = make_world("mujoco-velocity")     # route (a): FOPDT drives the ego inside MuJoCo
    world = make_world("mujoco-rollers")      # route (b): physical omni wheels with rollers

Factories are imported lazily so optional dependencies (mujoco) are only needed when used.
"""
from __future__ import annotations

from collections.abc import Callable

from dtssl.sim.world import World

_REGISTRY: dict[str, Callable[..., World]] = {}


def register(name: str, factory: Callable[..., World]) -> None:
    _REGISTRY[name] = factory


def available() -> list[str]:
    _ensure_builtin()
    return sorted(_REGISTRY)


def make_world(name: str = "fopdt", **opts) -> World:
    _ensure_builtin()
    try:
        factory = _REGISTRY[name]
    except KeyError as e:
        raise KeyError(f"unknown backend {name!r}; available: {available()}") from e
    return factory(**opts)


def _ensure_builtin() -> None:
    if _REGISTRY:
        return
    from dtssl.sim.twin_world import TwinWorld  # behavioral backends (no optional deps)

    register("fopdt", lambda **o: TwinWorld(plant="fopdt", **o))
    register("ideal", lambda **o: TwinWorld(plant="ideal", **o))
    try:
        from dtssl.physics.mujoco_world import MuJoCoWorld  # optional: needs mujoco

        register("mujoco-velocity", lambda **o: MuJoCoWorld(route="a", **o))
        register("mujoco-rollers", lambda **o: MuJoCoWorld(route="b", **o))
    except Exception:  # pragma: no cover - mujoco absent
        pass
