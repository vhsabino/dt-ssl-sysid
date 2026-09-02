"""ETL of ssl-unification logs: ``.log.gz`` (recordio + ``RCLog.Log``) -> per-stream tables -> labeled splits.

Faithful port of ``notebooks/01_logExtractor.ipynb`` (extraction, timestamp normalisation, dataset
writing) and ``notebooks/02_splitByLabels.ipynb`` (annotation chunking and per-event split). The
numeric semantics of the notebooks are reproduced step by step -- same row selection, same float
arithmetic (``timestamp`` cast to float64 in ns, ``((ts - timeref) % 1e13) / 1e9``), same
``sort_values`` call, same chunk arithmetic -- so that re-running the ETL on the archived log
regenerates the frozen dataset ``data/extracted/<dataset>/`` (see docs/refactor_notes/etl.md for
the few documented differences).

Output contract (the one consumed by :mod:`dtssl.data.loader`, MATLAB ``load_split.m`` and
``canonical_split.m``)::

    <dataset>/<stream>.parquet + manifest.json                       (write_dataset)
    <dataset>/splits/<label>/<label>_<anot:02d>_<chunk:02d>/<stream>.parquet   (split_by_labels)
    <dataset>/splits/all_<stream>_labeled.parquet, labels_manifest.csv

Units are the log's (vision frame, **mm**, mm/s, rad; commands in body frame, m/s, rad/s);
``timestamp`` is seconds from the first ball sample of the log and ``timestamp_event`` seconds
from the start of the chunk. SI conversion happens downstream (loader), never here.
"""
from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from dtssl.data import _proto as P
from dtssl.data.recordio import ReadStats, is_gzip_wrapped, iter_records

logger = logging.getLogger(__name__)

#: streams produced by :func:`extract_streams`, in the notebook's order
STREAMS: tuple[str, ...] = ("ball", "raw_ball", "processed_robots", "raw_robots",
                            "commands", "telemetry", "referee")

#: columns of each stream as written by ``write_dataset`` (after normalisation; contract)
COLUMNS: dict[str, tuple[str, ...]] = {
    "ball": ("timestamp", "position_x", "position_y", "velocity_x", "velocity_y",
             "acceleration_x", "acceleration_y", "velocity_norm", "acceleration_norm"),
    "raw_ball": ("timestamp", "position_x", "position_y"),
    "processed_robots": ("timestamp", "team", "robot_id", "position_x", "position_y", "position_w",
                         "velocity_x", "velocity_y", "velocity_norm"),
    "raw_robots": ("timestamp", "team", "robot_id", "position_x", "position_y", "position_w"),
    "commands": ("timestamp", "robot_id", "move_x", "move_y", "move_w",
                 "actuation_kick_strength", "actuation_front", "actuation_chip", "actuation_charge",
                 "actuation_dribbler", "actuation_dribbler_velocity"),
    "telemetry": ("timestamp", "robot_id", "position_x", "position_y", "position_w",
                  "velocity_x", "velocity_y", "velocity_w", "dribbler_speed", "capacitor_charge",
                  "dribbler_ball_contact", "battery", "count", "wheel1", "wheel2", "wheel3", "wheel4"),
    "referee": ("timestamp", "game_state_name"),
}

# dtype of every raw column (timestamp is int64 ns until normalisation casts it to float64)
_DTYPES: dict[str, str] = {
    "timestamp": "int64", "team": "str", "robot_id": "int64", "game_state_name": "str",
    "actuation_front": "bool", "actuation_chip": "bool", "actuation_charge": "bool",
    "actuation_dribbler": "bool", "dribbler_ball_contact": "bool", "count": "int64",
}
_DERIVED = {"velocity_norm", "acceleration_norm"}

#: raw annotations (label, t_start, t_end) in seconds from t=0 of the log, as hard-coded in
#: notebook 02 for the archived log. Kept here so the frozen dataset stays reproducible.
ANNOTATIONS: dict[str, list[tuple[str, float, float]]] = {
    "2026-05-18_19-2-15": [
        ("square", 30.225, 83.991),
        ("square", 1310.665, 1356.748),
        ("front_to_back", 497.298, 530.279),
        ("side_to_side", 341.668, 420.277),
        ("side_to_side", 454.223, 496.798),
        ("shoot_to_goal", 611.654, 616.548),
        ("shoot_to_goal", 617.085, 621.449),
        ("shoot_to_goal", 622.657, 630.929),
        ("shoot_to_goal", 631.534, 640.345),
        ("shoot_to_goal", 659.762, 671.415),
        ("shoot_to_goal", 709.028, 713.959),
        ("shoot_to_goal", 713.412, 720.057),   # overlaps the previous one (kept, as in the notebook)
        ("shoot_to_goal", 721.290, 726.117),
        ("shoot_to_goal", 728.569, 736.909),
        ("shoot_to_goal", 737.314, 742.809),
        ("shoot_to_goal", 743.416, 760.715),
        ("shoot_to_goal", 780.613, 790.155),
        ("shoot_to_goal", 806.835, 815.077),
        ("shoot_to_goal", 815.413, 829.618),
        ("shoot_to_goal", 830.824, 839.775),
    ],
}
CHUNK_MAX_SEC_DEFAULT = 10.0


class ExtractError(RuntimeError):
    """Raised when a log yields no usable data (e.g. no ball samples for the time reference)."""


class Streams(dict):
    """``dict[str, DataFrame]`` of the seven streams plus ``meta`` (log path, timeref, counters)."""

    def __init__(self, *args, meta: dict[str, Any] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.meta: dict[str, Any] = dict(meta or {})


# =============================================================================
# 1) log -> raw rows (notebook 01 §5, one pass over the records)
# =============================================================================
def dataset_name_from_log(log_path: str | Path) -> str:
    """``2026-05-18_19-2-15.log.gz`` -> ``2026-05-18_19-2-15`` (notebook 01 ``out_dir`` rule)."""
    return Path(log_path).stem.replace(".log", "")


def iter_logs(log_path: str | Path, *, stats: ReadStats | None = None,
              decode_errors: str = "skip", max_records: int | None = None) -> Iterator:
    """Decode every record of ``log_path`` as ``RCLog.Log`` (undecodable records are skipped/raised)."""
    n = 0
    for payload in iter_records(log_path, stats=stats):
        try:
            log = P.decode_log(payload)
        except P.LogDecodeError:
            if decode_errors == "raise":
                raise
            if stats is not None:
                stats.bad_records += 1
            continue
        yield log
        n += 1
        if max_records is not None and n >= max_records:
            return


class _Collector:
    """Column-wise accumulation of the raw rows of each stream (log order, int ns timestamps)."""

    def __init__(self):
        self.cols: dict[str, dict[str, list]] = {
            s: {c: [] for c in COLUMNS[s] if c not in _DERIVED} for s in STREAMS
        }
        self.n_records = 0

    def add(self, log) -> None:
        self.n_records += 1
        # --- processed frame: ball + robots (allies/enemies) --------------------------------
        pf = P.processed_frame(log)
        if pf is not None:
            ts = pf.publish_timestamp
            if ts > 1:
                b, c = pf.ball, self.cols["ball"]
                c["timestamp"].append(ts)
                c["position_x"].append(b.position.x)
                c["position_y"].append(b.position.y)
                c["velocity_x"].append(b.velocity.x)
                c["velocity_y"].append(b.velocity.y)
                c["acceleration_x"].append(b.acceleration.x)
                c["acceleration_y"].append(b.acceleration.y)
                c = self.cols["processed_robots"]
                for team, robots in (("allies", pf.allies), ("enemies", pf.enemies)):
                    for r in robots:
                        c["timestamp"].append(ts)
                        c["team"].append(team)
                        c["robot_id"].append(r.id)
                        c["position_x"].append(r.position.x)
                        c["position_y"].append(r.position.y)
                        c["position_w"].append(r.position.omega)
                        c["velocity_x"].append(r.velocity.x)
                        c["velocity_y"].append(r.velocity.y)
        # --- raw vision frames: robots (blue/yellow) + balls ---------------------------------
        for rf in P.raw_frames(log):
            ts = rf.publish_timestamp
            if ts <= 1:
                continue
            det = rf.packet.detection
            c = self.cols["raw_robots"]
            for team, robots in (("robots_blue", det.robots_blue), ("robots_yellow", det.robots_yellow)):
                for r in robots:
                    c["timestamp"].append(ts)
                    c["team"].append(team)
                    c["robot_id"].append(r.robot_id)
                    c["position_x"].append(r.x)
                    c["position_y"].append(r.y)
                    c["position_w"].append(r.orientation)
            c = self.cols["raw_ball"]
            for b in det.balls:
                c["timestamp"].append(ts)
                c["position_x"].append(b.x)
                c["position_y"].append(b.y)
        # --- navigation commands ------------------------------------------------------------
        c = self.cols["commands"]
        for rc in P.robot_commands(log):
            ts = rc.publish_timestamp
            if ts <= 1:
                continue
            mv, ac = rc.move, rc.actuation
            c["timestamp"].append(ts)
            c["robot_id"].append(rc.id)
            c["move_x"].append(mv.x)
            c["move_y"].append(mv.y)
            c["move_w"].append(mv.omega)
            c["actuation_kick_strength"].append(ac.kick_strength)
            c["actuation_front"].append(ac.front)
            c["actuation_chip"].append(ac.chip)
            c["actuation_charge"].append(ac.charge)
            c["actuation_dribbler"].append(ac.dribbler)
            c["actuation_dribbler_velocity"].append(ac.dribbler_velocity)
        # --- telemetry ----------------------------------------------------------------------
        c = self.cols["telemetry"]
        for t in P.telemetries(log):
            ts = t.receive_timestamp
            if ts <= 1:
                continue
            c["timestamp"].append(ts)
            c["robot_id"].append(t.id)
            c["position_x"].append(t.position.x)
            c["position_y"].append(t.position.y)
            c["position_w"].append(t.position.omega)
            c["velocity_x"].append(t.velocity.x)
            c["velocity_y"].append(t.velocity.y)
            c["velocity_w"].append(t.velocity.omega)
            c["dribbler_speed"].append(t.dribbler_speed)
            c["capacitor_charge"].append(t.capacitor_charge)
            c["dribbler_ball_contact"].append(t.dribbler_ball_contact)
            c["battery"].append(t.battery)
            c["count"].append(t.count)
            c["wheel1"].append(t.wheel1)
            c["wheel2"].append(t.wheel2)
            c["wheel3"].append(t.wheel3)
            c["wheel4"].append(t.wheel4)
        # --- referee (game state name; empty names are dropped, as in the notebook) ---------
        ref = P.referee(log)
        if ref is not None and ref.publish_timestamp > 1 and ref.game_state_name:
            c = self.cols["referee"]
            c["timestamp"].append(ref.publish_timestamp)
            c["game_state_name"].append(ref.game_state_name)

    def frames(self) -> dict[str, pd.DataFrame]:
        return {name: _frame(cols) for name, cols in self.cols.items()}


def _frame(cols: dict[str, list]) -> pd.DataFrame:
    data = {}
    for name, values in cols.items():
        dt = _DTYPES.get(name, "float64")
        data[name] = list(values) if dt == "str" else np.asarray(values, dtype=dt)
    return pd.DataFrame(data)


def extract_raw_streams(log_path: str | Path, *, max_records: int | None = None,
                        progress: Callable[[int], None] | None = None) -> Streams:
    """Streams in log order with **ns integer** timestamps (before :func:`normalize_streams`)."""
    stats = ReadStats()
    col = _Collector()
    for log in iter_logs(log_path, stats=stats, max_records=max_records):
        col.add(log)
        if progress is not None and col.n_records % 5000 == 0:
            progress(col.n_records)
    meta = {
        "log_file": str(log_path),
        "n_records": col.n_records,
        "n_bad_records": stats.bad_records,
        "n_resyncs": stats.resyncs,
        "truncated": stats.truncated,
        "gzip_wrapped": stats.gzip_wrapped,
    }
    return Streams(col.frames(), meta=meta)


# =============================================================================
# 2) timestamp normalisation + derived columns (notebook 01 §7)
# =============================================================================
def _norm2(df: pd.DataFrame, column: str) -> pd.Series:
    """``utils.gel_2d_length_in_column``: sqrt(x^2 + y^2) with pandas arithmetic."""
    return np.sqrt(df[column + "_x"] ** 2 + df[column + "_y"] ** 2)


def normalize_streams(dfs: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], float]:
    """Notebook 01 §7 verbatim: cast ``timestamp`` to float64 (ns), drop ``timestamp <= 1``,
    ``timeref`` = smaller first sample of ``ball``/``raw_ball`` (log order), ns -> s via
    ``((ts - timeref) % 1e13) / 1e9``, sort by ``timestamp`` and add the norm columns.

    Returns ``(streams, timeref_ns)``
    the input dict is modified in place.
    """
    for name, df in dfs.items():
        if df.empty:
            continue
        df["timestamp"] = df["timestamp"].astype(float)
        dfs[name] = df[df["timestamp"] > 1].reset_index(drop=True)

    candidates = [d["timestamp"].iloc[0] for d in (dfs["ball"], dfs["raw_ball"]) if not d.empty]
    if not candidates:
        raise ExtractError("neither ball nor raw_ball has data -- check the log")
    timeref = min(candidates)

    for name, df in dfs.items():
        if df.empty:
            continue
        df["timestamp"] = ((df["timestamp"] - timeref) % 1e13) / 1e9
        dfs[name] = df.sort_values("timestamp").reset_index(drop=True)

    if not dfs["ball"].empty:
        dfs["ball"]["velocity_norm"] = _norm2(dfs["ball"], "velocity")
        dfs["ball"]["acceleration_norm"] = _norm2(dfs["ball"], "acceleration")
    if not dfs["processed_robots"].empty:
        dfs["processed_robots"]["velocity_norm"] = _norm2(dfs["processed_robots"], "velocity")
    # empty streams keep the full contract columns (typed) for a stable schema
    for name, df in dfs.items():
        if df.empty:
            for c in COLUMNS[name]:
                if c not in df.columns:
                    df[c] = np.empty(0, dtype=float)
    return dfs, float(timeref)


def extract_streams(log_path: str | Path, *, max_records: int | None = None,
                    progress: Callable[[int], None] | None = None) -> Streams:
    """Notebook 01 in one call: ``.log.gz`` -> the seven normalised streams (seconds from t=0).

    ``streams.meta`` carries ``log_file``, ``timeref_ns`` and the read counters used by
    :func:`write_dataset`. ``max_records`` truncates the log (quick looks at 300 MB files).
    """
    streams = extract_raw_streams(log_path, max_records=max_records, progress=progress)
    dfs, timeref = normalize_streams(dict(streams))
    out = Streams(dfs, meta=streams.meta)
    out.meta["timeref_ns"] = timeref
    for name, df in dfs.items():
        logger.info("%20s: %8d rows, t=[%s, %s] s", name, len(df),
                    f"{df['timestamp'].iloc[0]:.3f}" if len(df) else "-",
                    f"{df['timestamp'].iloc[-1]:.3f}" if len(df) else "-")
    return out


# =============================================================================
# 3) dataset directory (notebook 01 §8)
# =============================================================================
def write_dataset(streams: dict[str, pd.DataFrame], out_dir: str | Path, *,
                  log_file: str | Path | None = None, timeref_ns: float | None = None,
                  csv: bool = False, parquet: bool = True) -> Path:
    """Write ``<out_dir>/<stream>.parquet`` (+ ``.csv`` if ``csv``) and ``manifest.json``.

    ``log_file``/``timeref_ns`` default to ``streams.meta`` (set by :func:`extract_streams`).
    The manifest keeps the notebook keys (``log_file``, ``timeref_ns``, ``tables``) and adds an
    ``extraction`` block with provenance. Returns the manifest path.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = dict(getattr(streams, "meta", {}) or {})
    if log_file is not None:
        meta["log_file"] = str(log_file)
    if timeref_ns is not None:
        meta["timeref_ns"] = float(timeref_ns)
    manifest: dict[str, Any] = {
        "log_file": meta.get("log_file"),
        "timeref_ns": float(meta["timeref_ns"]) if meta.get("timeref_ns") is not None else None,
        "tables": {},
    }
    for name, df in streams.items():
        base = out_dir / name
        if csv:
            df.to_csv(base.with_suffix(".csv"), index=False)
        if parquet and not df.empty:
            df.to_parquet(base.with_suffix(".parquet"), index=False)
        manifest["tables"][name] = {
            "rows": int(len(df)),
            "columns": list(df.columns),
            "t_start": float(df["timestamp"].iloc[0]) if not df.empty else None,
            "t_end": float(df["timestamp"].iloc[-1]) if not df.empty else None,
        }
    extraction = {k: meta[k] for k in ("n_records", "n_bad_records", "n_resyncs", "truncated", "gzip_wrapped")
                  if k in meta}
    if extraction:
        from dtssl import __version__

        extraction["dtssl_version"] = __version__
        extraction["tool"] = "dtssl.data.extract"
        manifest["extraction"] = extraction
    path = out_dir / "manifest.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    return path


def read_dataset(dataset_dir: str | Path, streams: Iterable[str] = STREAMS) -> dict[str, pd.DataFrame]:
    """Notebook 02 ``_load_stream``: parquet if present, else csv, else an empty frame."""
    dataset_dir = Path(dataset_dir)
    out = {}
    for name in streams:
        pq = dataset_dir / f"{name}.parquet"
        cs = dataset_dir / f"{name}.csv"
        if pq.exists():
            out[name] = pd.read_parquet(pq)
        elif cs.exists() and cs.stat().st_size > 0:
            out[name] = pd.read_csv(cs)
        else:
            out[name] = pd.DataFrame()
    return out


def read_manifest(dataset_dir: str | Path) -> dict[str, Any]:
    with open(Path(dataset_dir) / "manifest.json", encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# 4) annotations -> chunks (notebook 02 §3-§5)
# =============================================================================
def _safe(s: Any) -> str:
    return re.sub(r"[^A-Za-z0-9_\-]+", "_", str(s))


def annotations_frame(labels: Any, dataset: str | None = None) -> pd.DataFrame:
    """Raw annotations as a ``DataFrame(label, t_start, t_end, duration)``.

    ``labels`` may be ``None`` (built-in :data:`ANNOTATIONS` of ``dataset``), a CSV path with
    columns ``label,t_start,t_end``, a DataFrame or an iterable of ``(label, t_start, t_end)``
    tuples / dicts.
    """
    if labels is None:
        if dataset not in ANNOTATIONS:
            raise KeyError(f"no built-in annotations for dataset {dataset!r}; pass a labels CSV "
                           f"(known: {sorted(ANNOTATIONS)})")
        labels = ANNOTATIONS[dataset]
    if isinstance(labels, (str, Path)):
        df = pd.read_csv(labels)
    elif isinstance(labels, pd.DataFrame):
        df = labels.copy()
    else:
        rows = [r if isinstance(r, dict) else {"label": r[0], "t_start": r[1], "t_end": r[2]} for r in labels]
        df = pd.DataFrame(rows)
    missing = {"label", "t_start", "t_end"} - set(df.columns)
    if missing:
        raise ValueError(f"annotations missing columns {sorted(missing)}")
    df = df[["label", "t_start", "t_end"]].reset_index(drop=True)
    df["label"] = df["label"].astype(str)
    df["t_start"] = df["t_start"].astype(float)
    df["t_end"] = df["t_end"].astype(float)
    df["duration"] = df["t_end"] - df["t_start"]
    return df


def chunk_intervals(intervals: pd.DataFrame, max_sec: float = CHUNK_MAX_SEC_DEFAULT) -> pd.DataFrame:
    """Notebook 02 ``chunk_intervals``: each annotation of duration ``D`` becomes
    ``N = max(1, ceil(D / max_sec))`` contiguous chunks of equal length ``D/N``; ``source_idx`` counts
    annotations *per label* (order of appearance); ``event_id = <label>_<source:02d>_<chunk:02d>``."""
    rows = []
    for label, grp in intervals.groupby("label", sort=False):
        for src_idx, (_, ev) in enumerate(grp.iterrows(), start=1):
            t0, t1 = float(ev["t_start"]), float(ev["t_end"])
            dur = t1 - t0
            n = max(1, int(np.ceil(dur / max_sec)))
            cdur = dur / n
            for ck in range(1, n + 1):
                rows.append({
                    "label": label,
                    "source_idx": src_idx,
                    "chunk_idx": ck,
                    "n_chunks": n,
                    "t_start": t0 + (ck - 1) * cdur,
                    "t_end": t0 + ck * cdur,
                    "duration": cdur,
                })
    out = pd.DataFrame(rows)
    out["event_id"] = [f"{_safe(lab)}_{s:02d}_{c:02d}"
                       for lab, s, c in zip(out["label"], out["source_idx"], out["chunk_idx"], strict=True)]
    return out


def validate_intervals(intervals: pd.DataFrame, dfs: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Notebook 02 §5: chunks must lie inside the log; overlaps between annotations are reported."""
    if not (intervals["t_end"] > intervals["t_start"]).all():
        raise ValueError("t_end <= t_start in some interval")
    nonempty = [d for d in dfs.values() if not d.empty and "timestamp" in d.columns]
    t_min = min(d["timestamp"].iloc[0] for d in nonempty)
    t_max = max(d["timestamp"].iloc[-1] for d in nonempty)
    out_of = intervals[(intervals["t_start"] < t_min) | (intervals["t_end"] > t_max)]
    if not out_of.empty:
        logger.warning("%d chunks outside the log [%.2f, %.2f] s:\n%s", len(out_of), t_min, t_max,
                       out_of[["event_id", "t_start", "t_end"]].to_string(index=False))
    else:
        logger.info("all %d chunks inside the log [%.2f, %.2f] s", len(intervals), t_min, t_max)
    src = (intervals.groupby(["label", "source_idx"])
           .agg(t_start=("t_start", "min"), t_end=("t_end", "max"))
           .reset_index().sort_values("t_start").reset_index(drop=True))
    overlaps = []
    for i in range(len(src) - 1):
        if src.loc[i, "t_end"] > src.loc[i + 1, "t_start"]:
            overlaps.append((f"{src.loc[i, 'label']}#{src.loc[i, 'source_idx']}",
                             f"{src.loc[i + 1, 'label']}#{src.loc[i + 1, 'source_idx']}"))
    if overlaps:
        logger.info("overlapping annotations (ok, just recording): %s",
                    "; ".join(f"{a} <-> {b}" for a, b in overlaps))
    return {"t_min": float(t_min), "t_max": float(t_max), "out_of_range": out_of, "overlaps": overlaps}


# =============================================================================
# 5) split (notebook 02 §6)
# =============================================================================
def split_dataset(dfs: dict[str, pd.DataFrame], intervals: pd.DataFrame, out_root: str | Path, *,
                  save_per_event: bool = True, save_concat: bool = True, rebase: bool = True,
                  csv: bool = False) -> pd.DataFrame:
    """Notebook 02 ``split_dataset``: for each chunk and stream select ``t_start <= timestamp < t_end``,
    add ``timestamp_event = timestamp - t_start``, write ``<out_root>/<label>/<event_id>/<stream>.parquet``
    (+ csv), concatenate per stream into ``all_<stream>_labeled.parquet`` (with ``label``,
    ``event_id``, ``source_idx``, ``chunk_idx``) and write ``labels_manifest.csv``. Returns the manifest."""
    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    manifest = []
    concat: dict[str, list[pd.DataFrame]] = {name: [] for name in dfs}

    for _, ev in intervals.iterrows():
        t0, t1 = float(ev["t_start"]), float(ev["t_end"])
        label = ev["label"]
        event_id = ev["event_id"]

        rec: dict[str, Any] = {"event_id": event_id, "label": label,
                               "source_idx": int(ev["source_idx"]),
                               "chunk_idx": int(ev["chunk_idx"]),
                               "n_chunks": int(ev["n_chunks"]),
                               "t_start": t0, "t_end": t1, "duration": t1 - t0}

        event_dir = out_root / _safe(label) / event_id
        if save_per_event:
            event_dir.mkdir(parents=True, exist_ok=True)

        for name, df in dfs.items():
            if df.empty or "timestamp" not in df.columns:
                rec[f"{name}_rows"] = 0
                continue

            # [t0, t1) -> no double counting at the boundary between contiguous chunks
            mask = (df["timestamp"] >= t0) & (df["timestamp"] < t1)
            sub = df.loc[mask].copy()
            if rebase and not sub.empty:
                sub["timestamp_event"] = sub["timestamp"] - t0

            rec[f"{name}_rows"] = int(len(sub))

            if save_per_event and not sub.empty:
                if csv:
                    sub.to_csv(event_dir / f"{name}.csv", index=False)
                sub.to_parquet(event_dir / f"{name}.parquet", index=False)

            if save_concat and not sub.empty:
                sub["label"] = label
                sub["event_id"] = event_id
                sub["source_idx"] = int(ev["source_idx"])
                sub["chunk_idx"] = int(ev["chunk_idx"])
                concat[name].append(sub)

        manifest.append(rec)

    manifest_df = pd.DataFrame(manifest)
    manifest_df.to_csv(out_root / "labels_manifest.csv", index=False)

    if save_concat:
        for name, chunks in concat.items():
            if not chunks:
                continue
            big = pd.concat(chunks, ignore_index=True)
            big.to_parquet(out_root / f"all_{name}_labeled.parquet", index=False)

    return manifest_df


def split_by_labels(dataset_dir: str | Path, labels: Any = None, chunk_s: float = CHUNK_MAX_SEC_DEFAULT, *,
                    out_dir: str | Path | None = None, streams: Iterable[str] = STREAMS,
                    csv: bool = False, save_per_event: bool = True, save_concat: bool = True,
                    rebase: bool = True, validate: bool = True) -> pd.DataFrame:
    """Notebook 02 in one call: ``<dataset_dir>/<stream>.parquet`` + annotations -> ``<dataset_dir>/splits``.

    ``labels``: CSV path (``label,t_start,t_end`` in seconds from t=0 of the log), DataFrame, list
    of tuples, or ``None`` for the built-in annotations of the dataset (directory name).
    Returns the labels manifest (one row per chunk with the row count of every stream).
    """
    dataset_dir = Path(dataset_dir)
    out_dir = Path(out_dir) if out_dir is not None else dataset_dir / "splits"
    dfs = read_dataset(dataset_dir, streams)
    raw = annotations_frame(labels, dataset=dataset_dir.name)
    intervals = chunk_intervals(raw, chunk_s)
    logger.info("annotations: %d -> chunks: %d (chunk_s=%.2f)", len(raw), len(intervals), chunk_s)
    if validate:
        validate_intervals(intervals, dfs)
    manifest = split_dataset(dfs, intervals, out_dir, save_per_event=save_per_event,
                             save_concat=save_concat, rebase=rebase, csv=csv)
    logger.info("%d sub-events written to %s", len(manifest), out_dir)
    return manifest


# =============================================================================
# 6) quick inspection (dtssl etl inspect)
# =============================================================================
def inspect_log(log_path: str | Path, *, max_records: int | None = None) -> dict[str, Any]:
    """Counts per stream and time span of a log without building the tables.

    Returns ``records``, ``bad_records``, ``gzip_wrapped``, ``truncated``, ``size_bytes``, per-stream
    ``counts`` (rows as :func:`extract_streams` would produce them, plus ``raw_referee`` records and
    ``raw_frames``), ``t_first``/``t_last`` (s, absolute epoch) per timestamp source (``ball`` =
    processed frame, ``raw_frames``, ``commands``, ``telemetry``, ``referee``, ``raw_referee``) and
    ``duration_s`` (span between the earliest and the latest of them).
    """
    log_path = Path(log_path)
    stats = ReadStats()
    counts = {"records": 0, "raw_frames": 0, "raw_referee": 0, **{s: 0 for s in STREAMS}}
    first: dict[str, int] = {}
    last: dict[str, int] = {}

    def see(name: str, ts: int) -> None:
        if ts <= 1:
            return
        if name not in first or ts < first[name]:
            first[name] = ts
        if name not in last or ts > last[name]:
            last[name] = ts

    for log in iter_logs(log_path, stats=stats, max_records=max_records):
        counts["records"] += 1
        pf = P.processed_frame(log)
        if pf is not None and pf.publish_timestamp > 1:
            counts["ball"] += 1
            counts["processed_robots"] += len(pf.allies) + len(pf.enemies)
            see("ball", pf.publish_timestamp)
        for rf in P.raw_frames(log):
            counts["raw_frames"] += 1
            if rf.publish_timestamp > 1:
                det = rf.packet.detection
                counts["raw_ball"] += len(det.balls)
                counts["raw_robots"] += len(det.robots_blue) + len(det.robots_yellow)
                see("raw_frames", rf.publish_timestamp)
        for rc in P.robot_commands(log):
            if rc.publish_timestamp > 1:
                counts["commands"] += 1
                see("commands", rc.publish_timestamp)
        for t in P.telemetries(log):
            if t.receive_timestamp > 1:
                counts["telemetry"] += 1
                see("telemetry", t.receive_timestamp)
        ref = P.referee(log)
        if ref is not None and ref.publish_timestamp > 1 and ref.game_state_name:
            counts["referee"] += 1
            see("referee", ref.publish_timestamp)
        rr = P.raw_referee(log)
        if rr is not None:
            counts["raw_referee"] += 1
            see("raw_referee", rr.publish_timestamp)

    t_first = {k: v / 1e9 for k, v in first.items()}
    t_last = {k: v / 1e9 for k, v in last.items()}
    duration = (max(last.values()) - min(first.values())) / 1e9 if first else 0.0
    return {
        "log_file": str(log_path),
        "size_bytes": log_path.stat().st_size,
        "gzip_wrapped": is_gzip_wrapped(log_path),
        "records": counts["records"],
        "bad_records": stats.bad_records,
        "resyncs": stats.resyncs,
        "truncated": stats.truncated,
        "counts": counts,
        "t_first": t_first,
        "t_last": t_last,
        "duration_s": float(duration),
    }


__all__ = [
    "STREAMS", "COLUMNS", "ANNOTATIONS", "CHUNK_MAX_SEC_DEFAULT", "ExtractError", "Streams",
    "dataset_name_from_log", "iter_logs", "extract_raw_streams", "normalize_streams", "extract_streams",
    "write_dataset", "read_dataset", "read_manifest",
    "annotations_frame", "chunk_intervals", "validate_intervals", "split_dataset", "split_by_labels",
    "inspect_log",
]
