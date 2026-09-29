"""Regression tests for generated Lua and publication privacy."""

from __future__ import annotations

import importlib.util
import os
import pathlib
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader


ROOT = pathlib.Path(__file__).resolve().parents[1]
LOADER = SourceFileLoader("monitor_align", str(ROOT / "monitor-align"))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load monitor-align")
APP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = APP
SPEC.loader.exec_module(APP)


class SerializationTests(unittest.TestCase):
    def test_lua_string_escapes_syntax_and_line_breaks(self) -> None:
        value = 'DP-1"\\\n\r\t\u2028'
        encoded = APP.lua_string(value)

        self.assertEqual(encoded, '"DP-1\\"\\\\\\n\\r\\t\\226\\128\\168"')
        self.assertNotIn("\n", encoded)
        self.assertNotIn("\r", encoded)
        self.assertNotIn("\u2028", encoded)

    def test_lua_string_handles_unpaired_surrogate_data(self) -> None:
        encoded = APP.lua_string("DP-1\ud800")

        self.assertEqual(encoded, '"DP-1\\237\\160\\128"')

    def test_comment_text_stays_on_one_line_and_hides_markers(self) -> None:
        value = "Display\nhl.monitor({ disabled = true })\r" + APP.BLOCK_END
        cleaned = APP.lua_comment_text(value)

        self.assertNotIn("\n", cleaned)
        self.assertNotIn("\r", cleaned)
        self.assertNotIn(APP.BLOCK_END, cleaned)
        self.assertIn("hl.monitor", cleaned)

    def test_rendered_description_cannot_add_a_lua_line(self) -> None:
        mode = APP.Mode(1920, 1080, 60.0)
        monitor = APP.Monitor(
            name='DP-1" }})\\nunsafe(',
            description="Display\nhl.monitor({ output = 'eDP-1', disabled = true })",
            modes=[mode],
            mode=mode,
            scale=1.0,
            transform=0,
            x=0,
            y=0,
            enabled=True,
            index=1,
        )

        rendered = APP.render_block([monitor])
        self.assertNotIn("\nhl.monitor({ output = 'eDP-1'", rendered)
        self.assertIn('output = "DP-1\\" }})\\\\nunsafe("', rendered)


class FractionalScaleTests(unittest.TestCase):
    def monitor(self, w: int, h: int, scale: float) -> "APP.Monitor":
        mode = APP.Mode(w, h, 60.0)
        return APP.Monitor(name="DP-1", description="", modes=[mode], mode=mode,
                           scale=APP.snap_scale(mode, scale), transform=0,
                           x=0, y=0, enabled=True, index=1)

    def test_two_decimal_scales_snap_to_the_real_lattice_value(self) -> None:
        self.assertEqual(self.monitor(2560, 1440, 1.33).scale, 160 / 120)
        self.assertEqual(self.monitor(2560, 1600, 1.67).scale, 200 / 120)
        self.assertEqual(self.monitor(1920, 1080, 1.25).scale, 1.25)

    def test_snapped_scale_gives_exact_logical_size(self) -> None:
        mon = self.monitor(2560, 1440, 1.33)
        self.assertEqual(mon.logical, (1920, 1080))
        self.assertTrue(mon.scale_ok())
        self.assertEqual(self.monitor(2560, 1600, 1.67).logical, (1536, 960))

    def test_raw_two_decimal_scale_is_flagged(self) -> None:
        mode = APP.Mode(2560, 1440, 60.0)
        self.assertFalse(APP.scale_fits(mode, 1.33))

    def test_lua_scale_round_trips_to_the_same_step(self) -> None:
        mon = self.monitor(2560, 1440, 1.33)
        written = mon.lua().split("scale = ")[1].split(",")[0]
        self.assertEqual(round(float(written) * 120), 160)
        self.assertEqual(APP.snap_scale(mon.mode, float(written)), mon.scale)

    def test_unfit_scale_falls_back_to_nearest_step(self) -> None:
        mode = APP.Mode(1366, 768, 60.0)
        self.assertEqual(APP.snap_scale(mode, 1.33), 160 / 120)


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

    def source_remove(self, source) -> None:
        self.timers.pop(source, None)


class TryItConfirmationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dialogs: list[FakeDialog] = []
        self.evals: list[str] = []
        self.saved = (APP.Adw, APP.GLib, APP.hyprctl_eval)

        def make_dialog(**kw):
            dialog = FakeDialog(**kw)
            self.dialogs.append(dialog)
            return dialog

        APP.Adw = type("Adw", (), {"AlertDialog": staticmethod(make_dialog),
                                   "ResponseAppearance": type("RA", (), {
                                       "SUGGESTED": 1, "DESTRUCTIVE": 2})})
        self.glib = FakeGLib()
        APP.GLib = self.glib
        APP.hyprctl_eval = lambda chunk: (self.evals.append(chunk), (True, "ok"))[1]

        cls = APP.MonitorAlign

        class Window:
            _dismiss_pending = cls._dismiss_pending
            _confirm_keep = cls._confirm_keep

            def __init__(self) -> None:
                self._pending = None
                self.baseline = ["kept"]
                self.applied = ["kept"]
                self.reloads = 0

            def reload(self) -> None:
                self.reloads += 1

            def _toast(self, _text) -> None:
                pass

        self.win = Window()

    def tearDown(self) -> None:
        APP.Adw, APP.GLib, APP.hyprctl_eval = self.saved

    def try_it(self, layout: str) -> FakeDialog:
        self.win.applied = [layout]
        self.win._confirm_keep()
        return self.dialogs[-1]

    def test_second_try_replaces_first_prompt(self) -> None:
        first = self.try_it("A")
        second = self.try_it("B")
        self.assertTrue(first.closed)
        self.assertEqual(len(self.glib.timers), 1)
        first.respond("revert")  # stale: must not touch the live layout
        self.assertEqual(self.evals, [])
        self.assertEqual(self.win.reloads, 0)
        second.respond("keep")
        self.assertEqual(self.win.baseline, ["B"])

    def test_revert_uses_last_kept_layout_captured_at_open(self) -> None:
        self.try_it("A")
        second = self.try_it("B")
        self.win.baseline = ["changed-after-open"]
        second.respond("revert")
        self.assertEqual(self.evals, ["kept"])
        self.assertEqual(self.win.reloads, 1)

    def test_keep_stores_the_applied_layout_not_later_edits(self) -> None:
        dialog = self.try_it("A")
        self.win.applied = ["edited"]
        dialog.respond("keep")
        self.assertEqual(self.win.baseline, ["A"])

    def test_stale_timer_stops_without_reverting(self) -> None:
        self.try_it("A")
        stale_tick = next(iter(self.glib.timers.values()))
        self.try_it("B")
        self.assertIs(stale_tick(), False)
        self.assertEqual(self.evals, [])


class SaveLuaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "hypr", "monitors.lua")
        self.saved = (APP.MONITORS_LUA, APP.hyprctl, APP.apply_monitors)
        APP.MONITORS_LUA = self.path
        self.errors_before = "no errors"
        self.errors_after = "no errors"
        self.apply_result = (True, "ok")
        self.reloaded = False

        def fake_hyprctl(*args):
            if args == ("reload",):
                self.reloaded = True
                return "ok"
            if args == ("configerrors",):
                return self.errors_after if self.reloaded else self.errors_before
            return ""

        APP.hyprctl = fake_hyprctl
        APP.apply_monitors = lambda _m: self.apply_result
        mode = APP.Mode(1920, 1080, 60.0)
        self.monitors = [APP.Monitor(name="DP-1", description="", modes=[mode],
                                     mode=mode, scale=1.0, transform=0, x=0, y=0,
                                     enabled=True, index=1)]

    def tearDown(self) -> None:
        APP.MONITORS_LUA, APP.hyprctl, APP.apply_monitors = self.saved
        self.tmp.cleanup()

    def write_original(self, text: str = "-- mine\n") -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as handle:
            handle.write(text)

    def read(self) -> str:
        with open(self.path) as handle:
            return handle.read()

    def test_pre_existing_config_errors_do_not_fail_save(self) -> None:
        self.write_original()
        self.errors_before = "hyprland.lua:3: unrelated"
        self.errors_after = "hyprland.lua:3: unrelated"
        ok, message = APP.save_lua(self.monitors)
        self.assertTrue(ok, message)
        self.assertIn(APP.BLOCK_BEGIN, self.read())

    def test_new_config_error_restores_backup_and_names_it(self) -> None:
        self.write_original()
        self.errors_after = "monitors.lua:4: bad"
        ok, message = APP.save_lua(self.monitors)
        self.assertFalse(ok)
        self.assertIn("monitors.lua:4: bad", message)
        self.assertIn("monitors.lua.bak.", message)
        self.assertEqual(self.read(), "-- mine\n")

    def test_failed_live_apply_is_reported_and_rolled_back(self) -> None:
        self.write_original()
        self.apply_result = (False, "nope")
        ok, message = APP.save_lua(self.monitors)
        self.assertFalse(ok)
        self.assertIn("nope", message)
        self.assertEqual(self.read(), "-- mine\n")

    def test_failed_first_save_removes_new_file(self) -> None:
        self.errors_after = "monitors.lua:2: bad"
        ok, _message = APP.save_lua(self.monitors)
        self.assertFalse(ok)
        self.assertFalse(os.path.exists(self.path))

    def test_write_error_leaves_original_and_names_backup(self) -> None:
        self.write_original()
        real_replace = os.replace

        def broken_replace(*_a):
            raise OSError("disk full")

        APP.os.replace = broken_replace
        try:
            ok, message = APP.save_lua(self.monitors)
        finally:
            APP.os.replace = real_replace
        self.assertFalse(ok)
        self.assertIn("disk full", message)
        self.assertIn("monitors.lua.bak.", message)
        self.assertEqual(self.read(), "-- mine\n")
        self.assertFalse(any(".tmp." in f for f in os.listdir(os.path.dirname(self.path))))


class PositionRowTests(unittest.TestCase):
    def test_position_nudge_updates_identify_overlay(self) -> None:
        cls = APP.MonitorAlign
        mode = APP.Mode(1920, 1080, 60.0)
        mon = APP.Monitor(name="DP-1", description="", modes=[mode], mode=mode,
                          scale=1.0, transform=0, x=0, y=0, enabled=True, index=1)

        class Row:
            def __init__(self, value) -> None:
                self.value = value

            def get_value(self):
                return self.value

        class Toggle:
            def get_active(self) -> bool:
                return True

        class Overlay:
            visible = True
            pending = False
            bound = None

            def rebind(self, monitors) -> None:
                self.bound = [(m.x, m.y) for m in monitors]

            def show(self, monitors) -> None:
                self.rebind(monitors)

        class Canvas:
            def queue_draw(self) -> None:
                pass

        class Window:
            _on_position = cls._on_position
            on_geometry_changed = cls.on_geometry_changed
            _sync_identify = cls._sync_identify

            def __init__(self) -> None:
                self._loading = False
                self.selected = mon
                self.monitors = [mon]
                self.applied = [mon.lua()]
                self.x_row, self.y_row = Row(7), Row(-3)
                self.identify_button = Toggle()
                self.identify = Overlay()
                self.canvas = Canvas()
                self.checked = 0

            def refresh_controls(self) -> None:
                pass

            def _check(self) -> None:
                self.checked += 1

        win = Window()
        win._on_position(win.x_row, None)
        self.assertEqual((mon.x, mon.y), (7, -3))
        self.assertEqual(win.identify.bound, [(7, -3)])
        self.assertTrue(win.identify.pending)
        self.assertEqual(win.checked, 1)


class NormalizeTests(unittest.TestCase):
    def monitor(self, name: str, w: int, h: int, x: int, y: int) -> "APP.Monitor":
        mode = APP.Mode(w, h, 60.0)
        return APP.Monitor(name=name, description="", modes=[mode], mode=mode,
                           scale=1.0, transform=0, x=x, y=y, enabled=True, index=1)

    def test_disabling_left_display_keeps_it_beside_the_shifted_group(self) -> None:
        left = self.monitor("eDP-1", 1920, 1080, 0, 0)
        right = self.monitor("DP-1", 2560, 1440, 1920, 0)
        left.enabled = False
        APP.normalize([left, right])
        self.assertEqual((right.x, right.y), (0, 0))
        self.assertEqual((left.x, left.y), (-1920, 0))

    def test_disabling_top_display_keeps_it_above_the_shifted_group(self) -> None:
        top = self.monitor("eDP-1", 1920, 1080, 0, 0)
        bottom = self.monitor("DP-1", 1920, 1080, 0, 1080)
        top.enabled = False
        APP.normalize([top, bottom])
        self.assertEqual((bottom.x, bottom.y), (0, 0))
        self.assertEqual((top.x, top.y), (0, -1080))

class CanvasDragTests(unittest.TestCase):
    def setUp(self) -> None:
        cls = APP.Canvas

        def monitor(name: str, x: int) -> "APP.Monitor":
            mode = APP.Mode(1920, 1080, 60.0)
            return APP.Monitor(name=name, description="", modes=[mode], mode=mode,
                               scale=1.0, transform=0, x=x, y=0, enabled=True, index=1)

        class App:
            def __init__(self) -> None:
                self.monitors = [monitor("eDP-1", 0), monitor("DP-1", 1920)]

            def select(self, _mon) -> None:
                pass

            def on_geometry_changed(self, redraw_only: bool = False) -> None:
                pass

        class FakeCanvas:
            _fit = cls.__dict__["_fit"]
            _view = cls.__dict__["_view"]
            _snap = cls.__dict__["_snap"]
            to_desktop = cls.__dict__["to_desktop"]
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

        self.canvas = FakeCanvas()
        self.canvas._view(800, 500)

    def test_drag_keeps_projection_and_follows_pointer(self) -> None:
        canvas = self.canvas
        zoom, offset = canvas.zoom, canvas.offset
        start = zoom * 1920 + offset[0] + 10
        canvas._drag_begin(None, start, 250)
        dragged = canvas.drag_target
        self.assertEqual(dragged.name, "DP-1")
        for step in (30, 150, 450):
            canvas._drag_update(None, step, 0)
            canvas._view(800, 500)  # what every repaint does
            self.assertEqual((canvas.zoom, canvas.offset), (zoom, offset))
        self.assertAlmostEqual(dragged.x, 1920 + 450 / zoom, delta=1)

    def test_drag_end_refits_after_normalize(self) -> None:
        canvas = self.canvas
        zoom = canvas.zoom
        canvas._drag_begin(None, zoom * 1920 + canvas.offset[0] + 10, 250)
        canvas._drag_update(None, 450, 0)
        canvas._drag_end(None, 450, 0)
        self.assertIsNone(canvas.drag_target)
        self.assertLess(canvas.zoom, zoom)


class PublicationPrivacyTests(unittest.TestCase):
    def test_tracked_release_files_do_not_contain_original_home_path(self) -> None:
        for path in (ROOT / "monitor-align", ROOT / "monitor-align.desktop"):
            self.assertNotIn("/home/" + "joshua", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
