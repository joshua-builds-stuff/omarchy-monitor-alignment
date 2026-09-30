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

The steps below are the short path. [docs/how-to.md](docs/how-to.md) walks through scale snapping, dragging, disabled displays, Identify, the single Try it confirmation, and Save.

In the window:

1. Drag displays or edit their position, orientation, resolution, refresh rate, and scale. During a drag the canvas keeps the zoom and offset from when the drag began, and pointer movement uses that zoom, so the display stays under the pointer; the canvas refits when the drag ends. When the desktop shifts so the enabled displays' top-left sits at `0,0`, disabled displays move by the same amount and keep their place relative to that group. Scales read from `hyprctl` are snapped onto Hyprland's 1/120 lattice before they are stored. When that step is valid for the mode, a printed `1.33` is kept as `4/3` (`160/120`) and a printed `1.67` as `5/3` (`200/120`). **Arrange**, edge snapping, and Identify compute logical size from the snapped scale, and the generated Lua writes that same scale.
2. Use **Identify** to draw numbered coordinate grids on the physical displays. While the toggle is on, the grids follow the arrangement being edited, including **Position X** and **Position Y**. When that arrangement's generated Lua differs from the arrangement last applied, each grid draws a **PREVIEW** chip: `PREVIEW — press “Try it” to move the screens`.
3. Select **Try it** to apply the arrangement live. One **Keep this arrangement?** dialog counts down from 15 seconds. **Keep** retains the arrangement that was just applied. **Revert**, closing the dialog, or the end of the countdown returns to the last kept arrangement. If that apply fails, the banner shows `Could not revert:` and the window does not reload or toast `Reverted`. A newer **Try it** replaces that dialog and cancels its timer, so only the newest countdown can revert. Try it does not write `monitors.lua`.
4. Select **Save** to apply the arrangement and write the generated block to `~/.config/hypr/monitors.lua`. The new text is written to a temporary file and renamed into place. Config errors Hyprland already reported are ignored. After `hyprctl reload`, if the following re-apply fails, or Hyprland reports a new config error, the previous file is restored and, when it has a generated block, its `hl.monitor` lines are applied again. If that restored-layout apply fails, the banner adds `could not re-apply its layout:`. A file this save created is removed instead.

The save operation preserves content outside the marked `monitor-align` block. If `monitors.lua` already exists, the app first makes a timestamped backup beside it, named `monitors.lua.bak.<timestamp>`. Existing backups are never overwritten.

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

The tests cover Lua serialization, generated-comment safety, fractional scale snapping, the single Try it confirmation (including a failed revert), save rollback (including re-applying a restored layout), Identify updates from Position X/Y, shifting disabled displays with the enabled group, a drag that keeps its canvas projection, and accidental publication of maintainer home paths.

## Privacy and security

The application runs as the current desktop user and does not use `sudo`, contact network services, collect analytics, or send telemetry. It reads monitor information from local `hyprctl` output and theme colors from `~/.local/state/omarchy/current/theme/colors.toml`. The Identify overlay intentionally shows monitor names, descriptions, modes, and geometry on the connected screens.

Monitor metadata is treated as untrusted when it is written into generated Lua: connector names are string-escaped and descriptions are constrained to inert, single-line comments. Subprocesses use argument arrays without a command shell.

`Try it` has a timed live rollback and does not write `monitors.lua`. If that rollback cannot be applied, the banner shows `Could not revert:` and the window does not claim it reverted. A successful `Save` is persistent. If saving cannot re-apply the arrangement, or Hyprland reports a new config error, the previous `monitors.lua` is restored and, when that file has a generated block, its `hl.monitor` lines are applied again; a file created by that save is removed. Review the preview before using Save. Backups are not automatically pruned.

For vulnerability reports, use GitHub's private security advisory feature rather than a public issue.

## Uninstall

```bash
rm "$HOME/.local/bin/monitor-align"
rm "$HOME/.local/share/applications/org.omarchy.MonitorAlign.desktop"
```

Uninstalling does not remove `~/.config/hypr/monitors.lua` or its backups.

## License

MIT. See [LICENSE](LICENSE).
