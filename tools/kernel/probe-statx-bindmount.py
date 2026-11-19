#!/usr/bin/env python3
"""Check real per-mount IDs for one inode in a private mount namespace."""
import ctypes
import json
import os
from pathlib import Path
import struct
import sys
import tempfile


if os.uname().machine != "aarch64":
    raise SystemExit("This probe uses the ARM64 statx syscall number")
libc = ctypes.CDLL(None, use_errno=True)
libc.syscall.restype = ctypes.c_long
libc.mount.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
                       ctypes.c_ulong, ctypes.c_void_p]
libc.umount2.argtypes = [ctypes.c_char_p, ctypes.c_int]


def checked(result, operation):
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, f"{operation}: {os.strerror(error)}")


def probe(path):
    fd = os.open(path, os.O_PATH | os.O_CLOEXEC)
    try:
        info = Path(f"/proc/self/fdinfo/{fd}").read_text()
        expected = int(next(line.split(":", 1)[1] for line in info.splitlines()
                            if line.startswith("mnt_id:")))
        rows = []
        for request in [0x1000, 0x17FF, 0x5101]:
            for empty_path in [False, True]:
                buf = ctypes.create_string_buffer(256)
                ctypes.set_errno(0)
                result = libc.syscall(
                    ctypes.c_long(291), ctypes.c_int(fd if empty_path else -100),
                    ctypes.c_char_p(b"" if empty_path else os.fsencode(path)),
                    ctypes.c_int(0x1000 if empty_path else 0),
                    ctypes.c_uint(request), ctypes.byref(buf),
                )
                mask = struct.unpack_from("<I", buf.raw, 0)[0]
                mount_id = struct.unpack_from("<Q", buf.raw, 144)[0]
                rows.append({"request": hex(request), "empty_path": empty_path,
                             "return": result, "errno": ctypes.get_errno(),
                             "mask": hex(mask), "mount_id": mount_id,
                             "verified": result == 0 and bool(mask & 0x1000)
                                         and mount_id == expected})
        stat = os.fstat(fd)
        return {"path": str(path), "dev": stat.st_dev, "ino": stat.st_ino,
                "fdinfo_mount_id": expected, "probes": rows}
    finally:
        os.close(fd)


# Unshare before creating mounts; all mount changes are private to this process.
checked(libc.unshare(ctypes.c_int(0x00020000)), "unshare(CLONE_NEWNS)")
checked(libc.mount(None, b"/", None, (1 << 18) | (1 << 14), None),
        "make mounts recursively private")
with tempfile.TemporaryDirectory(prefix="jingpad-statx-bind-") as temporary:
    root = Path(temporary)
    source, target = root / "source", root / "target"
    source.mkdir()
    target.mkdir()
    (source / "marker").write_text("JingPad mount-ID validation\n")
    checked(libc.mount(os.fsencode(source), os.fsencode(target), None, 4096, None),
            "bind mount")
    try:
        original, bound = probe(source / "marker"), probe(target / "marker")
        same_inode = (original["dev"], original["ino"]) == (bound["dev"], bound["ino"])
        different_mounts = original["fdinfo_mount_id"] != bound["fdinfo_mount_id"]
        verified = same_inode and different_mounts and all(
            row["verified"] for item in [original, bound] for row in item["probes"])
        print(json.dumps({"kernel": os.uname().release, "private_namespace": True,
                          "same_inode": same_inode, "different_mounts": different_mounts,
                          "all_verified": verified, "paths": [original, bound]}, indent=2))
    finally:
        checked(libc.umount2(os.fsencode(target), 0), "unmount bind mount")
sys.exit(0 if verified else 1)
