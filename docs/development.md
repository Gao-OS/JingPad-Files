# Application Development and Elixir Service Deployment

[Home](../README.md) · [Device status](device-status.md) · [Software management](software-management.md)

## Choose a development path

| Goal | Suitable approach | Current validation on this device |
| --- | --- | --- |
| Touch-oriented business UI or control panel | Web / Phoenix, accessed through a browser | Networking verified; the specific project, browser compatibility, and service remain unverified |
| Close integration with the JingOS desktop | Qt Quick / QML matching the installed Qt 5.15.2 and interfaces | System Qt libraries confirmed; development SDK not configured |
| Flutter desktop UI | Package a Linux ARM64 release with a compatible Flatpak runtime | GSMLG basic use, 2x sizing/touch, and keyboard entry confirmed on 2026-11-21; Chinese display confirmed on 2026-11-22 |
| Independently distributed desktop app | Build an aarch64 Flatpak with a matching runtime | Calculator CLI and GUI passed with the combined kernel patches, and the user confirmed touch and sound; custom apps need separate acceptance tests |
| Long-running Elixir backend service | ARM64 Release including ERTS, managed by systemd | Hardware and system prerequisites are available; no project has been selected or deployed |

Edit, test, and build on the maintenance computer, then transfer ARM64 artifacts to the tablet. The tablet does not need a full development toolchain. Whether to compile natively depends on the dependencies, versions, and build environment.

## Establish compatibility requirements

- The target is Linux **aarch64 / arm64**, with host glibc **2.31**.
- The maintenance computer runs x86_64 NixOS. Its Erlang binaries, NIFs, and Nix store path dependencies cannot simply be copied to the tablet.
- CPU architecture, glibc/musl, and dynamic library versions must match. Portable BEAM bytecode does not make its runtime or NIFs portable between arbitrary systems.
- Executables built on a newer Ubuntu release may require a newer glibc. If `GLIBC_x.xx not found` appears, adjust the build environment instead of replacing the device's libc.
- The system has OpenSSL 1.1.1 runtime libraries. Modern OTP releases or NIFs may need another version; inspect and package the actual requirements. Do not assume the latest OTP can use the installed libraries directly.
- The vendor 4.14 kernel and graphics drivers are also runtime constraints. A separate runtime or container does not remove kernel, hardware, or suspend limitations.

## Qt / QML applications

The device has Qt core libraries 5.15.2 with JingOS/KDE modifications. Before selecting an SDK, check that the required Qt modules, QML imports, JingOS controls, and platform plugins exist.

GCC and Python are available; G++, CMake, and Git are not installed. `qmake` exists, but its default Qt configuration query fails. Running Qt applications does not establish that a complete Qt development environment is available.

If tools are needed, follow the [software management guide](software-management.md) to restore APT repositories for the same Ubuntu release and simulate installation first. Build in a compatible ARM64 environment and transfer artifacts with ADB if appropriate. Installing an SDK must not replace the JingOS Qt/KDE stack with ordinary Ubuntu desktop packages.

Run graphical tests in the tablet's desktop session. If testing software rendering, set variables only for the target process and record the result; do not change the entire desktop graphics configuration.

## Flutter Linux desktop apps

On 2026-11-21, the existing GSMLG ARM64 Linux release from `rock-5-itx` was packaged and installed for `gao` as `org.gsmlg.app`. Its source revision is `d5120c82c6bd956ea630941a4f686cab3d7954cf`, built with Flutter **3.47.7** and Dart **3.13.5**, with local LLM support disabled. The existing executable, plugins, and application assets were reused; no Flutter SDK is needed on the tablet. The original kiosk process on `rock-5-itx` remained running.

The native executable requires glibc 2.34, and its secure-storage plugin requires 2.38; JingOS provides 2.31. The Flatpak uses the already installed `org.gnome.Platform/aarch64/51`, whose glibc was 2.44 at this check, together with its GTK3, GStreamer, and libsecret libraries. A build for another CPU architecture, or a bundle requiring newer native symbols, needs a separate compatibility check.

Run these commands in **`gao`'s graphical terminal on the tablet**:

```bash
flatpak info --user org.gsmlg.app
flatpak info --user --show-commit org.gsmlg.app
flatpak run --user org.gsmlg.app
```

The installed commit is `34e5d12bf19f059e62ffa1625ea9e5813dbb830d4bd96de719bfa9dc3db78f2b`, including the screen-keyboard integration and Chinese font profile below. The app wrapper sets `LD_LIBRARY_PATH=/app/lib/gsmlg/lib:/app/lib`, `LIBGL_ALWAYS_SOFTWARE=1`, and `LP_NUM_THREADS=2` for this app. The startup log reported the Impeller OpenGLESSDF backend. This verifies a software-rendering deployment; hardware acceleration has not been established.

### HiDPI configuration

The user confirmed that GSMLG was usable, then reported that text, buttons, and icons were all too small. GTK 3.24.52 in the app's native Wayland session reported scale 1 and a logical monitor size of 2072 by 1512. A process-local `GDK_SCALE=2` probe still reported scale 1 on Wayland. Flutter 3.47.7's Linux embedder derives its viewport pixel ratio and input-coordinate scaling from GTK's widget scale factor.

The current device profile runs **only GSMLG** through Xwayland with a GTK scale factor of 2. Run as `gao`:

```bash
flatpak override --user --nosocket=wayland --socket=x11 \
  --env=GDK_BACKEND=x11 --env=GDK_SCALE=2 org.gsmlg.app
```

Close GSMLG normally, then reopen it from its home screen icon or with `flatpak run --user org.gsmlg.app`. The override persists for future launches. A probe using the saved profile, without additional launch flags, reported an X11 display, GTK widget/monitor scales of 2, and a logical monitor size of 1036 by 756. The restarted app remained running with the saved environment and a responsive 2072-by-1470 Xwayland window. The user confirmed that the size and touch behavior were satisfactory. A full reboot has not been tested with this profile.

The previous override state and DPI verification records are retained under `dpi-20261121T112950Z-57jlv4px/` inside the maintenance directory below. That initial state had no app-specific override file. If these display settings remain the only user overrides, `flatpak override --user --reset org.gsmlg.app` restores the original profile after restarting the app. If other overrides have since been added, preserve them when reverting the display settings.

### On-screen keyboard

After the DPI adjustment, the user reported that several input fields could not open the screen keyboard. JingOS's Maliit keyboard was running and enabled. The sandbox inherited `GTK_IM_MODULE=Maliit`, but the GNOME runtime had no Maliit GTK module, and the app had no permission to discover `org.maliit.server`. Setting the environment variable alone was insufficient.

The keyboard rebuild includes the existing tablet's `maliit-inputcontext-gtk3` module, the matching `libmaliit-glib.so.0`, and its private Qt5Core, double-conversion, and ICU 66 dependencies. These were copied from the working JingOS installation and checked in the GNOME runtime. At that rebuild, all 157 original release-manifest files remained hash-identical. The package adds a GTK module cache containing the runtime's original entries plus `Maliit`, and declares:

```ini
[Environment]
GTK_IM_MODULE=Maliit
GTK_IM_MODULE_FILE=/app/lib/gtk-3.0/3.0.0/immodules.cache
LD_LIBRARY_PATH=/app/lib/gsmlg/lib:/app/lib

[Session Bus Policy]
org.maliit.server=talk
```

The Maliit address is discovered through D-Bus; its peer connection uses an abstract Unix socket reachable through the app's existing shared network namespace. No host filesystem grant was added to the installed app. This integration targets the GTK3/X11 profile above; native Wayland and other GTK versions need separate checks.

Loader relocation checks passed, a sandbox probe selected the `Maliit` context and read the server address, and the restarted GSMLG process loaded both Maliit libraries while retaining scale 2. The user then confirmed automatic keyboard popup and text entry. The validation did not record the entered text. Complex composition, additional keyboard layouts, and a full reboot have not been tested.

The signed rebuild, source-package versions, library hashes, rollback commit, and acceptance records are under `keyboard-20261121T140031Z-om8jtl02/` in the maintenance directory below. The previous app commit was `3df331c3a9668885528b7ca93309aeae882eef000ff79593988443cc7fc3770a`; app data and the DPI override were preserved during the update.

### Chinese text and packaged fonts

Chinese characters appeared as missing-glyph boxes in GSMLG even though JingOS displayed Chinese correctly. Both the host and sandbox's `fc-match sans-serif:lang=zh-cn` found Source Han Sans CN; inside Flatpak it was mounted under `/run/host/fonts/`. Fontconfig availability alone did not establish that Flutter used those fonts.

The matching Flutter 3.47.7 engine source (`deb287481e3ce9468f3434937ced4240a70539ca`) selects a directory font manager scanning `/usr/share/fonts/` when built without Fontconfig support. Its matching Skia directory manager has no character-based fallback. The deployed engine contained that directory path and no Fontconfig API imports. Changing the system language or rebuilding Fontconfig caches does not supply the missing Flutter default font.

The device profile now includes the tablet's unchanged `SourceHanSansCN-Regular-2.otf` as a Flutter asset, with the SIL Open Font License included under `/app/share/licenses/org.gsmlg.app/`. Append this entry to the existing `data/flutter_assets/FontManifest.json`, preserving all existing icon and math font declarations:

```json
{
  "family": "Ubuntu",
  "fonts": [
    {"asset": "fonts/SourceHanSansCN-Regular.otf", "weight": 400}
  ]
}
```

`Ubuntu` is an application-level alias for Source Han Sans CN here, chosen because it is the engine's first Linux default family. It supplies a CJK-capable default when a requested family is unavailable; it does not install the Ubuntu font or implement arbitrary system-font fallback. This also changes the default Latin font. Explicit requests for an available Latin-only family can still lack Chinese glyphs, and additional scripts, emoji, and font weights need separate validation. No GSMLG source or engine binary was changed.

A small release-mode rendering fixture was built on `rock-5-itx` with two CPUs and nice level 10. Its engine was hash-identical to GSMLG's. In the actual sandbox, the original profile rendered four known Chinese characters as one identical missing glyph. With the packaged default, all four characters matched the independently loaded reference font exactly for default, `Roboto`, `monospace`, and `sans-serif` requests. These images contain fixed test text, not a desktop capture or user input. The original GSMLG release's other 156 manifest-listed files remained hash-identical; only `FontManifest.json` changed, alongside the added font and license.

The signed font update was installed on 2026-11-22 (tablet local time), preserving the keyboard metadata, app-specific DPI override, and launcher layout. After a normal close and restart, the responsive GSMLG process mapped the new font and both Maliit libraries while retaining `GDK_SCALE=2`. The user confirmed normal Chinese display after the update. Its previous commit is `bd6553164bec22b48d7510e6cff4117b491e9df43f00806fd1e7ce451bd4392d`. Package, signature, rollback, rendering, and user-acceptance records are retained under `fonts-20261121T155640Z-c5eoca36/` in the maintenance directory below. A full reboot with this profile remains untested.

### Local repository and updates

The local origin is `jingpad-gsmlg-local`. Both the repository commit and summary signatures were checked with GPG, and both signature requirements are enabled on that remote. The signing fingerprint is `EE8C81A7E35BFFC2CA828CEF34CCEF4ADCAA04AF`. This is a private local test repository, not a public update service. Its key and build materials are retained outside Git under `/home/gao/jingos-maintenance/flutter-20261121T094800Z-gsmlg-2itfd9mq/` on the tablet. Keep that repository available when updating this app:

```bash
flatpak update --user --no-deps --no-related org.gsmlg.app
```

This applies only the local app rebuild with the already installed, verified runtime. It does not resolve or update runtime dependencies; check the declared runtime separately for future builds. An earlier update attempt with dependency/related-ref handling enabled timed out; this app-only update completed. The command does not fetch a newer GSMLG source revision or rebuild it. Future releases must first be exported and signed with the same trusted key, or use an explicitly configured replacement repository. Single-file `.flatpak` generation timed out after 150 seconds during this experiment; the successful installation used the signed local repository directly.

Packaging and acceptance findings:

- All 157 files listed in the original build manifest passed hash verification after transfer. The font rebuild intentionally changes only `FontManifest.json` among those original files, as explained above. Dynamic-loader relocation checks passed for the runner, SQLite, and Tree-sitter libraries in the chosen runtime.
- PNG launcher icons must be at most 512 pixels per side for Flatpak export. The package exports a 256-pixel PNG and the original SVG; the original application icon assets are preserved.
- A `flatpak build` test needed an explicit display variable, then failed because GTK's image-loader helper tried to spawn an uninstalled app. After installation, the same nested-sandbox probe passed. Test the installed application when validating these helpers.
- The initial native Wayland window submitted a 2072-by-1470 buffer, and the user confirmed basic use. The current profile uses Xwayland with user-confirmed 2x sizing/touch and Maliit keyboard input. Its window, live process, input module, and service access were checked separately. Other application features need separate acceptance. AT-SPI and unsupported desktop-portal settings produced startup warnings and remain unverified.
- `/usr/share/applications/org.gsmlg.app.desktop` links to the user's stable Flatpak export, following the [home screen integration procedure](software-management.md#missing-home-screen-icons). KDE found one launcher, JingOS saved it at `0,11`, and previous positions were preserved. Icon visibility, tapping this new icon, and a full device reboot remain unverified.

App data belongs to the tablet user under `~/.var/app/org.gsmlg.app/`; the kiosk's account data and credentials were not copied. To remove this test installation, use `flatpak uninstall --user org.gsmlg.app` and remove only its matching system launcher link as described in the software guide. Preserve app data unless deletion is intended.

## Flatpak application development

Flatpak isolates application dependencies. This device has Flatpak 1.16.6 and Calculator 51.1. On 2026-11-19, the combined kernel patches passed real mount ID, sandbox, and compatibility interface tests; Calculator's `--solve=2+2` returned `4`, and the user confirmed GUI, touch, and sound. Historical factory-kernel failures do not describe the patched kernel's current behavior. Calculator's success also does not establish compatibility for every custom app. See the [kernel execution log](kernel-backport-2026-11-18.md) for evidence and the [software management guide](software-management.md) for installation and architecture checks.

When building your own app:

1. Select a maintained Freedesktop, GNOME, or KDE runtime and SDK containing the required libraries.
2. Check the host kernel, Flatpak version, and minimum requirements of both the app and runtime. Successful installation or execution on the development computer is insufficient.
3. Use a native ARM64 environment or a verified ARM64 cross-compilation/emulation workflow; explicitly produce `aarch64` artifacts.
4. Declare the required file, display, network, and audio permissions in the manifest, preferring portals.
5. Deliver through a signed repository or trusted build artifacts. Offline installation also requires the runtime and extensions; a `.flatpakref` file does not contain them.
6. Test startup, touch, input methods, file chooser, sound, display, and the launcher after reboot in the actual JingOS session.

`flatpak-builder` is not installed. This repository does not yet contain a device-validated manifest, so it does not provide an untested app template presented as ready to install.

## Elixir / Phoenix services

### Current assessment

The tablet has the resources to run services: 8 GB RAM, sufficient storage, ARM64 Linux, and systemd. Erlang/Elixir/Mix is not installed, and no demonstration service has been deployed.

Build an **ARM64 Release that includes the Erlang runtime**, using the project's Elixir/OTP versions, and run it under systemd with a dedicated unprivileged account. The target then does not need Mix or the full source tree.

The examples use the release name `jingapp`. Replace it with the actual release name from `mix.exs` and adapt runtime configuration, database access, persistent storage, and health checks to the project. This is an undeployed template, not a validated service installation.

### 1. Select the project and build environment

Inspect `mix.exs`, `mix.lock`, version pin files, CI, `config/runtime.exs`, and existing deployment instructions first. Preserve the project's dependency and startup conventions.

The build environment must meet these requirements:

- aarch64 CPU / ABI, with a base glibc no newer than the target's 2.31; verify the final dependencies.
- An Elixir/Erlang combination supported by the project, with ERTS included in the Release.
- ARM64 builds of all NIFs, port programs, database clients, and other native dependencies.
- SSL, ncurses, libstdc++, and other actual dynamic library requirements matching the target or packaged compatibly with the artifact.

Use a dedicated ARM64 build host or a compatible ARM64 Linux environment. Emulated builds on x86_64 require verified QEMU/binfmt support and a suitable build image; adding `--arch arm64` alone does not create a working emulation environment. Do not modify the tablet's boot chain for this.

### 2. Test, build, and package

Run these commands in the **actual project directory within a target-compatible build environment**. Install `unbuffer` first; Ubuntu provides it in `expect`:

```bash
unbuffer mix deps.get
unbuffer mix test
MIX_ENV=prod unbuffer mix deps.get --only prod
MIX_ENV=prod unbuffer mix compile
```

If the Phoenix project defines an `assets.deploy` alias, build assets using its conventions:

```bash
MIX_ENV=prod unbuffer mix assets.deploy
```

Build the Release and confirm that an `erts-*` directory exists:

```bash
MIX_ENV=prod unbuffer mix release
ls _build/prod/rel/jingapp
file _build/prod/rel/jingapp/erts-*/bin/beam.smp
tar -C _build/prod/rel/jingapp -czf jingapp-aarch64.tar.gz .
sha256sum jingapp-aarch64.tar.gz
```

`file` should identify an AArch64 ELF executable. Check all NIFs and external programs too; checking `beam.smp` alone does not validate the whole Release. Projects using `include_erts: false` need a different packaging configuration; do not assume Erlang exists on the target.

A packaged Release is not automatically compatible with every ARM64 Linux system. Start and validate it in a matching environment before deploying it to the tablet.

### 3. Transfer artifacts and prepare service directories

Push the completed build from the maintenance computer:

```bash
adb -s C12144MKCA001176 push jingapp-aarch64.tar.gz /tmp/jingapp-aarch64.tar.gz
adb -s C12144MKCA001176 shell
```

In the tablet's root shell, run `sha256sum /tmp/jingapp-aarch64.tar.gz` and compare it with the build host's result. As with all ADB examples, use the serial from the current device enumeration.

For the first deployment, create a dedicated system user and use these directories:

| Path | Purpose |
| --- | --- |
| `/opt/jingapp/releases/<version>/` | Versioned artifacts managed by root, readable and executable by the service user |
| `/opt/jingapp/current` | Symlink to the active version |
| `/var/lib/jingapp` | Service user's home and persistent data |
| `/etc/jingapp.env` | Root-owned environment configuration, mode 0600; never committed |

Example user creation; first run `id jingapp` to check for an existing account:

```bash
useradd --system --user-group --home-dir /var/lib/jingapp \
  --create-home --shell /usr/sbin/nologin jingapp
```

Extract the trusted package into a new version directory, then set `current`. Keep the previous version. The service user should not be able to rewrite release executables. Put writable data under `/var/lib/jingapp` as required instead of making all of `/opt` writable.

Include only configuration the application actually reads in `/etc/jingapp.env`. A web project might use `PORT`, `PHX_HOST`, `PHX_SERVER`, `SECRET_KEY_BASE`, and a database address. `RELEASE_COOKIE` can supply a deployment-specific cookie. Use securely generated values and keep development keys, cookies, database passwords, and environment files out of Git.

Environment variables do not automatically configure arbitrary applications to listen on a port. Phoenix's `PHX_HOST` normally specifies the URL hostname, not the listening address. LAN access also requires the project configuration to read and set the correct listening IP.

### 4. Configure systemd

Create `/etc/systemd/system/jingapp.service`, adapting the release name and data paths:

```ini
[Unit]
Description=JingPad Elixir service
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=jingapp
Group=jingapp
WorkingDirectory=/opt/jingapp/current
EnvironmentFile=/etc/jingapp.env
Environment=RELEASE_TMP=/var/lib/jingapp/tmp
StateDirectory=jingapp
StateDirectoryMode=0750
UMask=0077
ExecStart=/opt/jingapp/current/bin/jingapp start
Restart=on-failure
RestartSec=5
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

Use foreground `start` under systemd. Run database migrations through the project's existing release tasks. Do not assume Mix is available inside a Release or attach migrations to every restart without confirming the application's requirements.

After preparing files, configuration, dynamic dependencies, and the actual startup path:

```bash
systemd-analyze verify /etc/systemd/system/jingapp.service
systemctl daemon-reload
systemctl enable --now jingapp
systemctl status jingapp --no-pager
journalctl -u jingapp -b --no-pager -n 100
```

### 5. Verify and update

Deployment acceptance should establish at least the following:

- The service runs as `jingapp`, remains active under systemd, and has no dynamic library, NIF, or configuration errors in its logs.
- The tablet can access the actual health endpoint, with the status code and response specified by the project.
- Another LAN computer can reach the tablet's current IP and service port; loopback-only access does not establish LAN reachability.
- Required database connections, migrations, reads, and writes work, and persistent data is stored in the intended directories.
- The service remains reachable after the screen turns off and after waiting. Test suspend policies separately for always-on operation; an active systemd unit does not prevent CPU suspend.
- Reboot the tablet when physical assistance is available, then confirm automatic startup and data retention.

For a project providing `/health` on port 4000, check from the maintenance computer, replacing the route and IP as needed:

```bash
curl --fail --show-error http://10.100.8.232:4000/health
```

Use the LAN for initial development. Configure domains, HTTPS, reverse proxies, and external access separately according to actual needs. This work did not expose a service publicly or change the firewall.

For updates, place the new Release in a separate version directory, run preflight checks, then switch `current`, restart, and validate. Database changes may make the previous version incompatible; account for migrations and business data before rollback.

## Source code and reference material

These repositories explain existing interfaces and build methods. Their availability does not establish a complete, reproducible C1 firmware build environment:

- [JingOS repository and documentation](https://github.com/JingOS-team/JingOS)
- [JingOS controlkit](https://github.com/JingOS-team/controlkit)
- [Plasma phone components](https://github.com/JingOS-team/plasma-phone-components)
- [JingOS kernel4.14](https://github.com/JingOS-team/kernel4.14)
- [JingPad Android BSP archive](https://github.com/deadman96385/jingpad_android_bsp)
- [Flatpak first build](https://docs.flatpak.org/en/latest/first-build.html)
- [Mix Release documentation](https://hexdocs.pm/mix/Mix.Tasks.Release.html)

Some old SDK and installation links are unavailable and need individual checks. The historical [Flutter installation guide](https://github.com/JingOS-team/JingOS/blob/main/doc/guide_install_flutter.md) discusses OpenGL/libhybris compatibility and software rendering. See [Flutter Linux desktop apps](#flutter-linux-desktop-apps) for the current GSMLG deployment and its acceptance limits.
