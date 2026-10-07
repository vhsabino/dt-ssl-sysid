"""3D view: geometry (no Qt) + the pyqtgraph.opengl widget (requires_gui; GL parts skip without a context).

The GL tests run for real on a desktop (``QT_QPA_PLATFORM=windows``/``xcb``) or under ``xvfb-run``; with the
``offscreen`` platform ``QOpenGLWidget`` has no context and they are skipped (the widget must still build
and accept frames there, which is what the MainWindow tests exercise).
"""
from __future__ import annotations

import math
import os

import numpy as np
import pytest

from dtssl.gui import scene3d as S
from dtssl.physics.mjcf import WheelGeometry
from dtssl.sim.world import FieldGeometry, RobotSpec

WHEEL = WheelGeometry()


# ---------------------------------------------------------------- geometry (pure numpy)
def _euler_characteristic(m: S.Mesh) -> int:
    f = m.faces
    edges = {tuple(sorted((int(a), int(b)))) for tri in f for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0]))}
    return len(m.vertices) - len(edges) + len(f)


def test_parse_obj_handles_polygons_and_slashes():
    obj = "# c\nv 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nvn 0 0 1\nf 1/1/1 2/2/1 3/3/1 4/4/1\nf 1 2 3\n"
    m = S.parse_obj(obj)
    assert m.vertices.shape == (4, 3) and m.faces.shape == (3, 3)      # quad -> 2 triangles + 1
    assert m.faces.tolist() == [[0, 1, 2], [0, 2, 3], [0, 1, 2]]


def test_cad_meshes_match_the_physics_assets():
    chassis, wheel, meta = S.cad_meshes()
    assert chassis.n_faces == meta["chassis"]["faces"] and wheel.n_faces == meta["wheel"]["faces"]
    assert len({tuple(c) for c in chassis.colors}) == len(meta["chassis"]["materials"])   # Inventor colours
    lo, hi = chassis.bbox()
    assert hi[2] == pytest.approx(meta["chassis"]["z_top_above_axle"], abs=1e-6)
    assert 0.07 < hi[0] < 0.08 and lo[0] < -0.085                    # dribbler at +x
    r = np.hypot(wheel.vertices[:, 1], wheel.vertices[:, 2]).max()
    assert r == pytest.approx(meta["wheel"]["outer_radius"], abs=1e-6)


def test_mechanism_meshes_match_the_physics_assets():
    """Kicker and dribbler (Inventor assembly) share the chassis frame: the dribbler spans the mouth at the
    front (+x), the kicker lies on the body x axis behind it; the LOD pair is a decimation of the same parts."""
    meta = S.cad_meta()
    full, lod = S.mechanism_meshes(lod=False), S.mechanism_meshes(lod=True)
    assert set(full) == set(lod) == {"kicker", "dribbler"}
    for key in full:
        assert full[key].n_faces == meta[key]["faces"] and lod[key].n_faces == meta[f"{key}_lod"]["faces"]
        assert 2 * lod[key].n_faces < full[key].n_faces
        np.testing.assert_allclose(lod[key].bbox()[1], full[key].bbox()[1], atol=0.002)
    lo, hi = full["dribbler"].bbox()
    assert 0.07 < hi[0] < 0.085 and lo[0] > 0.04 and abs(hi[1] + lo[1]) < 0.004      # across the mouth, centred
    lo, hi = full["kicker"].bbox()
    assert hi[0] < 0.0765 and abs(hi[1] + lo[1]) < 0.002 and hi[1] - lo[1] < 0.06      # behind the front face
    assert all(m.bbox()[0][2] + WHEEL.r > 0.0 for m in full.values())                  # nothing below the floor


def test_primitive_meshes_are_closed_surfaces():
    for m in (S.d_prism_mesh(0.09, 0.075, 0.008, 0.15), S.cylinder_mesh(0.03, 0.009), S.cylinder_mesh_z(0.02, 0.001)):
        assert _euler_characteristic(m) == 2                          # genus 0: V - E + F = 2
        assert m.faces.min() == 0 and m.faces.max() == len(m.vertices) - 1


def test_id_plate_mesh_colours_follow_the_rulebook_pattern():
    m = S.id_plate_mesh("blue", 3, 0.15)
    assert m.colors is not None and len(m.colors) == m.n_faces
    cols = {tuple(np.round(c, 2)) for c in m.colors}
    assert len(cols) == 3                                             # team disc + pink + green
    assert m.vertices[:, 2].min() >= 0.15 - 1e-9                       # sits on top of the cover
    m2 = S.id_plate_mesh("yellow", 3 + 16, 0.15)
    np.testing.assert_allclose(m2.colors[-m.n_faces + 24 * 4:], m.colors[-m.n_faces + 24 * 4:])   # same dots
    assert not np.allclose(m2.colors[0], m.colors[0])                 # different team disc


def test_robot_meshes_build_all_variants():
    cad = S.RobotMeshes.build(WHEEL, RobotSpec(), cad=True, lod=False)
    lod = S.RobotMeshes.build(WHEEL, RobotSpec(), cad=True, lod=True)
    prim = S.RobotMeshes.build(WHEEL, RobotSpec(), cad=False)
    assert cad.cad and not cad.lod and cad.z_chassis == pytest.approx(WHEEL.r)
    assert 0.145 < cad.z_top <= 0.150                                  # id plate on the CAD decal plane
    assert cad.z_top == pytest.approx(WHEEL.r + S.cad_plate_z())
    assert lod.cad and lod.lod and lod.z_top == cad.z_top and lod.z_chassis == cad.z_chassis
    assert 3 * lod.chassis.n_faces < cad.chassis.n_faces and 3 * lod.wheel.n_faces < cad.wheel.n_faces
    assert not prim.cad and prim.z_chassis == 0.0 and prim.z_top == pytest.approx(RobotSpec().height)
    assert lod.chassis.n_faces > 10 * prim.chassis.n_faces
    assert set(cad.mechanisms) == set(lod.mechanisms) == {"kicker", "dribbler"} and prim.mechanisms == {}
    assert all(lod.mechanisms[k].n_faces < cad.mechanisms[k].n_faces for k in cad.mechanisms)
    for mesh in (cad.chassis, cad.wheel, lod.chassis, *cad.mechanisms.values()):   # CAD colours per face
        assert mesh.colors is not None and mesh.colors.shape == (mesh.n_faces, 4)
        assert len({tuple(np.round(c, 3)) for c in mesh.colors}) >= 3
    assert prim.chassis.colors is None


def test_robot_transform_maps_body_points_to_world():
    T = S.robot_transform(1.0, -2.0, math.pi / 2, z=0.03)
    p = T @ np.array([0.075, 0.0, 0.0, 1.0])                          # dribbler face
    np.testing.assert_allclose(p[:3], [1.0, -2.0 + 0.075, 0.03], atol=1e-12)


def test_wheel_transform_places_the_wheel_on_the_rim_with_its_axle_radial():
    x, y, th = 0.5, 0.2, 0.3
    for i, phi in enumerate(WHEEL.angles):
        T = S.wheel_transform(x, y, th, WHEEL, i, spin=1.0)
        centre = (T @ np.array([0.0, 0.0, 0.0, 1.0]))[:3]
        exp = [x + WHEEL.R * math.cos(th + phi), y + WHEEL.R * math.sin(th + phi), WHEEL.r]
        np.testing.assert_allclose(centre, exp, atol=1e-12)
        axle = (T @ np.array([1.0, 0.0, 0.0, 0.0]))[:3]                 # mesh +x -> outward radial u_r
        np.testing.assert_allclose(axle, [math.cos(th + phi), math.sin(th + phi), 0.0], atol=1e-12)


def test_wheel_spin_rolls_without_slip():
    """Contact point of every wheel is (to first order) stationary while the body moves: the spin sign and
    magnitude from the inverse kinematics match the wheel transform."""
    spin = S.WheelSpin(WHEEL)
    dt = 1e-4
    for vx, vy, w in ((1.0, 0.0, 0.0), (0.0, 0.7, 0.0), (0.0, 0.0, 2.0), (0.6, -0.3, 1.1)):
        spin.reset()
        th0 = 0.4
        a0 = spin.advance(("blue", 0), vx, vy, w, 0.0)
        # body pose after dt (world velocity from the body velocity)
        c, s = math.cos(th0), math.sin(th0)
        x1, y1, th1 = (c * vx - s * vy) * dt, (s * vx + c * vy) * dt, th0 + w * dt
        a1 = spin.advance(("blue", 0), vx, vy, w, dt)
        for i in range(4):
            bottom = np.array([0.0, 0.0, -WHEEL.r, 1.0])                  # contact point in the wheel mesh frame
            p0 = (S.wheel_transform(0.0, 0.0, th0, WHEEL, i, float(a0[i])) @ bottom)[:3]
            p1 = (S.wheel_transform(x1, y1, th1, WHEEL, i, float(a1[i])) @ bottom)[:3]
            v_contact = (p1 - p0) / dt
            # the roller axis lets the wheel slide freely along u_r: only the tangential component must vanish
            phi = float(WHEEL.angles[i]) + th0
            t = np.array([-math.sin(phi), math.cos(phi), 0.0])
            assert abs(v_contact @ t) < 5e-3, (vx, vy, w, i, v_contact @ t)


def test_wheel_spin_bookkeeping():
    spin = S.WheelSpin(WHEEL)
    a = spin.advance(("y", 1), 0.0, 0.0, 10.0, 1.0)
    assert np.all(a >= 0) and np.all(a < 2 * math.pi)
    np.testing.assert_allclose(spin.wheel_speeds(0.0, 0.0, 1.0), WHEEL.R / WHEEL.r)
    same = spin.advance(("y", 1), 5.0, 5.0, 5.0, 0.0)
    np.testing.assert_allclose(same, a)
    spin.reset()
    assert not spin.angles


def test_field_geometry_arrays():
    f = FieldGeometry()
    frame, inner = S.floor_quads(f)
    assert frame.shape == (16, 3) and inner.shape == (4, 3)
    L, W, b = f.half_length, f.half_width, f.boundary_width

    def area(q):
        return abs(q[1, 0] - q[0, 0]) * abs(q[2, 1] - q[1, 1])
    assert sum(area(frame[4 * k:4 * k + 4]) for k in range(4)) + area(inner) == pytest.approx(4 * (L + b) * (W + b))
    segs = S.field_segments(f)
    assert segs.shape[0] % 2 == 0 and np.all(segs[:, 2] == S.LINE_Z)
    assert np.abs(segs[:, 0]).max() == pytest.approx(L + f.goal_depth) and np.abs(segs[:, 1]).max() == pytest.approx(W)
    goals = S.goal_frames(f)
    assert goals.shape[0] % 2 == 0 and goals[:, 2].max() > 0.1
    q = S.quad_mesh(frame, S.BOUNDARY_RGBA)
    assert q.n_faces == 8 and q.colors.shape == (8, 4)


def test_compute_frame_hides_absent_robots_and_spins_wheels():
    meshes = S.RobotMeshes.build(WHEEL, RobotSpec(), cad=False)
    poses = {("blue", 0): S.RobotPose(0.0, 0.0, 0.0, vx=1.0), ("blue", 1): S.RobotPose(1.0, 1.0, 0.0, present=False)}
    spin = S.WheelSpin(WHEEL)
    fr0 = S.compute_frame(poses, (0.1, 0.2, 0.0), meshes, WHEEL, spin, 0.0)
    fr1 = S.compute_frame(poses, (0.1, 0.2, 0.0), meshes, WHEEL, spin, 1 / 60)
    assert fr1.hidden == {("blue", 1)} and set(fr1.chassis) == {("blue", 0)} and len(fr1.wheels[("blue", 0)]) == 4
    assert not np.allclose(fr0.wheels[("blue", 0)][0], fr1.wheels[("blue", 0)][0])   # the wheel turned
    np.testing.assert_allclose(fr1.chassis[("blue", 0)][:3, 3], [0.0, 0.0, meshes.z_chassis])
    frn = S.compute_frame(poses, (0.0, 0.0, 0.0), meshes, WHEEL, None, 1 / 60)
    np.testing.assert_allclose(frn.wheels[("blue", 0)][0], S.wheel_transform(0.0, 0.0, 0.0, WHEEL, 0, 0.0))


# ---------------------------------------------------------------- widget (requires_gui)
@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    pytest.importorskip("pyqtgraph")
    from PySide6 import QtCore, QtWidgets

    if QtWidgets.QApplication.instance() is None:       # GL resources shared between widgets (as in app.run)
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts, True)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(["dtssl-tests"])
    yield app


def _world(n_blue=2, n_yellow=1):
    from dtssl.sim.twin_world import TwinWorld

    return TwinWorld(plant="fopdt", n_blue=n_blue, n_yellow=n_yellow, watchdog_clock="sim")


def _pump(app, n=3):
    for _ in range(n):
        app.processEvents()


def test_arcball_point_maps_the_widget_to_the_unit_sphere():
    c = S.arcball_point(200, 150, 400, 300)
    np.testing.assert_allclose(c, [0.0, 0.0, 1.0])                       # centre: towards the viewer
    r = S.arcball_point(350, 150, 400, 300)                              # right edge of the sphere (radius 150 px)
    np.testing.assert_allclose(r, [1.0, 0.0, 0.0], atol=1e-12)
    u = S.arcball_point(200, 75, 400, 300)                               # up = -y pixels
    assert u[1] > 0 and u[2] > 0 and np.linalg.norm(u) == pytest.approx(1.0)
    out = S.arcball_point(0, 0, 400, 300)                                # outside: projected on the rim
    assert np.linalg.norm(out) == pytest.approx(1.0) and out[2] == 0.0


def test_axis_angle_and_rotation_between_are_proper_rotations():
    T = S.axis_angle((0.0, 0.0, 2.0), math.pi / 2)
    np.testing.assert_allclose(T[:3, :3] @ [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], atol=1e-12)
    np.testing.assert_allclose(S.axis_angle((0.0, 0.0, 0.0), 1.0), np.eye(4))
    R = S.rotation_between([1.0, 0.0, 0.0], [0.0, 1.0, 0.0])
    np.testing.assert_allclose(R[:3, :3] @ [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], atol=1e-12)
    np.testing.assert_allclose(R[:3, :3] @ R[:3, :3].T, np.eye(3), atol=1e-12)
    assert np.linalg.det(R[:3, :3]) == pytest.approx(1.0)
    np.testing.assert_allclose(S.rotation_between([0, 0, 1], [0, 0, 1]), np.eye(4))


def test_arcball_drag_turns_the_part_about_the_screen_axis():
    ab = S.Arcball(centre=(0.0, 0.0, 0.07))
    assert not ab.dragging and not ab.drag(0, 0, 400, 300, [1, 0, 0], [0, 0, 1], [0, -1, 0])
    # camera at -y looking at +y: right = +x, up = +z, toward = -y; a horizontal drag to the right turns the
    # part about the screen "up" axis (= world z), positive (counter-clockwise seen from above)
    ab.begin(200, 150, 400, 300)
    assert ab.dragging
    assert ab.drag(200 + 150 * math.sin(math.radians(30)), 150, 400, 300, [1, 0, 0], [0, 0, 1], [0, -1, 0])
    ab.end()
    Rz = S.axis_angle((0, 0, 1), math.radians(30))
    np.testing.assert_allclose(ab.R, Rz, atol=1e-9)
    # the transform rotates about the centre: the centre itself does not move
    T = ab.transform()
    np.testing.assert_allclose(T @ [0.0, 0.0, 0.07, 1.0], [0.0, 0.0, 0.07, 1.0], atol=1e-12)
    p = T @ [0.1, 0.0, 0.07, 1.0]
    np.testing.assert_allclose(p[:2], [0.1 * math.cos(math.radians(30)), 0.1 * math.sin(math.radians(30))], atol=1e-9)
    ab.spin((0, 0, 1), -math.radians(30))
    np.testing.assert_allclose(ab.R, np.eye(4), atol=1e-9)
    ab.reset()
    np.testing.assert_allclose(ab.transform(), np.eye(4))


def test_wheel_angles_integrate_the_record_speeds():
    wa = S.WheelAngles(4)
    np.testing.assert_allclose(wa.advance(1.0, (10.0, -10.0, 0.0, 1.0)), 0.0)         # first sample: no dt
    a = wa.advance(1.1, (10.0, -10.0, 0.0, 1.0))
    np.testing.assert_allclose(a, [1.0, 2 * math.pi - 1.0, 0.0, 0.1], atol=1e-9)
    np.testing.assert_allclose(wa.advance(1.0, (10.0,) * 4), a)                       # not monotonic: ignored
    np.testing.assert_allclose(wa.advance(1.1, None), a)                              # no speeds: hold
    wa.reset()
    np.testing.assert_allclose(wa.angles, 0.0)


def test_robot_part_transforms_and_arrow_segments():
    meshes = S.RobotMeshes.build(WHEEL, RobotSpec(), cad=False)
    T = S.axis_angle((0, 0, 1), math.pi / 2)
    ch, wh, body = S.robot_part_transforms(T, meshes, WHEEL, [0.0, 0.0, 0.0, 0.0])
    np.testing.assert_allclose(body, T)
    np.testing.assert_allclose(ch, T @ S.translate(0.0, 0.0, meshes.z_chassis))
    assert len(wh) == 4
    phi = float(WHEEL.angles[0])
    c = wh[0] @ [0.0, 0.0, 0.0, 1.0]                                                   # wheel 0 centre, turned by T
    np.testing.assert_allclose(c[:3], [-WHEEL.R * math.sin(phi), WHEEL.R * math.cos(phi), WHEEL.r], atol=1e-12)
    segs = S.arrow_segments(1.0, 0.0, 0.2, 0.1)
    assert segs.shape == (6, 3) and segs[1].tolist() == [0.1, 0.0, 0.2]
    assert S.arrow_segments(0.0, 0.0, 0.2, 0.1).shape == (0, 3)


@pytest.mark.requires_gui
def test_view3d_builds_and_accepts_frames_without_a_context(qapp):
    from dtssl.gui.view3d import View3D

    w = _world()
    v = View3D(w.field, spec=w.spec)
    assert v.available, v.error
    v.show()
    _pump(qapp)
    ws = w.step()
    v.update_state(ws, ("blue", 0), ws.t)
    assert v.frames == 1 and len(v._robots) == 3
    v.hide()
    _pump(qapp)
    v.update_state(w.step(), ("blue", 0))
    assert v.frames == 1                                              # hidden tab: no work
    v.show()
    _pump(qapp)                                                       # showEvent re-applies the last state
    assert v.frames == 2
    v.set_hq(True)
    assert v.hq and v.frames == 3 and not v._meshes.lod                 # rebuild re-applied the last state
    v.set_cad(False)
    v.update_state(w.step(), None)
    assert not v.cad and v.frames == 5                                 # rebuild forced one update + this one
    v.set_field(FieldGeometry(length=12.0, width=9.0))
    assert v.field.length == 12.0
    v.close()


@pytest.mark.requires_gui
def test_view3d_camera_presets_and_follow(qapp):
    from dtssl.gui.view3d import View3D

    w = _world()
    v = View3D(w.field, spec=w.spec)
    ws = w.step()
    v.update_state(ws, ("yellow", 0), ws.t, force=True)
    for name, (el, az, dist) in S.CAMERA_PRESETS.items():
        v.set_preset(name)
        cam = v.camera()
        assert (cam["elevation"], cam["azimuth"], cam["distance"]) == (el, az, dist)
    w.teleport_robot("yellow", 0, 2.0, -1.5, 0.0)
    v.set_follow(True)
    v.update_state(w.step(), ("yellow", 0), force=True)
    c = v.camera()["center"]
    assert (c.x(), c.y()) == pytest.approx((2.0, -1.5), abs=1e-6)
    v.fit()
    assert not v.follow and v.camera()["center"].x() == 0.0
    v.close()


@pytest.mark.requires_gui
def test_view3d_renders_the_scene_when_a_context_exists(qapp):
    from dtssl.gui.view3d import View3D

    w = _world(6, 6)
    v = View3D(w.field, spec=w.spec)
    v.resize(640, 480)
    v.show()
    _pump(qapp)
    ws = w.step()
    v.update_state(ws, ("blue", 0), ws.t, force=True)
    _pump(qapp)
    img = v.grab_image()
    if img is None:
        pytest.skip("no OpenGL context on this Qt platform (offscreen); run under xvfb or on a desktop")
    from pyqtgraph import functions as fn

    arr = fn.imageToArray(img, copy=True, transpose=False)[..., :3]
    assert arr.std() > 10.0                                           # not a blank frame
    green = (arr[..., 1] > arr[..., 0] + 20) & (arr[..., 1] > arr[..., 2] + 20)
    assert 0.2 < green.mean() < 0.95                                  # the field is drawn, robots on it
    v.set_preset("top")
    _pump(qapp)
    img2 = v.grab_image()
    arr2 = fn.imageToArray(img2, copy=True, transpose=False)[..., :3]
    assert not np.array_equal(arr, arr2)
    v.close()


@pytest.mark.requires_gui
def test_mainwindow_has_the_3d_tab(qapp):
    from dtssl.gui.app import MainWindow

    win = MainWindow(backend="fopdt", mode="debug", team="yellow", n_blue=1, n_yellow=1, use_pygame=False,
                     autostart=False)
    try:
        assert win.tabs.count() == 3 and win.view3d is not None and win.tabs.widget(1) is win.view3d   # 2D, 3D, Robot
        assert win.view3d.selected == win.controller.selected == ("yellow", 0)
        win.controller.select(("blue", 0))
        assert win.view3d.selected == ("blue", 0)
        win.tabs.setCurrentWidget(win.view3d)
        win.fit_current_view()
        assert win.view3d.camera()["center"].x() == 0.0
    finally:
        win.close()
    win2 = MainWindow(backend="fopdt", mode="debug", team="yellow", n_blue=1, n_yellow=1, use_pygame=False,
                      autostart=False, view3d=False)
    try:
        assert win2.tabs.count() == 2 and win2.view3d is None                                          # 2D, Robot
        win2.fit_current_view()
    finally:
        win2.close()
