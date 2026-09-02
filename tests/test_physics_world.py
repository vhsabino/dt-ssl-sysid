"""MuJoCoWorld (routes a/b): plant fidelity, contacts, kick/dribbler, kinematics, registry."""
from __future__ import annotations

import math

import numpy as np
import pytest

pytestmark = pytest.mark.requires_mujoco

from dtssl.models import AnalyticFOPDTPlant, load_twin_params  # noqa: E402
from dtssl.sim.entities import BallState, RobotCmd, RobotSpawn, Scene  # noqa: E402

TS = 1.0 / 60.0


def _world(route, robots, ball=None, **kw):
    from dtssl.physics.mujoco_world import MuJoCoWorld

    scene = Scene(robots=robots, ball=ball or BallState(x=3.0, y=2.0))
    return MuJoCoWorld(route, scene=scene, watchdog_clock="sim", **kw)


def _drive(world, key, cmd, n):
    ws = None
    for _ in range(n):
        world.set_command(*key, RobotCmd(*cmd) if isinstance(cmd, tuple) else cmd)
        ws = world.step()
    return ws


def _ang(a):
    return math.atan2(math.sin(a), math.cos(a))


# ============================================================ (i) route a follows the plant
@pytest.mark.parametrize("cmd", [(1.0, 0.5, 1.0), (0.0, 0.0, 5.0), (-1.0, 0.5, -2.0), (2.0, 1.0, 3.0)])
def test_route_a_tracks_standalone_plant(cmd, capsys):
    """No contacts: chassis pose vs AnalyticFOPDTPlant over 3 s -> < 2 mm, < 0.01 rad (achieved
    0.14 mm / 0 rad for (1, 0.5, 1); 1.5 mm for (2, 1, 3) where the 150 N limit clips the first jumps)."""
    pose0 = (-3.0, -1.0, 0.3)
    w = _world("a", [RobotSpawn("blue", 0, *pose0)])
    plant = AnalyticFOPDTPlant(load_twin_params())
    plant.reset(pose0)
    plant.prime_delay([])
    worst_pos = worst_ang = 0.0
    for _ in range(int(round(3.0 / TS))):
        w.set_command("blue", 0, RobotCmd(*cmd))
        r = w.step().robots[("blue", 0)]
        x, y, th = plant.step(cmd, TS)
        worst_pos = max(worst_pos, math.hypot(r.x - x, r.y - y))
        worst_ang = max(worst_ang, abs(_ang(r.theta - th)))
    with capsys.disabled():
        print(f"\n  route a vs plant cmd={cmd}: max e_pos={worst_pos * 1e3:.3f} mm, max e_ang={worst_ang:.5f} rad")
    assert worst_pos < 2e-3
    assert worst_ang < 0.01
    # body velocity reported by the world ~ the plant's (MuJoCo holds the interval-mean world
    # velocity, rotated back with the end-of-interval heading: ~1 % apart at w = 1-3 rad/s)
    vb = plant.body_velocity
    assert np.allclose([r.vx_b, r.vy_b, r.w], vb, rtol=0.03, atol=5e-3)


def test_route_a_exact_when_unclamped():
    """Dead-beat servo without force limits reproduces the plant to numerical precision."""
    from dtssl.physics.mjcf import RouteAOptions

    pose0 = (0.0, 0.0, 0.0)
    w = _world("a", [RobotSpawn("blue", 0, *pose0)], route_a=RouteAOptions(force_max=None, torque_max=None))
    plant = AnalyticFOPDTPlant(load_twin_params())
    plant.reset(pose0)
    plant.prime_delay([])
    worst = 0.0
    for _ in range(120):
        w.set_command("blue", 0, RobotCmd(1.5, -0.5, 2.0))
        r = w.step().robots[("blue", 0)]
        x, y, th = plant.step((1.5, -0.5, 2.0), TS)
        worst = max(worst, math.hypot(r.x - x, r.y - y), abs(_ang(r.theta - th)))
    assert worst < 1e-6


# ============================================================ (ii) ball, contacts, walls
@pytest.mark.parametrize("route", ["a", "b"])
def test_kick_moves_ball_along_heading_and_decelerates(route):
    th = 0.5
    d = 0.075 + 0.0215
    w = _world(route, [RobotSpawn("blue", 0, 0.0, 0.0, th)], BallState(x=d * math.cos(th), y=d * math.sin(th)))
    ws = w.step()
    assert ws.robots[("blue", 0)].has_ball
    w.set_command("blue", 0, RobotCmd(kick_speed=3.0))
    speeds, dirs = [], []
    for _ in range(120):
        b = w.step().ball
        speeds.append(math.hypot(b.vx, b.vy))
        dirs.append(math.atan2(b.vy, b.vx))
    assert w.kicks == 1
    assert 2.5 < speeds[0] <= 3.0
    assert all(abs(_ang(a - th)) < 0.02 for a in dirs)                    # along the heading
    assert speeds[30] < speeds[0] and speeds[119] < speeds[30] > 0.5         # decelerates (two phases)
    assert not w.step().robots[("blue", 0)].has_ball


def test_chip_kick_leaves_the_floor():
    d = 0.075 + 0.0215
    w = _world("a", [RobotSpawn("blue", 0, 0.0, 0.0, 0.0)], BallState(x=d, y=0.0))
    w.step()
    w.set_command("blue", 0, RobotCmd(kick_speed=3.0, kick_angle_deg=45.0))
    zmax = max(w.step().ball.z for _ in range(90))
    assert 0.15 < zmax < 0.30                                               # v^2 sin^2(45) / 2g = 0.229


@pytest.mark.parametrize("route", ["a", "b"])
def test_robot_pushes_ball_without_passing_through(route):
    w = _world(route, [RobotSpawn("blue", 0, 0.0, 0.0, 0.0)], BallState(x=0.3, y=0.0))
    ws = _drive(w, ("blue", 0), (0.5, 0.0, 0.0), 120)
    r, b = ws.robots[("blue", 0)], ws.ball
    assert r.x > 0.8                                                        # robot kept moving
    assert b.x - r.x >= 0.075 + 0.0215 - 0.003                              # ball stays on the flat face
    assert b.vx > 0.3                                                       # ball being pushed
    assert r.has_ball


@pytest.mark.parametrize("route", ["a", "b"])
def test_robot_cannot_pass_through_boundary_wall(route):
    w = _world(route, [RobotSpawn("blue", 0, 4.0, 2.0, 0.0)])
    xs = [_drive(w, ("blue", 0), (1.0, 0.0, 0.0), 1).robots[("blue", 0)].x for _ in range(180)]
    limit = w.field.half_length + w.field.boundary_width - w.spec.dribbler_offset   # flat front face
    assert max(xs) < limit + 0.01
    assert max(xs) > limit - 0.02                                           # it did reach the wall
    assert w.contacts > 0


def test_robots_collide_head_on():
    w = _world("a", [RobotSpawn("blue", 0, -0.5, 0.0, 0.0), RobotSpawn("yellow", 0, 0.5, 0.0, math.pi)])
    for _ in range(120):
        w.set_command("blue", 0, RobotCmd(vx=1.0))
        w.set_command("yellow", 0, RobotCmd(vx=1.0))
        ws = w.step()
    a, b = ws.robots[("blue", 0)], ws.robots[("yellow", 0)]
    assert b.x - a.x >= 2 * w.spec.dribbler_offset - 0.005                 # flat faces touch, no overlap
    assert abs(a.x + b.x) < 0.02                                            # symmetric


@pytest.mark.parametrize("route", ["a", "b"])
def test_dribbler_holds_ball_while_reversing(route):
    w = _world(route, [RobotSpawn("blue", 0, 0.0, 0.0, 0.0)], BallState(x=0.11, y=0.01))
    ws = _drive(w, ("blue", 0), RobotCmd(dribbler_rpm=6000.0), 60)
    assert ws.robots[("blue", 0)].has_ball
    ws = _drive(w, ("blue", 0), RobotCmd(vx=-0.3, w=0.5, dribbler_rpm=6000.0), 120)
    r, b = ws.robots[("blue", 0)], ws.ball
    assert r.has_ball
    assert abs(math.hypot(b.x - r.x, b.y - r.y) - (0.075 + 0.0215)) < 0.01
    assert r.x < -0.3                                                       # the robot really moved


# ============================================================ (iii) route b kinematics
def test_route_b_forward_distance_and_drift(capsys):
    w = _world("b", [RobotSpawn("blue", 0, -1.0, 0.0, 0.0)])
    ws = _drive(w, ("blue", 0), (0.5, 0.0, 0.0), 120)
    r = ws.robots[("blue", 0)]
    dist = r.x + 1.0
    with capsys.disabled():
        print(f"\n  route b vx=0.5 for 2 s: dist={dist:.4f} m ({(dist / 1.0 - 1) * 100:+.1f} %), "
              f"lateral={r.y * 1e3:+.2f} mm, heading={r.theta:+.4f} rad, v_ss={r.vx_b:.3f} m/s")
    assert abs(dist - 1.0) < 0.05                                           # +-5 % of the integrated command
    assert abs(r.y) < 0.05                                                  # lateral drift
    assert abs(r.theta) < 0.05
    assert abs(r.vx_b - 0.5) < 0.03                                          # steady state within 6 %


@pytest.mark.parametrize("wcmd", [1.0, -2.0])
def test_route_b_rotation_direction(wcmd):
    w = _world("b", [RobotSpawn("blue", 0, 0.0, 0.0, 0.0)])
    ws = _drive(w, ("blue", 0), (0.0, 0.0, wcmd), 60)
    r = ws.robots[("blue", 0)]
    assert math.copysign(1.0, r.theta) == math.copysign(1.0, wcmd)
    assert abs(r.theta) > 0.6 * abs(wcmd)                                   # ~1 s minus the start
    assert abs(r.w - wcmd) < 0.15 * abs(wcmd)
    assert math.hypot(r.x, r.y) < 0.02                                      # spins in place


def test_route_b_wheel_speeds_follow_inverse_kinematics():
    from dtssl.physics.mjcf import body_to_wheels

    w = _world("b", [RobotSpawn("blue", 0, 0.0, 0.0, 0.0)])
    _drive(w, ("blue", 0), (0.4, 0.2, 0.5), 90)
    target = body_to_wheels(0.4, 0.2, 0.5, w.wheel)
    assert np.allclose(w.wheel_speeds("blue", 0), target, atol=1.0)          # rad/s (targets ~10-15)


def test_route_b_deadzone_zeroes_small_wheel_commands():
    w = _world("b", [RobotSpawn("blue", 0, 0.0, 0.0, 0.0)], deadzone=True)
    ws = _drive(w, ("blue", 0), (0.0, 0.0, 0.3), 60)                         # 0.3 * R / r = 0.81 < 1.567
    assert np.all(w.robots[("blue", 0)].wheel_target == 0.0)
    assert abs(ws.robots[("blue", 0)].theta) < 1e-3


def test_route_b_pi_mode_runs():
    w = _world("b", [RobotSpawn("blue", 0, 0.0, 0.0, 0.0)], wheel_control="pi")
    ws = _drive(w, ("blue", 0), (0.5, 0.0, 0.0), 60)
    r = ws.robots[("blue", 0)]
    assert np.isfinite(w.data.qpos).all() and r.x > 0.05                    # moves forward, no NaN


# ============================================================ (iv) registry / World API
@pytest.mark.parametrize("name", ["mujoco-velocity", "mujoco-rollers"])
def test_registry_state_teleport(name):
    from dtssl.sim.backends import available, make_world

    assert name in available()
    w = make_world(name, n_blue=2, n_yellow=1, watchdog_clock="sim")
    ws = w.step()
    assert set(ws.robots) == {("blue", 0), ("blue", 1), ("yellow", 0)}
    assert ws.frame == 1 and ws.t == pytest.approx(TS)
    for r in ws.robots.values():
        assert r.present and abs(r.theta) <= math.pi
    assert ws.ball.z == pytest.approx(0.0, abs=1e-3)
    w.teleport_robot("blue", 1, 1.0, -1.0, 2.0)
    w.teleport_ball(0.5, 0.25, vx=1.0)
    ws = w.step()
    r = ws.robots[("blue", 1)]
    assert abs(r.x - 1.0) < 1e-2 and abs(r.y + 1.0) < 1e-2 and abs(r.theta - 2.0) < 1e-2
    assert abs(ws.ball.x - (0.5 + TS)) < 5e-3 and ws.ball.vx > 0.9
    w.teleport_robot("yellow", 0, 0.0, 0.0, 0.0, present=False)
    ws = w.step()
    assert not ws.robots[("yellow", 0)].present and ws.robots_of("yellow") == []
    w.set_present("yellow", 0, True)
    assert w.step().robots[("yellow", 0)].present
    assert w.field.length == 9.0 and w.spec.radius == 0.09
    w.close()


def test_watchdog_zeroes_stale_command():
    w = _world("a", [RobotSpawn("blue", 0, 0.0, 0.0, 0.0)])
    w.set_command("blue", 0, RobotCmd(vx=1.0))
    for _ in range(12):
        w.step()
    assert w.state().robots[("blue", 0)].vx_b > 0.2
    for _ in range(60):
        ws = w.step()
    assert w.watchdog_hits == 1
    assert abs(ws.robots[("blue", 0)].vx_b) < 0.02


def test_set_plant_params_hot_swap():
    from dtssl.models import DofParam

    w = _world("a", [RobotSpawn("blue", 0, 0.0, 0.0, 0.0)])
    fast = {d: DofParam(K=1.0, tau=0.01, Td=0.0) for d in ("vx", "vy", "w")}
    w.set_plant_params(fast)
    ws = _drive(w, ("blue", 0), (1.0, 0.0, 0.0), 30)
    assert abs(ws.robots[("blue", 0)].vx_b - 1.0) < 0.02                    # K=1, no delay, tiny lag


def test_step_dt_is_exact_and_substeps_rescale():
    w = _world("a", [RobotSpawn("blue", 0, 0.0, 0.0, 0.0)])
    assert w.substeps() == 8
    ws = w.step(0.01)
    assert ws.t == pytest.approx(0.01) and w.model.opt.timestep == pytest.approx(0.002)
    ws = w.step()
    assert ws.t == pytest.approx(0.01 + TS)
    assert w.model.opt.timestep == pytest.approx(TS / 8)


def test_route_a_generated_xml_matches_world():
    from dtssl.physics.mjcf import build_world_xml

    scene = Scene.default(1, 1)
    w = _world("a", scene.robots)
    assert w.xml.startswith("<mujoco") and w.model.nu == 6
    assert len(build_world_xml(scene, "a")) > 1000
