# Code signing policy

**English** · [Français](../fr/code-signing.md)

Free code signing provided by [SignPath.io](https://about.signpath.io/),
certificate by [SignPath Foundation](https://signpath.org/).

> The application to SignPath Foundation is in progress: until it is accepted,
> the Windows packages are not signed (see [Desktop app](desktop-app.md#windows-and-macos-packages)).

## What is signed

Only the Windows packages of the desktop app, published in the
[GitHub releases](https://github.com/Mektoub/alesis-multipad-kit-manager/releases):

- the `alesis-kit-manager-X.Y.Z-win-x64-setup.exe` installer;
- the executables built from this repository that it contains
  (`alesis-kit-manager.exe`, `alesis-kit-manager-server.exe`).

They are built by GitHub Actions on GitHub-hosted runners, from the source of
this repository at the release tag (`.github/workflows/release.yml` and
`build.yml`), then submitted to SignPath. Third-party components (Electron,
Python and their libraries) are included as published by their authors and are
not signed by this project. The Linux and macOS packages are not signed by
SignPath.

## Team roles

| Role | Members |
|---|---|
| Committers and reviewers | [Mektoub](https://github.com/Mektoub) |
| Approvers | [Mektoub](https://github.com/Mektoub) |

- Committers may change the source of the repository directly.
- Every change from someone else (pull request) is reviewed by a committer before it is merged.
- Every signing request is approved by hand by an approver, for each release.
- All members use multi-factor authentication on GitHub and SignPath.

## Privacy policy

This program will not transfer any information to other networked systems
unless specifically requested by the user or the person installing or
operating it.

The editor runs a local server, reachable only from the computer itself
(`127.0.0.1`); the backups, kits and samples stay on the computer. The app
does not check for updates and sends no usage statistics.

## Uninstallation

The Windows installer adds an uninstaller: *Settings › Apps › Installed apps*,
*Alesis Kit Manager*, *Uninstall*. The `.zip` archive is removed by deleting its
folder. The preferences stay in `%APPDATA%\AlesisKitManager\`, to be deleted
by hand (see [Preferences](web-editor.md#preferences)).
