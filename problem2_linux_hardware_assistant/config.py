"""
Configuration, Command Allowlists, and Execution Limits for Hardware Assistant.
Enforces strict security constraints: read-only commands, exact argument matching,
and execution timeouts.
"""

from typing import Dict, List, Tuple

# Execution bounds
COMMAND_TIMEOUT_SECONDS = 5.0
MAX_OUTPUT_BYTES = 512 * 1024  # 512 KB maximum to prevent buffer DOS
SAFE_LOCALE = "C.UTF-8"
SAFE_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Explicit immutable allowlist of executable command tuples:
# Format: (binary_name, tuple_of_allowed_arguments)
ALLOWED_COMMAND_SCHEMAS: Dict[str, List[Tuple[str, ...]]] = {
    "lscpu": [
        ("-J",),                         # JSON output
        (),                              # Plain output fallback
    ],
    "lsblk": [
        ("-J", "-o", "NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,ROTA,TRAN,MODEL"),
        ("-J",),
        ("-d", "-o", "NAME,SIZE,TYPE,TRAN,MODEL,ROTA"),
    ],
    "free": [
        ("-b",),                         # Exact bytes
        ("-m",),                         # Megabytes fallback
    ],
    "lspci": [
        ("-mm",),                        # Machine-readable output
        ("-nnk",),                       # Detailed device with kernel drivers
    ],
    "dmidecode": [
        ("-t", "memory"),                # RAM slots and capacity
        ("-t", "processor"),             # Physical CPU sockets
        ("-t", "baseboard"),             # Motherboard specifications
        ("-t", "bios"),                  # BIOS/UEFI firmware info
    ],
    "uname": [
        ("-a",),
        ("-r",),
    ],
}

# Allowlisted readable virtual filesystem paths for non-root / fallback inspection
ALLOWED_SYSFS_PATHS = [
    "/proc/cpuinfo",
    "/proc/meminfo",
    "/proc/partitions",
    "/proc/version",
    "/sys/class/dmi/id/product_name",
    "/sys/class/dmi/id/sys_vendor",
    "/sys/class/dmi/id/board_name",
    "/sys/class/dmi/id/bios_version",
    "/sys/block",
]
