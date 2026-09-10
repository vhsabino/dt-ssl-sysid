"""Motor de rollout multi-horizonte em FREE-RUN.

DRIVER FINO: NAO implementa integracao, discretizacao nem dinamica. So janelamento,
condicao inicial via API da Plant, free-run e coleta. Toda a dinamica vem de
Plant.reset / Plant.prime_delay / Plant.step. NAO computa metrica.

Por janela (a cada stride):
  reset(pose0 = pose real em t0, velb0 = serie vel-de-corpo em t0)   [serie do loader]
  prime_delay(comandos imediatamente anteriores a t0; lookback generoso)
  free-run de H_max passos: pose_sim[0]=pose0; pose_sim[h]=step(cmd[t0+h-1], dt)
INVARIANTE: dentro da janela so se roda na propria predicao. Reinicializar por
janela e permitido; reancorar a cada passo (teacher forcing) e PROIBIDO — nenhum
indice de pose real > t0 e lido para conduzir a simulacao.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from dtssl.data.schema import Segment
from dtssl.models import Plant
from dtssl.models.params import load_twin_params

__all__ = [
    "DEFAULT_HMAX", "DEFAULT_HORIZONS", "DEFAULT_STRIDE", "DEFAULT_LOOKBACK",
    "DEFAULT_TRANS_FLOOR", "DEFAULT_ROT_FLOOR", "Window", "WindowRollout",
    "max_command_delay", "free_run", "rollout_segment", "plant_params",
    "save_rollouts", "load_rollouts", "convert_pickle_cache", "ROLLOUT_NPZ_FORMAT",
]

DEFAULT_HMAX = 90
DEFAULT_HORIZONS = (6, 12, 24, 42, 60, 90)
DEFAULT_STRIDE = 15
DEFAULT_LOOKBACK = 16
DEFAULT_TRANS_FLOOR = 0.05   # m/s
DEFAULT_ROT_FLOOR = 0.10     # rad/s


def max_command_delay(dt: float, params=None) -> int:
    """max sobre DOF de ceil(Td_dof/dt); ``params`` default = config/twin_params.json.
    Recalcula sozinho quando os params (ex.: de w) mudam. Casa com o tap do plant
    (floor(j - Td/dt) => ceil(Td/dt) amostras)."""
    p = params or load_twin_params()
    def m(dof: str) -> int:
        Td = p[dof].Td
        return 0 if Td <= 0.0 else int(math.ceil(Td / dt - 1e-9))
    return max(m("vx"), m("vy"), m("w"))


def plant_params(plant: Plant):
    """theta (dict[str, DofParam]) carried by ``plant``, or None (ideal/rSim plants)."""
    p = getattr(plant, "params", None)
    if p is None:
        return None
    try:
        for dof in ("vx", "vy", "w"):
            float(p[dof].Td)
    except (KeyError, TypeError, AttributeError):
        return None
    return p


@dataclass
class Window:
    t0: int                    # indice da CI no segmento
    t0_time: float             # seg.t[t0] (s)
    pose_sim: np.ndarray       # (H_max+1, 3) free-run; linha h alinha com pose_real[h]
    pose_real: np.ndarray      # (H_max+1, 3) pose real em t0..t0+H_max
    cmd: np.ndarray            # (H_max, 3) comandos usados (t0..t0+H_max-1) — p/ estratificacao
    velb: np.ndarray           # (H_max+1, 3) serie vel-de-corpo na janela — p/ estratificacao
    velb0: tuple               # CI de velocidade de corpo (= serie em t0)
    trans_peak: float          # m/s   (conteudo de comando da janela)
    trans_mean: float          # m/s
    rot_peak: float            # rad/s
    rot_mean: float            # rad/s
    idle: bool                 # quase-parada (sinalizada, NAO apagada)


@dataclass
class WindowRollout:
    meta: dict
    windows: list

    @property
    def n_total(self) -> int:
        return len(self.windows)

    @property
    def n_idle(self) -> int:
        return sum(1 for w in self.windows if w.idle)


# =========================================================================
def free_run(plant: Plant, win_cmds: np.ndarray, pose0, velb0, dt: float,
             prev_cmds=None) -> np.ndarray:
    """Conduz a planta em free-run por len(win_cmds) passos e devolve pose_sim
    (H+1, 3) com pose_sim[0]=pose0. Driver FINO: reset -> (prime) -> step loop.
    Nenhuma dinamica/integracao aqui — tudo vem da Plant.

    Plantas que expõem ``free_run_window(win_cmds, pose0, velb0, dt, prev_cmds)`` (ex.:
    ``ProtocolPlant``, que precisa transmitir a janela inteira em tempo real) recebem a
    janela de uma vez; o contrato de saída é o mesmo."""
    batch = getattr(plant, "free_run_window", None)
    if batch is not None:
        pose_sim = np.asarray(batch(np.asarray(win_cmds, dtype=float), pose0, velb0, dt, prev_cmds), dtype=float)
        pose_sim[0] = pose0
        return pose_sim
    plant.reset(pose0=pose0, velb0=velb0)
    if prev_cmds is not None and len(prev_cmds) > 0:
        plant.prime_delay(prev_cmds)
    h_max = len(win_cmds)
    pose_sim = np.empty((h_max + 1, 3), dtype=float)
    pose_sim[0] = pose0
    for h in range(1, h_max + 1):
        pose_sim[h] = plant.step(win_cmds[h - 1], dt)
    return pose_sim


def rollout_segment(seg: Segment, plant: Plant, *, h_max: int = DEFAULT_HMAX,
                    horizons=DEFAULT_HORIZONS, stride: int = DEFAULT_STRIDE,
                    lookback: int = DEFAULT_LOOKBACK,
                    trans_floor: float = DEFAULT_TRANS_FLOOR,
                    rot_floor: float = DEFAULT_ROT_FLOOR, params=None,
                    t0_anchor: int | None = None) -> WindowRollout:
    """Janela o segmento e roda free-run por janela. Veja o invariante no topo.

    Janelas: ``t0 = t0_anchor + k*stride`` (k >= 0), so as que satisfazem ``t0 >= idx_min``.

    * ``idx_min = max_command_delay(params) + 1`` e a primeira CI ADMISSIVEL (precisa de
      ``ceil(Td/dt)`` comandos anteriores para primar o atraso). ``params`` default = theta
      DA PROPRIA PLANTA (``plant.params``, AnalyticFOPDTPlant); so na falta dele
      (IdealKinematicPlant, RSimReplay) usa-se config/twin_params.json.
    * ``t0_anchor`` (grade das janelas) default = ``max_command_delay(theta oficial) + 1``, i.e.
      a grade do config/twin_params.json. A grade e FIXA por design: qualquer theta candidato
      (e qualquer baseline) e avaliado nas MESMAS janelas — um theta com atraso maior que o
      oficial apenas perde a(s) primeira(s) janela(s) inadmissiveis. Para theta == oficial a
      grade coincide com a do harness de 2026-08 (bit-a-bit).
    """
    if max(horizons) > h_max:
        raise ValueError(f"horizontes {horizons} excedem H_max={h_max}")
    dt = seg.ts
    N = seg.n
    if params is None:
        params = plant_params(plant)       # None -> max_command_delay le o config
    md = max_command_delay(dt, params)
    idx_min = md + 1                       # precisa de comandos anteriores p/ primar
    if t0_anchor is None:
        t0_anchor = max_command_delay(dt, None) + 1     # grade oficial (theta do config)
    t0_anchor = int(t0_anchor)
    if t0_anchor < 1:
        raise ValueError(f"t0_anchor={t0_anchor} deve ser >= 1")
    t0_start = t0_anchor + stride * max(0, math.ceil((idx_min - t0_anchor) / stride))

    cmd = np.column_stack([seg.cmd_vx, seg.cmd_vy, seg.cmd_w])
    velb = np.column_stack([seg.velb_x, seg.velb_y, seg.velb_w])   # serie do loader
    pos = np.column_stack([seg.pos_x, seg.pos_y, seg.theta])

    windows: list[Window] = []
    for t0 in range(t0_start, N - h_max, stride):
        pose0 = (float(pos[t0, 0]), float(pos[t0, 1]), float(pos[t0, 2]))   # pose real em t0
        velb0 = (float(velb[t0, 0]), float(velb[t0, 1]), float(velb[t0, 2]))  # serie em t0
        P = min(t0, lookback)
        prev = cmd[t0 - P:t0]              # comandos antes de t0 (antigo->recente)
        win_cmds = cmd[t0:t0 + h_max]      # cmd[t0 .. t0+H_max-1]

        pose_sim = free_run(plant, win_cmds, pose0, velb0, dt, prev_cmds=prev)
        pose_real = pos[t0:t0 + h_max + 1].copy()   # coleta (NAO usada p/ conduzir)
        velb_win = velb[t0:t0 + h_max + 1].copy()

        tr = np.hypot(win_cmds[:, 0], win_cmds[:, 1])
        rot = np.abs(win_cmds[:, 2])
        tp, tm = float(tr.max()), float(tr.mean())
        rp, rm = float(rot.max()), float(rot.mean())
        idle = (tp < trans_floor) and (rp < rot_floor)

        windows.append(Window(t0=t0, t0_time=float(seg.t[t0]), pose_sim=pose_sim,
                              pose_real=pose_real, cmd=win_cmds.copy(), velb=velb_win,
                              velb0=velb0, trans_peak=tp, trans_mean=tm,
                              rot_peak=rp, rot_mean=rm, idle=idle))

    meta = dict(event=seg.meta.get("event"), label=seg.meta.get("label"),
                dataset=seg.meta.get("dataset"), ts=dt, n_samples=N, h_max=h_max,
                horizons=tuple(horizons), stride=stride, lookback=lookback,
                max_delay=md, idx_min=idx_min, t0_anchor=t0_anchor,
                plant=type(plant).__name__, trans_floor=trans_floor, rot_floor=rot_floor)
    return WindowRollout(meta=meta, windows=windows)


# =========================================================================
# Serialisation of rollouts: .npz (+ JSON meta sidecar) instead of pickle
ROLLOUT_NPZ_FORMAT = "dtssl.rollouts/1"
_WIN_ARRAYS = ("pose_sim", "pose_real", "cmd", "velb")                       # (nw, H+1|H, 3)
_WIN_SCALARS = ("t0", "t0_time", "trans_peak", "trans_mean", "rot_peak", "rot_mean", "idle")


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (set, tuple)):
        return list(o)
    if isinstance(o, Path):
        return str(o)
    return str(o)


def _meta_from_json(meta: dict) -> dict:
    meta = dict(meta)
    if isinstance(meta.get("horizons"), list):
        meta["horizons"] = tuple(meta["horizons"])
    return meta


def save_rollouts(path, rollouts) -> Path:
    """Write ``rollouts`` (list/tuple of ``WindowRollout``, or a dict of them) to ``<path>.npz``
    plus a human-readable ``<path>.json`` sidecar with the per-rollout ``meta``.

    npz layout (self-contained; also readable by ``dtssl.analysis.common.load_rsim_cache_npz``):
    ``__meta__`` (JSON header: format, n_rollouts, keys, rollouts=[meta...]), ``meta_json``
    (JSON list of metas), ``n_segments`` and, per rollout ``i``: ``pose_sim_i``/``pose_real_i``/
    ``velb_i`` (nw, H+1, 3), ``cmd_i`` (nw, H, 3), ``t0_i`` (int), ``t0_time_i``,
    ``trans_peak_i``, ``trans_mean_i``, ``rot_peak_i``, ``rot_mean_i`` (float), ``idle_i``
    (bool) — all (nw,) — and ``velb0_i`` (nw, 3). Returns the npz path.
    """
    keys = None
    if isinstance(rollouts, dict):
        keys = [str(k) for k in rollouts.keys()]
        items = list(rollouts.values())
    else:
        items = list(rollouts)
    path = Path(path)
    if path.suffix != ".npz":
        path = path.with_suffix(path.suffix + ".npz") if path.suffix else path.with_suffix(".npz")
    arrays: dict[str, np.ndarray] = {}
    metas = []
    for i, ro in enumerate(items):
        meta = dict(ro.meta)
        metas.append(meta)
        wins = list(ro.windows)
        nw = len(wins)
        h_max = int(meta.get("h_max", (wins[0].pose_sim.shape[0] - 1) if wins else 0))
        for name in _WIN_ARRAYS:
            if nw:
                arrays[f"{name}_{i}"] = np.stack([np.asarray(getattr(w, name), dtype=float) for w in wins])
            else:
                h = h_max if name == "cmd" else h_max + 1
                arrays[f"{name}_{i}"] = np.zeros((0, h, 3))
        arrays[f"t0_{i}"] = np.array([int(w.t0) for w in wins], dtype=np.int64)
        arrays[f"idle_{i}"] = np.array([bool(w.idle) for w in wins], dtype=bool)
        for name in ("t0_time", "trans_peak", "trans_mean", "rot_peak", "rot_mean"):
            arrays[f"{name}_{i}"] = np.array([float(getattr(w, name)) for w in wins], dtype=float)
        arrays[f"velb0_{i}"] = np.array([np.asarray(w.velb0, dtype=float).reshape(3) for w in wins],
                                        dtype=float).reshape(nw, 3)
    header = {"format": ROLLOUT_NPZ_FORMAT, "n_rollouts": len(items), "keys": keys, "rollouts": metas}
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, __meta__=np.array(json.dumps(header, default=_json_default)),
                        meta_json=np.array(json.dumps(metas, default=_json_default)),
                        n_segments=np.array(len(items)), **arrays)
    path.with_suffix(".json").write_text(json.dumps(header, indent=1, default=_json_default) + "\n",
                                         encoding="utf-8")
    return path


def load_rollouts(path, as_dict: bool = False):
    """Read rollouts written by ``save_rollouts`` (or by ``analysis.common.save_rsim_cache_npz``).
    Returns a list of ``WindowRollout`` (or a dict keyed by the original keys when ``as_dict``
    and the file was saved from a dict)."""
    path = Path(path)
    with np.load(path, allow_pickle=False) as z:
        names = set(z.files)
        if "__meta__" in names:
            header = json.loads(str(z["__meta__"]))
            if header.get("format") != ROLLOUT_NPZ_FORMAT:
                raise ValueError(f"{path}: unknown rollout file format {header.get('format')!r}")
            metas = header["rollouts"]
            keys = header.get("keys")
        elif "meta_json" in names and "n_segments" in names:      # analysis.common layout
            metas = json.loads(str(z["meta_json"]))
            keys = None
            if len(metas) != int(z["n_segments"]):
                raise ValueError(f"{path}: meta_json/n_segments mismatch")
        else:
            raise ValueError(f"{path}: not a dtssl rollout file (no __meta__/meta_json)")
        out = []
        for i, meta in enumerate(metas):
            t0 = z[f"t0_{i}"]
            nw = int(t0.shape[0])
            cols = {name: z[f"{name}_{i}"] for name in _WIN_ARRAYS + _WIN_SCALARS[1:]}
            velb0 = z[f"velb0_{i}"].reshape(nw, 3)
            wins = [Window(t0=int(t0[k]), t0_time=float(cols["t0_time"][k]),
                           pose_sim=np.array(cols["pose_sim"][k], dtype=float),
                           pose_real=np.array(cols["pose_real"][k], dtype=float),
                           cmd=np.array(cols["cmd"][k], dtype=float),
                           velb=np.array(cols["velb"][k], dtype=float),
                           velb0=tuple(float(v) for v in velb0[k]),
                           trans_peak=float(cols["trans_peak"][k]), trans_mean=float(cols["trans_mean"][k]),
                           rot_peak=float(cols["rot_peak"][k]), rot_mean=float(cols["rot_mean"][k]),
                           idle=bool(cols["idle"][k]))
                    for k in range(nw)]
            out.append(WindowRollout(meta=_meta_from_json(meta), windows=wins))
    if as_dict and keys is not None:
        return dict(zip(keys, out, strict=True))
    return out


class _LegacyUnpickler:
    """Unpickler that resolves the pre-refactor class paths (``phase0_replay.rollout.Window``)."""

    _MAP = {"phase0_replay.rollout": "dtssl.sim.rollout"}

    @classmethod
    def load(cls, fh):
        import importlib
        import pickle

        class U(pickle.Unpickler):
            def find_class(self, module, name):
                module = cls._MAP.get(module, module)
                return getattr(importlib.import_module(module), name)

        return U(fh).load()


def convert_pickle_cache(pkl_path, npz_path) -> Path:
    """Convert the legacy ``results/_cache_rsim_rollouts.pkl`` (dict ``{"0": WindowRollout, ...}``
    pickled with ``phase0_replay.rollout`` class paths) into the ``.npz`` format.

    The ``phase0_replay`` shim is imported when available (it aliases the old module names);
    a mapping unpickler covers the case where the shim is not on ``sys.path``.
    """
    import sys
    import warnings

    try:
        from dtssl.paths import repo_root
        root = str(repo_root())
        if root not in sys.path:
            sys.path.append(root)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            import phase0_replay  # noqa: F401  (compatibility shim)
    except Exception:  # pragma: no cover - shim absent: the mapping unpickler suffices
        pass
    with open(pkl_path, "rb") as fh:
        obj = _LegacyUnpickler.load(fh)
    if isinstance(obj, dict):
        def _key(k):
            try:
                return (0, int(k))
            except (TypeError, ValueError):
                return (1, str(k))
        obj = {k: obj[k] for k in sorted(obj, key=_key)}
    return save_rollouts(npz_path, obj)
