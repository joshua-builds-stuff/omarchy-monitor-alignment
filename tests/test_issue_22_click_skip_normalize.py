"""Regression tests for #22: a click on a tile must not normalize the desk."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
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


def monitor(name: str, x: int, y: int = 0) -> "APP.Monitor":
    mode = APP.Mode(1920, 1080, 60.0)
    return APP.Monitor(name=name, description="", modes=[mode], mode=mode,
                       scale=1.0, transform=0, x=x, y=y, enabled=True, index=1)


class DragMovedTests(unittest.TestCase):
    def test_same_position_is_a_click(self) -> None:
        self.assertFalse(APP.drag_moved((100, 50), (100, 50)))

    def test_changed_position_is_a_move(self) -> None:
        self.assertTrue(APP.drag_moved((100, 50), (101, 50)))
        self.assertTrue(APP.drag_moved((100, 50), (100, 49)))


class CanvasReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        cls = APP.Canvas

        class App:
            def __init__(self) -> None:
                # An origin offset typed into Position X/Y.
                self.monitors = [monitor("eDP-1", 100, 40), monitor("DP-1", 2020, 40)]

            def select(self, _mon) -> None:
                pass

            def on_geometry_changed(self, redraw_only: bool = False) -> None:
                pass

        class FakeCanvas:
            _fit = cls.__dict__["_fit"]
            _view = cls.__dict__["_view"]
            _snap = cls.__dict__["_snap"]
            to_desktop = cls.__dict__["to_desktop"]
            to_widget = cls.__dict__["to_widget"]
            monitor_at = cls.__dict__["monitor_at"]
            _drag_begin = cls.__dict__["_drag_begin"]
            _drag_update = cls.__dict__["_drag_update"]
            _drag_end = cls.__dict__["_drag_end"]

            def __init__(self) -> None:
                self.app = App()
                self.zoom = 1.0
                self.offset = (0.0, 0.0)
                self.drag_target = None
                self.drag_origin = (0, 0)
                self.drag_view = (1.0, (0.0, 0.0))
                self.guides = []

            def get_width(self) -> int:
                return 800

            def get_height(self) -> int:
                return 500

            def set_cursor(self, _cursor) -> None:
                pass

        patcher = mock.patch.object(APP, "Gdk")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.canvas = FakeCanvas()
        self.canvas._view(800, 500)

    def press_on(self, mon) -> None:
        wx, wy = self.canvas.to_widget(mon.x + 10, mon.y + 10)
        self.canvas._drag_begin(None, wx, wy)
        self.assertIs(self.canvas.drag_target, mon)

    def test_click_keeps_typed_origin(self) -> None:
        first, second = self.canvas.app.monitors
        self.press_on(first)
        self.canvas._drag_end(None, 0, 0)
        self.assertIsNone(self.canvas.drag_target)
        self.assertEqual((first.x, first.y), (100, 40))
        self.assertEqual((second.x, second.y), (2020, 40))

    def test_real_drag_still_normalizes(self) -> None:
        first, _second = self.canvas.app.monitors
        self.press_on(first)
        self.canvas._drag_update(None, 0, 300)
        self.canvas._drag_end(None, 0, 300)
        active = APP.active_of(self.canvas.app.monitors)
        self.assertEqual(min(m.x for m in active), 0)
        self.assertEqual(min(m.y for m in active), 0)

    def test_release_offset_is_applied_without_a_final_update(self) -> None:
        first, _second = self.canvas.app.monitors
        self.press_on(first)
        self.canvas._drag_end(None, 0, 300)
        self.assertNotEqual((first.x, first.y), (100, 40))
        active = APP.active_of(self.canvas.app.monitors)
        self.assertEqual(min(m.y for m in active), 0)


if __name__ == "__main__":
    unittest.main()
