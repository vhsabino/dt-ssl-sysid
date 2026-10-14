"""Regenerate the ``*_pb2.py`` modules of ``dtssl.bridge.proto`` from the ``.proto`` sources.

The ``.proto`` files are verbatim copies of
``ssl-unification/libs/protobufs/include/protobufs/pb/proto/`` (ssl-vision +
ssl-simulation-protocol + the ``ssl_gc_common`` dependency). The generated modules are
**versioned in git** so users never need ``protoc``; run this script only when the
protocol sources change::

    pip install grpcio-tools          # any version; see the compatibility note below
    python -m dtssl.bridge.proto.build_proto            # regenerate in place
    python -m dtssl.bridge.proto.build_proto --check    # exit 1 if the tree is stale

Generation is done with the ``.proto`` files at the package root (``-I <this dir>``), which
makes protoc emit absolute imports such as ``import ssl_vision_detection_pb2 as ...``. Those
lines are rewritten to relative imports (``from . import ssl_vision_detection_pb2 as ...``)
so the modules work as a regular sub-package without touching ``sys.path``.

Compatibility note: the Python gencode emitted by protoc >= 26 embeds a runtime-version
check (``google.protobuf.runtime_version``) that refuses to load on any protobuf runtime
older than the protoc used to generate it. The committed files were produced with protoc
25.1 (grpcio-tools 1.62.3), whose gencode carries no such check and loads on every
protobuf runtime >= 4.21 (tested with 4.25 and 7.36). Regenerating with a newer protoc
raises the minimum ``protobuf`` version of the package accordingly.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROTO_FILES = sorted(p.name for p in HERE.glob("*.proto"))

_IMPORT_RE = re.compile(r"^import (\w+_pb2) as (\w+)$", re.MULTILINE)


def _rewrite_imports(text: str) -> str:
    """``import x_pb2 as y`` -> ``from . import x_pb2 as y`` (package-relative)."""
    return _IMPORT_RE.sub(r"from . import \1 as \2", text)


def generate(out_dir: Path | None = None, protoc_module: str = "grpc_tools.protoc") -> list[Path]:
    out_dir = Path(out_dir) if out_dir else HERE
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", protoc_module, f"-I{HERE}", f"--python_out={out_dir}",
           *[str(HERE / f) for f in PROTO_FILES]]
    subprocess.run(cmd, check=True)
    written: list[Path] = []
    for f in PROTO_FILES:
        py = out_dir / (f[:-len(".proto")] + "_pb2.py")
        text = py.read_text(encoding="utf-8")
        py.write_text(_rewrite_imports(text), encoding="utf-8")
        written.append(py)
    return written


def check(protoc_module: str = "grpc_tools.protoc") -> bool:
    """Regenerate into a temporary directory and compare with the committed modules."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        fresh = generate(Path(tmp), protoc_module)
        stale = []
        for py in fresh:
            committed = HERE / py.name
            if not committed.is_file() or committed.read_text(encoding="utf-8") != py.read_text(encoding="utf-8"):
                stale.append(py.name)
    if stale:
        print("stale generated modules:", ", ".join(stale))
        return False
    print("generated modules are up to date")
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="verify the committed *_pb2.py are current")
    ap.add_argument("--protoc-module", default="grpc_tools.protoc",
                    help="python module exposing protoc (default grpc_tools.protoc)")
    args = ap.parse_args(argv)
    ver = subprocess.run([sys.executable, "-m", args.protoc_module, "--version"],
                         capture_output=True, text=True, check=False)
    print("protoc:", (ver.stdout or ver.stderr).strip())
    if args.check:
        return 0 if check(args.protoc_module) else 1
    for py in generate(None, args.protoc_module):
        print("wrote", py)
    return 0


if __name__ == "__main__":
    sys.exit(main())
