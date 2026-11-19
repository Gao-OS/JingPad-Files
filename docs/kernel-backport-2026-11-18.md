# 4.14 Kernel Mount ID Backport Execution Log

[Home](../README.md) · [Source research](kernel-upgrade-research.md) · [Flatpak baseline](flatpak-test-2026-11-13.md)

Status, 2026-11-19: **Backport acceptance is complete. The combined kernel booted, and real mount ID, proc sandbox, Ticket protocol, and original module checks passed. KWin/PowerVR compositing, audio, and power services respond normally. Flatpak Calculator returned `4` for `2+2` and `30` for `(12+8)*3/2`; the user confirmed Calculator GUI, touch, and speakers.**

All times in this log are China Standard Time (UTC+8). Work began at **2026-11-18 00:40**, with an initial eight-hour limit ending at **08:40**. The objective was to implement real `STATX_MNT_ID` support on the factory 4.14.133 kernel, verify existing drivers and Flatpak, and preserve JingOS and user data.

At **07:08**, the user authorized up to **five more hours** from that point. At **23:48**, the user authorized a fresh **eight-hour** window, with a final experimental deadline of **2026-11-19 07:48**. Attempts were unlimited within the window, and all historical attempt records were retained.

The combined candidate was compiled, written to boot, and automatically checked within that window. Manual confirmation followed at approximately **2026-11-19 22:10**. The evening follow-up only inspected the current session and application and restored Calculator to the foreground; no additional kernel build or boot write occurred.

## Completed preparation and tests

| Check | Result |
| --- | --- |
| Boot and calibration partition backups | 23 partitions, all independently compared using device-side and host-side SHA256 |
| Current GPT | Primary and backup tables and their CRCs valid; 53 partitions, 4096-byte logical sectors |
| Current recovery path | Loaded stock C1 FDLs into RAM from genuine BROM (`1782:4d00`, `bcdDevice=ffff`); the 1 MiB partition table prefix matched the Linux backup byte for byte, with all 53 partition CRCs, positions, and sizes matching; then rebooted normally into the original system |
| `boot` partition | 35 MiB; Android boot header v2; uncompressed ARM64 Image, original ramdisk, and DTB |
| Driver location | 22 `.ko` files in the `socko` ext4 filesystem; `odmko` was empty |
| Driver compatibility baseline | Extracted 710 required symbol CRCs; original vermagic `4.14.133-202201191758+ SMP preempt mod_unload modversions aarch64` |
| Baseline build symbol compatibility | 695 kernel export CRCs matched factory modules; another 15 came from retained factory `sprd_vdsp.ko` / `vdsp_sipc.ko`; all 710 resolved, with no changed CRCs or unresolved symbols |
| Missing interface reproduction | Original kernel syscall succeeded but returned no mount ID; comparison with `/proc/self/fdinfo` failed |
| Bind mount control | In a private mount namespace, two paths to the same device and inode had distinct `fdinfo` mount IDs; all 12 `statx` calls lacked mount IDs, matching the original kernel |
| Flatpak baseline | Calculator launched with the actual desktop session environment still reported `statx didn't return all required fields` |
| Boot signing | BSP boot public key matched the device; offline repack/sign of the original image reproduced the full 35 MiB backup byte for byte; explicit trusted public key verification passed |
| Packaging tool | 10 host tests passed, including damaged images, wrong keys, and rejected inputs; modified kernel fixtures were marked `NEVER_BOOT` and must not be installed |
| Source | Retrieved and verified all 63,112 files from the pinned official source commit |
| Baseline rebuild | Full `Image modules dtbs` completed, producing 252 modules; all 4,352 configuration options matched the device |
| Baseline image installation | Wrote only `boot`; full readback and trusted public key verification passed; actual baseline marker observed; 24 syscall controls reproduced missing mount IDs; baseline desktop was not manually accepted |
| Full patched build | Full `Image modules dtbs` completed, with `BUILD_PHASE_COMPLETE patched` in the log |
| Full patched ABI checks | All 11,524 exported symbol entries matched the baseline; `Module.symvers` SHA256 was identical; all 710 required symbols matched |
| Patched configuration and release | All 4,352 options and original UTS_RELEASE preserved; build marker `gao@jingpad-patched-statx414` |
| Patched installation and interface | Full readback and trusted public key verification passed; actual marker `gao@jingpad-patched-statx414`; all 24 real syscall checks across both probes passed |
| First patched desktop and Flatpak | Desktop remained at the logo; Calculator passed the mount ID check but reported `bwrap: Can't mount proc on /proc: Device or resource busy`; the combined patches below resolved these failures |
| Proc fix | Minimal `sget_userns(..., ns->user_ns, ns)` fix passed full build and ABI/config checks; booted in the combined candidate; USER+PID/proc positive controls passed and unauthorized mounts remained denied |
| Factory rollback control | Restored and independently read back the full factory `boot`; actual `jenkins` marker, original boot hash, KWin compositing, PowerVR, and audio services passed automatic checks |
| Combined candidate build and installation | Ticket compatibility passed 1,010 codec vectors; full build, existing ABI/config, and driver checks passed; wrote only `boot`, with full readback/signature verification; actual running marker and boot hash matched |
| Combined candidate interface retest | All 24 real mount ID calls passed; proc namespace identities matched, unauthorized mounts remained denied; 4 valid Ticket handshakes passed and 8 classes of invalid requests were rejected |
| Combined candidate desktop services | KWin D-Bus, PowerVR Rogue GM9446 / GLES compositing, Plasma, PulseAudio output sink, and repowerd responded; Wi-Fi and HTTPS passed |
| Flatpak Calculator | Actual desktop user `gao` ran `--help`, `--solve=2+2`, and `--solve='(12+8)*3/2'`, all exit 0; calculations returned `4` and `30`, with empty stderr; user confirmed GUI interaction |
| Combined candidate manual acceptance | User unlocked the current patched kernel and explicitly confirmed that Calculator, touch, and sound all worked normally |
| Evening follow-up | Same patched kernel boot, approximately 19 hours uptime; unlock, backlight, and KWin compositing worked; first-buffer and responsiveness checks passed after restoring Calculator to the foreground; this was not a continuous stress test or a complete suspend test |

Pinned source commit: `JingOS-team/kernel4.14@84a635cee601934f5eee09da5ab8e1e2be269a26`.

```text
Source Git tree: 0ffa4d1db290b9f0d2bfe1e34ddd140f1c303050
Source archive SHA256: eee9c58a2f9f952c7a14986c0e3a84dde83f089923788c9cfce01e936c607899
Original boot SHA256: 1c149d658710a4116a76b143065223d6cd17d7ddc2c9be9a095e60945703673b
```

Preprocessing and `genksyms` comparisons showed that adding the newer `mnt_id` field directly to public `struct kstat` changes CRCs for symbols such as `module_layout` and `filp_open`, breaking factory driver compatibility. The backport therefore passes the mount ID through a private helper, preserving the original structure and public function signatures. The complete symbol table still has to be checked after building.

## Patch attempts and correction

The first patch changed only `fs/stat.c` and `include/uapi/linux/stat.h`. It reads `real_mount(path.mnt)->mnt_id` while the path reference is held, passes it through a private output parameter to the syscall, and writes it into reserved userspace space. Static assertions in the actual Kbuild context confirmed that both original and patched `struct statx` are 256 bytes, with the mount ID at offset 144. The patched `fs/stat.o` compiled.

However, including private `fs/mount.h` changed type definitions visible to `genksyms`, changing CRCs for 9 exports including `generic_fillattr` and `vfs_getattr`. ABI acceptance failed and the build was stopped. That version did not complete a full build and was not installed. Unchanged public structure layouts and signatures do not justify skipping driver checks.

The private include was guarded with `#ifndef __GENKSYMS__`: normal compilation still sees complete type definitions, while symbol generation retains the original declaration view. After correction, **all 11 `fs/stat.o` export CRCs matched the baseline**, with no missing or added entries. After the full rebuild, **all 11,524 symbol entries** and **4,352 configuration options** also matched. No CRC values were replaced and no module checks were disabled.

The validated changes are in the [two-file patch](../patches/0001-statx-mount-id-preserve-module-abi.patch), targeting the pinned `84a635cee601934f5eee09da5ab8e1e2be269a26` source commit. `patch --dry-run --batch --fuzz=0 -p1` passed against pristine source. The baseline and patched builds retain the same release for factory module compatibility; device acceptance must check both the `/proc/version` build marker and actual syscall results.

Baseline rebuild artifacts that booted on the device:

```text
Image SHA256: 21d98a9625c20f1280ad00909ebb003b2fcce148706f138c025e2c725e0e6d01
boot.img SHA256: 6db5406073c818a8efed73538ac3de83ae1cf9bb057979e5a894351fabb5b4bf
boot.img size: 36,700,160 bytes
```

The rebuilt baseline booted but did not receive manual desktop acceptance. The original factory boot backup remains available, with its SHA256 listed above. Kernel boot and module loading alone do not establish desktop usability.

Initial mount ID patch artifacts, later superseded by the combined candidate:

```text
Image SHA256: f84588c8a7eca50ba75861497c0b5fbdf08a80a9fb4706365bac644bb3faf73d
boot.img SHA256: 6f3a50eaf73b4cee5933888a7914c2d64f388c106fa3ce8a5dcea1f3e662e08f
boot.img size: 36,700,160 bytes
Module.symvers SHA256, identical to baseline: f3ccf3c49a0ee0fae33f9137559edbc7ff45a81dfb0e74d835ab07acd1ea9609
```

The local work directory's `build/patched-v1/` contains the image, configuration, symbol table, build log, and verification summary. `boot-research/candidates/statx-mnt-id-v1/` contains the signed boot image and component verification records. The full debug `vmlinux` remains in the corresponding work directory on T430. Backups and images are not stored in Git.

## Device results and subsequent compatibility problems

The mount ID patch ran on the tablet. Results for the same FD matched `/proc/self/fdinfo`; the same inode accessed through separate bind mounts returned distinct real IDs. All 24 calls across both probes passed with `all_verified: true`. The corresponding 24 calls on the rebuilt baseline reproduced the missing field. The release and all 18 required factory modules were preserved.

Flatpak then exposed another compatibility problem in the public-source rebuild. As `gao`, the USER-only bubblewrap/proc test passed, but combining USER and PID namespaces caused `/proc` mounting to fail with `EBUSY`. Source and syscall tracing showed that an early-created proc superblock used the parent's user namespace, so a child in the new user namespace was rejected. The fix uses the PID namespace's `ns->user_ns`, preserving capability and permission checks. See the [proc patch](../patches/0002-proc-use-pid-namespace-userns.patch), based on upstream [proc user namespace ownership corrections](https://github.com/torvalds/linux/commit/6e4eab577a0cae15b3da9b888cff16fe57981b3e) and [related superblock semantics](https://github.com/torvalds/linux/commit/e94591d0d90c13166cb6eb54ce5f96ed13d81b55). The factory binary already passed this combined test and continued to reject unauthorized proc mounts, establishing a difference between published source and factory behavior. The combined candidate also passed: sandbox `/proc/self/ns/pid` matched `/proc/1/ns/pid`, and unauthorized proc mounts remained denied.

After the user reported that the first patched build still displayed the logo, KWin stack traces showed KWin, PulseAudio, and repowerd blocked in the existing libhybris `q.so` error path in `ticket_auth_with_kernel()`. The factory kernel contains a built-in `Ticket netlink` interface using protocol 30, missing from the published source and initial rebuilds. Restoring the factory kernel made that socket work and restored KWin PowerVR compositing, desktop processes, and audio services. Full factory image readback matched the backup hash.

Official source history, accessible forks, BSPs, and other JingPad ports were searched without finding authoritative Ticket source. The [Ticket compatibility patch](../patches/0003-jingos-ticket-netlink-compat.patch) reconstructs the interface from static analysis of the factory implementation and real protocol tests; it is not recovered vendor source. Both the factory kernel and combined candidate passed 4 valid handshakes and rejected 8 classes of malformed length, identity, memory, and time requests. The compatibility code also passed 1,010 codec vectors. Desktop, touch, sound, and Flatpak were separately accepted as listed above; interface tests alone were not treated as completion.

The combined candidate, `statx-proc-ticket-v1`, has Image SHA256 `7c4f275347be95d3214062413a9eb1c17df05398fb64d19e7189ed6bf0317e8c` and signed `boot.img` SHA256 `89a7fc6839e61ecf238a6b1e981f8092d9b4263ead8e13aa101c5d8cbc825815`. Configuration, the complete symbol table, and the previously accepted stat/proc objects were preserved. Its build marker is `gao@jingpad-patched-ticket-statx414`.

The actual combined marker was observed at 2026-11-19 03:09. Installation record `boot-research/install-runs/20261118T190804Z-4f1c423c` confirms full readback and trusted public key verification. Runtime checks again verified the boot hash, original configuration, and 18 required modules, followed by the interface, desktop service, and Calculator CLI checks above.

The default Calculator GUI launch used no renderer overrides and disabled no sandbox checks. KWin contained a native `org.gnome.Calculator` `XdgToplevelClient` with a real Wayland surface, a 2072×1470 buffer, and a responsive, nonminimized window. This KWin version's first-buffer commit and window admission lifecycle establishes that the app submitted a buffer to the compositor; it does not independently establish pixel contents or visibility. The first observation occurred while the screen was locked and the backlight was off. After the user unlocked it that evening, Calculator was found minimized. Restoring the original window to the foreground made the unchanged probe pass again. The user then explicitly confirmed, translated into English: "Calculator, touch, and sound all work normally." App GPU acceleration, portals, input methods, Flatpak audio/video, and suspend/resume remain unverified.

Current combined artifacts are in the private work directory's `build/patched-ticket-v1/` and `boot-research/candidates/statx-proc-ticket-v1/`. Baseline and failed candidates, factory rollback controls, and stage logs are retained. The earlier mount ID-only candidate is superseded and should not be treated as the current recommended image.

## Validate real mount IDs

The repository includes a [same-FD comparison probe](../tools/kernel/probe-statx.py) and a [bind mount probe](../tools/kernel/probe-statx-bindmount.py). Both use real ARM64 syscalls and compare mount IDs with `/proc/self/fdinfo` for the same file descriptor. The bind probe also checks that the same inode returns different IDs through different mounts. It creates temporary bind mounts only inside a private mount namespace and cleans up on normal completion.

The current combined kernel has passed both probes. Restoring the factory kernel is expected to return `all_verified: false` again.

```bash
adb devices -l
JINGPAD_SERIAL='replace-with-current-serial'
adb -s "$JINGPAD_SERIAL" push tools/kernel/probe-statx.py /tmp/jingpad-probe-statx.py
adb -s "$JINGPAD_SERIAL" push tools/kernel/probe-statx-bindmount.py /tmp/jingpad-probe-statx-bindmount.py
adb -s "$JINGPAD_SERIAL" shell python3 /tmp/jingpad-probe-statx.py
adb -s "$JINGPAD_SERIAL" shell python3 /tmp/jingpad-probe-statx-bindmount.py
```

Both outputs must report `all_verified: true`. Old ADB `exec-out` may not propagate the remote program's exit status. Inspect real syscall results in JSON instead of relying on the host command returning 0.

Remote Python source must be passed to `exec-out` as a single, complete shell command. Passing separately shell-quoted source as its own argument can preserve extra quotes and cause a syntax error. The installer transport was corrected; 11 host tests and a full read-only preflight on the real device passed. Write, readback, and explicit reboot guards were preserved.

## Build resources and boundaries

The primary build host was `t430`: x86_64, 48 logical CPUs, approximately 96 GiB RAM, matching the original Android x86_64 toolchain. `dgx-spark` was the ARM64 fallback host.

Builds ran as an ordinary user in a temporary cgroup. Verified limits were **400% CPU**, **12 GiB memory maximum**, **8 GiB memory high watermark**, **2 GiB swap maximum**, nice **10**, and at most **4** parallel make jobs. A local fallback would use at most **2** cores and **2** jobs. No persistent host configuration or unrelated services were changed.

The factory Makefile hardcodes paths such as `/bin/pwd`, `/bin/grep`, and `/usr/bin/size`. On the NixOS build host, a temporary Bubblewrap namespace supplied those paths and `/dev`; `size` came from the original cross toolchain's GNU binutils 2.27. This adaptation changed neither kernel source nor global host directories. Nix's default format-warning hardening was disabled only for host build tools; target kernel compilation flags were preserved.

Only public source, toolchains, kernel configuration, and driver symbol metadata were transferred to the build host. Original partition images, calibration data, and signing private keys were neither transferred there nor added to Git. Signing keys were passed to the signing process only through an in-memory file on the maintenance computer.

### Pinned toolchain and reproduction inputs

The build used Android clang **9.0.3 / r353983c / build 5484270**, matching the tablet's `/proc/version`. The original compiler SHA256 was `60883f56ef124bc7c80f79b9796928268ad15846f29fe4035d8a43e60d7c2def`, from the [pinned AOSP mirror commit](https://github.com/msft-mirror-aosp/platform.prebuilts.clang.host.linux-x86/tree/3f889f9c9d42bae85728fa89ba5f92a01704fd83/clang-r353983c). GNU binutils **2.27** came from the [pinned BSP commit](https://github.com/deadman96385/jingpad_android_bsp/tree/e2ae454a203619b297a8711633516ee729811526/toolchain/prebuilts/gcc/linux-x86/aarch64/aarch64-linux-android-4.9). The Nix build environment was pinned to `NixOS/nixpkgs@cd63096d6d887d689543a0b97743d28995bc9bc3`.

Build input used the complete configuration extracted from the tablet's `/proc/config.gz`. Target parameters were `ARCH=arm64`, `CC=clang`, `CROSS_COMPILE=aarch64-linux-android-`, `CLANG_TRIPLE=aarch64-linux-gnu-`, and `JING_BUILD_KERNEL_EXTRAVERSION=-202201191758+`. Baseline and patched builds preserved `4.14.133-202201191758+` and original module vermagic. Build host markers were `jingpad-baseline-statx414`, then `jingpad-patched-statx414`, and finally `jingpad-patched-ticket-statx414` for the combined kernel.

The full build ran `olddefconfig`, followed by `Image modules dtbs`, using `-j4 -l24` under the verified cgroup limits. Preserve source commit, original configuration, toolchain, and target parameters when reproducing. Use complete symbol table and factory module CRC comparisons as the ABI acceptance criteria.

## Acceptance and recovery

Build, ABI, configuration, recovery path, boot readback, real mount IDs, positive and negative proc/Ticket controls, Calculator CLI, and GUI checks all passed. The user confirmed touch and speakers on the current kernel. The 4.14 backport objective is complete. Other Flatpak apps, portals, input methods, camera, stylus, app GPU acceleration, and full suspend/resume are outside this successful result.

If later display or hardware issues appear, preserve the running marker and relevant logs before restoring the original boot image. Recovery must also write only `boot`, require full readback and signature verification, and preserve ramdisk, DTB, `dtbo`, `vbmeta`, recovery, and boot chain components. The experimental cutoff for new boot writes was 2026-11-19 06:48, reserving the final hour for recovery. Writes for this experiment have ended.

This device's BSP registers `fastboot boot` as continuing normal boot; it does not establish temporary execution of a downloaded kernel. The recovery entry needs physical button assistance. The verified sequence is to disconnect USB, complete shutdown, hold Volume Down while reconnecting USB, then release the key after the host confirms genuine BROM and completes loading. Normal shutdown took approximately 95 seconds, during which the desktop could remain visible. A black screen or charging mode (`bcdDevice=2430`) alone does not prove download mode. The read-only download-mode test passed.

The private work directory is `/data/development/Gao-OS/JingPad-kernel-work/20261118T004028`, containing backup manifests, stage logs, and verification evidence. Evening follow-up and final CLI records are `reports/patched-ticket-manual-followup-20261119.json`, `reports/patched-ticket-calculator-foreground-20261119.json`, and `reports/patched-ticket-flatpak-final-cli-20261119.json`; the user's manual confirmation is stored in a separate acceptance record. The successful result is limited to the checks explicitly documented here.
