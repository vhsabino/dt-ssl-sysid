"""Gamepad (DualSense / PS5 or any SDL controller) -> :class:`RobotCmd` for the Debug mode.

Pure-Python mapping layer over an *input provider* (``pygame`` when available, a
:class:`KeyboardProvider` fallback, or a :class:`FakeProvider` in tests)::

    reader = JoystickReader(limits)          # limits: RobotSpec-like (v_max, w_max, kick_*)
    cmd, events = reader.read()              # poll at 120 Hz from a QTimer
    reader.name, reader.connected            # status bar

Mapping (SDL GameController layout, see :data:`DEFAULT_JOY_MAP`; overridable with a JSON file
through ``--joy-map``):

* left stick ``LY -> vx = -LY * v_max * scale``, ``LX -> vy = -LX * v_max * scale``;
  right stick ``RX -> w = -RX * w_max * scale`` (body frame: x forward, y left, w CCW);
* radial deadzone 0.08 on the left stick + expo 0.3 (``y = (1-e) x + e x^3``); the same 1-D
  curve on ``RX``;
* ``R2`` (trigger, normalised to 0..1) above 0.5 = turbo (``scale = 1.0`` instead of ``0.5``);
* buttons: cross (0) flat kick (``kick_flat_max``), circle (1) chip (``kick_chip_max``,
  ``chip_angle_deg``), R1 (10) dribbler toggle, D-pad left/right (hat or buttons 13/14)
  previous/next robot, Options (6) teleport selected robot to the centre, PS (5) stop;
* hot-plug: devices are re-scanned every ``rescan_s`` (2 s); the DualSense is preferred by
  name (``"DualSense"``, ``"PS5"``, ``"Wireless Controller"``) but any gamepad works.

Headless: pygame is initialised with ``SDL_VIDEODRIVER=dummy`` (no window) and
``SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS=1`` so the pad keeps reporting while the Qt window has
focus. The GameController API (``pygame._sdl2.controller``) is used when SDL recognises the
device (standard button/axis indices on Windows and Linux); otherwise the raw joystick API with
the user map (or :func:`JoyMap.dualsense_raw_linux` for a DualSense on ``hid-playstation``).
"""
from __future__ import annotations

import json
import logging
import math
import os
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Protocol

from dtssl.sim.entities import RobotCmd

log = logging.getLogger(__name__)

#: Standard SDL GameController axis indices.
DEFAULT_AXES: dict[str, int] = {"lx": 0, "ly": 1, "rx": 2, "ry": 3, "l2": 4, "r2": 5}
#: Standard SDL GameController button indices (PlayStation names).
DEFAULT_BUTTONS: dict[str, int] = {
    "cross": 0, "circle": 1, "square": 2, "triangle": 3, "share": 4, "ps": 5, "options": 6,
    "l3": 7, "r3": 8, "l1": 9, "r1": 10, "dpad_up": 11, "dpad_down": 12, "dpad_left": 13, "dpad_right": 14,
}
#: Raw ``pygame.joystick`` layout of a DualSense on Linux ``hid-playstation`` (no GameController mapping).
DUALSENSE_RAW_LINUX_AXES: dict[str, int] = {"lx": 0, "ly": 1, "l2": 2, "rx": 3, "ry": 4, "r2": 5}
DUALSENSE_RAW_LINUX_BUTTONS: dict[str, int] = {
    "cross": 0, "circle": 1, "triangle": 2, "square": 3, "l1": 4, "r1": 5, "l2": 6, "r2": 7,
    "share": 8, "options": 9, "ps": 10, "l3": 11, "r3": 12,
}
#: Raw ``pygame.joystick`` layout of a DualSense on Windows (DirectInput, no HIDAPI mapping).
DUALSENSE_RAW_WINDOWS_AXES: dict[str, int] = {"lx": 0, "ly": 1, "rx": 2, "ry": 3, "l2": 4, "r2": 5}
DUALSENSE_RAW_WINDOWS_BUTTONS: dict[str, int] = {
    "square": 0, "cross": 1, "circle": 2, "triangle": 3, "l1": 4, "r1": 5, "l2": 6, "r2": 7,
    "share": 8, "options": 9, "l3": 10, "r3": 11, "ps": 12,
}

PREFERRED_NAMES: tuple[str, ...] = ("DualSense", "PS5", "Wireless Controller")

EVENT_KICK_FLAT = "kick_flat"
EVENT_KICK_CHIP = "kick_chip"
EVENT_DRIBBLER_ON = "dribbler_on"
EVENT_DRIBBLER_OFF = "dribbler_off"
EVENT_PREV_ROBOT = "prev_robot"
EVENT_NEXT_ROBOT = "next_robot"
EVENT_TELEPORT_CENTER = "teleport_center"
EVENT_STOP = "stop"
EVENT_CONNECTED = "connected"
EVENT_DISCONNECTED = "disconnected"


# =========================================================================== map
@dataclass
class JoyMap:
    """Axis/button indices and the response curve; JSON-serialisable (``--joy-map``)."""

    axes: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_AXES))
    buttons: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_BUTTONS))
    invert: dict[str, bool] = field(default_factory=dict)      # per axis name, e.g. {"ly": true}
    hat_dpad: bool = True                                       # D-pad on hat 0 when no dpad_* buttons
    deadzone: float = 0.08
    expo: float = 0.3
    turbo_threshold: float = 0.5
    turbo_scale: float = 1.0
    normal_scale: float = 0.5
    trigger_range: str = "auto"                                 # "auto" | "signed" (-1..1) | "unit" (0..1)
    name: str = "gamecontroller"

    # ------------------------------------------------------------------ presets
    @staticmethod
    def default() -> JoyMap:
        return JoyMap()

    @staticmethod
    def dualsense_raw_linux() -> JoyMap:
        return JoyMap(axes=dict(DUALSENSE_RAW_LINUX_AXES), buttons=dict(DUALSENSE_RAW_LINUX_BUTTONS),
                      trigger_range="signed", name="dualsense-raw-linux")

    @staticmethod
    def dualsense_raw_windows() -> JoyMap:
        return JoyMap(axes=dict(DUALSENSE_RAW_WINDOWS_AXES), buttons=dict(DUALSENSE_RAW_WINDOWS_BUTTONS),
                      trigger_range="signed", name="dualsense-raw-windows")

    PRESETS = ("gamecontroller", "dualsense-raw-linux", "dualsense-raw-windows")

    @staticmethod
    def preset(name: str) -> JoyMap:
        table = {"gamecontroller": JoyMap.default, "default": JoyMap.default,
                 "dualsense-raw-linux": JoyMap.dualsense_raw_linux,
                 "dualsense-raw-windows": JoyMap.dualsense_raw_windows}
        try:
            return table[name]()
        except KeyError as e:
            raise KeyError(f"unknown joy-map preset {name!r}; presets: {JoyMap.PRESETS}") from e

    # ------------------------------------------------------------------ JSON
    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "base": None, "axes": dict(self.axes), "buttons": dict(self.buttons),
                "invert": dict(self.invert), "hat_dpad": self.hat_dpad, "deadzone": self.deadzone,
                "expo": self.expo, "turbo_threshold": self.turbo_threshold, "turbo_scale": self.turbo_scale,
                "normal_scale": self.normal_scale, "trigger_range": self.trigger_range}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> JoyMap:
        """Partial dicts are merged over the ``base`` preset (default: GameController layout);
        ``"base": null`` (what :meth:`to_dict` writes) takes the tables verbatim."""
        base_name = d.get("base", "gamecontroller")
        base = JoyMap.preset(str(base_name)) if base_name is not None else JoyMap(axes={}, buttons={})
        axes = dict(base.axes)
        axes.update({k: int(v) for k, v in (d.get("axes") or {}).items()})
        buttons = dict(base.buttons)
        buttons.update({k: int(v) for k, v in (d.get("buttons") or {}).items()})
        invert = dict(base.invert)
        invert.update({k: bool(v) for k, v in (d.get("invert") or {}).items()})
        kw = {k: d[k] for k in ("hat_dpad", "deadzone", "expo", "turbo_threshold", "turbo_scale",
                                 "normal_scale", "trigger_range") if k in d}
        return replace(base, axes=axes, buttons=buttons, invert=invert, name=str(d.get("name", base.name)), **kw)

    @staticmethod
    def load(path: str | Path) -> JoyMap:
        """A preset name or a JSON file path."""
        s = str(path)
        if s in JoyMap.PRESETS or s == "default":
            return JoyMap.preset(s)
        with open(Path(path).expanduser(), encoding="utf-8") as f:
            return JoyMap.from_dict(json.load(f))

    def save(self, path: str | Path) -> Path:
        p = Path(path).expanduser()
        p.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
        return p


DEFAULT_JOY_MAP = JoyMap.default()


# =========================================================================== state
@dataclass
class JoystickState:
    """Normalised snapshot of the pad: sticks in [-1, 1], triggers in [0, 1], named buttons."""

    connected: bool = False
    name: str = "keyboard"
    lx: float = 0.0
    ly: float = 0.0
    rx: float = 0.0
    ry: float = 0.0
    l2: float = 0.0
    r2: float = 0.0
    buttons: dict[str, bool] = field(default_factory=dict)
    dpad: tuple[int, int] = (0, 0)
    t: float = 0.0

    def pressed(self, name: str) -> bool:
        return bool(self.buttons.get(name, False))


# =========================================================================== providers
class InputProvider(Protocol):
    """Minimal device abstraction (pygame Controller/Joystick, keyboard, fake)."""

    name: str
    gamecontroller: bool       # True = SDL GameController indices/ranges (triggers 0..1)

    def pump(self) -> None: ...
    def alive(self) -> bool: ...
    def num_axes(self) -> int: ...
    def num_buttons(self) -> int: ...
    def num_hats(self) -> int: ...
    def axis(self, i: int) -> float: ...
    def button(self, i: int) -> bool: ...
    def hat(self, i: int) -> tuple[int, int]: ...


class FakeProvider:
    """Settable provider for tests: ``axes`` (-1..1; triggers 0..1 when ``gamecontroller``)."""

    def __init__(self, name: str = "Fake DualSense", n_axes: int = 6, n_buttons: int = 16, n_hats: int = 1,
                 gamecontroller: bool = True):
        self.name = name
        self.gamecontroller = gamecontroller
        self.axes = [0.0] * n_axes
        self.buttons = [False] * n_buttons
        self.hats = [(0, 0)] * n_hats
        self._alive = True
        self.pumps = 0

    def pump(self) -> None:
        self.pumps += 1

    def alive(self) -> bool:
        return self._alive

    def disconnect(self) -> None:
        self._alive = False

    def num_axes(self) -> int:
        return len(self.axes)

    def num_buttons(self) -> int:
        return len(self.buttons)

    def num_hats(self) -> int:
        return len(self.hats)

    def axis(self, i: int) -> float:
        return float(self.axes[i]) if 0 <= i < len(self.axes) else 0.0

    def button(self, i: int) -> bool:
        return bool(self.buttons[i]) if 0 <= i < len(self.buttons) else False

    def hat(self, i: int) -> tuple[int, int]:
        return self.hats[i] if 0 <= i < len(self.hats) else (0, 0)

    # convenience for tests
    def set_axis(self, i: int, v: float) -> None:
        self.axes[i] = float(v)

    def set_button(self, i: int, down: bool = True) -> None:
        self.buttons[i] = bool(down)

    def set_hat(self, x: int, y: int, i: int = 0) -> None:
        self.hats[i] = (int(x), int(y))


# ----------------------------------------------------------------------------- pygame
def _setup_sdl_env() -> None:
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")


def pygame_available() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("pygame") is not None
    except Exception:  # noqa: BLE001
        return False


class PygameProvider:
    """One opened device: ``pygame._sdl2.controller.Controller`` (preferred) or ``pygame.joystick.Joystick``."""

    def __init__(self, device, gamecontroller: bool, name: str, instance_id: int | None = None):
        self._dev = device
        self.gamecontroller = bool(gamecontroller)
        self.name = name
        self.instance_id = instance_id
        self._alive = True
        self._pg = _import_pygame()

    def pump(self) -> None:
        try:
            self._pg.event.pump()
            if self.gamecontroller:
                from pygame._sdl2 import controller as ctrl  # noqa: PLC0415

                ctrl.update()
        except Exception:  # noqa: BLE001 - video not initialised: the backend re-inits on rescan
            pass

    def alive(self) -> bool:
        if not self._alive:
            return False
        try:
            if self.gamecontroller:
                return bool(self._dev.attached())
            return bool(self._dev.get_init())
        except Exception:  # noqa: BLE001
            return False

    def num_axes(self) -> int:
        try:
            return 6 if self.gamecontroller else int(self._dev.get_numaxes())
        except Exception:  # noqa: BLE001
            return 0

    def num_buttons(self) -> int:
        try:
            return 21 if self.gamecontroller else int(self._dev.get_numbuttons())
        except Exception:  # noqa: BLE001
            return 0

    def num_hats(self) -> int:
        try:
            return 0 if self.gamecontroller else int(self._dev.get_numhats())
        except Exception:  # noqa: BLE001
            return 0

    def axis(self, i: int) -> float:
        try:
            if self.gamecontroller:
                v = float(self._dev.get_axis(i))
                return max(-1.0, min(1.0, v / 32767.0))
            return float(self._dev.get_axis(i))
        except Exception:  # noqa: BLE001
            self._alive = False
            return 0.0

    def button(self, i: int) -> bool:
        try:
            return bool(self._dev.get_button(i))
        except Exception:  # noqa: BLE001
            self._alive = False
            return False

    def hat(self, i: int) -> tuple[int, int]:
        if self.gamecontroller:
            return (0, 0)
        try:
            h = self._dev.get_hat(i)
            return (int(h[0]), int(h[1]))
        except Exception:  # noqa: BLE001
            return (0, 0)

    def close(self) -> None:
        self._alive = False
        try:
            self._dev.quit()
        except Exception:  # noqa: BLE001
            pass


def _import_pygame():
    _setup_sdl_env()
    import pygame  # noqa: PLC0415 - optional dependency

    return pygame


class PygameBackend:
    """Enumerates devices, prefers a DualSense by name, re-scans for hot-plug."""

    def __init__(self, prefer: tuple[str, ...] = PREFERRED_NAMES, use_gamecontroller: bool = True):
        self.prefer = tuple(prefer)
        self.use_gamecontroller = bool(use_gamecontroller)
        self.pg = _import_pygame()
        self._controller_mod = None
        self.ok = False
        try:
            if not self.pg.display.get_init():
                self.pg.display.init()
            if not self.pg.joystick.get_init():
                self.pg.joystick.init()
            if self.use_gamecontroller:
                try:
                    from pygame._sdl2 import controller as ctrl  # noqa: PLC0415

                    if not ctrl.get_init():
                        ctrl.init()
                    self._controller_mod = ctrl
                except Exception as e:  # noqa: BLE001 - old pygame without _sdl2.controller
                    log.info("pygame GameController API unavailable (%s); raw joystick only", e)
            self.ok = True
        except Exception as e:  # noqa: BLE001
            log.warning("pygame joystick init failed: %s", e)

    def pump(self) -> None:
        try:
            self.pg.event.pump()
        except Exception:  # noqa: BLE001
            pass

    def device_names(self) -> list[str]:
        if not self.ok:
            return []
        self.pump()
        names = []
        try:
            n = self.pg.joystick.get_count()
        except Exception:  # noqa: BLE001
            return []
        for i in range(n):
            try:
                names.append(str(self.pg.joystick.Joystick(i).get_name()))
            except Exception:  # noqa: BLE001
                names.append(f"joystick {i}")
        return names

    def _rank(self, name: str) -> int:
        low = name.lower()
        for k, pat in enumerate(self.prefer):
            if pat.lower() in low:
                return k
        return len(self.prefer)

    def open_best(self) -> PygameProvider | None:
        names = self.device_names()
        if not names:
            return None
        idx = min(range(len(names)), key=lambda i: (self._rank(names[i]), i))
        return self.open(idx, names[idx])

    def open(self, index: int, name: str | None = None) -> PygameProvider | None:
        ctrl = self._controller_mod
        if ctrl is not None:
            try:
                if ctrl.is_controller(index):
                    dev = ctrl.Controller(index)
                    nm = name or str(getattr(dev, "name", None) or ctrl.name_forindex(index) or f"controller {index}")
                    return PygameProvider(dev, gamecontroller=True, name=nm, instance_id=_instance_id(dev))
            except Exception as e:  # noqa: BLE001
                log.info("GameController open failed for %d (%s); using raw joystick", index, e)
        try:
            js = self.pg.joystick.Joystick(index)
            js.init()
            nm = name or str(js.get_name())
            return PygameProvider(js, gamecontroller=False, name=nm, instance_id=_instance_id(js))
        except Exception as e:  # noqa: BLE001
            log.warning("joystick %d open failed: %s", index, e)
            return None


def _instance_id(dev) -> int | None:
    for attr in ("get_instance_id", "id"):
        try:
            v = getattr(dev, attr)
            return int(v() if callable(v) else v)
        except Exception:  # noqa: BLE001
            continue
    return None


# =========================================================================== mapping (pure)
def expo_curve(x: float, expo: float) -> float:
    """``(1-e) x + e x^3`` (odd, monotone, keeps the end points)."""
    return (1.0 - expo) * x + expo * x * x * x


def apply_deadzone_expo(x: float, y: float, deadzone: float, expo: float) -> tuple[float, float]:
    """Radial deadzone (rescaled so the output reaches 1 at full deflection) + expo on the magnitude."""
    r = math.hypot(x, y)
    if r <= deadzone or r <= 0.0:
        return (0.0, 0.0)
    r = min(1.0, (r - deadzone) / (1.0 - deadzone)) if deadzone < 1.0 else 1.0
    r = expo_curve(r, expo)
    n = math.hypot(x, y)
    return (x / n * r, y / n * r)


def apply_deadzone_expo_1d(x: float, deadzone: float, expo: float) -> float:
    a = abs(x)
    if a <= deadzone:
        return 0.0
    a = min(1.0, (a - deadzone) / (1.0 - deadzone)) if deadzone < 1.0 else 1.0
    return math.copysign(expo_curve(a, expo), x)


def _trigger_unit(v: float, provider_gc: bool, trigger_range: str) -> float:
    """Trigger value -> [0, 1]."""
    rng = trigger_range
    if rng == "auto":
        rng = "unit" if provider_gc else "signed"
    if rng == "signed":
        v = (v + 1.0) / 2.0
    return max(0.0, min(1.0, v))


def read_state(provider: InputProvider, joy_map: JoyMap = DEFAULT_JOY_MAP, now: float | None = None) -> JoystickState:
    """Sample a provider into a normalised :class:`JoystickState` (pure, no edge detection)."""
    provider.pump()
    st = JoystickState(connected=provider.alive(), name=provider.name, t=time.monotonic() if now is None else now)
    if not st.connected:
        return st
    gc = bool(getattr(provider, "gamecontroller", False))
    n_axes = provider.num_axes()

    def ax(name: str) -> float:
        i = joy_map.axes.get(name, -1)
        if i < 0 or i >= n_axes:
            return 0.0
        v = provider.axis(i)
        return -v if joy_map.invert.get(name, False) else v

    st.lx, st.ly, st.rx, st.ry = ax("lx"), ax("ly"), ax("rx"), ax("ry")
    st.l2 = _trigger_unit(ax("l2"), gc, joy_map.trigger_range) if joy_map.axes.get("l2", -1) < n_axes else 0.0
    st.r2 = _trigger_unit(ax("r2"), gc, joy_map.trigger_range) if joy_map.axes.get("r2", -1) < n_axes else 0.0
    n_btn = provider.num_buttons()
    st.buttons = {name: (0 <= i < n_btn and provider.button(i)) for name, i in joy_map.buttons.items()}
    dx = int(st.buttons.get("dpad_right", False)) - int(st.buttons.get("dpad_left", False))
    dy = int(st.buttons.get("dpad_up", False)) - int(st.buttons.get("dpad_down", False))
    if dx == 0 and dy == 0 and joy_map.hat_dpad and provider.num_hats() > 0:
        dx, dy = provider.hat(0)
    st.dpad = (int(dx), int(dy))
    return st


@dataclass
class CmdLimits:
    """Subset of :class:`dtssl.sim.world.RobotSpec` used by the mapping."""

    v_max: float = 3.0
    w_max: float = 10.0
    kick_flat_max: float = 6.5
    kick_chip_max: float = 6.0
    chip_angle_deg: float = 45.0
    dribbler_rpm_max: float = 6000.0
    dribbler_rpm: float | None = None      # rpm used when the dribbler is on (default: 0.5 * max)

    @staticmethod
    def from_spec(spec) -> CmdLimits:
        kw = {k: float(getattr(spec, k)) for k in ("v_max", "w_max", "kick_flat_max", "kick_chip_max",
                                                    "chip_angle_deg", "dribbler_rpm_max") if hasattr(spec, k)}
        return CmdLimits(**kw)

    @property
    def dribbler_on_rpm(self) -> float:
        return float(self.dribbler_rpm if self.dribbler_rpm is not None else 0.5 * self.dribbler_rpm_max)


def _rising(name: str, st: JoystickState, prev: JoystickState | None) -> bool:
    return st.pressed(name) and not (prev is not None and prev.pressed(name))


def map_state(st: JoystickState, prev: JoystickState | None, limits: CmdLimits, joy_map: JoyMap,
              dribbler_on: bool) -> tuple[RobotCmd, list[str], bool]:
    """State (+ previous state for edges) -> ``(RobotCmd, events, dribbler_on)``. Pure."""
    events: list[str] = []
    if not st.connected:
        return RobotCmd(), events, dribbler_on
    lx, ly = apply_deadzone_expo(st.lx, st.ly, joy_map.deadzone, joy_map.expo)
    rx = apply_deadzone_expo_1d(st.rx, joy_map.deadzone, joy_map.expo)
    turbo = st.r2 > joy_map.turbo_threshold
    scale = joy_map.turbo_scale if turbo else joy_map.normal_scale
    cmd = RobotCmd(vx=-ly * limits.v_max * scale, vy=-lx * limits.v_max * scale, w=-rx * limits.w_max * scale)

    if _rising("r1", st, prev):
        dribbler_on = not dribbler_on
        events.append(EVENT_DRIBBLER_ON if dribbler_on else EVENT_DRIBBLER_OFF)
    if _rising("ps", st, prev):
        events.append(EVENT_STOP)
        dribbler_on = False
        cmd = RobotCmd()
    if _rising("options", st, prev):
        events.append(EVENT_TELEPORT_CENTER)
    pdx = prev.dpad[0] if prev is not None else 0
    if st.dpad[0] < 0 and pdx >= 0:
        events.append(EVENT_PREV_ROBOT)
    elif st.dpad[0] > 0 and pdx <= 0:
        events.append(EVENT_NEXT_ROBOT)

    # kicks are sent while the button is held (the world consumes one, then a 0.1 s cooldown applies)
    if st.pressed("cross"):
        cmd.kick_speed, cmd.kick_angle_deg = limits.kick_flat_max, 0.0
        if _rising("cross", st, prev):
            events.append(EVENT_KICK_FLAT)
    elif st.pressed("circle"):
        cmd.kick_speed, cmd.kick_angle_deg = limits.kick_chip_max, limits.chip_angle_deg
        if _rising("circle", st, prev):
            events.append(EVENT_KICK_CHIP)
    cmd.dribbler_rpm = limits.dribbler_on_rpm if dribbler_on else 0.0
    return cmd, events, dribbler_on


# =========================================================================== reader
class JoystickReader:
    """Polls a provider (pygame device, keyboard, fake) and maps it to :class:`RobotCmd` + events.

    ``provider`` fixes the input (tests / keyboard); otherwise pygame is probed and the best
    device opened, with hot-plug re-scans every ``rescan_s``. ``fallback`` (e.g. a
    :class:`~dtssl.gui.keyboard.KeyboardProvider`) is used whenever no pad is connected.
    """

    def __init__(self, limits: CmdLimits | Any = None, joy_map: JoyMap | None = None, *,
                 provider: InputProvider | None = None, fallback: InputProvider | None = None,
                 use_pygame: bool | None = None, rescan_s: float = 2.0, prefer: tuple[str, ...] = PREFERRED_NAMES):
        self.limits = limits if isinstance(limits, CmdLimits) else (
            CmdLimits.from_spec(limits) if limits is not None else CmdLimits())
        self.joy_map = joy_map or JoyMap.default()
        self.user_map = joy_map is not None
        self.rescan_s = float(rescan_s)
        self.prefer = prefer
        self.fallback = fallback
        self._fixed = provider
        self.provider: InputProvider | None = provider
        self.backend: PygameBackend | None = None
        self.dribbler_on = False
        self.turbo = False
        self.state = JoystickState()
        self._prev: JoystickState | None = None
        self._t_scan = -math.inf
        self.last_cmd = RobotCmd()
        self.last_events: list[str] = []
        if provider is None:
            if use_pygame is None:
                use_pygame = pygame_available()
            if use_pygame:
                try:
                    self.backend = PygameBackend(prefer=prefer)
                except Exception as e:  # noqa: BLE001
                    log.warning("pygame unavailable: %s", e)
                    self.backend = None
            self.rescan(force=True)

    # ------------------------------------------------------------------ devices
    @property
    def connected(self) -> bool:
        p = self.provider
        return p is not None and p is not self.fallback and p.alive()

    @property
    def name(self) -> str:
        if self.connected:
            return self.provider.name  # type: ignore[union-attr]
        return self.fallback.name if self.fallback is not None else "keyboard"

    def active_map(self) -> JoyMap:
        """The map in force for the current provider (GameController layout unless the user gave one)."""
        p = self.provider
        if p is None or p is self.fallback or self.user_map:
            return self.joy_map
        if getattr(p, "gamecontroller", True):
            return self.joy_map
        low = p.name.lower()
        if "dualsense" in low or "ps5" in low or "wireless controller" in low:
            return JoyMap.dualsense_raw_windows() if os.name == "nt" else JoyMap.dualsense_raw_linux()
        return self.joy_map

    def rescan(self, force: bool = False) -> list[str]:
        """Re-enumerate devices (hot-plug). Returns the events generated (connected/disconnected)."""
        events: list[str] = []
        if self._fixed is not None:
            return events
        now = time.monotonic()
        if not force and now - self._t_scan < self.rescan_s:
            return events
        self._t_scan = now
        if self.provider is not None and self.provider is not self.fallback:
            if self.provider.alive():
                return events
            events.append(EVENT_DISCONNECTED)
            log.info("joystick disconnected: %s", self.provider.name)
            self.provider = None
        if self.backend is not None:
            try:
                dev = self.backend.open_best()
            except Exception as e:  # noqa: BLE001
                log.warning("joystick scan failed: %s", e)
                dev = None
            if dev is not None:
                self.provider = dev
                self._prev = None
                events.append(f"{EVENT_CONNECTED}:{dev.name}")
                log.info("joystick connected: %s (%s)", dev.name,
                         "GameController" if dev.gamecontroller else "raw joystick")
                return events
        self.provider = self.fallback
        return events

    # ------------------------------------------------------------------ polling
    def poll(self) -> JoystickState:
        ev = self.rescan()
        self.last_events = list(ev)
        p = self.provider
        if p is None:
            self.state = JoystickState()
            return self.state
        self.state = read_state(p, self.active_map())
        if self.state.connected and p is self.fallback:
            self.state.name = p.name
        return self.state

    def read(self) -> tuple[RobotCmd, list[str]]:
        """Poll once and return ``(RobotCmd, events)``; call at ~120 Hz."""
        st = self.poll()
        events = list(self.last_events)
        cmd, ev, self.dribbler_on = map_state(st, self._prev, self.limits, self.active_map(), self.dribbler_on)
        self.turbo = st.connected and st.r2 > self.active_map().turbo_threshold
        events.extend(ev)
        self._prev = st
        self.last_cmd = cmd
        return cmd, events

    def close(self) -> None:
        p = self.provider
        if p is not None and hasattr(p, "close") and p is not self.fallback:
            p.close()  # type: ignore[union-attr]
        self.provider = None


__all__ = [
    "JoyMap", "JoystickState", "JoystickReader", "CmdLimits", "InputProvider", "FakeProvider",
    "PygameProvider", "PygameBackend", "read_state", "map_state", "apply_deadzone_expo",
    "apply_deadzone_expo_1d", "expo_curve", "pygame_available", "DEFAULT_JOY_MAP", "DEFAULT_AXES",
    "DEFAULT_BUTTONS", "PREFERRED_NAMES",
    "EVENT_KICK_FLAT", "EVENT_KICK_CHIP", "EVENT_DRIBBLER_ON", "EVENT_DRIBBLER_OFF", "EVENT_PREV_ROBOT",
    "EVENT_NEXT_ROBOT", "EVENT_TELEPORT_CENTER", "EVENT_STOP", "EVENT_CONNECTED", "EVENT_DISCONNECTED",
]
