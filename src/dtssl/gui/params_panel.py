"""Parameter panel: ``K``, ``tau``, ``Td`` per DOF with the SLDD bounds, presets, JSON load/save.

Bounds (``config/ssl_robot.sldd`` identification ranges): ``K in [0.5, 2.0]``,
``tau in [0.01, 0.5]`` s, ``Td in [0, 0.2]`` s. Presets: **oficial** (``config/twin_params.json``),
**ω placeholder** (vx/vy official, ``w = {K: 1, tau: 0.1, Td: 0, placeholder: true}`` — the
pre-2026-07-24 value) and **ideal** (``K = 1, tau = 0.01, Td = 0`` for every DOF).

``Apply`` emits :attr:`ParamsPanel.apply_requested` with ``dict[str, DofParam]``; the controller
hot-swaps it into the world (``world.set_plant_params``) without resetting poses. Load/Save use
the ``twin_params.json`` schema (``dof`` + ``order`` + ``ts``/``robot_radius``/``wheel_radius``).
"""
from __future__ import annotations

import json
from pathlib import Path

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Signal

from dtssl.models.params import DOFS, DofParam, load_twin_params

BOUNDS: dict[str, tuple[float, float]] = {"K": (0.5, 2.0), "tau": (0.01, 0.5), "Td": (0.0, 0.2)}
STEPS: dict[str, float] = {"K": 0.01, "tau": 0.005, "Td": 0.005}
ORDER: tuple[str, ...] = ("K_vx", "tau_vx", "Td_vx", "K_vy", "tau_vy", "Td_vy", "K_w", "tau_w", "Td_w")
PLACEHOLDER_W = DofParam(K=1.0, tau=0.1, Td=0.0, placeholder=True)
IDEAL = DofParam(K=1.0, tau=0.01, Td=0.0, placeholder=False)
PRESETS = ("oficial", "ω placeholder", "ideal")


def params_to_dict(params: dict[str, DofParam], *, source: str = "dtssl gui", note: str = "",
                   ts: float = 1.0 / 60.0, robot_radius: float = 0.079601, wheel_radius: float = 0.029492) -> dict:
    """``twin_params.json`` schema (same keys and the fixed ``order``)."""
    return {
        "source": source,
        "note": note,
        "ts": ts,
        "robot_radius": robot_radius,
        "wheel_radius": wheel_radius,
        "dof": {d: {"K": float(params[d].K), "tau": float(params[d].tau), "Td": float(params[d].Td),
                    "placeholder": bool(params[d].placeholder)} for d in DOFS},
        "order": list(ORDER),
    }


def params_from_dict(d: dict) -> dict[str, DofParam]:
    dof = d["dof"]
    return {k: DofParam(K=float(dof[k]["K"]), tau=float(dof[k]["tau"]), Td=float(dof[k]["Td"]),
                        placeholder=bool(dof[k].get("placeholder", False))) for k in DOFS}


def clamp(name: str, value: float) -> float:
    lo, hi = BOUNDS[name]
    return min(hi, max(lo, float(value)))


class ParamsPanel(QtWidgets.QWidget):
    apply_requested = Signal(object)     # dict[str, DofParam]
    params_changed = Signal(object)      # dict[str, DofParam] (any edit)

    def __init__(self, params: dict[str, DofParam] | None = None, parent=None):
        super().__init__(parent)
        self._official: dict[str, DofParam] | None = None
        self.spins: dict[tuple[str, str], QtWidgets.QDoubleSpinBox] = {}
        self.placeholders: dict[str, QtWidgets.QCheckBox] = {}
        self._building = True
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)

        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(6)
        for j, name in enumerate(("K", "tau [s]", "Td [s]", "placeholder")):
            lab = QtWidgets.QLabel(f"<b>{name}</b>")
            lab.setAlignment(QtCore.Qt.AlignCenter)
            grid.addWidget(lab, 0, j + 1)
        for i, dof in enumerate(DOFS):
            grid.addWidget(QtWidgets.QLabel(f"<b>{dof}</b>"), i + 1, 0)
            for j, name in enumerate(("K", "tau", "Td")):
                sb = QtWidgets.QDoubleSpinBox()
                sb.setDecimals(4)
                lo, hi = BOUNDS[name]
                sb.setRange(lo, hi)
                sb.setSingleStep(STEPS[name])
                sb.setKeyboardTracking(False)
                sb.setToolTip(f"{name}_{dof} in [{lo}, {hi}]")
                sb.valueChanged.connect(self._on_edit)
                grid.addWidget(sb, i + 1, j + 1)
                self.spins[(dof, name)] = sb
            cb = QtWidgets.QCheckBox()
            cb.setToolTip(f"{dof}: parameters NOT identified (placeholder)")
            cb.toggled.connect(self._on_edit)
            grid.addWidget(cb, i + 1, 4, alignment=QtCore.Qt.AlignCenter)
            self.placeholders[dof] = cb
        lay.addLayout(grid)

        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("Preset:"))
        self.preset_box = QtWidgets.QComboBox()
        self.preset_box.addItems(list(PRESETS))
        row.addWidget(self.preset_box, 1)
        self.btn_preset = QtWidgets.QPushButton("Set")
        self.btn_preset.clicked.connect(lambda: self.apply_preset(self.preset_box.currentText()))
        row.addWidget(self.btn_preset)
        lay.addLayout(row)

        row2 = QtWidgets.QHBoxLayout()
        self.btn_load = QtWidgets.QPushButton("Load JSON…")
        self.btn_save = QtWidgets.QPushButton("Save JSON…")
        self.btn_apply = QtWidgets.QPushButton("Apply")
        self.btn_apply.setDefault(True)
        self.btn_load.clicked.connect(self._load_dialog)
        self.btn_save.clicked.connect(self._save_dialog)
        self.btn_apply.clicked.connect(self.apply)
        row2.addWidget(self.btn_load)
        row2.addWidget(self.btn_save)
        row2.addStretch(1)
        row2.addWidget(self.btn_apply)
        lay.addLayout(row2)

        self.status = QtWidgets.QLabel("")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        lay.addStretch(1)
        self._building = False
        self.set_params(params or self.official())

    # ------------------------------------------------------------------ values
    def official(self) -> dict[str, DofParam]:
        if self._official is None:
            self._official = load_twin_params()
        return dict(self._official)

    def params(self) -> dict[str, DofParam]:
        return {d: DofParam(K=self.spins[(d, "K")].value(), tau=self.spins[(d, "tau")].value(),
                            Td=self.spins[(d, "Td")].value(), placeholder=self.placeholders[d].isChecked())
                for d in DOFS}

    def set_params(self, params: dict[str, DofParam], note: str | None = None) -> None:
        self._building = True
        clipped = []
        try:
            for d in DOFS:
                p = params[d]
                for name in ("K", "tau", "Td"):
                    v = float(getattr(p, name))
                    c = clamp(name, v)
                    if abs(c - v) > 1e-12:
                        clipped.append(f"{name}_{d}={v:.4g}->{c:.4g}")
                    self.spins[(d, name)].setValue(c)
                self.placeholders[d].setChecked(bool(p.placeholder))
        finally:
            self._building = False
        msg = note or ""
        if clipped:
            msg = (msg + " " if msg else "") + "clipped to bounds: " + ", ".join(clipped)
        self.status.setText(msg)
        self.params_changed.emit(self.params())

    def _on_edit(self, *_):
        if not self._building:
            self.params_changed.emit(self.params())

    # ------------------------------------------------------------------ presets / JSON
    def apply_preset(self, name: str) -> dict[str, DofParam]:
        if name == "oficial":
            p = self.official()
        elif name in ("ω placeholder", "w placeholder", "placeholder"):
            p = self.official()
            p["w"] = PLACEHOLDER_W
        elif name == "ideal":
            p = {d: IDEAL for d in DOFS}
        else:
            raise KeyError(f"unknown preset {name!r}; presets: {PRESETS}")
        self.set_params(p, note=f"preset: {name}")
        return p

    def to_dict(self, note: str = "") -> dict:
        return params_to_dict(self.params(), note=note)

    def load_json(self, path: str | Path) -> dict[str, DofParam]:
        with open(Path(path).expanduser(), encoding="utf-8") as f:
            d = json.load(f)
        p = params_from_dict(d)
        self.set_params(p, note=f"loaded {Path(path).name}")
        return p

    def save_json(self, path: str | Path, note: str = "") -> Path:
        p = Path(path).expanduser()
        p.write_text(json.dumps(self.to_dict(note=note), indent=2) + "\n", encoding="utf-8")
        self.status.setText(f"saved {p.name}")
        return p

    def _load_dialog(self) -> None:
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load twin parameters", "", "JSON (*.json)")
        if fn:
            try:
                self.load_json(fn)
            except Exception as e:  # noqa: BLE001 - shown to the user
                self.status.setText(f"load failed: {e}")

    def _save_dialog(self) -> None:
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save twin parameters", "twin_params_gui.json",
                                                      "JSON (*.json)")
        if fn:
            try:
                self.save_json(fn, note="saved from dtssl gui")
            except Exception as e:  # noqa: BLE001
                self.status.setText(f"save failed: {e}")

    def apply(self) -> dict[str, DofParam]:
        p = self.params()
        self.apply_requested.emit(p)
        self.status.setText("applied " + "  ".join(
            f"{d}: K={p[d].K:.3f} τ={p[d].tau:.3f} Td={p[d].Td:.3f}" for d in DOFS))
        return p


__all__ = ["ParamsPanel", "params_to_dict", "params_from_dict", "BOUNDS", "PRESETS", "ORDER",
           "PLACEHOLDER_W", "IDEAL", "clamp"]
