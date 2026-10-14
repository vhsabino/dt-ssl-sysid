"""MJCF builder: XML generation without mujoco, loading with mujoco (0..6 robots per team)."""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from dtssl.physics import mjcf
from dtssl.sim.entities import RobotSpawn, Scene
from dtssl.sim.world import FieldGeometry, RobotSpec


# ---------------------------------------------------------------- pure python (no mujoco)
def test_import_physics_does_not_import_mujoco():
    import subprocess
    import sys

    code = "import sys, dtssl.physics, dtssl.physics.mjcf, dtssl.physics.cli; print('mujoco' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    assert out.strip() == "False"


def test_field_xml_structure():
    xml = mjcf.build_field_xml(mjcf.load_field_geometry(), boundary=True)
    root = ET.fromstring(xml)
    names = {g.get("name") for g in root.iter("geom")}
    assert {"floor", "wall_xpos", "wall_xneg", "wall_ypos", "wall_yneg", "goal_left_back", "goal_right_back"} <= names
    floor = next(g for g in root.iter("geom") if g.get("name") == "floor")
    assert floor.get("condim") == "3" and floor.get("friction").startswith("0.9")
    lines = [g for g in root.iter("geom") if g.get("class") == "field_line"]
    assert len(lines) > 40                      # rectangle, half line, penalty areas, centre circle
    line_cls = next(d for d in root.iter("default") if d.get("class") == "field_line").find("geom")
    assert line_cls.get("contype") == "0" and line_cls.get("conaffinity") == "0"
    xml2 = mjcf.build_field_xml(boundary=False)
    assert "wall_xpos" not in xml2


def test_ball_xml_parameters():
    ball = mjcf.load_ball_spec()
    assert ball.radius == pytest.approx(0.0215) and ball.mass == pytest.approx(0.046)
    root = ET.fromstring(mjcf.build_ball_xml(ball))
    g = next(g for g in root.iter("geom") if g.get("name") == "ball_geom")
    assert g.get("condim") == "6" and g.get("priority") == "1"
    mu = [float(v) for v in g.get("friction").split()]
    assert mu[0] == pytest.approx(ball.sliding_decel / 9.81, rel=1e-3)          # sliding phase
    assert mu[2] == pytest.approx(ball.rolling_decel * 1.4 * ball.radius / 9.81, rel=1e-3)   # rolling phase
    assert root.find(".//freejoint").get("name") == mjcf.BALL_JOINT


@pytest.mark.parametrize("route", ["a", "b"])
def test_robot_xml_structure(route):
    root = ET.fromstring(mjcf.build_robot_xml("blue", 3, route))
    body = next(b for b in root.iter("body") if b.get("name") == "blue_3")
    joints = [(j.tag, j.get("type")) for j in body if j.tag in ("joint", "freejoint")]
    if route == "a":
        assert joints == [("joint", "slide"), ("joint", "slide"), ("joint", "hinge")]
        assert body.get("pos") == "0 0 0"                                       # world frame = body frame
        acts = root.find("actuator")
        assert [a.tag for a in acts] == ["velocity"] * 3
        assert all(a.get("forcerange") for a in acts)
    else:
        assert joints == [("freejoint", None)]
        wheels = [b for b in body.findall("body")]
        assert len(wheels) == 4
        rollers = [r for w in wheels for r in w.findall("body")]
        assert len(rollers) == 4 * 12
        assert all(r.find("joint").get("class") == "roller" for r in rollers)
        assert len(root.find("actuator")) == 4
    sites = {s.get("name") for s in body.findall("site")}
    assert sites == {"blue_3_dribbler", "blue_3_kicker"}
    inertial = body.find("inertial")
    assert float(inertial.get("mass")) == pytest.approx(2.4)


def test_route_b_wheel_axes_follow_sign_convention():
    """Hinge axis = inward radial (-cos phi, -sin phi, 0) so that positive wheel speed = CCW tangent."""
    wheel = mjcf.WheelGeometry()
    root = ET.fromstring(mjcf.build_robot_xml("yellow", 0, "b", wheel=wheel))
    for i, phi in enumerate(wheel.angles):
        j = next(j for j in root.iter("joint") if j.get("name") == f"yellow_0_wheel{i}")
        ax = np.array([float(v) for v in j.get("axis").split()])
        assert np.allclose(ax, [-math.cos(phi), -math.sin(phi), 0.0], atol=1e-6)
        wb = next(b for b in root.iter("body") if b.get("name") == f"yellow_0_wheel{i}")
        pos = np.array([float(v) for v in wb.get("pos").split()])
        assert np.allclose(pos, [wheel.R * math.cos(phi), wheel.R * math.sin(phi), wheel.r], atol=1e-6)
        # roller axes are perpendicular to the wheel axle
        for rb in wb.findall("body"):
            rax = np.array([float(v) for v in rb.find("joint").get("axis").split()])
            assert abs(np.dot(rax, ax)) < 1e-6
            assert abs(np.linalg.norm(rax) - 1.0) < 1e-6


def test_ik_matrix_matches_spec_formula_and_kinematics_module():
    wheel = mjcf.load_wheel_geometry()
    M = mjcf.ik_matrix(wheel)
    phi = wheel.angles
    expected = np.column_stack([-np.sin(phi), np.cos(phi), np.full(4, wheel.R)]) / wheel.r
    assert np.allclose(M, expected)
    assert np.allclose(mjcf.body_to_wheels(0, 0, 1, wheel), wheel.R / wheel.r)           # pure rotation
    kin = pytest.importorskip("dtssl.kinematics")
    assert np.allclose(M, kin.body_to_wheel_matrix(wheel.to_robot_geometry()))


def test_field_xml_follows_the_division_a_geometry():
    """``config/field_divA.json`` through the same fragment: goals 1.8 m wide at x = +-6 m, walls at +-6.3 / +-4.8."""
    from dtssl.config import load_field_preset

    fld = load_field_preset("divA").field
    root = ET.fromstring(mjcf.build_field_xml(fld, boundary=True))
    geoms = {g.get("name"): g for g in root.iter("geom") if g.get("name")}
    bodies = {b.get("name"): b for b in root.iter("body") if b.get("name")}
    gx = [float(v) for v in bodies["goal_right"].get("pos").split()]
    assert gx[0] == pytest.approx(6.0 + 0.18 / 2)                                   # goal body centred on its depth
    top = [float(v) for v in geoms["goal_right_top"].get("pos").split()]
    assert top[1] == pytest.approx(0.9 + 0.01)                                      # half the 1.8 m goal + wall/2
    wx = [float(v) for v in geoms["wall_xpos"].get("pos").split()]
    wy = [float(v) for v in geoms["wall_ypos"].get("pos").split()]
    assert wx[0] == pytest.approx(6.3 + 0.01) and wy[1] == pytest.approx(4.8 + 0.01)
    pen = [float(v) for v in geoms["pen_right_front"].get("pos").split()]
    assert pen[0] == pytest.approx(6.0 - 1.8)                                       # 3.6 x 1.8 m defense area
    assert float(geoms["pen_right_front"].get("size").split()[1]) == pytest.approx(1.8 + 0.005)


def test_mjcf_cli_field_option_writes_the_division_a_model(tmp_path):
    """``dtssl mjcf --route a --field divA``: Division A fragment, the division's 11 robots per team, file names
    suffixed with the preset; without ``--field`` the Division B files keep their names and 6 per team."""
    import argparse

    from dtssl.physics.cli import _add_arguments, write_models

    ap = argparse.ArgumentParser()
    _add_arguments(ap)
    args = ap.parse_args(["--route", "a", "--field", "divA"])
    assert (args.field, args.n_blue) == ("divA", None)
    written = write_models("a", tmp_path, field=args.field)
    assert [p.name for p in written] == ["ssl_route_a_divA.xml", "ssl_route_a_divA.md"]
    root = ET.fromstring(written[0].read_text(encoding="utf-8").split("\n", 1)[1])
    geoms = {g.get("name"): g for g in root.iter("geom") if g.get("name")}
    assert float(geoms["wall_xpos"].get("pos").split()[0]) == pytest.approx(6.3 + 0.01)
    robots = [b.get("name") for b in root.iter("body") if b.get("name", "").startswith(("blue_", "yellow_"))
              and b.get("name", "").count("_") == 1]
    assert len(robots) == 22 and "--field divA" in written[0].read_text(encoding="utf-8").split("\n", 1)[0]
    written = write_models("a", tmp_path, n_blue=2, n_yellow=0)
    assert [p.name for p in written] == ["ssl_route_a.xml", "ssl_route_a.md"]
    root = ET.fromstring(written[0].read_text(encoding="utf-8").split("\n", 1)[1])
    geoms = {g.get("name"): g for g in root.iter("geom") if g.get("name")}
    assert float(geoms["wall_xpos"].get("pos").split()[0]) == pytest.approx(4.8 + 0.01)


def test_loaders_read_config_files():
    fld = mjcf.load_field_geometry()
    assert isinstance(fld, FieldGeometry) and fld.length == 9.0 and fld.goal_depth == pytest.approx(0.18)
    spec = mjcf.load_robot_spec()
    assert isinstance(spec, RobotSpec) and spec.radius == 0.09 and spec.watchdog_s == 0.3
    wheel = mjcf.load_wheel_geometry()
    assert wheel.R == pytest.approx(0.079601) and wheel.r == pytest.approx(0.029492)
    enabled, dz = mjcf.load_deadzone()
    assert enabled is False and dz == pytest.approx(1.567)


def test_chassis_inertia_is_uniform_cylinder():
    ixx, iyy, izz = mjcf.chassis_inertia(RobotSpec())
    assert izz == pytest.approx(0.5 * 2.4 * 0.09 ** 2)
    assert ixx == iyy == pytest.approx(2.4 * (3 * 0.09 ** 2 + 0.15 ** 2) / 12)


def test_dead_beat_gains():
    ra = mjcf.RouteAOptions()
    kv_s, kv_h = ra.gains(RobotSpec(), 1.0 / 480.0)
    assert kv_s == pytest.approx(2.4 * 480.0)
    assert kv_h == pytest.approx(mjcf.chassis_inertia(RobotSpec())[2] * 480.0)


def test_describe_xml_lists_bodies_and_actuators():
    md = mjcf.describe_xml(mjcf.build_world_xml(Scene.default(1, 1), "a"), title="t")
    assert "blue_0_act_x" in md and "yellow_0" in md and "## sites" in md


# ---------------------------------------------------------------- with mujoco
@pytest.mark.requires_mujoco
@pytest.mark.parametrize("route", ["a", "b"])
@pytest.mark.parametrize("n", [0, 1, 3, 6])
def test_world_xml_loads_in_mujoco(route, n):
    mujoco = pytest.importorskip("mujoco")
    scene = Scene.default(n, n)
    xml = mjcf.build_world_xml(scene, route)
    model = mujoco.MjModel.from_xml_string(xml)
    n_rob = 2 * n
    assert model.nu == (3 if route == "a" else 4) * n_rob
    if route == "a":
        assert model.nv == 6 + 3 * n_rob                      # ball + planar robots
    else:
        assert model.nv == 6 + (6 + 4 + 4 * 12) * n_rob
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    for _ in range(10):
        mujoco.mj_step(model, data)
    assert np.isfinite(data.qpos).all()


@pytest.mark.requires_mujoco
def test_standalone_builders_load_in_mujoco():
    mujoco = pytest.importorskip("mujoco")
    for xml in (mjcf.build_field_xml(), mjcf.build_ball_xml(), mjcf.build_robot_xml("blue", 0, "a"),
                mjcf.build_robot_xml("blue", 15, "b", wheel=mjcf.WheelGeometry(roller_shape="capsule"))):
        mujoco.MjModel.from_xml_string(xml)


@pytest.mark.requires_mujoco
def test_chassis_com_on_joint_axis():
    """The explicit inertial must win over the D-shaped mesh (inertiafromgeom=auto)."""
    mujoco = pytest.importorskip("mujoco")
    model = mujoco.MjModel.from_xml_string(mjcf.build_world_xml(Scene(robots=[RobotSpawn("blue", 0, 0, 0, 0)]), "a"))
    b = model.body("blue_0")
    assert abs(model.body_ipos[b.id][0]) < 1e-9 and abs(model.body_ipos[b.id][1]) < 1e-9
    assert model.body_inertia[b.id][2] == pytest.approx(mjcf.chassis_inertia(RobotSpec())[2])
