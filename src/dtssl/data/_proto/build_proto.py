"""Regenerate the vendored ``*_pb2.py`` modules of ``dtssl.data._proto`` from their ``.proto`` sources.

Only the messages that the ssl-unification **log** needs and that :mod:`dtssl.bridge.proto` does
not already provide live here: ``rc_log.proto`` (the record type) and the game-controller referee
message it embeds (``ssl_gc_referee_message`` -> ``ssl_gc_game_event`` -> ``ssl_gc_geometry``).
The vision wrapper (``ssl_vision_*``) and ``ssl_gc_common`` are imported from
``dtssl.bridge.proto`` so that every ``.proto`` file is registered exactly once in the process-wide
protobuf descriptor pool (a second copy would raise "duplicate file name").

Usage (repository root; needs ``grpcio-tools`` -> ``pip install dtssl[dev]``)::

    python -m dtssl.data._proto.build_proto              # regenerate in place
    python -m dtssl.data._proto.build_proto --check      # exit 1 if the committed modules are stale
    python -m dtssl.data._proto.build_proto --sync DIR   # copy DIR/*.proto (ssl-unification) first

``DIR`` is normally ``<ssl-unification>/libs/protobufs/include/protobufs/pb/proto``.

Post-processing applied to protoc's output (the generated modules are otherwise verbatim):

* imports of sibling modules become package-relative (``from . import x_pb2 as ...``) and imports
  of modules owned by the bridge become ``from dtssl.bridge.proto import x_pb2 as ...``;
* the ``runtime_version.ValidateProtobufRuntimeVersion`` gencode/runtime pin emitted by protoc >= 26
  is removed: the modules only use the stable ``google.protobuf.internal.builder`` API
  (protobuf >= 3.20) and must not refuse to load on a runtime older than the generating protoc.
  The committed files were produced with protoc 25.1 (grpcio-tools 1.62.3), like the bridge's.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BRIDGE_PROTO_DIR = HERE.parents[1] / "bridge" / "proto"

#: proto files vendored and generated HERE, in dependency order
PROTO_FILES = [
    "ssl_gc_geometry.proto",
    "ssl_gc_game_event.proto",
    "ssl_gc_referee_message.proto",
    "rc_log.proto",
]

_IMPORT_RE = re.compile(r"^import (\w+)_pb2 as (\w+)$", re.MULTILINE)
_VERSION_IMPORT_RE = re.compile(r"^from google\.protobuf import runtime_version as _runtime_version\n", re.MULTILINE)
_VERSION_CALL_RE = re.compile(r"^_runtime_version\.ValidateProtobufRuntimeVersion\((?:.|\n)*?\)\n", re.MULTILINE)


def _rewrite_import(m: re.Match) -> str:
    stem, alias = m.group(1), m.group(2)
    if (HERE / f"{stem}.proto").is_file():
        return f"from . import {stem}_pb2 as {alias}"
    if (BRIDGE_PROTO_DIR / f"{stem}.proto").is_file():
        return f"from dtssl.bridge.proto import {stem}_pb2 as {alias}"
    raise RuntimeError(f"{stem}.proto is neither vendored here nor in {BRIDGE_PROTO_DIR}")


def postprocess(text: str) -> str:
    text = _IMPORT_RE.sub(_rewrite_import, text)
    text = _VERSION_IMPORT_RE.sub("", text)
    text = _VERSION_CALL_RE.sub("", text)
    return text


def sync_protos(src_dir: Path) -> None:
    for name in PROTO_FILES:
        src = src_dir / name
        if not src.is_file():
            raise FileNotFoundError(src)
        shutil.copyfile(src, HERE / name)
        print(f"[build_proto] synced {name}")


def generate(out_dir: Path | None = None, protoc_module: str = "grpc_tools.protoc") -> list[Path]:
    out_dir = Path(out_dir) if out_dir else HERE
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", protoc_module, f"-I{HERE}", f"-I{BRIDGE_PROTO_DIR}",
           f"--python_out={out_dir}", *PROTO_FILES]
    subprocess.run(cmd, cwd=HERE, check=True)
    written = []
    for name in PROTO_FILES:
        py = out_dir / (name[: -len(".proto")] + "_pb2.py")
        py.write_text(postprocess(py.read_text(encoding="utf-8")), encoding="utf-8")
        written.append(py)
    return written


def check(protoc_module: str = "grpc_tools.protoc") -> bool:
    """Regenerate into a temporary directory and compare with the committed modules."""
    with tempfile.TemporaryDirectory() as tmp:
        fresh = generate(Path(tmp), protoc_module)
        stale = [py.name for py in fresh
                 if not (HERE / py.name).is_file()
                 or (HERE / py.name).read_text(encoding="utf-8") != py.read_text(encoding="utf-8")]
    if stale:
        print("stale generated modules:", ", ".join(stale))
        return False
    print("generated modules are up to date")
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--sync", metavar="DIR", default=None,
                    help="copy the .proto sources from DIR (ssl-unification proto directory) before generating")
    ap.add_argument("--check", action="store_true", help="verify the committed *_pb2.py are current")
    ap.add_argument("--protoc-module", default="grpc_tools.protoc",
                    help="python module exposing protoc (default grpc_tools.protoc)")
    args = ap.parse_args(argv)
    try:
        ver = subprocess.run([sys.executable, "-m", args.protoc_module, "--version"],
                             capture_output=True, text=True, check=False)
        print("protoc:", (ver.stdout or ver.stderr).strip())
    except OSError as e:  # pragma: no cover
        raise SystemExit(f"grpcio-tools is required (pip install grpcio-tools): {e}") from e
    if args.sync:
        sync_protos(Path(args.sync).expanduser().resolve())
    if args.check:
        return 0 if check(args.protoc_module) else 1
    for py in generate(None, args.protoc_module):
        print("wrote", py)
    return 0


if __name__ == "__main__":
    sys.exit(main())
