"""Regression tests for #37: disabled-position recovery reads the last hl.monitor rule."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import types
import unittest
from importlib.machinery import SourceFileLoader
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]


class _StubModule(types.ModuleType):
    """Any attribute is a fresh class, so the app can subclass GTK types."""

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        value = type(name, (), {"__init__": lambda self, *a, **k: None,
                                "__getattr__": lambda self, n: (lambda *a, **k: None)})
        setattr(self, name, value)
        return value


def _load_app():
    try:
        import gi  # noqa: F401
        import cairo  # noqa: F401
        import ctypes
        ctypes.CDLL("libgtk4-layer-shell.so.0")
        stubs = {}
    except (ImportError, OSError):
        gi = _StubModule("gi")
        gi.require_version = lambda *a, **k: None
        repo = _StubModule("gi.repository")
        gi.repository = repo
        stubs = {"gi": gi, "gi.repository": repo, "cairo": _StubModule("cairo")}
        for name in ("Gtk", "Gdk", "Adw", "GLib", "Pango", "PangoCairo",
                     "Gtk4LayerShell"):
            mod = _StubModule(f"gi.repository.{name}")
            setattr(repo, name, mod)
            stubs[f"gi.repository.{name}"] = mod
    loader = SourceFileLoader("monitor_align_issue_37", str(ROOT / "monitor-align"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    app = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, stubs), mock.patch("ctypes.CDLL"):
        sys.modules[loader.name] = app
        loader.exec_module(app)
    return app


APP = _load_app()


class SavedPositionLastRuleTests(unittest.TestCase):
    def test_multi_line_rule(self) -> None:
        text = ('hl.monitor({\n'
                '  output = "HDMI-A-1",\n'
                '  position = "1920x1080",\n'
                '  disabled = true,\n'
                '})\n')
        self.assertEqual(APP.saved_position(text, "HDMI-A-1"), (1920, 1080))

    def test_later_multi_line_rule_wins_over_earlier_single_line(self) -> None:
        text = ('hl.monitor({ output = "HDMI-A-1", position = "0x0" })\n'
                'hl.monitor({\n'
                '  output = "HDMI-A-1",\n'
                '  position = "1920x0",\n'
                '})\n')
        self.assertEqual(APP.saved_position(text, "HDMI-A-1"), (1920, 0))

    def test_single_quoted_output_and_position(self) -> None:
        text = "hl.monitor({ output = 'HDMI-A-1', position = '1920x0', disabled = true })\n"
        self.assertEqual(APP.saved_position(text, "HDMI-A-1"), (1920, 0))

    def test_negative_coordinates(self) -> None:
        text = 'hl.monitor({ output = "HDMI-A-1", position = "-1440x-120" })\n'
        self.assertEqual(APP.saved_position(text, "HDMI-A-1"), (-1440, -120))

    def test_later_rule_without_position_returns_none(self) -> None:
        text = ('hl.monitor({ output = "HDMI-A-1", position = "1920x0" })\n'
                'hl.monitor({\n'
                '  output = "HDMI-A-1",\n'
                '  disabled = true,\n'
                '})\n')
        self.assertIsNone(APP.saved_position(text, "HDMI-A-1"))

    def test_other_output_rule_ignored(self) -> None:
        text = ('hl.monitor({ output = "HDMI-A-1", position = "1920x0" })\n'
                'hl.monitor({ output = "DP-1", position = "0x0" })\n')
        self.assertEqual(APP.saved_position(text, "HDMI-A-1"), (1920, 0))


if __name__ == "__main__":
    unittest.main()
