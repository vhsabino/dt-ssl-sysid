"""``SimControlServer``: ``SimulatorCommand`` datagrams on ``control.port_simcontrol`` (10300).

Supported (ssl-simulation-protocol ``ssl_simulation_control.proto``):

* ``control.teleport_ball`` — ``x, y, z`` [m], ``vx, vy, vz`` [m/s], ``roll`` (start in the
  rolling phase); missing fields keep the current value;
* ``control.teleport_robot[]`` — ``id.team`` + ``id.id``, ``x, y, orientation`` (missing ->
  current), ``v_x, v_y, v_angular`` (global), ``present`` (missing -> keep; ``True`` adds a
  robot that does not exist yet);
* ``control.simulation_speed`` — accepted and applied through ``speed_setter`` (the SimServer)
  when ``0 < speed <= max_speed`` (10x), otherwise reported in ``errors``;
* ``config`` — ``vision_port`` is forwarded to ``vision_port_setter`` when given; geometry /
  robot specs / realism are acknowledged with an ``UNSUPPORTED`` error entry (the twin keeps
  its own configs).

Every datagram is answered with a ``SimulatorResponse`` (empty ``errors`` on success). The
``by_force`` variants are treated as plain teleports (documented limitation).
"""
from __future__ import annotations

import logging
import socket
import threading
import time
from collections.abc import Callable

from dtssl.bridge.config import BridgeConfig, as_bridge_config
from dtssl.bridge.proto import TEAM_NAME, SimulatorCommand, SimulatorResponse

log = logging.getLogger(__name__)


class SimControlServer:
    def __init__(self, world, config: BridgeConfig | dict | None = None, *,
                 speed_setter: Callable[[float], None] | None = None,
                 vision_port_setter: Callable[[int], None] | None = None,
                 max_speed: float = 10.0, recv_timeout: float = 0.05):
        self.world = world
        self.cfg = as_bridge_config(config).control
        self.speed_setter = speed_setter
        self.vision_port_setter = vision_port_setter
        self.max_speed = float(max_speed)
        self.recv_timeout = float(recv_timeout)
        self.sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.running = False
        self.packets = 0
        self.parse_errors = 0
        self.resets = 0                     # ConnectionResetError on recvfrom (Windows ICMP port unreachable), ignored
        self.teleports_ball = 0
        self.teleports_robot = 0
        self.speed_changes = 0
        self.last_addr: tuple[str, int] | None = None
        self.last_recv = 0.0

    # ------------------------------------------------------------------ lifecycle
    def start(self, threaded: bool = True) -> None:
        if self.running:
            return
        self._stop.clear()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.cfg.bind_ip, int(self.cfg.port_simcontrol)))
        s.settimeout(self.recv_timeout)
        self.sock = s
        self.running = True
        if threaded:
            self._thread = threading.Thread(target=self._loop, name="dtssl-simcontrol", daemon=True)
            self._thread.start()
        log.info("simcontrol: listening on %s:%d", self.cfg.bind_ip, self.port)

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None
        self.running = False

    @property
    def port(self) -> int:
        return self.sock.getsockname()[1] if self.sock is not None else int(self.cfg.port_simcontrol)

    # ------------------------------------------------------------------ receive
    def _loop(self) -> None:
        sock = self.sock
        while not self._stop.is_set() and sock is not None:
            try:
                data, addr = sock.recvfrom(65535)
            except TimeoutError:
                continue
            except ConnectionResetError:
                # Windows (WSAECONNRESET): ICMP "port unreachable" from a client that went away after we replied;
                # the socket is fine (a break would leave the simulator deaf to every later SimulatorCommand)
                self.resets += 1
                continue
            except OSError:
                if self._stop.is_set():
                    break
                log.warning("simcontrol: recvfrom failed; retrying", exc_info=True)
                time.sleep(0.01)
                continue
            self._process(data, addr, sock)

    def poll(self, max_packets: int = 64) -> int:
        sock = self.sock
        if sock is None:
            return 0
        n = 0
        sock.setblocking(False)
        try:
            for _ in range(max_packets):
                try:
                    data, addr = sock.recvfrom(65535)
                except ConnectionResetError:              # Windows, see _loop
                    self.resets += 1
                    continue
                except (BlockingIOError, InterruptedError, OSError):
                    break
                self._process(data, addr, sock)
                n += 1
        finally:
            sock.settimeout(self.recv_timeout)
        return n

    def _process(self, data: bytes, addr, sock) -> None:
        self.packets += 1
        self.last_addr = addr
        self.last_recv = time.monotonic()
        resp = self.handle_datagram(data)
        if resp is None:
            return
        try:
            sock.sendto(resp.SerializeToString(), addr)
        except OSError as e:
            log.debug("simcontrol: reply to %s failed: %s", addr, e)

    def handle_datagram(self, data: bytes) -> SimulatorResponse | None:
        msg = SimulatorCommand()
        try:
            msg.ParseFromString(data)
        except Exception as e:  # noqa: BLE001
            self.parse_errors += 1
            log.warning("simcontrol: malformed SimulatorCommand (%d so far): %s", self.parse_errors, e)
            return None
        return self.apply(msg)

    # ------------------------------------------------------------------ semantics
    def apply(self, msg: SimulatorCommand) -> SimulatorResponse:
        resp = SimulatorResponse()

        def error(code: str, text: str) -> None:
            e = resp.errors.add()
            e.code = code
            e.message = text

        if msg.HasField("control"):
            ctl = msg.control
            if ctl.HasField("teleport_ball"):
                self._teleport_ball(ctl.teleport_ball)
            for tr in ctl.teleport_robot:
                err = self._teleport_robot(tr)
                if err:
                    error(*err)
            if ctl.HasField("simulation_speed"):
                sp = float(ctl.simulation_speed)
                if 0.0 < sp <= self.max_speed:
                    if self.speed_setter is not None:
                        self.speed_setter(sp)
                    self.speed_changes += 1
                else:
                    error("INVALID_SIMULATION_SPEED", f"simulation_speed {sp} not in (0, {self.max_speed}]")
        if msg.HasField("config"):
            cfg = msg.config
            if cfg.HasField("vision_port") and self.vision_port_setter is not None:
                self.vision_port_setter(int(cfg.vision_port))
            if cfg.HasField("geometry") or len(cfg.robot_specs) or cfg.HasField("realism_config"):
                error("UNSUPPORTED", "SimulatorConfig geometry/robot_specs/realism_config are not applied by dtssl")
        return resp

    def _teleport_ball(self, tb) -> None:
        cur = self.world.ball()
        x = tb.x if tb.HasField("x") else cur.x
        y = tb.y if tb.HasField("y") else cur.y
        z = tb.z if tb.HasField("z") else cur.z
        vx = tb.vx if tb.HasField("vx") else 0.0
        vy = tb.vy if tb.HasField("vy") else 0.0
        vz = tb.vz if tb.HasField("vz") else 0.0
        kwargs = {}
        if tb.roll:
            kwargs["rolling"] = True
        try:
            self.world.teleport_ball(float(x), float(y), float(vx), float(vy), float(z), float(vz), **kwargs)
        except TypeError:  # World without the ``rolling`` extension
            self.world.teleport_ball(float(x), float(y), float(vx), float(vy), float(z), float(vz))
        self.teleports_ball += 1

    def _teleport_robot(self, tr) -> tuple[str, str] | None:
        team = TEAM_NAME.get(int(tr.id.team)) if tr.id.HasField("team") else None
        if team is None:
            return ("INVALID_TEAM", "TeleportRobot.id.team must be BLUE or YELLOW")
        rid = int(tr.id.id)
        ws = self.world.state()
        cur = ws.robots.get((team, rid))
        present_known = tr.HasField("present")
        if cur is None and not (present_known and tr.present):
            return ("UNKNOWN_ROBOT", f"robot {team} {rid} is not in the world (send present=true to add it)")
        x = tr.x if tr.HasField("x") else (cur.x if cur else 0.0)
        y = tr.y if tr.HasField("y") else (cur.y if cur else 0.0)
        th = tr.orientation if tr.HasField("orientation") else (cur.theta if cur else 0.0)
        present = bool(tr.present) if present_known else (cur.present if cur else True)
        vx, vy, w = float(tr.v_x), float(tr.v_y), float(tr.v_angular)
        moved = tr.HasField("x") or tr.HasField("y") or tr.HasField("orientation") or cur is None \
            or vx != 0.0 or vy != 0.0 or w != 0.0
        if moved:
            try:
                self.world.teleport_robot(team, rid, float(x), float(y), float(th), present, vx=vx, vy=vy, w=w)
            except TypeError:  # World without velocity kwargs
                self.world.teleport_robot(team, rid, float(x), float(y), float(th), present)
        elif present_known and hasattr(self.world, "set_present"):
            self.world.set_present(team, rid, present)
        else:
            self.world.teleport_robot(team, rid, float(x), float(y), float(th), present)
        self.teleports_robot += 1
        return None

    @property
    def stats(self) -> dict:
        return {"port": self.port, "packets": self.packets, "parse_errors": self.parse_errors, "resets": self.resets,
                "teleports_ball": self.teleports_ball, "teleports_robot": self.teleports_robot,
                "speed_changes": self.speed_changes, "last_addr": self.last_addr}


__all__ = ["SimControlServer"]
