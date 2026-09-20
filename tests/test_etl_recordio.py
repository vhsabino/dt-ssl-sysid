"""recordio container: round trip, gzip-wrapped variant, corruption/truncation handling."""
from __future__ import annotations

import gzip
import os
import struct
import zlib

import pytest

from dtssl.data import recordio as R


@pytest.fixture
def payloads() -> list[bytes]:
    rng = os.urandom
    return [rng(10), b"", b"x" * 100_000, bytes(range(256)) * 3, rng(1)]


def test_header_layout_matches_recordio_cpp():
    rec = R.pack_record(b"abc", compress=False)
    magic, usize, csize = struct.unpack("<iQQ", rec[:20])
    assert magic == 0x3ED7230A and R.MAGIC_BYTES == b"\x0a\x23\xd7\x3e"
    assert (usize, csize) == (3, 0) and rec[20:] == b"abc"
    rec = R.pack_record(b"abc")
    magic, usize, csize = struct.unpack("<iQQ", rec[:20])
    assert usize == 3 and csize == len(rec) - 20
    assert zlib.decompress(rec[20:]) == b"abc"  # zlib format (RFC 1950), as zlib compress()


def test_round_trip_raw_container_with_gz_misnomer(tmp_path, payloads):
    path = tmp_path / "2026-01-01_00-0-00.log.gz"  # named .gz but NOT gzip, like ssl-unification
    assert R.write_records(path, payloads) == len(payloads)
    assert not R.is_gzip_wrapped(path)
    stats = R.ReadStats()
    assert list(R.iter_records(path, stats=stats)) == payloads
    assert stats.records == len(payloads) and stats.bad_records == 0 and not stats.truncated
    assert R.count_records(path) == len(payloads)


def test_round_trip_uncompressed_records(tmp_path, payloads):
    path = tmp_path / "plain.log"
    R.write_records(path, payloads, compress=False)
    assert R.read_records(path) == payloads


def test_round_trip_gzip_wrapped(tmp_path, payloads):
    path = tmp_path / "wrapped.log.gz"
    R.write_records(path, payloads, gzip_wrap=True)
    assert R.is_gzip_wrapped(path)
    with gzip.open(path, "rb") as f:
        assert f.read(4) == R.MAGIC_BYTES
    stats = R.ReadStats()
    assert list(R.iter_records(path, stats=stats)) == payloads
    assert stats.gzip_wrapped


def test_append_mode(tmp_path, payloads):
    path = tmp_path / "a.log.gz"
    R.write_records(path, payloads[:2])
    R.write_records(path, payloads[2:], append=True)
    assert R.read_records(path) == payloads
    with pytest.raises(ValueError):
        R.write_records(path, payloads, append=True, gzip_wrap=True)


def test_file_object_source(tmp_path, payloads):
    path = tmp_path / "f.log.gz"
    R.write_records(path, payloads)
    with open(path, "rb") as f:
        assert list(R.iter_records(f)) == payloads


def test_corruption_is_skipped_and_resynced(tmp_path, payloads):
    good = [R.pack_record(p) for p in payloads]
    bad_zlib = struct.pack("<iQQ", R.MAGIC, 50, 10) + b"\x00" * 10
    wrong_size = struct.pack("<iQQ", R.MAGIC, 999, 0)  # declares 999 bytes but ...
    data = (good[0] + b"GARBAGE\x0a\x23\xd7GARB" + good[1] + bad_zlib + good[2]
            + struct.pack("<iQQ", R.MAGIC, 7, len(zlib.compress(b"1234567"))) + zlib.compress(b"1234567")
            + good[3] + wrong_size[:12])  # truncated header at the very end
    path = tmp_path / "corrupt.log.gz"
    path.write_bytes(data)
    stats = R.ReadStats()
    out = list(R.iter_records(path, stats=stats))
    assert out == payloads[:3] + [b"1234567", payloads[3]]
    assert stats.bad_records == 1 and stats.resyncs == 1 and stats.skipped_bytes == 14
    assert stats.truncated
    with pytest.raises(R.RecordIOError):
        list(R.iter_records(path, strict=True))


def test_truncated_payload_ends_iteration(tmp_path, payloads):
    path = tmp_path / "trunc.log.gz"
    R.write_records(path, payloads)
    data = path.read_bytes()
    path.write_bytes(data[: len(data) - 1])  # cut the last byte of the last record
    stats = R.ReadStats()
    assert list(R.iter_records(path, stats=stats)) == payloads[:-1]
    assert stats.truncated
    with pytest.raises(R.RecordIOError):
        list(R.iter_records(path, strict=True))


def test_size_mismatch_is_skipped(tmp_path):
    comp = zlib.compress(b"hello")
    rec = struct.pack("<iQQ", R.MAGIC, 4, len(comp)) + comp  # header says 4, payload is 5
    path = tmp_path / "mismatch.log.gz"
    path.write_bytes(rec + R.pack_record(b"ok"))
    stats = R.ReadStats()
    assert list(R.iter_records(path, stats=stats)) == [b"ok"]
    assert stats.bad_records == 1


def test_empty_file(tmp_path):
    path = tmp_path / "empty.log.gz"
    path.write_bytes(b"")
    assert R.read_records(path) == []
