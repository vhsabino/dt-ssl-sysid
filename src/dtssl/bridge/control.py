"""``ControlServer``: ``RobotControl`` datagrams (one UDP socket per team) -> ``World.set_command``.

Protocol (ssl-simulation-protocol, checked against ssl-unification ``SimulationUtils.h``):

* blue robots on ``control.port_blue`` (10301), yellow on ``control.port_yellow`` (10302);
* each ``RobotCommand`` carries a ``move_command`` oneof:
  ``local_velocity(forward, left, angular)`` = body frame = :class:`RobotCmd` directly;
  ``global_velocity(x, y, angular)`` is rotated into the body frame with the robot's *current*
  heading; ``wheel_velocity`` is converted with the wheel kinematics (see
  :func:`proto_wheels_to_body` for the wheel order mapping);
* ``kick_speed`` [m/s], ``kick_angle`` [deg] (0 = flat, 45 = chip in ssl-unification) and
  ``dribbler_speed`` [rpm] map 1:1 to :class:`RobotCmd`;
* **every** datagram is answered to its source address with a ``RobotControlResponse`` whose
  ``feedback[]`` lists ``(id, dribbler_ball_contact)`` for the robots it commanded
  (ssl-unification turns it into ``Telemetry`` = "has ball");
* malformed datagrams are counted, logged (rate-limited) and ignored; ids outside ``[0, 15]``
  are reported in ``errors[]``.
"""
from __future__ import annotations

import logging
import math
import socket
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from google.protobuf.message import DecodeError

from dtssl.bridge.config import BridgeConfig, as_bridge_config
from dtssl.bridge.proto import RobotControl, RobotControlResponse
from dtssl.sim.entities import MAX_ROBOTS, TEAMS, RobotCmd, WorldState
from dtssl.sim.twin_world import WHEEL_RADIUS, wheels_to_body

log = logging.getLogger(__name__)

#: ``MoveWheelVelocity`` field order (front_right, back_right, back_left, front_left) -> index
#: into the dtssl wheel order ``phi = (60, 135, 225, 300)`` deg = (front_left, back_left,
#: back_right, front_right). I.e. proto wheel k corresponds to dtssl wheel PROTO_WHEEL_ORDER[k].
PROTO_WHEEL_ORDER: tuple[int, int, int, int] = (3, 2, 1, 0)


def proto_wheels_to_body(front_right: float, back_right: float, back_left: float,
                         front_left: float, wheel_radius: float = WHEEL_RADIUS) -> tuple[float, float, float]:
    """``MoveWheelVelocity`` (wheel *surface* speeds in m/s, positive = CCW tangent as in
    spec §3) -> body velocity ``(vx, vy, w)`` by least squares.

    Mapping: proto (front_right, back_right, back_left, front_left) = dtssl phi (300, 225, 135,
    60) deg, i.e. the reversed dtssl order. Surface speed / wheel radius = wheel rad/s.
    """
    proto = (front_right, back_right, back_left, front_left)
    wheels_rad_s = [0.0] * 4
    for k, idx in enumerate(PROTO_WHEEL_ORDER):
        wheels_rad_s[idx] = float(proto[k]) / wheel_radius
    return wheels_to_body(wheels_rad_s)


def robot_command_to_cmd(rc, theta: float | None) -> RobotCmd:
    """Convert one ``RobotCommand`` message into a :class:`RobotCmd` (body frame).

    ``theta`` is the robot's current heading (needed for ``global_velocity``; ``None`` -> 0).
    """
    cmd = RobotCmd()
    if rc.HasField("move_command"):
        mc = rc.move_command
        which = mc.WhichOneof("command")
        if which == "local_velocity":
            lv = mc.local_velocity
            cmd.vx, cmd.vy, cmd.w = float(lv.forward), float(lv.left), float(lv.angular)
        elif which == "global_velocity":
            gv = mc.global_velocity
            th = 0.0 if theta is None else float(theta)
            c, s = math.cos(th), math.sin(th)
            cmd.vx = c * gv.x + s * gv.y
            cmd.vy = -s * gv.x + c * gv.y
            cmd.w = float(gv.angular)
        elif which == "wheel_velocity":
            wv = mc.wheel_velocity
            cmd.vx, cmd.vy, cmd.w = proto_wheels_to_body(wv.front_right, wv.back_right,
                                                         wv.back_left, wv.front_left)
    if rc.HasField("kick_speed"):
        cmd.kick_speed = max(0.0, float(rc.kick_speed))
    if rc.HasField("kick_angle"):
        cmd.kick_angle_deg = float(rc.kick_angle)
    if rc.HasField("dribbler_speed"):
        cmd.dribbler_rpm = max(0.0, float(rc.dribbler_speed))
    return cmd


@dataclass
class TeamPortStats:
    packets: int = 0
    bytes: int = 0
    commands: int = 0
    responses: int = 0
    parse_errors: int = 0
    invalid_ids: int = 0
    resets: int = 0                     # ConnectionResetError on recvfrom (Windows ICMP port unreachable), ignored
    last_addr: tuple[str, int] | None = None
    last_recv: float = 0.0
    port: int = 0


@dataclass
class ControlStats:
    blue: TeamPortStats = field(default_factory=TeamPortStats)
    yellow: TeamPortStats = field(default_factory=TeamPortStats)

    def of(self, team: str) -> TeamPortStats:
        return self.blue if team == "blue" else self.yellow

    def as_dict(self) -> dict:
        return {t: vars(self.of(t)).copy() for t in TEAMS}


class ControlServer:
    """Two UDP sockets (blue/yellow), one receive thread each, replying to every datagram."""

    def __init__(self, world, config: BridgeConfig | dict | None = None, *,
                 state_provider: Callable[[], WorldState] | None = None,
                 recv_timeout: float = 0.05, log_every: int = 50):
        self.world = world
        self.cfg = as_bridge_config(config).control
        self.state_provider = state_provider or world.state
        self.recv_timeout = float(recv_timeout)
        self.log_every = int(log_every)
        self.stats = ControlStats()
        self.socks: dict[str, socket.socket] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._stop = threading.Event()
        self.running = False

    # ------------------------------------------------------------------ lifecycle
    def start(self, threaded: bool = True) -> None:
        if self.running:
            return
        self._stop.clear()
        for team in TEAMS:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.cfg.bind_ip, self.cfg.port_of(team)))
            s.settimeout(self.recv_timeout)
            self.socks[team] = s
            self.stats.of(team).port = s.getsockname()[1]
        self.running = True
        if threaded:
            for team in TEAMS:
                t = threading.Thread(target=self._loop, args=(team,), name=f"dtssl-control-{team}", daemon=True)
                self._threads[team] = t
                t.start()
        log.info("control: blue on %s:%d, yellow on %s:%d", self.cfg.bind_ip, self.port("blue"),
                 self.cfg.bind_ip, self.port("yellow"))

    def stop(self) -> None:
        self._stop.set()
        for t in self._threads.values():
            t.join(timeout=1.0)
        self._threads.clear()
        for s in self.socks.values():
            try:
                s.close()
            except OSError:
                pass
        self.socks.clear()
        self.running = False

    def port(self, team: str) -> int:
        s = self.socks.get(team)
        return s.getsockname()[1] if s is not None else self.cfg.port_of(team)

    # ------------------------------------------------------------------ receive
    def _loop(self, team: str) -> None:
        sock = self.socks[team]
        while not self._stop.is_set():
            try:
                data, addr = sock.recvfrom(65535)
            except TimeoutError:
                continue
            except ConnectionResetError:
                # Windows (WSAECONNRESET): an ICMP "port unreachable" from a client whose port went away after we
                # answered it; the socket itself is fine -- a break here would silently deafen the server
                self.stats.of(team).resets += 1
                continue
            except OSError:
                if self._stop.is_set():
                    break
                log.warning("control %s: recvfrom failed; retrying", team, exc_info=True)
                time.sleep(0.01)
                continue
            self._process(team, data, addr, sock)

    def poll(self, max_packets: int = 64) -> int:
        """Drain pending datagrams without threads (step mode). Returns the number handled."""
        n = 0
        for team, sock in self.socks.items():
            sock.setblocking(False)
            try:
                for _ in range(max_packets):
                    try:
                        data, addr = sock.recvfrom(65535)
                    except (BlockingIOError, InterruptedError):
                        break
                    except ConnectionResetError:          # Windows, see _loop
                        self.stats.of(team).resets += 1
                        continue
                    except OSError:
                        break
                    self._process(team, data, addr, sock)
                    n += 1
            finally:
                sock.settimeout(self.recv_timeout)
        return n

    def _process(self, team: str, data: bytes, addr, sock) -> None:
        st = self.stats.of(team)
        st.packets += 1
        st.bytes += len(data)
        st.last_addr = addr
        st.last_recv = time.monotonic()
        resp = self.handle_datagram(team, data)
        if resp is None:
            return
        try:
            sock.sendto(resp.SerializeToString(), addr)
            st.responses += 1
        except OSError as e:
            log.debug("control: reply to %s failed: %s", addr, e)

    def handle_datagram(self, team: str, data: bytes) -> RobotControlResponse | None:
        """Parse one ``RobotControl`` datagram, apply the commands, build the response.

        Returns ``None`` for malformed input (logged, ignored).
        """
        st = self.stats.of(team)
        msg = RobotControl()
        try:
            msg.ParseFromString(data)
        except (DecodeError, Exception) as e:  # noqa: BLE001 - any parser failure is "malformed"
            st.parse_errors += 1
            if st.parse_errors == 1 or st.parse_errors % self.log_every == 0:
                log.warning("control[%s]: malformed RobotControl (%d so far): %s", team, st.parse_errors, e)
            return None
        return self.apply(team, msg)

    def apply(self, team: str, msg: RobotControl) -> RobotControlResponse:
        st = self.stats.of(team)
        resp = RobotControlResponse()
        ws = None
        try:
            ws = self.state_provider()
        except Exception as e:  # noqa: BLE001
            log.debug("control: state provider failed: %s", e)
        for rc in msg.robot_commands:
            rid = int(rc.id)
            if rid < 0 or rid >= MAX_ROBOTS:
                st.invalid_ids += 1
                err = resp.errors.add()
                err.code = "INVALID_ROBOT_ID"
                err.message = f"robot id {rid} outside [0, {MAX_ROBOTS - 1}]"
                continue
            rs = ws.robots.get((team, rid)) if ws is not None else None
            theta = rs.theta if rs is not None else None
            cmd = robot_command_to_cmd(rc, theta)
            cmd.t_recv = time.monotonic()
            self.world.set_command(team, rid, cmd)
            st.commands += 1
            fb = resp.feedback.add()
            fb.id = rid
            fb.dribbler_ball_contact = bool(rs.has_ball) if rs is not None else False
        return resp


__all__ = ["ControlServer", "ControlStats", "TeamPortStats", "robot_command_to_cmd",
           "proto_wheels_to_body", "PROTO_WHEEL_ORDER"]
