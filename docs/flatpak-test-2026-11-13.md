# Historical Flatpak Device Test: Installation Passed, Launch Blocked by the Kernel

[Home](../README.md) · [Software management](software-management.md) · [Device status](device-status.md)

Test dates: 2026-11-13 through 2026-11-14. Device: JingPad C1, JingOS v1.2.0 / Ubuntu 20.04 focal, ARM64, vendor kernel `4.14.133-202201191758+`, glibc 2.31.

This document preserves historical factory-kernel results. The combined kernel patches passed real mount ID and sandbox tests on 2026-11-19. Calculator returned `4` for `2+2` and `30` for `(12+8)*3/2`, and the user confirmed Calculator GUI, touch, and sound. See the [kernel execution log](kernel-backport-2026-11-18.md) for the current state.

## Results and scope

User-level Flathub configuration, signature verification, metadata retrieval, and application installation succeeded. At the time of this test, GNOME Calculator 51.1 could not launch: Flatpak 1.16.6's secure path checks require `STATX_MNT_ID`, which this factory 4.14 kernel does not return. **Successful installation does not establish that a desktop app works.**

| Item | Result |
| --- | --- |
| `gao` user-level Flathub | Configured with `gpg-verify=true` and `gpg-verify-summary=true` |
| ARM64 app and runtime metadata | Retrieved successfully |
| Calculator installation | Exit 0 after approximately 1551 seconds; not terminated by a timeout |
| `flatpak info --user org.gnome.Calculator` | Exit 0; version 51.1, `aarch64/stable` |
| `flatpak run --user org.gnome.Calculator --help` | Exit 1; missing `statx` field |
| `flatpak run --user org.gnome.Calculator --solve=2+2` | Exit 1 with the same error; no calculation result |
| Basic bubblewrap user/PID namespace sandbox | Exit 0 |
| `dpkg --audit` | Exit 0, no output |
| GUI, touch, input methods, portals, audio/video, hardware acceleration | Unverified; the application had not started |

## First blocker: old OSTree summary size limit

The system originally had Flatpak `1.6.5-0ubuntu0.1` and OSTree `2020.3-1`. Initial 32/50-second probes were insufficient to establish the cause. A longer diagnostic run produced a clear error after approximately 165 seconds:

```text
URI https://dl.flathub.org/repo/summary exceeded maximum size of 10485760 bytes
```

The summary was approximately 12.8 MB, exceeding old OSTree's hardcoded 10 MiB limit. Downloading `.flatpakrepo` first or changing the old `max-metadata-size` setting does not change this summary retrieval path. Upgrading the packages below allowed repository access and installation.

## Actual package changes and verification

| Package | Before | After | Source |
| --- | --- | --- | --- |
| `flatpak` | `1.6.5-0ubuntu0.1` | `1.16.6-1~flatpak1~20.04.1` | Flatpak stable PPA, focal/arm64 |
| `bubblewrap` | `0.4.0-1ubuntu4` | `0.12.0-1~flatpak1~20.04.1` | Same PPA |
| `libostree-1-1` | `2020.3-1` | `2020.8-flatpak2~20.04` | Same PPA, including the summary size limit fix |
| `libcurl4` | Not installed | `7.68.0-1ubuntu2.25` | Official Ubuntu focal-updates/arm64 |

PPA and Ubuntu InRelease signatures, Packages index SHA256 values, each `.deb` SHA256, and package architectures were verified. The PPA signing fingerprint was:

```text
5C6D153A17C02C337EF6C663B8B9D41229DFA5F5
```

The dependency simulation involved only these four packages, with no removals. An APT local installation attempt failed with the internal error `Pathname to install is not absolute`. After confirming that package versions had not changed, the four verified local packages were installed with `dpkg --force-confold --install`. Comparing complete package inventories before and after also showed only these four changes.

**The PPA officially states that Ubuntu 20.04 and older branches no longer receive updates and have known security vulnerabilities.** These versions document the compatibility experiment; they are not a claim about the latest upstream release or a recommended long-term repository. The PPA was not added persistently on the device.

During this test, JingOS was not upgraded as a whole, and Qt, KDE, glibc, libhybris, drivers, the kernel, firmware, and the boot chain were unchanged. The original `/etc/apt/sources.list`, `sources.list.d/jingos.list`, and `preferences.d/jingos.pref` matched their backups; unavailable JingOS repositories had not been replaced.

## Installed artifacts

The application was installed in desktop user `gao`'s `~/.local/share/flatpak`, not root's user installation or the system installation.

| Item | Value |
| --- | --- |
| App | `org.gnome.Calculator/aarch64/stable`, 51.1 |
| App commit | `40a4a730925db4404a8682525594caaa2989d4e00b281f3ca1b5b0d5bb17d3bc` |
| Runtime | `org.gnome.Platform/aarch64/51` |
| Runtime commit | `90c984972c455ab43d4575cae99f8b29ac50da6c1489d69c4a95fdadd9622f47` |
| Graphics / codec extensions | `org.freedesktop.Platform.GL.default` 26.08 / 26.08-extra, and `codecs-extra` 26.08-extra |
| Repository | `https://dl.flathub.org/repo/` |

The GNOME runtime download was approximately 416.7 MB and occupied approximately 1.2 GB after installation, plus extensions and locales. Approximately 181 GiB remained free in `/home` and 35 GiB in the root partition. Test processes used an existing LAN HTTP proxy for faster downloads; persistent system proxy settings were not changed. Signature verification remained enabled throughout.

## Second blocker: the old kernel does not return mount IDs

Both launch tests reported:

```text
error: statx didn't return all required fields: No data available
```

The error string is in `/usr/bin/flatpak`, not `/usr/bin/bwrap`. `strace` showed Flatpak requesting `STATX_TYPE | STATX_INO | STATX_MNT_ID | STATX_MNT_ID_UNIQUE` before executing the app. The old kernel's returned mask lacked both mount ID fields. Independent syscall probes on `/` and the Flatpak user directory confirmed the missing bits, ruling out corruption of a single app file.

The libglnx bundled with Flatpak 1.16.6 requires a mount ID in `glnx_chase_statx()` and returns this error when it is missing. The upstream main branch's Host Requirements also specify Linux 5.8 for `STATX_MNT_ID`; upstream reports describe the same error on older kernels.

PPA version history and Flatpak 1.16.4 source were checked; 1.16.4 contains the same check. Going further back would involve versions missing later sandbox security fixes. Such older versions were not installed, checks were not removed, and app permissions were not expanded. No host tool version supporting 4.14 while retaining the necessary security fixes had been found and validated.

Launching with the real desktop user's Wayland and D-Bus environment extracted from `kwin_wayland` produced the same error. It therefore could not be attributed to missing ADB session variables, screen locking, or renderer settings. Unlocking, switching Flathub remotes, reinstalling the app, and software rendering cannot supply a kernel field.

The installation and backups were retained for retesting once a verifiable compatible tool version or device kernel became available. No vendor kernel replacement or further flashing occurred during this historical test.

## Repeat checks on the factory environment

Run from `gao`'s graphical terminal on the tablet:

```bash
flatpak --version
flatpak remotes --user --show-details
flatpak list --user
flatpak info --user org.gnome.Calculator
flatpak run --user org.gnome.Calculator --help
```

The final command is expected to fail on the factory environment tested here. In an ADB root shell, prefix query commands with `runuser -u gao --`; GUI launches need the user's real desktop session. The session bus has used an abstract Unix socket, so do not hardcode `/run/user/1000/bus`.

After compatibility repairs, acceptance should check `--help`, `--solve=2+2` returning `4`, and `--solve='(12+8)*3/2'` returning `30`, followed by the GUI and required desktop features. These tests were incomplete during the initial test. The combined patches passed all three CLI checks and manual Calculator GUI confirmation on 2026-11-19; other desktop integrations require separate tests.

## Backups, evidence, and rollback

The maintenance directory on the tablet is private to root:

```text
/home/gao/jingos-maintenance/flatpak-20261113T011746-1wqcsf1o
```

It contains complete device-repacked `.deb` backups of the three original packages, original APT and user Flatpak configuration, package inventories, signature/hash records, dependency simulations, installation logs, and app test results. The original package backups had no missing files; their final SHA256 values matched `backup-manifest.json`. Personal raw logs were not added to this repository.

Key evidence files:

- `upgrade-pass.json`: the four package changes, versions, dpkg audit, and basic sandbox results.
- `calculator-install-result.json`, `installed-info-result.json`: installation return code, duration, and app commit.
- `calculator-help-result.json`, `solve-simple-result.json`: original launch errors.
- `flatpak-statx.log`: syscall trace of the launch attempt.
- `final-checks-20261114.json`: mount ID probes, signature policy, configuration/backup checks, and system state.

Use the following commands in a root shell only if restoring the original host packages is necessary. First verify backup SHA256 values against `backup-manifest.json` and record the current package versions:

```bash
backup_dir=/home/gao/jingos-maintenance/flatpak-20261113T011746-1wqcsf1o
dpkg-query -W flatpak bubblewrap libostree-1-1 libcurl4
dpkg --force-confold --install \
  "$backup_dir/original-debs/bubblewrap-original.deb" \
  "$backup_dir/original-debs/flatpak-original.deb" \
  "$backup_dir/original-debs/libostree-1-1-original.deb"
dpkg --audit
```

Rollback packages are prepared, but rollback has not been rehearsed. This restores only three host packages, retaining the added `libcurl4` and user-installed apps/runtimes. It does not guarantee the old client can read the new installation, and it restores the old summary limit. It is not an app launch fix. Do not blindly run `autoremove` or overwrite the entire user directory as cleanup.

At the end of this historical test, the only failed system unit was the previously observed `proc-sys-fs-binfmt_misc.mount`. That independent issue was left untouched. Erlang/Elixir services remained uninstalled and undeployed.

## Upstream references

- [Old OSTree summary size issue](https://github.com/flatpak/flatpak/issues/6245)
- [OSTree summary limit increase](https://github.com/ostreedev/ostree/commit/4bac96a8c817beda37448f9b8c662162bb619981)
- [Flatpak stable PPA and maintenance statement](https://launchpad.net/~flatpak/+archive/ubuntu/stable)
- [libglnx mount ID check in 1.16.6](https://github.com/flatpak/flatpak/blob/1.16.6/subprojects/libglnx/glnx-chase.c#L105-L126)
- [Upstream kernel requirements discussion and matching error](https://github.com/flatpak/flatpak/issues/6774)
- [Current upstream Host Requirements](https://github.com/flatpak/flatpak#host-requirements)
- [Security fixes and release notes from 1.16.4 to 1.16.6](https://github.com/flatpak/flatpak/blob/1.16.6/NEWS)
