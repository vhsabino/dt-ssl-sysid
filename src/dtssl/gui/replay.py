"""Replay mode data model (Qt-free): dataset browsing + whole-event free-run vs truth.

    ds = list_datasets(); labels = list_labels(ds[0]); events = list_events(ds[0], labels[0])
    sess = ReplaySession.load(label, event, dataset=ds[0], params=theta)   # AnalyticFOPDTPlant
    sess.pose_sim, sess.epos, sess.epos_at_horizons()                        # e_pos per horizon

The free-run follows ``dtssl.cli.cmd_replay``: the plant starts from the event's first pose
and body velocity (``seg.pose0`` / ``seg.velb0``), no commands before t0, and is driven by
the logged commands (``dtssl.sim.rollout.free_run``). ``e_pos(t)`` / ``e_ang(t)`` come from
``dtssl.eval.metrics.pose_errors``; the horizons (samples) from ``config/metrics.json``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from dtssl.data.loader import DATASET_DEFAULT, body_velocity_series, load_segment
from dtssl.data.schema import Segment
from dtssl.eval.metrics import pose_errors
from dtssl.models import AnalyticFOPDTPlant, DofParam, IdealKinematicPlant, Plant
from dtssl.paths import data_root
from dtssl.sim.rollout import DEFAULT_HORIZONS, free_run

SPEEDS: tuple[float, ...] = (0.5, 1.0, 2.0)


# --------------------------------------------------------------------------- browsing
def list_datasets(root: Path | None = None) -> list[str]:
    """Dataset ids under ``data/extracted`` that have a ``splits`` directory (canonical first)."""
    r = Path(root) if root is not None else data_root()
    if not r.is_dir():
        return []
    out = sorted(p.name for p in r.iterdir() if (p / "splits").is_dir())
    if DATASET_DEFAULT in out:
        out.remove(DATASET_DEFAULT)
        out.insert(0, DATASET_DEFAULT)
    return out


def list_labels(dataset: str, root: Path | None = None) -> list[str]:
    r = (Path(root) if root is not None else data_root()) / dataset / "splits"
    if not r.is_dir():
        return []
    return sorted(p.name for p in r.iterdir() if p.is_dir() and not p.name.startswith("."))


def list_events(dataset: str, label: str, root: Path | None = None) -> list[str]:
    r = (Path(root) if root is not None else data_root()) / dataset / "splits" / label
    if not r.is_dir():
        return []
    return sorted(p.name for p in r.iterdir() if (p / "commands.parquet").is_file())


def horizons_from_config(mcfg: dict | None = None) -> tuple[int, ...]:
    if mcfg is None:
        try:
            from dtssl.config import load_metrics_config

            mcfg = load_metrics_config()
        except Exception:  # noqa: BLE001 - config absent
            return tuple(DEFAULT_HORIZONS)
    return tuple(int(h) for h in mcfg.get("horizons", DEFAULT_HORIZONS))


def make_plant(params: dict[str, DofParam] | None, kind: str = "fopdt") -> Plant:
    """``"ideal"`` -> IdealKinematicPlant; anything else -> AnalyticFOPDTPlant(params or config theta)."""
    if kind == "ideal":
        return IdealKinematicPlant()
    if params is None:
        from dtssl.models import load_twin_params

        params = load_twin_params()
    return AnalyticFOPDTPlant(params)


# --------------------------------------------------------------------------- session
@dataclass
class ReplaySession:
    """One event: truth arrays, commands, and the free-run of the current plant (recomputable)."""

    seg: Segment
    plant_kind: str = "fopdt"
    horizons: tuple[int, ...] = tuple(DEFAULT_HORIZONS)
    pose_sim: np.ndarray = field(default_factory=lambda: np.zeros((0, 3)))
    velb_sim: np.ndarray = field(default_factory=lambda: np.zeros((0, 3)))
    epos: np.ndarray = field(default_factory=lambda: np.zeros(0))
    eang: np.ndarray = field(default_factory=lambda: np.zeros(0))
    index: int = 0
    speed: float = 1.0
    playing: bool = False
    _acc: float = 0.0

    # ------------------------------------------------------------------ construction
    @staticmethod
    def load(label: str, event: str, *, dataset: str = DATASET_DEFAULT, params: dict[str, DofParam] | None = None,
             plant_kind: str = "fopdt", horizons: tuple[int, ...] | None = None, team: str = "allies",
             data_root: Path | None = None) -> ReplaySession:
        seg = load_segment(label, event, dataset=dataset, team=team, data_root=data_root)
        s = ReplaySession(seg=seg, plant_kind=plant_kind, horizons=tuple(horizons or horizons_from_config()))
        s.recompute(params)
        return s

    @staticmethod
    def from_segment(seg: Segment, params: dict[str, DofParam] | None = None, plant_kind: str = "fopdt",
                     horizons: tuple[int, ...] | None = None) -> ReplaySession:
        s = ReplaySession(seg=seg, plant_kind=plant_kind, horizons=tuple(horizons or DEFAULT_HORIZONS))
        s.recompute(params)
        return s

    def recompute(self, params: dict[str, DofParam] | None = None, plant: Plant | None = None) -> None:
        """Re-run the free-run with new parameters (``ParamsPanel`` Apply) keeping the playhead."""
        seg = self.seg
        plant = plant or make_plant(params, self.plant_kind)
        cmd = self.cmd
        if seg.n >= 2:
            self.pose_sim = free_run(plant, cmd[:-1], pose0=seg.pose0, velb0=seg.velb0, dt=seg.ts, prev_cmds=None)
        else:
            self.pose_sim = np.asarray([seg.pose0], dtype=float).reshape(-1, 3)
        vx, vy, w = body_velocity_series(seg.t, self.pose_sim[:, 0], self.pose_sim[:, 1], self.pose_sim[:, 2])
        self.velb_sim = np.column_stack([vx, vy, w])
        self.epos, self.eang = pose_errors(self.pose_sim, self.truth)
        self.index = min(self.index, self.n - 1)

    # ------------------------------------------------------------------ arrays
    @property
    def n(self) -> int:
        return int(self.seg.n)

    @property
    def ts(self) -> float:
        return float(self.seg.ts)

    @property
    def t(self) -> np.ndarray:
        return self.seg.t - self.seg.t[0]

    @property
    def duration_s(self) -> float:
        return float(self.seg.duration_s)

    @property
    def cmd(self) -> np.ndarray:
        s = self.seg
        return np.column_stack([s.cmd_vx, s.cmd_vy, s.cmd_w])

    @property
    def truth(self) -> np.ndarray:
        s = self.seg
        return np.column_stack([s.pos_x, s.pos_y, s.theta])

    @property
    def velb_truth(self) -> np.ndarray:
        s = self.seg
        return np.column_stack([s.velb_x, s.velb_y, s.velb_w])

    @property
    def label(self) -> str:
        return str(self.seg.meta.get("label", "?"))

    @property
    def event(self) -> str:
        return str(self.seg.meta.get("event", "?"))

    @property
    def dataset(self) -> str:
        return str(self.seg.meta.get("dataset", "?"))

    def horizon_times(self) -> list[float]:
        return [h * self.ts for h in self.horizons]

    def epos_at_horizons(self) -> dict[int, float]:
        """``e_pos`` of the whole-event free-run at each horizon (samples after the first pose)."""
        return {h: (float(self.epos[h]) if h < self.epos.size else float("nan")) for h in self.horizons}

    # ------------------------------------------------------------------ playhead
    def sample(self, i: int | None = None) -> dict:
        """Everything the views need at index ``i`` (default: playhead)."""
        i = self.index if i is None else max(0, min(self.n - 1, int(i)))
        return {"i": i, "t": float(self.t[i]), "cmd": tuple(float(v) for v in self.cmd[i]),
                "pose_sim": tuple(float(v) for v in self.pose_sim[i]),
                "pose_truth": tuple(float(v) for v in self.truth[i]),
                "velb_sim": tuple(float(v) for v in self.velb_sim[i]),
                "velb_truth": tuple(float(v) for v in self.velb_truth[i]),
                "epos": float(self.epos[i]), "eang": float(self.eang[i])}

    def seek(self, i: int) -> int:
        self.index = max(0, min(self.n - 1, int(i)))
        self._acc = 0.0
        return self.index

    def seek_time(self, t: float) -> int:
        return self.seek(int(round(t / self.ts)))

    def set_speed(self, speed: float) -> None:
        self.speed = float(speed)

    def advance(self, dt_wall: float) -> int:
        """Advance the playhead by ``dt_wall * speed`` seconds (returns the number of samples moved)."""
        if not self.playing or self.n < 2:
            return 0
        self._acc += float(dt_wall) * self.speed
        k = int(self._acc / self.ts)
        if k <= 0:
            return 0
        self._acc -= k * self.ts
        new = self.index + k
        if new >= self.n - 1:
            new = self.n - 1
            self.playing = False
        moved = new - self.index
        self.index = new
        return moved

    def play(self) -> None:
        if self.index >= self.n - 1:
            self.index = 0
        self.playing = True
        self._acc = 0.0

    def pause(self) -> None:
        self.playing = False

    def toggle(self) -> bool:
        if self.playing:
            self.pause()
        else:
            self.play()
        return self.playing


__all__ = ["ReplaySession", "list_datasets", "list_labels", "list_events", "horizons_from_config",
           "make_plant", "SPEEDS"]
