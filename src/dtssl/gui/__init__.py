"""``dtssl.gui`` — PySide6 + pyqtgraph desktop GUI of the twin (``dtssl gui``).

Modules: ``app`` (MainWindow, ``main``), ``controller`` (world/server/timers), ``field_view``,
``plots``, ``params_panel``, ``joystick`` (pygame, Qt-free), ``keyboard`` (fallback, Qt-free),
``replay`` (dataset free-run vs truth, Qt-free), ``cli`` (``register(subparsers)``).

Importing this package does not import Qt; ``dtssl.gui.joystick`` / ``replay`` / ``keyboard``
work without PySide6.
"""
from __future__ import annotations

__all__ = ["main"]


def main(argv=None) -> int:
    from dtssl.gui.app import main as _main

    return _main(argv)
