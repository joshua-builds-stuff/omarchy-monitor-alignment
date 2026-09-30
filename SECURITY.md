# Security Policy

## Supported versions

Security fixes are provided for the latest tagged release.

| Version | Supported |
| --- | --- |
| 1.x | Yes |

## Configuration writes

A failed read of `hyprctl -j monitors all`, and a successful read that returns no monitors, do not apply an arrangement and do not rewrite `~/.config/hypr/monitors.lua`. Save does not replace the generated block when no monitors are loaded, so existing `hl.monitor` rules stay in the file. A second Save that starts while a save is still running is ignored. Each backup of an existing `monitors.lua` is copied to a new `monitors.lua.bak.<timestamp>` name, and an earlier backup is left in place.

## Reporting a vulnerability

Please use GitHub's private security advisory feature for this repository. Do not include passwords, access tokens, private configuration files, or other sensitive personal data in a public issue.

Include the affected version, a concise impact description, reproduction prerequisites, and the smallest safe proof needed to demonstrate the issue. Reports involving monitor metadata should state whether the source is a physical display, an emulated display, or compositor output.
