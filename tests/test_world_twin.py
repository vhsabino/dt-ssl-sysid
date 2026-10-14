"""TwinWorld: plant fidelity (bit-identical), watchdog, saturation/deadzone, contacts, teleports."""
from __future__ import annotations

import math

import numpy as np
import pytest

from dtssl.models import AnalyticFOPDTPlant, DofParam, IdealKinematicPlant, load_twin_params, wrap_to_pi
from dtssl.sim.backends import available, make_world
from dtssl.sim.collisions import GOAL_WALL_THICKNESS, clamp_to_goals, goal_segments
from dtssl.sim.entities import ACTIVE_ROBOTS, ROSTER_SIZE, BallState, RobotCmd, RobotSpawn, Scene, park_spot
from dtssl.sim.twin_world import (
    R_CONTACT,
    WHEEL_RADIUS,
    TwinWorld,
    apply_body_deadzone,
    body_to_wheels,
    load_field_geometry,
    load_robot_spec,
    saturate_body,
    wheels_to_body,
)
from dtssl.sim.world import World


def _cmds(n: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.uniform([-2.0, -2.0, -6.0], [2.0, 2.0, 6.0], size=(n, 3))


def test_backends_registered_and_world_abc():
    assert {"fopdt", "ideal"} <= set(available())
    w = make_world("fopdt", n_blue=2, n_yellow=1)
    assert isinstance(w, World) and isinstance(w, TwinWorld)
    assert w.name == "TwinWorld[fopdt]"
    assert sorted(w.plants) == [("blue", 0), ("blue", 1), ("yellow", 0)]
    assert all(isinstance(p, AnalyticFOPDTPlant) for p in w.plants.values())
    wi = make_world("ideal", n_blue=1, n_yellow=0)
    assert isinstance(wi.plants[("blue", 0)], IdealKinematicPlant)
    assert w.field.length == 9.0 and w.field.boundary_width == 0.3
    assert w.spec.radius == 0.09 and w.spec.watchdog_s == 0.3


def test_config_loaders_map_field_keys():
    f = load_field_geometry()
    assert (f.length, f.width, f.goal_width) == (9.0, 6.0, 1.0)
    s = load_robot_spec()
    assert s.kick_flat_max == 6.5 and s.a_max is None


def test_fopdt_world_reproduces_plant_bit_for_bit():
    params = load_twin_params()
    pose0 = (0.3, -0.4, 0.8)
    ref = AnalyticFOPDTPlant(params)
    ref.reset(pose0)
    ref.prime_delay([])
    scene = Scene(robots=[RobotSpawn("blue", 0, *pose0)], ball=BallState(x=3.0, y=2.0))
    w = TwinWorld("fopdt", params=params, scene=scene)
    for c in _cmds(300):
        w.set_command("blue", 0, RobotCmd(vx=c[0], vy=c[1], w=c[2]))
        ws = w.step()
        pr = ref.step(tuple(c), w.ts)
        pw = w.plants[("blue", 0)].pose
        assert pw == pr                                             # exact equality
        r = ws.robots[("blue", 0)]
        assert (r.x, r.y) == (pr[0], pr[1]) and r.theta == wrap_to_pi(pr[2])
        assert (r.vx_b, r.vy_b, r.w) == tuple(ref.body_velocity)


def test_ideal_world_reproduces_ideal_plant():
    ref = IdealKinematicPlant()
    ref.reset((0.0, 0.0, 0.0))
    w = TwinWorld("ideal", scene=Scene(robots=[RobotSpawn("yellow", 5, 0.0, 0.0, 0.0)], ball=BallState(x=2.0)))
    for c in _cmds(120, seed=1):
        w.set_command("yellow", 5, RobotCmd(vx=c[0], vy=c[1], w=c[2]))
        w.step()
        assert w.plants[("yellow", 5)].pose == ref.step(tuple(c), w.ts)


def test_state_theta_is_wrapped():
    w = TwinWorld("ideal", scene=Scene(robots=[RobotSpawn("blue", 0, 0.0, 0.0, 0.0)], ball=BallState(x=2.0)))
    w.set_command("blue", 0, RobotCmd(w=6.0))
    for _ in range(120):
        ws = w.step()
    assert w.plants[("blue", 0)].pose[2] > math.pi                 # unwrapped internally
    assert -math.pi < ws.robots[("blue", 0)].theta <= math.pi


def test_watchdog_zeroes_command_after_timeout():
    w = TwinWorld("ideal", n_blue=1, n_yellow=0, watchdog_s=0.3, watchdog_clock="sim")
    w.set_command("blue", 0, RobotCmd(vx=1.0, dribbler_rpm=6000.0))
    x_prev = w.state().robots[("blue", 0)].x
    moved = 0
    for _ in range(int(0.3 * 60) + 1):                              # up to and including the timeout
        x = w.step().robots[("blue", 0)].x
        moved += x > x_prev
        x_prev = x
    assert moved >= 18
    assert w.watchdog_hits == 0
    ws = w.step()                                                   # first frame past the watchdog
    assert w.watchdog_hits == 1
    assert w.commands[("blue", 0)].vx == 0.0 and w.commands[("blue", 0)].dribbler_rpm == 0.0
    assert ws.robots[("blue", 0)].vx_b == 0.0
    x_stop = ws.robots[("blue", 0)].x
    for _ in range(10):
        ws = w.step()
    assert ws.robots[("blue", 0)].x == x_stop and w.watchdog_hits == 1
    # a new command re-arms it
    w.set_command("blue", 0, RobotCmd(vx=1.0))
    assert w.step().robots[("blue", 0)].x > x_stop


def test_watchdog_uses_wall_clock_by_default(monkeypatch):
    w = TwinWorld("ideal", n_blue=1, n_yellow=0, watchdog_s=0.3)
    now = [1000.0]
    monkeypatch.setattr("dtssl.sim.twin_world.time.monotonic", lambda: now[0])
    w.set_command("blue", 0, RobotCmd(vx=1.0))
    assert w.commands[("blue", 0)].t_recv == 1000.0
    now[0] += 0.2
    assert w.step().robots[("blue", 0)].vx_b == 1.0
    now[0] += 0.2
    assert w.step().robots[("blue", 0)].vx_b == 0.0 and w.watchdog_hits == 1


def test_saturation_and_deadzone_are_off_by_default_and_optional():
    assert saturate_body(4.0, 3.0, 20.0, 3.0, 10.0) == pytest.approx((2.4, 1.8, 10.0))
    w = TwinWorld("ideal", n_blue=1, n_yellow=0)
    w.set_command("blue", 0, RobotCmd(vx=5.0))
    assert w.step().robots[("blue", 0)].vx_b == 5.0                 # no saturation (published model)
    ws = TwinWorld("ideal", n_blue=1, n_yellow=0, saturate=True)
    ws.set_command("blue", 0, RobotCmd(vx=5.0, w=20.0))
    r = ws.step().robots[("blue", 0)]
    assert r.vx_b == pytest.approx(3.0) and r.w == pytest.approx(10.0)
    # per-wheel deadzone: |w| = 0.5 rad/s -> wheels at 0.5*R/r = 1.35 < 1.567 -> zeroed
    assert apply_body_deadzone(0.0, 0.0, 0.5) == pytest.approx((0.0, 0.0, 0.0))
    assert apply_body_deadzone(0.0, 0.0, 1.0) == pytest.approx((0.0, 0.0, 1.0))
    wd = TwinWorld("ideal", n_blue=1, n_yellow=0, deadzone=True)
    wd.set_command("blue", 0, RobotCmd(w=0.5))
    assert wd.step().robots[("blue", 0)].w == 0.0
    wd.set_command("blue", 0, RobotCmd(w=1.0))
    assert wd.step().robots[("blue", 0)].w == pytest.approx(1.0)


def test_wheel_kinematics_convention():
    wheels = body_to_wheels(0.0, 0.0, 1.0)
    assert np.allclose(wheels, R_CONTACT / WHEEL_RADIUS)
    v = (0.3, -0.2, 0.7)
    assert np.allclose(wheels_to_body(body_to_wheels(*v)), v)
    # vx forward: wheel 0 (60 deg) turns backwards (-sin 60), wheel 3 (300 deg) forwards
    w = body_to_wheels(1.0, 0.0, 0.0)
    assert w[0] < 0 < w[3] and np.isclose(w[0], -w[3])


def test_robot_wall_clamp():
    f = load_field_geometry()
    w = TwinWorld("ideal", scene=Scene(robots=[RobotSpawn("blue", 0, 4.0, 2.5, 0.0)], ball=BallState(x=-2.0)))
    w.set_command("blue", 0, RobotCmd(vx=3.0, vy=3.0))
    for _ in range(120):
        ws = w.step()
    r = ws.robots[("blue", 0)]
    assert r.x == pytest.approx(f.half_length + f.boundary_width - w.spec.radius)
    assert r.y == pytest.approx(f.half_width + f.boundary_width - w.spec.radius)
    assert w.plants[("blue", 0)].pose[0] == r.x                     # plant pose patched in place


def test_robot_robot_push_out_is_symmetric():
    scene = Scene(robots=[RobotSpawn("blue", 0, -0.5, 0.0, 0.0), RobotSpawn("yellow", 0, 0.5, 0.0, math.pi)],
                  ball=BallState(x=0.0, y=2.0))
    w = TwinWorld("ideal", scene=scene)
    w.set_command("blue", 0, RobotCmd(vx=1.0))
    w.set_command("yellow", 0, RobotCmd(vx=1.0))
    for _ in range(90):
        ws = w.step()
    b, y = ws.robots[("blue", 0)], ws.robots[("yellow", 0)]
    assert math.hypot(y.x - b.x, y.y - b.y) >= 2 * w.spec.radius - 1e-9
    assert math.hypot(y.x - b.x, y.y - b.y) == pytest.approx(2 * w.spec.radius, abs=1e-6)
    assert b.x == pytest.approx(-y.x, abs=1e-9)                     # symmetric about the origin
    assert w.contacts > 0


def test_absent_robot_is_parked_outside_not_simulated_nor_published():
    w = TwinWorld("ideal", n_blue=2, n_yellow=0)
    f = w.field
    w.set_present("blue", 1, False)
    w.set_command("blue", 1, RobotCmd(vx=1.0))
    spot = w.park_spot("blue", 1)
    assert tuple(w.plants[("blue", 1)].pose) == spot                 # parked at its spot outside the walls
    assert spot[1] < -(f.half_width + f.boundary_width) and spot[0] < 0.0 and spot[2] == pytest.approx(math.pi / 2)
    ws = w.step()
    r = ws.robots[("blue", 1)]
    assert not r.present and (r.x, r.y) == spot[:2] and r.vx_b == 0.0   # reported, not stepped
    assert [r.id for r in ws.robots_of("blue")] == [0]
    w.set_present("blue", 1, True)                                      # back in: just inside the nearest wall
    r = w.state().robots[("blue", 1)]
    assert r.present and r.x == pytest.approx(spot[0]) and r.y == pytest.approx(-(f.half_width + f.boundary_width
                                                                                   - w.spec.radius))
    assert w.step().robots[("blue", 1)].y > r.y                         # and the pending command drives it (+y)
    w.teleport_robot("blue", 1, 1.0, 1.0, 0.0, present=False)           # a teleport out ignores the coordinates
    assert tuple(w.plants[("blue", 1)].pose) == spot and not w.is_present("blue", 1)
    w.teleport_robot("blue", 1, 1.0, 1.0, 0.0, present=True)
    assert w.step().robots[("blue", 1)].present


def test_default_roster_parks_the_substitutes_outside_the_walls():
    w = TwinWorld("ideal", n_blue=ROSTER_SIZE, n_yellow=ROSTER_SIZE, n_active=ACTIVE_ROBOTS)
    ws = w.step()
    f = w.field
    on, off = [k for k, r in ws.robots.items() if r.present], [k for k, r in ws.robots.items() if not r.present]
    assert len(on) == 2 * ACTIVE_ROBOTS and len(off) == 2 * (ROSTER_SIZE - ACTIVE_ROBOTS)
    assert all(rid < ACTIVE_ROBOTS for _, rid in on) and all(rid >= ACTIVE_ROBOTS for _, rid in off)
    pts = [(ws.robots[k].x, ws.robots[k].y) for k in ws.robots]
    for i in range(len(pts)):                                             # nobody overlaps anybody
        for j in range(i + 1, len(pts)):
            assert math.hypot(pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]) >= 2 * w.spec.radius - 1e-9
    for k in on:
        assert abs(ws.robots[k].x) < f.half_length and abs(ws.robots[k].y) < f.half_width
    for k in off:
        r = ws.robots[k]
        assert r.y + w.spec.radius < -(f.half_width + f.boundary_width)   # fully beyond the -y wall
        assert abs(r.x) < f.half_length and (r.x < 0) == (k[0] == "blue") # bench on the team's own half
        assert (r.x, r.y, r.theta) == pytest.approx(park_spot(k[0], k[1], f.length, f.width, f.boundary_width))
    assert Scene.default(3, 2) == Scene.default(3, 2, n_active=None)         # no roster: everybody on the field


def test_goal_walls_stop_robots_and_bounce_the_ball():
    """Goal posts, sides and back are solid for robots and the ball (the mouth stays open); without ``goals``
    everything goes through to the arena wall, as before."""
    f = load_field_geometry()
    segs = goal_segments(f)
    assert len(segs) == 6 and GOAL_WALL_THICKNESS == 0.02
    R = 0.09
    x_back = f.half_length + f.goal_depth - GOAL_WALL_THICKNESS - R              # robot centre at the back wall
    assert clamp_to_goals(4.6, 0.0, R, f, segs) == pytest.approx((x_back, 0.0))
    assert clamp_to_goals(4.0, 0.0, R, f, segs) == (4.0, 0.0)                     # in front of the goal: free
    x, y = clamp_to_goals(4.55, 0.45, R, f, segs)                                 # inside, against a side wall
    assert y == pytest.approx(f.goal_width / 2 - R) and x == pytest.approx(4.55)
    # robot driving into the goal mouth stops at the back wall; beside the post it stops on the wall line
    w = TwinWorld("ideal", n_blue=2, n_yellow=0, watchdog_clock="sim")
    w.teleport_robot("blue", 0, 4.0, 0.0, 0.0)
    w.teleport_robot("blue", 1, 4.2, 0.9, 0.0)
    for _ in range(90):
        w.set_command("blue", 0, RobotCmd(vx=1.0))
        w.set_command("blue", 1, RobotCmd(vx=1.0))
        ws = w.step()
    assert ws.robots[("blue", 0)].x == pytest.approx(x_back, abs=1e-6)
    assert ws.robots[("blue", 1)].x == pytest.approx(f.half_length + f.boundary_width - R, abs=1e-6)
    # ball shot into the goal (robots out of the way): bounces off the back wall and never crosses it
    w.teleport_robot("blue", 0, -3.0, 2.0, 0.0)
    w.teleport_robot("blue", 1, -3.0, -2.0, 0.0)
    w.teleport_ball(3.0, 0.0, vx=3.0, vy=0.0)
    xs = [w.step().ball.x for _ in range(120)]
    x_ball_max = f.half_length + f.goal_depth - GOAL_WALL_THICKNESS - w.ball_params.radius
    assert max(xs) <= x_ball_max + 1e-9 and max(xs) > f.half_length + 0.1       # entered the goal, stopped by it
    assert xs[-1] < max(xs) - 0.05                                                # and came back out
    # ball at the post: deflected, never reaches the goal line between the posts
    w.teleport_ball(4.0, 0.53, vx=2.0, vy=0.0)
    pts = [(b.x, b.y) for b in (w.step().ball for _ in range(60))]
    assert max(x for x, _ in pts) < f.half_length + f.goal_depth and all(y > 0.4 for _, y in pts)
    # without goal walls the ball runs on to the arena wall
    w0 = TwinWorld("ideal", n_blue=0, n_yellow=0, goals=False)
    w0.teleport_ball(3.0, 0.0, vx=3.0, vy=0.0)
    xs0 = [w0.step().ball.x for _ in range(120)]
    assert max(xs0) > x_ball_max + 0.05 and max(xs0) <= f.half_length + f.boundary_width - w0.ball_params.radius


def test_boundary_off_lets_robots_and_ball_leave_the_arena():
    w = TwinWorld("ideal", n_blue=1, n_yellow=0, boundary=False, goals=False, watchdog_clock="sim")
    w.teleport_robot("blue", 0, 4.0, 2.0, 0.0)
    w.teleport_ball(4.0, -2.0, vx=4.0, vy=0.0)
    for _ in range(120):
        w.set_command("blue", 0, RobotCmd(vx=1.0))
        ws = w.step()
    assert ws.robots[("blue", 0)].x > w.field.half_length + w.field.boundary_width
    assert ws.ball.x > w.field.half_length + w.field.boundary_width


def test_teleport_resets_plant_and_velocity():
    w = TwinWorld("fopdt", n_blue=1, n_yellow=0)
    w.set_command("blue", 0, RobotCmd(vx=2.0))
    for _ in range(30):
        w.step()
    w.teleport_robot("blue", 0, 1.0, -1.0, 0.5, vx=1.0, vy=0.0, w=0.0)
    r = w.state().robots[("blue", 0)]
    assert (r.x, r.y, r.theta) == (1.0, -1.0, 0.5)
    assert r.vx_b == pytest.approx(math.cos(0.5)) and r.vy_b == pytest.approx(-math.sin(0.5))
    p = w.plants[("blue", 0)]
    assert p._k == 0 and p._hist == []                              # delay buffer primed empty
    # the new robot id can be added by teleport
    w.teleport_robot("yellow", 3, 0.0, 0.0, 0.0)
    assert ("yellow", 3) in w.plants and w.state().robots[("yellow", 3)].present


def test_set_plant_params_hot_swaps_theta_keeping_pose():
    w = TwinWorld("fopdt", n_blue=1, n_yellow=0)
    w.set_command("blue", 0, RobotCmd(vx=1.0))
    for _ in range(30):
        w.step()
    pose = w.plants[("blue", 0)].pose
    new = {d: DofParam(K=1.0, tau=0.05, Td=0.0) for d in ("vx", "vy", "w")}
    w.set_plant_params(new)
    assert w.plants[("blue", 0)].pose == pose
    assert w.params is new and w.plants[("blue", 0)].params is new
    assert np.allclose(w.plants[("blue", 0)].Td, 0.0)
    for _ in range(120):
        r = w.step().robots[("blue", 0)]
    assert r.vx_b == pytest.approx(1.0, abs=1e-6)                   # K = 1 steady state


def test_reset_scene_and_state_copy_are_independent():
    w = TwinWorld("ideal", n_blue=1, n_yellow=1)
    w.set_command("blue", 0, RobotCmd(vx=1.0))
    for _ in range(10):
        w.step()
    assert w.t > 0 and w.frame == 10
    w.reset(Scene(robots=[RobotSpawn("blue", 7, 0.1, 0.2, 0.3)], ball=BallState(x=1.0, y=1.0)))
    ws = w.state()
    assert list(ws.robots) == [("blue", 7)] and w.t == 0.0 and w.frame == 0
    assert (ws.ball.x, ws.ball.y) == (1.0, 1.0)
    ws.robots[("blue", 7)].x = 99.0
    assert w.state().robots[("blue", 7)].x == 0.1


def test_default_scene_spacing_keeps_robots_inside_field_without_overlap():
    w = TwinWorld("ideal", n_blue=6, n_yellow=6)
    ws = w.step()
    xs = [(r.x, r.y) for r in ws.robots.values()]
    for i in range(len(xs)):
        assert abs(xs[i][0]) < 4.5 and abs(xs[i][1]) < 3.0
        for j in range(i + 1, len(xs)):
            assert math.hypot(xs[j][0] - xs[i][0], xs[j][1] - xs[i][1]) >= 2 * w.spec.radius


def test_division_a_field_fits_the_full_roster_and_builds_its_goals_and_walls():
    """``config/field_divA.json`` (12 x 9 m, goal 1.8 m): 11 robots per team on the field without overlap, walls
    and goal walls at the Division A positions, substitutes (if any) parked beyond the wider arena."""
    from dtssl.config import load_field_preset

    preset = load_field_preset("divA")
    f = preset.field
    assert preset.robots_per_team == 11 and (f.length, f.width, f.goal_width) == (12.0, 9.0, 1.8)
    w = TwinWorld("ideal", n_blue=11, n_yellow=11, field=f, n_active=preset.robots_per_team)
    ws = w.step()
    assert len(ws.robots) == 22 and all(r.present for r in ws.robots.values())
    pts = [(r.x, r.y) for r in ws.robots.values()]
    for i, (x, y) in enumerate(pts):
        assert abs(x) < f.half_length and abs(y) < f.half_width
        for j in range(i + 1, len(pts)):
            assert math.hypot(pts[j][0] - x, pts[j][1] - y) >= 2 * w.spec.radius
    R = w.spec.radius
    w.teleport_robot("blue", 0, 5.5, 0.3, 0.0)                  # into the right goal mouth (|y| < 0.9)
    w.teleport_robot("blue", 1, 5.5, 2.5, 0.0)                  # beside the goal: stops at the arena wall
    for _ in range(120):
        w.set_command("blue", 0, RobotCmd(vx=1.5))
        w.set_command("blue", 1, RobotCmd(vx=1.5))
        ws = w.step()
    x_goal_back = f.half_length + f.goal_depth - GOAL_WALL_THICKNESS - R
    assert ws.robots[("blue", 0)].x == pytest.approx(x_goal_back, abs=1e-6) and x_goal_back > 6.0
    assert ws.robots[("blue", 1)].x == pytest.approx(f.half_length + f.boundary_width - R, abs=1e-6)
    # a Division A world with the Division B roster rule parks 5 per team beyond the -y wall of the wider arena
    w2 = TwinWorld("ideal", n_blue=11, n_yellow=11, field=f, n_active=6)
    parked = [r for r in w2.state().robots.values() if not r.present]
    assert len(parked) == 10 and all(r.y < -(f.half_width + f.boundary_width) for r in parked)
    assert all(abs(r.x) < f.half_length for r in parked)
