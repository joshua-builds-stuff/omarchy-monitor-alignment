"""Regression tests for #23: save_lua keeps text after the block after it."""

from __future__ import annotations

import importlib.util
import os
import pathlib
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
LOADER = SourceFileLoader("monitor_align", str(ROOT / "monitor-align"))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load monitor-align")
APP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = APP
SPEC.loader.exec_module(APP)


def monitor(name: str, x: int) -> "APP.Monitor":
    mode = APP.Mode(1920, 1080, 60.0)
    return APP.Monitor(name=name, description="Display", modes=[mode], mode=mode,
                       scale=1.0, transform=0, x=x, y=0, enabled=True, index=1)


class BlockTailOrderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "monitors.lua")
        for name, value in (("MONITORS_LUA", self.path),
                            ("hyprctl", mock.Mock(return_value="")),
                            ("apply_monitors", mock.Mock(return_value=(True, "ok"))),
                            ("config_errors", mock.Mock(return_value=set()))):
            patcher = mock.patch.object(APP, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def save(self, original: str) -> str:
        with open(self.path, "w") as handle:
            handle.write(original)
        ok, message = APP.save_lua([monitor("DP-1", 0)])
        self.assertTrue(ok, message)
        with open(self.path) as handle:
            return handle.read()

    def test_line_after_block_end_stays_after_block_end(self) -> None:
        original = ("-- header\n"
                    + APP.BLOCK_BEGIN + "\nhl.monitor({ output = \"OLD\" })\n"
                    + APP.BLOCK_END + "\n"
                    + "hl.monitor({ output = \"HDMI-A-1\", disabled = true })\n")
        saved = self.save(original)

        self.assertEqual(saved.count(APP.BLOCK_BEGIN), 1)
        self.assertEqual(saved.count(APP.BLOCK_END), 1)
        self.assertLess(saved.index("-- header"), saved.index(APP.BLOCK_BEGIN))
        self.assertGreater(saved.index('"HDMI-A-1"'), saved.index(APP.BLOCK_END))
        self.assertNotIn('"OLD"', saved)
        self.assertIn('"DP-1"', saved)

    def test_file_without_block_still_appends(self) -> None:
        saved = self.save("-- header\n")
        self.assertTrue(saved.startswith("-- header\n\n" + APP.BLOCK_BEGIN))
        self.assertTrue(saved.endswith(APP.BLOCK_END + "\n"))


if __name__ == "__main__":
    unittest.main()
