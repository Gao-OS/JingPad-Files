# USB-C PD Charging Investigation

[Home](../README.md) · [Device status](device-status.md) · [Kernel build and recovery](kernel-backport-2026-11-18.md)

Status, **2026-11-24**: a PD charge-type reporting bug was reproduced in the published driver and matched live device logs. A minimal [candidate patch](../patches/0004-sc2730-report-pd-fast-charge.patch) passed offline regression checks and ARM64 driver compilation. **The patch has not been installed, and 9V charging has not been demonstrated.** Device access in this investigation was read-only.

## Observed charging behavior

The user connected a 100W USB-C charger using a C-to-C cable. TCPM received these source capabilities:

| Profile | Advertised capability |
| --- | --- |
| Fixed | 5V/3A, 9V/3A, 12V/3A, 15V/3A, 20V/5A |
| PPS | 3.3–11V/5A and 3.3–20V/5A |

The tablet explicitly requested `PDO 0: 5000 mV, 2000 mA`; negotiation completed and reached `SNK_READY`. TCPM reported `online=1`, `voltage_now=5000000`, and `current_now=2000000`. These TCPM values describe the negotiated supply contract: **10W is the nominal contract budget, not measured wall power or battery charging power**.

Despite the available higher-voltage profiles, the tablet reported:

```text
sc2730_fast_charger/charge_type: Unknown
sc2730-fast-charger: pd type = 8
sc2730-fast-charger: pd_enable = 1, sfcp_enable = 0
charger-manager: is_fast_charge = 0, enable_fast_charge = 0
```

`8` is `POWER_SUPPLY_USB_TYPE_PD_PPS`. In this TCPM implementation, `[PD_PPS]` indicates partner PPS capability; it does not prove that an adjustable PPS contract is active. The actual request and completed contract were fixed 5V/2A.

One charger-manager sample showed battery voltage 4.013V and battery current +1.277A, approximately **5.1W net into the battery** at that instant. A separate computer-USB sample showed an SDP input limit of 0.5A and battery current −0.342A at 3.778V, approximately **1.29W net discharge**. The aggregate battery status still said `Charging`. These samples were taken at different times and do not establish a constant device power consumption; a USB power meter is needed for actual input power.

A later screen-on check at 04:35 UTC took three samples over six seconds. All showed positive battery current, approximately **4.2–5.0W net charging**, with battery capacity 38% and temperature 31.5°C. The 5V/2A contract covered the observed screen-on load and left charging headroom; sustained heavy workloads were not tested.

The computer-USB sample establishes the tablet's selected SDP mode and 0.5A limit, not the computer port's maximum output. Even a port capable of 10W needs compatible charging detection before the tablet can draw that power. The computer is a Maxsun MS-Terminator B760ITX D4 V2; its [official specification table](https://www.maxsun.com.cn/2024/0910/6266.html) lists front and rear USB-C data rates without stating per-port charging wattage. The physical port and cable used in that sample remain unconfirmed. Do not attribute its limit to the PD reporting bug without further evidence.

## Existing managed 9V path

Source: [`JingOS-team/kernel4.14@84a635cee601934f5eee09da5ab8e1e2be269a26`](https://github.com/JingOS-team/kernel4.14/tree/84a635cee601934f5eee09da5ab8e1e2be269a26).

The live device tree starts with a 5V/2A sink PDO and `op-sink-microwatt=10000000`. This is a conservative initial profile, **not an absolute system ceiling**. `op-sink-microwatt` expresses operating-power metadata, rather than independently enforcing a maximum.

The [SC2730 fast-charger driver](https://github.com/JingOS-team/kernel4.14/blob/84a635cee601934f5eee09da5ab8e1e2be269a26/drivers/power/supply/sc2730_fast_charger.c#L410) already defines a `sc2730_snk9v_pdo` table containing 5V/2A and 9V/2A. `sc2730_fchg_pd_adjust_voltage()` can install that table with `tcpm_update_sink_capabilities()` and an 18W operating-power request. Charger manager prepares the main and secondary chargers before requesting 9V and retains its battery, temperature, and protection checks.

Relevant built-in options were verified: `CONFIG_TYPEC_TCPM`, `CONFIG_FAST_CHARGER_SC2730`, `CONFIG_CHARGER_SC2703`, `CONFIG_CHARGER_ETA6937`, and `CONFIG_CHARGER_MANAGER` are all `y`. This fix therefore requires rebuilding the kernel; loading a replacement module is insufficient.

## Charge-type mismatch and candidate fix

`sc2730_fchg_pd_change_work()` recognizes both PD and PD-PPS and stores:

```c
info->pd_enable = true;
info->state = POWER_SUPPLY_USB_TYPE_PD; /* 6 */
```

The `CHARGE_TYPE` getter copies that state, then rejects values above `POWER_SUPPLY_CHARGE_TYPE_FAST` (`3`). The resulting `UNKNOWN` (`0`) prevents `cm_charger_is_support_fchg()` from recognizing the PD source, even though that consumer accepts either FAST or the raw PD value. Live `pd_enable=1` alongside `charge_type=Unknown` matches this failure.

Patch `0004` translates the active internal PD state to the public `POWER_SUPPLY_CHARGE_TYPE_FAST` value before range validation. It preserves internal state, PDOs, current limits, temperature policy, and protection thresholds. Changing the internal assignment directly to FAST would interfere with the existing Type-C fallback branch, which distinguishes PD from legacy SFCP FAST state.

This fixes one confirmed software gate. It does not establish that every other prerequisite for 9V charging is satisfied on this tablet.

## Offline verification and reproduction

The [regression helper](../tools/kernel/check-pd-charge-type.py) needs Python 3, Git, a host C compiler, and a Linux host. Point it at the pristine pinned source above:

```bash
JINGPAD_KERNEL_SOURCE='/path/to/pristine/kernel4.14'
python3 tools/kernel/check-pd-charge-type.py \
  --kernel-source "$JINGPAD_KERNEL_SOURCE"
```

It applies the actual repository patch to a temporary driver copy, extracts the real getter and charger-manager consumer, and compiles them with enums from `include/linux/power_supply.h`. Transport and locking are mocked. The source checkout remains unchanged; no tablet connection or root access is required. Execution is limited to two CPUs with nice level at least 10.

Inspect `all_verified: true` and the process exit status. The original must fail only the two PD fixture labels; the patched version must pass all ten fixtures. Fixed PD and PD-PPS deliberately share the same internal-state fixture because the notifier maps both to raw PD. Other fixtures cover withdrawn PD, ordinary Type-C, legacy SFCP, unknown, none, trickle, unclassified PD, and invalid state. Getter calls must also preserve internal state. These are property/consumer checks, not a simulation of PD negotiation, notifier races, or hardware fallback.

The complete original and patched driver also compiled to AArch64 objects on T430 using the previous kernel build's recorded command, configuration, headers, and original toolchain. Compilation was restricted to two CPUs with nice 10. Original source, configuration, and existing build object were unchanged. No full kernel link, boot image, full symbol-CRC comparison, or device boot test was performed. The objects have no global defined symbols; their matching global-symbol sets are not a full ABI validation.

Public patch and source references are in this repository. Raw logs, test outputs, generated objects, and the source subset remain outside Git under `/data/development/Gao-OS/JingPad-charge-work/20261124T035257Z-d7542qkv`. The ARM64 build record is under `/home/gao/jingpad-kernel-work/20261118T004028/charging-object-o4a_dda5/` on T430.

## Remaining device validation

The existing driver path targets **9V/2A, nominally 18W**. A 100W source rating does not imply that this tablet can accept 100W. No 12V, 15V, 20V, or forced PPS experiment is justified by these results.

Before an authorized installation, preserve the accepted statx/proc/Ticket fixes and original configuration, complete a full kernel build and symbol-CRC checks, and verify current boot backups, signing, and the recovery path described in the [backport log](kernel-backport-2026-11-18.md). Keep build limits at two CPUs and nice 10 for this investigation.

SC2703's fast-charge path checks the IC revision at register `0x42` against `0x80`; the actual revision has not been verified. Normal/fast input protection thresholds are 6.5V/10.5V in the live manager configuration and 6.5V/11V in the SC2703 driver. Do not bypass those gates or force voltage through sysfs or raw bus writes.

After a separately authorized kernel installation, verify the actual PD request and completed contract, charger-manager state, battery current and temperature, stable charging, and return to 5V after charger changes. Retest desktop, touch, audio, Wi-Fi, and the existing Flatpak probes. Report 9V success only after observing the completed contract and stable hardware behavior.
