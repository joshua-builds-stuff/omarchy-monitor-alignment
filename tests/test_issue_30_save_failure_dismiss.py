"""Regression tests for #30: a failed Save must retire the Keep/Revert prompt."""

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
    loader = SourceFileLoader("monitor_align_issue_30", str(ROOT / "monitor-align"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    app = importlib.util.module_from_spec(spec)
    with mock.patch.dict(sys.modules, stubs), mock.patch("ctypes.CDLL"):
        sys.modules[loader.name] = app
        loader.exec_module(app)
    return app


APP = _load_app()


class FakeDialog:
    def __init__(self, **_kw) -> None:
        self.handlers = []
        self.closed = False

    def connect(self, _signal, handler) -> None:
        self.handlers.append(handler)

    def respond(self, response: str) -> None:
        for handler in self.handlers:
            handler(self, response)

    def force_close(self) -> None:
        self.closed = True

    def close(self) -> None:
        self.respond("revert")

    def __getattr__(self, _name):
        return lambda *a, **k: None


class FakeGLib:
    SOURCE_REMOVE = False
    SOURCE_CONTINUE = True

    def __init__(self) -> None:
        self.timers = {}
        self.next_id = 1

    def timeout_add_seconds(self, _secs, fn) -> int:
        self.next_id += 1
        self.timers[self.next_id] = fn
        return self.next_id

    def timeout_add(self, _ms, fn) -> int:
        return self.timeout_add_seconds(0, fn)

    def source_remove(self, source) -> None:
        self.timers.pop(source, None)


def live_monitor(x: int) -> "APP.Monitor":
    mode = APP.Mode(1920, 1080, 60.0)
    return APP.Monitor(name="DP-1", description="Display", modes=[mode], mode=mode,
                       scale=1.0, transform=0, x=x, y=0, enabled=True, index=1)


class SaveFailureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dialogs: list[FakeDialog] = []

        def make_dialog(**kw):
            dialog = FakeDialog(**kw)
            self.dialogs.append(dialog)
            return dialog

        self.glib = FakeGLib()
        adw = type("Adw", (), {"AlertDialog": staticmethod(make_dialog),
                               "ResponseAppearance": type("RA", (), {
                                   "SUGGESTED": 1, "DESTRUCTIVE": 2})})
        self.restored = live_monitor(0)
        for name, value in (("Adw", adw), ("GLib", self.glib),
                            ("hyprctl_eval", mock.Mock(return_value=(True, "ok"))),
                            ("apply_monitors", mock.Mock(return_value=(True, "ok"))),
                            ("save_lua", mock.Mock(return_value=(False, "config error — restored"))),
                            ("load_monitors", mock.Mock(return_value=[self.restored]))):
            patcher = mock.patch.object(APP, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

        cls = APP.MonitorAlign

        class Window:
            _dismiss_pending = cls._dismiss_pending
            _confirm_keep = cls._confirm_keep
            _save = cls._save
            _on_close = cls._on_close

            def __init__(self) -> None:
                self._pending = None
                self.monitors = [live_monitor(1920)]
                self.baseline = [live_monitor(0).lua()]
                self.applied = list(self.baseline)
                self.toasts = []
                self.warnings = []
                self.identify_syncs = 0
                self.identify = mock.Mock()
                self.banner = mock.Mock()

            def _refuse_write(self) -> bool:
                return False

            def _sync_identify(self, restructure: bool = False) -> None:
                self.identify_syncs += 1

            def reload(self) -> None:
                pass

            def _toast(self, text) -> None:
                self.toasts.append(text)

            def _warn(self, text) -> None:
                self.warnings.append(text)

        self.win = Window()

    def try_it(self) -> FakeDialog:
        self.win.applied = [m.lua() for m in self.win.monitors]
        self.win._confirm_keep()
        return self.dialogs[-1]

    def test_failed_save_dismisses_prompt_and_keep_cannot_adopt(self) -> None:
        dialog = self.try_it()
        tried = list(self.win.applied)
        kept = list(self.win.baseline)

        self.win._save()

        self.assertIsNone(self.win._pending)
        self.assertTrue(dialog.closed)
        self.assertEqual(self.glib.timers, {})
        self.assertEqual(self.win.applied, [self.restored.lua()])
        self.assertGreaterEqual(self.win.identify_syncs, 1)
        self.assertIn("config error — restored", self.win.warnings)

        dialog.respond("keep")  # a late Keep must not adopt the rolled-back layout
        self.assertEqual(self.win.baseline, kept)
        self.assertNotEqual(self.win.baseline, tried)
        self.assertEqual(self.win.toasts, [])

    def test_failed_save_marks_snapshot_rolled_back(self) -> None:
        self.try_it()
        state = self.win._pending
        self.win._save()
        self.assertTrue(state["rolled_back"])

    def test_failed_save_with_unreadable_hyprctl_clears_applied(self) -> None:
        self.try_it()
        with mock.patch.object(APP, "load_monitors", mock.Mock(return_value=None)):
            self.win._save()
        self.assertEqual(self.win.applied, [])

    def test_close_cancels_pending_prompt(self) -> None:
        dialog = self.try_it()
        self.assertEqual(len(self.glib.timers), 1)
        self.assertIs(self.win._on_close(), False)
        self.assertIsNone(self.win._pending)
        self.assertTrue(dialog.closed)
        self.assertEqual(self.glib.timers, {})
        self.win.identify.hide.assert_called_once()


if __name__ == "__main__":
    unittest.main()
