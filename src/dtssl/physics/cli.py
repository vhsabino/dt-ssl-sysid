"""``dtssl mjcf`` — write the generated MJCF models (+ a markdown description) and, optionally,
open the MuJoCo viewer on a live world.

    dtssl mjcf --route a --out models/mjcf/                 # ssl_route_a.xml + ssl_route_a.md
    dtssl mjcf --route b --n-blue 1 --n-yellow 1 --out models/mjcf/
    dtssl mjcf --route a --view --demo                      # passive viewer, robots driven in circles
    dtssl mjcf --route b --view --visual cad                # CAD meshes (RobôCIn v2025) instead of primitives
    dtssl mjcf --route a --field divA --out models/mjcf/    # Division A field (12 x 9 m, 11 robots per team)
    python -m dtssl.physics.cli --route b --out /tmp/mjcf   # same without the dtssl entry point

``--visual cad`` draws the chassis, wheels, kicker and dribbler with the CAD meshes of ``src/dtssl/physics/assets``
(visual-only geoms in their Inventor colours; the physics is the same as with ``--visual primitive``). With
``--out`` the per-colour sub-mesh OBJ files the XML references are written next to it so the model loads
standalone (``mujoco.MjModel.from_xml_path``). ``--dribbler bar`` builds the physical dribbler (sprung spinning
bar + mouth, see ``dtssl.physics.mjcf.DribblerOptions``). ``--field divB|divA|FILE`` picks the field preset
(``dtssl.config.load_field_preset``): geometry of the fragment and, for route a, the division's robots per team
unless ``--n-blue/--n-yellow`` say otherwise; a non-default preset is appended to the file names (``_divA``).

Registered into the main parser through ``register(subparsers)`` (see ``dtssl.cli``). Only the
``--view`` mode needs the ``mujoco`` package; writing the XML does not.
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from collections.abc import Sequence
from pathlib import Path

__all__ = ["register", "main", "cmd_mjcf"]


def register(subparsers) -> None:
    p = subparsers.add_parser("mjcf", help="generate the MuJoCo MJCF models (routes a/b) or open the viewer")
    _add_arguments(p)
    p.set_defaults(func=cmd_mjcf)


def _add_arguments(p: argparse.ArgumentParser) -> None:
    p.add_argument("--route", choices=("a", "b", "both"), default="both",
                   help="a = mujoco-velocity (FOPDT ego + contacts), b = mujoco-rollers (physical wheels)")
    p.add_argument("--out", type=Path, default=None, help="output directory (default models/mjcf/ in the repo)")
    p.add_argument("--field", default=None, metavar="divB|divA|FILE",
                   help="field preset: SSL division (divB = 9 x 6 m, divA = 12 x 9 m) or a field JSON in mm "
                        "(default config/field_divB.json)")
    p.add_argument("--n-blue", type=int, default=None,
                   help="robots per team (default: the division's for route a, 6 in Div B and 11 in Div A; 1 for b)")
    p.add_argument("--n-yellow", type=int, default=None)
    p.add_argument("--n-rollers", type=int, default=None, help="rollers per wheel (route b, default 12)")
    p.add_argument("--no-boundary", action="store_true", help="omit the boundary walls")
    p.add_argument("--visual", choices=("primitive", "cad"), default="primitive",
                   help="primitive = collision shapes drawn as-is; cad = RobôCIn v2025 CAD meshes (visual only)")
    p.add_argument("--dribbler", choices=("spring", "bar"), default="spring",
                   help="spring = pull-in force of the world (default); bar = physical sprung spinning bar + mouth")
    p.add_argument("--view", action="store_true", help="open mujoco.viewer on a live MuJoCoWorld (needs mujoco)")
    p.add_argument("--demo", action="store_true", help="with --view: drive every robot on a slow circle")
    p.add_argument("--seconds", type=float, default=0.0, help="with --view: run for this long (0 = until closed)")


def _preset(field):
    """``FieldPreset`` of ``--field`` (None -> the default, Division B)."""
    from dtssl.config import FieldPreset, load_field_preset

    return field if isinstance(field, FieldPreset) else load_field_preset(field)


def _scene(route: str, n_blue: int | None, n_yellow: int | None, field=None):
    """``Scene.default`` on the field of ``field`` (preset name, JSON path, ``FieldPreset`` or None = Division B);
    without ``n_blue``/``n_yellow`` route a gets the division's robots per team and route b one robot."""
    from dtssl.sim.entities import Scene

    preset = _preset(field)
    fld = preset.field
    nb = (preset.robots_per_team if route == "a" else 1) if n_blue is None else n_blue
    ny = (preset.robots_per_team if route == "a" else 1) if n_yellow is None else n_yellow
    return Scene.default(nb, ny, fld.length, fld.width, boundary_width_m=fld.boundary_width)


def write_models(route: str, out: Path, n_blue: int | None = None, n_yellow: int | None = None,
                 n_rollers: int | None = None, boundary: bool = True, visual: str = "primitive",
                 dribbler: str = "spring", field=None) -> list[Path]:
    """Write ``ssl_route_<r>.xml`` and ``ssl_route_<r>.md`` for each requested route (+ the CAD sub-mesh
    files next to them when ``visual='cad'``). ``field``: preset name / JSON path (None = Division B); a
    non-default preset is appended to the file names."""
    from dataclasses import replace

    from dtssl.config import DEFAULT_FIELD
    from dtssl.physics.mjcf import (
        ASSET_DIR,
        build_world_xml,
        cad_mesh_files,
        describe_xml,
        load_wheel_geometry,
    )

    routes = ("a", "b") if route == "both" else (route,)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    preset = _preset(field)
    suffix = (("" if visual == "primitive" else f"_{visual}") + ("" if dribbler == "spring" else f"_{dribbler}")
              + ("" if preset.name == DEFAULT_FIELD else f"_{preset.name}"))
    for r in routes:
        scene = _scene(r, n_blue, n_yellow, preset)
        wheel = load_wheel_geometry()
        if n_rollers is not None:
            wheel = replace(wheel, n_rollers=int(n_rollers))
        xml = build_world_xml(scene, r, fld=preset.field, wheel=wheel, boundary=boundary, visual=visual,
                              dribbler=dribbler)
        name = "mujoco-velocity" if r == "a" else "mujoco-rollers"
        md = describe_xml(xml, title=f"dtssl MJCF route {r} ({name}) — {len(scene.robots)} robots")
        head = (f"<!-- generated by `dtssl mjcf --route {r} --visual {visual} --dribbler {dribbler} "
                f"--field {preset.name}`; do not edit, regenerate from dtssl.physics.mjcf (config/*.json) -->\n")
        xml_path = out / f"ssl_route_{r}{suffix}.xml"
        md_path = out / f"ssl_route_{r}{suffix}.md"
        xml_path.write_text(head + xml + "\n", encoding="utf-8")
        md_path.write_text(md, encoding="utf-8")
        written += [xml_path, md_path]
        print(f"route {r}: {xml_path} ({xml_path.stat().st_size / 1024:.0f} kB), {md_path}")
    if visual == "cad":
        files = dict(cad_mesh_files())
        files["meshes.json"] = (ASSET_DIR / "meshes.json").read_bytes()      # provenance of the meshes
        for f, data in files.items():
            dst = out / f
            if not dst.exists() or dst.read_bytes() != data:
                dst.write_bytes(data)
            written.append(dst)
        print(f"CAD meshes: {len(files) - 1} sub-mesh OBJ files + meshes.json written to {out}")
    return written


def view(route: str, n_blue: int | None, n_yellow: int | None, n_rollers: int | None, demo: bool,
         seconds: float, boundary: bool = True, visual: str = "primitive", dribbler: str = "spring",
         field=None) -> int:
    """Open ``mujoco.viewer`` on a live ``MuJoCoWorld`` stepped in real time."""
    from dtssl.physics.mujoco_world import MuJoCoWorld
    from dtssl.sim.entities import RobotCmd

    r = "a" if route in ("a", "both") else "b"
    preset = _preset(field)
    scene = _scene(r, n_blue, n_yellow, preset)
    kw = {} if n_rollers is None else {"n_rollers": int(n_rollers)}
    world = MuJoCoWorld(r, scene=scene, field=preset.field, boundary=boundary, watchdog_clock="sim", visual=visual,
                        dribbler=dribbler, **kw)
    handle = world.viewer()
    t0 = time.monotonic()
    k = 0
    try:
        while handle.is_running() and (seconds <= 0 or time.monotonic() - t0 < seconds):
            if demo:
                t = world.t
                for i, key in enumerate(world.robot_keys()):
                    world.set_command(*key, RobotCmd(vx=0.6, w=0.8 * (1 if i % 2 else -1),
                                                     dribbler_rpm=3000.0 if math.sin(t) > 0 else 0.0))
            world.step()
            k += 1
            target = t0 + k * world.ts
            delay = target - time.monotonic()
            if delay > 0:
                time.sleep(delay)
    finally:
        world.close()
    return 0


def cmd_mjcf(args) -> int:
    visual = getattr(args, "visual", "primitive") or "primitive"
    dribbler = getattr(args, "dribbler", "spring") or "spring"
    field = getattr(args, "field", None)
    if args.view:
        return view(args.route, args.n_blue, args.n_yellow, args.n_rollers, args.demo, args.seconds,
                    boundary=not args.no_boundary, visual=visual, dribbler=dribbler, field=field)
    out = args.out
    if out is None:
        from dtssl.paths import repo_root

        out = repo_root() / "models" / "mjcf"
    write_models(args.route, Path(out), args.n_blue, args.n_yellow, args.n_rollers, boundary=not args.no_boundary,
                 visual=visual, dribbler=dribbler, field=field)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="dtssl mjcf", description=__doc__.split("\n\n")[0])
    _add_arguments(ap)
    args = ap.parse_args(list(sys.argv[1:] if argv is None else argv))
    return cmd_mjcf(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
