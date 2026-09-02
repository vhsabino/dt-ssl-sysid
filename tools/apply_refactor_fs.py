#!/usr/bin/env python3
"""Apply the dtssl refactor to the user's working copy — FILE-SYSTEM part (no git).

Runs inside the Cowork Linux VM where the repo is mounted read-write but `rm` is not
permitted: every removal is a MOVE into `<repo>/_to_delete/<original path>` (gitignored),
so nothing is lost and `git add -A` on Windows records the deletions/renames.

Steps:
  1. binary renames (files that are not in the overlay: .slx/.usd/.mlx/... ) -> mv old -> new
  2. text renames -> mv old -> _to_delete/old   (the overlay brings the new path)
  3. deletes (git + manifest, with globs) -> mv -> _to_delete/
  4. extract the overlay (text/code files of the refactored tree) over the repo
  5. sweep leftover directories (open-source/, python/, automation/, archive/, ...) -> _to_delete/
  6. write _to_delete/APPLY_LOG.txt

Usage: python3 apply_refactor_fs.py <repo_root> <apply_list.json> <refactor_overlay.tar.gz> [--dry-run]
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import sys
import tarfile
import time
from pathlib import Path

LOG: list[str] = []


def log(msg: str) -> None:
    LOG.append(msg)
    print(msg)


def safe_move(root: Path, src: Path, dst: Path, dry: bool) -> bool:
    if not src.exists() and not src.is_symlink():
        return False
    if dst.exists():
        if src.is_dir() and dst.is_dir():
            # merge directory contents into the existing destination
            for child in sorted(src.iterdir()):
                safe_move(root, child, dst / child.name, dry)
            if not dry:
                try:
                    src.rmdir()
                except OSError:
                    pass
            log(f"merged {src.relative_to(root)} -> {dst.relative_to(root)}")
            return True
        # destination file exists: keep the destination (already applied), park the source
        park = root / "_to_delete" / "conflicts" / src.relative_to(root)
        log(f"CONFLICT keep {dst.relative_to(root)}, park {src.relative_to(root)} -> {park.relative_to(root)}")
        dst = park
    log(f"mv {src.relative_to(root)} -> {dst.relative_to(root)}")
    if not dry:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
    return True


def to_trash(root: Path, rel: str, dry: bool) -> bool:
    src = root / rel
    dst = root / "_to_delete" / rel
    return safe_move(root, src, dst, dry)


def expand(root: Path, pattern: str) -> list[str]:
    pattern = pattern.rstrip("/")
    if "*" in pattern:
        hits = glob.glob(str(root / pattern), recursive=True)
        rels = sorted(os.path.relpath(h, root) for h in hits)
        return [r for r in rels if not r.startswith(("_to_delete/", ".git/"))]
    return [pattern]


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    root = Path(sys.argv[1]).resolve()
    plan = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    overlay = Path(sys.argv[3])
    dry = "--dry-run" in sys.argv
    trash = root / plan.get("to_delete_dir", "_to_delete")
    if not dry:
        trash.mkdir(exist_ok=True)
    keep = [root / k for k in plan.get("keep_paths", [])]

    def protected(rel: str) -> bool:
        p = (root / rel).resolve()
        return any(p == k or k in p.parents for k in keep)

    log(f"== apply dtssl refactor {plan.get('head')} on {root} (dry={dry}) ==")
    # 1-2 renames
    for r in plan["renames"]:
        srcs = expand(root, r["from"]) if r.get("glob") else [r["from"]]
        for s in srcs:
            if r.get("glob") and s.endswith((".asv", ".autosave")):
                continue  # autosaves are deleted, never moved into legacy/
            if protected(s):
                log(f"SKIP protected {s}")
                continue
            src = root / s
            if r.get("binary"):
                dst_rel = r["to"]
                if r.get("glob") or dst_rel.endswith("/"):
                    dst_rel = str(Path(r["to"]) / Path(s).name)
                safe_move(root, src, root / dst_rel, dry)
            else:
                to_trash(root, s, dry)
    # 3 deletes
    for d in plan["deletes"]:
        for s in expand(root, d["path"]):
            if protected(s):
                log(f"SKIP protected {s}")
                continue
            to_trash(root, s, dry)
    # 4 overlay
    log(f"extract overlay {overlay.name}")
    if not dry:
        with tarfile.open(overlay, "r:gz") as tf:
            members = [m for m in tf.getmembers() if not m.name.startswith("/") and ".." not in m.name]
            tf.extractall(root, members=members)
        log(f"  {len(members)} entries extracted")
    # 5 sweep leftovers
    for d in plan.get("sweep_dirs", []):
        p = root / d
        if p.exists():
            # only sweep if nothing tracked-new lives there (phase0_replay shim is new: skip its files)
            to_trash(root, d, dry)
    # remove now-empty directories (best effort)
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        rel = os.path.relpath(dirpath, root)
        if rel.startswith((".git", "_to_delete", "data", "scripts/local", "slr", "cad", "usd", "models", "tests")) or rel == ".":
            continue
        if not dirnames and not filenames:
            try:
                if not dry:
                    os.rmdir(dirpath)
                log(f"rmdir {rel}")
            except OSError:
                pass
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    if not dry:
        (trash / "APPLY_LOG.txt").write_text(f"# dtssl refactor apply log {stamp}\n" + "\n".join(LOG) + "\n", encoding="utf-8")
    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
