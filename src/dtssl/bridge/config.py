"""Typed view of ``config/bridge.json`` (vision / control / sim sections) with CLI overrides.

    cfg = BridgeConfig.load()                       # config/bridge.json
    cfg = BridgeConfig.from_dict({...})             # any mapping with the same sections
    cfg = cfg.with_overrides(vision_port=10020, unicast=["172.20.0.5:10020"], blue_port=0)

Every network object of the bridge accepts either a ``BridgeConfig`` or a plain dict/path and
normalises it through :func:`as_bridge_config`.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any


def parse_hostport(s: str | tuple | list, default_port: int | None = None) -> tuple[str, int]:
    """``"host:port"`` / ``("host", port)`` / ``{"ip":..., "port":...}`` -> ``(host, port)``."""
    if isinstance(s, dict):
        return (str(s.get("ip", s.get("host", "127.0.0.1"))), int(s.get("port", default_port or 0)))
    if isinstance(s, (tuple, list)):
        return (str(s[0]), int(s[1]))
    s = str(s).strip()
    if ":" in s:
        host, port = s.rsplit(":", 1)
        return (host or "127.0.0.1", int(port))
    if default_port is None:
        raise ValueError(f"expected host:port, got {s!r}")
    return (s, int(default_port))


@dataclass
class VisionConfig:
    ip: str = "224.5.23.2"
    port: int = 10006
    multicast_if: str = "127.0.0.1"
    ttl: int = 1
    loop: bool = True
    unicast_targets: list[str] = field(default_factory=list)   # "host:port"
    rate_hz: float = 60.0
    camera_id: int = 0
    geometry_every: int = 60
    position_noise_std_mm: float = 0.0
    orientation_noise_std_rad: float = 0.0
    latency_frames: int = 0

    @property
    def is_multicast(self) -> bool:
        try:
            first = int(self.ip.split(".")[0])
        except ValueError:
            return False
        return 224 <= first <= 239

    def targets(self) -> list[tuple[str, int]]:
        out = [(self.ip, int(self.port))] if self.ip else []
        out += [parse_hostport(t, self.port) for t in self.unicast_targets]
        return out


@dataclass
class ControlConfig:
    bind_ip: str = "0.0.0.0"
    port_blue: int = 10301
    port_yellow: int = 10302
    port_simcontrol: int = 10300
    watchdog_s: float = 0.3

    def port_of(self, team: str) -> int:
        return int(self.port_blue if team == "blue" else self.port_yellow)


@dataclass
class SimConfig:
    backend: str = "fopdt"
    n_blue: int = 6
    n_yellow: int = 6
    realtime: bool = True
    speed: float = 1.0


@dataclass
class BridgeConfig:
    vision: VisionConfig = field(default_factory=VisionConfig)
    control: ControlConfig = field(default_factory=ControlConfig)
    sim: SimConfig = field(default_factory=SimConfig)
    source: str | None = None

    # ------------------------------------------------------------------ construction
    @staticmethod
    def from_dict(d: dict[str, Any], source: str | None = None) -> BridgeConfig:
        def section(cls, key):
            raw = {k: v for k, v in (d.get(key) or {}).items() if not k.startswith("_")}
            known = {k: v for k, v in raw.items() if k in cls.__dataclass_fields__}
            return cls(**known)

        return BridgeConfig(vision=section(VisionConfig, "vision"),
                            control=section(ControlConfig, "control"),
                            sim=section(SimConfig, "sim"), source=source)

    @staticmethod
    def load(path: str | Path | None = None) -> BridgeConfig:
        import json

        from dtssl.paths import config_path

        p = Path(path) if path else config_path("bridge.json")
        with open(p, encoding="utf-8") as f:
            return BridgeConfig.from_dict(json.load(f), source=str(p))

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("source", None)
        return d

    # ------------------------------------------------------------------ overrides
    def with_overrides(self, *, vision_ip: str | None = None, vision_port: int | None = None,
                       multicast_if: str | None = None, unicast: list[str] | None = None,
                       blue_port: int | None = None, yellow_port: int | None = None,
                       simcontrol_port: int | None = None, bind_ip: str | None = None,
                       n_blue: int | None = None, n_yellow: int | None = None,
                       backend: str | None = None, realtime: bool | None = None,
                       speed: float | None = None, rate_hz: float | None = None,
                       geometry_every: int | None = None, latency_frames: int | None = None,
                       watchdog_s: float | None = None) -> BridgeConfig:
        v = replace(self.vision)
        c = replace(self.control)
        s = replace(self.sim)
        if vision_ip is not None:
            v.ip = vision_ip
        if vision_port is not None:
            v.port = int(vision_port)
        if multicast_if is not None:
            v.multicast_if = multicast_if
        if unicast is not None:
            v.unicast_targets = list(unicast)
        if rate_hz is not None:
            v.rate_hz = float(rate_hz)
        if geometry_every is not None:
            v.geometry_every = int(geometry_every)
        if latency_frames is not None:
            v.latency_frames = int(latency_frames)
        if blue_port is not None:
            c.port_blue = int(blue_port)
        if yellow_port is not None:
            c.port_yellow = int(yellow_port)
        if simcontrol_port is not None:
            c.port_simcontrol = int(simcontrol_port)
        if bind_ip is not None:
            c.bind_ip = bind_ip
        if watchdog_s is not None:
            c.watchdog_s = float(watchdog_s)
        if n_blue is not None:
            s.n_blue = int(n_blue)
        if n_yellow is not None:
            s.n_yellow = int(n_yellow)
        if backend is not None:
            s.backend = backend
        if realtime is not None:
            s.realtime = bool(realtime)
        if speed is not None:
            s.speed = float(speed)
        return BridgeConfig(vision=v, control=c, sim=s, source=self.source)


def as_bridge_config(config: BridgeConfig | dict | str | Path | None) -> BridgeConfig:
    """Normalise ``None`` (-> config/bridge.json), a path, a dict or a BridgeConfig."""
    if config is None:
        return BridgeConfig.load()
    if isinstance(config, BridgeConfig):
        return config
    if isinstance(config, (str, Path)):
        return BridgeConfig.load(config)
    if isinstance(config, dict):
        return BridgeConfig.from_dict(config)
    raise TypeError(f"unsupported config type {type(config).__name__}")


__all__ = ["BridgeConfig", "VisionConfig", "ControlConfig", "SimConfig", "as_bridge_config", "parse_hostport"]
