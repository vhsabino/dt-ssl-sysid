"""Analytic ball: two-phase deceleration, kicks, chip, walls, robot contact, dribbler capture."""
from __future__ import annotations

import math

import numpy as np
import pytest

from dtssl.sim.ball import Ball, BallParams, Walls, stopping_distance, stopping_time
from dtssl.sim.collisions import ball_in_front, robot_ball_contact
from dtssl.sim.entities import BallState, RobotCmd, RobotSpawn, Scene
from dtssl.sim.twin_world import TwinWorld
from dtssl.sim.world import FieldGeometry

DT_SUB = 1.0 / 600.0


def _roll_until_stop(ball: Ball, walls=None, t_max: float = 60.0) -> float:
    t = 0.0
    while (ball.speed() > 0.0 or ball.airborne) and t < t_max:
        ball.step(DT_SUB, walls)
        t += DT_SUB
    return t


@pytest.mark.parametrize("v0", [0.5, 2.0, 4.0, 6.5])
def test_two_phase_stops_at_analytic_distance(v0):
    p = BallParams()
    b = Ball(p)
    b.set(0.0, 0.0)
    heading = 0.7
    b.kick(v0, heading)
    assert not b.state.rolling and b.v_switch == pytest.approx(p.sliding_to_rolling_speed_ratio * v0)
    t = _roll_until_stop(b)
    d = math.hypot(b.state.x, b.state.y)
    d_ref = stopping_distance(v0, p)
    assert d == pytest.approx(d_ref, abs=1e-9)                     # exact piecewise integration
    assert t == pytest.approx(stopping_time(v0, p), abs=2 * DT_SUB)
    assert b.speed() == 0.0 and b.state.rolling
    # travelled along the heading
    assert math.atan2(b.state.y, b.state.x) == pytest.approx(heading, abs=1e-12)


def test_phase_switch_happens_at_k_times_v0():
    p = BallParams()
    b = Ball(p)
    b.set(0.0, 0.0)
    b.kick(3.0, 0.0)
    was_sliding = True
    switch_speed = None
    while b.speed() > 0.0:
        b.step(DT_SUB)
        if was_sliding and b.state.rolling:
            switch_speed = b.speed()
            was_sliding = False
    assert switch_speed is not None
    # first rolling sample is at most one substep of rolling deceleration below k*v0
    assert p.sliding_to_rolling_speed_ratio * 3.0 - switch_speed <= p.rolling_decel * DT_SUB + 1e-12


def test_flat_kick_moves_ball_along_robot_heading():
    th = -0.9
    hold = 0.075 + 0.0215
    scene = Scene(robots=[RobotSpawn("blue", 3, 0.5, -0.2, th)],
                  ball=BallState(x=0.5 + hold * math.cos(th), y=-0.2 + hold * math.sin(th)))
    w = TwinWorld("ideal", scene=scene)
    assert w.state().robots[("blue", 3)].has_ball
    w.set_command("blue", 3, RobotCmd(kick_speed=4.0))
    ws = w.step()
    v = math.hypot(ws.ball.vx, ws.ball.vy)
    assert 0.0 < v <= 4.0 and v > 3.9                              # one frame of sliding deceleration
    assert math.atan2(ws.ball.vy, ws.ball.vx) == pytest.approx(th, abs=1e-9)
    assert w.kicks == 1
    assert w.commands[("blue", 3)].kick_speed == 0.0               # consumed once
    for _ in range(30):
        ws = w.step()
    d = math.hypot(ws.ball.x - 0.5, ws.ball.y + 0.2)
    assert d > 1.5 and ws.ball.z == 0.0


def test_kick_speed_is_saturated_to_kick_flat_max():
    hold = 0.075 + 0.0215
    scene = Scene(robots=[RobotSpawn("yellow", 0, 0.0, 0.0, 0.0)], ball=BallState(x=hold, y=0.0))
    w = TwinWorld("ideal", scene=scene)
    w.set_command("yellow", 0, RobotCmd(kick_speed=50.0))
    ws = w.step()
    assert math.hypot(ws.ball.vx, ws.ball.vy) <= w.spec.kick_flat_max


def test_chip_kick_is_ballistic_and_lands():
    p = BallParams()
    b = Ball(p)
    b.set(0.0, 0.0)
    v0, ang = 4.0, 45.0
    b.kick(v0, 0.0, chip=True, chip_angle_deg=ang)
    assert b.airborne and b.state.vz == pytest.approx(v0 * math.sin(math.radians(ang)))
    z_max = 0.0
    t = 0.0
    while b.airborne and b.bounces == 0:
        b.step(DT_SUB)
        z_max = max(z_max, b.state.z)
        t += DT_SUB
    vz0 = v0 * math.sin(math.radians(ang))
    assert z_max == pytest.approx(vz0 ** 2 / (2 * p.g), abs=1e-6)
    assert t == pytest.approx(2 * vz0 / p.g, abs=2 * DT_SUB)
    assert b.state.x == pytest.approx(v0 * math.cos(math.radians(ang)) * 2 * vz0 / p.g, abs=v0 * DT_SUB)
    # after the first bounce vz is scaled by the floor restitution (minus gravity over the
    # remainder of the substep in which the impact happened)
    assert b.state.vz == pytest.approx(p.restitution_floor * vz0, abs=p.g * DT_SUB)
    _roll_until_stop(b)
    assert b.state.z == 0.0 and b.state.vz == 0.0 and b.speed() == 0.0


def test_chip_from_world_ignores_robot_collision_while_high():
    hold = 0.075 + 0.0215
    scene = Scene(robots=[RobotSpawn("blue", 0, 0.0, 0.0, 0.0), RobotSpawn("blue", 1, 0.6, 0.0, math.pi)],
                  ball=BallState(x=hold, y=0.0))
    w = TwinWorld("ideal", scene=scene)
    w.set_command("blue", 0, RobotCmd(kick_speed=5.0, kick_angle_deg=45.0))
    ws = w.step()
    assert ws.ball.vz > 0.0
    for _ in range(12):
        ws = w.step()
    # the ball flew over the second robot standing 0.6 m ahead
    assert ws.ball.x > 0.6 + w.spec.radius and ws.ball.vx > 0.0


def test_wall_bounce_reflects_with_restitution():
    p = BallParams()
    field = FieldGeometry()
    walls = Walls.from_field(field, p.radius)
    b = Ball(p)
    b.set(4.5, 0.3, vx=3.0, vy=0.0)
    xs = []
    for _ in range(120):
        b.step(DT_SUB, walls)
        xs.append(b.state.x)
    assert max(xs) <= walls.x_max + 1e-12
    assert b.state.vx < 0.0                                        # came back
    # speed right after the bounce ~ e * speed just before (minus a few substeps of decel)
    assert abs(b.state.vx) < p.restitution_wall * 3.0
    assert abs(b.state.vx) > 0.5 * p.restitution_wall * 3.0


def test_robot_ball_contact_pushes_out_and_reflects():
    p = BallParams(restitution_robot=0.5)
    b = Ball(p)
    # ball overlapping the left side of a robot at the origin facing +x, ball moving into it
    b.set(-0.02, 0.10, vx=0.0, vy=-1.0)
    hit = robot_ball_contact(b, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.09, 0.075, 0.15, p.restitution_robot)
    assert hit
    d = math.hypot(b.state.x, b.state.y)
    assert d == pytest.approx(0.09 + p.radius, abs=1e-12)
    assert b.state.vy > 0.0                                        # reflected on the normal
    # flat face: a resting ball on the dribbler is not pushed to radius + r_ball
    b.set(0.0965 - 0.005, 0.0)
    robot_ball_contact(b, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.09, 0.075, 0.15, p.restitution_robot)
    assert b.state.x == pytest.approx(0.0965, abs=1e-12)
    assert ball_in_front(b.state.x, b.state.y, 0.0, 0.0, 0.0, 0.0, 0.11, 0.31)


def test_dribbler_captures_and_releases_ball():
    scene = Scene(robots=[RobotSpawn("blue", 0, 0.0, 0.0, 0.0)], ball=BallState(x=0.10, y=0.01))
    w = TwinWorld("ideal", scene=scene)
    w.set_command("blue", 0, RobotCmd(vx=1.0, dribbler_rpm=6000.0))
    for _ in range(60):
        ws = w.step()
    r = ws.robots[("blue", 0)]
    assert r.has_ball and w.ball_obj.captured_by == ("blue", 0)
    hold = w.spec.dribbler_offset + w.ball_params.radius
    assert ws.ball.x == pytest.approx(r.x + hold, abs=1e-9)
    assert ws.ball.y == pytest.approx(r.y, abs=1e-9)
    assert ws.ball.vx == pytest.approx(1.0, abs=1e-9)              # moves with the robot
    # turning with the ball keeps it in front
    w.set_command("blue", 0, RobotCmd(w=2.0, dribbler_rpm=6000.0))
    for _ in range(30):
        ws = w.step()
    r = ws.robots[("blue", 0)]
    assert ws.ball.x == pytest.approx(r.x + hold * math.cos(r.theta), abs=1e-9)
    assert ws.ball.y == pytest.approx(r.y + hold * math.sin(r.theta), abs=1e-9)
    # dribbler off: released, keeps the robot's velocity, still touching the face
    w.set_command("blue", 0, RobotCmd(vx=0.5, dribbler_rpm=0.0))
    ws = w.step()
    assert w.ball_obj.captured_by is None
    # kick from the dribbler
    w.set_command("blue", 0, RobotCmd(dribbler_rpm=6000.0))
    w.step()
    assert w.ball_obj.captured_by == ("blue", 0)
    w.set_command("blue", 0, RobotCmd(kick_speed=3.0, dribbler_rpm=6000.0))
    ws = w.step()
    assert w.ball_obj.captured_by is None and math.hypot(ws.ball.vx, ws.ball.vy) > 2.5


def test_ball_out_of_cone_is_not_in_front():
    assert not ball_in_front(0.0, 0.2, 0.0, 0.0, 0.0, 0.0, 0.11, 0.31)      # too far / 90 deg off
    assert not ball_in_front(-0.09, 0.0, 0.0, 0.0, 0.0, 0.0, 0.11, 0.31)    # behind
    assert not ball_in_front(0.09, 0.0, 0.1, 0.0, 0.0, 0.0, 0.11, 0.31)     # in the air
    assert ball_in_front(0.09, 0.02, 0.0, 0.0, 0.0, 0.0, 0.11, 0.31)


def test_teleport_ball_with_velocity_uses_two_phase_model():
    w = TwinWorld("ideal", n_blue=0, n_yellow=0)
    w.teleport_ball(1.0, -1.0, vx=0.0, vy=2.0)
    ws = w.step()
    assert ws.ball.vy < 2.0 and ws.ball.vy > 2.0 - 1.82135 * (1 / 60) - 1e-9
    t = 0.0
    while math.hypot(w.state().ball.vx, w.state().ball.vy) > 0 and t < 20:
        w.step()
        t += w.ts
    assert w.state().ball.y - (-1.0) == pytest.approx(stopping_distance(2.0, w.ball_params), abs=1e-6)
    assert np.isfinite(w.state().ball.x)
