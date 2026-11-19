# Device Status and Connections

[Home](../README.md) · [Software management](software-management.md) · [Development and deployment](development.md)

## Verification scope

Updated: 2026-11-19. Base system information and factory hardware behavior were checked on November 12-14; the combined kernel patches were tested on November 19. Results come from the connected JingPad C1 and local installation acceptance records. IP addresses, free space, process states, and network results are snapshots from those checks.

Kernel update, 2026-11-19: the device runs the `statx-proc-ticket-v1` combined patches. `/proc/version` contains `gao@jingpad-patched-ticket-statx414`, while the release remains `4.14.133-202201191758+`. Real mount ID, proc sandbox, Ticket protocol, original module, and desktop service checks passed. Flatpak Calculator returned `4` for `2+2` and `30` for `(12+8)*3/2`. The user confirmed Calculator display and interaction, touch, and speakers on this kernel. Factory backups and verified rollback materials are retained. See the [kernel execution log](kernel-backport-2026-11-18.md).

## System and hardware

| Item | Device result |
| --- | --- |
| Model | JingPad C1 |
| OS | JingOS v1.2.0 / JingOS Preview Edition |
| Ubuntu base | 20.04, `focal`; `ID_LIKE="ubuntu debian"` |
| CPU architecture | `aarch64`; Debian package architecture is `arm64` |
| Kernel | `4.14.133-202201191758+` |
| glibc | 2.31 |
| PID 1 | systemd 245 |
| Desktop | Plasma Wayland, `kwin_wayland --hwcomposer`, using the device graphics stack through libhybris |
| Qt core libraries | 5.15.2 with JingOS/KDE version suffixes |
| Memory | Approximately 7.6 GiB usable capacity, advertised as 8 GB; approximately 4.8 GiB available during the check |
| Root partition | 40 GiB, approximately 35 GiB free after the Flatpak test |
| `/home` | F2FS, 197906001920 bytes, approximately 184.3 GiB; approximately 181 GiB free after the Flatpak test |
| Desktop user | `gao`, UID 1000 |

Refresh these details before development:

```bash
cat /etc/os-release
uname -rm
getconf GNU_LIBC_VERSION
df -h / /home
free -h
```

## Installation and functional checks

The initial Linux installation and boot acceptance tests are complete. All 35 write targets in the installation record passed independent readback checks. Both GPTs and the storage layout were checked, and the original calibration data and critical boot chain components were preserved. Subsequent kernel experiments updated only `boot`, with full independent readback and signature verification after each write. Factory backups and the physical recovery path remain available.

| Item | Evidence / status |
| --- | --- |
| Native Linux boot | systemd is PID 1; system and desktop user sessions work |
| Initialization / login | Completed by the user on the tablet |
| Touch / speakers | Confirmed by the user with both the factory kernel and the current combined patches |
| Wi-Fi / DNS / HTTPS | Verified on the tablet with both the factory kernel and the current combined patches |
| USB / wireless ADB | Both have reached the same Linux root environment |
| Flatpak apps | User-level Flathub and ARM64 Calculator 51.1 are installed; CLI calculation and GUI interaction passed with the combined kernel; file chooser, Flatpak audio/video, and app GPU acceleration remain unverified |
| Elixir / Phoenix services | Not deployed |
| Long-running services after closing the cover or turning off the screen | Unverified; access while awake does not establish this |
| `proc-sys-fs-binfmt_misc.mount` | Observed as failed during earlier checks and left untouched; this does not invalidate the desktop checks above |

Full backups and flashing logs are stored locally on the maintenance computer and are not committed to Git. This repository does not contain personal raw partitions, calibration data, or a complete flashing script. Another device requires its own backups and model/image compatibility checks.

## USB ADB

On the maintenance computer:

```bash
adb devices -l
JINGPAD_SERIAL='replace-with-current-serial'
adb -s "$JINGPAD_SERIAL" shell
```

The USB serial observed on 2026-11-19 was `Jingos123`; earlier checks reported `C12144MKCA001176`. Always use `-s` when multiple devices or both USB and wireless transports are connected. Use the current `adb devices -l` output as the authority for the serial and USB state.

Inside the shell, `id` reports UID 0. This is a Linux shell; ordinary Linux services do not require an Android APK, Magisk, or the Android SDK.

## Wireless ADB

On 2026-11-12, the Wi-Fi address was `10.100.8.232`, and TCP ADB was reachable on port 5555. The Flatpak follow-up used USB and did not revalidate this wireless address:

```bash
adb connect 10.100.8.232:5555
adb -s 10.100.8.232:5555 shell
```

DHCP assigns this address; it is not a fixed device address. If it is unreachable, query the current address over USB:

```bash
adb -s "$JINGPAD_SERIAL" shell ip -4 -brief address show wlan0
```

Wireless ADB grants root access and should be used only on a trusted LAN. `ssh` / `sshd` is masked; ADB reachability does not mean SSH is enabled. SSH was not enabled during this work.

## Root and the desktop user

Run system maintenance commands in the ADB root shell. Flatpak's `--user` refers to **the user executing the command**. Root's user installation directory is separate from `gao`'s.

To query the desktop user's Flatpak installation:

```bash
runuser -u gao -- flatpak remotes --user --show-details
runuser -u gao -- flatpak list --user
```

Run application launch, display, and file chooser tests from a graphical terminal in `gao`'s desktop session. An ADB shell does not automatically inherit the desktop Wayland and D-Bus environment; a GUI launch from that shell alone is not a reliable application compatibility test.

## Installed tools and missing components

- Installed: APT 2.0.2, dpkg 1.19.7, Flatpak 1.16.6, bubblewrap 0.12.0, OSTree 2020.8, Python 3, and GCC. Experimental Flatpak package versions, sources, and rollback are documented in the [test log](flatpak-test-2026-11-13.md).
- Desktop integration packages: `plasma-discover-backend-flatpak`, `xdg-desktop-portal` 1.8.0, and `xdg-desktop-portal-kde` 5.20.5.
- The portal was inactive when queried. These services can be activated on demand through D-Bus; inactivity alone does not establish a fault.
- Not installed: Git, G++, CMake, flatpak-builder, Erlang/Elixir/Mix, or Podman/Docker.
- A `qmake` command exists, but `qmake -query QT_VERSION` fails; the Qt SDK is not confirmed to be fully configured.
- The combined patches passed the unprivileged USER+PID/proc sandbox test and still reject unauthorized proc mounts. Calculator CLI tests also passed. Other applications need their own portal, audio, and display checks.

## System maintenance boundaries

JingOS's Qt, KDE, libhybris, hwcomposer, firmware, and original boot chain work together. Simulate dependency changes before installing development tools; see the [software management guide](software-management.md).

Installing apps does not require entering a flashing workflow. In particular, do not run `adb reboot autodloader`. Similar A1/C1 image names or platform strings do not replace device compatibility checks and complete backups.
