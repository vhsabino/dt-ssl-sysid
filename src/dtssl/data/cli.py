"""``dtssl etl ...`` -- command-line front end of the ETL (:mod:`dtssl.data.extract` / :mod:`dtssl.data.rotate`).

Wired into the top-level ``dtssl`` CLI through :func:`register` (``register(parser.add_subparsers())``
adds the ``etl`` command with its sub-commands); also runnable on its own::

    python -m dtssl.data.cli extract logs/2026-05-18_19-2-15.log.gz data/extracted/2026-05-18_19-2-15
    python -m dtssl.data.cli split   data/extracted/2026-05-18_19-2-15 [labels.csv] [--chunk-s 10]
    python -m dtssl.data.cli rotate  data/extracted/<ds>/splits/rotate/rotate_raw.csv data/extracted/<ds>/splits/rotate
    python -m dtssl.data.cli inspect logs/2026-05-18_19-2-15.log.gz [--json]

Every sub-parser stores its handler in ``args.func`` (convention of the ``dtssl`` CLI).
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ETL_HELP = "log ETL: extract ssl-unification .log.gz, split by labels, rotate dataset, inspect"


# ----------------------------------------------------------------------------- handlers
def cmd_extract(args: argparse.Namespace) -> int:
    from dtssl.data.extract import extract_streams, write_dataset

    log = Path(args.log)
    out = Path(args.out)
    print(f"[etl extract] log: {log}")
    streams = extract_streams(log, max_records=args.max_records,
                              progress=lambda n: print(f"[etl extract] {n} records ...", file=sys.stderr))
    for name, df in streams.items():
        t = (f"t=[{df['timestamp'].iloc[0]:.3f}, {df['timestamp'].iloc[-1]:.3f}] s" if len(df) else "empty")
        print(f"{name:>20s}: {len(df):>8d} rows, {len(df.columns):>2d} cols  {t}")
    m = streams.meta
    print(f"[etl extract] records={m['n_records']} undecodable={m['n_bad_records']} resyncs={m['n_resyncs']} "
          f"truncated={m['truncated']} timeref_ns={m['timeref_ns']:.0f}")
    manifest = write_dataset(streams, out, csv=args.csv)
    print(f"[etl extract] dataset written to {out} ({manifest.name})")
    return 0


def cmd_split(args: argparse.Namespace) -> int:
    from dtssl.data.extract import split_by_labels

    manifest = split_by_labels(Path(args.dataset_dir), args.labels, args.chunk_s,
                               out_dir=args.out, csv=args.csv, save_concat=not args.no_concat)
    row_cols = [c for c in manifest.columns if c.endswith("_rows")]
    by_label = manifest.groupby("label")[row_cols].sum()
    by_label.insert(0, "n_events", manifest.groupby("label").size())
    print(by_label.to_string())
    if "ball_rows" in manifest.columns:  # notebook 02 §7 sanity: probable gap in the log
        thin = manifest[manifest["ball_rows"] < 30]
        if len(thin):
            print(f"[etl split] WARNING: {len(thin)} chunks with < 30 ball samples: {list(thin['event_id'])}")
    out = Path(args.out) if args.out else Path(args.dataset_dir) / "splits"
    print(f"[etl split] {len(manifest)} sub-events written to {out}")
    return 0


def cmd_rotate(args: argparse.Namespace) -> int:
    from dtssl.data.rotate import build_rotate_splits

    metas = build_rotate_splits(Path(args.raw_csv), Path(args.out), geometry=args.geometry, dataset=args.dataset,
                                pad_s=args.pad_s, sg_win=args.sg_win, sg_order=args.sg_order, csv=args.csv,
                                qc=args.qc, qc_report=args.qc_report, figs_dir=args.figs_dir)
    for md in metas:
        print(f"[etl rotate] {md['event']}: w={md['cmd_w_amplitude_rad_s']:+.2f} rad/s -> {md['split']:9s} "
              f"({md['duration_padded_s']:.2f} s)")
    print(f"[etl rotate] {len(metas)} events written to {args.out}")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    from dtssl.data.extract import STREAMS, inspect_log

    info = inspect_log(Path(args.log), max_records=args.max_records)
    if args.json:
        print(json.dumps(info, indent=2))
        return 0
    print(f"log:        {info['log_file']} ({info['size_bytes'] / 1e6:.1f} MB, "
          f"{'gzip-wrapped' if info['gzip_wrapped'] else 'raw recordio'})")
    print(f"records:    {info['records']} (undecodable {info['bad_records']}, resyncs {info['resyncs']}, "
          f"truncated {info['truncated']})")
    print(f"duration:   {info['duration_s']:.3f} s")
    print(f"{'stream':>18s} {'rows':>8s} {'t_first (s)':>16s} {'t_last (s)':>16s}")
    key_of = {"raw_ball": "raw_frames", "raw_robots": "raw_frames", "processed_robots": "ball"}
    for name in (*STREAMS, "raw_frames", "raw_referee"):
        key = key_of.get(name, name)
        tf, tl = info["t_first"].get(key), info["t_last"].get(key)
        print(f"{name:>18s} {info['counts'][name]:>8d} "
              f"{(f'{tf:.3f}' if tf is not None else '-'):>16s} {(f'{tl:.3f}' if tl is not None else '-'):>16s}")
    return 0


# ----------------------------------------------------------------------------- parsers
def add_etl_commands(sub: argparse._SubParsersAction) -> None:
    """Add ``extract``/``split``/``rotate``/``inspect`` to an ``etl``-level subparsers action."""
    p = sub.add_parser("extract", help="ssl-unification .log.gz -> <out>/<stream>.parquet + manifest.json")
    p.add_argument("log", help="log file (recordio; the .gz suffix is a misnomer, real gzip also accepted)")
    p.add_argument("out", help="dataset directory, e.g. data/extracted/2026-05-18_19-2-15")
    p.add_argument("--csv", action="store_true", help="also write <stream>.csv (the notebook wrote both)")
    p.add_argument("--max-records", type=int, default=None, help="stop after N records (quick look)")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("split", help="dataset -> splits/<label>/<label>_<anot>_<chunk>/<stream>.parquet")
    p.add_argument("dataset_dir", help="directory written by `etl extract`")
    p.add_argument("labels", nargs="?", default=None,
                   help="annotations CSV (label,t_start,t_end in s from t=0); default: built-in "
                        "annotations of the dataset (2026-05-18_19-2-15)")
    p.add_argument("--chunk-s", type=float, default=10.0, help="max chunk duration (s), default 10")
    p.add_argument("--out", default=None, help="output directory (default <dataset_dir>/splits)")
    p.add_argument("--csv", action="store_true", help="also write per-event csv")
    p.add_argument("--no-concat", action="store_true", help="skip all_<stream>_labeled.parquet")
    p.set_defaults(func=cmd_split)

    p = sub.add_parser("rotate", help="rotate_raw.csv (multiplexed) -> rotate_01_01..10 splits (+ QC)")
    p.add_argument("raw_csv", help="path of rotate_raw.csv (never modified)")
    p.add_argument("out", help="parent directory of rotate_01_XX (normally .../splits/rotate)")
    p.add_argument("--dataset", default="2026-05-18_19-2-15")
    p.add_argument("--geometry", default=None, help="robot_geometry.json (default config/robot_geometry.json)")
    p.add_argument("--pad-s", type=float, default=0.2)
    p.add_argument("--sg-win", type=int, default=7)
    p.add_argument("--sg-order", type=int, default=2)
    p.add_argument("--csv", action="store_true", help="also write per-event csv")
    p.add_argument("--qc", action="store_true", help="write the QC report (results/qc_rotate_<ts>.md + figs)")
    p.add_argument("--qc-report", default=None, help="QC markdown path (default results/qc_rotate_<ts>.md)")
    p.add_argument("--figs-dir", default=None, help="QC figures directory (default <report dir>/figs)")
    p.set_defaults(func=cmd_rotate)

    p = sub.add_parser("inspect", help="counts per stream and duration of a log (no tables written)")
    p.add_argument("log")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("--max-records", type=int, default=None)
    p.set_defaults(func=cmd_inspect)


def register(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Register ``dtssl etl <extract|split|rotate|inspect>`` on the top-level subparsers."""
    etl = subparsers.add_parser("etl", help=ETL_HELP, description=ETL_HELP)
    sub = etl.add_subparsers(dest="etl_cmd", metavar="COMMAND")
    sub.required = True
    add_etl_commands(sub)
    return etl


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dtssl etl", description=ETL_HELP)
    parser.add_argument("-v", "--verbose", action="store_true", help="INFO logging of the ETL steps")
    sub = parser.add_subparsers(dest="etl_cmd", metavar="COMMAND")
    sub.required = True
    add_etl_commands(sub)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO if getattr(args, "verbose", False) else logging.WARNING,
                        format="%(name)s: %(message)s")
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
