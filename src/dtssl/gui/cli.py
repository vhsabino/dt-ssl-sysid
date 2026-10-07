"""``dtssl gui`` subcommand (registered into :mod:`dtssl.cli` through ``register``).

    dtssl gui [--backend fopdt] [--mode debug|bridge|replay] [--team yellow]
              [--config config/bridge.json] [--joy-map file.json|preset] ...
    python -m dtssl.gui ...            (same arguments)

This module only needs ``argparse`` so ``dtssl gui --help`` works without PySide6; the GUI
packages are imported when the command runs (a missing extra prints the install hint).
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

from dtssl.sim.entities import ACTIVE_ROBOTS, ROSTER_SIZE

GUI_MODULES = ("PySide6", "pyqtgraph")


def add_gui_arguments(p: argparse.ArgumentParser) -> None:
    p.add_argument("--backend", default="fopdt", help="world backend: fopdt | ideal | mujoco-velocity | mujoco-rollers")
    p.add_argument("--mode", default="debug", choices=("debug", "bridge", "replay"), help="initial mode")
    p.add_argument("--team", default="yellow", choices=("blue", "yellow"), help="team driven by the joystick")
    p.add_argument("--config", type=Path, default=None, help="bridge config JSON (default config/bridge.json)")
    p.add_argument("--joy-map", default=None, metavar="FILE|PRESET",
                   help="joystick map JSON or preset (gamecontroller, dualsense-raw-linux, dualsense-raw-windows)")
    p.add_argument("--n-blue", type=int, default=ROSTER_SIZE, help="robots of the blue roster (ids 0..n-1)")
    p.add_argument("--n-yellow", type=int, default=ROSTER_SIZE, help="robots of the yellow roster")
    p.add_argument("--n-active", type=int, default=ACTIVE_ROBOTS,
                   help="robots per team on the field at start (Division B: 6); the rest wait parked outside the "
                        "walls (Shift+click on the field brings one in, Shift+click on a robot takes it out)")
    p.add_argument("--publish", action="store_true", help="Debug: publish vision through a step-mode SimServer")
    p.add_argument("--no-realtime", action="store_true", help="Bridge: tick the SimServer from the GUI timer")
    p.add_argument("--no-joystick", action="store_true", help="do not probe pygame (keyboard only)")
    p.add_argument("--theta", type=Path, default=None, help="twin_params JSON to start with")
    p.add_argument("--saturate", action="store_true", help="enable v_max/w_max saturation in the world")
    p.add_argument("--deadzone", action="store_true", help="enable the firmware per-wheel deadzone")
    p.add_argument("--dataset", default=None, help="Replay: dataset id under data/extracted")
    p.add_argument("--label", default=None, help="Replay: split label to load at start-up")
    p.add_argument("--event", default=None, help="Replay: event id to load at start-up")
    p.add_argument("--no-3d", action="store_true", help="no 3D anywhere: neither the 3D tab nor the robot view of the Robot tab (pyqtgraph.opengl)")
    p.add_argument("--no-cad", action="store_true", help="3D tab: primitive shapes instead of the CAD meshes")
    p.add_argument("--no-robot-tab", action="store_true", help="do not create the Robot (telemetry) tab")
    p.add_argument("--telemetry", action="store_true",
                   help="Robot tab: listen for real-robot Feedback over the radio multicast (config/telemetry.json)")
    p.add_argument("--telemetry-config", type=Path, default=None, help="telemetry JSON (default config/telemetry.json)")
    p.add_argument("-v", "--verbose", action="store_true")


def missing_gui_modules() -> list[str]:
    return [m for m in GUI_MODULES if importlib.util.find_spec(m) is None]


def cmd_gui(args) -> int:
    missing = missing_gui_modules()
    if missing:
        print(f"dtssl gui needs {', '.join(missing)}: pip install dtssl[gui]", file=sys.stderr)
        return 2
    from dtssl.gui.app import run

    return run(args)


def register(subparsers) -> None:
    p = subparsers.add_parser("gui", help="PySide6 GUI: field view, plots, parameter panel, DualSense debug mode")
    add_gui_arguments(p)
    p.set_defaults(func=cmd_gui)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="dtssl gui", description=__doc__.split("\n")[0])
    add_gui_arguments(ap)
    ap.set_defaults(func=cmd_gui)
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
