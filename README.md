# JingPad / JingOS Development Guide

This repository documents software management and development on a JingPad C1 running JingOS Linux. It also preserves the original [firmware download index](docs/firmware-archive.md). The guide is based on tests on this particular C1; it is not a general flashing guide for every A1 or C1.

## Current status

Updated: **2026-11-19**. Initial hardware and Flatpak tests took place on November 12-14, kernel source research on November 16, and the 4.14 backport and device acceptance tests are complete.

| Item | Current state |
| --- | --- |
| Device / OS | JingPad C1 running JingOS v1.2.0, based on Ubuntu 20.04 focal |
| Architecture / kernel | ARM64 (`aarch64`), Linux `4.14.133-202201191758+` |
| Base environment | glibc 2.31, systemd 245, Qt 5.15.2, libhybris |
| Storage / memory | 40 GiB root partition; approximately 184 GiB in `/home`; 8 GB RAM |
| Verified functions | Desktop login, touch, speakers, Wi-Fi, DNS, HTTPS, and an ADB root shell work with the combined kernel patches |
| APT | Still the system package manager; the original JingOS repositories are unavailable |
| Flatpak | Calculator 51.1 CLI and GUI tests passed; `2+2` returned `4`, and the user confirmed that Calculator, touch, and sound work normally |
| Development services | Erlang/Elixir is not installed, and no service has been deployed |

**The combined 4.14 patches passed boot, driver compatibility, and Flatpak Calculator acceptance tests on this device. Follow the guide to evaluate aarch64 Flatpak desktop apps, use ARM64 APT packages for the same Ubuntu release for system tools, and use an ARM64 Release with systemd for Elixir services.**

The old OSTree 10 MiB summary limit was resolved, allowing ARM64 GNOME Calculator 51.1 to be installed. The factory 4.14 kernel lacked the mount ID required by Flatpak 1.16.6 and initially produced `statx didn't return all required fields`. A real kernel interface backport has now resolved this. See the [historical Flatpak test log](docs/flatpak-test-2026-11-13.md) and the [current backport execution log](docs/kernel-backport-2026-11-18.md). Changing repositories or reinstalling an app cannot supply a missing kernel interface.

Kernel source remains available. A UD710 Linux 5.15.178 port with a matching board device tree was also found, but it has not been shown to boot on this C1. This project backported `STATX_MNT_ID` to the existing 4.14 kernel and verified display, touch, and speakers. Linux 5.8 introduced the upstream interface; upgrading the entire kernel is not required to obtain it. See [kernel source and upgrade feasibility](docs/kernel-upgrade-research.md).

The combined kernel booted successfully. Checks passed for all 11,524 exported symbol entries, 4,352 configuration options, and 710 driver-required symbols, along with 24 mount ID syscall checks, positive and negative proc sandbox controls, and Ticket protocol tests. Restoring proc and Ticket behavior missing from the published source made KWin/PowerVR compositing, audio, and power services responsive. Calculator CLI, GUI, and manual touch/sound tests passed. Other apps, portals, app GPU acceleration, and suspend/resume need separate validation. Patches and probes are linked from the [execution log](docs/kernel-backport-2026-11-18.md).

## Reading order

1. [Device status and connections](docs/device-status.md): hardware, verified behavior, ADB, accounts, and current limitations.
2. [Software installation and repositories](docs/software-management.md): Flatpak compatibility, user installations, architecture checks, and APT repository configuration and rollback.
3. [Application development and Elixir deployment](docs/development.md): Web, Qt/QML, Flatpak packaging, and ARM64 Releases.
4. [Historical firmware archive](docs/firmware-archive.md): download links for firmware and tools preserved by the original repository.
5. [Historical Flatpak test log](docs/flatpak-test-2026-11-13.md): package changes, signature checks, installation results, kernel blockers, and rollback materials.
6. [Kernel source and upgrade feasibility](docs/kernel-upgrade-research.md): official 4.14 source, the UD710 5.15 candidate, driver gaps, and validation steps.
7. [4.14 mount ID backport execution log](docs/kernel-backport-2026-11-18.md): builds, boot signing, backups, failed attempts, and final device acceptance.
8. [Rebuilding application and update services](docs/self-hosted-services.md): observed vendor APIs, signed Flatpak/APT repositories, client migration, staged validation, and rollback requirements.

## Connect to the device

Run these commands on the Linux computer connected to the tablet. `adb` is part of Android Platform Tools.

```bash
adb devices -l
JINGPAD_SERIAL='replace-with-current-serial'
adb -s "$JINGPAD_SERIAL" shell
```

The ADB shell on this device is already Linux `root`; neither `adb root` nor `su` is needed. Use the serial reported by the current `adb devices -l` output. The desktop user is `gao`; run user-level Flatpak operations as that account, as described in the [software management guide](docs/software-management.md).

## Scope of this record

The repository contains development documentation, kernel patches, and interface probes. The Flatpak experiment upgraded three packages, added `libcurl4`, and persistently configured Flathub and installed Calculator and its runtime for `gao`. Later kernel experiments updated only `boot`, with a full readback and signature verification after each write. The original image and recovery path were verified. Original packages, configuration, and logs were backed up; persistent APT sources were not changed, and no distribution upgrade was performed.

The APT repository and systemd deployment examples remain instructions for future work. Preserve the existing JingOS display, touch, audio, firmware, kernel, and boot chain components. The focal branch of the Flatpak PPA used in the experiment is no longer maintained and has known security vulnerabilities; it is documented as an experiment, not a long-term maintenance solution.
