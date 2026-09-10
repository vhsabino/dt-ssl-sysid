"""Protocol round trips over real UDP sockets on loopback (ephemeral ports) — ``requires_net``."""
from __future__ import annotations

import math
import socket
import struct
import threading
import time

import pytest

from dtssl.bridge import proto as P
from dtssl.bridge.config import BridgeConfig
from dtssl.bridge.fake_strategy import FakeStrategy
from dtssl.bridge.server import SimServer
from dtssl.sim.backends import make_world
from dtssl.sim.entities import BallState, RobotCmd, RobotSpawn, Scene
from dtssl.sim.twin_world import TwinWorld

pytestmark = pytest.mark.requires_net

MCAST_GROUP = "224.5.23.2"


def _multicast_loopback_works() -> bool:
    try:
        rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        rx.bind(("", 0))
        port = rx.getsockname()[1]
        rx.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                      struct.pack("4s4s", socket.inet_aton(MCAST_GROUP), socket.inet_aton("127.0.0.1")))
        tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        tx.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton("127.0.0.1"))
        tx.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        tx.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        tx.sendto(b"probe", (MCAST_GROUP, port))
        rx.settimeout(0.5)
        data, _ = rx.recvfrom(16)
        rx.close()
        tx.close()
        return data == b"probe"
    except OSError:
        return False


def _wait(cond, timeout: float = 2.0, step: float = 0.005) -> bool:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if cond():
            return True
        time.sleep(step)
    return False


def _server_and_strategy(team: str = "yellow", target=(1.0, 0.5), **world_opts):
    world = make_world("fopdt", n_blue=1, n_yellow=1, watchdog_clock="sim", **world_opts)
    fs = FakeStrategy(team, target=target, unicast=True, vision_ip="127.0.0.1", vision_port=0)
    fs.open()
    cfg = BridgeConfig.load().with_overrides(vision_ip="127.0.0.1", vision_port=fs.vision_port,
                                             blue_port=0, yellow_port=0, simcontrol_port=0, bind_ip="127.0.0.1")
    srv = SimServer(world, cfg, step_mode=True)
    srv.start()
    fs.control_port = srv.control.port(team)
    return world, srv, fs


def test_round_trip_step_mode_fake_strategy_drives_robot():
    world, srv, fs = _server_and_strategy("yellow", target=(1.0, 0.5))
    try:
        r0 = world.state().robots[("yellow", 0)]
        d0 = math.hypot(1.0 - r0.x, 0.5 - r0.y)
        for _ in range(240):
            srv.tick()
            assert fs.step(timeout=1.0)                            # vision received -> control sent
            assert _wait(lambda: srv.control.stats.yellow.packets >= fs.controls_sent)
        st = fs.stats
        assert st["frames"] == 240 and st["frame_gaps"] == 0 and st["decode_errors"] == 0
        assert st["responses"] == 240 and st["geometry_packets"] == 4      # frames 0, 60, 120, 180
        assert st["last_feedback"] == {0: False}
        assert st["reached"] and st["distance"] < 0.05 < d0
        cmd = world.commands[("yellow", 0)]
        assert isinstance(cmd, RobotCmd) and cmd.t_recv > 0
        assert srv.stats["packets"]["yellow"] == 240 and srv.stats["packets"]["blue"] == 0
        assert srv.stats["control"]["yellow"]["responses"] == 240
        assert srv.stats["watchdog_hits"] == 0
    finally:
        srv.stop()
        fs.close()


def test_control_datagram_sets_world_command_and_replies():
    world, srv, fs = _server_and_strategy("blue")
    try:
        srv.tick()
        rc = P.RobotControl()
        c = rc.robot_commands.add()
        c.id = 0
        gv = c.move_command.global_velocity
        gv.x, gv.y, gv.angular = 0.0, 1.0, 0.5
        c.dribbler_speed = 6000.0
        fs.send_control(rc)
        resp = fs.read_response(timeout=2.0)
        assert resp is not None and [f.id for f in resp.feedback] == [0]
        assert _wait(lambda: world.commands[("blue", 0)].dribbler_rpm == 6000.0)
        cmd = world.commands[("blue", 0)]
        th = world.state().robots[("blue", 0)].theta                # blue spawns facing +x (theta 0)
        assert cmd.vx == pytest.approx(math.sin(th), abs=1e-6) and cmd.vy == pytest.approx(math.cos(th), abs=1e-6)
        assert cmd.w == pytest.approx(0.5)
        # malformed datagram: ignored, server still alive
        fs.control_sock.sendto(b"\xff\xfe\x00garbage", ("127.0.0.1", fs.control_port))
        assert fs.read_response(timeout=0.3) is None
        assert _wait(lambda: srv.control.stats.blue.parse_errors == 1)
        fs.send_control(rc)
        assert fs.read_response(timeout=2.0) is not None
    finally:
        srv.stop()
        fs.close()


def test_simcontrol_teleport_over_udp():
    world, srv, fs = _server_and_strategy("blue")
    try:
        cmd = P.SimulatorCommand()
        tb = cmd.control.teleport_ball
        tb.x, tb.y = 2.0, -1.0
        tr = cmd.control.teleport_robot.add()
        tr.id.id, tr.id.team = 0, P.BLUE
        tr.x, tr.y, tr.orientation = -3.0, 1.5, 0.25
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2.0)
        s.sendto(cmd.SerializeToString(), ("127.0.0.1", srv.simcontrol.port))
        data, _ = s.recvfrom(4096)
        resp = P.SimulatorResponse.FromString(data)
        assert len(resp.errors) == 0
        ws = world.state()
        assert (ws.ball.x, ws.ball.y) == (2.0, -1.0)
        r = ws.robots[("blue", 0)]
        assert (r.x, r.y, r.theta) == pytest.approx((-3.0, 1.5, 0.25))
        srv.tick()
        pkt = fs.receive(timeout=2.0)
        assert pkt is not None and pkt.detection.balls[0].x == pytest.approx(2000.0)
        s.close()
    finally:
        srv.stop()
        fs.close()


def test_has_ball_feedback_reaches_strategy():
    hold = 0.075 + 0.0215
    scene = Scene(robots=[RobotSpawn("yellow", 0, 0.0, 0.0, 0.0)], ball=BallState(x=hold, y=0.0))
    world = TwinWorld("ideal", scene=scene, watchdog_clock="sim")
    fs = FakeStrategy("yellow", target=(0.0, 0.0), unicast=True, vision_ip="127.0.0.1", vision_port=0)
    fs.open()
    cfg = BridgeConfig.load().with_overrides(vision_ip="127.0.0.1", vision_port=fs.vision_port,
                                             blue_port=0, yellow_port=0, simcontrol_port=0, bind_ip="127.0.0.1")
    srv = SimServer(world, cfg, step_mode=True)
    srv.start()
    fs.control_port = srv.control.port("yellow")
    try:
        srv.tick()
        assert fs.step(timeout=1.0)
        assert fs.last_feedback == {0: True}
    finally:
        srv.stop()
        fs.close()


def test_realtime_loop_runs_near_rate():
    world = make_world("ideal", n_blue=1, n_yellow=0)
    cfg = BridgeConfig.load().with_overrides(vision_ip="127.0.0.1", vision_port=1, blue_port=0, yellow_port=0,
                                             simcontrol_port=0, bind_ip="127.0.0.1", rate_hz=60.0)
    srv = SimServer(world, cfg)
    with srv:
        n = srv.run(duration=0.5)
        st = srv.stats
    assert 20 <= n <= 40                                              # 30 expected at 60 Hz
    assert st["ticks"] == n and world.t == pytest.approx(n / 60.0)
    assert 30.0 <= st["hz_actual"] <= 90.0


def test_stop_from_another_thread():
    world = make_world("ideal", n_blue=1, n_yellow=0)
    cfg = BridgeConfig.load().with_overrides(vision_ip="127.0.0.1", vision_port=1, blue_port=0, yellow_port=0,
                                             simcontrol_port=0, bind_ip="127.0.0.1")
    srv = SimServer(world, cfg)
    srv.start()
    th = srv.run_in_thread()
    time.sleep(0.2)
    srv.stop()
    th.join(timeout=2.0)
    assert not th.is_alive() and srv.ticks >= 5 and not srv.started


@pytest.mark.skipif(not _multicast_loopback_works(), reason="multicast loopback not available on this host")
def test_multicast_vision_reaches_multicast_client():
    rx_probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx_probe.bind(("", 0))
    port = rx_probe.getsockname()[1]
    rx_probe.close()
    world = make_world("ideal", n_blue=1, n_yellow=1, watchdog_clock="sim")
    fs = FakeStrategy("blue", vision_ip=MCAST_GROUP, vision_port=port, multicast_if="127.0.0.1")
    fs.open()
    cfg = BridgeConfig.load().with_overrides(vision_ip=MCAST_GROUP, vision_port=port, multicast_if="127.0.0.1",
                                             blue_port=0, yellow_port=0, simcontrol_port=0, bind_ip="127.0.0.1")
    srv = SimServer(world, cfg, step_mode=True)
    srv.start()
    fs.control_port = srv.control.port("blue")
    try:
        got = 0
        for _ in range(10):
            srv.tick()
            if fs.step(timeout=1.0):
                got += 1
        assert got == 10 and fs.responses == 10 and fs.geometry_packets == 1
    finally:
        srv.stop()
        fs.close()


def test_threaded_receivers_are_thread_safe_under_load():
    """Commands from a network thread while the server thread steps: no exceptions, all applied."""
    world, srv, fs = _server_and_strategy("yellow")
    errors: list[BaseException] = []

    def hammer():
        try:
            for i in range(300):
                rc = P.RobotControl()
                c = rc.robot_commands.add()
                c.id = 0
                lv = c.move_command.local_velocity
                lv.forward, lv.left, lv.angular = 0.1 * (i % 5), 0.0, 0.0
                fs.send_control(rc)
                time.sleep(0.0005)                                 # ~2 kHz: far above any strategy rate
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    try:
        t = threading.Thread(target=hammer)
        t.start()
        for _ in range(120):
            srv.tick()
        t.join(timeout=5.0)
        assert not errors
        # UDP on loopback may still drop a few datagrams of a burst: require >= 95 %
        assert _wait(lambda: srv.control.stats.yellow.packets >= 285, timeout=5.0)
        st = srv.control.stats.yellow
        assert st.commands == st.packets and st.parse_errors == 0 and st.responses == st.packets
    finally:
        srv.stop()
        fs.close()


class _ResettingSocket:
    """Wraps a UDP socket so that the first ``n`` ``recvfrom`` calls raise ``ConnectionResetError`` -- what Windows
    does (WSAECONNRESET) after a reply was sent to a client port that has since gone away."""

    def __init__(self, sock: socket.socket, n: int = 3):
        self._sock = sock
        self.left = n

    def recvfrom(self, bufsize: int):
        if self.left > 0:
            self.left -= 1
            raise ConnectionResetError(10054, "WSAECONNRESET")
        return self._sock.recvfrom(bufsize)

    def __getattr__(self, name):
        return getattr(self._sock, name)


def test_control_and_simcontrol_survive_windows_connection_resets():
    """A ConnectionResetError on recvfrom must not kill the receive threads (it used to ``break`` out of the loop,
    leaving ``dtssl serve`` deaf to every later command)."""
    world = make_world("fopdt", n_blue=1, n_yellow=0, watchdog_clock="sim")
    cfg = BridgeConfig.load().with_overrides(vision_ip="127.0.0.1", vision_port=0, blue_port=0, yellow_port=0,
                                             simcontrol_port=0, bind_ip="127.0.0.1")
    srv = SimServer(world, cfg, step_mode=True, threaded_receivers=False)
    srv.start()
    try:
        srv.control.socks["blue"] = _ResettingSocket(srv.control.socks["blue"], n=3)
        srv.simcontrol.sock = _ResettingSocket(srv.simcontrol.sock, n=2)
        # no receiver threads: tick() -> poll() drains the sockets through the wrappers
        tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        rc = P.RobotControl()
        c = rc.robot_commands.add()
        c.id = 0
        lv = c.move_command.local_velocity
        lv.forward, lv.left, lv.angular = 0.7, 0.0, 0.0
        for _ in range(6):
            tx.sendto(rc.SerializeToString(), ("127.0.0.1", srv.control.port("blue")))
            time.sleep(0.02)
        sc = P.SimulatorCommand()
        tr = sc.control.teleport_robot.add()
        tr.id.id, tr.id.team = 0, P.TEAM_ENUM["blue"]
        tr.x, tr.y, tr.orientation = 1.5, -0.5, 0.3
        for _ in range(4):
            tx.sendto(sc.SerializeToString(), ("127.0.0.1", srv.simcontrol.port))
            time.sleep(0.02)
        for _ in range(5):
            srv.tick()
            time.sleep(0.01)
        st = srv.control.stats.of("blue")
        assert st.resets == 3 and st.commands >= 1, vars(st)
        assert srv.simcontrol.resets == 2 and srv.simcontrol.teleports_robot >= 1, srv.simcontrol.stats
        ws = world.state()
        r = ws.robots[("blue", 0)]
        assert math.hypot(r.x - 1.5, r.y + 0.5) < 0.2
        tx.close()
    finally:
        srv.stop()
    # threaded receivers: the loop must keep running after the resets
    world = make_world("fopdt", n_blue=1, n_yellow=0, watchdog_clock="sim")
    srv = SimServer(world, cfg, step_mode=True, threaded_receivers=True)
    srv.control.start(threaded=False)                      # sockets first, then wrap, then the threads
    srv.control.socks["blue"] = _ResettingSocket(srv.control.socks["blue"], n=2)
    t = threading.Thread(target=srv.control._loop, args=("blue",), daemon=True)
    t.start()
    try:
        tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        for _ in range(4):
            tx.sendto(rc.SerializeToString(), ("127.0.0.1", srv.control.port("blue")))
            time.sleep(0.02)
        assert _wait(lambda: srv.control.stats.of("blue").commands >= 2)
        assert srv.control.stats.of("blue").resets == 2 and t.is_alive()
        tx.close()
    finally:
        srv.control.stop()
        t.join(timeout=1.0)
