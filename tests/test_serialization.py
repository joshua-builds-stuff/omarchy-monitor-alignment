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


class PublicationPrivacyTests(unittest.TestCase):
    def test_tracked_release_files_do_not_contain_original_home_path(self) -> None:
        for path in (ROOT / "monitor-align", ROOT / "monitor-align.desktop"):
            self.assertNotIn("/home/" + "joshua", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
