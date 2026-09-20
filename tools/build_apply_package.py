"""Build the package that applies this refactor onto the user's working copy (Windows PC).

Outputs (in ../dist-apply/):
  refactor_overlay.tar.gz   text/code files of HEAD (git archive minus binaries that already exist on the PC)
  apply_list.json           renames/deletes computed from `git diff baseline..HEAD` + tools/apply_refactor_manifest.json
  apply_refactor_fs.py      the script executed on the PC side (Linux VM with the repo mounted): moves + overlay
  apply_refactor.ps1        the git part to run on Windows (branch, add, commit)

Run from the repo root of the cloud working copy: python tools/build_apply_package.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "dist-apply"
BINARY_EXT = {".slx", ".usd", ".usda", ".usdc", ".sldd", ".parquet", ".mat", ".pkl", ".npz", ".png", ".jpg",
              ".jpeg", ".pdf", ".stp", ".mlx", ".asv", ".svg", ".pt", ".pth", ".onnx", ".obj", ".fbx", ".glb",
              ".gltf", ".tga", ".hdr", ".ov"}


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def is_binary(path: str) -> bool:
    return Path(path).suffix.lower() in BINARY_EXT


def main() -> None:
    OUT.mkdir(exist_ok=True)
    head = git("rev-parse", "--short", "HEAD").strip()
    tracked = git("ls-files", "-z").split("\0")
    tracked = [t for t in tracked if t]
    text_files = [t for t in tracked if not is_binary(t)]
    # overlay: text files only
    (OUT / "overlay_list.txt").write_text("\n".join(text_files) + "\n", encoding="utf-8")
    subprocess.check_call(
        ["bash", "-c", f"git archive --format=tar HEAD $(cat {OUT}/overlay_list.txt | tr '\\n' ' ') | gzip -9 > {OUT}/refactor_overlay.tar.gz"],
        cwd=ROOT,
    )
    # renames / deletes from baseline
    renames: list[dict] = []
    deletes: list[dict] = []
    for line in git("diff", "--name-status", "-M50%", "baseline", "HEAD").splitlines():
        parts = line.split("\t")
        code = parts[0][0]
        if code == "R":
            old, new = parts[1], parts[2]
            renames.append({"from": old, "to": new, "binary": is_binary(old), "source": "git"})
        elif code == "D":
            deletes.append({"path": parts[1], "source": "git"})
    manifest = json.loads((ROOT / "tools/apply_refactor_manifest.json").read_text(encoding="utf-8"))
    for m in manifest["moves"]:
        renames.append({"from": m["from"], "to": m["to"], "binary": True, "source": "manifest", "glob": "*" in m["from"]})
    for d in manifest["deletes"]:
        deletes.append({"path": d["path"], "source": "manifest", "glob": bool(d.get("glob")) or "*" in d["path"]})
    # whole directories that must not survive (leftovers such as __pycache__, figures, empty dirs)
    sweep_dirs = ["open-source", "python", "automation", "archive", "apresentacao", "scripts/__pycache__",
                  "phase0_replay/__pycache__", "matlab/sysid", "matlab/optimization", "matlab/train",
                  "matlab/viewer", "matlab/analytical", "matlab/ros_bridge", "scripts/.vscode", "src/envs",
                  "src/utils", "config/task", "config/train", "scripts/analyticalModel", ".pytest_cache"]
    keep_paths = ["scripts/local", "data", "models", "results", "cad", "usd", "slr", "latex", "tests/fixtures"]
    apply = {
        "head": head,
        "generated": git("log", "-1", "--format=%cI").strip(),
        "to_delete_dir": "_to_delete",
        "renames": renames,
        "deletes": deletes,
        "sweep_dirs": sweep_dirs,
        "keep_paths": keep_paths,
    }
    (OUT / "apply_list.json").write_text(json.dumps(apply, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"overlay: {len(text_files)} files; renames: {len(renames)}; deletes: {len(deletes)}; HEAD {head}")


if __name__ == "__main__":
    sys.exit(main())
