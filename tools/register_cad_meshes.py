"""Register the CAD meshes written by ``tools/inventor_export_cad.m`` in ``src/dtssl/physics/assets/meshes.json``.

The four meshes (``ssl_chassis``, ``ssl_wheel``, ``ssl_kicker``, ``ssl_dribbler`` + their ``_lod`` twins) are
tessellated out of the Inventor assembly ``robot_v2025_v3.iam`` by the MATLAB exporter, which writes OBJ files with one
``g`` group per part, one ``usemtl`` per colour (materials in ``ssl_<tag>.mtl``) and a comment header that records the
provenance and one ``# part`` line per part. This script only *reads* those files (numpy, no CAD package needed) and
derives what ``dtssl.physics.mjcf`` and the GUI need:

* counts, bounding boxes, md5 and the header provenance of every OBJ;
* the material table of every mesh (``{m_rrggbb: {rgb, name}}``, RGB in 0-1);
* chassis: ``z_top_above_axle`` (bbox), ``z_cover_above_axle`` (highest large horizontal plane = the cover top) and
  ``z_id_plate_above_axle`` (the decal plane of the SSL id pattern in the CAD, where the dtssl id plate is drawn);
* wheel: ``outer_radius`` and the CAD wheel angle/centre (header);
* kicker/dribbler ``features``: dribbler bar axis, kicker plunger axes and heads, IR boards, the chip plate as an
  oriented box fitted to its vertices (the ramp the ball rests on) and the mouth walls (side plates, top plate):
  these drive the physical dribbler of ``dtssl.physics.mjcf`` (``dribbler="bar"``).

Run from the repo root after the MATLAB export::

    python tools/register_cad_meshes.py            # rewrites src/dtssl/physics/assets/meshes.json
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
AXLE_Z_MM = 24.15            # wheel-axle plane in the Inventor frame (mm), z origin of the meshes
TAGS = ("chassis", "wheel", "kicker", "dribbler")
PART_LINE = re.compile(r"^# part (?P<path>.+?) \| lo (?P<lo>[-\d. ]+) \| hi (?P<hi>[-\d. ]+)"
                       r"(?: \| mtl (?P<mtl>\S+) \| (?P<app>.*))?$")
ID_PLATE_LINE = re.compile(r"^# id plate z .*?: (?P<z>[-\d.]+)$")
AXLE_LINE = re.compile(r"^# wheel axle: CAD angle (?P<ang>[-\d.]+) deg.*?centre \(MJCF frame, mm\) \[(?P<c>[-\d. ]+)\]"
                       r", outer radius (?P<r>[-\d.]+) mm")


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def read_obj(path: Path) -> dict:
    """Parse the exporter OBJ: ``header`` (comment lines), ``mtllib``, ``vertices`` (n, 3), ``faces`` (m, 3) and
    ``groups`` = list of ``(name, material, face_start, face_end)`` in file order."""
    header, pts, faces, groups, mtllib = [], [], [], [], None
    cur_name, cur_mtl, start = None, None, 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            header.append(line)
        elif line.startswith("v "):
            pts.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("f "):
            faces.append([int(tok.split("/")[0]) - 1 for tok in line.split()[1:4]])
        elif line.startswith("g "):
            if cur_name is not None and len(faces) > start:
                groups.append((cur_name, cur_mtl, start, len(faces)))
            cur_name, start = line[2:].strip(), len(faces)
        elif line.startswith("usemtl "):
            cur_mtl = line[7:].strip()
        elif line.startswith("mtllib "):
            mtllib = line[7:].strip()
    if cur_name is not None and len(faces) > start:
        groups.append((cur_name, cur_mtl, start, len(faces)))
    return dict(header=header, mtllib=mtllib, vertices=np.asarray(pts, dtype=float).reshape(-1, 3),
                faces=np.asarray(faces, dtype=np.int64).reshape(-1, 3), groups=groups)


def read_mtl(path: Path) -> dict[str, dict]:
    """``{material: {rgb: [r, g, b] (0-1), name: appearance}}`` from the exporter ``.mtl``."""
    out: dict[str, dict] = {}
    cur = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("newmtl "):
            cur = line[7:].strip()
            out[cur] = dict(rgb=[0.5, 0.5, 0.5], name="")
        elif cur and line.startswith("# "):
            out[cur]["name"] = line[2:].strip()
        elif cur and line.startswith("Kd "):
            out[cur]["rgb"] = [round(float(v), 4) for v in line.split()[1:4]]
    return out


def parts_of(obj: dict) -> dict[str, dict]:
    """``{part path: {lo, hi (mm), mtl, app, faces (slice)}}`` joining the ``# part`` header lines with the ``g``
    groups (same order; the group name is the path with whitespace replaced by ``_``)."""
    lines = [m for m in (PART_LINE.match(ln) for ln in obj["header"]) if m]
    out: dict[str, dict] = {}
    for i, m in enumerate(lines):
        d = dict(lo=[float(v) for v in m["lo"].split()], hi=[float(v) for v in m["hi"].split()],
                 mtl=m["mtl"], app=m["app"])
        if i < len(obj["groups"]):
            name, mtl, a, b = obj["groups"][i]
            if name == re.sub(r"\s+", "_", m["path"]):
                d["faces"] = (a, b)
                if d["mtl"] is None:
                    d["mtl"] = mtl
        out[m["path"]] = d
    return out


def part_vertices(obj: dict, part: dict) -> np.ndarray:
    a, b = part["faces"]
    idx = np.unique(obj["faces"][a:b])
    return obj["vertices"][idx]


# --------------------------------------------------------------------------------------
# Derived geometry
# --------------------------------------------------------------------------------------
def _box_m(box: dict) -> dict:
    return dict(lo=(np.asarray(box["lo"]) / 1000.0).round(6).tolist(), hi=(np.asarray(box["hi"]) / 1000.0).round(6).tolist())


def _axis_of(box: dict) -> dict:
    """Axis of a cylindrical part from its box (mm -> m): the long side is the axis; ``centre`` is the box centre,
    ``radius`` the mean transverse half-extent, ``span`` the extent along the axis."""
    lo, hi = np.asarray(box["lo"]) / 1000.0, np.asarray(box["hi"]) / 1000.0
    size = hi - lo
    i = int(np.argmax(size))
    j, k = [a for a in range(3) if a != i]
    return dict(axis="xyz"[i], centre=((lo + hi) / 2.0).round(6).tolist(),
                radius=round(float((size[j] + size[k]) / 4.0), 6), length=round(float(size[i]), 6),
                span=[round(float(lo[i]), 6), round(float(hi[i]), 6)])


def oriented_box(pts: np.ndarray) -> dict:
    """Oriented bounding box of a point cloud (PCA axes, right-handed, first axis = longest): ``centre``,
    ``axes`` (rows = unit vectors in the mesh frame), ``half`` (half-extents), metres."""
    c = pts.mean(0)
    _, _, vt = np.linalg.svd(pts - c, full_matrices=False)
    axes = vt.copy()
    if np.linalg.det(axes) < 0:
        axes[2] *= -1.0
    proj = (pts - c) @ axes.T
    lo, hi = proj.min(0), proj.max(0)
    centre = c + ((lo + hi) / 2.0) @ axes
    return dict(centre=centre.round(6).tolist(), axes=axes.round(6).tolist(), half=((hi - lo) / 2.0).round(6).tolist())


def cover_plane(obj: dict, bin_mm: float = 0.5, min_area_cm2: float = 50.0) -> float | None:
    """Height (m, above the axle plane) of the highest large up-facing horizontal plane of the chassis: the cover
    top. Up-facing faces (n_z > 0.95) are binned by centroid height; the highest bin whose area (with its lower
    neighbour) exceeds ``min_area_cm2`` wins and the area-weighted height of those faces is returned."""
    v, f = obj["vertices"], obj["faces"]
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    n = np.cross(b - a, c - a)
    area2 = np.linalg.norm(n, axis=1)
    ok = area2 > 1e-14
    nz = np.zeros(len(f))
    nz[ok] = n[ok, 2] / area2[ok]
    up = nz > 0.95
    if not up.any():
        return None
    zc = (a[:, 2] + b[:, 2] + c[:, 2]) / 3.0
    area = area2 / 2.0
    h = bin_mm / 1000.0
    bins = np.floor(zc[up] / h).astype(int)
    tot = {}
    for bi, ar in zip(bins, area[up], strict=True):
        tot[bi] = tot.get(bi, 0.0) + ar
    for bi in sorted(tot, reverse=True):
        if (tot[bi] + tot.get(bi - 1, 0.0)) * 1e4 >= min_area_cm2:
            sel = up & (zc >= (bi - 1) * h) & (zc < (bi + 1) * h)
            return float(np.sum(zc[sel] * area[sel]) / np.sum(area[sel]))
    return None


def mechanism_features(obj: dict, parts: dict[str, dict]) -> dict:
    """Derived constants (metres, MJCF body frame, z from the wheel-axle plane): the dribbler bar axis, the
    flat/chip kicker plunger axes and heads, the IR boards, the chip plate (box + oriented box fitted to its
    vertices) and the mouth walls (inner faces of the side plates / chip holders, underside of the top plate,
    rear of the chip plate)."""
    def pick(pred):
        return [(p, b) for p, b in parts.items() if pred(p)]

    feats: dict = {}
    bar = pick(lambda p: "Dribblerschnecke" in p)
    if bar:
        feats["dribbler_bar"] = _axis_of(bar[0][1])
    for tag, sub in (("flat", "kicker_assembly_front"), ("chip", "kicker_assembly_chip")):
        irons = [b for _, b in pick(lambda p, sub=sub: sub in p and "Kicker Eisen" in p)]
        if irons:
            lo = np.min([b["lo"] for b in irons], axis=0)
            hi = np.max([b["hi"] for b in irons], axis=0)
            feats[f"kicker_{tag}_plunger"] = _axis_of(dict(lo=lo.tolist(), hi=hi.tolist()))
        head = pick(lambda p, sub=sub: sub in p and "head" in p.rsplit("/", 1)[-1])
        if head:
            feats[f"kicker_{tag}_head"] = _box_m(head[0][1])
    plate = pick(lambda p: "ChipKicker_v2020" in p)
    if plate:
        feats["chip_plate"] = _box_m(plate[0][1])
        if "faces" in plate[0][1]:
            feats["chip_plate"]["obb"] = oriented_box(part_vertices(obj, plate[0][1]))
    boards = [b for _, b in pick(lambda p: p.rsplit("/", 1)[-1] in ("Board:1", "Board_MIR:1"))]
    if boards:
        feats["ir_boards"] = [_box_m(b) for b in boards]
    sides = [b for _, b in pick(lambda p: re.search(r"/(PartA_3D|PartB_3D|ChipHolderV17)", p) is not None)]
    top = [b for _, b in pick(lambda p: p.rsplit("/", 1)[-1].startswith("PartC"))]
    if sides and plate:
        right = [b["hi"][1] for b in sides if b["hi"][1] < 0.0]      # walls on the -y side: inner face = max y
        left = [b["lo"][1] for b in sides if b["lo"][1] > 0.0]       # walls on the +y side: inner face = min y
        mouth = dict(y_min=round(max(right) / 1000.0, 6) if right else None,
                     y_max=round(min(left) / 1000.0, 6) if left else None,
                     x_back=round(plate[0][1]["lo"][0] / 1000.0, 6),
                     x_front=round(max(b["hi"][0] for b in sides) / 1000.0, 6),
                     z_top=round(min(b["lo"][2] for b in top) / 1000.0, 6) if top else None,
                     z_bottom=round(min(b["lo"][2] for b in sides) / 1000.0, 6))
        feats["mouth"] = mouth
    return feats


# --------------------------------------------------------------------------------------
# Registration
# --------------------------------------------------------------------------------------
def register(assets: Path = ASSETS) -> dict:
    """Build the whole ``meshes.json`` dict from the OBJ/MTL files in ``assets``."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    meta: dict = dict(
        generated=stamp, generator="tools/register_cad_meshes.py (meshes by tools/inventor_export_cad.m)", units="m",
        frame="dtssl MJCF body frame: dribbler at +x, wheels at 60/135/225/300 deg; Inventor -> MJCF = R_z(+90 deg), "
              "z origin on the wheel-axle plane (Inventor z = 24.15 mm); wheel mesh in its own axle frame (+x outward)",
        axle_z_inventor_mm=AXLE_Z_MM,
    )
    sources: dict[str, str] = {}
    for tag in TAGS:
        full: dict | None = None
        for suffix in ("", "_lod"):
            f = assets / f"ssl_{tag}{suffix}.obj"
            if not f.is_file():
                continue
            obj = read_obj(f)
            parts = parts_of(obj)
            pts = obj["vertices"]
            lo, hi = pts.min(0), pts.max(0)
            src = [ln[2:] for ln in obj["header"] if not ln.startswith(("# part ", "# materials", "# skipped"))]
            m_src = re.search(r"^source (?P<file>.+?), target", src[1]) if len(src) > 1 else None
            if m_src:
                sources[m_src["file"]] = "tools/inventor_export_cad.m (Inventor COM API, CalculateFacets)"
            mtl = read_mtl(assets / obj["mtllib"]) if obj["mtllib"] and (assets / obj["mtllib"]).is_file() else {}
            used = {g[1] for g in obj["groups"]}
            n_skipped = 0
            for ln in obj["header"]:
                m_sk = re.match(r"^# skipped \((\d+)\)", ln)
                if m_sk:
                    n_skipped = int(m_sk[1])
            entry: dict = dict(
                file=f.name, mtl=obj["mtllib"], n_parts=len(parts), n_skipped=n_skipped,
                faces_source=full["faces"] if full else int(len(obj["faces"])), faces=int(len(obj["faces"])),
                vertices=int(len(pts)), bbox=dict(lo=lo.round(6).tolist(), hi=hi.round(6).tolist()), md5=_md5(f),
                source=src, materials={k: v for k, v in mtl.items() if k in used},
            )
            if tag == "chassis":
                entry["z_top_above_axle"] = float(hi[2])
                entry["z_bottom_above_axle"] = float(lo[2])
                if full:
                    entry["z_cover_above_axle"] = full["z_cover_above_axle"]
                    entry["z_id_plate_above_axle"] = full["z_id_plate_above_axle"]
                else:
                    zc = cover_plane(obj)
                    entry["z_cover_above_axle"] = round(zc, 6) if zc is not None else float(hi[2])
                    zid = [float(m["z"]) for m in (ID_PLATE_LINE.match(ln) for ln in obj["header"]) if m]
                    entry["z_id_plate_above_axle"] = round(zid[0] / 1000.0, 6) if zid else entry["z_cover_above_axle"]
            elif tag == "wheel":
                entry["outer_radius"] = round(float(np.hypot(pts[:, 1], pts[:, 2]).max()), 6)
                entry["axle"] = "+x"
                for ln in obj["header"]:
                    m_ax = AXLE_LINE.match(ln)
                    if m_ax:
                        entry["cad_angle_deg"] = float(m_ax["ang"])
                        entry["cad_centre"] = [round(float(v) / 1000.0, 6) for v in m_ax["c"].split()]
            else:
                entry["features"] = full["features"] if full else mechanism_features(obj, parts)
            if suffix == "":
                full = entry
            meta[f"{tag}{suffix}"] = entry
    meta["sources"] = sources
    return meta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--assets", type=Path, default=ASSETS, help="folder with the OBJ/MTL files (and meshes.json)")
    a = ap.parse_args(argv)
    meta = register(a.assets)
    out = a.assets / "meshes.json"
    out.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    for k in [t + s for t in TAGS for s in ("", "_lod")]:
        if k in meta:
            m = meta[k]
            print(f"{m['file']}: {m['n_parts']} parts, {m['faces']} faces, {m['vertices']} vertices, "
                  f"{len(m['materials'])} colours, bbox lo {m['bbox']['lo']} hi {m['bbox']['hi']}")
    if "chassis" in meta:
        c = meta["chassis"]
        print(f"chassis: top {c['z_top_above_axle']:.4f} m, cover {c['z_cover_above_axle']:.4f} m, id plate "
              f"{c['z_id_plate_above_axle']:.4f} m above the axle")
    if "wheel" in meta:
        print(f"wheel outer radius {meta['wheel']['outer_radius']:.4f} m (physics r = 0.029492 m)")
    if "dribbler" in meta:
        print("dribbler features: " + ", ".join(meta["dribbler"]["features"]))
    print(f"written {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
