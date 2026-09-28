"""Regression tests for generated Lua and publication privacy."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
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


class PublicationPrivacyTests(unittest.TestCase):
    def test_tracked_release_files_do_not_contain_original_home_path(self) -> None:
        for path in (ROOT / "monitor-align", ROOT / "monitor-align.desktop"):
            self.assertNotIn("/home/" + "joshua", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
