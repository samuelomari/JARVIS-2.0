import os
from pathlib import Path
import platform
import shutil


def get_system_status():
    memory = None
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        values = {}
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition(":")
            if value.strip().endswith("kB"):
                values[key] = int(value.strip().split()[0]) * 1024
        total = values.get("MemTotal")
        available = values.get("MemAvailable")
        if total and available is not None:
            memory = {
                "total_bytes": total,
                "available_bytes": available,
                "used_percent": round((total - available) / total * 100, 1),
            }

    disk = shutil.disk_usage(Path.home())
    load_average = os.getloadavg() if hasattr(os, "getloadavg") else None
    uptime_seconds = None
    uptime_file = Path("/proc/uptime")
    if uptime_file.exists():
        uptime_seconds = int(float(uptime_file.read_text(encoding="utf-8").split()[0]))

    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
        "cpu_count": os.cpu_count(),
        "load_average": load_average,
        "memory": memory,
        "disk": {
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
            "used_percent": round(disk.used / disk.total * 100, 1) if disk.total else 0,
        },
        "uptime_seconds": uptime_seconds,
    }