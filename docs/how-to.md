# Using Monitor Align

This is the operator guide for `monitor-align` as shipped. Install, package names, and the privacy summary stay in the [README](../README.md). The window title is **Monitor Align**.

The app reads the current desk from `hyprctl`, lets you edit it, and can push the result live. Persistent configuration is the generated block in `~/.config/hypr/monitors.lua`.

## Open the window

Launch **Monitor Align** from the application menu, or run:

```bash
monitor-align
```

The session must be Wayland, and `hyprctl` must be on `PATH`. Otherwise the program exits before opening a window.

The header has **Identify**, a reload button (the refresh icon; tooltip “Reload the live configuration, discarding changes”), **Try it**, and **Save**. The sidebar has **Arrangement**, the selected **Display**, and a **Preview** of the Lua block that Save would write.

The refresh button reads the desk again with `hyprctl -j monitors all`. It is not **Revert** on the Try it dialog. When that read succeeds, unapplied edits are discarded and the window shows the desk `hyprctl` reported. When the read fails and the window already has displays, those displays and their edits stay, and the banner shows `Could not read monitors from hyprctl — is Hyprland running?`.

A read that times out, exits non-zero, or does not return a JSON list is a failed load. **Try it** and **Save** stay refused until a later reload succeeds. The banner on that reload is `Could not read monitors from hyprctl — is Hyprland running?`. When the window had no displays yet, the model stays empty.

A read that returns an empty JSON list is an empty desk: the window has no displays, and the geometry check that follows a successful load clears the banner when there is nothing to report. **Try it** and **Save** stay refused until a reload returns at least one monitor. Those buttons warn `No monitors loaded — nothing to apply or save`.

## Scale

Hyprland honors scales on a 1/120 lattice. `hyprctl -j monitors` prints the scale to two decimal places, so `4/3` arrives as `1.33` and `5/3` as `1.67`. On load, `monitor-align` snaps that printed value before storing it.

When a lattice scale that divides the mode into an integer logical size sits within `0.0051` of the printed value, that scale is stored. For a 2560×1440 mode, `1.33` becomes `4/3` (`160/120`) and the logical size is 1920×1080. For a 2560×1600 mode, `1.67` becomes `5/3` (`200/120`) and the logical size is 1536×960. A printed `1.25` stays `1.25`. A non-positive report is stored as `1.0`. If no fitting scale is that close, the nearest 1/120 step is stored, and not a step below `1/120`.

Logical size is the mode divided by that snapped scale, rounded to integers, with width and height swapped for the rotated transforms (90°, 270°, and the flipped 90° and 270° variants). **Arrange**, edge snapping, and the Identify grid use that size. The generated Lua writes the snapped scale (enough digits to land on the same step again, such as `1.333333333` for `4/3`). The Scale row shows the lattice value, not the two-decimal print: `4/3` is labeled `1.3333×`, and `5/3` is labeled `1.6667×`.

The **Scale** combo is built from the targets 1, 1.25, 1.3333, 1.5, 1.6, 1.75, 2, 2.25, 2.5, and 3. Each target contributes the nearest valid step for the current mode when that step is closer than `0.01`. The current scale is added when it is not already listed. Valid steps run from `0.5` to `3` in increments of `1/120` and must divide both mode sides exactly. Changing **Resolution** selects the highest refresh rate listed for that resolution and, when the current scale no longer fits, moves to the nearest valid scale (or `1.0` when the mode has none). A scale that is still not exact is named in the banner: Hyprland will adjust it.

## Arrange

Drag a display on the canvas. Edges and centres snap to neighbouring displays. The hint under the canvas describes that snap.

The canvas records its zoom and offset when the drag starts. While the drag continues, repaints keep that projection, and the pointer's movement is divided by that zoom, so the display stays under the pointer. When the gesture ends, the canvas refits to the desktop.

A click that does not move the tile selects that display and leaves every position as it was. **Position X** and **Position Y** keep the origin you typed, including a value other than `0,0`. Releasing a drag whose offset moved the tile applies that move, then shifts the desktop so the enabled group's top-left sits at `0,0`.

**Position X** and **Position Y**, on the selected display, accept whole pixels from -20000 to 20000. Editing either of them updates the canvas immediately and leaves the other displays where they are. Typing a position does not run the shift to `0,0`.

**Arrange**, under **Arrangement**, packs enabled displays edge to edge in their current order. **Direction** is `Row — left to right` or `Column — top to bottom`. **Align on** is `Top edges`, `Centers`, or `Bottom edges` in a row, and `Left edges`, `Centers`, or `Right edges` in a column. **Landscape** and **Portrait** under **Rotate every display** set every enabled display, then pack them the same way.

**Order**, on the selected display, moves that display earlier or later in the current order (tooltips: “Move earlier (left, or up)” and “Move later (right, or down)”), then packs again. The **Enabled** switch turns the selected display on or off. Turning off the last enabled display is rejected with the toast `At least one display has to stay on`.

After a drag that moved its tile, and after an accepted **Enabled** change, Arrange, Order, scale, orientation, or resolution, the desktop is shifted so the top-left of the enabled displays sits at `0,0`. Every display is shifted by that same amount, including disabled ones, so a disabled panel keeps its position relative to the enabled group. A disabled display that sat to the left or above that group can end at a negative origin. A click on a tile does not run this shift.

Turning a display off does not drop that place from the generated rule. **Save**, and the sidebar **Preview**, write `mode`, `position`, `scale`, and `transform` on the disabled line, plus `disabled = true`. An enabled line does not gain a `disabled` key. On the next load, a disabled output that `hyprctl` reports at `0x0` takes its position from the last `hl.monitor` line for that output in `monitors.lua`. A non-zero position from `hyprctl` is kept. If that last line has no `position = "XxY"`, the `0x0` report is kept, including when an earlier line for the same output had a position. A commented-out line is not used. A missing `monitors.lua` leaves the `hyprctl` position.

## Identify

**Identify** in the header toggles a numbered coordinate grid on each enabled display whose connector name matches a screen (tooltip: “Show a numbered alignment grid on every screen”). The grids stay up until you toggle them off. Turning the toggle on toasts `Grid stays up while you drag — line the major lines up across the bezel to match the offset`.

The same minor and major spacing is used on every screen, chosen from the smallest enabled logical edge so the densest display stays readable. Major lines are labeled with global desktop coordinates. Each overlay also shows the display number, connector name, description, mode, refresh rate, scale, transform, origin, and logical size, plus a marker where a neighbouring display shares an edge.

While Identify is on, geometry edits repaint those grids from the arrangement in the window. **Position X** and **Position Y** do this on each change, and so do dragging, scale, orientation, resolution, and Arrange. The corner chips and the origin line follow the new geometry. Changing **Refresh rate** updates the Lua preview in the sidebar. The grids repaint when geometry changes.

When Identify refreshes and the window's generated Lua differs from the last applied arrangement, each grid draws this chip:

`PREVIEW — press “Try it” to move the screens`

After a successful **Try it** or **Save**, if Identify is still on, the grids are shown again from the arrangement that was applied. When that matches the window, the chip is absent.

The desktop launcher’s **Identify Screens** action, and the command below, show the grid for the live desk and leave the editor closed. Those grids are drawn without the PREVIEW chip:

```bash
monitor-align --identify 15
```

The first number after `--identify` is how many seconds the grids stay up. The launcher passes `15`. With no number, they stay up for 8 seconds.

To print the installed version (`monitor-align 1.0.0`):

```bash
monitor-align --version
```

## Try it

**Try it** pushes the current arrangement to Hyprland immediately (tooltip: “Apply live with a 15 second auto-revert”).

**Try it** does not call `hyprctl` when the last load failed or the window has no monitors. After a failed load the banner is `Could not read monitors from hyprctl — reload before applying or saving`. With an empty desk it is `No monitors loaded — nothing to apply or save`. No confirmation dialog opens. Use the refresh button to read the desk again.

When monitors are loaded and the apply fails, the banner reports `Could not apply:` and no confirmation dialog opens.

When the apply succeeds, one dialog is shown:

- Heading: **Keep this arrangement?**
- **Keep** is the default.
- **Revert** is the close response, so dismissing the dialog reverts.
- The body counts down one second at a time from 15: `Reverting to the previous setup in N s.` followed by `Nothing has been written to monitors.lua yet.`

**Keep** makes the arrangement that was just applied the one a later revert returns to, and toasts `Applied. Save to keep it across restarts.` Edits you make while the dialog is open are not what Keep stores.

**Revert**, dismissing the dialog, or the countdown reaching zero applies the last kept arrangement. When that succeeds, the window reloads from `hyprctl` and toasts `Reverted`. When it fails, the banner shows `Could not revert:` and the error, the window is not reloaded, and `Reverted` is not toasted. The last kept arrangement is the one captured when that dialog opened: the desk from launch, the last **Keep**, or the last successful **Save**.

Only one of these dialogs is pending. A second **Try it** closes the first dialog and cancels its timer before the new countdown starts. A response or tick from the older dialog does nothing, including when that older timer reaches zero. The new dialog still reverts to the last kept arrangement, not to the attempt it replaced.

The lines **Try it** applies are the same lines **Save** would write, including `mirror` and keys copied from `monitors.lua` (see Save). **Try it** still does not write the file.

A failed **Save** while this dialog is open closes the dialog and cancels its countdown. The tried layout is not kept. The banner shows the save failure. If **Identify** is on, the grids are redrawn from a fresh `hyprctl` read of the desk after the rollback. If that read fails, the snapshot those grids compare against is cleared, so the **PREVIEW** chip can show again.

If **Keep** is answered for a snapshot that failed **Save** has already rolled back, and that answer is still handled as the open prompt, the banner is `The tried layout is no longer on screen — not kept`. There is no `Applied. Save to keep it across restarts.` toast, and the last kept arrangement does not change. A **Keep** that arrives after the dialog has already been retired does nothing: no toast, and the last kept arrangement stays as it was.

Closing the window cancels the open dialog and its timer. That close does not **Keep** and does not **Revert**. The identification overlay is hidden. Closing the window does not write `monitors.lua`.

## Save

**Save** applies the arrangement and writes `~/.config/hypr/monitors.lua` (tooltip: “Apply and write to ~/.config/hypr/monitors.lua”). Review the **Preview** group first. That text is the block that will be written, including `mirror` and any keys copied from the existing file.

**Save** uses the same refusal as **Try it**. After a failed load the banner is `Could not read monitors from hyprctl — reload before applying or saving`. With an empty desk it is `No monitors loaded — nothing to apply or save`. In both cases the arrangement is not applied and `monitors.lua` is left unchanged, so an empty generated block is not written over existing `hl.monitor` rules. Selecting **Save** again while a save is still running is ignored: that click does not apply the arrangement, write the file, or make another backup.

1. The arrangement is applied live. If that fails, the banner reports `Could not apply:` and the file is left untouched.
2. The existing `monitors.lua` is read. A missing file is treated as empty. The block starts with `-- >>> monitor-align: generated block, edits here are overwritten` and ends with `-- <<< monitor-align`. When the file contains both markers, the block is replaced where it stands: text before the begin marker stays before the new block, and text after the end marker stays after it. When the file has other text and lacks either marker, that text is kept and the block is appended after a blank line. Each `hl.monitor` line in the new block is the line described under **What a generated line keeps** below.
3. Config errors already reported by `hyprctl configerrors` are recorded. Those existing errors do not fail the save.
4. If the file already exists, it is copied to `monitors.lua.bak.<timestamp>` beside it. `<timestamp>` is the Unix time in nanoseconds. If that path already exists, the name gains a `.1`, `.2`, … suffix (`monitors.lua.bak.<timestamp>.1`) until it is free, so an earlier backup is never overwritten. Backups are not pruned.
5. The new file is written to a temporary file in the same directory, flushed, and renamed over `monitors.lua`. A failed write leaves the existing file in place and removes the temporary file. When a backup was made, the banner includes `original kept` and the backup name.
6. The app runs `hyprctl reload`, then applies the same explicit geometry again so a catch-all `position = "auto"` rule cannot leave the desk shuffled.
7. If that re-apply fails, or `hyprctl configerrors` reports an error that was not in the set from step 3, the save fails. The previous file contents are written back by the same rename, or the new `monitors.lua` is removed when this save created it, and `hyprctl reload` runs again. When a backup was restored, the `hl.monitor` lines from its generated block are then applied again, the same way step 6 re-asserts the new block; if that re-apply fails, the banner adds `could not re-apply its layout:` and the error. A restored file with no generated block, and a file this save created, have no such lines, so only the reload runs. The banner includes the failure and either `monitors.lua restored from monitors.lua.bak.<timestamp>` or `new monitors.lua removed`. If that restore fails, the banner says `could not roll back monitors.lua` and, when a backup exists, names that backup. The open **Keep this arrangement?** dialog, if any, is closed and its countdown is cancelled. The tried layout is not kept. If **Identify** is on, it is refreshed from a fresh `hyprctl` read; if that read fails, the applied snapshot is cleared.
8. On success, an open Try it dialog is closed without reverting. The saved arrangement becomes the one a later Try it would revert to. The toast is `Saved to monitors.lua`, plus the backup name when a backup was made.

A **Save** that fails at step 1 leaves the Keep dialog open: nothing was written, and the countdown still applies. Any later failure — the file could not be read or written, or step 7 rolled the file back — closes that dialog and cancels its countdown, as step 7 describes. **Keep** cannot adopt the layout that **Save** did not keep.

## What a generated line keeps

There is no control for mirroring another output, or for keys such as `bitdepth`, `cm`, `vrr`, `sdrbrightness`, and `sdrsaturation`. **Try it** and **Save** still write them, so replacing the generated block does not drop them.

`mirror` comes from Hyprland, not from a stale key in the file. If `hyprctl` reports `mirrorOf` as anything other than `none`, the line includes `mirror` set to that output name, string-escaped the same way a connector name is. If it reports `none`, or omits it, the line has no `mirror` key, even when an older rule in `monitors.lua` had one.

Other keys this editor does not write are copied from the last `hl.monitor` rule for that output in `monitors.lua`. The search uses the whole file. Commented-out rules are skipped. The last matching rule wins, so a later rule that omits a key drops it. Values are copied as they appear in that rule, including a nested table or a string that contains a comma. They are appended after `transform`. On a disabled line they follow `disabled = true`. A disabled line also keeps `mode`, `position`, `scale`, and `transform`, as described under Arrange.

Keys the editor writes itself are not copied from the file, so they are not duplicated: `output`, `mode`, `position`, `scale`, `transform`, `disabled`, and `mirror`.

Connector names in the generated Lua are string-escaped. Descriptions are kept on a single comment line. That handling is unchanged; see the README privacy section.
