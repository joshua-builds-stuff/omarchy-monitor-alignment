"""Regression tests for #24: a second save must not overwrite the first backup."""

from __future__ import annotations

import importlib.util
import os
import pathlib
import sys
import tempfile
import types
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


class UniqueBackupTests(unittest.TestCase):
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

    def backups(self) -> list[str]:
        return sorted(n for n in os.listdir(self.tmp.name) if ".bak." in n)

    def test_two_saves_in_one_second_keep_first_backup(self) -> None:
        original = b"-- the user's original monitors.lua\n"
        with open(self.path, "wb") as handle:
            handle.write(original)

        # Same wall-clock second and same nanosecond stamp for both saves.
        with mock.patch.object(APP.time, "time", return_value=1_700_000_000.0), \
                mock.patch.object(APP.time, "time_ns", return_value=1_700_000_000_000_000_000):
            ok, message = APP.save_lua([monitor("DP-1", 0)])
            self.assertTrue(ok, message)
            first = self.backups()
            self.assertEqual(len(first), 1)
            ok, message = APP.save_lua([monitor("DP-1", 1920)])
            self.assertTrue(ok, message)

        backups = self.backups()
        self.assertEqual(len(backups), 2)
        with open(os.path.join(self.tmp.name, first[0]), "rb") as handle:
            self.assertEqual(handle.read(), original)

    def test_save_ignored_while_a_save_is_running(self) -> None:
        window = types.SimpleNamespace(_saving=True, _save=mock.Mock())
        APP.MonitorAlign._on_save(window)
        window._save.assert_not_called()

    def test_save_flag_resets_after_save(self) -> None:
        window = types.SimpleNamespace(_saving=False, _save=mock.Mock())
        APP.MonitorAlign._on_save(window)
        window._save.assert_called_once()
        self.assertFalse(window._saving)


if __name__ == "__main__":
    unittest.main()
