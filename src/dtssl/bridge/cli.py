"""CLI of the bridge: ``dtssl serve``, ``dtssl fake-strategy``, ``dtssl proto-build``.

Registered into the main ``dtssl`` parser through ``register(subparsers)`` (see
``dtssl.cli``); also runnable standalone: ``python -m dtssl.bridge.cli serve --help``.
"""
from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from pathlib import Path

log = logging.getLogger(__name__)


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")


# ---------------------------------------------------------------------------- serve
def add_serve_arguments(p: argparse.ArgumentParser) -> None:
    p.add_argument("--backend", default=None, help="world backend (fopdt | ideal | mujoco-*; default from config)")
    p.add_argument("--config", type=Path, default=None, help="bridge config JSON (default config/bridge.json)")
    p.add_argument("--vision-port", type=int, default=None, help="vision UDP port (ssl-unification DataWorld Raw.Port)")
    p.add_argument("--vision-ip", default=None, help="vision multicast group or unicast IP (default 224.5.23.2)")
    p.add_argument("--multicast-if", default=None, help="interface IP for IP_MULTICAST_IF (default 127.0.0.1)")
    p.add_argument("--unicast", action="append", default=None, metavar="HOST:PORT",
                   help="extra unicast vision target (repeatable), e.g. the WSL2 IP")
    p.add_argument("--blue-port", type=int, default=None, help="RobotControl port of the blue team (10301)")
    p.add_argument("--yellow-port", type=int, default=None, help="RobotControl port of the yellow team (10302)")
    p.add_argument("--simcontrol-port", type=int, default=None, help="SimulatorCommand port (10300)")
    p.add_argument("--bind-ip", default=None, help="bind address of the control sockets (default 0.0.0.0)")
    p.add_argument("--n-blue", type=int, default=None)
    p.add_argument("--n-yellow", type=int, default=None)
    p.add_argument("--duration", type=float, default=None, help="stop after S seconds (default: run until Ctrl-C)")
    p.add_argument("--no-realtime", action="store_true", help="step as fast as possible (no sleeping)")
    p.add_argument("--speed", type=float, default=None, help="simulation speed factor (real-time mode)")
    p.add_argument("--rate-hz", type=float, default=None, help="vision/step rate (default 60)")
    p.add_argument("--theta", type=Path, default=None, help="twin_params JSON for the fopdt backend")
    p.add_argument("--saturate", action="store_true", help="enable v_max/w_max saturation in the world")
    p.add_argument("--deadzone", action="store_true", help="enable the firmware per-wheel deadzone")
    p.add_argument("--record", type=Path, default=None, help="directory to write commands/processed_robots parquet")
    p.add_argument("--record-team", default="blue", choices=("blue", "yellow", "both"))
    p.add_argument("--stats-every", type=float, default=5.0, help="log server stats every S seconds (0 = never)")
    p.add_argument("-v", "--verbose", action="store_true")


def build_world_from_args(args, cfg):
    from dtssl.sim.backends import make_world

    opts: dict = {"n_blue": cfg.sim.n_blue, "n_yellow": cfg.sim.n_yellow}
    if getattr(args, "saturate", False):
        opts["saturate"] = True
    if getattr(args, "deadzone", False):
        opts["deadzone"] = True
    if getattr(args, "theta", None):
        from dtssl.models.params import load_twin_params

        opts["params"] = load_twin_params(args.theta)
    return make_world(cfg.sim.backend, **opts)


def cmd_serve(args) -> int:
    from dtssl.bridge.config import BridgeConfig
    from dtssl.bridge.recorder import SessionRecorder
    from dtssl.bridge.server import SimServer

    _setup_logging(args.verbose)
    cfg = BridgeConfig.load(args.config).with_overrides(
        vision_ip=args.vision_ip, vision_port=args.vision_port, multicast_if=args.multicast_if,
        unicast=args.unicast, blue_port=args.blue_port, yellow_port=args.yellow_port,
        simcontrol_port=args.simcontrol_port, bind_ip=args.bind_ip, n_blue=args.n_blue,
        n_yellow=args.n_yellow, backend=args.backend,
        realtime=(False if args.no_realtime else None), speed=args.speed, rate_hz=args.rate_hz)
    world = build_world_from_args(args, cfg)
    recorder = None
    if args.record:
        teams = None if args.record_team == "both" else args.record_team
        recorder = SessionRecorder(teams=teams)
    server = SimServer(world, cfg, step_mode=not cfg.sim.realtime, recorder=recorder)

    stop_flag = {"stop": False}

    def _sig(*_):
        stop_flag["stop"] = True
        server.stop()

    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(s, _sig)
        except (ValueError, OSError):  # not in main thread
            pass

    server.start()
    print(f"dtssl serve: backend={world.name} vision->{server.vision.targets} "
          f"control blue={server.control.port('blue')} yellow={server.control.port('yellow')} "
          f"simcontrol={server.simcontrol.port} mode={'real-time' if cfg.sim.realtime else 'fast-step'}",
          flush=True)
    t0 = time.monotonic()
    t_log = t0
    try:
        if cfg.sim.realtime:
            if args.stats_every and args.stats_every > 0:
                th = server.run_in_thread(args.duration)
                while th.is_alive():
                    th.join(timeout=0.2)
                    now = time.monotonic()
                    if now - t_log >= args.stats_every:
                        t_log = now
                        _print_stats(server)
            else:
                server.run(args.duration)
        else:
            n_max = None if args.duration is None else int(args.duration * cfg.vision.rate_hz)
            while not stop_flag["stop"] and (n_max is None or server.ticks < n_max):
                server.tick()
                now = time.monotonic()
                if args.stats_every and now - t_log >= args.stats_every:
                    t_log = now
                    _print_stats(server)
    finally:
        server.stop()
        if recorder is not None:
            cp, rp = recorder.save(args.record)
            print(f"recorded {len(recorder)} rows ({recorder.duration_s:.1f} s) -> {cp}, {rp}")
    _print_stats(server)
    return 0


def _print_stats(server) -> None:
    st = server.stats
    pk = st["packets"]
    print(f"[stats] t_sim={st['sim_time']:.1f}s ticks={st['ticks']} hz={st['hz_actual']:.1f}/{st['hz_target']:.0f} "
          f"late={st['late_ticks']} pkts vision={pk['vision']} blue={pk['blue']} yellow={pk['yellow']} "
          f"simctl={pk['simcontrol']} watchdog={st['watchdog_hits']} kicks={st['kicks']}", flush=True)


# ---------------------------------------------------------------------------- fake strategy
def add_fake_strategy_arguments(p: argparse.ArgumentParser) -> None:
    p.add_argument("--team", default="yellow", choices=("blue", "yellow"))
    p.add_argument("--robot", type=int, default=0, help="robot id to drive (default 0)")
    p.add_argument("--target", type=float, nargs=2, default=(0.0, 0.0), metavar=("X", "Y"), help="goal point [m]")
    p.add_argument("--target-theta", type=float, default=None, help="goal heading [rad] (default: keep)")
    p.add_argument("--config", type=Path, default=None, help="bridge config JSON for the default ports")
    p.add_argument("--vision-ip", default=None)
    p.add_argument("--vision-port", type=int, default=None)
    p.add_argument("--multicast-if", default=None)
    p.add_argument("--unicast", action="store_true", help="listen on a plain UDP port instead of joining multicast")
    p.add_argument("--control-host", default="127.0.0.1", help="twin host (RobotControl destination)")
    p.add_argument("--control-port", type=int, default=None, help="default: 10301 blue / 10302 yellow from config")
    p.add_argument("--duration", type=float, default=None, help="seconds to run (default: until Ctrl-C)")
    p.add_argument("--kp", type=float, default=2.0)
    p.add_argument("--v-max", type=float, default=1.5)
    p.add_argument("--stop-when-reached", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")


def cmd_fake_strategy(args) -> int:
    from dtssl.bridge.config import BridgeConfig
    from dtssl.bridge.fake_strategy import FakeStrategy

    _setup_logging(args.verbose)
    cfg = BridgeConfig.load(args.config)
    fs = FakeStrategy(args.team, robot_id=args.robot, target=tuple(args.target), target_theta=args.target_theta,
                      vision_ip=args.vision_ip or cfg.vision.ip, vision_port=args.vision_port or cfg.vision.port,
                      multicast_if=args.multicast_if or cfg.vision.multicast_if, unicast=args.unicast,
                      control_host=args.control_host,
                      control_port=args.control_port or cfg.control.port_of(args.team),
                      kp=args.kp, v_max=args.v_max)
    with fs:
        print(f"fake-strategy: team={args.team} robot={args.robot} vision={fs.vision_ip}:{fs.vision_port} "
              f"control={fs.control_host}:{fs.control_port} target={fs.target}", flush=True)
        try:
            st = fs.run(duration=args.duration, stop_when_reached=args.stop_when_reached)
        except KeyboardInterrupt:
            st = fs.stats
    print(f"frames={st['frames']} controls={st['controls_sent']} responses={st['responses']} "
          f"pose={st['last_pose']} dist={st['distance']:.3f} reached={st['reached']} "
          f"has_ball={st['last_feedback'].get(args.robot)}")
    return 0


# ---------------------------------------------------------------------------- proto-build
def cmd_proto_build(args) -> int:
    from dtssl.bridge.proto.build_proto import main as build_main

    argv = ["--check"] if args.check else []
    return build_main(argv)


# ---------------------------------------------------------------------------- registration
def register(subparsers) -> None:
    p = subparsers.add_parser("serve", help="ssl-simulation-protocol server (grSim drop-in) around a twin world")
    add_serve_arguments(p)
    p.set_defaults(func=cmd_serve)

    p = subparsers.add_parser("fake-strategy", help="minimal ssl-unification-like client (GoToPoint) for the twin")
    add_fake_strategy_arguments(p)
    p.set_defaults(func=cmd_fake_strategy)

    p = subparsers.add_parser("proto-build", help="regenerate dtssl.bridge.proto *_pb2.py (needs grpcio-tools)")
    p.add_argument("--check", action="store_true", help="only verify that the committed modules are current")
    p.set_defaults(func=cmd_proto_build)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="dtssl-bridge", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", metavar="<command>")
    register(sub)
    args = ap.parse_args(argv)
    if not getattr(args, "func", None):
        ap.print_help()
        return 2
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
