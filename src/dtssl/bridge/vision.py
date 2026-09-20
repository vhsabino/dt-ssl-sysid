"""``VisionPublisher``: ``WorldState`` -> ``SSL_WrapperPacket`` (detection + geometry) over UDP.

Wire conventions (docs/SPEC_DTSSL.md §4.4, checked against ssl-unification ``DataWorld.cpp``):

* detection: ``frame_number`` contiguous per camera (the strategy's ``LossDetection`` flags
  gaps/swaps), ``t_capture = t_sent = time.time()``, ``camera_id`` from config; robots and
  ball in **mm**, ``orientation`` in rad wrapped to (-pi, pi], ``confidence = 1.0``,
  ``pixel_x = pixel_y = 0``; ``z`` of the ball = height of its bottom above the floor (mm);
* geometry: **mandatory** for the strategy (it derives the field from it), sent on the first
  frame and every ``geometry_every`` frames, with ``field_lines``/``field_arcs`` of the
  standard Div B markings (so grSim-style visualisers draw them) and the ball model;
* transport: multicast (``IP_MULTICAST_IF``/``TTL``/``LOOP`` from config) plus optional
  unicast targets; ``latency_frames`` delays every packet through a ring buffer; Gaussian
  position/orientation noise is optional (seeded).

``build_packet`` is pure (no socket) so tests can inspect packets; ``publish`` builds and sends.
"""
from __future__ import annotations

import logging
import math
import socket
import time
from collections import deque

import numpy as np

from dtssl.bridge.config import BridgeConfig, VisionConfig, as_bridge_config
from dtssl.bridge.proto import (
    SSL_DetectionFrame,
    SSL_FieldShapeType,
    SSL_GeometryData,
    SSL_WrapperPacket,
)
from dtssl.sim.entities import WorldState
from dtssl.sim.world import FieldGeometry

log = logging.getLogger(__name__)

M_TO_MM = 1000.0


def wrap_to_pi(a: float) -> float:
    return math.atan2(math.sin(a), math.cos(a))


def _vision_config(config) -> VisionConfig:
    if isinstance(config, VisionConfig):
        return config
    if isinstance(config, dict) and "vision" not in config and ("ip" in config or "port" in config):
        known = {k: v for k, v in config.items() if k in VisionConfig.__dataclass_fields__}
        return VisionConfig(**known)
    cfg: BridgeConfig = as_bridge_config(config)
    return cfg.vision


def fill_field_geometry(field_msg, field: FieldGeometry, *, ball_radius_m: float = 0.0215,
                        max_robot_radius_m: float = 0.09, goal_height_mm: int = 155) -> None:
    """Fill an ``SSL_GeometryFieldSize`` message from ``field`` (m) with Div B markings."""
    mm = field.to_mm()
    field_msg.field_length = mm["length"]
    field_msg.field_width = mm["width"]
    field_msg.goal_width = mm["goal_width"]
    field_msg.goal_depth = mm["goal_depth"]
    field_msg.boundary_width = mm["boundary_width"]
    field_msg.penalty_area_depth = mm["penalty_area_depth"]
    field_msg.penalty_area_width = mm["penalty_area_width"]
    field_msg.center_circle_radius = mm["center_circle_radius"]
    field_msg.line_thickness = mm["line_thickness"]
    field_msg.goal_center_to_penalty_mark = mm["goal_center_to_penalty_mark"]
    field_msg.goal_height = int(goal_height_mm)
    field_msg.ball_radius = float(ball_radius_m * M_TO_MM)
    field_msg.max_robot_radius = float(max_robot_radius_m * M_TO_MM)

    hl, hw = mm["length"] / 2.0, mm["width"] / 2.0
    pd, hpw = mm["penalty_area_depth"], mm["penalty_area_width"] / 2.0
    th = float(mm["line_thickness"])
    T = SSL_FieldShapeType
    lines = [
        ("TopTouchLine", (-hl, hw), (hl, hw), T.TopTouchLine),
        ("BottomTouchLine", (-hl, -hw), (hl, -hw), T.BottomTouchLine),
        ("LeftGoalLine", (-hl, -hw), (-hl, hw), T.LeftGoalLine),
        ("RightGoalLine", (hl, -hw), (hl, hw), T.RightGoalLine),
        ("HalfwayLine", (0.0, -hw), (0.0, hw), T.HalfwayLine),
        ("CenterLine", (-hl, 0.0), (hl, 0.0), T.CenterLine),
        ("LeftPenaltyStretch", (-hl + pd, -hpw), (-hl + pd, hpw), T.LeftPenaltyStretch),
        ("RightPenaltyStretch", (hl - pd, -hpw), (hl - pd, hpw), T.RightPenaltyStretch),
        ("LeftFieldLeftPenaltyStretch", (-hl, hpw), (-hl + pd, hpw), T.LeftFieldLeftPenaltyStretch),
        ("LeftFieldRightPenaltyStretch", (-hl, -hpw), (-hl + pd, -hpw), T.LeftFieldRightPenaltyStretch),
        ("RightFieldLeftPenaltyStretch", (hl, -hpw), (hl - pd, -hpw), T.RightFieldLeftPenaltyStretch),
        ("RightFieldRightPenaltyStretch", (hl, hpw), (hl - pd, hpw), T.RightFieldRightPenaltyStretch),
    ]
    del field_msg.field_lines[:]
    del field_msg.field_arcs[:]
    for name, p1, p2, typ in lines:
        seg = field_msg.field_lines.add()
        seg.name = name
        seg.p1.x, seg.p1.y = float(p1[0]), float(p1[1])
        seg.p2.x, seg.p2.y = float(p2[0]), float(p2[1])
        seg.thickness = th
        seg.type = typ
    arc = field_msg.field_arcs.add()
    arc.name = "CenterCircle"
    arc.center.x, arc.center.y = 0.0, 0.0
    arc.radius = float(mm["center_circle_radius"])
    arc.a1, arc.a2 = 0.0, 2.0 * math.pi
    arc.thickness = th
    arc.type = T.CenterCircle


class VisionPublisher:
    """Builds and sends ``SSL_WrapperPacket`` datagrams from :class:`WorldState`."""

    def __init__(self, config, field: FieldGeometry, *, ball_radius: float = 0.0215,
                 robot_radius: float = 0.09, robot_height: float = 0.15, ball_model=None,
                 open_socket: bool = True, seed: int | None = None):
        self.cfg = _vision_config(config)
        self.field = field
        self.ball_radius = float(ball_radius)
        self.robot_radius = float(robot_radius)
        self.robot_height = float(robot_height)
        self.ball_model = ball_model
        self.rng = np.random.default_rng(seed)
        self.frame_number = 0
        self.packets_sent = 0
        self.bytes_sent = 0
        self.send_errors = 0
        self.last_error: str | None = None
        self._latency: deque = deque()
        self._geometry: SSL_GeometryData | None = None
        self.sock: socket.socket | None = None
        self.targets: list[tuple[str, int]] = self.cfg.targets()
        if open_socket:
            self.open()

    # ------------------------------------------------------------------ socket
    def open(self) -> None:
        if self.sock is not None:
            return
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if self.cfg.is_multicast:
            try:
                s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, int(self.cfg.ttl))
                s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1 if self.cfg.loop else 0)
                if self.cfg.multicast_if:
                    s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF,
                                 socket.inet_aton(self.cfg.multicast_if))
            except OSError as e:  # e.g. interface address not present: keep the default route
                log.warning("vision: multicast socket options failed (%s); using default interface", e)
        self.sock = s

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None

    # ------------------------------------------------------------------ builders (pure)
    def build_geometry(self) -> SSL_GeometryData:
        if self._geometry is None:
            g = SSL_GeometryData()
            fill_field_geometry(g.field, self.field, ball_radius_m=self.ball_radius,
                                max_robot_radius_m=self.robot_radius)
            bm = self.ball_model
            if bm is not None:
                m = g.models.straight_two_phase
                m.acc_slide = -abs(float(bm.sliding_decel))
                m.acc_roll = -abs(float(bm.rolling_decel))
                m.k_switch = float(bm.sliding_to_rolling_speed_ratio)
                c = g.models.chip_fixed_loss
                c.damping_xy_first_hop = 1.0
                c.damping_xy_other_hops = 1.0
                c.damping_z = float(bm.restitution_floor)
            self._geometry = g
        return self._geometry

    def invalidate_geometry(self) -> None:
        self._geometry = None

    def build_detection(self, ws: WorldState, frame_number: int, t_capture: float | None = None,
                        det: SSL_DetectionFrame | None = None) -> SSL_DetectionFrame:
        det = det if det is not None else SSL_DetectionFrame()
        now = time.time() if t_capture is None else t_capture
        det.frame_number = int(frame_number)
        det.t_capture = now
        det.t_sent = now
        det.camera_id = int(self.cfg.camera_id)
        pstd = float(self.cfg.position_noise_std_mm)
        ostd = float(self.cfg.orientation_noise_std_rad)
        b = ws.ball
        ball = det.balls.add()
        ball.confidence = 1.0
        ball.x = b.x * M_TO_MM + (self.rng.normal(0.0, pstd) if pstd > 0 else 0.0)
        ball.y = b.y * M_TO_MM + (self.rng.normal(0.0, pstd) if pstd > 0 else 0.0)
        ball.z = max(0.0, b.z) * M_TO_MM
        ball.pixel_x = 0.0
        ball.pixel_y = 0.0
        for team, container in (("blue", det.robots_blue), ("yellow", det.robots_yellow)):
            for r in ws.robots_of(team):
                m = container.add()
                m.confidence = 1.0
                m.robot_id = int(r.id)
                m.x = r.x * M_TO_MM + (self.rng.normal(0.0, pstd) if pstd > 0 else 0.0)
                m.y = r.y * M_TO_MM + (self.rng.normal(0.0, pstd) if pstd > 0 else 0.0)
                m.orientation = wrap_to_pi(r.theta + (self.rng.normal(0.0, ostd) if ostd > 0 else 0.0))
                m.pixel_x = 0.0
                m.pixel_y = 0.0
                m.height = self.robot_height * M_TO_MM
        return det

    def build_packet(self, ws: WorldState, with_geometry: bool | None = None) -> SSL_WrapperPacket:
        """Next wrapper packet (consumes one frame number). Geometry on frame 0 and every
        ``geometry_every`` frames unless ``with_geometry`` forces it."""
        n = self.frame_number
        self.frame_number += 1
        pkt = SSL_WrapperPacket()
        self.build_detection(ws, n, det=pkt.detection)
        every = int(self.cfg.geometry_every)
        if with_geometry is None:
            with_geometry = every > 0 and (n % every == 0)
        if with_geometry:
            pkt.geometry.CopyFrom(self.build_geometry())
        return pkt

    # ------------------------------------------------------------------ sending
    def send(self, pkt: SSL_WrapperPacket | bytes) -> int:
        if isinstance(pkt, bytes):
            data = pkt
        else:
            if pkt.HasField("detection"):
                pkt.detection.t_sent = time.time()
            data = pkt.SerializeToString()
        if self.sock is None:
            self.open()
        sent = 0
        for tgt in self.targets:
            try:
                self.sock.sendto(data, tgt)  # type: ignore[union-attr]
                sent += 1
            except OSError as e:
                self.send_errors += 1
                self.last_error = f"{tgt}: {e}"
        if sent:
            self.packets_sent += 1
            self.bytes_sent += len(data)
        return len(data) if sent else 0

    def publish(self, ws: WorldState) -> int:
        """Build the packet for ``ws`` and send it (or the delayed one when ``latency_frames``)."""
        pkt = self.build_packet(ws)
        lat = int(self.cfg.latency_frames)
        if lat <= 0:
            return self.send(pkt)
        self._latency.append(pkt)
        if len(self._latency) > lat:
            return self.send(self._latency.popleft())
        return 0

    def flush_latency(self) -> int:
        n = 0
        while self._latency:
            self.send(self._latency.popleft())
            n += 1
        return n

    @property
    def stats(self) -> dict:
        return {"frames": self.frame_number, "packets_sent": self.packets_sent,
                "bytes_sent": self.bytes_sent, "send_errors": self.send_errors,
                "targets": list(self.targets), "latency_frames": int(self.cfg.latency_frames)}


__all__ = ["VisionPublisher", "fill_field_geometry", "M_TO_MM"]
