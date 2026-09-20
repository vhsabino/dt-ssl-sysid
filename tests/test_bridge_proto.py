"""Generated protobuf modules, vision packet builder, command mapping, recorder (no sockets)."""
from __future__ import annotations

import math

import numpy as np
import pytest

from dtssl.bridge import proto as P
from dtssl.bridge.config import BridgeConfig, VisionConfig, parse_hostport
from dtssl.bridge.control import PROTO_WHEEL_ORDER, ControlServer, proto_wheels_to_body, robot_command_to_cmd
from dtssl.bridge.simcontrol import SimControlServer
from dtssl.bridge.vision import VisionPublisher
from dtssl.sim.entities import BallState, RobotCmd, RobotSpawn, Scene
from dtssl.sim.twin_world import TwinWorld, body_to_wheels
from dtssl.sim.world import FieldGeometry

MODULES = ["rc_communication_pb2", "ssl_gc_common_pb2", "ssl_simulation_config_pb2", "ssl_simulation_control_pb2",
           "ssl_simulation_error_pb2", "ssl_simulation_robot_control_pb2",
           "ssl_simulation_robot_feedback_pb2", "ssl_simulation_synchronous_pb2",
           "ssl_vision_detection_pb2", "ssl_vision_geometry_pb2", "ssl_vision_wrapper_pb2"]


def test_generated_modules_import_as_package():
    for m in MODULES:
        assert hasattr(P, m), m
    assert P.SSL_WrapperPacket.DESCRIPTOR.full_name == "RoboCupSSL.SSL_WrapperPacket"
    assert P.TEAM_NAME[P.YELLOW] == "yellow" and P.TEAM_ENUM["blue"] == P.BLUE


def test_generated_modules_are_current_with_sources():
    """The committed *_pb2.py must be regenerable: every .proto has its module and vice versa."""
    from pathlib import Path

    d = Path(P.__file__).parent
    protos = {p.stem for p in d.glob("*.proto")}
    pb2 = {p.stem[:-4] for p in d.glob("*_pb2.py")}
    assert protos == pb2 == {m[:-4] for m in MODULES}
    for py in d.glob("*_pb2.py"):
        text = py.read_text(encoding="utf-8")
        assert "\nimport ssl_" not in text, f"{py.name}: absolute import left by build_proto"


def test_wrapper_packet_round_trip():
    w = P.SSL_WrapperPacket()
    d = w.detection
    d.frame_number, d.t_capture, d.t_sent, d.camera_id = 7, 1.5, 1.6, 0
    r = d.robots_yellow.add()
    r.confidence, r.robot_id, r.x, r.y, r.orientation, r.pixel_x, r.pixel_y = 1.0, 4, 100.0, -50.0, 0.5, 0.0, 0.0
    b = d.balls.add()
    b.confidence, b.x, b.y, b.pixel_x, b.pixel_y = 1.0, 10.0, 20.0, 0.0, 0.0
    assert w.IsInitialized()
    w2 = P.SSL_WrapperPacket.FromString(w.SerializeToString())
    assert w2.detection.robots_yellow[0].robot_id == 4 and w2.detection.balls[0].y == 20.0
    assert not w2.HasField("geometry")


def _world_state():
    scene = Scene(robots=[RobotSpawn("blue", 1, 1.0, -2.0, 0.5), RobotSpawn("yellow", 0, -1.0, 2.0, 4.0),
                          RobotSpawn("yellow", 3, 0.0, 0.0, 0.0, present=False)],
                  ball=BallState(x=0.25, y=-0.5, z=0.1))
    return TwinWorld("ideal", scene=scene).state()


def test_vision_packet_has_required_fields_and_units():
    pub = VisionPublisher(VisionConfig(camera_id=2, geometry_every=60), FieldGeometry(), open_socket=False,
                          ball_model=TwinWorld("ideal", n_blue=0, n_yellow=0).ball_params)
    ws = _world_state()
    pkt = pub.build_packet(ws)
    assert pkt.IsInitialized()
    pkt2 = P.SSL_WrapperPacket.FromString(pkt.SerializeToString())
    det = pkt2.detection
    assert det.frame_number == 0 and det.camera_id == 2
    assert det.t_capture > 1.6e9 and det.t_sent >= det.t_capture
    assert len(det.robots_blue) == 1 and len(det.robots_yellow) == 1            # absent robot not published
    rb = det.robots_blue[0]
    assert rb.robot_id == 1 and rb.x == pytest.approx(1000.0) and rb.y == pytest.approx(-2000.0)
    assert rb.orientation == pytest.approx(0.5, abs=1e-6) and rb.confidence == 1.0
    assert rb.pixel_x == 0.0 and rb.pixel_y == 0.0 and rb.height == pytest.approx(150.0)
    ry = det.robots_yellow[0]
    assert -math.pi < ry.orientation <= math.pi and ry.orientation == pytest.approx(4.0 - 2 * math.pi, abs=1e-6)
    ball = det.balls[0]
    assert ball.x == pytest.approx(250.0) and ball.y == pytest.approx(-500.0) and ball.z == pytest.approx(100.0)
    # geometry on frame 0
    assert pkt2.HasField("geometry")
    f = pkt2.geometry.field
    assert (f.field_length, f.field_width, f.goal_width, f.goal_depth, f.boundary_width) == (9000, 6000, 1000, 180, 300)
    assert f.penalty_area_depth == 1000 and f.penalty_area_width == 2000 and f.center_circle_radius == 500
    assert f.goal_center_to_penalty_mark == 6000 and f.line_thickness == 10
    names = {seg.name for seg in f.field_lines}
    assert {"TopTouchLine", "BottomTouchLine", "LeftGoalLine", "RightGoalLine", "HalfwayLine", "CenterLine",
            "LeftPenaltyStretch", "RightPenaltyStretch"} <= names and len(f.field_lines) == 12
    assert f.field_arcs[0].name == "CenterCircle" and f.field_arcs[0].radius == 500.0
    assert pkt2.geometry.models.straight_two_phase.acc_slide == pytest.approx(-1.82135)
    assert pkt2.geometry.models.straight_two_phase.k_switch == pytest.approx(0.6)


def test_vision_frame_numbers_contiguous_and_geometry_every_n():
    pub = VisionPublisher(VisionConfig(geometry_every=10), FieldGeometry(), open_socket=False)
    ws = _world_state()
    for i in range(35):
        pkt = pub.build_packet(ws)
        assert pkt.detection.frame_number == i
        assert pkt.HasField("geometry") == (i % 10 == 0)
    assert pub.build_packet(ws, with_geometry=True).HasField("geometry")


def test_vision_noise_and_latency_buffer():
    pub = VisionPublisher(VisionConfig(position_noise_std_mm=5.0, orientation_noise_std_rad=0.01, latency_frames=3),
                          FieldGeometry(), open_socket=False, seed=1)
    ws = _world_state()
    xs = np.array([pub.build_packet(ws).detection.robots_blue[0].x for _ in range(200)])
    assert abs(xs.mean() - 1000.0) < 2.0 and 3.0 < xs.std() < 7.0
    sent = []
    pub.send = lambda pkt: sent.append(pkt.detection.frame_number) or 1  # type: ignore[method-assign]
    for _ in range(6):
        pub.publish(ws)
    assert sent == [200, 201, 202]                                          # delayed by 3 frames


def test_robot_command_mapping_local_global_wheel():
    rc = P.RobotCommand()
    rc.id = 2
    lv = rc.move_command.local_velocity
    lv.forward, lv.left, lv.angular = 1.0, -0.5, 2.0
    rc.kick_speed, rc.kick_angle, rc.dribbler_speed = 3.0, 45.0, 6000.0
    cmd = robot_command_to_cmd(rc, theta=1.0)
    assert (cmd.vx, cmd.vy, cmd.w) == (1.0, -0.5, 2.0)
    assert cmd.kick_speed == 3.0 and cmd.kick_angle_deg == 45.0 and cmd.dribbler_rpm == 6000.0
    # global: world +x with heading pi/2 -> body -y (right)
    rc2 = P.RobotCommand()
    rc2.id = 0
    gv = rc2.move_command.global_velocity
    gv.x, gv.y, gv.angular = 1.0, 0.0, 0.0
    cmd2 = robot_command_to_cmd(rc2, theta=math.pi / 2)
    assert cmd2.vx == pytest.approx(0.0, abs=1e-12) and cmd2.vy == pytest.approx(-1.0)
    # wheel: build proto wheel speeds (m/s surface) from a body velocity and recover it
    v = (0.4, -0.3, 1.5)
    omega = body_to_wheels(*v)
    from dtssl.sim.twin_world import WHEEL_RADIUS

    surface = omega * WHEEL_RADIUS                                          # dtssl order (60,135,225,300)
    proto_order = [surface[idx] for idx in PROTO_WHEEL_ORDER]               # (front_right, back_right, back_left, front_left)
    assert np.allclose(proto_wheels_to_body(*proto_order), v)
    rc3 = P.RobotCommand()
    rc3.id = 1
    wv = rc3.move_command.wheel_velocity
    wv.front_right, wv.back_right, wv.back_left, wv.front_left = proto_order
    cmd3 = robot_command_to_cmd(rc3, theta=0.0)
    assert (cmd3.vx, cmd3.vy, cmd3.w) == pytest.approx(v, abs=1e-5)
    # no move command -> zero velocity
    rc4 = P.RobotCommand()
    rc4.id = 1
    assert (robot_command_to_cmd(rc4, None).vx, robot_command_to_cmd(rc4, None).w) == (0.0, 0.0)


def test_control_server_apply_and_feedback_without_sockets():
    hold = 0.075 + 0.0215
    scene = Scene(robots=[RobotSpawn("blue", 0, 0.0, 0.0, 0.0), RobotSpawn("blue", 1, 1.0, 1.0, 0.0)],
                  ball=BallState(x=hold, y=0.0))
    world = TwinWorld("ideal", scene=scene)
    cs = ControlServer(world, BridgeConfig())
    msg = P.RobotControl()
    for rid, vx in ((0, 0.5), (1, -0.5), (20, 1.0)):
        c = msg.robot_commands.add()
        c.id = rid
        c.move_command.local_velocity.forward = vx
        c.move_command.local_velocity.left = 0.0
        c.move_command.local_velocity.angular = 0.0
    resp = cs.handle_datagram("blue", msg.SerializeToString())
    assert resp is not None and [f.id for f in resp.feedback] == [0, 1]
    assert resp.feedback[0].dribbler_ball_contact is True and resp.feedback[1].dribbler_ball_contact is False
    assert len(resp.errors) == 1 and resp.errors[0].code == "INVALID_ROBOT_ID"
    assert world.commands[("blue", 0)].vx == 0.5 and world.commands[("blue", 1)].vx == -0.5
    assert cs.stats.blue.commands == 2 and cs.stats.blue.invalid_ids == 1
    # malformed datagram: ignored, counted, no response
    assert cs.handle_datagram("yellow", b"\xff\xff\xff\x01garbage") is None
    assert cs.stats.yellow.parse_errors == 1


def test_simcontrol_apply_teleports_without_sockets():
    world = TwinWorld("ideal", n_blue=1, n_yellow=1)
    speeds = []
    sc = SimControlServer(world, BridgeConfig(), speed_setter=speeds.append)
    cmd = P.SimulatorCommand()
    tb = cmd.control.teleport_ball
    tb.x, tb.y, tb.vx, tb.vy = 1.0, 0.5, 0.0, 0.0
    tr = cmd.control.teleport_robot.add()
    tr.id.id, tr.id.team = 0, P.YELLOW
    tr.x, tr.y, tr.orientation, tr.present = -2.0, 1.0, 1.0, True
    tr2 = cmd.control.teleport_robot.add()
    tr2.id.id, tr2.id.team = 0, P.BLUE
    tr2.present = False
    tr3 = cmd.control.teleport_robot.add()
    tr3.id.id, tr3.id.team = 9, P.BLUE
    tr3.x, tr3.y, tr3.orientation, tr3.present = 0.5, 0.5, 0.0, True   # adds a new robot
    cmd.control.simulation_speed = 2.0
    resp = sc.apply(cmd)
    assert len(resp.errors) == 0
    ws = world.state()
    assert (ws.ball.x, ws.ball.y) == (1.0, 0.5)
    y = ws.robots[("yellow", 0)]
    assert (y.x, y.y, y.theta) == (-2.0, 1.0, 1.0) and y.present
    assert not ws.robots[("blue", 0)].present
    assert ws.robots[("blue", 9)].present and speeds == [2.0]
    bad = P.SimulatorCommand()
    bad.control.simulation_speed = 50.0
    t = bad.control.teleport_robot.add()
    t.id.id = 1
    assert {e.code for e in sc.apply(bad).errors} == {"INVALID_SIMULATION_SPEED", "INVALID_TEAM"}
    assert sc.handle_datagram(b"\x00\xff\xff") is None or True         # never raises


def test_bridge_config_defaults_and_overrides():
    cfg = BridgeConfig.load()
    assert cfg.vision.ip == "224.5.23.2" and cfg.vision.port == 10006 and cfg.vision.is_multicast
    assert (cfg.control.port_blue, cfg.control.port_yellow, cfg.control.port_simcontrol) == (10301, 10302, 10300)
    c2 = cfg.with_overrides(vision_ip="127.0.0.1", vision_port=10020, unicast=["10.0.0.5:10020"], blue_port=0)
    assert not c2.vision.is_multicast and c2.vision.targets() == [("127.0.0.1", 10020), ("10.0.0.5", 10020)]
    assert c2.control.port_blue == 0 and cfg.control.port_blue == 10301
    assert parse_hostport("host:1") == ("host", 1) and parse_hostport("1.2.3.4", 9) == ("1.2.3.4", 9)
    assert BridgeConfig.from_dict(cfg.to_dict()).vision == cfg.vision


def test_recorder_matches_log_contract():
    from dtssl.bridge.recorder import COMMAND_COLUMNS, ROBOT_COLUMNS, SessionRecorder

    world = TwinWorld("ideal", n_blue=1, n_yellow=1)
    rec = SessionRecorder(teams="blue", t0_wall=1000.0)
    world.set_command("blue", 0, RobotCmd(vx=1.0, kick_speed=2.0, dribbler_rpm=6000.0))
    for _ in range(3):
        rec.record(world.step(), world.commands)
    C, R = rec.commands_df(), rec.robots_df()
    assert list(C.columns) == COMMAND_COLUMNS and list(R.columns) == ROBOT_COLUMNS
    assert len(C) == 3 and len(R) == 3 and set(R["team"]) == {"allies"} and set(C["robot_id"]) == {0}
    assert C["timestamp_event"].iloc[0] == 0.0 and C["timestamp"].iloc[1] == pytest.approx(1000.0 + 1 / 60)
    assert R["timestamp_event"].iloc[0] == pytest.approx(1 / 60)      # pose is the result of the command
    assert bool(C["actuation_front"].iloc[0]) and bool(C["actuation_dribbler"].iloc[0])
    assert C["move_x"].dtype == np.float64 and C["robot_id"].dtype == np.int64
    assert R["position_x"].iloc[-1] == pytest.approx(world.state().robots[("blue", 0)].x * 1000.0)
    assert R["velocity_norm"].iloc[-1] == pytest.approx(1000.0)      # mm/s
