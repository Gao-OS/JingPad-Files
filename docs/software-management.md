# Software Installation and Repositories

[Home](../README.md) · [Device status](device-status.md) · [Development and deployment](development.md)

## Choose an installation method

| Need | Recommended approach | Notes |
| --- | --- | --- |
| Desktop apps such as browsers and editors | Check compatibility, then evaluate aarch64 Flatpak apps first | Calculator CLI and GUI passed with the combined kernel patches; test each app separately and check dependencies for same-release APT packages too |
| System tools such as Git, compilers, and CMake | Restore Ubuntu focal ARM64 APT repositories, then install selected tools | Flatpak does not install host compilers or upgrade system libraries |
| Elixir / Phoenix backend services | ARM64 Release including the Erlang runtime, managed by systemd | See [development and deployment](development.md); a desktop app sandbox is not required for these services |
| JingOS desktop, drivers, and firmware | Preserve the existing verified versions | Ordinary Ubuntu repositories cannot reconstruct the vendor-customized software stack |

Flatpak does not fully replace APT and does not upgrade the host kernel, libhybris, or the Flatpak client itself. The factory kernel cannot run the app tested here directly. The combined kernel patches passed Calculator CLI and GUI acceptance, and the user confirmed touch and sound.

Update, 2026-11-19: the combined kernel patches passed 24 real mount ID calls, a USER+PID/proc sandbox test, rejection of unauthorized mounts, and factory Ticket protocol tests. Desktop graphics and audio services respond normally. Calculator's `--solve=2+2` returned `4`, and `--solve='(12+8)*3/2'` returned `30`; the user confirmed GUI interaction, touch, and speakers. See the [kernel execution log](kernel-backport-2026-11-18.md). The installation commands below do not replace device acceptance tests for other apps.

Repeat these checks in `gao`'s graphical terminal on the tablet running the combined kernel patches:

```bash
cat /proc/version
flatpak run --user org.gnome.Calculator --solve=2+2
flatpak run --user org.gnome.Calculator --solve='(12+8)*3/2'
flatpak run --user org.gnome.Calculator
```

The first command should include `gao@jingpad-patched-ticket-statx414`. The CLI calculations returned `4` and `30`, both with exit code 0. The final command opens the GUI for visual and interaction tests, which the user confirmed passed. `uname -r` retains the original release string and cannot distinguish the factory and patched kernels by itself.

## Device test results from 2026-11-12 through 2026-11-14

Network checks ran on the tablet itself; maintenance computer connectivity was not used as a substitute.

| Check | Result |
| --- | --- |
| `http://ubuntu-ports.jingos.com/ubuntu-ports/dists/focal/InRelease` | HTTP 404 |
| `archive-mirrors.jingos.com` | Resolved to `offline.specialcdnstatus.com` / `169.254.254.254`; repository requests timed out |
| Official `ports.ubuntu.com` focal / focal-updates / focal-security InRelease | HTTPS 200; complete files verified with the tablet's Ubuntu archive keyring using `gpgv`, all exit 0 |
| Old OSTree reading the Flathub summary | Failed clearly after approximately 165 seconds: `exceeded maximum size of 10485760 bytes`; summary approximately 12.8 MB |
| Tools after the experiment | Flatpak 1.16.6, bubblewrap 0.12.0, OSTree 2020.8; architecture `aarch64` |
| Remotes | Flathub configured for `gao`, with repository and summary GPG verification enabled; no system-level remote |
| Metadata / installation | ARM64 app and runtime metadata readable; Calculator 51.1 and GNOME 51 runtime installation exited 0 |
| Basic bubblewrap sandbox / dpkg audit | Both exit 0 |
| App launch | `--help` and `--solve=2+2` both exited 1: `statx didn't return all required fields: No data available` |
| GUI, touch, file chooser, audio/video, hardware acceleration | Unverified in this initial test; launch failed before the app executed |

Initial 32/50-second probes only observed timeouts. Longer diagnosis established the old OSTree 10 MiB limit. Signed, hash-verified focal/arm64 package upgrades fixed repository access and installation, but not application launch.

The launch error came from Flatpak's secure path checks: the factory 4.14 kernel's `statx` does not return `STATX_MNT_ID`, which Flatpak 1.16.6 requires. See the [Flatpak test log](flatpak-test-2026-11-13.md) for package versions, sources, backups, and evidence. The PPA's focal branch is unmaintained and has known security vulnerabilities; this upgrade was an experiment, not a supported long-term solution.

## Configure a user Flatpak installation

Run these commands in **`gao`'s graphical terminal on the tablet**, without sudo. A user installation uses the larger `/home` partition and stays separate from system software.

Check the current state first:

```bash
whoami
flatpak --version
flatpak --default-arch
flatpak remotes --user --show-details
flatpak list --user
```

Flathub is already configured for `gao` on this device. Inspect existing configuration first. For an environment without that remote, add it using the official configuration containing the GPG public key:

```bash
flatpak remote-add --user --if-not-exists flathub \
  https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak remotes --user --show-details
```

Adding a remote also accesses repository metadata. If it stalls, diagnose it as described below. An interrupted operation may have configured part of the remote; check `remotes` before retrying. Do not repeatedly add it or disable signature checks.

If only an ADB root shell is available, use `runuser` to manage the desktop user's installation:

```bash
runuser -u gao -- flatpak remote-add --user --if-not-exists flathub \
  https://dl.flathub.org/repo/flathub.flatpakrepo
runuser -u gao -- flatpak remotes --user --show-details
```

This avoids installing into root's user directory. Return to the desktop terminal to launch GUI apps.

## Check architecture and minimum versions before installation

`org.gnome.Calculator` is installed, and CLI calculations run with the combined kernel patches. The factory kernel still has the mount ID limitation described above; restoring it does not preserve the patched kernel's successful result. For other apps, first list ARM64 applications and inspect the target:

```bash
flatpak remote-ls --user --app --arch=aarch64 \
  --columns=application,branch,arch flathub

app_id=org.gnome.Calculator
flatpak remote-info --user --arch=aarch64 --show-metadata flathub "$app_id"
flatpak remote-info --user --arch=aarch64 --show-runtime flathub "$app_id"
```

Check `required-flatpak` in the app metadata, then inspect its runtime too:

```bash
runtime_ref="$(flatpak remote-info --user --arch=aarch64 \
  --show-runtime flathub "$app_id")"
flatpak remote-info --user --arch=aarch64 --show-metadata flathub "$runtime_ref"
```

Both apps and runtimes may require a newer Flatpak version. Do not remove version constraints, disable sandboxing, or install x86_64 packages to bypass errors. Runtime branch numbers are not host Flatpak versions; runtime `25.08`, for example, does not mean Flatpak 25.08 is required.

Only after checking host compatibility, metadata, versions, and free space:

```bash
flatpak install --user --arch=aarch64 flathub "$app_id"
flatpak run --user "$app_id"
```

Inspect the architecture, runtime, disk usage, and permissions in the installation prompt. The first runtime download may be much larger than the app. After installation, test touch, keyboard, windows, file chooser, and any required audio/video features.

User-installed desktop entries are exported to `~/.local/share/flatpak/exports/share`. On this JingOS build, additional integration was needed for the home screen to register them; follow the steps below.

### Graphical Flathub store

Bazaar 0.10.0 (`io.github.kolunmi.Bazaar`, aarch64) was installed for `gao` on 2026-11-20. Its window started, the ARM64 application catalog synchronized, and its search provider returned application results. The user reported seeing the store. Installing an application through its graphical interface still needs separate verification.

Open **Bazaar** from the home screen, or run this in `gao`'s desktop terminal:

```bash
flatpak run --user io.github.kolunmi.Bazaar
```

Flathub provides the software repository; Bazaar provides its graphical browser and installer. The bundled JingOS Discover build only listed `packagekit-backend` in `plasma-discover --listbackends`. Although `plasma-discover-backend-flatpak` was installed, its package contained documentation without a backend plugin. Use Bazaar for the graphical Flatpak workflow on this device.

For replacing the vendor catalog and system-update services, see [Rebuilding JingOS Application and Update Services](self-hosted-services.md). That guide records the inspected interfaces and a proposed self-hosted migration procedure; the replacement services have not been deployed.

### Missing home screen icons

On 2026-11-20, linking the exported launchers into `~/.local/share/applications` and rebuilding the KDE application cache caused JingOS to add Bazaar and GNOME Calculator to its saved home screen grid. The original icon positions were preserved. The links follow Flatpak's exported launchers across application updates.

The links, KDE cache entries, and saved grid positions were verified. After unlocking the tablet, the user confirmed that both icons were visible and that tapping each icon opened its application. Earlier native KDE command-line launch probes timed out after 25 seconds while the tablet was locked; those timeouts are retained in the maintenance logs.

Run as **`gao` in the tablet's graphical terminal**, without sudo:

```bash
mkdir -p "$HOME/.local/share/applications"
for desktop_file in "$HOME/.local/share/flatpak/exports/share/applications/"*.desktop; do
  [ -f "$desktop_file" ] || continue
  launcher_path="$HOME/.local/share/applications/${desktop_file##*/}"
  if [ ! -e "$launcher_path" ] && [ ! -L "$launcher_path" ]; then
    ln -s -- "$desktop_file" "$launcher_path"
  fi
done
kbuildsycoca5 --noincremental
```

This preserves existing files and links. Repeat after installing another app if its icon is missing; automatic integration for future installations has not been configured. Return to the home screen and tap each new icon to verify visibility and launch. GNOME Calculator and the factory Calculator are separate applications.

After uninstalling an app, inspect its user launcher with `readlink` and remove only a link pointing to that app's Flatpak export, then rebuild the cache. Preserve unrelated launchers. A KDE cache query alone does not establish that an icon is visible or can be tapped.

## Updates, permissions, and removal

Use the same desktop account:

```bash
flatpak list --user --app
flatpak update --user
flatpak info --user --show-permissions "$app_id"
flatpak override --user --show "$app_id"
```

App configuration and data usually live in `~/.var/app/<app-id>/`. Prefer portal file chooser authorization. If the app needs direct access to Documents, grant it only to that app:

```bash
flatpak override --user --filesystem=xdg-documents "$app_id"
```

`flatpak override --user --reset "$app_id"` clears all user overrides for the app. Record existing settings before using it.

Remove an app or unused runtimes:

```bash
flatpak uninstall --user "$app_id"
flatpak uninstall --user --unused
```

Back up app data first. Avoid `--delete-data` unless data removal is intended. `flatpak update` updates apps and runtimes, not the host Flatpak client or kernel.

## Diagnose common Flatpak blockers

### Adding a remote or retrieving the summary times out

Distinguish network reachability from a successful repository operation. Use the tablet's existing Python installation:

```bash
python3 - <<'PY'
import urllib.request
for path in ["flathub.flatpakrepo", "summary", "summary.sig"]:
    url = "https://dl.flathub.org/repo/" + path
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=15) as response:
        print(path, response.status, response.headers.get("Content-Length"))
PY
```

Then inspect Flatpak's own output as the target user:

```bash
flatpak remote-info --user --arch=aarch64 --verbose --ostree-verbose \
  flathub org.gnome.Calculator
```

If it still stalls at the summary, record the complete error, duration, network state, and client versions. Check the clock, CA certificates, proxy settings, and large downloads. A single HTTP 200 does not establish correct repository configuration. Remove proxy credentials before sharing logs.

Downloading `.flatpakrepo` first and adding it locally was tested on this device. It still fetches the summary online and cannot fix old OSTree's size limit. Address the host OSTree/Flatpak version instead; the old `max-metadata-size` setting does not control this summary path. `.flatpakrepo` and `.flatpakref` files are descriptors, not offline application packages.

### The app requires a newer version of Flatpak

Upgrade the **host client**. Restore same-release Ubuntu sources as described below, then inspect actual candidates with `apt-cache policy flatpak`. Do not assume focal's standard repositories provide the version an app needs.

The experiment verified and installed Flatpak stable PPA packages for focal/arm64. Dependencies were satisfied, but the factory 4.14 kernel lacked required interfaces; the combined patches have since passed Calculator CLI tests. The PPA branch is unmaintained. Do not treat `add-apt-repository` as a sustainable update solution. Other backports or custom builds also need kernel compatibility and security maintenance checks. Do not mix in jammy/noble packages or copy a newer executable over a system file.

Runtimes also have support lifecycles. Keeping an EOL runtime indefinitely to accommodate an old client should not be the default approach.

### statx didn't return all required fields

This is a confirmed factory-kernel blocker occurring before Calculator executes. `strace` and independent syscall probes show that the factory kernel supports `statx`, but its returned mask lacks a mount ID. The libglnx bundled with Flatpak 1.16.6 rejects the missing field. This differs from Wayland connection, lock screen, or GTK rendering errors.

Current upstream main-branch documentation requires Linux 5.8 for `STATX_MNT_ID`. That is the version that introduced the upstream interface; vendor 4.14 kernels can also receive a real backport. The combined patches passed device syscall, sandbox, Calculator CLI, and GUI tests, and the user confirmed touch and sound. The same-platform 5.15 candidate remains untested on the device. See [kernel research](kernel-upgrade-research.md) and the [execution log](kernel-backport-2026-11-18.md).

This work did not establish a continuously maintained Flatpak client or kernel update channel. Implementing the missing interface does not restore full security maintenance to the old system. Changing runtimes, expanding app permissions, switching repositories, and software rendering cannot supply the missing field.

No downgrade or removal of Flatpak checks was used to skip this requirement. The kernel experiment implemented the real interface and retained the installed app, runtime, and backups for follow-up testing. See the [historical test log](flatpak-test-2026-11-13.md) for the original unmodified-kernel result.

### GUI blank screen, crash, or file chooser failure

JingOS uses libhybris/hwcomposer. Mesa bundled in a Flatpak runtime is not automatically compatible with this stack. Launch from the desktop terminal and retain error output first.

For Qt apps, software rendering can be a temporary diagnostic. Its behavior and performance need testing:

```bash
flatpak run --env=QT_QUICK_BACKEND=software \
  --env=QT_OPENGL=software "$app_id"
```

Portals are activated on demand by the desktop user's D-Bus session. Check them from that user's graphical terminal:

```bash
systemctl --user status xdg-desktop-portal xdg-document-portal
journalctl --user -b -u xdg-desktop-portal --no-pager -n 100
```

The KDE portal backend on this device is D-Bus activated and has no corresponding systemd user unit. `systemctl --user start xdg-desktop-portal-kde` is not a general fix. Do not grant every app access to the whole root filesystem to resolve an individual file access issue.

## Optional: restore Ubuntu APT repositories

**These are configuration instructions; they have not been executed.** Flatpak desktop app installation does not require this section first. Use it when system tools or a host Flatpak update are needed.

Official Ubuntu ARM64 repositories were reachable and their signatures verified, but they do not contain the customized JingOS repository. Keep `focal`. Do not switch Ubuntu releases or run blanket `upgrade`, `full-upgrade`, `dist-upgrade`, `do-release-upgrade`, or blind `autoremove` operations.

### Back up configuration and package inventories

Run each block in the **tablet's root shell** and retain the printed backup path:

```bash
mkdir -p /home/gao/jingos-maintenance
backup_dir="/home/gao/jingos-maintenance/apt-$(date +%Y%m%dT%H%M%S)"
mkdir -m 700 "$backup_dir"
cp -a /etc/apt "$backup_dir/apt"
dpkg-query -W > "$backup_dir/packages.tsv"
apt-mark showmanual > "$backup_dir/manual-packages.txt"
apt-mark showhold > "$backup_dir/held-packages.txt"
printf '%s\n' "$backup_dir"
```

Choose another directory name if it already exists; do not overwrite a backup. `apt-mark showhold` was empty during the checks, so do not assume the system already protects all customized components.

### Disable unavailable sources and use official same-release ARM64 repositories

The customized repository is in `/etc/apt/sources.list.d/jingos.list`. Preserve it under a name that does not end in `.list`:

```bash
mv /etc/apt/sources.list.d/jingos.list \
  /etc/apt/sources.list.d/jingos.list.disabled
```

Set `/etc/apt/sources.list` to:

```text
deb [arch=arm64 signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] https://ports.ubuntu.com/ubuntu-ports/ focal main restricted universe multiverse
deb [arch=arm64 signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] https://ports.ubuntu.com/ubuntu-ports/ focal-updates main restricted universe multiverse
deb [arch=arm64 signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] https://ports.ubuntu.com/ubuntu-ports/ focal-security main restricted universe multiverse
```

Keep signature verification enabled. The old `/etc/apt/preferences.d/jingos.pref` only sets priority 999 for `archive-mirrors.jingos.com`; it does not protect customized packages after switching to official sources.

### Refresh indexes and simulate each installation

```bash
apt-get update
apt-cache policy flatpak git gcc g++ cmake
apt-get -s --no-remove install git g++ cmake pkg-config expect
```

The global source configuration, index refresh, and Git/G++/CMake dependency simulation in this section have not been executed. The Flatpak experiment used separate temporary indexes and verified the four-package installation plan without changing persistent sources. Check future installations on the device. Even if `apt-get update` exits 0, inspect warnings for failed sources or reuse of stale indexes.

If the plan replaces or removes JingOS, Qt, KDE, libhybris, hwcomposer, firmware, the kernel, networking, or base system libraries, stop that installation and analyze the dependencies. `--no-remove` does not prevent every unsuitable upgrade. Only install selected tools once the simulated plan is understood:

```bash
apt-get --no-remove install git g++ cmake pkg-config expect
```

This tool set is an example, not a requirement to install everything at once. `expect` provides `unbuffer` for Mix commands in the development guide. If repository locations later move, revalidate official archive locations and signatures; do not disable HTTPS or GPG verification.

### Configuration rollback and maintenance lifecycle

To undo the repository configuration changes in this section, use the recorded `backup_dir`:

```bash
cp -a "$backup_dir/apt/sources.list" /etc/apt/sources.list
cp -a "$backup_dir/apt/sources.list.d/jingos.list" \
  /etc/apt/sources.list.d/jingos.list
rm /etc/apt/sources.list.d/jingos.list.disabled
```

This restores source configuration only. **It does not roll back installed or upgraded packages**, and it does not bring the old JingOS repositories back online. Back up system and application data separately before package changes.

Ubuntu 20.04 standard security maintenance ended in May 2025; ESM is separate Ubuntu Pro coverage. Public repository availability does not mean the entire JingOS system, custom kernel, or every package remains security-maintained.

## Official references

- [Flatpak usage and commands](https://docs.flatpak.org/en/latest/using-flatpak.html)
- [Flatpak metadata / required-flatpak](https://docs.flatpak.org/en/latest/flatpak-command-reference.html#flatpak-metadata)
- [Flatpak runtimes and support lifecycles](https://docs.flatpak.org/en/latest/available-runtimes.html)
- [Flatpak sandbox and portal permissions](https://docs.flatpak.org/en/latest/sandbox-permissions.html)
- [Official Flathub repository descriptor](https://dl.flathub.org/repo/flathub.flatpakrepo)
- [Ubuntu release and support lifecycle](https://ubuntu.com/about/release-cycle)

References describe current documentation; the device client is 1.16.6. Repository setup, Calculator installation, CLI, and GUI tests passed, and the user confirmed touch and sound. Portals, input methods, Flatpak audio/video, app GPU acceleration, and other apps need separate acceptance tests.
