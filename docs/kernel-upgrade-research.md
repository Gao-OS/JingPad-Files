# JingPad C1 Kernel Source and Upgrade Feasibility

[Home](../README.md) · [Device status](device-status.md) · [Flatpak tests](flatpak-test-2026-11-13.md)

Research date: **2026-11-16**. Finding: **Official 4.14 source is available, and community 5.15.178 source with UD710 / 3h10u support was found. The latter has not been shown to boot on this JingPad C1 with complete hardware support.**

The recommendation at the time was to rebuild the original 4.14 kernel first, then investigate a `STATX_MNT_ID` backport for the Flatpak error. A full migration to 5.15 is a separate effort requiring driver adaptation and device tests.

Implementation of the 4.14 backport began under user authorization on 2026-11-18. See the [execution log](kernel-backport-2026-11-18.md) for the process and latest results. The remaining sections preserve the original research findings and unverified boundaries.

Device update, 2026-11-19: the mount ID backport passed 24 real syscall checks. Proc namespace behavior and the Ticket netlink interface required by desktop libhybris, both missing from the published source, were restored. The combined kernel booted; factory module, sandbox, and positive/negative protocol checks passed, and KWin/PowerVR and audio services respond normally. Flatpak Calculator returned `4` for `2+2`; the user confirmed Calculator GUI, touch, and speakers. Backport acceptance is complete. References below to work not yet performed describe the research state on 2026-11-16; use the [execution log](kernel-backport-2026-11-18.md) for the current result.

## Device baseline

Read-only ADB checks during the research established:

```text
Device: JingPad C1, JingOS v1.2.0 / Ubuntu 20.04 focal, aarch64
uname: 4.14.133-202201191758+, #24-JingOS, 2022-01-19
Compiler: Android clang 9.0.3 (r353983c)
device-tree model: Spreadtrum UD710 3h10u Board
device-tree compatible: sprd,ud710_3h10u / sprd,ud710
```

`/proc/config.gz` was readable and included `CONFIG_ARCH_SPRD=y`, `CONFIG_SPRD_ROC1_CLK=y`, `CONFIG_DRM_SPRD=y`, and `CONFIG_MODVERSIONS=y`. The desktop used libhybris/hwcomposer, with vendor modules including `pvrsrvkm`, `sprdwl_ng`, `sprdbt_tty`, `gt738x_ts`, and `elan_ts_i2c` loaded.

A generic Ubuntu ARM64 kernel package therefore cannot be treated as a working upgrade for this device. In particular, `CONFIG_MODVERSIONS=y` requires checking module symbol versions and actual interfaces; existing `.ko` files cannot be assumed reusable with a new kernel.

## Located source repositories

Versions below were read from the actual `Makefile`, not inferred from repository names or update dates.

| Source | Confirmed content | Use |
| --- | --- | --- |
| [JingOS-team/kernel4.14](https://github.com/JingOS-team/kernel4.14) | `master` is 4.14.133, includes `ud710-3h10u.dts`, with model/compatible matching this device | Preferred starting point for rebuilding the original kernel and backporting features |
| [deadman96385/jingpad_android_bsp](https://github.com/deadman96385/jingpad_android_bsp/tree/W20.13.3) | `W20.13.3` includes 4.14, 3h10u product configuration, toolchains, and external module directories | Original drivers, build parameters, and packaging references; not a verified complete JingOS firmware build environment |
| [lineageos-on-jingpad/android_kernel_jingpad_ud710](https://github.com/lineageos-on-jingpad/android_kernel_jingpad_ud710) | `main` is 4.14.193; UAPI does not define `STATX_MNT_ID` | Community modifications; replacing the kernel with it does not establish a solution for missing mount IDs |
| [SpecSierra/jingpad-a1-kernel-sailfish](https://github.com/SpecSierra/jingpad-a1-kernel-sailfish) | `main` is 4.14.133; UAPI does not define `STATX_MNT_ID` | Reference for another A1 Linux port, not a verified C1 kernel upgrade |
| [Evarentha/android_kernel_iflytek_istudy_c10_5.15](https://github.com/Evarentha/android_kernel_iflytek_istudy_c10_5.15) | `main` is 5.15.178, with UD710 / ROC1 support, a same-named 3h10u device tree, and PowerVR port code | Same-platform port candidate worth evaluating |

Commits checked during the research:

```text
JingOS-team/kernel4.14                         84a635cee601934f5eee09da5ab8e1e2be269a26
deadman96385/jingpad_android_bsp                e2ae454a203619b297a8711633516ee729811526
lineageos-on-jingpad/android_kernel_jingpad_ud710
                                              9e15ff0c8772d460d39d1b8afda3609606243ab5
SpecSierra/jingpad-a1-kernel-sailfish            35bed45e0ded52e0a04d6aec95ddcb9f6021f9b1
Evarentha/android_kernel_iflytek_istudy_c10_5.15 b4c9a5bd98238f180e96f4e938e999791f838026
Evarentha/android_vendor_iflytek_istudy_c10      61dda4f57bd85d0f135d9848bde3828d982448be
```

The last public official 4.14 commit was from November 2021, preceding the January 2022 kernel build on this device. A matching version does not establish reproduction of the installed binary. The product defconfig reply in [official issue #1](https://github.com/JingOS-team/kernel4.14/issues/1) was a guess by someone without the device, not authoritative build instructions. Preserve the complete device configuration and compare it with the BSP's product and difference configurations.

The old BSP contains `modules/gpu/rogue/driver`, not just Mali drivers. The 3h10u `modules.cfg` lists `pvrsrvkm.ko`, `sprdwl_ng.ko`, `gt738x_ts.ko`, and `elan_ts_i2c.ko`. These source directories still need comparison with the installed module versions and required binary dependencies.

## Evidence and gaps for the 5.15 candidate

The following actual source files were inspected:

- [3h10u device tree](https://github.com/Evarentha/android_kernel_iflytek_istudy_c10_5.15/blob/b4c9a5bd98238f180e96f4e938e999791f838026/arch/arm64/boot/dts/sprd/ud710-3h10u.dts): same model/compatible names and a reference to `lcd_rm69380_lattice_fpga_mipi.dtsi`. A matching reference-board name still requires a component-by-component comparison with C1 hardware.
- [ROC1 configuration](https://github.com/Evarentha/android_kernel_iflytek_istudy_c10_5.15/blob/b4c9a5bd98238f180e96f4e938e999791f838026/arch/arm64/configs/sprd_roc1_defconfig): ROC1 clocks, Goodix GT738X, SPRD DPU/DSI, audio, and ION settings.
- [iFlytek C10 configuration](https://github.com/Evarentha/android_kernel_iflytek_istudy_c10_5.15/blob/b4c9a5bd98238f180e96f4e938e999791f838026/arch/arm64/configs/iflytek_istudy-c10_defconfig) enables `CONFIG_MITOCHODRIA_ROC1_PVR=y`. The [driver Kconfig](https://github.com/Evarentha/android_kernel_iflytek_istudy_c10_5.15/blob/b4c9a5bd98238f180e96f4e938e999791f838026/drivers/gpu/rogue/Kconfig) states that it uses JingPad/C8Pro BSP PowerVR `1.11@5516664` and the original userspace bridge protocol. This is a source claim, not validation against this tablet's graphics stack.

Unresolved issues:

1. **Different target hardware.** The repository targets an iFlytek tablet. No JingPad C1 boot or functional test record was found, and no Releases or Actions build records were available for verification at the time.
2. **Incomplete driver and build inputs.** Generic `build.config/build.config.gki.aarch64.ud710_userdebug` uses `sprd_roc1_defconfig` and references external `../modules/kernel5.15/...` and `../modules/common/...` directories. Do not mix it with the iFlytek custom configuration or assume cloning the kernel alone provides every module.
3. **Vendor files are not a drop-in match.** The [vendor source and instructions](https://github.com/Evarentha/android_vendor_iflytek_istudy_c10/tree/61dda4f57bd85d0f135d9848bde3828d982448be) cover camera/NPU/Wi-Fi ports and graphics userspace material, but Wi-Fi uses Broadcom `dhd`, while this tablet uses `sprdwl_ng`. Its README also requires matching factory extraction, Android BSP, toolchains, and kernel output; PowerVR userspace libraries and some firmware remain prebuilt.
4. **JingOS userspace is unverified.** GPU kernel source does not establish compatibility between 5.15 and existing EGL/GLES, ION, hwcomposer, libhybris, suspend, or audio. Touch/stylus, Wi-Fi/Bluetooth, charging, and storage driver coverage also need checks.
5. **Boot packaging is unverified.** Check this device's boot, DTB/DTBO, ramdisk, module deployment, and verification mechanism. Retain a recoverable original image before boot tests.

The [postmarketOS JingPad A1 page](https://wiki.postmarketos.org/wiki/JingPad_A1_(jingpad-a1)) still listed the original 4.14 kernel, `packaged=no`, and `booting=no` when read. It does not establish a completed newer-kernel port. No complete UD710/ROC1 board support was found in upstream Linux SPRD device tree and clock directories. Support for other Unisoc platforms does not establish mainline support for this device.

## Address Flatpak first: investigate a mount ID backport

The known launch blocker was `statx` not returning `STATX_MNT_ID`; see the [test log](flatpak-test-2026-11-13.md). Mainline Linux introduced the interface in 5.8. **Obtaining it does not require upgrading the whole kernel to 5.8 or later.**

The upstream commit [statx: add mount ID](https://github.com/torvalds/linux/commit/fa2fcf4f1df1559a0a4ee0f46915b496cc2ebf60) changes three files:

| File | Purpose |
| --- | --- |
| `fs/stat.c` | Read the actual mount object's ID, set the returned mask, and copy it to userspace |
| `include/linux/stat.h` | Store the mount ID in the kernel `kstat` |
| `include/uapi/linux/stat.h` | Add the field in reserved `statx` space and define `STATX_MNT_ID` |

Official 4.14 source has `vfs_statx()` and `cp_statx()`, `fs/mount.h` contains `mount.mnt_id` and `real_mount()`, and UAPI has reserved space. This provides a concrete backport basis. At the time of the research, no patch had been written or tested; a small upstream diff did not establish a flashable device kernel.

This route retains the vendor driver foundation and changes less than a cross-version migration. Kernel structure changes, module symbol CRCs, builds, and boot packaging still require work. It implements the real interface instead of removing Flatpak's path safety checks. Sandbox, graphics, and portal behavior need follow-up even after this error is resolved. Backporting one feature also does not restore full security maintenance to an old kernel.

## Proposed validation order at the time of research

These steps had not been executed on 2026-11-16:

1. **Establish a recoverable baseline.** Save the configuration, original boot/DTB/DTBO, modules, command line, and firmware information; verify that recovery materials apply to this device.
2. **Rebuild original 4.14 first.** Pin source, toolchain, and configuration; cross-compile on the maintenance computer and check required modules and packaging. Identify source gaps before considering a 5.15 migration.
3. **Test the rebuilt baseline.** With recovery available, check boot, display, touch, sound, Wi-Fi, charging, and suspend. Add the interface backport afterward to isolate failures.
4. **Backport and test `STATX_MNT_ID`.** Check syscall masks and field values against actual mount objects, then run Calculator as the desktop user and validate its GUI, sandbox, and integrations.
5. **Treat any 5.15 port as a separate acceptance effort.** Complete C1 device tree, driver, and module builds, then test boot, storage, input, network, sound, power management, and graphics. Version numbers or successful compilation alone are insufficient.

The research phase completed read-only device checks, public source and build material inspection, and this report. **It did not compile a kernel, produce a flashable image, change device configuration, reboot, or flash the device.** Later implementation and acceptance are documented in the linked execution log.
