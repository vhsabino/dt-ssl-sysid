"""ssl-simulation-protocol bridge: the twin as a grSim/ER-Force drop-in for ssl-unification.

    from dtssl.bridge import SimServer, BridgeConfig, FakeStrategy, SessionRecorder
    from dtssl.sim.backends import make_world

    with SimServer(make_world("fopdt"), BridgeConfig.load()) as srv:
        srv.run()

Modules: ``proto`` (generated messages), ``vision`` (SSL_WrapperPacket publisher), ``control``
(RobotControl per team), ``simcontrol`` (SimulatorCommand), ``server`` (composition + loop),
``fake_strategy`` (test client), ``recorder`` (session -> log-contract parquet), ``cli``.
"""
from __future__ import annotations

from dtssl.bridge.config import BridgeConfig, ControlConfig, SimConfig, VisionConfig, as_bridge_config
from dtssl.bridge.control import ControlServer, proto_wheels_to_body, robot_command_to_cmd
from dtssl.bridge.fake_strategy import FakeStrategy
from dtssl.bridge.recorder import SessionRecorder
from dtssl.bridge.server import SimServer
from dtssl.bridge.simcontrol import SimControlServer
from dtssl.bridge.vision import VisionPublisher

__all__ = [
    "BridgeConfig", "VisionConfig", "ControlConfig", "SimConfig", "as_bridge_config",
    "VisionPublisher", "ControlServer", "SimControlServer", "SimServer", "FakeStrategy",
    "SessionRecorder", "robot_command_to_cmd", "proto_wheels_to_body",
]
