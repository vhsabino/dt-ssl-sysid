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
the face budget is the ``--chassis-faces`` / ``--wheel-faces`` targets.  The exported OBJ files are
single-object, triangles only (MuJoCo reads the first shape of an OBJ), 6-decimal metres.

Requires ``usd-core`` (``pxr``), ``trimesh`` and ``fast_simplification`` (dev-only; not package
dependencies).  Run from the repo root::

    python tools/usd_to_mjcf_meshes.py [--chassis-faces 30000] [--wheel-faces 8000]

Writes the OBJ files plus ``meshes.json`` (provenance: sources + md5, transform, face counts, bounding
boxes and the derived constants used by ``dtssl.physics.mjcf``: top of the cover, wheel outer radius).
"""
from __future__ import annotations

import argparse
import hashlib
import json
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


def _decimate(points: np.ndarray, faces: np.ndarray, target_faces: int) -> tuple[np.ndarray, np.ndarray]:
    import fast_simplification as fs

    points, faces = _weld(points, faces)
    if len(faces) <= target_faces:
        return points, faces
    red = 1.0 - target_faces / len(faces)
    p, f = fs.simplify(points.astype(np.float32), faces.astype(np.int32), target_reduction=float(red), agg=5)
    return np.asarray(p, dtype=float), np.asarray(f, dtype=np.int64)


def _clean(points: np.ndarray, faces: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Drop degenerate triangles and unreferenced vertices (trimesh does the bookkeeping)."""
    import trimesh

    m = trimesh.Trimesh(points, faces, process=False)
    m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    return np.asarray(m.vertices, dtype=float), np.asarray(m.faces, dtype=np.int64)


def _merge(parts: list[tuple[np.ndarray, np.ndarray]]) -> tuple[np.ndarray, np.ndarray]:
    pts, fcs, off = [], [], 0
    for p, f in parts:
        pts.append(p)
        fcs.append(f + off)
        off += len(p)
    return np.vstack(pts), np.vstack(fcs)


def _budget(sizes: list[int], total: int, keep_below: int = 600) -> list[int]:
    """Face budget per part: parts below ``keep_below`` faces are kept, the rest share ``total``
    proportionally to their size (large parts are decimated the most in absolute terms)."""
    small = sum(s for s in sizes if s <= keep_below)
    big = sum(s for s in sizes if s > keep_below)
    rest = max(total - small, 1)
    return [s if s <= keep_below else max(int(rest * s / big), 200) for s in sizes]


def _write_obj(path: Path, points: np.ndarray, faces: np.ndarray, header: list[str]) -> None:
    lines = [f"# {h}" for h in header]
    lines += [f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in points]
    lines += [f"f {a + 1} {b + 1} {c + 1}" for a, b, c in faces]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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


def export_wheel(target_faces: int) -> dict:
    parts = [(pts, faces) for _, pts, faces in _usd_meshes(USD_WHEEL)]
    sizes = [len(f) for _, f in parts]
    # hub ~ 1/3 of the budget, rollers share the rest
    hub_i = int(np.argmax(sizes)) if len(parts) == 21 else None
    budgets = []
    for i in range(len(sizes)):
        if hub_i is not None and i == hub_i:
            budgets.append(max(int(target_faces * 0.35), 500))
        else:
            budgets.append(max(int(target_faces * 0.65 / max(len(parts) - 1, 1)), 60))
    dec = [_clean(*_decimate(p, f, b)) for (p, f), b in zip(parts, budgets, strict=True)]
    pts, faces = _merge(dec)               # hub.usd resolves to metres already (see _usd_meshes)
    pts, faces = _clean(pts, faces)
    lo, hi = pts.min(0), pts.max(0)
    radial = np.hypot(pts[:, 1], pts[:, 2]).max()
    return dict(points=pts, faces=faces, n_parts=len(parts), faces_source=int(sum(sizes)),
                bbox=dict(lo=lo.round(6).tolist(), hi=hi.round(6).tolist()), outer_radius=float(radial))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--chassis-faces", type=int, default=30000)
    ap.add_argument("--wheel-faces", type=int, default=8000)
    ap.add_argument("--out", type=Path, default=ASSETS)
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ch = export_chassis(a.chassis_faces)
    wh = export_wheel(a.wheel_faces)
    hdr = [f"generated by tools/usd_to_mjcf_meshes.py on {stamp}; do not edit (regenerate from usd/)",
           "units m; frame = dtssl MJCF body frame (dribbler at +x, wheels at 60/135/225/300 deg)"]
    _write_obj(a.out / "ssl_chassis.obj", ch["points"], ch["faces"],
               hdr + [f"source usd/wheel/robot_chasis.usd (md5 {_md5(USD_CHASSIS)}), {ch['n_parts']} solids, "
                      f"{ch['faces_source']} -> {len(ch['faces'])} faces; z origin at the wheel-axle plane "
                      f"(USD z = {AXLE_Z_MM} mm); place at pos = (0, 0, wheel.r)"])
    _write_obj(a.out / "ssl_wheel.obj", wh["points"], wh["faces"],
               hdr + [f"source usd/wheel/hub.usd (md5 {_md5(USD_WHEEL)}), hub + {wh['n_parts'] - 1} rollers, "
                      f"{wh['faces_source']} -> {len(wh['faces'])} faces; axle along +x, centred on the axle"])
    meta = dict(
        generated=stamp, generator="tools/usd_to_mjcf_meshes.py", units="m",
        frame="dtssl MJCF body frame: dribbler at +x, wheels at 60/135/225/300 deg; USD -> MJCF = R_z(+90 deg)",
        sources={"usd/wheel/robot_chasis.usd": _md5(USD_CHASSIS), "usd/wheel/hub.usd": _md5(USD_WHEEL),
                 "usd/ssl-robot.usd": _md5(USD_ROBOT)},
        axle_z_usd_mm=AXLE_Z_MM,
        chassis=dict(file="ssl_chassis.obj", n_parts=ch["n_parts"], faces_source=ch["faces_source"],
                     faces=int(len(ch["faces"])), vertices=int(len(ch["points"])), bbox=ch["bbox"],
                     z_top_above_axle=float(ch["bbox"]["hi"][2]), z_bottom_above_axle=float(ch["bbox"]["lo"][2]),
                     skipped=list(CHASSIS_SKIP)),
        wheel=dict(file="ssl_wheel.obj", n_parts=wh["n_parts"], faces_source=wh["faces_source"],
                   faces=int(len(wh["faces"])), vertices=int(len(wh["points"])), bbox=wh["bbox"],
                   outer_radius=round(wh["outer_radius"], 6), axle="+x"),
    )
    (a.out / "meshes.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    for k in ("chassis", "wheel"):
        m = meta[k]
        print(f"{m['file']}: {m['faces_source']} -> {m['faces']} faces, {m['vertices']} vertices, "
              f"bbox lo {m['bbox']['lo']} hi {m['bbox']['hi']}")
    print(f"chassis top above axle {meta['chassis']['z_top_above_axle']:.4f} m, wheel outer radius "
          f"{meta['wheel']['outer_radius']:.4f} m (physics r = 0.029492 m)")
    print(f"written to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
