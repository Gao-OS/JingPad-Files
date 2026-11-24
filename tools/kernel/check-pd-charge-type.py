#!/usr/bin/env python3
"""Check the PD charge-type patch offline using functions from kernel source."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


DRIVER = "drivers/power/supply/sc2730_fast_charger.c"
MANAGER = "drivers/power/supply/charger-manager.c"
HEADER = "include/linux/power_supply.h"
DEFAULT_PATCH = (
    Path(__file__).resolve().parents[2]
    / "patches/0004-sc2730-report-pd-fast-charge.patch"
)

# Only transport, locking, and minimal structures are mocked. GETTER and
# CONSUMER are extracted from source; ENUMS comes from the kernel header.
HARNESS = r'''
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
typedef uint32_t u32;
/* ENUMS */
enum power_supply_property { POWER_SUPPLY_PROP_CHARGE_TYPE };
union power_supply_propval { int intval; };
struct sc2730_fchg_info { u32 state; bool pd_enable; int lock; };
struct power_supply { void *driver_data; };
struct charger_desc { const char **psy_fast_charger_stat; bool is_fast_charge; };
struct charger_manager { struct charger_desc *desc; void *dev; };
static struct power_supply fixture_supply;
static void mutex_lock(int *lock) { (void)lock; }
static void mutex_unlock(int *lock) { (void)lock; }
static void *power_supply_get_drvdata(struct power_supply *psy) {
    return psy->driver_data;
}
#define dev_err(...) ((void)0)
/* GETTER */
static struct power_supply *power_supply_get_by_name(const char *name) {
    return strcmp(name, "sc2730_fast_charger") == 0 ? &fixture_supply : NULL;
}
static void power_supply_put(struct power_supply *psy) { (void)psy; }
static int power_supply_get_property(struct power_supply *psy,
        enum power_supply_property property, union power_supply_propval *value) {
    return sc2730_fchg_usb_get_property(psy, property, value);
}
/* CONSUMER */
int main(void) {
    const struct {
        const char *name; u32 state; bool pd_enabled; int expected;
    } cases[] = {
        { "unknown", POWER_SUPPLY_CHARGE_TYPE_UNKNOWN, false, POWER_SUPPLY_CHARGE_TYPE_UNKNOWN },
        { "PD_fixed", POWER_SUPPLY_USB_TYPE_PD, true, POWER_SUPPLY_CHARGE_TYPE_FAST },
        { "PD_PPS_same_internal_state", POWER_SUPPLY_USB_TYPE_PD, true, POWER_SUPPLY_CHARGE_TYPE_FAST },
        { "PD_withdrawn", POWER_SUPPLY_USB_TYPE_PD, false, POWER_SUPPLY_CHARGE_TYPE_UNKNOWN },
        { "Type_C_fallback_after_PD", POWER_SUPPLY_USB_TYPE_C, false, POWER_SUPPLY_CHARGE_TYPE_UNKNOWN },
        { "legacy_SFCP", POWER_SUPPLY_CHARGE_TYPE_FAST, false, POWER_SUPPLY_CHARGE_TYPE_FAST },
        { "none", POWER_SUPPLY_CHARGE_TYPE_NONE, false, POWER_SUPPLY_CHARGE_TYPE_NONE },
        { "trickle", POWER_SUPPLY_CHARGE_TYPE_TRICKLE, false, POWER_SUPPLY_CHARGE_TYPE_TRICKLE },
        { "PD_link_unclassified", POWER_SUPPLY_CHARGE_TYPE_UNKNOWN, true, POWER_SUPPLY_CHARGE_TYPE_UNKNOWN },
        { "invalid_state", 99, true, POWER_SUPPLY_CHARGE_TYPE_UNKNOWN },
    };
    unsigned int failures = 0;
    size_t i;
    printf("{\"failure_cases\":[");
    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        struct sc2730_fchg_info info = { cases[i].state, cases[i].pd_enabled, 0 };
        const char *names[] = { "sc2730_fast_charger", NULL };
        struct charger_desc desc = { names, false };
        struct charger_manager manager = { &desc, NULL };
        union power_supply_propval value = { -1 };
        bool expected_fast = cases[i].expected == POWER_SUPPLY_CHARGE_TYPE_FAST;
        bool recognized;
        int result;
        fixture_supply.driver_data = &info;
        result = sc2730_fchg_usb_get_property(&fixture_supply,
                                             POWER_SUPPLY_PROP_CHARGE_TYPE, &value);
        recognized = cm_charger_is_support_fchg(&manager);
        if (result != 0 || value.intval != cases[i].expected ||
            recognized != expected_fast || desc.is_fast_charge != expected_fast ||
            info.state != cases[i].state || info.pd_enable != cases[i].pd_enabled) {
            printf("%s\"%s\"", failures ? "," : "", cases[i].name);
            failures++;
        }
    }
    printf("],\"failures\":%u,\"cases\":%zu,\"pd_usb_enum\":%d,\"fast_charge_enum\":%d}\n",
           failures, sizeof(cases) / sizeof(cases[0]), POWER_SUPPLY_USB_TYPE_PD,
           POWER_SUPPLY_CHARGE_TYPE_FAST);
    return failures ? 1 : 0;
}
'''


def extract_function(source, signature):
    """Extract a function with the pinned kernel's column-zero closing brace."""
    match = re.search(r"^" + re.escape(signature) + r".*?^}", source, re.M | re.S)
    if match is None:
        raise ValueError(f"Function not found: {signature}")
    return match.group(0)


def extract_enum(header, member):
    for match in re.finditer(r"enum(?:\s+\w+)?\s*\{[^{}]*\};", header, re.S):
        if re.search(r"\b" + re.escape(member) + r"\b", match.group(0)):
            return match.group(0)
    raise ValueError(f"Enum not found: {member}")


def limit_resources():
    priority = os.getpriority(os.PRIO_PROCESS, 0)
    if priority < 10:
        os.nice(10 - priority)
    cpus = sorted(os.sched_getaffinity(0))[:2]
    os.sched_setaffinity(0, cpus)


def verify(args):
    source = args.kernel_source.resolve(strict=True)
    patch = args.patch.resolve(strict=True)
    compiler = shutil.which(args.cc)
    if compiler is None:
        raise ValueError(f"Host C compiler not found: {args.cc}")
    inputs = {name: (source / name).read_text() for name in (DRIVER, MANAGER, HEADER)}
    enums = "\n".join(
        extract_enum(inputs[HEADER], member)
        for member in ("POWER_SUPPLY_CHARGE_TYPE_UNKNOWN", "POWER_SUPPLY_USB_TYPE_PD_PPS")
    )
    consumer = extract_function(inputs[MANAGER], "static bool cm_charger_is_support_fchg(")
    harness = HARNESS.replace("/* ENUMS */", enums).replace("/* CONSUMER */", consumer)
    reports = {}
    limit_resources()
    with tempfile.TemporaryDirectory(prefix="jingpad-pd-regression-") as directory:
        temporary = Path(directory)
        driver = temporary / DRIVER
        driver.parent.mkdir(parents=True)
        driver.write_text(inputs[DRIVER])
        # Apply the actual repository patch only to a temporary source copy.
        for options in (["--check"], []):
            subprocess.run(
                ["git", "apply", *options, "--", str(patch)], cwd=temporary,
                check=True, capture_output=True, text=True, timeout=5,
            )
        for label, text in (("original", inputs[DRIVER]), ("patched", driver.read_text())):
            getter = extract_function(text, "static int sc2730_fchg_usb_get_property(")
            c_file = temporary / f"{label}.c"
            binary = temporary / label
            c_file.write_text(harness.replace("/* GETTER */", getter))
            subprocess.run(
                [compiler, "-std=c99", "-O2", "-Wall", "-Wextra", "-Werror",
                 str(c_file), "-o", str(binary)],
                check=True, capture_output=True, text=True, timeout=25,
            )
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=5)
            reports[label] = {"returncode": result.returncode, **json.loads(result.stdout)}

    original = reports["original"]
    patched = reports["patched"]
    expected_failures = ["PD_fixed", "PD_PPS_same_internal_state"]
    verified = (
        original["returncode"] == 1
        and original["failure_cases"] == expected_failures
        and original["failures"] == 2
        and original["cases"] == 10
        and patched["returncode"] == 0
        and patched["failure_cases"] == []
        and patched["failures"] == 0
        and patched["cases"] == 10
    )
    return {
        "all_verified": verified,
        "scope": "Actual getter and charger-manager consumer with mocked transport and locking",
        "patch": str(patch),
        "patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
        "source_sha256": {
            name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in inputs
        },
        "reports": reports,
        "hardware_negotiation_tested": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel-source", type=Path, required=True, help="Pristine pinned kernel source")
    parser.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    parser.add_argument("--cc", default="cc", help="Host C compiler executable (default: cc)")
    args = parser.parse_args()
    try:
        report = verify(args)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        detail = error.stderr if isinstance(error, subprocess.CalledProcessError) else str(error)
        report = {"all_verified": False, "error": detail}
    print(json.dumps(report, indent=2))
    return 0 if report["all_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
