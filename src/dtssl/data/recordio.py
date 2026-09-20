"""Pure-Python reader/writer for the ssl-unification ``recordio`` log container.

Wire format (``<ssl-unification>/libs/recordio/include/recordio.{h,cpp}``), one record after
another, no file header::

    int32  LE   magic              = 0x3ED7230A
    uint64 LE   uncompressed_size
    uint64 LE   compressed_size    (0 => the payload is stored uncompressed)
    bytes       payload            zlib stream (zlib ``compress()``, RFC 1950) of ``compressed_size``
                                   bytes, or ``uncompressed_size`` raw bytes when not compressed

Every payload written by the ssl-unification ``Logger`` module is a serialized ``RCLog.Log``
protobuf (``rc_log.proto``); decoding is the job of :mod:`dtssl.data._proto`. This module only
deals with bytes, so it has no protobuf dependency and can round-trip any payload.

The Logger names its files ``<date>.log.gz`` but opens them with plain ``fopen`` -- the files are
NOT gzip archives (the suffix is a misnomer; ``gzip -d`` fails on them). :func:`open_binary` sniffs
the two gzip magic bytes (``1f 8b``) and transparently unwraps a *really* gzipped container too, so
both forms are accepted (``write_records(..., gzip_wrap=True)`` produces the latter).

Robustness (mirrors the legacy ``pyrecordio`` reader, which skipped bad records): by default a
record whose zlib stream is corrupt or whose size does not match is skipped, a magic mismatch
triggers a byte-wise resynchronisation on the next magic, and a truncated tail (logger killed
mid-write) ends the iteration silently. ``strict=True`` raises :class:`RecordIOError` instead.
"""
from __future__ import annotations

import gzip
import struct
import zlib
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

MAGIC = 0x3ED7230A
MAGIC_BYTES = struct.pack("<i", MAGIC)
_HEADER = struct.Struct("<iQQ")
HEADER_SIZE = _HEADER.size  # 20
_GZIP_MAGIC = b"\x1f\x8b"
_RESYNC_CHUNK = 1 << 16


class RecordIOError(ValueError):
    """Malformed container (only raised in ``strict`` mode)."""


@dataclass
class ReadStats:
    """Counters filled by :func:`iter_records` (pass an instance to collect them)."""

    records: int = 0            # records yielded
    bad_records: int = 0        # records skipped (zlib error / size mismatch)
    resyncs: int = 0            # magic mismatches recovered by scanning forward
    skipped_bytes: int = 0      # bytes discarded while resynchronising
    truncated: bool = False     # file ended in the middle of a record
    gzip_wrapped: bool = False  # the container itself was gzip-compressed


# ----------------------------------------------------------------------------- helpers
def is_gzip_wrapped(path: str | Path) -> bool:
    """True when the file starts with the gzip magic (real gzip archive, not the misnomer)."""
    with open(path, "rb") as f:
        return f.read(2) == _GZIP_MAGIC


def open_binary(path: str | Path) -> BinaryIO:
    """Open ``path`` for reading, unwrapping a gzip envelope when one is present."""
    if is_gzip_wrapped(path):
        return gzip.open(path, "rb")  # type: ignore[return-value]
    return open(path, "rb")


class _Stream:
    """Minimal read/unread wrapper so that resync can push bytes back."""

    def __init__(self, f: BinaryIO):
        self.f = f
        self.buf = b""

    def read(self, n: int) -> bytes:
        if n <= 0:
            return b""
        if len(self.buf) >= n:
            out, self.buf = self.buf[:n], self.buf[n:]
            return out
        out = self.buf + self.f.read(n - len(self.buf))
        self.buf = b""
        return out

    def unread(self, data: bytes) -> None:
        self.buf = data + self.buf


def _resync(s: _Stream, window: bytes, stats: ReadStats) -> bool:
    """Scan forward for the next magic; leave the stream positioned at it. False at EOF."""
    start = 1  # window[0:4] is the bad magic we already rejected
    skipped = 0
    while True:
        i = window.find(MAGIC_BYTES, start)
        if i >= 0:
            s.unread(window[i:])
            stats.skipped_bytes += skipped + i
            stats.resyncs += 1
            return True
        skipped += max(0, len(window) - (len(MAGIC_BYTES) - 1))
        tail = window[-(len(MAGIC_BYTES) - 1):]
        chunk = s.read(_RESYNC_CHUNK)
        if not chunk:
            stats.skipped_bytes += skipped + len(tail)
            return False
        window = tail + chunk
        start = 0


# ----------------------------------------------------------------------------- reader
def iter_records(source: str | Path | BinaryIO, *, strict: bool = False,
                 stats: ReadStats | None = None) -> Iterator[bytes]:
    """Yield the (decompressed) payload of every record in ``source``.

    ``source`` is a path (``.log.gz`` misnomer or real gzip both accepted) or an open binary file.
    ``stats`` (optional :class:`ReadStats`) receives counters about skipped/corrupt data.
    """
    stats = stats if stats is not None else ReadStats()
    own = not hasattr(source, "read")
    if own:
        stats.gzip_wrapped = is_gzip_wrapped(source)  # type: ignore[arg-type]
        f = open_binary(source)  # type: ignore[arg-type]
    else:
        f = source  # type: ignore[assignment]
    s = _Stream(f)
    try:
        while True:
            header = s.read(HEADER_SIZE)
            if not header:
                return
            if len(header) < HEADER_SIZE:
                stats.truncated = True
                if strict:
                    raise RecordIOError("truncated record header at end of file")
                return
            magic, usize, csize = _HEADER.unpack(header)
            if magic != MAGIC:
                if strict:
                    raise RecordIOError(f"bad magic 0x{magic & 0xFFFFFFFF:08x} (expected 0x{MAGIC:08x})")
                if not _resync(s, header, stats):
                    return
                continue
            if csize:
                comp = s.read(csize)
                if len(comp) < csize:
                    stats.truncated = True
                    if strict:
                        raise RecordIOError("truncated compressed payload at end of file")
                    return
                try:
                    data = zlib.decompress(comp, bufsize=max(int(usize), 1))
                except zlib.error as e:
                    stats.bad_records += 1
                    if strict:
                        raise RecordIOError(f"zlib error: {e}") from e
                    continue
                if len(data) != usize:
                    stats.bad_records += 1
                    if strict:
                        raise RecordIOError(f"decompressed size {len(data)} != header {usize}")
                    continue
            else:
                data = s.read(usize)
                if len(data) < usize:
                    stats.truncated = True
                    if strict:
                        raise RecordIOError("truncated uncompressed payload at end of file")
                    return
            stats.records += 1
            yield data
    finally:
        if own:
            f.close()


def read_records(path: str | Path, **kwargs) -> list[bytes]:
    """All payloads of ``path`` in memory (see :func:`iter_records`)."""
    return list(iter_records(path, **kwargs))


def count_records(path: str | Path, **kwargs) -> int:
    n = 0
    for _ in iter_records(path, **kwargs):
        n += 1
    return n


# ----------------------------------------------------------------------------- writer
def pack_record(payload: bytes, *, compress: bool = True, level: int = zlib.Z_DEFAULT_COMPRESSION) -> bytes:
    """Header + payload bytes of one record (``compress=False`` stores it raw, csize=0)."""
    payload = bytes(payload)
    if compress:
        comp = zlib.compress(payload, level)
        return _HEADER.pack(MAGIC, len(payload), len(comp)) + comp
    return _HEADER.pack(MAGIC, len(payload), 0) + payload


def write_records(path: str | Path, payloads: Iterable[bytes], *, compress: bool = True,
                  level: int = zlib.Z_DEFAULT_COMPRESSION, gzip_wrap: bool = False,
                  append: bool = False) -> int:
    """Write ``payloads`` as a recordio container; returns the number of records written.

    ``compress=True`` reproduces the ssl-unification Logger (``set_use_compression(true)``, zlib
    default level). ``gzip_wrap=True`` additionally gzips the whole container (a *real* ``.gz``);
    the reader accepts both. ``append=True`` appends to an existing container (like the Logger's
    ``fopen(..., "a")``); it cannot be combined with ``gzip_wrap``.
    """
    if gzip_wrap and append:
        raise ValueError("append=True is not supported for gzip-wrapped containers")
    mode = "ab" if append else "wb"
    n = 0
    opener = gzip.open if gzip_wrap else open
    with opener(path, mode) as f:  # type: ignore[arg-type]
        for p in payloads:
            f.write(pack_record(p, compress=compress, level=level))
            n += 1
    return n


__all__ = [
    "MAGIC", "HEADER_SIZE", "RecordIOError", "ReadStats",
    "is_gzip_wrapped", "open_binary", "iter_records", "read_records", "count_records",
    "pack_record", "write_records",
]
