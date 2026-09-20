#!/usr/bin/env python3
"""Generate ssl-unification ``config/local/config.json`` pointed at the dtssl twin.

Only the Python standard library is used. The generator starts from a *shared* profile
(default ``config/shared/ronaldinho/config.json``) and rewrites the handful of keys that
select the simulator transport, the vision socket, the team colour, the referee and the
per-robot behaviour. Every other parameter of the profile is preserved verbatim.

Key paths rewritten (verified against the ssl-unification sources on 2026-09-02 —
``MainWindow.cpp::loadEvent`` reads ``<project>/config/local/config.{ini,json}``;
``ModuleBox::loadSettings`` uses ``comboBox``; ``Parameters::JsonHandler`` stores every
leaf as ``{"Value": "<text>"}`` and conditional sub-trees under ``"Conditional"``):

  MainWindow.CommunicationBase.comboBox                                   = "CommunicationSim"
  MainWindow.CommunicationBase.ParametersDialog.CommunicationSim
      .Communication.Port.Value                                           = 10301 (blue) | 10302 (yellow)
      .Communication."Using Hostname".Value                               = "false"
      .Communication."Using Hostname".Conditional.false.IP.Value          = --sim-ip (127.0.0.1)
      .Replacement.{IP,Port}.Value                                        = --sim-ip, 10300
      .Replacement.Enable.Value                                           = "true"
  MainWindow.VisionBase.comboBox                                          = "DataWorld"
  MainWindow.VisionBase.ParametersDialog.DataWorld
      .PacketType.Value = "Raw"; .Raw.IP.Value = --vision-ip; .Raw.Port.Value = --vision-port
      .TeamColor.Value = "Blue" | "Yellow"; .AttackingSide.Value = --attacking-side
  MainWindow.Environment.ParametersDialog.Environment.General.INET.Value  = --inet (lo)
  MainWindow.RefereeBase.comboBox                                         = "CustomRef"
  MainWindow.RefereeBase.ParametersDialog.CustomRef.Command.Value         = "Referee_Command_FORCE_START"
  MainWindow.RobotNN."BehaviorBase NN".comboBox                           = --behavior for NN < --n-robots, else "TurnedOff"

Ports follow the RoboCup ssl-simulation-protocol convention used by ``dtssl serve``
(``config/bridge.json``): 10300 simulation control, 10301 blue, 10302 yellow; vision
multicast 224.5.23.2:10006 (the ``develop``/``ronaldinho`` profiles already listen on 10006;
the C++ default would be 10020).

Examples
--------
  python tools/ssl_unification/make_local_config.py --ssl-unification ~/ssl-unification --team yellow
  python tools/ssl_unification/make_local_config.py --ssl-unification ~/ssl-unification --team blue \
      --n-robots 6 --behavior Player --dry-run
  # twin running on the Windows host, strategy in WSL2 (NAT): point the simulator at the host IP
  python tools/ssl_unification/make_local_config.py --ssl-unification ~/ssl-unification --team blue \
      --sim-ip "$(ip route | awk '/default/ {print $3}')" --inet eth0
"""
from __future__ import annotations

import argparse
import copy
import difflib
import json
import shutil
import sys
from pathlib import Path

MAX_ROBOTS = 16                      # src/main.cpp: MAX_ROBOTS = 16
BEHAVIORS = ("Player", "Debug", "MouseAndKeyboard")
CONTROL_PORT = {"blue": 10301, "yellow": 10302}
SIMCONTROL_PORT = 10300
TEAM_COLOR = {"blue": "Blue", "yellow": "Yellow"}


def _leaf(node: dict, *keys: str) -> dict:
    """Descend creating dicts; return the innermost dict (the ``{"Value": ...}`` holder)."""
    for k in keys:
        nxt = node.get(k)
        if not isinstance(nxt, dict):
            nxt = {}
            node[k] = nxt
        node = nxt
    return node


def _set_value(node: dict, *keys: str, value) -> None:
    _leaf(node, *keys)["Value"] = str(value)


def _module(mw: dict, name: str, combo: str) -> dict:
    mod = mw.setdefault(name, {})
    mod["comboBox"] = combo
    return mod.setdefault("ParametersDialog", {})


def robot_key(i: int) -> str:
    return f"Robot{i:02d}"


def base_key(prefix: str, i: int) -> str:
    return f"{prefix} {i:02d}"


def build_config(base: dict, *, team: str, vision_ip: str, vision_port: int, inet: str,
                 n_robots: int, behavior: str, sim_ip: str, attacking_side: str | None,
                 control_port: int | None = None, simcontrol_port: int = SIMCONTROL_PORT) -> dict:
    cfg = copy.deepcopy(base)
    mw = cfg.setdefault("MainWindow", {})

    # --- CommunicationBase -> CommunicationSim (ssl-simulation-protocol RobotControl) ---
    comm = _module(mw, "CommunicationBase", "CommunicationSim")
    sim = comm.setdefault("CommunicationSim", {})
    port = control_port if control_port is not None else CONTROL_PORT[team]
    _set_value(sim, "Communication", "Port", value=port)
    uh = _leaf(sim, "Communication", "Using Hostname")
    uh["Value"] = "false"
    _set_value(uh, "Conditional", "false", "IP", value=sim_ip)
    _leaf(uh, "Conditional", "true", "Hostname").setdefault("Value", "simulator")
    _set_value(sim, "Replacement", "IP", value=sim_ip)
    _set_value(sim, "Replacement", "Port", value=simcontrol_port)
    en = _leaf(sim, "Replacement", "Enable")
    en["Value"] = "true"
    _leaf(en, "Conditional", "true", "Robot Angle").setdefault("Value", "0.00")

    # --- VisionBase -> DataWorld (SSL_WrapperPacket raw multicast) ---
    vis = _module(mw, "VisionBase", "DataWorld")
    dw = vis.setdefault("DataWorld", {})
    _set_value(dw, "PacketType", value="Raw")
    _set_value(dw, "Raw", "IP", value=vision_ip)
    _set_value(dw, "Raw", "Port", value=vision_port)
    _set_value(dw, "TeamColor", value=TEAM_COLOR[team])
    if attacking_side:
        _set_value(dw, "AttackingSide", value=attacking_side)

    # --- Environment.General.INET: interface used for joinMulticastGroup (Utils::getNetworkInterface) ---
    env = mw.setdefault("Environment", {}).setdefault("ParametersDialog", {})
    _set_value(env, "Environment", "General", "INET", value=inet)

    # --- RefereeBase -> CustomRef, FORCE_START (no game-controller needed) ---
    ref = _module(mw, "RefereeBase", "CustomRef")
    _set_value(ref, "CustomRef", "Command", value="Referee_Command_FORCE_START")
    _leaf(ref, "CustomRef", "Stage").setdefault("Value", "Referee_Stage_NORMAL_FIRST_HALF")

    # --- Robots: 0..n-1 -> behavior, rest -> TurnedOff (DataWorld drops TurnedOff allies) ---
    template = mw.get(robot_key(0))
    for i in range(MAX_ROBOTS):
        rk = robot_key(i)
        if rk not in mw:
            if isinstance(template, dict):
                mw[rk] = _retag_robot(copy.deepcopy(template), 0, i)
            else:
                mw[rk] = {}
        rob = mw[rk]
        bk = base_key("BehaviorBase", i)
        beh = rob.setdefault(bk, {})
        beh["comboBox"] = behavior if i < n_robots else "TurnedOff"
        for prefix, combo in (("NavigationBase", "DefaultNavigation"), ("PlanningBase", "DefaultPlanning")):
            rob.setdefault(base_key(prefix, i), {}).setdefault("comboBox", combo)
    return cfg


def _retag_robot(rob: dict, src: int, dst: int) -> dict:
    """Rename ``XxxBase 00`` sub-keys of a copied robot block to the new index."""
    out = {}
    for k, v in rob.items():
        suffix = f" {src:02d}"
        out[(k[: -len(suffix)] + f" {dst:02d}") if k.endswith(suffix) else k] = v
    return out


def dumps(cfg: dict) -> str:
    # QJsonDocument::Indented sorts keys and uses 4 spaces, which ssl-unification collapses to 2.
    return json.dumps(cfg, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def load_bridge_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--ssl-unification", required=True, type=Path,
                    help="root of the ssl-unification checkout (contains config/shared)")
    ap.add_argument("--team", required=True, choices=("blue", "yellow"))
    ap.add_argument("--base", type=Path, default=None,
                    help="shared profile to start from (default: <ssl-unification>/config/shared/ronaldinho/config.json)")
    ap.add_argument("--bridge-json", type=Path, default=None,
                    help="dtssl config/bridge.json: take vision ip/port and control/simcontrol ports from it")
    ap.add_argument("--vision-ip", default="224.5.23.2")
    ap.add_argument("--vision-port", type=int, default=10006)
    ap.add_argument("--inet", default="lo", help="network interface name for the multicast join (QNetworkInterface name)")
    ap.add_argument("--sim-ip", default="127.0.0.1",
                    help="IP where dtssl serve listens for RobotControl/SimulatorCommand (Windows host IP when the twin runs outside WSL)")
    ap.add_argument("--n-robots", type=int, default=6, help="robots 0..N-1 get --behavior, the rest TurnedOff")
    ap.add_argument("--behavior", default="Player", choices=BEHAVIORS)
    ap.add_argument("--attacking-side", default=None, choices=("Left", "Right"))
    ap.add_argument("--out", type=Path, default=None,
                    help="output config.json (default: <ssl-unification>/config/local/config.json)")
    ap.add_argument("--dry-run", action="store_true", help="print the unified diff against --base and write nothing")
    args = ap.parse_args(argv)

    root = args.ssl_unification.expanduser().resolve()
    base_path = (args.base or root / "config" / "shared" / "ronaldinho" / "config.json").expanduser().resolve()
    if not base_path.is_file():
        print(f"error: base profile not found: {base_path}", file=sys.stderr)
        return 2
    if not 0 <= args.n_robots <= MAX_ROBOTS:
        print(f"error: --n-robots must be in [0, {MAX_ROBOTS}]", file=sys.stderr)
        return 2

    vision_ip, vision_port, control_port, simcontrol_port = args.vision_ip, args.vision_port, None, SIMCONTROL_PORT
    if args.bridge_json:
        bj = load_bridge_json(args.bridge_json.expanduser())
        vision_ip = bj.get("vision", {}).get("ip", vision_ip)
        vision_port = int(bj.get("vision", {}).get("port", vision_port))
        ctl = bj.get("control", {})
        control_port = int(ctl.get(f"port_{args.team}", CONTROL_PORT[args.team]))
        simcontrol_port = int(ctl.get("port_simcontrol", SIMCONTROL_PORT))

    with base_path.open(encoding="utf-8") as fh:
        base = json.load(fh)
    cfg = build_config(base, team=args.team, vision_ip=vision_ip, vision_port=vision_port, inet=args.inet,
                       n_robots=args.n_robots, behavior=args.behavior, sim_ip=args.sim_ip,
                       attacking_side=args.attacking_side, control_port=control_port,
                       simcontrol_port=simcontrol_port)

    out_json = (args.out or root / "config" / "local" / "config.json").expanduser()
    out_ini = out_json.with_suffix(".ini")
    base_ini = base_path.with_suffix(".ini")

    if args.dry_run:
        diff = difflib.unified_diff(dumps(base).splitlines(keepends=True), dumps(cfg).splitlines(keepends=True),
                                    fromfile=str(base_path), tofile=str(out_json))
        sys.stdout.writelines(diff)
        print(f"\n[dry-run] would write {out_json}" + (f" and copy {base_ini} -> {out_ini}" if base_ini.is_file() else ""))
        return 0

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(dumps(cfg), encoding="utf-8")
    if base_ini.is_file():
        shutil.copyfile(base_ini, out_ini)
    print(f"wrote {out_json}")
    if base_ini.is_file():
        print(f"copied {base_ini} -> {out_ini}")
    print(f"team={args.team} control_port={control_port or CONTROL_PORT[args.team]} simcontrol={simcontrol_port} "
          f"sim_ip={args.sim_ip} vision={vision_ip}:{vision_port} inet={args.inet} "
          f"robots 0..{args.n_robots - 1}={args.behavior}, rest TurnedOff")
    return 0


if __name__ == "__main__":
    sys.exit(main())
