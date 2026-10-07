"""Export the CAD (USD) of the SSL robot to decimated OBJ meshes for the MJCF visuals.

Sources (mm, Z-up, RobôCIn v2025 CAD):

* ``usd/wheel/robot_chasis.usd`` -> ``src/dtssl/physics/assets/ssl_chassis.obj``: all ``Mesh`` prims
  of the chassis (46 solids: shell, base plate, cover, motor mounts, electronics) except the
  ``Cylinder`` collision proxy, merged into one mesh.
* ``usd/wheel/hub.usd`` -> ``src/dtssl/physics/assets/ssl_wheel.obj``: hub ``hub_v2`` + the 20 barrel
  rollers of one omni wheel (this is the assembly instanced four times in ``usd/ssl-robot.usd``).

Frame conventions applied (see ``dtssl.physics.mjcf`` and ``docs/SPEC_DTSSL.md`` §3):

* chassis: the USD model has the dribbler (flat face) at ``-y`` and the wheel joints at
  ``atan2(y, x) = -30, 45, 135, 210 deg``; the MJCF body frame has the dribbler at ``+x`` and the wheels
  at ``60, 135, 225, 300 deg``.  Both are the same layout rotated by ``+90 deg`` about ``z``
  (``x' = -y, y' = x``).  Units mm -> m.  The origin is kept at the chassis centre and the ``z``
  origin is moved to the **wheel-axle plane** (USD ``z = 24.15 mm``, ``PhysicsRevoluteJoint`` localPos0),
  so the MJCF places the mesh at ``pos = (0, 0, wheel.r)``: the CAD wheels then touch the floor exactly
  where the physics wheels do, whatever ``wheel.r`` is in ``config/robot_geometry.json``.
* wheel: ``hub.usd`` is already expressed in the wheel frame (axle along ``+x``, rollers on the rim
  circle of radius 23.75 mm in the ``y``-``z`` plane); only the decimation is applied.  The MJCF
  orients the mesh with ``euler = (0, 0, phi_i)`` so that ``+x`` points along the outward radial
  direction ``u_r`` of wheel ``i`` (the hinge axis is ``-u_r``).

Decimation: ``fast_simplification`` (quadric edge collapse) per solid, keeping small parts intact;
the face budget is the ``--chassis-faces`` / ``--wheel-faces`` targets.  A second, lighter pair
(``ssl_chassis_lod.obj`` / ``ssl_wheel_lod.obj``, ``--lod-chassis-faces`` / ``--lod-wheel-faces``) is written for
the GUI 3D tab (12 robots drawn every frame on integrated GPUs): the chassis LOD keeps only the exterior
components of the full-resolution mesh (connected components at least ``--lod-min-diag`` mm across: shell,
base, cover; screws, headers and the electronics inside are dropped) and decimates them further; the wheel
LOD is a more aggressive decimation of the same assembly.  The exported OBJ files are single-object,
triangles only (MuJoCo reads the first shape of an OBJ), 6-decimal metres.

Requires ``usd-core`` (``pxr``), ``trimesh`` and ``fast_simplification`` (dev-only; not package
dependencies).  Run from the repo root::

    python tools/usd_to_mjcf_meshes.py [--chassis-faces 30000] [--wheel-faces 8000]
                                       [--lod-chassis-faces 10000] [--lod-wheel-faces 1200] [--lod-min-diag 60]

Writes the OBJ files plus ``meshes.json`` (provenance: sources + md5, transform, face counts, bounding
boxes and the derived constants used by ``dtssl.physics.mjcf``: top of the cover, wheel outer radius).

Kicker and dribbler (``ssl_kicker.obj``, ``ssl_dribbler.obj`` + ``_lod``): these two mechanisms are **not** in
``usd/`` (the chassis USD is the bare first floor). They are tessellated straight out of the Inventor assembly
``robot_v2025_v3.iam`` (occurrences ``kicker_assembly_5mm:1`` and ``Dribbler_Robocup2025v3:1``, already placed
by the assembly constraints) by ``tools/inventor_export_mechanisms.m`` (MATLAB + Inventor COM API, Windows),
which writes them in the same MJCF body frame as the chassis (z origin on the wheel-axle plane). This script
only *registers* them in ``meshes.json`` from the OBJ files themselves (counts, bbox, md5, header provenance and
the derived features: dribbler bar axis, kicker plunger axes), so a re-export of the chassis keeps them::

    python tools/usd_to_mjcf_meshes.py --register-mechanisms      # numpy only, no usd-core needed
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src" / "dtssl" / "physics" / "assets"
USD_CHASSIS = ROOT / "usd" / "wheel" / "robot_chasis.usd"
USD_WHEEL = ROOT / "usd" / "wheel" / "hub.usd"
USD_ROBOT = ROOT / "usd" / "ssl-robot.usd"
AXLE_Z_MM = 24.15            # wheel joint localPos0.z in ssl-robot.usd (chassis frame, mm)
CHASSIS_SKIP = ("Cylinder",)  # collision proxy in robot_chasis.usd, not a visual
R_Z90 = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])   # x' = -y, y' = x


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _usd_meshes(path: Path) -> list[tuple[str, np.ndarray, np.ndarray]]:
    """``(prim path, world points, triangle faces)`` for every Mesh prim, in stage units after the
    full xform stack (``hub.usd`` mixes metres and a 0.001 scale: ``ComputeLocalToWorldTransform``
    resolves that)."""
    from pxr import Usd, UsdGeom

    st = Usd.Stage.Open(str(path))
    out = []
    for p in st.Traverse():
        if not p.IsA(UsdGeom.Mesh):
            continue
        m = UsdGeom.Mesh(p)
        pts = np.asarray(m.GetPointsAttr().Get(), dtype=float)
        fvc = np.asarray(m.GetFaceVertexCountsAttr().Get(), dtype=int)
        fvi = np.asarray(m.GetFaceVertexIndicesAttr().Get(), dtype=int)
        faces = _triangulate(fvc, fvi)
        M = np.asarray(UsdGeom.Xformable(p).ComputeLocalToWorldTransform(Usd.TimeCode.Default())).T
        w = (M @ np.c_[pts, np.ones(len(pts))].T).T[:, :3]
        out.append((str(p.GetPath()), w, faces))
    return out


def _triangulate(counts: np.ndarray, idx: np.ndarray) -> np.ndarray:
    tris = []
    k = 0
    for n in counts:
        poly = idx[k:k + n]
        for j in range(1, n - 1):
            tris.append((poly[0], poly[j], poly[j + 1]))
        k += n
    return np.asarray(tris, dtype=np.int64).reshape(-1, 3)


def _weld(points: np.ndarray, faces: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Merge coincident vertices (CAD exports split every vertex per face, which would block the
    edge collapses of the decimation at every seam)."""
    import trimesh

    m = trimesh.Trimesh(points, faces, process=False)
    m.merge_vertices()
    return np.asarray(m.vertices, dtype=float), np.asarray(m.faces, dtype=np.int64)


def _decimate(points: np.ndarray, faces: np.ndarray, target_faces: int, agg: int = 5,
              passes: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """Quadric decimation to about ``target_faces``. CAD tessellations have many open seams, where the
    collapses are reluctant: ``agg`` (aggressiveness, 5 = quality, 8 = LOD) and a second pass when the
    first one stalls above 1.3x the target."""
    import fast_simplification as fs

    points, faces = _weld(points, faces)
    for _ in range(max(passes, 1)):
        if len(faces) <= 1.3 * target_faces:
            break
        red = 1.0 - target_faces / len(faces)
        p, f = fs.simplify(points.astype(np.float32), faces.astype(np.int32), target_reduction=float(red), agg=agg)
        points, faces = np.asarray(p, dtype=float), np.asarray(f, dtype=np.int64)
    return points, faces


def _clean(points: np.ndarray, faces: np.ndarray, min_diag: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """Drop degenerate triangles and unreferenced vertices (trimesh does the bookkeeping); with ``min_diag``
    (mm) also drop connected components smaller than that (screws, pin headers: invisible at GUI scale)."""
    import trimesh

    m = trimesh.Trimesh(points, faces, process=False)
    m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    if min_diag > 0.0 and len(m.faces):
        keep = [c for c in m.split(only_watertight=False)
                if np.linalg.norm(c.bounds[1] - c.bounds[0]) >= min_diag]
        if keep:
            m = trimesh.util.concatenate(keep)
    return np.asarray(m.vertices, dtype=float), np.asarray(m.faces, dtype=np.int64)


def _merge(parts: list[tuple[np.ndarray, np.ndarray]]) -> tuple[np.ndarray, np.ndarray]:
    pts, fcs, off = [], [], 0
    for p, f in parts:
        pts.append(p)
        fcs.append(f + off)
        off += len(p)
    return np.vstack(pts), np.vstack(fcs)


def _budget(sizes: list[int], total: int, keep_below: int = 600, floor: int = 200) -> list[int]:
    """Face budget per part: parts below ``keep_below`` faces are kept, the rest share ``total``
    proportionally to their size (large parts are decimated the most in absolute terms)."""
    small = sum(s for s in sizes if s <= keep_below)
    big = sum(s for s in sizes if s > keep_below)
    rest = max(total - small, 1)
    return [s if s <= keep_below else max(int(rest * s / big), floor) for s in sizes]


def _write_obj(path: Path, points: np.ndarray, faces: np.ndarray, header: list[str]) -> bool:
    """Write the OBJ; an existing file with the same geometry is left untouched (the header carries a
    timestamp, which would otherwise churn the git/LFS object). Returns True when written."""
    body = [f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in points]
    body += [f"f {a + 1} {b + 1} {c + 1}" for a, b, c in faces]
    if path.exists():
        old = [ln for ln in path.read_text(encoding="utf-8").splitlines() if not ln.startswith("#")]
        if old == body:
            return False
    lines = [f"# {h}" for h in header] + body
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def export_chassis(target_faces: int) -> dict:
    parts = []
    names = []
    for name, pts, faces in _usd_meshes(USD_CHASSIS):
        if name.rsplit("/", 1)[-1] in CHASSIS_SKIP:
            continue
        parts.append((pts, faces))
        names.append(name)
    sizes = [len(f) for _, f in parts]
    budgets = _budget(sizes, target_faces)
    dec = [_clean(*_decimate(p, f, b)) for (p, f), b in zip(parts, budgets, strict=True)]
    pts, faces = _merge(dec)
    # mm, USD frame -> m, MJCF frame, z origin at the wheel axle plane
    pts = (pts - np.array([0.0, 0.0, AXLE_Z_MM])) @ R_Z90.T / 1000.0
    pts, faces = _clean(pts, faces)
    lo, hi = pts.min(0), pts.max(0)
    return dict(points=pts, faces=faces, n_parts=len(parts), faces_source=int(sum(sizes)), names=names,
                bbox=dict(lo=lo.round(6).tolist(), hi=hi.round(6).tolist()))


def chassis_lod(full: dict, target_faces: int, min_diag_mm: float) -> dict:
    """Exterior-only LOD of the full-resolution chassis: connected components at least ``min_diag_mm``
    across (shell, base plate, cover) decimated (quality mode) to about ``target_faces`` in total."""
    import fast_simplification as fs
    import trimesh

    m = trimesh.Trimesh(full["points"], full["faces"], process=False)
    comps = [c for c in m.split(only_watertight=False)
             if np.linalg.norm(c.bounds[1] - c.bounds[0]) * 1000.0 >= min_diag_mm]
    total = sum(len(c.faces) for c in comps)
    red = max(0.0, 1.0 - target_faces / max(total, 1))
    out = []
    for c in comps:
        if red > 0.0 and len(c.faces) > 1500:
            p, f = fs.simplify(np.asarray(c.vertices, np.float32), np.asarray(c.faces, np.int32),
                               target_reduction=float(red), agg=5)
            out.append((np.asarray(p, dtype=float), np.asarray(f, dtype=np.int64)))
        else:
            out.append((np.asarray(c.vertices, dtype=float), np.asarray(c.faces, dtype=np.int64)))
    pts, faces = _clean(*_merge(out))
    lo, hi = pts.min(0), pts.max(0)
    return dict(points=pts, faces=faces, n_parts=len(comps), faces_source=int(len(full["faces"])),
                names=[], bbox=dict(lo=lo.round(6).tolist(), hi=hi.round(6).tolist()))


def export_wheel(target_faces: int, lod: bool = False) -> dict:
    parts = [(pts, faces) for _, pts, faces in _usd_meshes(USD_WHEEL)]
    sizes = [len(f) for _, f in parts]
    # hub ~ 1/3 of the budget, rollers share the rest
    hub_i = int(np.argmax(sizes)) if len(parts) == 21 else None
    budgets = []
    for i in range(len(sizes)):
        if hub_i is not None and i == hub_i:
            budgets.append(max(int(target_faces * 0.35), 120 if lod else 500))
        else:
            budgets.append(max(int(target_faces * 0.65 / max(len(parts) - 1, 1)), 24 if lod else 60))
    if lod:
        dec = [_clean(*_decimate(p, f, b, agg=8, passes=2)) for (p, f), b in zip(parts, budgets, strict=True)]
    else:
        dec = [_clean(*_decimate(p, f, b)) for (p, f), b in zip(parts, budgets, strict=True)]
    pts, faces = _merge(dec)               # hub.usd resolves to metres already (see _usd_meshes)
    pts, faces = _clean(pts, faces)
    lo, hi = pts.min(0), pts.max(0)
    radial = np.hypot(pts[:, 1], pts[:, 2]).max()
    return dict(points=pts, faces=faces, n_parts=len(parts), faces_source=int(sum(sizes)),
                bbox=dict(lo=lo.round(6).tolist(), hi=hi.round(6).tolist()), outer_radius=float(radial))


# --------------------------------------------------------------------------------------
# Kicker and dribbler: registered from the OBJ files written by tools/inventor_export_mechanisms.m
# --------------------------------------------------------------------------------------
MECHANISMS = ("kicker", "dribbler")
PART_LINE = re.compile(r"^# part (?P<path>.+?) \| lo (?P<lo>[-\d. ]+) \| hi (?P<hi>[-\d. ]+)$")


def _read_obj(path: Path) -> tuple[list[str], np.ndarray, int]:
    """``(header comment lines, vertices (n, 3), n_faces)`` of a single-object, triangles-only OBJ."""
    header, pts, n_faces = [], [], 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            header.append(line)
        elif line.startswith("v "):
            pts.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("f "):
            n_faces += 1
    return header, np.asarray(pts, dtype=float).reshape(-1, 3), n_faces


def _parts(header: list[str]) -> dict[str, dict]:
    """``{part path: {lo, hi}}`` (mm, MJCF body frame) from the ``# part`` lines of the exporter header."""
    out = {}
    for line in header:
        m = PART_LINE.match(line)
        if m:
            out[m["path"]] = dict(lo=[float(v) for v in m["lo"].split()], hi=[float(v) for v in m["hi"].split()])
    return out


def _box_m(box: dict) -> dict:
    return dict(lo=(np.asarray(box["lo"]) / 1000.0).round(6).tolist(), hi=(np.asarray(box["hi"]) / 1000.0).round(6).tolist())


def _axis_of(box: dict) -> dict:
    """Axis of a cylindrical part from its box (mm -> m): the long side is the axis; ``centre`` is the box
    centre (the axis passes through it), ``radius`` the mean transverse half-extent, ``span`` the extent along
    the axis. Used for the dribbler bar (along y) and the kicker plungers (along x)."""
    lo, hi = np.asarray(box["lo"]) / 1000.0, np.asarray(box["hi"]) / 1000.0
    size = hi - lo
    i = int(np.argmax(size))
    j, k = [a for a in range(3) if a != i]
    return dict(axis="xyz"[i], centre=((lo + hi) / 2.0).round(6).tolist(),
                radius=round(float((size[j] + size[k]) / 4.0), 6), length=round(float(size[i]), 6),
                span=[round(float(lo[i]), 6), round(float(hi[i]), 6)])


def mechanism_features(parts: dict[str, dict]) -> dict:
    """Derived constants (metres, MJCF body frame, z from the wheel-axle plane) read off the part boxes:
    the dribbler bar axis, the flat/chip kicker plunger axes and heads, the chip plate, the IR sensor boards."""
    def pick(pred):
        return [b for p, b in parts.items() if pred(p)]

    feats: dict = {}
    bar = pick(lambda p: "Dribblerschnecke" in p)
    if bar:
        feats["dribbler_bar"] = _axis_of(bar[0])
    for tag, sub in (("flat", "kicker_assembly_front"), ("chip", "kicker_assembly_chip")):
        irons = pick(lambda p, sub=sub: sub in p and "Kicker Eisen" in p)
        if irons:
            lo = np.min([b["lo"] for b in irons], axis=0)
            hi = np.max([b["hi"] for b in irons], axis=0)
            feats[f"kicker_{tag}_plunger"] = _axis_of(dict(lo=lo.tolist(), hi=hi.tolist()))
        head = pick(lambda p, sub=sub: sub in p and "head" in p.rsplit("/", 1)[-1])
        if head:
            feats[f"kicker_{tag}_head"] = _box_m(head[0])
    plate = pick(lambda p: "ChipKicker_v2020" in p)
    if plate:
        feats["chip_plate"] = _box_m(plate[0])
    boards = pick(lambda p: p.rsplit("/", 1)[-1] in ("Board:1", "Board_MIR:1"))
    if boards:
        feats["ir_boards"] = [_box_m(b) for b in boards]
    return feats


def register_mechanisms(meta: dict, assets: Path = ASSETS) -> dict:
    """Add or refresh the ``kicker``/``dribbler`` (+ ``_lod``) entries of ``meta`` from the OBJ files in
    ``assets`` (see the module docstring); an entry whose file is missing is dropped. Provenance = the four
    header lines of the OBJ (generator, source assembly/occurrence/tolerance, frame, occurrence transform) and
    the md5 of the OBJ itself. ``faces_source`` is the full-resolution count (the LOD is a decimation of it)."""
    for key in MECHANISMS:
        full = None
        for suffix in ("", "_lod"):
            f = assets / f"ssl_{key}{suffix}.obj"
            if not f.is_file():
                meta.pop(f"{key}{suffix}", None)
                continue
            header, pts, n_faces = _read_obj(f)
            parts = _parts(header)
            lo, hi = pts.min(0), pts.max(0)
            entry = dict(file=f.name, n_parts=len(parts), faces_source=full["faces"] if full else n_faces, faces=n_faces,
                         vertices=int(len(pts)), bbox=dict(lo=lo.round(6).tolist(), hi=hi.round(6).tolist()),
                         md5=_md5(f), source=[ln[2:] for ln in header[:4]],
                         features=full["features"] if full else mechanism_features(parts))
            if suffix == "":
                full = entry
            meta[f"{key}{suffix}"] = entry
    return meta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--chassis-faces", type=int, default=30000)
    ap.add_argument("--wheel-faces", type=int, default=8000)
    ap.add_argument("--lod-chassis-faces", type=int, default=10000)
    ap.add_argument("--lod-wheel-faces", type=int, default=1200)
    ap.add_argument("--lod-min-diag", type=float, default=60.0, help="mm; smaller chassis parts are dropped in the LOD")
    ap.add_argument("--out", type=Path, default=ASSETS)
    ap.add_argument("--register-mechanisms", action="store_true",
                    help="only refresh the kicker/dribbler entries of meshes.json from the OBJ files in --out "
                         "(written by tools/inventor_export_mechanisms.m); needs numpy only")
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    if a.register_mechanisms:
        meta_path = a.out / "meshes.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
        register_mechanisms(meta, a.out)
        meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        for k in (k for k in meta if k.startswith(MECHANISMS)):
            m = meta[k]
            print(f"{m['file']}: {m['n_parts']} parts, {m['faces']} faces, {m['vertices']} vertices, "
                  f"bbox lo {m['bbox']['lo']} hi {m['bbox']['hi']}")
        print(f"registered in {meta_path}")
        return 0
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    hdr = [f"generated by tools/usd_to_mjcf_meshes.py on {stamp}; do not edit (regenerate from usd/)",
           "units m; frame = dtssl MJCF body frame (dribbler at +x, wheels at 60/135/225/300 deg)"]
    meta = dict(
        generated=stamp, generator="tools/usd_to_mjcf_meshes.py", units="m",
        frame="dtssl MJCF body frame: dribbler at +x, wheels at 60/135/225/300 deg; USD -> MJCF = R_z(+90 deg)",
        sources={"usd/wheel/robot_chasis.usd": _md5(USD_CHASSIS), "usd/wheel/hub.usd": _md5(USD_WHEEL),
                 "usd/ssl-robot.usd": _md5(USD_ROBOT)},
        axle_z_usd_mm=AXLE_Z_MM,
    )
    full = export_chassis(a.chassis_faces)
    for key, lod, n_wh in (("", False, a.wheel_faces), ("_lod", True, a.lod_wheel_faces)):
        ch = chassis_lod(full, a.lod_chassis_faces, a.lod_min_diag) if lod else full
        wh = export_wheel(n_wh, lod=lod)
        tag = (f" (LOD for the GUI 3D tab: exterior components >= {a.lod_min_diag:g} mm of the full mesh)"
               if lod else "")
        _write_obj(a.out / f"ssl_chassis{key}.obj", ch["points"], ch["faces"],
                   hdr + [f"source usd/wheel/robot_chasis.usd (md5 {_md5(USD_CHASSIS)}), {ch['n_parts']} "
                          f"{'components' if lod else 'solids'}, {ch['faces_source']} -> {len(ch['faces'])} "
                          f"faces{tag}; z origin at the wheel-axle plane (USD z = {AXLE_Z_MM} mm); place at "
                          "pos = (0, 0, wheel.r)"])
        _write_obj(a.out / f"ssl_wheel{key}.obj", wh["points"], wh["faces"],
                   hdr + [f"source usd/wheel/hub.usd (md5 {_md5(USD_WHEEL)}), hub + {wh['n_parts'] - 1} rollers, "
                          f"{wh['faces_source']} -> {len(wh['faces'])} faces{tag}; axle along +x, centred on the "
                          "axle"])
        meta[f"chassis{key}"] = dict(
            file=f"ssl_chassis{key}.obj", n_parts=ch["n_parts"], faces_source=ch["faces_source"],
            faces=int(len(ch["faces"])), vertices=int(len(ch["points"])), bbox=ch["bbox"],
            z_top_above_axle=float(ch["bbox"]["hi"][2]), z_bottom_above_axle=float(ch["bbox"]["lo"][2]),
            skipped=list(CHASSIS_SKIP))
        meta[f"wheel{key}"] = dict(
            file=f"ssl_wheel{key}.obj", n_parts=wh["n_parts"], faces_source=wh["faces_source"],
            faces=int(len(wh["faces"])), vertices=int(len(wh["points"])), bbox=wh["bbox"],
            outer_radius=round(wh["outer_radius"], 6), axle="+x")
    register_mechanisms(meta, a.out)          # kicker/dribbler OBJ (from Inventor) stay registered
    (a.out / "meshes.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    for k in ("chassis", "wheel", "chassis_lod", "wheel_lod"):
        m = meta[k]
        print(f"{m['file']}: {m['faces_source']} -> {m['faces']} faces, {m['vertices']} vertices, "
              f"bbox lo {m['bbox']['lo']} hi {m['bbox']['hi']}")
    print(f"chassis top above axle {meta['chassis']['z_top_above_axle']:.4f} m, wheel outer radius "
          f"{meta['wheel']['outer_radius']:.4f} m (physics r = 0.029492 m)")
    print(f"written to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
