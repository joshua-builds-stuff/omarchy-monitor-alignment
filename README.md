# Omarchy Monitor Alignment

`monitor-align` is a visual display arrangement tool for Hyprland and Omarchy. It lets you drag displays into position, rotate them, select modes and scaling, show an alignment grid on the physical screens, try changes with a timed rollback, and save the result to `~/.config/hypr/monitors.lua`.

Current version: **1.0.0**

## Requirements

- Omarchy or another Hyprland environment using the Lua configuration parser
- Python 3.11 or newer
- GTK 4, Libadwaita, PyGObject, pycairo, and GTK4 Layer Shell
- `hyprctl`

On Arch Linux or Omarchy, install the runtime packages with:

```bash
sudo pacman -S --needed python python-gobject python-cairo gtk4 libadwaita gtk4-layer-shell hyprland
```

## Install

```bash
git clone https://github.com/joshua-builds-stuff/omarchy-monitor-alignment.git
cd omarchy-monitor-alignment
install -Dm755 monitor-align "$HOME/.local/bin/monitor-align"
install -Dm644 monitor-align.desktop \
  "$HOME/.local/share/applications/org.omarchy.MonitorAlign.desktop"
```

Make sure `~/.local/bin` is in the graphical session's `PATH`. Log out and back in if a newly installed desktop launcher does not appear. If `update-desktop-database` is installed, you can refresh the launcher cache immediately:

```bash
update-desktop-database "$HOME/.local/share/applications"
```

## Use

Launch **Monitor Align** from the application menu or run:

```bash
monitor-align
```

The steps below are the short path. [docs/how-to.md](docs/how-to.md) walks through scale snapping, dragging, a canvas click that keeps Position X/Y, disabled displays, Identify, a failed or empty `hyprctl` load, the single Try it confirmation, Save (including lines after the generated block), and backup names.

In the window:

1. Drag displays or edit their position, orientation, resolution, refresh rate, and scale. During a drag the canvas keeps the zoom and offset from when the drag began, and pointer movement uses that zoom, so the display stays under the pointer; the canvas refits when the drag ends. A click on a tile selects that display and leaves **Position X** and **Position Y** where they are, including an origin other than `0,0`. A drag that moves the tile still shifts the desktop so the enabled displays' top-left sits at `0,0`. When that shift runs, disabled displays move by the same amount and keep their place relative to that group. Scales read from `hyprctl` are snapped onto Hyprland's 1/120 lattice before they are stored. When that step is valid for the mode, a printed `1.33` is kept as `4/3` (`160/120`) and a printed `1.67` as `5/3` (`200/120`). **Arrange**, edge snapping, and Identify compute logical size from the snapped scale, and the generated Lua writes that same scale.
2. Use **Identify** to draw numbered coordinate grids on the physical displays. While the toggle is on, the grids follow the arrangement being edited, including **Position X** and **Position Y**. When that arrangement's generated Lua differs from the arrangement last applied, each grid draws a **PREVIEW** chip: `PREVIEW — press “Try it” to move the screens`.
3. Select **Try it** to apply the arrangement live. **Try it** is refused when the last `hyprctl -j monitors all` read failed, or when the window has no monitors: the banner is `Could not read monitors from hyprctl — reload before applying or saving` after a failed read, and `No monitors loaded — nothing to apply or save` when the desk is empty. In both cases nothing is applied. Otherwise one **Keep this arrangement?** dialog counts down from 15 seconds. **Keep** retains the arrangement that was just applied. **Revert**, closing the dialog, or the end of the countdown returns to the last kept arrangement. If that apply fails, the banner shows `Could not revert:` and the window does not reload or toast `Reverted`. A newer **Try it** replaces that dialog and cancels its timer, so only the newest countdown can revert. Try it does not write `monitors.lua`.
4. Select **Save** to apply the arrangement and write the generated block to `~/.config/hypr/monitors.lua`. **Save** uses the same refusal as **Try it** when the last read failed or no monitors are loaded, and it does not write the file in those cases. A **Save** that starts while another save is still running is ignored. Otherwise the new text is written to a temporary file and renamed into place. Config errors Hyprland already reported are ignored. After `hyprctl reload`, if the following re-apply fails, or Hyprland reports a new config error, the previous file is restored and, when it has a generated block, its `hl.monitor` lines are applied again. If that restored-layout apply fails, the banner adds `could not re-apply its layout:`. A file this save created is removed instead.

When `monitors.lua` already contains both block markers, Save replaces that block where it stands. Text before `-- >>> monitor-align: generated block, edits here are overwritten` stays before the new block, and text after `-- <<< monitor-align` stays after it. When the file has other text and lacks either marker, that text is kept and the block is appended after a blank line. If `monitors.lua` already exists, the app first copies it to `monitors.lua.bak.<timestamp>` beside it. `<timestamp>` is the Unix time in nanoseconds; if that name is already taken, a `.1`, `.2`, … suffix is appended. An earlier backup is never overwritten, and backups are not pruned.

To show the identification overlay without opening the editor:

```bash
monitor-align --identify 15
```

To print the installed version:

```bash
monitor-align --version
```

## Test

Run the standard-library regression suite from the repository root:

```bash
python -m unittest discover -s tests -v
```

The tests cover Lua serialization, generated-comment safety, fractional scale snapping, the single Try it confirmation (including a failed revert), save rollback (including re-applying a restored layout), Identify updates from Position X/Y, shifting disabled displays with the enabled group, a drag that keeps its canvas projection, a canvas click that keeps Position X/Y, refusing Try it and Save after a failed or empty `hyprctl` load, lines kept after the generated block, unique `monitors.lua` backup names (including a Save ignored while another save is running), and accidental publication of maintainer home paths.

## Privacy and security

The application runs as the current desktop user and does not use `sudo`, contact network services, collect analytics, or send telemetry. It reads monitor information from local `hyprctl` output and theme colors from `~/.local/state/omarchy/current/theme/colors.toml`. The Identify overlay intentionally shows monitor names, descriptions, modes, and geometry on the connected screens.

Monitor metadata is treated as untrusted when it is written into generated Lua: connector names are string-escaped and descriptions are constrained to inert, single-line comments. Subprocesses use argument arrays without a command shell.

`Try it` has a timed live rollback and does not write `monitors.lua`. If that rollback cannot be applied, the banner shows `Could not revert:` and the window does not claim it reverted. After `hyprctl -j monitors all` fails, or when that read returns no monitors, **Try it** and **Save** are refused. Neither applies an arrangement nor rewrites `monitors.lua`, so a failed or empty read cannot replace the generated block with an empty one and drop existing `hl.monitor` rules. If the window already had displays, a failed reload leaves them in place and they stay refused until a later reload succeeds. A **Save** that starts while another save is still running is ignored. A successful `Save` is persistent. If saving cannot re-apply the arrangement, or Hyprland reports a new config error, the previous `monitors.lua` is restored and, when that file has a generated block, its `hl.monitor` lines are applied again; a file created by that save is removed. Review the preview before using Save. Each save of an existing file copies it to a new backup name. Backups are not automatically pruned.

For vulnerability reports, use GitHub's private security advisory feature rather than a public issue.

## Uninstall

```bash
rm "$HOME/.local/bin/monitor-align"
rm "$HOME/.local/share/applications/org.omarchy.MonitorAlign.desktop"
```

Uninstalling does not remove `~/.config/hypr/monitors.lua` or its backups.

## License

MIT. See [LICENSE](LICENSE).
