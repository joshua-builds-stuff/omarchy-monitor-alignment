# Changelog

All notable changes to this project are documented here.

The application version remains **1.0.0**. The dated entries below are minor revisions of behavior already shipped on `main`.

## 2026-09-30 (minor)

- Refused **Try it** and **Save** after `hyprctl -j monitors all` fails (timeout, non-zero exit, or a result that is not a JSON list) or returns no monitors. Neither button applies an arrangement or writes `monitors.lua`. A failed reload that already had displays leaves them on the canvas. The banner is `Could not read monitors from hyprctl — reload before applying or saving` after a failed read, and `No monitors loaded — nothing to apply or save` when the desk is empty (#25).
- A click on a canvas tile selects that display and leaves **Position X** and **Position Y** unchanged, including an origin other than `0,0`. A drag that moves the tile still shifts the enabled group's top-left to `0,0` (#26).
- Save replaces the generated block in place when `monitors.lua` contains both markers, so lines after `-- <<< monitor-align` stay after the rewritten block. When the file has other text and lacks either marker, that text is kept and the block is appended after a blank line (#27).
- Backup names use a nanosecond stamp, `monitors.lua.bak.<timestamp>`, and `.1`, `.2`, … when that name already exists, so an earlier backup is never overwritten. A **Save** that starts while another save is still running is ignored (#28).

## 2026-09-29 (minor)

- Shifted every display, including disabled ones, when moving the enabled group's top-left to `0,0`, so a disabled panel keeps its relative position (#16).
- Froze the canvas zoom and offset for the duration of a drag so the display stays under the pointer, and refitted the canvas when the drag ends (#17).
- When Keep/Revert cannot apply the previous arrangement, showed `Could not revert:` and did not toast `Reverted` or reload the window (#18).
- After a failed Save restores `monitors.lua` from its backup, re-applied the `hl.monitor` lines from that file's generated block. If that re-apply fails, the banner adds `could not re-apply its layout:`. A backup with no generated block, and a file this save created, are reloaded without that re-apply (#19).

## 2026-09-28 (minor)

- Snapped fractional scales reported by `hyprctl` onto Hyprland's 1/120 lattice. `hyprctl` prints two decimal places, so `4/3` arrives as `1.33` and `5/3` as `1.67`. Arrange, edge snapping, and Identify compute logical size from the snapped scale, and generated Lua writes that scale (#6).
- Kept a single Try it confirmation. A newer Try it replaces the open Keep/Revert dialog and cancels its 15-second timer, so an older countdown cannot revert a newer attempt (#7).
- Save ignores config errors Hyprland already had, writes `monitors.lua` by renaming a temporary file into place, and restores the previous file when the re-apply after `hyprctl reload` fails or Hyprland reports a new config error. A file created by that save is removed instead (#8).
- Kept the Identify overlay in sync with Position X/Y edits, including the grids and the PREVIEW chip (#9).
- Removed unused `Monitor.copy()`. No user-facing behavior change (#1).

## 1.0.0 - 2026-09-03

- Initial public release of the visual Hyprland monitor arrangement tool.
- Added timed live rollback, persistent `monitors.lua` updates, backups, and display-identification overlays.
- Removed maintainer-specific paths from the desktop launcher.
- Added safe Lua string and comment serialization for monitor metadata.
- Added publication privacy and serialization regression tests.
