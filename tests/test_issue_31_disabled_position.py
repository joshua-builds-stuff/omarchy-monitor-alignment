"""Regression tests for #31: a disabled display keeps its position across Save and load."""

from __future__ import annotations

import importlib.util
import os
import tempfile
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
    loader = SourceFileLoader("monitor_align_issue_31", str(ROOT / "monitor-align"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    app = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, stubs), mock.patch("ctypes.CDLL"):
        sys.modules[loader.name] = app
        loader.exec_module(app)
    return app


APP = _load_app()
def disabled_monitor(x: int, y: int) -> "APP.Monitor":
    mode = APP.Mode(2560, 1440, 143.86)
    return APP.Monitor(name="HDMI-A-1", description="Panel", modes=[mode], mode=mode,
                       scale=1.25, transform=1, x=x, y=y, enabled=False, index=2)


def entry(name: str, x: int, y: int, disabled: bool) -> dict:
    return {"name": name, "description": "", "availableModes": ["2560x1440@143.86Hz"],
            "width": 2560, "height": 1440, "refreshRate": 143.86, "scale": 1.0,
            "transform": 0, "x": x, "y": y, "disabled": disabled}


class DisabledLuaTests(unittest.TestCase):
    def test_disabled_rule_keeps_position_mode_scale_transform(self) -> None:
        line = disabled_monitor(-1440, 120).lua()
        self.assertIn('output = "HDMI-A-1"', line)
        self.assertIn("disabled = true", line)
        self.assertIn('position = "-1440x120"', line)
        self.assertIn('mode = "2560x1440@143.86"', line)
        self.assertIn("scale = 1.25", line)
        self.assertIn("transform = 1", line)

    def test_enabled_rule_unchanged(self) -> None:
        mon = disabled_monitor(0, 0)
        mon.enabled = True
        self.assertNotIn("disabled", mon.lua())


class DisabledLoadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "monitors.lua")
        patcher = mock.patch.object(APP, "MONITORS_LUA", self.path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, text: str) -> None:
        with open(self.path, "w") as handle:
            handle.write(text)

    def load(self, entries: list[dict]) -> dict:
        with mock.patch.object(APP, "hyprctl_json", mock.Mock(return_value=entries)):
            return {m.name: m for m in APP.load_monitors()}

    def test_disabled_output_at_zero_prefers_saved_position(self) -> None:
        self.write(APP.BLOCK_BEGIN + "\n"
                   + 'hl.monitor({ output = "DP-1", mode = "2560x1440@143.86", '
                     'position = "0x0", scale = 1, transform = 0 })\n'
                   + disabled_monitor(-1440, 120).lua() + "\n"
                   + APP.BLOCK_END + "\n")
        loaded = self.load([entry("DP-1", 0, 0, False), entry("HDMI-A-1", 0, 0, True)])
        self.assertEqual((loaded["HDMI-A-1"].x, loaded["HDMI-A-1"].y), (-1440, 120))
        self.assertEqual((loaded["DP-1"].x, loaded["DP-1"].y), (0, 0))

    def test_later_rule_without_position_wins(self) -> None:
        self.write(disabled_monitor(-1440, 120).lua() + "\n"
                   + 'hl.monitor({ output = "HDMI-A-1", disabled = true })\n')
        loaded = self.load([entry("HDMI-A-1", 0, 0, True)])
        self.assertEqual((loaded["HDMI-A-1"].x, loaded["HDMI-A-1"].y), (0, 0))

    def test_reported_nonzero_position_is_kept(self) -> None:
        self.write(disabled_monitor(-1440, 120).lua() + "\n")
        loaded = self.load([entry("HDMI-A-1", 3840, 0, True)])
        self.assertEqual(loaded["HDMI-A-1"].x, 3840)

    def test_missing_file_falls_back_to_hyprctl(self) -> None:
        loaded = self.load([entry("HDMI-A-1", 0, 0, True)])
        self.assertEqual((loaded["HDMI-A-1"].x, loaded["HDMI-A-1"].y), (0, 0))

    def test_round_trip_of_saved_disabled_line(self) -> None:
        mon = disabled_monitor(-1440, 120)
        self.assertEqual(APP.saved_position(mon.lua(), mon.name), (-1440, 120))
        self.assertIsNone(APP.saved_position(mon.lua(), "HDMI-A-10"))


if __name__ == "__main__":
    unittest.main()
