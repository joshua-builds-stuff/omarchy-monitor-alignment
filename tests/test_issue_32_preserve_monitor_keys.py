"""Regression tests for #32: Try it and Save keep mirror and keys the editor does not edit."""

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
    loader = SourceFileLoader("monitor_align_issue_32", str(ROOT / "monitor-align"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    app = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, stubs), mock.patch("ctypes.CDLL"):
        sys.modules[loader.name] = app
        loader.exec_module(app)
    return app


APP = _load_app()
def monitor(**kw) -> "APP.Monitor":
    mode = APP.Mode(2560, 1440, 143.86)
    values = dict(name="DP-1", description="Panel", modes=[mode], mode=mode,
                  scale=1.0, transform=0, x=0, y=0, enabled=True, index=1)
    values.update(kw)
    return APP.Monitor(**values)


def entry(name: str, mirror_of: str = "none") -> dict:
    return {"name": name, "description": "", "availableModes": ["2560x1440@143.86Hz"],
            "width": 2560, "height": 1440, "refreshRate": 143.86, "scale": 1.0,
            "transform": 0, "x": 0, "y": 0, "disabled": False, "mirrorOf": mirror_of}


class LuaPassthroughTests(unittest.TestCase):
    def test_lua_includes_mirror_when_set(self) -> None:
        line = monitor(name="HDMI-A-1", mirror="DP-1").lua()
        self.assertIn('mirror = "DP-1"', line)
        self.assertTrue(line.endswith(" })"))

    def test_lua_without_mirror_or_extra_is_unchanged(self) -> None:
        line = monitor().lua()
        self.assertNotIn("mirror", line)
        self.assertTrue(line.endswith("transform = 0 })"))

    def test_existing_monitor_call_sites_default_empty(self) -> None:
        mon = monitor()
        self.assertEqual(mon.mirror, "")
        self.assertEqual(mon.extra, {})


class PreserveKeysTests(unittest.TestCase):
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

    def test_replacing_rule_keeps_bitdepth_vrr_cm(self) -> None:
        self.write('hl.monitor({ output = "DP-1", mode = "2560x1440@143.86", '
                   'position = "0x0", scale = 1, transform = 0, bitdepth = 10, '
                   'cm = "hdr", vrr = 1, sdrbrightness = 1.2, sdrsaturation = 0.98 })\n'
                   'hl.monitor({ output = "DP-2", vrr = 2 })\n')
        mon = self.load([entry("DP-1")])["DP-1"]
        mon.x, mon.scale = 1920, 1.25
        line = mon.lua()
        for kept in ("bitdepth = 10", 'cm = "hdr"', "vrr = 1",
                     "sdrbrightness = 1.2", "sdrsaturation = 0.98"):
            self.assertIn(kept, line)
        self.assertIn('position = "1920x0"', line)
        self.assertIn("scale = 1.25", line)
        self.assertEqual(line.count("position ="), 1)
        self.assertEqual(line.count("scale ="), 1)
        self.assertNotIn("vrr = 2", line)

    def test_render_block_carries_kept_keys(self) -> None:
        self.write('hl.monitor({\n  output = "DP-1",\n  bitdepth = 10, -- deep\n'
                   '  cm = { primaries = "dcip3", "x,y" },\n})\n')
        mon = self.load([entry("DP-1")])["DP-1"]
        block = APP.render_block([mon])
        self.assertIn("bitdepth = 10", block)
        self.assertIn('cm = { primaries = "dcip3", "x,y" }', block)

    def test_last_matching_rule_wins_and_comments_ignored(self) -> None:
        self.write('hl.monitor({ output = "DP-1", vrr = 1 })\n'
                   '-- hl.monitor({ output = "DP-1", vrr = 9 })\n'
                   "hl.monitor({ output = 'DP-1', bitdepth = 8 })\n")
        mon = self.load([entry("DP-1")])["DP-1"]
        self.assertEqual(mon.extra, {"bitdepth": "8"})

    def test_mirror_of_is_loaded(self) -> None:
        loaded = self.load([entry("DP-1"), entry("HDMI-A-1", mirror_of="DP-1")])
        self.assertEqual(loaded["HDMI-A-1"].mirror, "DP-1")
        self.assertEqual(loaded["DP-1"].mirror, "")
        self.assertIn('mirror = "DP-1"', loaded["HDMI-A-1"].lua())
        self.assertNotIn("mirror", loaded["DP-1"].lua())

    def test_stale_mirror_key_in_file_is_not_kept(self) -> None:
        self.write('hl.monitor({ output = "DP-1", mirror = "HDMI-A-1" })\n')
        mon = self.load([entry("DP-1")])["DP-1"]
        self.assertNotIn("mirror", mon.lua())


if __name__ == "__main__":
    unittest.main()
