"""``FakeStrategy``: minimal client that emulates ssl-unification against the twin server.

It joins the vision multicast group (or listens on a unicast port), parses
``SSL_WrapperPacket``, runs a proportional *GoToPoint* for one robot of its team and sends a
``RobotControl`` (``local_velocity`` in the body frame, exactly what
``Simulation::toRobotControl`` does) to the twin's control port at every vision frame, then
reads the ``RobotControlResponse``. Used by the ``requires_net`` tests and as a demo::

    dtssl fake-strategy --team yellow --target 1.0 0.5 --duration 10

Frames are in the ssl-vision convention (mm, rad); commands in m/s, rad/s.
"""
from __future__ import annotations

import logging
import math
import socket
import struct
import time

from google.protobuf.message import DecodeError

from dtssl.bridge.proto import RobotControl, RobotControlResponse, SSL_WrapperPacket

log = logging.getLogger(__name__)

MM_TO_M = 1e-3


def _is_multicast(ip: str) -> bool:
    try:
        return 224 <= int(ip.split(".")[0]) <= 239
    except ValueError:
        return False


def open_vision_socket(ip: str, port: int, multicast_if: str = "127.0.0.1", unicast: bool = False,
                       bind_ip: str | None = None) -> socket.socket:
    """UDP socket receiving ssl-vision packets: joins ``ip`` when it is a multicast group."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except OSError:
            pass
    mcast = _is_multicast(ip) and not unicast
    s.bind((bind_ip if bind_ip is not None else ("" if mcast else "0.0.0.0"), int(port)))
    if mcast:
        mreq = struct.pack("4s4s", socket.inet_aton(ip), socket.inet_aton(multicast_if or "0.0.0.0"))
        s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    return s


class FakeStrategy:
    def __init__(self, team: str = "yellow", *, robot_id: int = 0,
                 target: tuple[float, float] = (0.0, 0.0), target_theta: float | None = None,
                 vision_ip: str = "224.5.23.2", vision_port: int = 10006, multicast_if: str = "127.0.0.1",
                 unicast: bool = False, control_host: str = "127.0.0.1", control_port: int | None = None,
                 kp: float = 2.0, kp_w: float = 3.0, v_max: float = 1.5, w_max: float = 3.0,
                 tolerance: float = 0.05, recv_timeout: float = 0.5,
                 kick_speed: float = 0.0, dribbler_rpm: float = 0.0):
        if team not in ("blue", "yellow"):
            raise ValueError("team must be 'blue' or 'yellow'")
        self.team = team
        self.robot_id = int(robot_id)
        self.target = (float(target[0]), float(target[1]))
        self.target_theta = target_theta
        self.vision_ip = vision_ip
        self._vision_port = int(vision_port)
        self.multicast_if = multicast_if
        self.unicast = bool(unicast)
        self.control_host = control_host
        self.control_port = int(control_port) if control_port is not None else (10301 if team == "blue" else 10302)
        self.kp, self.kp_w, self.v_max, self.w_max = float(kp), float(kp_w), float(v_max), float(w_max)
        self.tolerance = float(tolerance)
        self.recv_timeout = float(recv_timeout)
        self.kick_speed = float(kick_speed)
        self.dribbler_rpm = float(dribbler_rpm)
        self.vision_sock: socket.socket | None = None
        self.control_sock: socket.socket | None = None
        # stats
        self.frames = 0
        self.detections = 0
        self.geometry_packets = 0
        self.controls_sent = 0
        self.responses = 0
        self.decode_errors = 0
        self.last_feedback: dict[int, bool] = {}
        self.last_pose: tuple[float, float, float] | None = None
        self.last_ball: tuple[float, float] | None = None
        self.last_frame_number: int | None = None
        self.frame_gaps = 0
        self.last_cmd: tuple[float, float, float] = (0.0, 0.0, 0.0)
        self.reached = False
        self.distance = math.inf
        self.field_length_mm: int | None = None

    # ------------------------------------------------------------------ sockets
    def open(self) -> FakeStrategy:
        if self.vision_sock is None:
            self.vision_sock = open_vision_socket(self.vision_ip, self._vision_port, self.multicast_if, self.unicast)
            self.vision_sock.settimeout(self.recv_timeout)
        if self.control_sock is None:
            c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            c.bind(("0.0.0.0", 0))
            c.settimeout(self.recv_timeout)
            self.control_sock = c
        return self

    def close(self) -> None:
        for name in ("vision_sock", "control_sock"):
            s = getattr(self, name)
            if s is not None:
                try:
                    s.close()
                except OSError:
                    pass
                setattr(self, name, None)

    def __enter__(self) -> FakeStrategy:
        return self.open()

    def __exit__(self, *exc) -> None:
        self.close()

    @property
    def vision_port(self) -> int:
        if self.vision_sock is not None:
            return self.vision_sock.getsockname()[1]
        return self._vision_port

    # ------------------------------------------------------------------ vision
    def receive(self, timeout: float | None = None) -> SSL_WrapperPacket | None:
        """Next wrapper packet (or ``None`` on timeout / decode error)."""
        if self.vision_sock is None:
            self.open()
        s = self.vision_sock
        assert s is not None
        s.settimeout(self.recv_timeout if timeout is None else timeout)
        try:
            data, _ = s.recvfrom(65535)
        except TimeoutError:
            return None
        pkt = SSL_WrapperPacket()
        try:
            pkt.ParseFromString(data)
        except DecodeError:
            self.decode_errors += 1
            return None
        self.frames += 1
        if pkt.HasField("geometry"):
            self.geometry_packets += 1
            self.field_length_mm = int(pkt.geometry.field.field_length)
        if pkt.HasField("detection"):
            det = pkt.detection
            self.detections += 1
            n = int(det.frame_number)
            if self.last_frame_number is not None and n != self.last_frame_number + 1:
                self.frame_gaps += 1
            self.last_frame_number = n
            if det.balls:
                self.last_ball = (det.balls[0].x * MM_TO_M, det.balls[0].y * MM_TO_M)
            robots = det.robots_blue if self.team == "blue" else det.robots_yellow
            for r in robots:
                if int(r.robot_id) == self.robot_id:
                    self.last_pose = (r.x * MM_TO_M, r.y * MM_TO_M, float(r.orientation))
        return pkt

    # ------------------------------------------------------------------ control law
    def compute_command(self, pose: tuple[float, float, float]) -> tuple[float, float, float]:
        """Proportional GoToPoint in the world frame, rotated to the body frame."""
        x, y, th = pose
        ex, ey = self.target[0] - x, self.target[1] - y
        self.distance = math.hypot(ex, ey)
        if self.distance <= self.tolerance:
            self.reached = True
            vxw = vyw = 0.0
        else:
            vxw, vyw = self.kp * ex, self.kp * ey
            n = math.hypot(vxw, vyw)
            if n > self.v_max:
                vxw, vyw = vxw * self.v_max / n, vyw * self.v_max / n
        c, s = math.cos(th), math.sin(th)
        vx_b = c * vxw + s * vyw
        vy_b = -s * vxw + c * vyw
        w = 0.0
        if self.target_theta is not None:
            e_th = math.atan2(math.sin(self.target_theta - th), math.cos(self.target_theta - th))
            w = max(-self.w_max, min(self.w_max, self.kp_w * e_th))
        self.last_cmd = (vx_b, vy_b, w)
        return self.last_cmd

    def build_control(self, cmd: tuple[float, float, float]) -> RobotControl:
        rc = RobotControl()
        c = rc.robot_commands.add()
        c.id = self.robot_id
        lv = c.move_command.local_velocity
        lv.forward, lv.left, lv.angular = float(cmd[0]), float(cmd[1]), float(cmd[2])
        c.kick_speed = float(self.kick_speed)
        c.kick_angle = 0.0
        c.dribbler_speed = float(self.dribbler_rpm)
        return rc

    def send_control(self, rc: RobotControl) -> None:
        if self.control_sock is None:
            self.open()
        assert self.control_sock is not None
        self.control_sock.sendto(rc.SerializeToString(), (self.control_host, self.control_port))
        self.controls_sent += 1

    def read_response(self, timeout: float | None = None) -> RobotControlResponse | None:
        assert self.control_sock is not None
        self.control_sock.settimeout(self.recv_timeout if timeout is None else timeout)
        try:
            data, _ = self.control_sock.recvfrom(65535)
        except TimeoutError:
            return None
        resp = RobotControlResponse()
        try:
            resp.ParseFromString(data)
        except DecodeError:
            self.decode_errors += 1
            return None
        self.responses += 1
        for fb in resp.feedback:
            self.last_feedback[int(fb.id)] = bool(fb.dribbler_ball_contact)
        return resp

    # ------------------------------------------------------------------ loop
    def step(self, timeout: float | None = None, wait_response: bool = True) -> bool:
        """Receive one vision packet; if it shows our robot, send a control and read the reply.
        Returns True when a control was sent."""
        pkt = self.receive(timeout)
        if pkt is None or not pkt.HasField("detection") or self.last_pose is None:
            return False
        cmd = self.compute_command(self.last_pose)
        self.send_control(self.build_control(cmd))
        if wait_response:
            self.read_response(timeout)
        return True

    def run(self, duration: float | None = None, max_frames: int | None = None,
            stop_when_reached: bool = False, log_every: float = 1.0) -> dict:
        self.open()
        t0 = time.monotonic()
        t_log = t0
        while True:
            now = time.monotonic()
            if duration is not None and now - t0 >= duration:
                break
            if max_frames is not None and self.frames >= max_frames:
                break
            if stop_when_reached and self.reached:
                break
            self.step()
            if log_every > 0 and now - t_log >= log_every:
                t_log = now
                log.info("fake-strategy[%s %d]: frames=%d ctrl=%d resp=%d pose=%s dist=%.3f has_ball=%s",
                         self.team, self.robot_id, self.frames, self.controls_sent, self.responses,
                         None if self.last_pose is None else tuple(round(v, 3) for v in self.last_pose),
                         self.distance, self.last_feedback.get(self.robot_id))
        return self.stats

    @property
    def stats(self) -> dict:
        return {"frames": self.frames, "detections": self.detections, "geometry_packets": self.geometry_packets,
                "controls_sent": self.controls_sent, "responses": self.responses,
                "decode_errors": self.decode_errors, "frame_gaps": self.frame_gaps,
                "last_pose": self.last_pose, "last_ball": self.last_ball, "distance": self.distance,
                "reached": self.reached, "last_feedback": dict(self.last_feedback)}


__all__ = ["FakeStrategy", "open_vision_socket"]
