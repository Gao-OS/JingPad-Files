# Application Development and Elixir Service Deployment

[Home](../README.md) · [Device status](device-status.md) · [Software management](software-management.md)

## Choose a development path

| Goal | Suitable approach | Current validation on this device |
| --- | --- | --- |
| Touch-oriented business UI or control panel | Web / Phoenix, accessed through a browser | Networking verified; the specific project, browser compatibility, and service remain unverified |
| Close integration with the JingOS desktop | Qt Quick / QML matching the installed Qt 5.15.2 and interfaces | System Qt libraries confirmed; development SDK not configured |
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

Some old SDK and installation links are unavailable and need individual checks. The historical [Flutter installation guide](https://github.com/JingOS-team/JingOS/blob/main/doc/guide_install_flutter.md) discusses OpenGL/libhybris compatibility and software rendering. Flutter GUI has not been verified on this device and is not listed as a working development environment.
