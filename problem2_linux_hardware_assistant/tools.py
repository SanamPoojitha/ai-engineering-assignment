"""
Safe System Inspection Tool Runner and Tool-Calling Registry.
Executes allowlisted system inspection commands with strict process isolation,
safe fallback chains, and cross-platform mock capability.
"""

import json
import os
import platform
import subprocess
from typing import Any, Callable, Dict, List, Optional, Tuple
from .config import COMMAND_TIMEOUT_SECONDS, MAX_OUTPUT_BYTES
from .hardware_store import (
    CPUInfo,
    GPUDevice,
    MemoryTopology,
    MemoryUsage,
    StorageTopology,
    bytes_to_human,
)
from .parsers import HardwareParsers
from .security import CommandSecurityValidator, PrivilegeManager, SecurityViolationError

# Output type alias for (exit_code, stdout, stderr)
Tuple_Output = Tuple[int, str, str]


class SystemInspectionBackend:
    """Abstract interface for command execution."""
    def run_command(self, binary: str, args: List[str]) -> Tuple_Output: ...
    def read_sysfs(self, path: str) -> str: ...


class NativeLinuxBackend:
    """Executes live commands on a Linux machine with security validation."""

    def run_command(self, binary: str, args: List[str]) -> Tuple_Output:
        # Validate binary and arguments against strict allowlist
        resolved_bin, safe_args = CommandSecurityValidator.validate_command(binary, args)
        env = CommandSecurityValidator.get_sanitized_environment()

        cmd = [resolved_bin] + safe_args

        # Handle root requirement for dmidecode
        if os.path.basename(resolved_bin) == "dmidecode" and not PrivilegeManager.is_root():
            if PrivilegeManager.can_run_sudo_non_interactive(resolved_bin):
                cmd = ["sudo", "-n"] + cmd
            else:
                return (
                    1,
                    "",
                    "Permission denied: dmidecode requires root privileges to read DMI tables. "
                    "Run with sudo or add a NOPASSWD sudoers rule."
                )

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT_SECONDS,
                shell=False,  # CRITICAL: zero shell execution
                env=env,
            )
            stdout = proc.stdout[:MAX_OUTPUT_BYTES]
            stderr = proc.stderr[:MAX_OUTPUT_BYTES]
            return proc.returncode, stdout, stderr
        except subprocess.TimeoutExpired:
            return 124, "", f"Command timed out after {COMMAND_TIMEOUT_SECONDS}s"
        except FileNotFoundError:
            return 127, "", f"Tool '{binary}' not installed on this system"
        except Exception as e:
            return 1, "", str(e)

    def read_sysfs(self, path: str) -> str:
        safe_path = CommandSecurityValidator.validate_sysfs_read(path)
        try:
            with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(MAX_OUTPUT_BYTES)
        except Exception as e:
            return f"Error reading {safe_path}: {e}"


class MockLinuxBackend:
    """
    Simulated Linux laptop backend matching realistic ThinkPad / Dell XPS hardware specs.
    Enables cross-platform testing (Windows, macOS, CI) and reproduces the interview example:
    - 16 GB RAM in 1 of 2 slots (upgradable to 64 GB, up to 32 GB per stick).
    - 1TB NVMe SSD.
    - Intel Core i7-12700H CPU.
    - Intel Iris Xe + NVIDIA RTX 3060 Discrete GPU.
    """

    MOCK_DMIDECODE_MEMORY = """
# dmidecode 3.4
Getting SMBIOS data from sysfs.
SMBIOS 3.3.0 present.

Handle 0x0010, DMI type 16, 23 bytes
Physical Memory Array
\tLocation: System Board
\tUse: System Memory
\tError Correction Type: None
\tMaximum Capacity: 64 GB
\tError Information Handle: Not Provided
\tNumber Of Devices: 2

Handle 0x0011, DMI type 17, 92 bytes
Memory Device
\tArray Handle: 0x0010
\tError Information Handle: Not Provided
\tTotal Width: 64 bits
\tData Width: 64 bits
\tSize: 16 GB
\tForm Factor: SODIMM
\tSet: None
\tLocator: ChannelA-DIMM0
\tBank Locator: BANK 0
\tType: DDR4
\tType Detail: Synchronous Unbuffered (Unregistered)
\tSpeed: 3200 MT/s
\tManufacturer: Samsung
\tSerial Number: 42A9B801
\tPart Number: M471A2K43DB1-CWE

Handle 0x0012, DMI type 17, 92 bytes
Memory Device
\tArray Handle: 0x0010
\tError Information Handle: Not Provided
\tTotal Width: Unknown
\tData Width: Unknown
\tSize: No Module Installed
\tForm Factor: SODIMM
\tSet: None
\tLocator: ChannelB-DIMM0
\tBank Locator: BANK 1
\tType: Unknown
\tType Detail: None
\tSpeed: Unknown
\tManufacturer: Not Specified
"""

    MOCK_FREE = """
               total        used        free      shared  buff/cache   available
Mem:     16719872000  4294967296  8589934592   536870912  3834970112 11848033792
Swap:     4294967296           0  4294967296
"""

    MOCK_LSCPU_JSON = json.dumps({
        "lscpu": [
            {"field": "Architecture:", "data": "x86_64"},
            {"field": "CPU op-mode(s):", "data": "32-bit, 64-bit"},
            {"field": "CPU(s):", "data": "14"},
            {"field": "On-line CPU(s) list:", "data": "0-13"},
            {"field": "Model name:", "data": "12th Gen Intel(R) Core(TM) i7-12700H"},
            {"field": "Socket(s):", "data": "1"},
            {"field": "Core(s) per socket:", "data": "14"},
            {"field": "CPU max MHz:", "data": "4700.0000"},
            {"field": "CPU min MHz:", "data": "400.0000"},
        ]
    })

    MOCK_LSBLK_JSON = json.dumps({
        "blockdevices": [
            {
                "name": "nvme0n1",
                "size": "1000204886016",
                "type": "disk",
                "fstype": None,
                "mountpoint": None,
                "rota": False,
                "tran": "nvme",
                "model": "Samsung SSD 980 PRO 1TB"
            },
            {
                "name": "nvme0n1p1",
                "size": "536870912",
                "type": "part",
                "fstype": "vfat",
                "mountpoint": "/boot/efi",
                "rota": False,
                "tran": "nvme",
                "model": None
            },
            {
                "name": "nvme0n1p2",
                "size": "999668015104",
                "type": "part",
                "fstype": "ext4",
                "mountpoint": "/",
                "rota": False,
                "tran": "nvme",
                "model": None
            }
        ]
    })

    MOCK_LSPCI = """
00:02.0 VGA compatible controller: Intel Corporation Alder Lake-P Integrated Graphics Controller (rev 0c)
01:00.0 3D controller: NVIDIA Corporation GA106M [GeForce RTX 3060 Mobile / Max-Q] (rev a1)
"""

    def run_command(self, binary: str, args: List[str]) -> Tuple_Output:
        CommandSecurityValidator.validate_command(binary, args)
        base = os.path.basename(binary)

        if base == "free":
            return 0, self.MOCK_FREE, ""
        elif base == "dmidecode":
            return 0, self.MOCK_DMIDECODE_MEMORY, ""
        elif base == "lscpu":
            return 0, self.MOCK_LSCPU_JSON, ""
        elif base == "lsblk":
            return 0, self.MOCK_LSBLK_JSON, ""
        elif base == "lspci":
            return 0, self.MOCK_LSPCI, ""

        return 1, "", f"Mock command {base} not found"

    def read_sysfs(self, path: str) -> str:
        CommandSecurityValidator.validate_sysfs_read(path)
        if "product_name" in path:
            return "ThinkPad T14 Gen 3"
        elif "sys_vendor" in path:
            return "LENOVO"
        return "Unknown"


class HardwareToolRegistry:
    """
    The tool registry exposes normalized, callable functions for LLM tool-calling.
    """

    def __init__(self, backend: Optional[Any] = None):
        if backend is not None:
            self.backend = backend
        elif platform.system() == "Linux":
            self.backend = NativeLinuxBackend()
        else:
            # Default to MockLinuxBackend on Windows/macOS/CI
            self.backend = MockLinuxBackend()

        # Invariant hardware cache: avoids running expensive commands repeatedly
        self._cache: Dict[str, Any] = {}

    def get_tool_definitions(self) -> List[dict]:
        """Returns JSON schema function calling specifications for LLMs."""
        return [
            {
                "name": "inspect_memory",
                "description": (
                    "Inspects installed RAM capacity, free/used memory, physical RAM slot topology, "
                    "slots in use vs empty, maximum motherboard capacity, and upgradeability."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "include_slots": {
                            "type": "boolean",
                            "description": "Whether to check physical DMI slots and maximum supported RAM.",
                            "default": True,
                        }
                    },
                },
            },
            {
                "name": "inspect_storage",
                "description": (
                    "Inspects disk drives, total storage space, drive types (NVMe vs SATA SSD vs HDD), "
                    "partition layouts, and mountpoints."
                ),
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "inspect_cpu",
                "description": (
                    "Inspects the processor architecture, model name, physical cores, logical threads, "
                    "sockets, and clock speed."
                ),
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "inspect_gpu",
                "description": (
                    "Inspects graphics cards, display controllers, GPU vendors (Intel/AMD/NVIDIA), "
                    "and distinguishes integrated vs discrete graphics."
                ),
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "inspect_motherboard",
                "description": "Inspects system manufacturer, model/product name, and BIOS version.",
                "parameters": {"type": "object", "properties": {}},
            },
        ]

    def inspect_memory(self, include_slots: bool = True) -> dict:
        """Executes `free -b` and `dmidecode -t memory`, returning structured JSON."""
        # 1. Volatile memory usage from `free -b`
        ret, stdout, stderr = self.backend.run_command("free", ["-b"])
        mem_usage = HardwareParsers.parse_free(stdout) if ret == 0 else MemoryUsage()

        # 2. Invariant physical slot topology from `dmidecode -t memory`
        if include_slots:
            if "dmidecode_memory" not in self._cache:
                ret_dmi, out_dmi, err_dmi = self.backend.run_command("dmidecode", ["-t", "memory"])
                topo = HardwareParsers.parse_dmidecode_memory(out_dmi if ret_dmi == 0 else "")
                self._cache["dmidecode_memory"] = topo
            topo = self._cache["dmidecode_memory"]
        else:
            topo = MemoryTopology()

        # Ensure installed_bytes is populated from free if DMI is restricted
        if topo.installed_bytes == 0 and mem_usage.total_bytes > 0:
            topo.installed_bytes = mem_usage.total_bytes

        result = {
            "usage": mem_usage.to_compact_dict(),
            "topology": topo.to_compact_dict(),
            "upgrade_guidance": self._calculate_ram_upgrade_guidance(topo),
        }
        return result

    def _calculate_ram_upgrade_guidance(self, topo: MemoryTopology) -> dict:
        """Computes deterministic, mathematically grounded RAM upgrade possibilities."""
        if topo.is_root_restricted:
            return {
                "upgradeable": "Unknown",
                "reason": "Root privileges required to inspect physical RAM slots and motherboard limits.",
            }

        if topo.total_slots == 0 or topo.max_capacity_bytes == 0:
            return {
                "upgradeable": "Unknown",
                "reason": "Motherboard firmware did not report slot count or maximum capacity.",
            }

        max_gb = topo.max_capacity_bytes // (1024**3)
        installed_gb = topo.installed_bytes // (1024**3)
        empty = topo.empty_slots
        max_per_slot_gb = (topo.max_per_slot_bytes // (1024**3)) if topo.max_per_slot_bytes else (max_gb // topo.total_slots)

        can_add = empty > 0 and installed_gb < max_gb
        remaining_gb = max_gb - installed_gb

        return {
            "can_add_ram": can_add,
            "installed_gb": installed_gb,
            "max_supported_gb": max_gb,
            "empty_slots": empty,
            "total_slots": topo.total_slots,
            "used_slots": topo.used_slots,
            "max_per_slot_gb": max_per_slot_gb,
            "max_addable_per_empty_slot_gb": min(max_per_slot_gb, remaining_gb) if empty > 0 else 0,
            "explanation": (
                f"You have {installed_gb} GB in {topo.used_slots} of {topo.total_slots} slots. "
                f"The board supports up to {max_gb} GB, so you can add a stick of up to {min(max_per_slot_gb, remaining_gb)} GB."
                if can_add else
                f"All {topo.total_slots} slots are populated with {installed_gb} GB. To upgrade, existing sticks must be replaced."
                if installed_gb < max_gb else
                f"System is already at maximum capacity ({max_gb} GB)."
            ),
        }

    def inspect_storage(self) -> dict:
        """Executes `lsblk -J`, returning normalized storage topology."""
        if "storage" not in self._cache:
            ret, stdout, stderr = self.backend.run_command(
                "lsblk",
                ["-J", "-o", "NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,ROTA,TRAN,MODEL"]
            )
            if ret != 0:
                ret, stdout, stderr = self.backend.run_command("lsblk", ["-J"])

            topo = HardwareParsers.parse_lsblk(stdout) if ret == 0 else StorageTopology()
            self._cache["storage"] = topo

        topo = self._cache["storage"]
        return topo.to_compact_dict()

    def inspect_cpu(self) -> dict:
        """Executes `lscpu -J`, returning normalized CPU info."""
        if "cpu" not in self._cache:
            ret, stdout, stderr = self.backend.run_command("lscpu", ["-J"])
            if ret != 0:
                ret, stdout, stderr = self.backend.run_command("lscpu", [])

            info = HardwareParsers.parse_lscpu(stdout) if ret == 0 else CPUInfo()
            self._cache["cpu"] = info

        info = self._cache["cpu"]
        return info.to_compact_dict()

    def inspect_gpu(self) -> dict:
        """Executes `lspci -mm` or `lspci`, returning graphics controllers."""
        if "gpu" not in self._cache:
            ret, stdout, stderr = self.backend.run_command("lspci", ["-mm"])
            if ret != 0:
                ret, stdout, stderr = self.backend.run_command("lspci", ["-nnk"])

            gpus = HardwareParsers.parse_lspci(stdout) if ret == 0 else []
            self._cache["gpu"] = gpus

        gpus = self._cache["gpu"]
        return {
            "gpu_count": len(gpus),
            "devices": [g.to_compact_dict() for g in gpus],
            "has_discrete_gpu": any(g.is_discrete for g in gpus),
        }

    def inspect_motherboard(self) -> dict:
        """Reads DMI system identity from sysfs."""
        vendor = self.backend.read_sysfs("/sys/class/dmi/id/sys_vendor").strip()
        product = self.backend.read_sysfs("/sys/class/dmi/id/product_name").strip()
        return {
            "vendor": vendor or "Unknown",
            "product_name": product or "Unknown Laptop",
        }

    def execute_tool_by_name(self, tool_name: str, arguments: Optional[dict] = None) -> dict:
        """Dispatches tool call by name."""
        arguments = arguments or {}
        dispatch_table: Dict[str, Callable[..., dict]] = {
            "inspect_memory": self.inspect_memory,
            "inspect_storage": self.inspect_storage,
            "inspect_cpu": self.inspect_cpu,
            "inspect_gpu": self.inspect_gpu,
            "inspect_motherboard": self.inspect_motherboard,
        }

        if tool_name not in dispatch_table:
            return {"error": f"Unknown tool '{tool_name}'"}

        func = dispatch_table[tool_name]
        return func(**arguments)
