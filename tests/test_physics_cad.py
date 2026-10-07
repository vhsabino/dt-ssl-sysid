"""CAD meshes as visual-only geoms (``visual='cad'``): assets, colours, XML, physics invariance, CLI."""
from __future__ import annotations

import hashlib
import json
import math
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from dtssl.physics import mjcf
from dtssl.sim.entities import BallState, RobotCmd, RobotSpawn, Scene

OBJ_FILES = tuple(f for f in mjcf.CAD_FILES if f.endswith(".obj"))
MTL_FILES = tuple(f for f in mjcf.CAD_FILES if f.endswith(".mtl"))
LOD_KEYS = tuple(f"{k}_lod" for k in mjcf.CAD_KEYS)
N_SUBMESH = {"chassis": 13, "wheel": 5, "kicker": 3, "dribbler": 9}        # colours (+ the bar) per CAD mesh


def _obj_stats(path):
    nv = nf = 0
    pts = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("v "):
            nv += 1
            pts.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("f "):
            nf += 1
            assert len(line.split()) == 4, "triangles only"
    return nv, nf, np.asarray(pts)


# ---------------------------------------------------------------- assets (no mujoco)
def test_assets_present_and_meta_consistent():
    meta = mjcf.cad_meta()
    assert "inventor_export_cad" in meta["generator"] and "register_cad_meshes" in meta["generator"]
    for key in mjcf.CAD_KEYS + LOD_KEYS:
        p = mjcf.ASSET_DIR / meta[key]["file"]
        assert p.is_file(), p
        nv, nf, _ = _obj_stats(p)
        assert nv == meta[key]["vertices"] and nf == meta[key]["faces"] and nf <= meta[key]["faces_source"]
        assert hashlib.md5(p.read_bytes()).hexdigest() == meta[key]["md5"], f"{p.name} changed: re-register"
        assert (mjcf.ASSET_DIR / meta[key]["mtl"]).is_file()
        src = "\n".join(meta[key]["source"])
        assert "robot_v2025_v3.iam" in src and f"target {key.removesuffix('_lod')}" in src
        used = {line.split()[1] for line in p.read_text(encoding="utf-8").splitlines() if line.startswith("usemtl ")}
        assert used <= set(meta[key]["materials"])                   # every colour of the OBJ is in the MTL
        for m in meta[key]["materials"].values():
            assert len(m["rgb"]) == 3 and all(0.0 <= c <= 1.0 for c in m["rgb"]) and m["name"]
    for key in mjcf.CAD_KEYS:                                          # LOD: same parts, decimated
        assert meta[f"{key}_lod"]["n_parts"] == meta[key]["n_parts"]
        assert meta[f"{key}_lod"]["faces"] < 0.4 * meta[key]["faces"]
        assert len(meta[key]["materials"]) == N_SUBMESH[key]        # (the bar has a colour of its own)
    assert set(mjcf.mesh_assets()) == set(OBJ_FILES) | set(MTL_FILES)
    for f in OBJ_FILES + MTL_FILES:
        assert mjcf.mesh_assets()[f] == (mjcf.ASSET_DIR / f).read_bytes()
    assert all(k.endswith("robot_v2025_v3.iam") for k in meta["sources"])


def test_chassis_mesh_is_in_the_body_frame():
    """Dribbler (flat face) at +x, round back at -x, symmetric in y, z origin on the wheel-axle plane; the cover
    and the id-pattern decal plane are recorded below the bbox top (features on the cover)."""
    meta = mjcf.cad_meta()
    _, _, pts = _obj_stats(mjcf.ASSET_DIR / meta["chassis"]["file"])
    lo, hi = pts.min(0), pts.max(0)
    assert 0.070 < hi[0] < 0.080 and lo[0] < -0.085          # flat face ~76 mm ahead, round back at -88 mm
    assert abs(hi[1] + lo[1]) < 0.002 and 0.085 < hi[1] < 0.090
    assert -0.030 < lo[2] < -0.020                           # base plate just below the axle plane
    c = meta["chassis"]
    assert hi[2] == pytest.approx(c["z_top_above_axle"], abs=1e-6)
    assert lo[2] == pytest.approx(c["z_bottom_above_axle"], abs=1e-6)
    assert c["z_id_plate_above_axle"] < c["z_cover_above_axle"] < c["z_top_above_axle"]
    assert c["z_top_above_axle"] - c["z_id_plate_above_axle"] < 0.008     # the dots used to float by this much
    r = mjcf.WheelGeometry().r
    assert 0.150 < r + hi[2] < 0.156                         # bbox top ~ SSL height limit above the floor
    assert 0.145 < r + mjcf.cad_plate_z(meta) <= 0.150       # the id plate sits on the decal plane, under 150 mm
    assert mjcf.cad_plate_z(meta) == c["z_id_plate_above_axle"]
    assert mjcf.cad_plate_z({"chassis": {"z_top_above_axle": 0.1}}) == 0.1    # fallbacks
    assert mjcf.cad_plate_z({"chassis": {"z_top_above_axle": 0.1, "z_cover_above_axle": 0.09}}) == 0.09
    assert r + lo[2] > 0.0                                   # nothing below the floor


@pytest.mark.parametrize("key", ["wheel", "wheel_lod"])
def test_wheel_mesh_is_centred_on_its_axle(key):
    meta = mjcf.cad_meta()
    _, _, pts = _obj_stats(mjcf.ASSET_DIR / meta[key]["file"])
    lo, hi = pts.min(0), pts.max(0)
    assert hi[0] - lo[0] < 0.015                             # thin along the axle (+x)
    radial = np.hypot(pts[:, 1], pts[:, 2])
    assert radial.max() == pytest.approx(meta[key]["outer_radius"], abs=1e-6)
    wheel = mjcf.WheelGeometry()
    assert abs(radial.max() - wheel.r) < 0.002               # CAD rollers vs physics wheel radius
    assert abs(lo[1] + hi[1]) < 1e-3 and abs(lo[2] + hi[2]) < 1e-3
    assert meta[key]["axle"] == "+x" and meta[key]["cad_angle_deg"] == pytest.approx(60.0, abs=0.01)
    assert math.hypot(*meta[key]["cad_centre"][:2]) == pytest.approx(wheel.R, abs=2e-4)   # on the wheel circle


def test_chassis_lod_is_the_exterior_of_the_full_mesh():
    meta = mjcf.cad_meta()
    _, _, full = _obj_stats(mjcf.ASSET_DIR / meta["chassis"]["file"])
    _, _, lod = _obj_stats(mjcf.ASSET_DIR / meta["chassis_lod"]["file"])
    np.testing.assert_allclose(lod.max(0), full.max(0), atol=0.002)    # same envelope (shell, cover)
    np.testing.assert_allclose(lod.min(0)[:2], full.min(0)[:2], atol=0.002)
    assert lod.min(0)[2] >= full.min(0)[2] - 0.005


def test_mechanism_meshes_sit_in_the_chassis_mouth():
    """Kicker and dribbler (occurrences of robot_v2025_v3.iam, tessellated in the assembly frame): same body
    frame as the chassis OBJ (z origin on the wheel-axle plane). The dribbler spans the open mouth at the front,
    the kicker lies on the body x axis behind it; nothing reaches below the floor."""
    meta = mjcf.cad_meta()
    r = mjcf.WheelGeometry().r
    _, _, drib = _obj_stats(mjcf.ASSET_DIR / meta["dribbler"]["file"])
    lo, hi = drib.min(0), drib.max(0)
    assert 0.045 < lo[0] and 0.076 < hi[0] < 0.085               # at the front; a few mm proud of the 76.5 mm face
    assert abs(hi[1] + lo[1]) < 0.004 and 0.095 < hi[1] - lo[1] < 0.105    # ~100 mm wide, centred on x
    assert lo[2] + r > 0.0 and hi[2] + r < 0.080                   # above the floor, motor below the cover
    _, _, kick = _obj_stats(mjcf.ASSET_DIR / meta["kicker"]["file"])
    lo, hi = kick.min(0), kick.max(0)
    assert abs(hi[1] + lo[1]) < 0.002 and hi[1] - lo[1] < 0.060    # centred, 57 mm wide (striking plate)
    assert -0.088 < lo[0] and hi[0] < 0.0765                       # inside the chassis, head behind the front face
    assert lo[2] + r > 0.0


def test_mechanism_features_from_the_part_boxes():
    """The exporter writes one box per part in the OBJ header; meshes.json derives the dribbler bar, the mouth,
    the chip plate and the kicker plungers from them (metres, body frame, z from the axle plane), and the
    dataclass defaults of the physical dribbler are those values."""
    meta = mjcf.cad_meta()
    feats = meta["dribbler"]["features"]
    r = mjcf.WheelGeometry().r
    bar = feats["dribbler_bar"]
    assert bar["axis"] == "y" and abs(bar["centre"][1]) < 0.002 and 0.070 < bar["length"] < 0.075
    assert 0.0055 < bar["radius"] < 0.0075 and 0.065 < bar["centre"][0] < 0.080
    assert 0.035 < bar["centre"][2] + r < 0.050                     # bar axis 36-50 mm above the floor
    mouth = feats["mouth"]
    assert mouth["y_min"] < -0.025 < 0.025 < mouth["y_max"] and 0.054 < mouth["y_max"] - mouth["y_min"] < 0.060
    assert 0.055 < mouth["x_back"] < mouth["x_front"] < 0.085
    obb = feats["chip_plate"]["obb"]
    assert np.allclose(np.abs(np.asarray(obb["axes"]) @ np.asarray(obb["axes"]).T), np.eye(3), atol=1e-6)
    assert meta["dribbler_lod"]["features"] == feats
    kf = meta["kicker"]["features"]
    flat, chip = kf["kicker_flat_plunger"], kf["kicker_chip_plunger"]
    for pl in (flat, chip):
        assert pl["axis"] == "x" and abs(pl["centre"][1]) < 0.002 and 0.004 < pl["radius"] < 0.006
    assert chip["centre"][2] < flat["centre"][2]                     # chip plunger under the flat one
    assert 0.010 < chip["centre"][2] + r < 0.025 and 0.030 < flat["centre"][2] + r < 0.045
    assert mjcf.MouthGeometry.from_cad(meta) == mjcf.MouthGeometry()
    opt = mjcf.DribblerOptions.from_cad(meta)
    assert opt == mjcf.DribblerOptions() and tuple(bar["centre"]) == opt.bar_centre
    assert mjcf.MouthGeometry.from_cad({"dribbler": {}}) == mjcf.MouthGeometry()   # tolerant of old meta


def test_obj_reader_and_colour_split():
    """The exporter OBJ carries ``g`` per part and ``usemtl`` per colour; the MJCF draws one mesh per colour."""
    meta = mjcf.cad_meta()
    kick = mjcf.cad_obj("kicker")
    assert len(kick.groups) == meta["kicker"]["n_parts"] and len(kick.faces) == meta["kicker"]["faces"]
    assert set(kick.materials) == set(meta["kicker"]["materials"])
    assert kick.groups[0][2] == 0 and kick.groups[-1][3] == len(kick.faces)
    for (_, _, a, b), (_, _, c, _) in zip(kick.groups, kick.groups[1:], strict=False):
        assert b == c and a < b                                      # contiguous, in file order
    subs = mjcf.split_obj(kick, "kicker")
    assert [sm.label for sm in subs] == list(dict.fromkeys(m for _, m, _, _ in kick.groups))
    assert sum(sm.faces for sm in subs) == len(kick.faces)
    for sm in subs:
        rgb = kick.materials[sm.label]
        assert sm.rgba == (*rgb, 1.0) and sm.mesh == f"{mjcf.CAD_MESH_PREFIX}kicker_{sm.label}"
        part = mjcf.read_obj(sm.data)
        assert len(part.faces) == sm.faces and part.faces.max() == len(part.vertices) - 1
    # the dribbler bar is split out on its own (it spins with the physical bar)
    all_subs = mjcf.cad_submeshes()
    assert {k: len(v) for k, v in all_subs.items()} == N_SUBMESH
    bar = next(sm for sm in all_subs["dribbler"] if sm.label == mjcf.CAD_BAR_LABEL)
    pts = mjcf.read_obj(bar.data).vertices
    feat = meta["dribbler"]["features"]["dribbler_bar"]
    np.testing.assert_allclose((pts.min(0) + pts.max(0)) / 2, feat["centre"], atol=1e-3)
    assert pts[:, 1].max() - pts[:, 1].min() == pytest.approx(feat["length"], abs=1e-3)
    assert np.hypot(pts[:, 0] - feat["centre"][0], pts[:, 2] - feat["centre"][2]).max() == pytest.approx(
        feat["radius"], abs=5e-4)
    assert sum(sm.faces for sm in all_subs["dribbler"]) == meta["dribbler"]["faces"]
    assert set(mjcf.cad_mesh_files()) == {sm.file for subs in all_subs.values() for sm in subs}
    assert mjcf.read_mtl("newmtl a\nKd 0.1 0.2 0.3\nnewmtl b\n") == {"a": (0.1, 0.2, 0.3), "b": (0.5, 0.5, 0.5)}
    quad = mjcf.read_obj("v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\ng p\nusemtl m\nf 1/1 2/2 3/3 4/4\n")
    assert quad.faces.tolist() == [[0, 1, 2], [0, 2, 3]] and quad.groups == (("p", "m", 0, 2),)


@pytest.mark.parametrize("route", ["a", "b"])
def test_cad_xml_adds_visual_only_geoms_and_hides_primitives(route):
    scene = Scene(robots=[RobotSpawn("blue", 2, 0.0, 0.0, 0.0), RobotSpawn("yellow", 5, 1.0, 0.0, math.pi)])
    xml_p = mjcf.build_world_xml(scene, route, visual="primitive")
    xml_c = mjcf.build_world_xml(scene, route, visual="cad")
    assert not mjcf.uses_cad(xml_p) and mjcf.uses_cad(xml_c)
    root = ET.fromstring(xml_c)
    meshes = {m.get("name"): m.get("file") for m in root.iter("mesh") if m.get("file")}
    assert len(meshes) == sum(N_SUBMESH.values()) and all(n.startswith(mjcf.CAD_MESH_PREFIX) for n in meshes)
    assert set(meshes.values()) == set(mjcf.cad_mesh_files())
    cad_geoms = [g for g in root.iter("geom") if g.get("mesh") in meshes]
    assert len(cad_geoms) == 2 * mjcf.cad_geom_count() == 2 * (13 + 4 * 5 + 3 + 9)
    for g in cad_geoms:
        assert g.get("contype") == "0" and g.get("conaffinity") == "0" and g.get("mass") == "0"
        assert len(g.get("rgba").split()) == 4
    wheel = mjcf.WheelGeometry()
    fixed = [g for g in cad_geoms if "_cad_wheel" not in g.get("name")]
    assert len(fixed) == 2 * (13 + 3 + 9)
    for g in fixed:                                           # mechanisms share the chassis frame and offset
        assert [float(v) for v in g.get("pos").split()] == pytest.approx([0.0, 0.0, wheel.r])
    names = {g.get("name") for g in fixed}
    assert {"blue_2_cad_kicker_m_999999", "blue_2_cad_dribbler_bar", "yellow_5_cad_chassis_m_bfbfbf"} <= names
    colours = {g.get("rgba") for g in fixed if g.get("name").startswith("blue_2_cad_chassis")}
    assert len(colours) == 13                                 # one geom per Inventor colour
    wheels = [g for g in cad_geoms if "_cad_wheel" in g.get("name")]
    assert len(wheels) == 2 * 4 * 5
    yaws = sorted(round(math.degrees(float(g.get("euler").split()[2]))) % 360 for g in wheels)
    assert yaws == sorted(list(wheel.angles_deg) * 2 * 5)
    # primitives hidden (group 3), CAD visible (group 1); the collision geoms are unchanged otherwise
    d_ch = next(d for d in root.iter("default") if d.get("class") == "chassis").find("geom")
    assert d_ch.get("group") == mjcf.HIDDEN_GROUP
    d_ch_p = next(d for d in ET.fromstring(xml_p).iter("default") if d.get("class") == "chassis").find("geom")
    assert {k: v for k, v in d_ch.attrib.items() if k != "group"} == {k: v for k, v in d_ch_p.attrib.items()
                                                                       if k != "group"}
    if route == "b":
        d_r = next(d for d in root.iter("default") if d.get("class") == "roller").find("geom")
        assert d_r.get("group") == mjcf.HIDDEN_GROUP
        hubs = [g for g in root.iter("geom") if (g.get("name") or "").endswith("_hub")]
        assert hubs and all(g.get("group") == mjcf.HIDDEN_GROUP for g in hubs)
        # the CAD wheel lives in the wheel body (spins with it), at the body origin
        for body in root.iter("body"):
            if (body.get("name") or "").endswith("_wheel0"):
                gs = [g for g in body.findall("geom") if g.get("mesh") in meshes]
                assert len(gs) == 5 and all(g.get("pos") == "0 0 0" for g in gs)
    # the SSL id plate sits on the decal plane of the CAD cover (not on the bbox top: the dots used to float)
    top = next(g for g in root.iter("geom") if g.get("name") == "blue_2_top")
    z = float(top.get("pos").split()[2])
    assert z == pytest.approx(wheel.r + mjcf.cad_plate_z() + 0.0015)
    assert z < wheel.r + mjcf.cad_meta()["chassis"]["z_top_above_axle"]
    top_p = next(g for g in ET.fromstring(xml_p).iter("geom") if g.get("name") == "blue_2_top")
    assert float(top_p.get("pos").split()[2]) == pytest.approx(mjcf.RobotSpec().height + 0.0015)


def test_visual_mode_validation():
    assert mjcf.normalize_visual(None) == "primitive"
    assert mjcf.normalize_visual("CAD") == "cad"
    with pytest.raises(ValueError):
        mjcf.normalize_visual("fancy")


# ---------------------------------------------------------------- with mujoco
@pytest.mark.requires_mujoco
@pytest.mark.parametrize("route", ["a", "b"])
def test_cad_models_compile_with_identical_physics_sizes(route):
    pytest.importorskip("mujoco")
    scene = Scene.default(2, 2)
    mp = mjcf.load_model(mjcf.build_world_xml(scene, route, visual="primitive"))
    mc = mjcf.load_model(mjcf.build_world_xml(scene, route, visual="cad"))
    assert (mc.nbody, mc.njnt, mc.nq, mc.nv, mc.nu, mc.nsite) == (mp.nbody, mp.njnt, mp.nq, mp.nv, mp.nu, mp.nsite)
    assert mc.ngeom == mp.ngeom + 4 * mjcf.cad_geom_count()
    assert mc.nmesh == mp.nmesh + sum(N_SUBMESH.values())
    faces = dict(zip((mc.mesh(i).name for i in range(mc.nmesh)), mc.mesh_facenum.tolist(), strict=True))
    meta = mjcf.cad_meta()
    for key in mjcf.CAD_KEYS:
        assert sum(faces[sm.mesh] for sm in mjcf.cad_submeshes()[key]) == meta[key]["faces"]
    # same mass and inertia on every body
    np.testing.assert_allclose(mc.body_mass, mp.body_mass)
    np.testing.assert_allclose(mc.body_inertia, mp.body_inertia)
    np.testing.assert_allclose(mc.body_ipos, mp.body_ipos)


@pytest.mark.requires_mujoco
@pytest.mark.parametrize("route", ["a", "b"])
def test_cad_visual_does_not_change_the_dynamics(route):
    """Same commands, same trajectories (including a ball contact) with and without the meshes."""
    pytest.importorskip("mujoco")
    from dtssl.physics.mujoco_world import MuJoCoWorld

    def run(visual):
        scene = Scene(robots=[RobotSpawn("blue", 0, -0.25, 0.0, 0.0), RobotSpawn("yellow", 1, 0.6, 0.05, math.pi)],
                      ball=BallState(x=0.0, y=0.0))
        w = MuJoCoWorld(route, scene=scene, watchdog_clock="sim", visual=visual)
        w.reset(scene)
        out = []
        for k in range(90):
            w.set_command("blue", 0, RobotCmd(vx=0.8, vy=0.1 * math.sin(k / 10), w=0.4))
            w.set_command("yellow", 1, RobotCmd(vx=0.3, w=-0.6))
            w.step()
            st = w.state()
            out.append([st.robots[("blue", 0)].x, st.robots[("blue", 0)].y, st.robots[("blue", 0)].theta,
                        st.robots[("yellow", 1)].x, st.robots[("yellow", 1)].y, st.robots[("yellow", 1)].theta,
                        st.ball.x, st.ball.y])
        w.close()
        return np.asarray(out)

    a, b = run("primitive"), run("cad")
    assert np.isfinite(a).all() and np.abs(a[-1, :2] - a[0, :2]).max() > 0.5      # the robot actually moved
    np.testing.assert_array_equal(b, a)                                            # bit-exact (measured)


@pytest.mark.requires_mujoco
def test_mjcf_cli_writes_standalone_cad_models(tmp_path):
    mujoco = pytest.importorskip("mujoco")
    from dtssl.physics.cli import write_models

    written = write_models("both", tmp_path, n_blue=1, n_yellow=1, visual="cad")
    names = {p.name for p in written}
    assert {"ssl_route_a_cad.xml", "ssl_route_b_cad.xml", "ssl_route_a_cad.md"} <= names
    assert set(mjcf.cad_mesh_files()) | {"meshes.json"} <= names
    for r in ("a", "b"):
        m = mujoco.MjModel.from_xml_path(str(tmp_path / f"ssl_route_{r}_cad.xml"))   # OBJ files resolved next to it
        assert m.nmesh == 1 + sum(N_SUBMESH.values())
    md = (tmp_path / "ssl_route_b_cad.md").read_text(encoding="utf-8")
    assert "## CAD meshes" in md and "ssl_chassis.obj" in md and "nbody=" in md
    assert "ssl_dribbler.obj" in md and "robot_v2025_v3.iam" in md
    assert json.loads((tmp_path / "meshes.json").read_text(encoding="utf-8")) == mjcf.cad_meta()


@pytest.mark.requires_mujoco
def test_world_plant_accepts_visual_option():
    """The harness adapter forwards world options: the meshes are irrelevant to the metric."""
    pytest.importorskip("mujoco")
    from dtssl.sim.world_plant import make_harness_plant

    p = make_harness_plant("mujoco-velocity", visual="cad")
    assert p.world.visual == "cad"
    p.reset((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    for _ in range(5):
        pose = p.step((0.5, 0.0, 0.0), 1 / 60)
    assert np.isfinite(pose).all()
