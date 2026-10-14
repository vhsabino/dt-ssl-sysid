"""Physical dribbler (``dribbler='bar'``): CAD geometry, MJCF structure, holding the ball in MuJoCo."""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from dtssl.physics import mjcf
from dtssl.sim.entities import BallState, RobotCmd, RobotSpawn, Scene

BALL_R = mjcf.BallSpec.radius
WHEEL = mjcf.WheelGeometry()


# ---------------------------------------------------------------- geometry / XML (no mujoco)
def test_dribbler_mode_validation():
    assert mjcf.normalize_dribbler(None) == "spring" and mjcf.normalize_dribbler("BAR") == "bar"
    with pytest.raises(ValueError):
        mjcf.normalize_dribbler("magnet")


def test_mouth_geometry_from_the_cad():
    """A ball on the floor touching the chip plate sits ~95 mm ahead of the centre, 3 mm short of the bar."""
    opt = mjcf.DribblerOptions.from_cad()
    mouth = opt.mouth
    p0, n = mouth.plate_front()
    assert n[0] > 0.9 and n[2] > 0.0                                  # front face: forward, leaning back
    ball = mouth.resting_ball(BALL_R, -WHEEL.r)
    assert ball[1] == 0.0 and ball[2] == pytest.approx(BALL_R - WHEEL.r)
    assert 0.093 < ball[0] < 0.097
    axis, gap = opt.engagement(BALL_R, WHEEL.r)
    assert np.linalg.norm(axis) == pytest.approx(1.0) and axis[1] == 0.0
    assert axis[0] > 0.6 and axis[2] < -0.6                            # bar sits behind and above the ball, ~45 deg
    assert 0.002 < gap < 0.004
    assert opt.speed_max(mjcf.RobotSpec()) == pytest.approx(6000 * 2 * math.pi / 60)
    assert opt.gain(1 / 480) == pytest.approx(opt.bar_inertia * 240)
    assert mjcf.DribblerOptions.from_cad(engage=None).engage is None


def test_spring_mode_xml_is_unchanged_by_the_bar_option():
    scene = Scene(robots=[RobotSpawn("blue", 0, 0.0, 0.0, 0.0)])
    for route in ("a", "b"):
        xml = mjcf.build_world_xml(scene, route)
        assert xml == mjcf.build_world_xml(scene, route, dribbler="spring")
        assert "_dribbler_module" not in xml and "mouth_plate" not in xml and "act_dribbler" not in xml


@pytest.mark.parametrize("route", ["a", "b"])
@pytest.mark.parametrize("visual", ["primitive", "cad"])
def test_bar_xml_structure(route, visual):
    scene = Scene(robots=[RobotSpawn("blue", 0, 0.0, 0.0, 0.0), RobotSpawn("yellow", 3, 1.0, 0.0, math.pi)])
    root = ET.fromstring(mjcf.build_world_xml(scene, route, visual=visual, dribbler="bar"))
    opt = mjcf.DribblerOptions.from_cad()
    axis, gap = opt.engagement(BALL_R, WHEEL.r)
    stop = gap + opt.engage
    bodies = {b.get("name"): b for b in root.iter("body") if b.get("name")}
    for name in ("blue_0", "yellow_3"):
        module = bodies[f"{name}_dribbler_module"]
        pos = np.array([float(v) for v in module.get("pos").split()])
        np.testing.assert_allclose(pos, np.asarray(opt.bar_centre) + [0, 0, WHEEL.r] + stop * axis, atol=1e-6)
        slide = module.find("joint")
        assert slide.get("type") == "slide" and slide.get("name") == f"{name}_dribbler_slide"
        np.testing.assert_allclose([float(v) for v in slide.get("axis").split()], axis, atol=1e-6)
        lo, hi = (float(v) for v in slide.get("range").split())
        assert hi == 0.0 and lo == pytest.approx(-(opt.travel_back + stop), abs=1e-6)   # rests at the stop
        assert float(slide.get("springref")) == 0.0 and float(slide.get("stiffness")) == opt.stiffness
        bar = bodies[f"{name}_dribbler_bar"]
        assert bar in list(module)
        hinge = bar.find("joint")
        assert hinge.get("type") == "hinge" and hinge.get("axis") == "0 1 0" and hinge.get("name") == f"{name}_dribbler"
        geom = next(g for g in bar.findall("geom") if g.get("name") == f"{name}_dribbler_bar_geom")
        assert geom.get("type") == "capsule" and float(geom.get("size")) == opt.bar_radius
        assert geom.get("contype") == str(mjcf.MOUTH_CONTYPE) and geom.get("conaffinity") == "0"
        assert geom.get("priority") == "2" and geom.get("group") == (mjcf.HIDDEN_GROUP if visual == "cad" else "0")
        cad_bar = [g for g in bar.findall("geom") if g.get("mesh") == f"{mjcf.CAD_MESH_PREFIX}dribbler_bar"]
        assert len(cad_bar) == (1 if visual == "cad" else 0)
        if cad_bar:   # the bar mesh is drawn on the spinning body, shifted back to the mesh origin
            np.testing.assert_allclose([float(v) for v in cad_bar[0].get("pos").split()],
                                       -np.asarray(opt.bar_centre) - stop * axis, atol=1e-6)
            chassis_bar = [g for g in bodies[name].findall("geom")
                           if g.get("mesh") == f"{mjcf.CAD_MESH_PREFIX}dribbler_bar"]
            assert chassis_bar == []                                   # and not on the chassis
        mouth = {g.get("name"): g for g in bodies[name].findall("geom") if g.get("class") == "mouth"}
        assert set(mouth) == {f"{name}_mouth_shell", f"{name}_mouth_cheek_l", f"{name}_mouth_cheek_r",
                              f"{name}_mouth_plate"}
        assert mouth[f"{name}_mouth_plate"].get("type") == "box"
        prim = next(g for g in bodies[name].findall("geom") if g.get("name") == f"{name}_dribbler_bar")
        assert prim.get("group") == mjcf.HIDDEN_GROUP                  # the visual box of the spring mode is hidden
    acts = {a.get("name"): a for a in root.find("actuator")}
    for name in ("blue_0", "yellow_3"):
        a = acts[f"{name}_act_dribbler"]
        assert a.tag == "velocity" and a.get("joint") == f"{name}_dribbler"
        lo, hi = (float(v) for v in a.get("ctrlrange").split())
        assert lo == 0.0 and hi == pytest.approx(opt.speed_max(mjcf.RobotSpec()))
    d_mouth = next(d for d in root.iter("default") if d.get("class") == "mouth").find("geom")
    assert d_mouth.get("contype") == str(mjcf.MOUTH_CONTYPE) and d_mouth.get("conaffinity") == "0"
    assert d_mouth.get("priority") == "2" and d_mouth.get("mass") == "0"
    d_ch = next(d for d in root.iter("default") if d.get("class") == "chassis").find("geom")
    assert d_ch.get("conaffinity") == str(mjcf.ROBOT_CONAFF_MOUTH)      # the D-shell no longer meets the ball
    ball = next(g for g in root.iter("geom") if g.get("name") == "ball_geom")
    assert ball.get("conaffinity") == str(mjcf.BALL_CONAFF_MOUTH)
    assert int(ball.get("conaffinity")) & mjcf.BIT_MOUTH
    # the moving module and bar take their mass out of the chassis inertial
    inertial = bodies["blue_0"].find("inertial")
    assert float(inertial.get("mass")) == pytest.approx(mjcf.RobotSpec().mass - opt.module_mass - opt.bar_mass)
    assert float(bodies["blue_0_dribbler_module"].find("inertial").get("mass")) == opt.module_mass


def test_mouth_cheeks_reach_the_side_plates_front_edge():
    """The cheek prisms extend to ``x_front`` of the CAD side plates (beyond the D-face) and leave the mouth open."""
    scene = Scene(robots=[RobotSpawn("blue", 0, 0.0, 0.0, 0.0)])
    root = ET.fromstring(mjcf.build_world_xml(scene, "a", dribbler="bar"))
    mouth = mjcf.MouthGeometry.from_cad()
    verts = {m.get("name"): np.array([float(v) for v in m.get("vertex").split()]).reshape(-1, 3)
             for m in root.iter("mesh") if m.get("name", "").startswith("mouth_")}
    cl, cr = verts["mouth_cheek_l"], verts["mouth_cheek_r"]
    assert cl[:, 0].max() == pytest.approx(mouth.x_front, abs=1e-6) and cl[:, 0].min() == pytest.approx(mouth.x_back)
    assert cl[:, 1].min() == pytest.approx(mouth.y_max, abs=1e-6) and cr[:, 1].max() == pytest.approx(mouth.y_min)
    shell = verts["mouth_shell"]
    assert shell[:, 0].max() == pytest.approx(mouth.x_back, abs=1e-6) and shell[:, 0].min() < -0.085


# ---------------------------------------------------------------- with mujoco
def _world(route="a", visual="primitive", ball_x=0.25, **opt):
    from dtssl.physics.mujoco_world import MuJoCoWorld

    scene = Scene(robots=[RobotSpawn("blue", 0, 0.0, 0.0, 0.0)], ball=BallState(x=ball_x, y=0.0))
    kw = dict(dribbler_opt=mjcf.DribblerOptions.from_cad(**opt)) if opt else {}
    return MuJoCoWorld(route, scene=scene, watchdog_clock="sim", dribbler="bar", visual=visual, **kw)


def _ball_in_body(ws):
    r, b = ws.robots[("blue", 0)], ws.ball
    c, s = math.cos(r.theta), math.sin(r.theta)
    dx, dy = b.x - r.x, b.y - r.y
    return c * dx + s * dy, -s * dx + c * dy


def _ramp(t, v0, v1, a):
    dv = v1 - v0
    return v1 if dv == 0.0 else v0 + math.copysign(min(abs(dv), a * t), dv)


def _run_phase(world, seconds, cmd_of_t):
    rows = []
    n = int(round(seconds * 60))
    for k in range(n):
        world.set_command("blue", 0, cmd_of_t(k / 60.0))
        ws = world.step()
        bx, by = _ball_in_body(ws)
        _, slide, touch = world.dribbler_state("blue", 0)
        rows.append((bx, by, ws.ball.z, touch, slide, ws.robots[("blue", 0)].has_ball))
    return np.asarray(rows)


@pytest.mark.requires_mujoco
@pytest.mark.parametrize("route", ["a", "b"])
def test_bar_models_compile_and_add_the_mechanism(route):
    pytest.importorskip("mujoco")
    scene = Scene.default(2, 1)
    ms = mjcf.load_model(mjcf.build_world_xml(scene, route))
    mb = mjcf.load_model(mjcf.build_world_xml(scene, route, dribbler="bar"))
    n = 3
    assert (mb.nbody, mb.njnt, mb.nv, mb.nu) == (ms.nbody + 2 * n, ms.njnt + 2 * n, ms.nv + 2 * n, ms.nu + n)
    assert mb.ngeom == ms.ngeom + 5 * n and mb.nmesh == ms.nmesh + 3
    np.testing.assert_allclose(mb.body_mass.sum(), ms.body_mass.sum())          # same total mass
    mc = mjcf.load_model(mjcf.build_world_xml(scene, route, dribbler="bar", visual="cad"))
    assert mc.ngeom == mb.ngeom + n * mjcf.cad_geom_count() and mc.nu == mb.nu


@pytest.mark.requires_mujoco
def test_bar_spins_the_ball_backwards_and_holds_it():
    """Capture at 0.3 m/s then ramped brake / reverse / turn / side step: the ball stays in the mouth, pressed by
    the bar (slide pushed back), with back-spin (negative rate about body y, surface speed of the bar)."""
    pytest.importorskip("mujoco")
    w = _world()
    m, d = w.model, w.data
    rpm = 3000.0
    w_bar = rpm * 2 * math.pi / 60
    a = _run_phase(w, 1.0, lambda t: RobotCmd(vx=0.3, dribbler_rpm=rpm))                         # approach
    assert a[-1, 0] < 0.11 and a[-20:, 3].any()                                                    # captured
    a = _run_phase(w, 0.7, lambda t: RobotCmd(vx=0.3, dribbler_rpm=rpm))                         # carry
    assert a[-1, 0] < 0.106 and a[-20:, 3].mean() > 0.8 and a[-20:, 4].max() < -1e-3             # held, pressed
    speed, slide, touch = w.dribbler_state("blue", 0)
    assert speed == pytest.approx(w_bar, rel=0.1)
    ball_body = m.geom_bodyid[m.geom("ball_geom").id]
    wy = float(d.cvel[ball_body][1])
    assert wy < 0.0 and abs(wy) == pytest.approx(w_bar * w.dribbler_opt.bar_radius / BALL_R, rel=0.35)
    phases = [
        ("brake", 1.3, lambda t: RobotCmd(vx=_ramp(t, 0.3, 0.0, 1.0), dribbler_rpm=rpm)),
        ("reverse", 1.3, lambda t: RobotCmd(vx=_ramp(t, 0.0, -0.3, 1.0), dribbler_rpm=rpm)),
        ("stop", 0.8, lambda t: RobotCmd(vx=_ramp(t, -0.3, 0.0, 1.0), dribbler_rpm=rpm)),
        ("turn", 2.0, lambda t: RobotCmd(w=_ramp(t, 0.0, 1.5, 3.0), dribbler_rpm=rpm)),
        ("side", 1.3, lambda t: RobotCmd(vy=_ramp(t, 0.0, 0.3, 1.0), dribbler_rpm=rpm)),
    ]
    for name, secs, fn in phases:
        rows = _run_phase(w, secs, fn)
        assert 0.085 < rows[-1, 0] < 0.106 and abs(rows[-1, 1]) < 0.012, name              # still in the mouth
        assert rows[:, 3].mean() > 0.8 and rows[:, 5].all() and rows[:, 2].max() < 0.004, name
        assert rows[:, 4].min() > -(w.dribbler_opt.travel_back + 0.012), name
    assert w.state().robots[("blue", 0)].has_ball
    w.close()


@pytest.mark.requires_mujoco
def test_ball_is_lost_when_braking_harder_than_the_friction_allows():
    """Only friction holds the ball: a step from 0.4 m/s to -1 m/s leaves it behind (same world, no ramp)."""
    pytest.importorskip("mujoco")
    w = _world()
    _run_phase(w, 1.0, lambda t: RobotCmd(vx=0.4, dribbler_rpm=3000.0))
    assert w.dribbler_state("blue", 0)[2]
    rows = _run_phase(w, 1.5, lambda t: RobotCmd(vx=-1.0, dribbler_rpm=3000.0))
    assert rows[-1, 0] > 0.3 and not rows[-1, 3]
    w.close()


@pytest.mark.requires_mujoco
def test_helix_centring_keeps_the_ball_in_a_turn():
    """Without the screw action of the bar (``helix=0``) a plain cylinder loses the ball sideways in the turn."""
    pytest.importorskip("mujoco")
    rpm = 3000.0
    out = {}
    for helix in (0.3, 0.0):
        w = _world(helix=helix)
        _run_phase(w, 1.0, lambda t: RobotCmd(vx=0.3, dribbler_rpm=rpm))
        _run_phase(w, 1.3, lambda t: RobotCmd(vx=_ramp(t, 0.3, 0.0, 1.0), dribbler_rpm=rpm))
        rows = _run_phase(w, 2.0, lambda t: RobotCmd(w=_ramp(t, 0.0, 1.5, 3.0), dribbler_rpm=rpm))
        out[helix] = rows
        w.close()
    assert abs(out[0.3][:, 1]).max() < 0.012 and out[0.3][-20:, 3].mean() > 0.8
    assert abs(out[0.0][:, 1]).max() > 0.02 and not out[0.0][-20:, 3].any()


@pytest.mark.requires_mujoco
def test_bar_world_state_and_spring_default():
    pytest.importorskip("mujoco")
    from dtssl.physics.mujoco_world import MuJoCoWorld

    w = MuJoCoWorld("a", scene=Scene.default(1, 0), watchdog_clock="sim")
    assert w.dribbler == "spring" and w.dribbler_state("blue", 0) == (0.0, 0.0, False)
    w.close()
    w = _world(ball_x=1.0)
    assert w.dribbler == "bar" and w.dribbler_opt == mjcf.DribblerOptions.from_cad()
    assert w.dribbler_state("blue", 0) == (0.0, 0.0, False)
    _run_phase(w, 0.5, lambda t: RobotCmd(dribbler_rpm=9000.0))                 # clamped to the spec maximum
    speed, slide, touch = w.dribbler_state("blue", 0)
    assert speed == pytest.approx(w.dribbler_opt.speed_max(w.spec), rel=0.05)
    assert slide == pytest.approx(0.0, abs=1e-3)                                # at the (soft) forward stop
    assert not touch and not w.state().robots[("blue", 0)].has_ball
    w.teleport_robot("blue", 0, 0.5, 0.2, 1.0)
    assert w.dribbler_state("blue", 0)[0] == 0.0                                # teleport stops the bar
    w.close()
