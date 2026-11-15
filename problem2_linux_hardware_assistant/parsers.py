"""
Structured Parsers and Normalizers for Linux System Commands.
Converts raw JSON or tabular output from lscpu, lsblk, free, lspci, dmidecode,
and /proc into normalized dataclasses.
"""

import json
import re
from typing import Any, Dict, List, Optional
from .hardware_store import (
    CPUInfo,
    GPUDevice,
    MemorySlot,
    MemoryTopology,
    MemoryUsage,
    StorageDevice,
    StorageTopology,
)


def parse_size_to_bytes(size_str: str) -> int:
    """
    Parses size strings like '16 GB', '512 MB', '1 TB', '16384M', '15.4G' to bytes.
    Uses standard binary multipliers (1024-based) adhering to JEDEC memory standards.
    """
    if not size_str or size_str.lower() in ["none", "no module installed", "unknown"]:
        return 0
    s = size_str.strip().upper()
    match = re.match(r"^([0-9\.]+)\s*([KMGTPE]?I?[B]?)$", s)
    if not match:
        return 0
    val = float(match.group(1))
    unit = match.group(2)
    multipliers = {
        "": 1,
        "B": 1,
        "K": 1024,
        "KB": 1024,
        "KIB": 1024,
        "M": 1024**2,
        "MB": 1024**2,
        "MIB": 1024**2,
        "G": 1024**3,
        "GB": 1024**3,
        "GIB": 1024**3,
        "T": 1024**4,
        "TB": 1024**4,
        "TIB": 1024**4,
    }
    return int(val * multipliers.get(unit, 1024**3))


class HardwareParsers:
    """Parsers for all allowlisted system inspection commands."""

    @staticmethod
    def parse_lscpu(raw_output: str) -> CPUInfo:
        """Parses `lscpu -J` (JSON) or plain text `lscpu`."""
        info = CPUInfo()
        if not raw_output or not raw_output.strip():
            return info

        try:
            # Try JSON parsing
            data = json.loads(raw_output)
            fields = {item["field"].rstrip(":"): item["data"] for item in data.get("lscpu", [])}
        except Exception:
            # Plain text parsing fallback
            fields = {}
            for line in raw_output.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    fields[k.strip()] = v.strip()

        info.architecture = str(fields.get("Architecture", "x86_64"))
        info.model_name = str(fields.get("Model name", fields.get("Processor", "Unknown CPU")))
        info.total_cores = int(fields.get("CPU(s)", fields.get("Core(s) per socket", 1)))
        info.total_threads = int(fields.get("CPU(s)", 1))
        info.sockets = int(fields.get("Socket(s)", 1))
        info.cores_per_socket = int(fields.get("Core(s) per socket", 1))

        # Max frequency
        freq_str = str(fields.get("CPU max MHz", fields.get("CPU MHz", "0")))
        try:
            info.max_mhz = float(freq_str.replace(",", "."))
        except ValueError:
            info.max_mhz = 0.0

        return info

    @staticmethod
    def parse_free(raw_output: str) -> MemoryUsage:
        """Parses `free -b` (exact bytes)."""
        usage = MemoryUsage()
        lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
        for line in lines:
            parts = line.split()
            if not parts:
                continue
            if parts[0].startswith("Mem:"):
                # Format: Mem: total used free shared buff/cache available
                if len(parts) >= 4:
                    usage.total_bytes = int(parts[1])
                    usage.used_bytes = int(parts[2])
                    usage.free_bytes = int(parts[3])
                if len(parts) >= 7:
                    usage.available_bytes = int(parts[6])
                else:
                    usage.available_bytes = usage.free_bytes
            elif parts[0].startswith("Swap:"):
                if len(parts) >= 3:
                    usage.swap_total_bytes = int(parts[1])
                    usage.swap_used_bytes = int(parts[2])

        return usage

    @staticmethod
    def parse_lsblk(raw_output: str) -> StorageTopology:
        """Parses `lsblk -J -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,ROTA,TRAN,MODEL`."""
        topology = StorageTopology()
        if not raw_output or not raw_output.strip():
            return topology

        try:
            data = json.loads(raw_output)
            blockdevices = data.get("blockdevices", [])
        except Exception:
            # Fallback if non-JSON
            return topology

        for dev in blockdevices:
            dev_type = dev.get("type", "disk")
            if dev_type != "disk":
                continue

            name = dev.get("name", "")
            model = dev.get("model", "Unknown Drive").strip()
            tran = str(dev.get("tran", "")).lower()
            rota = dev.get("rota", True)
            if isinstance(rota, str):
                rota = rota == "1" or rota.lower() == "true"

            size_str = str(dev.get("size", "0"))
            size_bytes = parse_size_to_bytes(size_str)

            is_nvme = "nvme" in tran or name.startswith("nvme")
            is_ssd = not rota or is_nvme

            storage_dev = StorageDevice(
                name=name,
                size_bytes=size_bytes,
                device_type=dev_type,
                is_ssd=is_ssd,
                is_nvme=is_nvme,
                rotational=rota,
                transport=tran or ("nvme" if is_nvme else "sata"),
                mountpoint=dev.get("mountpoint"),
                model=model,
            )
            topology.disks.append(storage_dev)

        return topology

    @staticmethod
    def parse_lspci(raw_output: str) -> List[GPUDevice]:
        """Parses `lspci -mm` or standard `lspci` for graphics devices."""
        gpus: List[GPUDevice] = []
        lines = raw_output.splitlines()

        for line in lines:
            line_clean = line.strip()
            # Match display/VGA controllers
            if any(term in line_clean.lower() for term in ["vga compatible controller", "3d controller", "display controller"]):
                gpu = GPUDevice()
                # Machine readable lspci -mm: Slot "Class" "Vendor" "Device" ...
                # Or standard lspci: 00:02.0 VGA compatible controller: Intel Corporation ...
                if ":" in line_clean:
                    parts = line_clean.split(":", 2)
                    gpu.bus_id = parts[0].strip()
                    desc = parts[-1].strip()
                    gpu.model = desc

                    desc_lower = desc.lower()
                    if "nvidia" in desc_lower:
                        gpu.vendor = "NVIDIA"
                        gpu.is_discrete = True
                    elif "amd" in desc_lower or "advanced micro devices" in desc_lower or "radeon" in desc_lower:
                        gpu.vendor = "AMD"
                        gpu.is_discrete = "radeon rx" in desc_lower or "discrete" in desc_lower
                    elif "intel" in desc_lower:
                        gpu.vendor = "Intel"
                        gpu.is_discrete = "arc" in desc_lower
                    else:
                        gpu.vendor = "Unknown"

                gpus.append(gpu)

        return gpus

    @staticmethod
    def parse_dmidecode_memory(raw_output: str) -> MemoryTopology:
        """
        Parses `dmidecode -t memory` output.
        Extracts Physical Memory Array (max capacity, total slots) and
        Memory Device sections (locator, size, type, speed).
        """
        topo = MemoryTopology()
        if not raw_output or "Permission denied" in raw_output or "/dev/mem" in raw_output:
            topo.is_root_restricted = True
            topo.note = "dmidecode requires root privileges to read physical DMI memory tables."
            return topo

        sections = raw_output.split("Handle ")
        for sec in sections:
            if not sec.strip():
                continue

            lines = [l.strip() for l in sec.splitlines()]
            header = lines[0] if lines else ""

            if "Physical Memory Array" in sec:
                for line in lines:
                    if line.startswith("Maximum Capacity:"):
                        cap_str = line.split(":", 1)[1].strip()
                        topo.max_capacity_bytes = parse_size_to_bytes(cap_str)
                    elif line.startswith("Number Of Devices:"):
                        try:
                            topo.total_slots = int(line.split(":", 1)[1].strip())
                        except ValueError:
                            pass

            elif "Memory Device" in sec:
                slot = MemorySlot(locator="Unknown")
                is_installed = False

                for line in lines:
                    if line.startswith("Locator:"):
                        slot.locator = line.split(":", 1)[1].strip()
                    elif line.startswith("Size:"):
                        size_str = line.split(":", 1)[1].strip()
                        if "no module" not in size_str.lower() and size_str != "0 B":
                            slot.size_bytes = parse_size_to_bytes(size_str)
                            is_installed = True
                    elif line.startswith("Form Factor:"):
                        slot.form_factor = line.split(":", 1)[1].strip()
                    elif line.startswith("Type:") and not line.startswith("Type Detail:"):
                        slot.memory_type = line.split(":", 1)[1].strip()
                    elif line.startswith("Speed:"):
                        speed_str = line.split(":", 1)[1].strip()
                        speed_match = re.search(r"(\d+)", speed_str)
                        if speed_match:
                            slot.speed_mhz = int(speed_match.group(1))
                    elif line.startswith("Manufacturer:"):
                        slot.manufacturer = line.split(":", 1)[1].strip()

                slot.installed = is_installed
                topo.slots.append(slot)
                if is_installed:
                    topo.used_slots += 1
                    topo.installed_bytes += slot.size_bytes

        # If total_slots was not found in Physical Memory Array, infer from Memory Device count
        if topo.total_slots == 0:
            topo.total_slots = len(topo.slots)

        topo.empty_slots = max(0, topo.total_slots - topo.used_slots)

        # Upgrade calculation
        if topo.total_slots > 0 and topo.max_capacity_bytes > 0:
            topo.max_per_slot_bytes = topo.max_capacity_bytes // topo.total_slots
            # Can add RAM if empty slots exist or if current capacity is below board maximum
            topo.upgradeable = (topo.empty_slots > 0) or (topo.installed_bytes < topo.max_capacity_bytes)

        return topo

    @staticmethod
    def parse_proc_meminfo(raw_output: str) -> MemoryUsage:
        """Fallback memory parser for /proc/meminfo when `free` is missing."""
        usage = MemoryUsage()
        for line in raw_output.splitlines():
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            k = k.strip()
            match = re.search(r"(\d+)", v)
            if not match:
                continue
            kb_val = int(match.group(1))
            bytes_val = kb_val * 1024

            if k == "MemTotal":
                usage.total_bytes = bytes_val
            elif k == "MemFree":
                usage.free_bytes = bytes_val
            elif k == "MemAvailable":
                usage.available_bytes = bytes_val
            elif k == "SwapTotal":
                usage.swap_total_bytes = bytes_val
            elif k == "SwapFree":
                usage.swap_used_bytes = (usage.swap_total_bytes - bytes_val) if usage.swap_total_bytes else 0

        usage.used_bytes = max(0, usage.total_bytes - usage.available_bytes)
        return usage
