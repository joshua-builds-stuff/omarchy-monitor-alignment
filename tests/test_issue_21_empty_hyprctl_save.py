"""Regression tests for #21: a failed hyprctl read must not reach save_lua."""

from __future__ import annotations

import importlib.util
import os
import pathlib
import subprocess
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


def completed(stdout: str, returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(["hyprctl"], returncode, stdout, "")


def fake_window(monitors, load_failed: bool):
    window = types.SimpleNamespace(monitors=monitors, load_failed=load_failed,
                                   warnings=[])
    window._warn = window.warnings.append
    window._refuse_write = lambda: APP.MonitorAlign._refuse_write(window)
    return window


class FailedLoadTests(unittest.TestCase):
    def test_timeout_is_a_failed_load(self) -> None:
        with mock.patch.object(APP.subprocess, "run",
                               side_effect=subprocess.TimeoutExpired("hyprctl", 5)):
            self.assertIsNone(APP.load_monitors())

    def test_non_json_is_a_failed_load(self) -> None:
        with mock.patch.object(APP.subprocess, "run",
                               return_value=completed("not json")):
            self.assertIsNone(APP.load_monitors())

    def test_nonzero_exit_is_a_failed_load(self) -> None:
        with mock.patch.object(APP.subprocess, "run",
                               return_value=completed("[]", returncode=1)):
            self.assertIsNone(APP.load_monitors())

    def test_empty_json_array_is_an_empty_desk(self) -> None:
        with mock.patch.object(APP.subprocess, "run",
                               return_value=completed("[]")):
            self.assertEqual(APP.load_monitors(), [])


class RefuseEmptySaveTests(unittest.TestCase):
    def test_apply_monitors_refuses_empty_list(self) -> None:
        with mock.patch.object(APP.subprocess, "run") as run:
            ok, _ = APP.apply_monitors([])
        self.assertFalse(ok)
        run.assert_not_called()

    def test_save_lua_refuses_empty_block_without_confirm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "monitors.lua")
            original = (APP.BLOCK_BEGIN + "\nhl.monitor({ output = \"DP-1\" })\n"
                        + APP.BLOCK_END + "\n")
            with open(path, "w") as handle:
                handle.write(original)
            with mock.patch.object(APP, "MONITORS_LUA", path), \
                    mock.patch.object(APP, "hyprctl") as hyprctl:
                ok, _ = APP.save_lua([])
            with open(path) as handle:
                self.assertEqual(handle.read(), original)
            self.assertEqual(os.listdir(tmp), ["monitors.lua"])
        self.assertFalse(ok)
        hyprctl.assert_not_called()

    def test_save_after_failed_load_never_reaches_save_lua(self) -> None:
        window = fake_window([], load_failed=True)
        with mock.patch.object(APP, "save_lua") as save, \
                mock.patch.object(APP, "apply_monitors") as apply:
            APP.MonitorAlign._on_save(window)
        save.assert_not_called()
        apply.assert_not_called()
        self.assertTrue(window.warnings)

    def test_save_with_empty_model_never_reaches_save_lua(self) -> None:
        window = fake_window([], load_failed=False)
        with mock.patch.object(APP, "save_lua") as save, \
                mock.patch.object(APP, "apply_monitors") as apply:
            APP.MonitorAlign._on_save(window)
        save.assert_not_called()
        apply.assert_not_called()

    def test_try_it_after_failed_load_is_refused(self) -> None:
        window = fake_window([object()], load_failed=True)
        with mock.patch.object(APP, "apply_monitors") as apply:
            APP.MonitorAlign._on_apply(window)
        apply.assert_not_called()
        self.assertTrue(window.warnings)


if __name__ == "__main__":
    unittest.main()
