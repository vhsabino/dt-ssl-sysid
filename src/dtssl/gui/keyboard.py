"""Keyboard fallback for the Debug mode: a virtual gamepad with the SDL GameController layout.

Qt-free so it can be unit-tested; the window feeds key names through :meth:`press` /
:meth:`release` (``"w"``, ``"space"``, ``"shift"`` ...). Bindings (see :data:`KEY_BINDINGS`)::

    W / S        forward / backward   (LY)      Q / E     rotate CCW / CW     (RX)
    A / D        left / right         (LX)      Shift     turbo               (R2)
    Space        flat kick (cross)              C         chip kick (circle)
    R            dribbler toggle (R1)           , / .  or  [ / ]   previous / next robot (D-pad)
    Home / T     teleport to the centre (Options)         Esc / X   stop (PS)

Stick values ramp linearly over ``ramp_s`` (default 0.25 s) instead of jumping to ±1, so the
plant sees a smooth command; releasing the key ramps back to zero.
"""
from __future__ import annotations

import time

from dtssl.gui.joystick import DEFAULT_AXES, DEFAULT_BUTTONS

#: key name -> ("axis", axis_name, target) | ("button", button_name)
KEY_BINDINGS: dict[str, tuple] = {
    "w": ("axis", "ly", -1.0), "s": ("axis", "ly", +1.0),
    "a": ("axis", "lx", -1.0), "d": ("axis", "lx", +1.0),
    "q": ("axis", "rx", -1.0), "e": ("axis", "rx", +1.0),
    "up": ("axis", "ly", -1.0), "down": ("axis", "ly", +1.0),
    "left": ("axis", "lx", -1.0), "right": ("axis", "lx", +1.0),
    "shift": ("axis", "r2", 1.0),
    "space": ("button", "cross"), "c": ("button", "circle"),
    "r": ("button", "r1"),
    ",": ("button", "dpad_left"), ".": ("button", "dpad_right"),
    "[": ("button", "dpad_left"), "]": ("button", "dpad_right"),
    "home": ("button", "options"), "t": ("button", "options"),
    "escape": ("button", "ps"), "x": ("button", "ps"),
}


class KeyboardProvider:
    """Virtual GameController driven by key names; implements :class:`dtssl.gui.joystick.InputProvider`."""

    gamecontroller = True

    def __init__(self, ramp_s: float = 0.25, name: str = "keyboard", clock=time.monotonic):
        self.name = name
        self.ramp_s = float(ramp_s)
        self._clock = clock
        self._keys: set[str] = set()
        self._axes = [0.0] * 6
        self._t_last = self._clock()

    # ------------------------------------------------------------------ key input
    @staticmethod
    def normalize(key: str) -> str:
        return key.strip().lower()

    def press(self, key: str) -> bool:
        k = self.normalize(key)
        if k not in KEY_BINDINGS:
            return False
        self._keys.add(k)
        return True

    def release(self, key: str) -> bool:
        k = self.normalize(key)
        self._keys.discard(k)
        return k in KEY_BINDINGS

    def release_all(self) -> None:
        self._keys.clear()

    @property
    def keys_down(self) -> frozenset[str]:
        return frozenset(self._keys)

    # ------------------------------------------------------------------ provider API
    def pump(self) -> None:
        now = self._clock()
        dt = max(0.0, now - self._t_last)
        self._t_last = now
        targets = [0.0] * 6
        for k in self._keys:
            b = KEY_BINDINGS[k]
            if b[0] == "axis":
                targets[DEFAULT_AXES[b[1]]] += b[2]        # opposite keys cancel out
        targets = [max(-1.0, min(1.0, t)) for t in targets]
        step = dt / self.ramp_s if self.ramp_s > 0.0 else 1.0
        for i in range(6):
            if i in (DEFAULT_AXES["l2"], DEFAULT_AXES["r2"]):
                self._axes[i] = targets[i]          # triggers switch instantly
                continue
            cur, tgt = self._axes[i], targets[i]
            if step >= 1.0 or abs(tgt - cur) <= step:
                self._axes[i] = tgt
            else:
                self._axes[i] = cur + step * (1.0 if tgt > cur else -1.0)

    def alive(self) -> bool:
        return True

    def num_axes(self) -> int:
        return 6

    def num_buttons(self) -> int:
        return 15

    def num_hats(self) -> int:
        return 0

    def axis(self, i: int) -> float:
        return self._axes[i] if 0 <= i < 6 else 0.0

    def button(self, i: int) -> bool:
        for k in self._keys:
            b = KEY_BINDINGS[k]
            if b[0] == "button" and DEFAULT_BUTTONS.get(b[1], -1) == i:
                return True
        return False

    def hat(self, i: int) -> tuple[int, int]:
        return (0, 0)


__all__ = ["KeyboardProvider", "KEY_BINDINGS"]
