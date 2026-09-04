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

In the window:

1. Drag displays or edit their position, orientation, resolution, refresh rate, and scale.
2. Use **Identify** to draw numbered coordinate grids on the physical displays.
3. Select **Try it** to apply the arrangement temporarily. Confirm within 15 seconds or it reverts to the previous live arrangement.
4. Select **Save** to apply the arrangement and write the generated block to `~/.config/hypr/monitors.lua`.

The save operation preserves content outside the marked `monitor-align` block. If `monitors.lua` already exists, the app first makes a timestamped backup beside it, named `monitors.lua.bak.<timestamp>`.

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

The tests cover Lua serialization, generated-comment safety, and accidental publication of maintainer home paths.

## Privacy and security

The application runs as the current desktop user and does not use `sudo`, contact network services, collect analytics, or send telemetry. It reads monitor information from local `hyprctl` output and theme colors from `~/.local/state/omarchy/current/theme/colors.toml`. The Identify overlay intentionally shows monitor names, descriptions, modes, and geometry on the connected screens.

Monitor metadata is treated as untrusted when it is written into generated Lua: connector names are string-escaped and descriptions are constrained to inert, single-line comments. Subprocesses use argument arrays without a command shell.

`Try it` has a timed live rollback. `Save` is intentionally persistent; review the preview before using it. Backups are not automatically pruned.

For vulnerability reports, use GitHub's private security advisory feature rather than a public issue.

## Uninstall

```bash
rm "$HOME/.local/bin/monitor-align"
rm "$HOME/.local/share/applications/org.omarchy.MonitorAlign.desktop"
```

Uninstalling does not remove `~/.config/hypr/monitors.lua` or its backups.

## License

MIT. See [LICENSE](LICENSE).
