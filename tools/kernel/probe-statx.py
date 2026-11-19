#!/usr/bin/env python3
"""Probe the real ARM64 statx syscall and compare mount ID with fdinfo."""
import ctypes
import json
import os
from pathlib import Path
import struct

if os.uname().machine != "aarch64":
    raise SystemExit("This probe uses the ARM64 statx syscall number")

libc = ctypes.CDLL(None, use_errno=True)
libc.syscall.restype = ctypes.c_long
rows = []
for path in ["/", "/home/gao/.local/share/flatpak", "/proc", "/sys", "/dev", "/tmp"]:
    fd = os.open(path, os.O_PATH | os.O_CLOEXEC)
    try:
        info = Path(f"/proc/self/fdinfo/{fd}").read_text()
        expected = int(next(line.split(":", 1)[1] for line in info.splitlines() if line.startswith("mnt_id:")))
        for request in [0x17FF, 0x5101]:
            buf = ctypes.create_string_buffer(256)
            ctypes.set_errno(0)
            result = libc.syscall(
                ctypes.c_long(291), ctypes.c_int(fd), ctypes.c_char_p(b""),
                ctypes.c_int(0x1000), ctypes.c_uint(request), ctypes.byref(buf),
            )
            mask = struct.unpack_from("<I", buf.raw, 0)[0]
            mount_id = struct.unpack_from("<Q", buf.raw, 144)[0]
            rows.append({"path": path, "request": hex(request), "return": result,
                         "errno": ctypes.get_errno(), "mask": hex(mask),
                         "mount_id": mount_id, "fdinfo_mount_id": expected,
                         "mount_id_verified": result == 0 and bool(mask & 0x1000) and mount_id == expected})
    finally:
        os.close(fd)
print(json.dumps({"kernel": os.uname().release, "all_verified": all(r["mount_id_verified"] for r in rows), "probes": rows}, indent=2))
