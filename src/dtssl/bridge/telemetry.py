"""Per-robot telemetry for the GUI *Robot* tab: what the twin knows about a robot, and what a real robot
reports over the radio (``rc_communication.proto`` ``Feedback``), in one record.

Two sources, one dataclass (:class:`RobotTelemetry`):

* ``source="twin"`` (:func:`twin_telemetry`): built from the world state and the last command of a robot.
  Pose, body velocities (commanded and resulting), the four wheel speeds by the inverse kinematics of
  ``dtssl.kinematics`` (the same IK that spins the wheels of the 3D tab; the firmware per-wheel deadzone can be
  applied to the commanded wheels), ball sensor (``has_ball``), dribbler, command age and watchdog state. Battery
  and capacitor do not exist in the identified model: :class:`SyntheticHardware` provides an **illustrative**
  model (capacitor empties on a kick and recharges with a time constant; battery drains with wheel usage), and
  every record built from it is flagged ``hardware_illustrative=True`` so the GUI can label it.
* ``source="real"`` (:class:`TelemetryReceiver`): the ``RCCommunication.Feedback`` datagrams the RobôCIn robots
  send back over the radio (ssl-unification ``CommunicationWifi``: multicast 224.0.1.99, port 19903 by default),
  parsed as they come: body velocity, commanded and measured speed per motor, PWM, PI error and current per
  motor, capacitor and battery charge, ball sensor. Units are whatever the firmware reports; the labels come
  from ``config/telemetry.json`` and can be corrected there without touching code. The receiver keeps the latest
  record per robot id (the message carries no team: ``config/telemetry.json`` ``real.team`` says whose robots
  they are).

Nothing here touches the simulation: it is read-only over ``WorldState`` / ``RobotCmd`` and lives in the bridge
package because of the radio protocol.
"""
from __future__ import annotations

import json
import math
import socket
import struct
import threading
import time
from collections import deque
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
from google.protobuf.message import DecodeError

from dtssl.bridge.proto import RCFeedback, RCWrapperMessage
from dtssl.geometry import RobotGeometry
from dtssl.kinematics import apply_wheel_deadzone, body_to_wheels
from dtssl.paths import repo_root
from dtssl.sim.entities import RobotCmd, RobotState, WorldState

N_WHEELS = 4
Vec4 = tuple[float, float, float, float]

DEFAULT_CONFIG: dict = {
    "real": {
        "enabled": False, "ip": "224.0.1.99", "port": 19903, "multicast_if": "0.0.0.0", "team": None,
        "stale_s": 1.0,
        "fields": {"wheel_meas": "c_speed", "wheel_cmd": "d_speed"},
        "units": {"wheel_speed": "rad/s (como reportado)", "battery": "V (como reportado)",
                  "capacitor": "V (como reportado)", "current": "A (como reportado)", "pwm": "duty (como reportado)"},
    },
    "synthetic": {"illustrative": True, "capacitor_tau_s": 2.5, "battery_full": 1.0, "battery_drain_per_rad": 2e-6},
}


def load_telemetry_config(path: str | Path | None = None) -> dict:
    """``config/telemetry.json`` merged over :data:`DEFAULT_CONFIG` (missing file = defaults)."""
    p = Path(path) if path is not None else repo_root() / "config" / "telemetry.json"
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if p.is_file():
        with open(p, encoding="utf-8") as f:
            user = json.load(f)
        for section in ("real", "synthetic"):
            if isinstance(user.get(section), dict):
                for k, v in user[section].items():
                    if isinstance(v, dict) and isinstance(cfg[section].get(k), dict):
                        cfg[section][k].update(v)
                    else:
                        cfg[section][k] = v
    return cfg


@dataclass
class RobotTelemetry:
    """One robot, one instant, from the twin or from the radio (``None`` = the source does not report it)."""

    source: str                              # "twin" | "real"
    team: str | None
    id: int
    t: float                                 # sim time (twin) or monotonic reception time (real)
    vx: float = 0.0                          # body velocity, m/s, m/s, rad/s
    vy: float = 0.0
    w: float = 0.0
    cmd_vx: float | None = None              # commanded body velocity (twin only)
    cmd_vy: float | None = None
    cmd_w: float | None = None
    wheel_cmd: Vec4 | None = None            # rad/s per wheel, commanded / desired
    wheel_meas: Vec4 | None = None           # rad/s per wheel, resulting / measured
    has_ball: bool = False
    dribbler_on: bool | None = None
    cmd_age_s: float | None = None
    watchdog: bool | None = None             # True = no command for longer than watchdog_s (robot zeroed)
    kicks: int | None = None
    battery: float | None = None             # real: as reported; twin: fraction 0..1 (illustrative)
    capacitor: float | None = None
    hardware_illustrative: bool = False
    pwm: Vec4 | None = None
    error: Vec4 | None = None
    current: Vec4 | None = None
    pose: tuple[float, float, float] | None = None

    def as_dict(self) -> dict:
        return {k: (list(v) if isinstance(v, tuple) else v) for k, v in self.__dict__.items()}


# --------------------------------------------------------------------------------------
# Twin side
# --------------------------------------------------------------------------------------
@dataclass
class _HwState:
    battery: float
    capacitor_t_kick: float | None = None    # sim time of the last kick (None = never)
    had_ball: bool = False
    t_last: float | None = None


class SyntheticHardware:
    """Illustrative battery / capacitor model for the twin's robots (NOT identified; labelled as such).

    Capacitor: fraction in [0, 1]; empties at a kick (``cmd.kick_speed > 0`` while the ball leaves the dribbler)
    and recharges as ``1 - exp(-(t - t_kick) / tau)``. Battery: fraction starting at ``battery_full``, drained
    by ``drain_per_rad * sum(|omega_wheel|) * dt``.
    """

    def __init__(self, cfg: dict | None = None):
        c = (cfg or DEFAULT_CONFIG)["synthetic"]
        self.tau = float(c.get("capacitor_tau_s", 2.5))
        self.full = float(c.get("battery_full", 1.0))
        self.drain = float(c.get("battery_drain_per_rad", 2e-6))
        self.illustrative = bool(c.get("illustrative", True))
        self._s: dict[tuple[str, int], _HwState] = {}

    def reset(self) -> None:
        self._s.clear()

    def update(self, key: tuple[str, int], t: float, robot: RobotState, cmd: RobotCmd,
               wheel_meas: Vec4 | None) -> tuple[float, float]:
        """Advance the model of ``key`` to time ``t``; returns ``(battery, capacitor)`` fractions."""
        s = self._s.get(key)
        if s is None:
            s = _HwState(battery=self.full)
            self._s[key] = s
        if s.t_last is not None and t > s.t_last and wheel_meas is not None:
            dt = t - s.t_last
            s.battery = max(0.0, s.battery - self.drain * float(np.sum(np.abs(wheel_meas))) * dt)
        kicked = bool(cmd.kick_speed > 0.0) and s.had_ball and not robot.has_ball
        if kicked:
            s.capacitor_t_kick = t
        s.had_ball = bool(robot.has_ball)
        s.t_last = t
        if s.capacitor_t_kick is None:
            cap = 1.0
        else:
            cap = 1.0 - math.exp(-max(0.0, t - s.capacitor_t_kick) / self.tau) if self.tau > 0 else 1.0
        return s.battery, float(min(max(cap, 0.0), 1.0))


def twin_telemetry(ws: WorldState, key: tuple[str, int], cmd: RobotCmd, *, geom: RobotGeometry | None = None,
                   deadzone_rad_s: float = 0.0, watchdog_s: float | None = None, now: float | None = None,
                   kicks: int | None = None, hardware: SyntheticHardware | None = None) -> RobotTelemetry | None:
    """The twin's record of robot ``key`` at ``ws`` (``None`` when the robot is absent)."""
    r = ws.robots.get(key)
    if r is None:
        return None
    body_cmd = np.array([cmd.vx, cmd.vy, cmd.w], dtype=float)
    body_meas = np.array([r.vx_b, r.vy_b, r.w], dtype=float)
    wc = body_to_wheels(body_cmd, geom)
    if deadzone_rad_s > 0.0:
        wc = apply_wheel_deadzone(wc, deadzone_rad_s)
    wm = body_to_wheels(body_meas, geom)
    age = None
    wd = None
    if cmd.t_recv > 0.0:
        age = max(0.0, (time.monotonic() if now is None else now) - cmd.t_recv)
        if watchdog_s is not None and watchdog_s > 0.0:
            wd = age > watchdog_s
    rec = RobotTelemetry(source="twin", team=key[0], id=int(key[1]), t=float(ws.t),
                         vx=float(r.vx_b), vy=float(r.vy_b), w=float(r.w),
                         cmd_vx=float(cmd.vx), cmd_vy=float(cmd.vy), cmd_w=float(cmd.w),
                         wheel_cmd=tuple(float(v) for v in wc), wheel_meas=tuple(float(v) for v in wm),
                         has_ball=bool(r.has_ball), dribbler_on=bool(cmd.dribbler_rpm > 0.0),
                         cmd_age_s=age, watchdog=wd, kicks=kicks, pose=(float(r.x), float(r.y), float(r.theta)))
    if hardware is not None:
        b, c = hardware.update(key, float(ws.t), r, cmd, rec.wheel_meas)
        rec = replace(rec, battery=b, capacitor=c, hardware_illustrative=hardware.illustrative)
    return rec


# --------------------------------------------------------------------------------------
# Real side: rc_communication Feedback over the radio multicast
# --------------------------------------------------------------------------------------
def parse_feedback(data: bytes, *, team: str | None = None, t: float | None = None,
                   fields: dict | None = None) -> RobotTelemetry | None:
    """Decode one datagram: a bare ``Feedback`` (what ``CommunicationWifi`` expects) or a ``WrapperMessage``
    carrying one. ``fields`` maps ``wheel_meas`` / ``wheel_cmd`` to the ``c_speed`` / ``d_speed`` groups."""
    fb = RCFeedback()
    try:
        fb.ParseFromString(data)
        ok = _looks_like_feedback(fb)
    except DecodeError:
        ok = False
    if not ok:
        wm = RCWrapperMessage()
        try:
            wm.ParseFromString(data)
        except DecodeError:
            return None
        if wm.WhichOneof("message") != "feedback":
            return None
        fb = wm.feedback
    f = fields or DEFAULT_CONFIG["real"]["fields"]
    groups = {"c_speed": _motor4(fb, "c_speed_m"), "d_speed": _motor4(fb, "d_speed_m")}
    return RobotTelemetry(
        source="real", team=team, id=int(fb.id), t=time.monotonic() if t is None else float(t),
        vx=float(fb.vx), vy=float(fb.vy), w=float(fb.w),
        wheel_cmd=groups.get(f.get("wheel_cmd", "d_speed")), wheel_meas=groups.get(f.get("wheel_meas", "c_speed")),
        has_ball=bool(fb.hasBall), battery=float(fb.batteryCharge), capacitor=float(fb.capacitorCharge),
        hardware_illustrative=False, pwm=_motor4(fb, "pwm_m"), error=_motor4(fb, "error_m"),
        current=_motor4(fb, "current_m"))


def _motor4(fb, prefix: str) -> Vec4:
    return tuple(float(getattr(fb, f"{prefix}{i}")) for i in (1, 2, 3, 4))  # type: ignore[return-value]


def _looks_like_feedback(fb) -> bool:
    """A ``WrapperMessage`` decoded as ``Feedback`` leaves its payload as unknown fields (wire-type mismatch);
    a genuine ``Feedback`` parses with none."""
    try:
        from google.protobuf.unknown_fields import UnknownFieldSet

        return len(UnknownFieldSet(fb)) == 0
    except Exception:  # noqa: BLE001 - older runtimes: accept
        return True


def _is_multicast(ip: str) -> bool:
    try:
        first = int(ip.split(".")[0])
    except ValueError:
        return False
    return 224 <= first <= 239


class TelemetryReceiver(threading.Thread):
    """Listens for ``Feedback`` datagrams and keeps the latest record per robot id (thread-safe)."""

    def __init__(self, cfg: dict | None = None, *, ip: str | None = None, port: int | None = None,
                 multicast_if: str | None = None, team: str | None = None, recv_timeout: float = 0.2,
                 history: int = 600):
        super().__init__(name="dtssl-telemetry", daemon=True)
        c = (cfg or DEFAULT_CONFIG)["real"]
        self.ip = str(ip or c.get("ip", "224.0.1.99"))
        self.port = int(port if port is not None else c.get("port", 19903))
        self.multicast_if = str(multicast_if or c.get("multicast_if", "0.0.0.0"))
        self.team = team if team is not None else c.get("team")
        self.stale_s = float(c.get("stale_s", 1.0))
        self.fields = dict(c.get("fields", DEFAULT_CONFIG["real"]["fields"]))
        self.units = dict(c.get("units", DEFAULT_CONFIG["real"]["units"]))
        self.lock = threading.Lock()
        self.latest_by_id: dict[int, RobotTelemetry] = {}
        self.history_by_id: dict[int, deque[RobotTelemetry]] = {}
        self._history_n = int(history)
        self.packets = 0
        self.decode_errors = 0
        self._t_recv: deque[float] = deque(maxlen=200)
        self._stop_evt = threading.Event()
        self.sock = self._open(recv_timeout)

    def _open(self, recv_timeout: float) -> socket.socket:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except OSError:
                pass
        mcast = _is_multicast(self.ip)
        s.bind(("" if mcast else self.ip, self.port))
        if mcast:
            mreq = struct.pack("4s4s", socket.inet_aton(self.ip), socket.inet_aton(self.multicast_if))
            s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        s.settimeout(recv_timeout)
        if self.port == 0:                       # ephemeral (tests): report the port actually bound
            self.port = int(s.getsockname()[1])
        return s

    @property
    def endpoint(self) -> str:
        return f"{self.ip}:{self.port}"

    def run(self) -> None:
        while not self._stop_evt.is_set():
            try:
                data, _ = self.sock.recvfrom(65535)
            except TimeoutError:
                continue
            except ConnectionResetError:
                continue
            except OSError:
                break
            self.ingest(data)

    def ingest(self, data: bytes, t: float | None = None) -> RobotTelemetry | None:
        """Decode and store one datagram (also usable without the thread, e.g. tests / log replay)."""
        rec = parse_feedback(data, team=self.team, t=t, fields=self.fields)
        if rec is None:
            self.decode_errors += 1
            return None
        with self.lock:
            self.packets += 1
            self._t_recv.append(rec.t)
            self.latest_by_id[rec.id] = rec
            self.history_by_id.setdefault(rec.id, deque(maxlen=self._history_n)).append(rec)
        return rec

    def latest(self, rid: int, *, now: float | None = None) -> RobotTelemetry | None:
        """Latest record of ``rid``, or ``None`` when there is none or it is older than ``stale_s``."""
        with self.lock:
            rec = self.latest_by_id.get(int(rid))
        if rec is None:
            return None
        if (time.monotonic() if now is None else now) - rec.t > self.stale_s:
            return None
        return rec

    def history(self, rid: int) -> list[RobotTelemetry]:
        with self.lock:
            return list(self.history_by_id.get(int(rid), ()))

    @property
    def rate_hz(self) -> float:
        with self.lock:
            ts = list(self._t_recv)
        if len(ts) < 2 or ts[-1] <= ts[0]:
            return 0.0
        return (len(ts) - 1) / (ts[-1] - ts[0])

    def ids(self) -> list[int]:
        with self.lock:
            return sorted(self.latest_by_id)

    def stop(self) -> None:
        self._stop_evt.set()
        try:
            self.sock.close()
        except OSError:
            pass


__all__ = ["RobotTelemetry", "SyntheticHardware", "twin_telemetry", "parse_feedback", "TelemetryReceiver",
           "load_telemetry_config", "DEFAULT_CONFIG", "N_WHEELS"]
