"""``ProtocolPlant``: an external simulator that speaks the ssl-simulation-protocol as a harness ``Plant``.

The paper's harness drives a ``Plant`` per re-anchored window (``reset(pose0, velb0)`` -> commands at 60 Hz ->
poses).  This adapter replays those windows through **any** simulator that implements the league protocol
(grSim, the ER-Force ``simulator-cli``, or ``dtssl serve`` itself) over UDP, so the league simulators can be
evaluated on the hold-out with *exactly* the same windows and metric as the behavioral twin ("replay via
protocol", C2b).  Per window:

1. ``TeleportRobot`` (pose + **world** velocity from ``velb0``) on the simulator-control port, immediately
   followed by the first ``RobotControl`` (``local_velocity`` = body command).  What the simulator does with
   the velocity is *its* business and part of the baseline: ``dtssl serve`` and ER-Force set the body velocity
   (ER-Force only the linear one, see ``Endpoint.teleport_omega``), grSim resets the robot and turns it into a
   wheel-motor setpoint, i.e. every grSim window starts from rest;
2. the remaining commands are streamed at exactly ``dt`` wall-clock intervals (paced by a monotonic clock,
   independent of the vision packets: a simulator with vision delay such as ER-Force's 35 ms would otherwise
   delay every command by that much);
3. every ``SSL_DetectionFrame`` is collected until ``H dt + tail`` after the teleport;
4. **alignment**: the anchor is the first frame after the teleport whose pose is consistent with ``pose0``
   (the teleport is visible), the sub-frame offset ``tau0`` between the teleport and that capture is estimated
   from ``velb0`` when the robot moves (``(p_anchor - pose0) . v0 / |v0|^2``, else the running median), and the
   pose at ``h dt`` is linearly interpolated from the frames (``t_capture`` deltas, x/y and unwrapped theta).

The harness calls :meth:`free_run_window` (batch) when the plant offers it (``dtssl.sim.rollout.free_run``);
the step-wise ``Plant`` API is also implemented (one vision tick per ``step``) for interactive use.

Delay: ``delay=None`` sends the recorded commands as they are (the simulator's own latency is part of the
baseline); ``delay="theta"`` applies the identified per-DOF transport delay ``Td`` on the sending side
(``ud[j] = u[j - ceil(Td/dt)]``, primed with the commands before the window), the analogue of the
``mujoco-rollers-delay`` / rSim + Td ablation.

Everything about the simulator is declared in an :class:`Endpoint` (``config/external_sims.json``).  The
statistics of a run (anchor failures, ``tau0`` estimates, frame gaps, command timing jitter, measured vision
period) are kept in :attr:`ProtocolPlant.stats` for the result artefact.  Real-time by construction:
one window of 90 samples costs 1.5 s + tail; the hold-out (265 windows) ~8 min per simulator.
"""
from __future__ import annotations

import json
import logging
import math
import socket
import struct
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from google.protobuf.message import DecodeError

from dtssl.bridge.proto import (
    TEAM_ENUM,
    RobotControl,
    SimulatorCommand,
    SimulatorResponse,
    SSL_WrapperPacket,
)
from dtssl.models.base import Plant, Pose, Vel
from dtssl.models.params import DofParam, load_twin_params

log = logging.getLogger(__name__)

MM_TO_M = 1e-3
DEFAULT_DT = 1.0 / 60.0
FAR = (-6.0, -4.5)          # parking spot (m) for the ball and the other robots
ANCHOR_SEARCH_FRAMES = 12   # frames (after the calibrated latency) in which the teleport must show up
LATE_SEND_S = 0.010         # a command sent more than this after its slot counts as "late" (stats.send_late)
_WIN = sys.platform == "win32"
SPIN_S = 0.0015 if _WIN else 0.0004   # sleep until this close to a send slot, then spin (Windows sleeps overshoot ~1 ms)
_clock = time.perf_counter  # QueryPerformanceCounter on every Windows Python (monotonic() was 15.6 ms before 3.13)


class _RealTimeMode:
    """Process-wide knobs for the streaming loop: 1 ms timer resolution on Windows (``timeBeginPeriod``) and a
    short GIL switch interval so the sender thread is not held back by the receiver / an in-process server."""

    def __init__(self, switch_interval: float = 0.001):
        self._switch = switch_interval
        self._prev_switch: float | None = None
        self._period_set = False

    def enter(self) -> None:
        if self._prev_switch is None:
            self._prev_switch = sys.getswitchinterval()
            sys.setswitchinterval(self._switch)
        if _WIN and not self._period_set:
            try:
                import ctypes

                ctypes.windll.winmm.timeBeginPeriod(1)  # type: ignore[attr-defined]
                self._period_set = True
            except Exception:  # pragma: no cover - best effort
                pass

    def exit(self) -> None:
        if self._prev_switch is not None:
            sys.setswitchinterval(self._prev_switch)
            self._prev_switch = None
        if self._period_set:
            try:
                import ctypes

                ctypes.windll.winmm.timeEndPeriod(1)  # type: ignore[attr-defined]
            except Exception:  # pragma: no cover
                pass
            self._period_set = False


def _is_multicast(ip: str) -> bool:
    try:
        return 224 <= int(ip.split(".")[0]) <= 239
    except ValueError:
        return False


# --------------------------------------------------------------------------------------
# Endpoint (config/external_sims.json)
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Endpoint:
    """Where and how a protocol simulator is reached (defaults = league conventions)."""

    name: str = "sim"
    host: str = "127.0.0.1"
    port_blue: int = 10301
    port_yellow: int = 10302
    port_simcontrol: int = 10300
    vision_ip: str = "224.5.23.2"
    vision_port: int = 10020
    multicast_if: str = "127.0.0.1"
    unicast: bool = False
    team: str = "blue"
    robot_id: int = 0
    vision_rate: float | None = None     # frames per *simulated* second; None = measured (real-time sims stamp
                                         # t_capture in sim time: grSim 60, ER-Force 66.67); set it for dtssl serve
                                         # at speed != 1 (wall-clock stamps)
    clear_others: bool = True            # remove the other robots and park the ball at open()
    n_robots_per_team: int = 16          # ids swept by clear_others
    teleport_omega: bool = True          # send the yaw-rate IC in TeleportRobot.v_angular (False for ER-Force,
                                         # whose simrobot.cpp applies it about the x axis: the robot would tip)
    notes: str = ""

    @property
    def control_port(self) -> int:
        return int(self.port_blue if self.team == "blue" else self.port_yellow)

    @classmethod
    def from_dict(cls, name: str, d: dict) -> Endpoint:
        keys = cls.__dataclass_fields__
        return cls(name=name, **{k: v for k, v in d.items() if k in keys and k != "name"})


def load_endpoints(path: Path | str | None = None) -> dict[str, Endpoint]:
    """``config/external_sims.json`` -> {name: Endpoint} (keys starting with ``_`` are comments)."""
    if path is None:
        from dtssl.paths import config_path

        path = config_path("external_sims.json")
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return {k: Endpoint.from_dict(k, v) for k, v in raw.items() if not k.startswith("_") and isinstance(v, dict)}


def load_endpoint(name: str, path: Path | str | None = None) -> Endpoint:
    eps = load_endpoints(path)
    try:
        return eps[name]
    except KeyError as e:
        raise KeyError(f"unknown external simulator {name!r}; config/external_sims.json has {sorted(eps)}") from e


# --------------------------------------------------------------------------------------
# Vision receiver (thread)
# --------------------------------------------------------------------------------------
@dataclass
class Frame:
    t_recv: float                  # monotonic wall clock at reception
    t_capture: float               # simulator's capture stamp (sim time for grSim/ER-Force, wall for dtssl)
    frame_number: int
    camera_id: int
    pose: tuple[float, float, float] | None      # (x, y, theta) in m / rad, None when the robot is absent


class VisionReceiver(threading.Thread):
    """Collects the detection frames of one robot into a bounded deque (``t_recv`` monotonic)."""

    def __init__(self, ep: Endpoint, maxlen: int = 20000, recv_timeout: float = 0.2):
        super().__init__(name=f"dtssl-vision-{ep.name}", daemon=True)
        self.ep = ep
        self.frames: deque[Frame] = deque(maxlen=maxlen)
        self.lock = threading.Lock()
        self.packets = 0
        self.decode_errors = 0
        self.geometry_packets = 0
        self.last_frame_number: dict[int, int] = {}
        self.gaps = 0
        self._stop = threading.Event()
        self.sock = self._open(recv_timeout)

    def _open(self, recv_timeout: float) -> socket.socket:
        ep = self.ep
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except OSError:
                pass
        mcast = _is_multicast(ep.vision_ip) and not ep.unicast
        s.bind(("" if mcast else "0.0.0.0", int(ep.vision_port)))
        if mcast:
            mreq = struct.pack("4s4s", socket.inet_aton(ep.vision_ip), socket.inet_aton(ep.multicast_if or "0.0.0.0"))
            s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        s.settimeout(recv_timeout)
        return s

    def run(self) -> None:
        team, rid = self.ep.team, int(self.ep.robot_id)
        while not self._stop.is_set():
            try:
                data, _ = self.sock.recvfrom(65535)
            except TimeoutError:
                continue
            except ConnectionResetError:          # Windows ICMP port unreachable: the socket is still usable
                continue
            except OSError:
                break
            t_recv = _clock()
            pkt = SSL_WrapperPacket()
            try:
                pkt.ParseFromString(data)
            except DecodeError:
                self.decode_errors += 1
                continue
            self.packets += 1
            if pkt.HasField("geometry"):
                self.geometry_packets += 1
            if not pkt.HasField("detection"):
                continue
            det = pkt.detection
            cam = int(det.camera_id)
            n = int(det.frame_number)
            last = self.last_frame_number.get(cam)
            if last is not None and n > last + 1:
                self.gaps += n - last - 1
            self.last_frame_number[cam] = n
            pose = None
            for r in (det.robots_blue if team == "blue" else det.robots_yellow):
                if int(r.robot_id) == rid:
                    pose = (float(r.x) * MM_TO_M, float(r.y) * MM_TO_M, float(r.orientation))
                    break
            fr = Frame(t_recv=t_recv, t_capture=float(det.t_capture), frame_number=n, camera_id=cam, pose=pose)
            with self.lock:
                self.frames.append(fr)

    def stop(self) -> None:
        self._stop.set()
        try:
            self.sock.close()
        except OSError:
            pass

    def since(self, t_recv_min: float) -> list[Frame]:
        with self.lock:
            return [f for f in self.frames if f.t_recv >= t_recv_min]

    def latest(self) -> Frame | None:
        with self.lock:
            return self.frames[-1] if self.frames else None


# --------------------------------------------------------------------------------------
# Alignment (pure numpy; unit-tested without a network)
# --------------------------------------------------------------------------------------
def unwrap_series(th: np.ndarray, start: float) -> np.ndarray:
    """Unwrap ``th`` (rad) so that the sequence is continuous and its first value is ``start``-consistent."""
    out = np.empty_like(th, dtype=float)
    prev = float(start)
    for i, v in enumerate(th):
        d = math.atan2(math.sin(v - prev), math.cos(v - prev))
        prev = prev + d
        out[i] = prev
    return out


def find_anchor(frames: list[Frame], pose0: Pose, velw0: tuple[float, float, float], period: float,
                tol_pos: float = 0.05, tol_ang: float = 0.15) -> int | None:
    """Index of the first frame (after the teleport) consistent with ``pose0`` moving at ``velw0`` for at most
    two vision periods: ``|p - pose0| <= tol_pos + |v0| 2 period`` and the same for the heading."""
    x0, y0, th0 = pose0
    vx, vy, w = velw0
    dmax = tol_pos + math.hypot(vx, vy) * 2.0 * period
    amax = tol_ang + abs(w) * 2.0 * period
    for i, f in enumerate(frames):
        if f.pose is None:
            continue
        x, y, th = f.pose
        if math.hypot(x - x0, y - y0) <= dmax and abs(math.atan2(math.sin(th - th0), math.cos(th - th0))) <= amax:
            return i
    return None


def estimate_tau0(p_anchor: Pose, pose0: Pose, velw0: tuple[float, float, float], period: float,
                  v_min: float = 0.15) -> float | None:
    """Sub-frame offset between the teleport and the anchor capture from the displacement along ``v0``;
    ``None`` when the robot is too slow to tell (``|v0| < v_min``)."""
    vx, vy, _ = velw0
    v2 = vx * vx + vy * vy
    if v2 < v_min * v_min:
        return None
    d = (p_anchor[0] - pose0[0]) * vx + (p_anchor[1] - pose0[1]) * vy
    return float(min(max(d / v2, 0.0), period))


def interpolate_poses(frames: list[Frame], anchor: int, tau0: float, capture_scale: float, dt: float, h_max: int,
                      pose0: Pose, frame_period: float | None = None) -> tuple[np.ndarray, int]:
    """``pose_sim`` (h_max + 1, 3) at ``h dt`` after the teleport from the detected frames (frames at the same
    tick are averaged; theta unwrapped from ``pose0``).  The time base is ``t_capture`` (scaled by
    ``capture_scale``) or, when ``frame_period`` is given, the per-camera frame counter (for simulators that
    stamp wall-clock time, whose catch-up ticks would distort the capture stamps).  Returns
    ``(pose_sim, n_frames_used)``."""
    fa = frames[anchor]
    t_a = fa.t_capture
    ts: list[float] = []
    xs: list[float] = []
    ys: list[float] = []
    ths: list[float] = []
    ns: list[int] = []
    for f in frames[anchor:]:
        if f.pose is None:
            continue
        if frame_period is not None:
            if f.camera_id != fa.camera_id:
                continue
            t = (f.frame_number - fa.frame_number) * frame_period + tau0
        else:
            t = (f.t_capture - t_a) * capture_scale + tau0      # sim time since the teleport
        if ts and abs(t - ts[-1]) < 1e-6:                          # same tick, another camera: average x, y
            n = ns[-1]
            xs[-1] = (xs[-1] * n + f.pose[0]) / (n + 1)
            ys[-1] = (ys[-1] * n + f.pose[1]) / (n + 1)
            ns[-1] = n + 1
            continue
        ts.append(t)
        xs.append(f.pose[0])
        ys.append(f.pose[1])
        ths.append(f.pose[2])
        ns.append(1)
    pose_sim = np.full((h_max + 1, 3), np.nan)
    pose_sim[0] = pose0
    if len(ts) < 2:
        return pose_sim, len(ts)
    t_arr = np.asarray(ts)
    order = np.argsort(t_arr)
    t_arr = t_arr[order]
    x_arr = np.asarray(xs)[order]
    y_arr = np.asarray(ys)[order]
    th_arr = unwrap_series(np.asarray(ths)[order], pose0[2])
    want = dt * np.arange(1, h_max + 1)
    ok = (want >= t_arr[0] - 1e-9) & (want <= t_arr[-1] + 1e-9)
    pose_sim[1:, 0] = np.where(ok, np.interp(want, t_arr, x_arr), np.nan)
    pose_sim[1:, 1] = np.where(ok, np.interp(want, t_arr, y_arr), np.nan)
    pose_sim[1:, 2] = np.where(ok, np.interp(want, t_arr, th_arr), np.nan)
    return pose_sim, len(ts)


# --------------------------------------------------------------------------------------
# The plant
# --------------------------------------------------------------------------------------
@dataclass
class ProtocolStats:
    windows: int = 0
    anchor_failures: int = 0
    anchor_late: int = 0                   # anchor found > 1.5 periods after the teleport (a frame was missed)
    short_windows: int = 0                 # fewer frames than needed to cover H dt
    frames_used: list[int] = field(default_factory=list)
    tau0: list[float] = field(default_factory=list)
    send_phase: list[float] = field(default_factory=list)   # (T0 - last frame arrival) / period, mod 1
    tau0_estimated: int = 0
    send_jitter_max: float = 0.0           # s, |actual - scheduled| of the command sends
    send_jitter_mean: float = 0.0
    send_late: int = 0                     # sends later than LATE_SEND_S (scheduler stalls; the previous command persists)
    vision_period_wall: float | None = None
    vision_rate_sim: float | None = None
    capture_scale: float | None = None
    wall_per_sim: float | None = None
    teleport_latency_wall: float | None = None     # s, send -> first frame showing the teleport (median)
    teleport_latency_spread: float | None = None
    vision_gaps: int = 0
    decode_errors: int = 0
    controls_sent: int = 0
    teleports: int = 0
    _jit_sum: float = 0.0
    _jit_n: int = 0

    def as_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
        d["tau0_median"] = float(np.median(self.tau0)) if self.tau0 else None
        d["frames_used_median"] = float(np.median(self.frames_used)) if self.frames_used else None
        d["send_phase_median"] = float(np.median(self.send_phase)) if self.send_phase else None
        d.pop("frames_used")
        d.pop("tau0")
        d.pop("send_phase")
        return d


class ProtocolPlant(Plant):
    """See the module docstring.  ``params`` (theta) is only used by the ``delay="theta"`` tap."""

    def __init__(self, endpoint: Endpoint | str, *, delay: str | None = None,
                 params: dict[str, DofParam] | None = None, dt: float = DEFAULT_DT, tail_s: float = 0.25,
                 lead_s: float = 0.05, tol_pos: float = 0.05, tol_ang: float = 0.15, probe_s: float = 0.6,
                 auto_open: bool = True):
        self.ep = load_endpoint(endpoint) if isinstance(endpoint, str) else endpoint
        if delay not in (None, "theta"):
            raise ValueError("delay must be None or 'theta'")
        self.delay = delay
        self._theta = params if params is not None else (load_twin_params() if delay == "theta" else None)
        self._Td = (np.array([self._theta[d].Td for d in ("vx", "vy", "w")], dtype=float)
                    if self._theta is not None else np.zeros(3))
        self.dt = float(dt)
        self.tail_s = float(tail_s)
        self.lead_s = float(lead_s)
        self.tol_pos, self.tol_ang = float(tol_pos), float(tol_ang)
        self.probe_s = float(probe_s)
        self.stats = ProtocolStats()
        self.rx: VisionReceiver | None = None
        self.tx: socket.socket | None = None
        self._rt = _RealTimeMode()
        self._period_wall = self.dt                 # wall seconds between vision frames (measured at open)
        self._rate_sim = 1.0 / self.dt              # frames per simulated second
        self._capture_scale = 1.0                   # sim seconds per t_capture second
        self._wall_per_sim = 1.0                    # wall seconds per simulated second
        self._latency = 0.0                         # wall s from a teleport send to the frame that shows it
        self._tau0_hist: list[float] = []
        # step-wise state
        self.x = self.y = self.th = 0.0
        self._vbody = np.zeros(3)
        self._hist: list[np.ndarray] = []
        self._base = 0
        self._k = 0
        self._t_last_tick: float | None = None
        if auto_open:
            self.open()

    # ------------------------------------------------------------------ lifecycle
    def open(self) -> ProtocolPlant:
        if self.rx is not None:
            return self
        self._rt.enter()
        self.rx = VisionReceiver(self.ep)
        self.rx.start()
        self.tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.tx.bind(("0.0.0.0", 0))
        self.tx.settimeout(0.2)
        self._probe()
        if self.ep.clear_others:
            self.clear_field()
        self._calibrate_latency()
        return self

    def close(self) -> None:
        if self.rx is not None:
            self.rx.stop()
            self.rx = None
        if self.tx is not None:
            try:
                self.tx.close()
            except OSError:
                pass
            self.tx = None
        self._rt.exit()

    def __enter__(self) -> ProtocolPlant:
        return self.open()

    def __exit__(self, *exc) -> None:
        self.close()

    @property
    def params(self):
        """theta seen by the harness: the identified theta when the delay tap is ours, else None
        (the window grid stays the official one, see ``rollout_segment``)."""
        return self._theta if self.delay == "theta" else None

    # ------------------------------------------------------------------ protocol helpers
    def _send_control(self, cmd) -> None:
        rc = RobotControl()
        c = rc.robot_commands.add()
        c.id = int(self.ep.robot_id)
        lv = c.move_command.local_velocity
        lv.forward, lv.left, lv.angular = float(cmd[0]), float(cmd[1]), float(cmd[2])
        assert self.tx is not None
        self.tx.sendto(rc.SerializeToString(), (self.ep.host, self.ep.control_port))
        self.stats.controls_sent += 1

    def _send_simcontrol(self, msg: SimulatorCommand, wait: float = 0.0) -> SimulatorResponse | None:
        assert self.tx is not None
        self.tx.sendto(msg.SerializeToString(), (self.ep.host, int(self.ep.port_simcontrol)))
        if wait <= 0.0:
            return None
        self.tx.settimeout(wait)
        try:
            data, _ = self.tx.recvfrom(65535)
        except (TimeoutError, OSError):
            return None
        resp = SimulatorResponse()
        try:
            resp.ParseFromString(data)
        except DecodeError:
            return None
        return resp

    def _drain_tx(self) -> None:
        """Discard pending SimulatorResponse / RobotControlResponse datagrams on the send socket."""
        assert self.tx is not None
        self.tx.settimeout(0.0)
        try:
            while True:
                self.tx.recvfrom(65535)
        except (BlockingIOError, TimeoutError, OSError):
            pass

    def teleport_msg(self, pose: Pose, velw: tuple[float, float, float], present: bool | None = True) -> SimulatorCommand:
        msg = SimulatorCommand()
        tr = msg.control.teleport_robot.add()
        tr.id.id = int(self.ep.robot_id)
        tr.id.team = TEAM_ENUM[self.ep.team]
        tr.x, tr.y, tr.orientation = float(pose[0]), float(pose[1]), float(pose[2])
        tr.v_x, tr.v_y = float(velw[0]), float(velw[1])
        tr.v_angular = float(velw[2]) if self.ep.teleport_omega else 0.0
        if present is not None:
            tr.present = bool(present)
        return msg

    def clear_field(self) -> None:
        """Park the ball in a corner and remove every other robot (``present=false`` + far teleport)."""
        msg = SimulatorCommand()
        b = msg.control.teleport_ball
        b.x, b.y, b.z, b.vx, b.vy, b.vz = FAR[0], FAR[1], 0.0, 0.0, 0.0, 0.0
        k = 0
        for team in ("blue", "yellow"):
            for rid in range(int(self.ep.n_robots_per_team)):
                if team == self.ep.team and rid == int(self.ep.robot_id):
                    continue
                tr = msg.control.teleport_robot.add()
                tr.id.id, tr.id.team = rid, TEAM_ENUM[team]
                tr.x, tr.y, tr.orientation = FAR[0] + 0.25 * (k % 8), FAR[1] - 0.25 * (k // 8), 0.0
                tr.v_x = tr.v_y = tr.v_angular = 0.0
                tr.present = False
                k += 1
        self._send_simcontrol(msg, wait=0.3)
        self._drain_tx()
        time.sleep(0.1)

    def _probe(self) -> None:
        """Measure the vision cadence (wall period, capture scale) over ``probe_s`` seconds."""
        assert self.rx is not None
        t0 = _clock()
        time.sleep(self.probe_s)
        frames = self.rx.since(t0)
        if len(frames) < 3:
            raise ConnectionError(f"{self.ep.name}: no vision on {self.ep.vision_ip}:{self.ep.vision_port} "
                                  f"({len(frames)} frames in {self.probe_s:.1f} s) -- is the simulator running?")
        # one entry per tick (distinct t_capture)
        ticks: list[Frame] = []
        for f in frames:
            if not ticks or abs(f.t_capture - ticks[-1].t_capture) > 1e-6:
                ticks.append(f)
        if len(ticks) < 3:
            raise ConnectionError(f"{self.ep.name}: vision frames carry a constant t_capture")
        d_wall = np.diff([f.t_recv for f in ticks])
        d_cap = np.diff([f.t_capture for f in ticks])
        self._period_wall = float(np.median(d_wall))
        med_cap = float(np.median(d_cap))
        # frames per simulated second: declared (wall-clock stamps, dtssl serve at speed != 1) or measured
        # from the capture stamps (grSim / ER-Force stamp t_capture in simulated time)
        rate = float(self.ep.vision_rate) if self.ep.vision_rate else (1.0 / med_cap if med_cap > 0 else 1.0 / self.dt)
        self._rate_sim = rate
        self._capture_scale = (1.0 / rate) / med_cap if med_cap > 0 else 1.0
        wps = self._period_wall * rate
        # real-time simulator: pace with the exact nominal period (a 0.5 s probe has ~1 % error, which would
        # drift the sends by half a frame over a window); keep the measured value only for speed != 1
        self._wall_per_sim = 1.0 if abs(wps - 1.0) < 0.03 else wps
        self.stats.vision_period_wall = self._period_wall
        self.stats.vision_rate_sim = rate
        self.stats.capture_scale = self._capture_scale
        self.stats.wall_per_sim = self._wall_per_sim
        log.info("%s: vision %.1f Hz wall (period %.2f ms), %.2f frames per simulated s, capture scale %.3f, "
                 "wall/sim %.3f", self.ep.name, 1.0 / self._period_wall, 1e3 * self._period_wall, rate,
                 self._capture_scale, self._wall_per_sim)

    def _calibrate_latency(self, n: int = 3) -> None:
        """Teleport the robot to ``n`` distinct resting poses and time the first frame that shows each; the
        median is the send-to-vision latency used to skip pre-teleport frames in the anchor search."""
        assert self.rx is not None
        poses = [(0.0, 0.0, 0.0), (1.0, 0.5, 1.0), (-1.0, -0.5, -1.0)][:n]
        lat = []
        for pose in poses:
            self._drain_tx()
            T0 = _clock()
            self._send_simcontrol(self.teleport_msg(pose, (0.0, 0.0, 0.0)))
            self.stats.teleports += 1
            deadline = T0 + 1.0
            seen = None
            while _clock() < deadline and seen is None:
                for f in self.rx.since(T0):
                    if f.pose is not None and math.hypot(f.pose[0] - pose[0], f.pose[1] - pose[1]) <= self.tol_pos:
                        seen = f.t_recv - T0
                        break
                if seen is None:
                    time.sleep(0.002)
            if seen is None:
                raise ConnectionError(f"{self.ep.name}: TeleportRobot of {self.ep.team} {self.ep.robot_id} not "
                                      f"reflected in the vision within 1 s (pose {pose}); check the simulator "
                                      "control port and that the robot exists")
            lat.append(seen)
        self._latency = float(np.median(lat))
        self.stats.teleport_latency_wall = self._latency
        self.stats.teleport_latency_spread = float(np.max(lat) - np.min(lat))
        log.info("%s: teleport -> vision latency %.1f ms (spread %.1f ms)", self.ep.name, 1e3 * self._latency,
                 1e3 * self.stats.teleport_latency_spread)

    # ------------------------------------------------------------------ delay tap (sending side)
    def _delayed_stream(self, win_cmds: np.ndarray, prev_cmds, dt: float) -> np.ndarray:
        """``ud[j] = u[j - ceil(Td/dt)]`` per DOF, taking the pre-window commands from ``prev_cmds``."""
        u = np.asarray(win_cmds, dtype=float).reshape(-1, 3)
        if self.delay != "theta":
            return u
        prev = np.asarray(prev_cmds, dtype=float).reshape(-1, 3) if prev_cmds is not None else np.zeros((0, 3))
        hist = np.vstack([prev, u])
        base = len(prev)
        ud = np.zeros_like(u)
        for i in range(3):
            m = 0 if self._Td[i] <= 0.0 else int(math.ceil(self._Td[i] / dt - 1e-9))
            for j in range(len(u)):
                pos = base + j - m
                ud[j, i] = hist[pos, i] if pos >= 0 else 0.0
        return ud

    # ------------------------------------------------------------------ batch window (harness path)
    def free_run_window(self, win_cmds, pose0: Pose, velb0: Vel, dt: float, prev_cmds=None) -> np.ndarray:
        """Teleport, stream the window, collect the vision, align: ``pose_sim`` (H + 1, 3)."""
        if self.rx is None:
            self.open()
        assert self.rx is not None
        dt = float(dt)
        ud = self._delayed_stream(win_cmds, prev_cmds, dt)
        H = len(ud)
        x0, y0, th0 = (float(v) for v in pose0)
        c, s = math.cos(th0), math.sin(th0)
        velw0 = (c * velb0[0] - s * velb0[1], s * velb0[0] + c * velb0[1], float(velb0[2]))
        wps = self._wall_per_sim
        self._drain_tx()
        # send phase: the simulator applies a datagram at its next physics tick; vision frames arrive right
        # after a tick, so scheduling the sends half a period after a frame arrival keeps every command (and
        # the teleport) safely inside one tick interval instead of straddling a boundary
        t_start = _clock() + self.lead_s
        last = self.rx.latest()
        if last is not None and self._period_wall > 0:
            n = math.ceil((t_start - last.t_recv) / self._period_wall - 0.5)
            t_start = last.t_recv + (n + 0.5) * self._period_wall
        self._sleep_until(t_start)
        T0 = _clock()
        if last is not None:
            self.stats.send_phase.append(((T0 - last.t_recv) / self._period_wall) % 1.0)
        before = self.rx.latest()                    # every frame up to this one was captured before the teleport
        self._send_simcontrol(self.teleport_msg((x0, y0, th0), velw0))
        self.stats.teleports += 1
        self._send_control(ud[0])
        jit = []
        for k in range(1, H):
            t_k = T0 + k * dt * wps
            self._sleep_until(t_k)
            jit.append(_clock() - t_k)
            self._send_control(ud[k])
        t_end = T0 + (H * dt + self.tail_s) * wps
        k = H
        while _clock() < t_end:                              # keep the last command alive during the tail
            t_k = T0 + k * dt * wps
            self._sleep_until(min(t_k, t_end))
            self._send_control(ud[-1])
            k += 1
        if jit:
            aj = np.abs(jit)
            self.stats.send_jitter_max = max(self.stats.send_jitter_max, float(aj.max()))
            self.stats.send_late += int((aj > LATE_SEND_S).sum())
            self.stats._jit_sum += float(aj.sum())
            self.stats._jit_n += len(jit)
            self.stats.send_jitter_mean = self.stats._jit_sum / self.stats._jit_n
        self._drain_tx()
        # frames captured after the teleport: skip those still in flight when it was sent (vision delay)
        # frames captured after the teleport: everything received up to the teleport is out by frame number
        # (robust to a stalled receiver); frames still in flight at the teleport (vision delay) show the old
        # pose and are skipped by the anchor's pose check
        frames = self.rx.since(T0 - self._period_wall)
        if before is not None:
            frames = [f for f in frames if f.camera_id != before.camera_id or f.frame_number > before.frame_number]
        self.stats.vision_gaps = self.rx.gaps
        self.stats.decode_errors = self.rx.decode_errors
        self.stats.windows += 1
        period_sim = 1.0 / self._rate_sim
        anchor = find_anchor(frames[:ANCHOR_SEARCH_FRAMES], (x0, y0, th0), velw0, period_sim, self.tol_pos,
                             self.tol_ang)
        pose_sim = np.full((H + 1, 3), np.nan)
        pose_sim[0] = (x0, y0, th0)
        if anchor is None:
            self.stats.anchor_failures += 1
            log.warning("%s: teleport not seen in %d frames (window at %.2f, %.2f)", self.ep.name, len(frames), x0, y0)
            self._set_state(pose_sim, velb0)
            return pose_sim
        tau = estimate_tau0(frames[anchor].pose, (x0, y0, th0), velw0, period_sim)
        if tau is not None:
            raw = estimate_tau0(frames[anchor].pose, (x0, y0, th0), velw0, 10.0 * period_sim)
            if raw is not None and raw > 1.5 * period_sim:      # the anchor is not the first post-teleport frame
                self.stats.anchor_late += 1
                log.debug("%s: anchor %.1f frames after the teleport (window at %.2f, %.2f)", self.ep.name,
                          raw / period_sim, x0, y0)
            self._tau0_hist.append(tau)
            self.stats.tau0_estimated += 1
        else:
            tau = float(np.median(self._tau0_hist)) if self._tau0_hist else 0.5 * period_sim
        self.stats.tau0.append(float(tau))
        pose_sim, n_used = interpolate_poses(frames, anchor, tau, self._capture_scale, dt, H, (x0, y0, th0),
                                             frame_period=period_sim if self.ep.vision_rate else None)
        self.stats.frames_used.append(n_used)
        if np.isnan(pose_sim[1:]).any():
            self.stats.short_windows += 1
        self._set_state(pose_sim, velb0)
        return pose_sim

    def _set_state(self, pose_sim: np.ndarray, velb0) -> None:
        last = pose_sim[np.isfinite(pose_sim).all(axis=1)][-1]
        self.x, self.y, self.th = (float(v) for v in last)
        self._vbody = np.asarray(velb0, dtype=float)

    @staticmethod
    def _sleep_until(t: float) -> None:
        """Sleep (releasing the GIL) until ~0.4 ms before ``t``, then spin: the receiver thread and an
        in-process ``SimServer`` (tests) keep running."""
        while True:
            rem = t - _clock()
            if rem <= 0.0:
                return
            if rem > SPIN_S + 0.0002:
                time.sleep(rem - SPIN_S)

    # ------------------------------------------------------------------ step-wise Plant API
    def reset(self, pose0: Pose, velb0: Vel = (0.0, 0.0, 0.0)) -> None:
        if self.rx is None:
            self.open()
        x0, y0, th0 = (float(v) for v in pose0)
        c, s = math.cos(th0), math.sin(th0)
        velw0 = (c * velb0[0] - s * velb0[1], s * velb0[0] + c * velb0[1], float(velb0[2]))
        self._drain_tx()
        self._send_simcontrol(self.teleport_msg((x0, y0, th0), velw0))
        self.stats.teleports += 1
        self.x, self.y, self.th = x0, y0, th0
        self._vbody = np.asarray(velb0, dtype=float)
        self._hist, self._base, self._k = [], 0, 0
        last = self.rx.latest()
        self._t_last_tick = last.t_capture if last is not None else None

    def prime_delay(self, prev_cmds) -> None:
        prev = [np.asarray(c, dtype=float).reshape(3) for c in prev_cmds]
        if self.delay == "theta":
            self._hist, self._base = prev, len(prev)

    def _tap(self, cmd: np.ndarray, dt: float) -> np.ndarray:
        if self.delay != "theta":
            return cmd
        j = self._k
        self._hist.append(cmd)
        ud = np.zeros(3)
        for i in range(3):
            src = j if self._Td[i] <= 0.0 else int(math.floor(j - self._Td[i] / dt + 1e-9))
            pos = src + self._base
            if 0 <= pos < len(self._hist):
                ud[i] = self._hist[pos][i]
        self._k = j + 1
        return ud

    def step(self, cmd: Vel, dt: float) -> Pose:
        """Send the command, wait for the next vision tick that shows the robot, return its pose."""
        assert self.rx is not None
        u = self._tap(np.asarray(cmd, dtype=float).reshape(3), float(dt))
        self._send_control(u)
        deadline = _clock() + max(0.5, 4.0 * self._period_wall)
        t_prev = self._t_last_tick
        while _clock() < deadline:
            last = self.rx.latest()
            if last is not None and last.pose is not None and (t_prev is None or last.t_capture > t_prev + 1e-6):
                self._t_last_tick = last.t_capture
                x, y, th = last.pose
                if abs(th - self.th) > math.pi:
                    th = self.th + math.atan2(math.sin(th - self.th), math.cos(th - self.th))
                self.x, self.y, self.th = x, y, th
                return (self.x, self.y, self.th)
            time.sleep(0.0005)
        return (self.x, self.y, self.th)


# --------------------------------------------------------------------------------------
# Probe CLI: python -m dtssl.sim.protocol_plant --sim grsim
# --------------------------------------------------------------------------------------
def probe(name: str, seconds: float = 2.0) -> dict:
    """Connect, measure the vision cadence, teleport once and stream one short window; print a summary."""
    ep = load_endpoint(name)
    p = ProtocolPlant(ep, delay=None, probe_s=min(seconds, 1.0))
    try:
        H = 60
        cmds = np.tile([0.5, 0.0, 0.0], (H, 1))
        pose = p.free_run_window(cmds, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), p.dt)
        ok = np.isfinite(pose).all()
        moved = float(np.hypot(*(pose[-1, :2] - pose[0, :2]))) if ok else float("nan")
        out = dict(endpoint=ep.name, stats=p.stats.as_dict(), window_ok=bool(ok), moved_m=moved,
                   expected_m=0.5 * H * p.dt)
    finally:
        p.close()
    return out


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="probe an external ssl-simulation-protocol simulator")
    ap.add_argument("--sim", default="dtssl", help="name in config/external_sims.json")
    ap.add_argument("--seconds", type=float, default=2.0)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    out = probe(a.sim, a.seconds)
    print(json.dumps(out, indent=2, default=str))
    return 0 if out["window_ok"] else 1


__all__ = ["Endpoint", "load_endpoints", "load_endpoint", "Frame", "VisionReceiver", "ProtocolPlant",
           "ProtocolStats", "find_anchor", "estimate_tau0", "interpolate_poses", "unwrap_series", "probe"]

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
