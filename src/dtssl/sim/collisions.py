"""Contact helpers of the analytic twin world (circle robots, flat dribbler face, walls).

All functions are pure (no world state) and work in SI world coordinates. The robot is a
disc of radius ``robot_radius`` with a flat *dribbler face* at ``dribbler_offset`` from the
centre along the heading: inside the chord sector (half-angle ``acos(offset / radius)``)
the ball collides with the flat face, elsewhere with the circle. This keeps a ball resting
on the dribbler inside ``ball_contact_dist`` instead of being pushed to ``radius + r_ball``.
"""
from __future__ import annotations

import math
from collections.abc import Sequence

from dtssl.sim.ball import Ball


def clamp_to_walls(x: float, y: float, radius: float, field) -> tuple[float, float]:
    """Keep a robot centre inside the arena (field + boundary) accounting for its radius."""
    lx = field.half_length + field.boundary_width - radius
    ly = field.half_width + field.boundary_width - radius
    return (min(max(x, -lx), lx), min(max(y, -ly), ly))


def resolve_robot_robot(positions: list[list[float]], radius: float, passes: int = 4,
                        margin: float = 0.0) -> bool:
    """Symmetric positional push-out of overlapping discs (in place). Returns True if any pair
    overlapped. ``positions`` is a list of mutable ``[x, y]`` pairs (one per present robot)."""
    n = len(positions)
    min_d = 2.0 * radius + margin
    any_contact = False
    for _ in range(passes):
        moved = False
        for i in range(n):
            xi, yi = positions[i]
            for j in range(i + 1, n):
                xj, yj = positions[j]
                dx, dy = xj - xi, yj - yi
                d = math.hypot(dx, dy)
                if d >= min_d:
                    continue
                any_contact = moved = True
                if d < 1e-9:                    # coincident centres: separate along +x
                    nx, ny = 1.0, 0.0
                else:
                    nx, ny = dx / d, dy / d
                push = 0.5 * (min_d - d)
                positions[i][0] -= push * nx
                positions[i][1] -= push * ny
                positions[j][0] += push * nx
                positions[j][1] += push * ny
                xi, yi = positions[i]
        if not moved:
            break
    return any_contact


def robot_ball_contact(ball: Ball, rx: float, ry: float, rtheta: float,
                       rvx: float, rvy: float, rw: float,
                       robot_radius: float, dribbler_offset: float,
                       robot_height: float, restitution: float | None = None) -> bool:
    """Resolve ball vs one robot (disc + flat dribbler face). Modifies the ball in place.

    ``(rvx, rvy)`` is the robot's world velocity and ``rw`` its angular velocity, used for
    the velocity of the contact point. Returns True when a contact was resolved. Balls whose
    bottom is above the robot (``ball.z > robot_height``, chip in flight) are ignored.
    """
    st = ball.state
    if st.z > robot_height:
        return False
    r_ball = ball.radius
    dx, dy = st.x - rx, st.y - ry
    d = math.hypot(dx, dy)
    if d >= robot_radius + r_ball:
        return False
    c, s = math.cos(rtheta), math.sin(rtheta)
    bx = c * dx + s * dy            # ball in body frame
    by = -s * dx + c * dy
    half_chord = math.sqrt(max(robot_radius * robot_radius - dribbler_offset * dribbler_offset, 0.0))
    if bx > 0.0 and abs(by) <= half_chord and dribbler_offset < robot_radius:
        # flat face region
        face_x = dribbler_offset + r_ball
        if bx >= face_x:
            return False
        nx, ny = c, s                                        # outward normal = heading
        # push out along the normal
        shift = face_x - bx
        st.x += shift * nx
        st.y += shift * ny
        cx, cy = st.x - rx, st.y - ry                        # contact point velocity (rigid body)
        svx, svy = rvx - rw * cy, rvy + rw * cx
        ball.reflect(nx, ny, svx, svy, restitution)
        return True
    if d < 1e-9:
        nx, ny = c, s
    else:
        nx, ny = dx / d, dy / d
    target = robot_radius + r_ball
    st.x = rx + nx * target
    st.y = ry + ny * target
    cx, cy = st.x - rx, st.y - ry
    svx, svy = rvx - rw * cy, rvy + rw * cx
    ball.reflect(nx, ny, svx, svy, restitution)
    return True


def ball_in_front(ball_x: float, ball_y: float, ball_z: float, rx: float, ry: float, rtheta: float,
                  contact_dist: float, half_angle: float, z_tol: float = 0.02) -> bool:
    """Ball inside the dribbler acceptance cone (centre->ball <= contact_dist, |angle| <= half_angle)."""
    if ball_z > z_tol:
        return False
    dx, dy = ball_x - rx, ball_y - ry
    d = math.hypot(dx, dy)
    if d > contact_dist:
        return False
    ang = math.atan2(dy, dx) - rtheta
    ang = math.atan2(math.sin(ang), math.cos(ang))
    return abs(ang) <= half_angle


def dribbler_hold_pose(rx: float, ry: float, rtheta: float, dribbler_offset: float,
                       r_ball: float) -> tuple[float, float]:
    """World position of a ball held centred on the dribbler face."""
    dist = dribbler_offset + r_ball
    return (rx + dist * math.cos(rtheta), ry + dist * math.sin(rtheta))


def pairwise_overlaps(positions: Sequence[Sequence[float]], radius: float) -> list[tuple[int, int]]:
    out = []
    for i in range(len(positions)):
        for j in range(i + 1, len(positions)):
            if math.hypot(positions[j][0] - positions[i][0], positions[j][1] - positions[i][1]) < 2.0 * radius:
                out.append((i, j))
    return out
