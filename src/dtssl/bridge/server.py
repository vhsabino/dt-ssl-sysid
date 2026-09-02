"""``SimServer``: the grSim drop-in = world + vision publisher + control + simulation control.

    world = make_world("fopdt", n_blue=6, n_yellow=6)
    with SimServer(world, BridgeConfig.load()) as srv:
        srv.run(duration=None)            # real-time loop at vision.rate_hz until stop()

    srv = SimServer(world, cfg, step_mode=True); srv.start()
    srv.tick()                            # one world step + one vision packet (tests / GUI)

Real-time loop: monotonic clock, one tick per ``1 / (rate_hz * speed)`` seconds, sleeping
until the next deadline; a tick that starts late counts in ``late_ticks`` and the schedule
re-anchors when it falls more than ``max_lag_s`` behind (no burst catch-up). Network I/O
runs in the receive threads of :class:`ControlServer` / :class:`SimControlServer`; the world
lock serialises them with ``tick``. ``stats`` (Hz achieved, packets per port, watchdog hits,
world counters) is safe to read from another thread (GUI status bar).
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque

from dtssl.bridge.config import BridgeConfig, as_bridge_config
from dtssl.bridge.control import ControlServer
from dtssl.bridge.simcontrol import SimControlServer
from dtssl.bridge.vision import VisionPublisher
from dtssl.sim.entities import WorldState

log = logging.getLogger(__name__)


class SimServer:
    def __init__(self, world, config: BridgeConfig | dict | str | None = None, *,
                 step_mode: bool = False, recorder=None, speed: float | None = None,
                 threaded_receivers: bool = True, hz_window_s: float = 2.0, max_lag_s: float = 0.5,
                 vision_seed: int | None = None):
        self.world = world
        self.cfg = as_bridge_config(config)
        self.step_mode = bool(step_mode)
        self.recorder = recorder
        self.speed = float(self.cfg.sim.speed if speed is None else speed)
        self.threaded_receivers = bool(threaded_receivers)
        self.max_lag_s = float(max_lag_s)
        self._hz_window_s = float(hz_window_s)
        self._tick_times: deque[float] = deque()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._running = False
        self.started = False
        self.ticks = 0
        self.late_ticks = 0
        self.last_state: WorldState | None = None
        self.t_start: float | None = None
        ball_model = getattr(world, "ball_params", None)
        self.vision = VisionPublisher(self.cfg, world.field, ball_radius=getattr(ball_model, "radius", 0.0215),
                                      robot_radius=world.spec.radius, robot_height=world.spec.height,
                                      ball_model=ball_model, open_socket=False, seed=vision_seed)
        self.control = ControlServer(world, self.cfg, state_provider=self._latest_state)
        self.simcontrol = SimControlServer(world, self.cfg, speed_setter=self.set_speed,
                                           vision_port_setter=self.set_vision_port)
        if hasattr(world, "watchdog_s"):
            world.watchdog_s = float(self.cfg.control.watchdog_s)

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        if self.started:
            return
        self.vision.open()
        self.control.start(threaded=self.threaded_receivers)
        self.simcontrol.start(threaded=self.threaded_receivers)
        self._stop.clear()
        self.started = True
        self.t_start = time.monotonic()
        if self.recorder is not None and hasattr(self.recorder, "record_initial"):
            self.recorder.record_initial(self.world.state())
        log.info("SimServer started: vision -> %s, control blue/yellow %d/%d, simcontrol %d, backend %s, %s",
                 self.vision.targets, self.control.port("blue"), self.control.port("yellow"),
                 self.simcontrol.port, getattr(self.world, "name", type(self.world).__name__),
                 "step mode" if self.step_mode else f"real-time x{self.speed:g}")

    def stop(self) -> None:
        self._stop.set()
        if not self.started:
            return
        self.control.stop()
        self.simcontrol.stop()
        self.vision.close()
        self.started = False

    def close(self) -> None:
        self.stop()
        try:
            self.world.close()
        except Exception:  # noqa: BLE001
            pass

    def __enter__(self) -> SimServer:
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ------------------------------------------------------------------ stepping
    def _latest_state(self) -> WorldState:
        ws = self.last_state
        return ws if ws is not None else self.world.state()

    def tick(self) -> WorldState:
        """One simulation step + vision publish (+ recorder). Thread-safe."""
        with self._lock:
            if not self.threaded_receivers and self.started:
                self.control.poll()
                self.simcontrol.poll()
            ws = self.world.step()
            self.last_state = ws
            if self.started:
                self.vision.publish(ws)
            if self.recorder is not None:
                self.recorder.record(ws, getattr(self.world, "commands", {}))
            self.ticks += 1
            now = time.monotonic()
            self._tick_times.append(now)
            horizon = now - self._hz_window_s
            while self._tick_times and self._tick_times[0] < horizon:
                self._tick_times.popleft()
            return ws

    def run(self, duration: float | None = None) -> int:
        """Real-time loop (blocking). Returns the number of ticks executed."""
        if not self.started:
            self.start()
        self._running = True
        self._stop.clear()
        n0 = self.ticks
        t_end = None if duration is None else time.monotonic() + float(duration)
        next_t = time.monotonic()
        try:
            while not self._stop.is_set():
                now = time.monotonic()
                if t_end is not None and now >= t_end:
                    break
                if now < next_t:
                    time.sleep(min(next_t - now, 0.05))
                    continue
                if now - next_t > self.period:
                    self.late_ticks += 1
                if now - next_t > self.max_lag_s:        # too far behind: re-anchor, no catch-up
                    next_t = now
                self.tick()
                next_t += self.period
        finally:
            self._running = False
        return self.ticks - n0

    def run_in_thread(self, duration: float | None = None) -> threading.Thread:
        t = threading.Thread(target=self.run, args=(duration,), name="dtssl-simserver", daemon=True)
        t.start()
        return t

    @property
    def period(self) -> float:
        return 1.0 / (float(self.cfg.vision.rate_hz) * max(self.speed, 1e-6))

    @property
    def running(self) -> bool:
        return self._running

    def set_speed(self, speed: float) -> None:
        self.speed = float(speed)

    def set_vision_port(self, port: int) -> None:
        self.cfg.vision.port = int(port)
        self.vision.cfg.port = int(port)
        self.vision.targets = self.vision.cfg.targets()
        log.info("vision port changed to %d", port)

    # ------------------------------------------------------------------ stats
    @property
    def hz_actual(self) -> float:
        n = len(self._tick_times)
        if n < 2:
            return 0.0
        span = self._tick_times[-1] - self._tick_times[0]
        return (n - 1) / span if span > 0 else 0.0

    @property
    def stats(self) -> dict:
        w = self.world
        return {
            "ticks": self.ticks,
            "late_ticks": self.late_ticks,
            "hz_actual": self.hz_actual,
            "hz_target": float(self.cfg.vision.rate_hz) * self.speed,
            "speed": self.speed,
            "step_mode": self.step_mode,
            "sim_time": getattr(w, "t", None),
            "watchdog_hits": getattr(w, "watchdog_hits", None),
            "kicks": getattr(w, "kicks", None),
            "vision": self.vision.stats,
            "control": self.control.stats.as_dict(),
            "simcontrol": self.simcontrol.stats,
            "packets": {
                "vision": self.vision.packets_sent,
                "blue": self.control.stats.blue.packets,
                "yellow": self.control.stats.yellow.packets,
                "simcontrol": self.simcontrol.packets,
            },
        }


__all__ = ["SimServer"]
