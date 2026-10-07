"""``Controller``: owns the world, the optional ``SimServer``, the joystick and the timers.

Modes (``set_mode``):

* ``debug`` — the joystick/keyboard drives the selected robot of a local world created with
  ``make_world(backend)``; a 60 Hz wall-clock accumulator (5 ms ``QTimer``) steps the world
  (``world.step()``), or ticks a step-mode ``SimServer`` when ``publish`` is on so external
  tools receive vision / can command the other robots;
* ``bridge`` — ``SimServer`` on the chosen backend/config: real-time loop in a thread
  (``run_in_thread``) and the GUI polls ``server.last_state`` (produced under the server lock),
  or, with ``realtime=False``, the GUI timer ticks the server in step mode. Teleports and
  parameter hot-swaps are allowed; the joystick only selects robots;
* ``replay`` — a :class:`~dtssl.gui.replay.ReplaySession` (dataset event, free-run of the
  current θ vs truth); play/pause/scrub/speed.

Views subscribe to ``frame_ready`` (30 Hz, :class:`Frame`), ``sample_ready`` (60 Hz, plot data
of the selected robot), ``stats_ready`` (2 Hz, status bar) and ``message``.

The field is a :class:`~dtssl.config.FieldPreset` (``divB`` by default, ``divA`` or a field JSON): ``set_field``
rebuilds the world on the new geometry, like ``set_backend`` does, and the number of robots per team on the
field follows the division (6 in B, 11 in A) unless ``n_active`` pins it.
"""
from __future__ import annotations

import logging
import math
import threading
import time
from collections import deque
from dataclasses import dataclass, replace
from pathlib import Path

from PySide6 import QtCore
from PySide6.QtCore import Signal

from dtssl.config import FieldPreset, load_field_preset
from dtssl.gui.joystick import (
    EVENT_NEXT_ROBOT,
    EVENT_PREV_ROBOT,
    EVENT_STOP,
    EVENT_TELEPORT_CENTER,
    CmdLimits,
    JoyMap,
    JoystickReader,
)
from dtssl.gui.keyboard import KeyboardProvider
from dtssl.gui.replay import ReplaySession, horizons_from_config
from dtssl.models.params import DofParam, load_twin_params
from dtssl.sim.backends import available, make_world
from dtssl.sim.entities import ROSTER_SIZE, BallState, RobotCmd, RobotState, Scene, WorldState
from dtssl.sim.world import World

log = logging.getLogger(__name__)

MODES: tuple[str, ...] = ("debug", "bridge", "replay")
Key = tuple[str, int]


@dataclass
class Frame:
    """What the field view needs at 30 Hz."""

    ws: WorldState
    t: float
    selected: Key | None
    truth_pose: tuple[float, float, float] | None = None
    show_ball: bool = True
    replay_index: int | None = None
    mode: str = "debug"


def commanded(world: World, key: Key) -> RobotCmd:
    """Latest command applied to a robot, whatever the backend (TwinWorld / MuJoCoWorld)."""
    fn = getattr(world, "effective_command", None)
    if fn is not None:
        try:
            return fn(*key)
        except Exception:  # noqa: BLE001
            pass
    cmds = getattr(world, "commands", None)
    if isinstance(cmds, dict) and key in cmds:
        return cmds[key]
    robots = getattr(world, "robots", None)
    if isinstance(robots, dict) and key in robots and hasattr(robots[key], "cmd"):
        return robots[key].cmd
    return RobotCmd()


class Controller(QtCore.QObject):
    frame_ready = Signal(object)                    # Frame
    sample_ready = Signal(float, object, object, object)   # t, cmd(3), sim(3), truth(3) | None
    stats_ready = Signal(dict)
    mode_changed = Signal(str)
    backend_changed = Signal(str)
    field_changed = Signal(str)                     # FieldPreset.name (world rebuilt on the new geometry)
    selection_changed = Signal(object)              # Key | None
    replay_loaded = Signal(object)                  # ReplaySession
    replay_changed = Signal(object)                 # ReplaySession (recompute / seek)
    server_changed = Signal(bool)                   # running?
    message = Signal(str)
    joystick_event = Signal(str)

    def __init__(self, backend: str = "fopdt", mode: str = "debug", team: str = "yellow", *,
                 bridge_config: str | Path | dict | None = None, joy_map: JoyMap | str | Path | None = None,
                 n_blue: int = ROSTER_SIZE, n_yellow: int = ROSTER_SIZE, n_active: int | None = None,
                 field: FieldPreset | str | Path | None = None,
                 publish: bool = False, realtime: bool | None = None,
                 params: dict[str, DofParam] | None = None, world_opts: dict | None = None,
                 use_pygame: bool | None = None, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.team = team
        self.n_blue, self.n_yellow = int(n_blue), int(n_yellow)
        self.field_preset: FieldPreset = field if isinstance(field, FieldPreset) else load_field_preset(field)
        self.n_active_pinned = None if n_active is None else int(n_active)   # --n-active: overrides the division
        self.publish = bool(publish)
        self.world_opts = dict(world_opts or {})
        self.params: dict[str, DofParam] = params or load_twin_params()
        self.speed = 1.0
        self.mode = "debug"
        self.selected: Key | None = None
        self.replay: ReplaySession | None = None
        self.bridge_config_src = bridge_config
        self.bridge_cfg = self._load_bridge_config(bridge_config)
        self.realtime = bool(self.bridge_cfg.sim.realtime if realtime is None else realtime)
        self.server = None
        self._server_thread: threading.Thread | None = None
        self._last_frame_seen = -1
        self._ws: WorldState | None = None
        self._tick_times: deque[float] = deque()
        self._t_last = time.monotonic()
        self._acc = 0.0
        self._pkt_prev: dict[str, int] = {}
        self._pkt_t_prev = time.monotonic()
        self._pkt_rate: dict[str, float] = {}
        self.running = False
        self.joy_cmd = RobotCmd()
        self.pending_messages: list[str] = []          # emitted before any listener connected
        self.message.connect(self.pending_messages.append)
        self.kb = KeyboardProvider()
        jm = joy_map if isinstance(joy_map, JoyMap) or joy_map is None else JoyMap.load(joy_map)
        self.world: World = self._make_world(backend)
        self.joystick = JoystickReader(CmdLimits.from_spec(self.world.spec), jm, fallback=self.kb,
                                       use_pygame=use_pygame)

        self._sim_timer = QtCore.QTimer(self)
        self._sim_timer.setTimerType(QtCore.Qt.PreciseTimer)
        self._sim_timer.setInterval(5)
        self._sim_timer.timeout.connect(self._on_sim_tick)
        self._joy_timer = QtCore.QTimer(self)
        self._joy_timer.setTimerType(QtCore.Qt.PreciseTimer)
        self._joy_timer.setInterval(8)                   # ~120 Hz
        self._joy_timer.timeout.connect(self._on_joy_tick)
        self._render_timer = QtCore.QTimer(self)
        self._render_timer.setInterval(33)               # ~30 Hz
        self._render_timer.timeout.connect(self._on_render)
        self._stats_timer = QtCore.QTimer(self)
        self._stats_timer.setInterval(500)
        self._stats_timer.timeout.connect(self._on_stats)
        self._select_default()
        self.set_mode(mode, force=True)

    # ------------------------------------------------------------------ construction helpers
    @staticmethod
    def _load_bridge_config(src):
        from dtssl.bridge.config import as_bridge_config

        try:
            return as_bridge_config(src)
        except Exception as e:  # noqa: BLE001 - keep the GUI usable without config/bridge.json
            log.warning("bridge config %r unavailable (%s); using defaults", src, e)
            from dtssl.bridge.config import BridgeConfig

            return BridgeConfig()

    def _make_world(self, backend: str) -> World:
        opts = dict(self.world_opts)
        opts.setdefault("n_blue", self.n_blue)
        opts.setdefault("n_yellow", self.n_yellow)
        opts.setdefault("n_active", self.n_active)
        opts.setdefault("field", self.field_preset.field)
        if backend != "ideal":
            opts.setdefault("params", self.params)
        world = make_world(backend, **opts)
        self._ws = world.state()
        self._last_frame_seen = -1
        return world

    def _select_default(self) -> None:
        keys = self.robot_keys(self.team)
        self.selected = keys[0] if keys else (self.robot_keys()[0] if self.robot_keys() else None)

    def drain_messages(self) -> list[str]:
        """Messages emitted during construction (e.g. a SimServer bind failure); stops buffering."""
        try:
            self.message.disconnect(self.pending_messages.append)
        except (RuntimeError, TypeError):
            pass
        out, self.pending_messages = list(self.pending_messages), []
        return out

    # ------------------------------------------------------------------ properties
    @property
    def ts(self) -> float:
        return float(getattr(self.world, "ts", 1.0 / 60.0))

    @property
    def n_active(self) -> int:
        """Robots per team on the field at a reset: ``n_active`` given to the constructor, else the division of the
        current field (6 in Division B, 11 in Division A); the rest of the roster waits parked."""
        return self.field_preset.robots_per_team if self.n_active_pinned is None else self.n_active_pinned

    @property
    def field_name(self) -> str:
        return self.field_preset.name

    @property
    def server_running(self) -> bool:
        return self.server is not None and self.server.started

    def backends(self) -> list[str]:
        return available()

    def latest_state(self) -> WorldState:
        if self._ws is None:
            self._ws = self.world.state()
        return self._ws

    def robot_keys(self, team: str | None = None, present: bool | None = True) -> list[Key]:
        """Robots of ``team`` (both teams when None): in play (``present=True``, default), parked (``False``) or
        all (``None``)."""
        ws = self.latest_state()
        return [k for k, r in sorted(ws.robots.items())
                if (present is None or r.present == present) and (team is None or k[0] == team)]

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self._t_last = time.monotonic()
        self._acc = 0.0
        self._sim_timer.start()
        self._joy_timer.start()
        self._render_timer.start()
        self._stats_timer.start()

    def stop(self) -> None:
        self.running = False
        for t in (self._sim_timer, self._joy_timer, self._render_timer, self._stats_timer):
            t.stop()

    def shutdown(self) -> None:
        """Stop timers, the server thread, the joystick and the world (idempotent)."""
        self.stop()
        self.stop_server()
        try:
            self.joystick.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            self.world.close()
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------ modes / backend
    def set_mode(self, mode: str, force: bool = False) -> None:
        mode = mode.lower()
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
        if mode == self.mode and not force:
            return
        self.stop_server()
        self.mode = mode
        self._acc = 0.0
        self._tick_times.clear()
        if mode == "debug":
            if self.publish:
                self._start_server(step_mode=True)
        elif mode == "bridge":
            self._start_server(step_mode=not self.realtime)
        elif mode == "replay":
            if self.replay is not None:
                self.replay.pause()
        self.mode_changed.emit(mode)

    def set_publish(self, on: bool) -> None:
        self.publish = bool(on)
        if self.mode == "debug":
            if self.publish and not self.server_running:
                self._start_server(step_mode=True)
            elif not self.publish and self.server_running:
                self.stop_server()

    def set_realtime(self, on: bool) -> None:
        self.realtime = bool(on)
        if self.mode == "bridge":
            self.set_mode("bridge", force=True)

    def set_speed(self, speed: float) -> None:
        self.speed = max(0.05, float(speed))
        if self.replay is not None:
            self.replay.set_speed(self.speed)
        if self.server is not None and self.mode == "bridge":
            self.server.set_speed(self.speed)

    def set_backend(self, backend: str) -> None:
        if backend == self.backend:
            return
        if backend not in available():
            raise KeyError(f"unknown backend {backend!r}; available: {available()}")
        was_server = self.server_running
        self.stop_server()
        old = self.world
        try:
            self.world = self._make_world(backend)
        except Exception as e:  # noqa: BLE001 - e.g. mujoco missing
            self.message.emit(f"backend {backend} failed: {e}")
            self.world = old
            if was_server:
                self._start_server(step_mode=(self.mode == "debug") or not self.realtime)
            return
        try:
            old.close()
        except Exception:  # noqa: BLE001
            pass
        self.backend = backend
        self.joystick.limits = CmdLimits.from_spec(self.world.spec)
        self._select_default()
        if was_server:
            self._start_server(step_mode=(self.mode == "debug") or not self.realtime)
        if self.replay is not None:
            self.replay.plant_kind = "ideal" if backend == "ideal" else "fopdt"
            self.replay.recompute(self.params)
            self.replay_changed.emit(self.replay)
        self.backend_changed.emit(backend)
        self.selection_changed.emit(self.selected)

    def set_field(self, field: FieldPreset | str | Path) -> None:
        """Rebuild the world on another field (preset name, JSON path or :class:`FieldPreset`): the roster is
        re-spawned with the division's robots on the field, θ is kept and a running server is restarted (it
        publishes the new geometry). Replay keeps its own session; the local world is rebuilt anyway."""
        try:
            preset = field if isinstance(field, FieldPreset) else load_field_preset(field)
        except Exception as e:  # noqa: BLE001 - missing or invalid field JSON
            self.message.emit(f"field {Path(str(field)).stem} failed: {e}")
            return
        if preset == self.field_preset:
            return
        was_server = self.server_running
        self.stop_server()
        old, old_preset = self.world, self.field_preset
        self.field_preset = preset
        try:
            self.world = self._make_world(self.backend)
        except Exception as e:  # noqa: BLE001 - keep the old world on any failure
            self.message.emit(f"field {preset.label} failed: {e}")
            self.field_preset, self.world = old_preset, old
            if was_server:
                self._start_server(step_mode=(self.mode == "debug") or not self.realtime)
            return
        try:
            old.close()
        except Exception:  # noqa: BLE001
            pass
        self._select_default()
        if was_server:
            self._start_server(step_mode=(self.mode == "debug") or not self.realtime)
        self.field_changed.emit(preset.name)
        self.selection_changed.emit(self.selected)

    def reset_scene(self) -> None:
        f = self.world.field
        scene = Scene.default(self.n_blue, self.n_yellow, f.length, f.width, n_active=self.n_active,
                              boundary_width_m=f.boundary_width)
        self.world.reset(scene)
        self._ws = self.world.state()
        self._select_default()
        self.selection_changed.emit(self.selected)

    # ------------------------------------------------------------------ server
    def _start_server(self, step_mode: bool) -> bool:
        from dtssl.bridge.server import SimServer

        self.stop_server()
        try:
            self.server = SimServer(self.world, self.bridge_cfg, step_mode=step_mode, speed=self.speed)
            self.server.start()
        except Exception as e:  # noqa: BLE001 - port in use, no network ...
            self.message.emit(f"SimServer failed to start: {e}")
            self.server = None
            self.server_changed.emit(False)
            return False
        self._pkt_prev = {}
        if not step_mode:
            self._server_thread = self.server.run_in_thread()
        self.message.emit(f"SimServer started ({'step mode' if step_mode else 'real-time thread'}): "
                          f"vision {self.server.vision.targets}, control {self.server.control.port('blue')}/"
                          f"{self.server.control.port('yellow')}, simcontrol {self.server.simcontrol.port}")
        self.server_changed.emit(True)
        return True

    def stop_server(self) -> None:
        srv, self.server = self.server, None
        if srv is None:
            return
        try:
            srv.stop()
        except Exception:  # noqa: BLE001
            pass
        th, self._server_thread = self._server_thread, None
        if th is not None and th.is_alive():
            th.join(timeout=1.0)
        self.server_changed.emit(False)

    # ------------------------------------------------------------------ selection / teleports
    def select(self, key: Key | None) -> None:
        if key is not None:
            key = (str(key[0]), int(key[1]))
        if key == self.selected:
            return
        self.selected = key
        self.selection_changed.emit(key)

    def select_team(self, team: str) -> None:
        self.team = team
        keys = self.robot_keys(team)
        if keys and (self.selected is None or self.selected[0] != team):
            self.select(keys[0])

    def _cycle(self, step: int) -> None:
        keys = self.robot_keys(self.team) or self.robot_keys()
        if not keys:
            return
        if self.selected in keys:
            i = (keys.index(self.selected) + step) % len(keys)
        else:
            i = 0
        self.select(keys[i])

    def select_next(self) -> None:
        self._cycle(+1)

    def select_prev(self) -> None:
        self._cycle(-1)

    def teleport_selected(self, x: float, y: float, theta: float | None = None) -> bool:
        if self.mode == "replay" or self.selected is None:
            return False
        key = self.selected
        ws = self.latest_state()
        th = ws.robots[key].theta if (theta is None and key in ws.robots) else float(theta or 0.0)
        self.world.teleport_robot(key[0], key[1], float(x), float(y), th)
        self._ws = self.world.state()
        return True

    def teleport_ball(self, x: float, y: float) -> bool:
        if self.mode == "replay":
            return False
        self.world.teleport_ball(float(x), float(y))
        self._ws = self.world.state()
        return True

    # ------------------------------------------------------------------ substitutions
    def park_robot(self, key: Key) -> bool:
        """Take a robot out of play: the world parks it outside the arena walls."""
        if self.mode == "replay":
            return False
        key = (str(key[0]), int(key[1]))
        if key not in self.robot_keys(present=True):
            return False
        self.world.set_present(key[0], key[1], False)
        self._ws = self.world.state()
        if self.selected == key:
            self._select_default()
            self.selection_changed.emit(self.selected)
        return True

    def enter_robot(self, x: float, y: float, team: str | None = None) -> Key | None:
        """Bring the lowest-id parked robot of ``team`` (the joystick team by default) into play at ``(x, y)``,
        facing the opponent goal, and select it. Returns its key, or None when nobody is on the bench."""
        if self.mode == "replay":
            return None
        team = team or self.team
        parked = self.robot_keys(team, present=False)
        if not parked:
            return None
        key = parked[0]
        theta = 0.0 if team == "blue" else math.pi
        self.world.teleport_robot(key[0], key[1], float(x), float(y), theta, present=True)
        self._ws = self.world.state()
        self.select(key)
        return key

    # ------------------------------------------------------------------ parameters
    def apply_params(self, params: dict[str, DofParam]) -> None:
        self.params = dict(params)
        try:
            self.world.set_plant_params(self.params)
        except Exception as e:  # noqa: BLE001
            self.message.emit(f"set_plant_params failed: {e}")
        if self.replay is not None:
            self.replay.recompute(self.params)
            self.replay_changed.emit(self.replay)
        self.message.emit("parameters applied")

    # ------------------------------------------------------------------ replay
    def load_replay(self, label: str, event: str, dataset: str | None = None) -> ReplaySession:
        from dtssl.data.loader import DATASET_DEFAULT

        kind = "ideal" if self.backend == "ideal" else "fopdt"
        sess = ReplaySession.load(label, event, dataset=dataset or DATASET_DEFAULT, params=self.params,
                                  plant_kind=kind, horizons=horizons_from_config())
        sess.set_speed(self.speed)
        self.replay = sess
        rid = int(sess.seg.meta.get("robot_id", 0))
        self.selected = (self.team, rid)
        self.replay_loaded.emit(sess)
        self.selection_changed.emit(self.selected)
        self.message.emit(f"replay {sess.label}/{sess.event}: N={sess.n} ({sess.duration_s:.2f} s), "
                          f"e_pos@h: " + ", ".join(f"{h}={v:.3f}" for h, v in sess.epos_at_horizons().items()))
        return sess

    def replay_play(self) -> None:
        if self.replay is not None:
            self.replay.play()

    def replay_pause(self) -> None:
        if self.replay is not None:
            self.replay.pause()

    def replay_toggle(self) -> bool:
        return self.replay.toggle() if self.replay is not None else False

    def replay_seek(self, index: int) -> None:
        if self.replay is not None:
            self.replay.seek(index)
            self.replay_changed.emit(self.replay)

    # ------------------------------------------------------------------ ticks
    def _apply_joystick(self) -> None:
        """Debug: the joystick command goes to the selected robot at every world step (ZOH grid)."""
        if self.mode != "debug" or self.selected is None:
            return
        self.world.set_command(self.selected[0], self.selected[1], replace(self.joy_cmd))

    def _step_once(self) -> WorldState:
        self._apply_joystick()
        srv = self.server
        ws = srv.tick() if (srv is not None and srv.started and srv.step_mode) else self.world.step()
        self._ws = ws
        self._record_tick()
        self._emit_sample(ws)
        return ws

    def _record_tick(self) -> None:
        now = time.monotonic()
        self._tick_times.append(now)
        horizon = now - 2.0
        while self._tick_times and self._tick_times[0] < horizon:
            self._tick_times.popleft()

    @property
    def hz_actual(self) -> float:
        if self.mode == "bridge" and self.server is not None and not self.server.step_mode:
            return float(self.server.hz_actual)
        n = len(self._tick_times)
        if n < 2:
            return 0.0
        span = self._tick_times[-1] - self._tick_times[0]
        return (n - 1) / span if span > 0 else 0.0

    def _emit_sample(self, ws: WorldState) -> None:
        key = self.selected
        if key is None or key not in ws.robots:
            return
        r = ws.robots[key]
        c = commanded(self.world, key)
        self.sample_ready.emit(float(ws.t), (c.vx, c.vy, c.w), (r.vx_b, r.vy_b, r.w), None)

    def tick(self, n: int = 1) -> WorldState | None:
        """Advance ``n`` steps synchronously (tests / step button); returns the last state."""
        ws = None
        if self.mode == "replay":
            if self.replay is not None:
                self.replay.seek(self.replay.index + n)
                ws = self._replay_ws()
            return ws
        for _ in range(max(1, int(n))):
            ws = self._step_once()
        return ws

    def _on_sim_tick(self) -> None:
        now = time.monotonic()
        dt = now - self._t_last
        self._t_last = now
        try:
            if self.mode == "replay":
                if self.replay is not None and self.replay.playing:
                    self.replay.advance(dt)
                return
            srv = self.server
            if self.mode == "bridge" and srv is not None and srv.started and not srv.step_mode:
                ws = srv.last_state
                if ws is not None and ws.frame != self._last_frame_seen:
                    self._last_frame_seen = ws.frame
                    self._ws = ws
                    self._emit_sample(ws)
                return
            self._acc += dt * self.speed
            ts = self.ts
            n = 0
            while self._acc >= ts and n < 4:
                self._acc -= ts
                n += 1
                self._step_once()
            if n >= 4 and self._acc > ts:
                self._acc = 0.0                            # drop the backlog instead of spiralling
        except Exception as e:  # noqa: BLE001 - keep the GUI alive, report once
            log.exception("simulation tick failed")
            self.message.emit(f"simulation stopped: {e}")
            self._sim_timer.stop()

    def _on_joy_tick(self) -> None:
        try:
            cmd, events = self.joystick.read()
        except Exception as e:  # noqa: BLE001
            log.warning("joystick read failed: %s", e)
            return
        self.joy_cmd = cmd
        for ev in events:
            self._handle_joy_event(ev)

    def _handle_joy_event(self, ev: str) -> None:
        self.joystick_event.emit(ev)
        if ev == EVENT_NEXT_ROBOT:
            self.select_next()
        elif ev == EVENT_PREV_ROBOT:
            self.select_prev()
        elif ev == EVENT_TELEPORT_CENTER:
            if self.mode != "replay" and self.selected is not None:
                self.world.teleport_robot(self.selected[0], self.selected[1], 0.0, 0.0, 0.0)
        elif ev == EVENT_STOP:
            if self.mode == "debug" and self.selected is not None:
                self.world.set_command(self.selected[0], self.selected[1], RobotCmd())
        elif ev.startswith("connected:") or ev == "disconnected":
            self.message.emit(f"joystick {ev.replace(':', ': ', 1)}")

    def _replay_ws(self) -> WorldState | None:
        rp = self.replay
        if rp is None or self.selected is None:
            return None
        s = rp.sample()
        team, rid = self.selected
        x, y, th = s["pose_sim"]
        vb = s["velb_sim"]
        robot = RobotState(team=team, id=rid, x=x, y=y, theta=math.atan2(math.sin(th), math.cos(th)),
                           vx_b=vb[0], vy_b=vb[1], w=vb[2], has_ball=False, present=True)
        return WorldState(t=s["t"], frame=s["i"], robots={(team, rid): robot}, ball=BallState(x=1e3, y=1e3))

    def current_frame(self) -> Frame | None:
        if self.mode == "replay":
            ws = self._replay_ws()
            if ws is None:
                return None
            s = self.replay.sample()   # type: ignore[union-attr]
            return Frame(ws=ws, t=s["t"], selected=self.selected, truth_pose=s["pose_truth"], show_ball=False,
                         replay_index=s["i"], mode="replay")
        ws = self.latest_state()
        return Frame(ws=ws, t=float(ws.t), selected=self.selected, mode=self.mode)

    def _on_render(self) -> None:
        fr = self.current_frame()
        if fr is not None:
            self.frame_ready.emit(fr)

    def stats(self) -> dict:
        w = self.world
        now = time.monotonic()
        st: dict = {
            "mode": self.mode, "backend": self.backend, "world": getattr(w, "name", type(w).__name__),
            "hz": self.hz_actual, "sim_time": float(getattr(w, "t", 0.0)),
            "watchdog_hits": int(getattr(w, "watchdog_hits", 0) or 0), "kicks": int(getattr(w, "kicks", 0) or 0),
            "joystick": self.joystick.name, "joystick_connected": self.joystick.connected,
            "dribbler": self.joystick.dribbler_on, "turbo": self.joystick.turbo,
            "selected": self.selected, "speed": self.speed, "server": self.server_running,
            "packets_per_s": {}, "packets": {}, "late_ticks": 0,
        }
        srv = self.server
        if srv is not None and srv.started:
            try:
                s = srv.stats
                pk = dict(s.get("packets", {}))
                dt = now - self._pkt_t_prev
                if dt > 0.25:
                    self._pkt_rate = {k: (pk[k] - self._pkt_prev.get(k, pk[k])) / dt for k in pk}
                    self._pkt_prev, self._pkt_t_prev = pk, now
                st["packets"] = pk
                st["packets_per_s"] = dict(self._pkt_rate)
                st["late_ticks"] = int(s.get("late_ticks", 0))
                st["ports"] = {"vision": srv.vision.targets, "blue": srv.control.port("blue"),
                               "yellow": srv.control.port("yellow"), "simcontrol": srv.simcontrol.port}
            except Exception:  # noqa: BLE001
                pass
        if self.replay is not None and self.mode == "replay":
            rp = self.replay
            st["replay"] = {"label": rp.label, "event": rp.event, "index": rp.index, "n": rp.n,
                            "t": float(rp.t[rp.index]), "playing": rp.playing, "epos": float(rp.epos[rp.index])}
        return st

    def _on_stats(self) -> None:
        try:
            self.stats_ready.emit(self.stats())
        except Exception as e:  # noqa: BLE001
            log.warning("stats failed: %s", e)


__all__ = ["Controller", "Frame", "MODES", "commanded"]
