"""``dtssl etl`` CLI: register() on a parent parser and the standalone main() on a synthetic log."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import pytest

from dtssl.data import cli
from dtssl.data.extract import STREAMS
from test_etl_extract import DATASET, build_synthetic_log


@pytest.fixture(scope="module")
def log(tmp_path_factory) -> Path:
    p = tmp_path_factory.mktemp("cli") / f"{DATASET}.log.gz"
    build_synthetic_log(p, n_frames=300)
    return p


def test_register_adds_etl_subcommands():
    parser = argparse.ArgumentParser(prog="dtssl")
    sub = parser.add_subparsers(dest="cmd")
    cli.register(sub)
    args = parser.parse_args(["etl", "extract", "a.log.gz", "out", "--csv"])
    assert args.cmd == "etl" and args.etl_cmd == "extract" and args.func is cli.cmd_extract and args.csv
    args = parser.parse_args(["etl", "split", "ds"])
    assert args.func is cli.cmd_split and args.labels is None and args.chunk_s == 10.0
    args = parser.parse_args(["etl", "rotate", "raw.csv", "out", "--qc"])
    assert args.func is cli.cmd_rotate and args.qc
    args = parser.parse_args(["etl", "inspect", "a.log.gz", "--json"])
    assert args.func is cli.cmd_inspect
    with pytest.raises(SystemExit):
        parser.parse_args(["etl"])


def test_inspect_json(log, capsys):
    assert cli.main(["inspect", str(log), "--json"]) == 0
    info = json.loads(capsys.readouterr().out)
    assert info["records"] == 301 and info["counts"]["commands"] == 600 and info["bad_records"] == 1


def test_extract_then_split(log, tmp_path, capsys):
    out = tmp_path / DATASET
    assert cli.main(["extract", str(log), str(out), "--max-records", "201"]) == 0
    assert (out / "manifest.json").is_file() and (out / "commands.parquet").is_file()
    assert "commands:      400 rows" in capsys.readouterr().out
    labels = tmp_path / "labels.csv"
    labels.write_text("label,t_start,t_end\nsquare,0.5,2.5\n")
    assert cli.main(["split", str(out), str(labels), "--chunk-s", "1.0"]) == 0
    text = capsys.readouterr().out
    assert "2 sub-events written" in text
    for name in STREAMS:
        assert (out / "splits" / "square" / "square_01_02" / f"{name}.parquet").is_file()
    m = pd.read_csv(out / "splits" / "labels_manifest.csv")
    assert list(m["event_id"]) == ["square_01_01", "square_01_02"]
