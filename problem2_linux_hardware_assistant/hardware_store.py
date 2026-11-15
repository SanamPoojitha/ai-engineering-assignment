"""
Hardware Data Models and Canonical Normalized Representations.
All raw hardware telemetry is converted into these strongly-typed dataclasses
before being passed to the LLM context or user.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


def bytes_to_human(b: int) -> str:
    """Converts bytes into clean human-readable GiB / GB string."""
    if b <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    val = float(b)
    for u in units:
        if val < 1024.0 or u == "TB":
            return f"{val:.1f} {u}" if val % 1 != 0 else f"{int(val)} {u}"
        val /= 1024.0
    return f"{b} B"


@dataclass
class CPUInfo:
    architecture: str = "Unknown"
    model_name: str = "Unknown"
    sockets: int = 1
    cores_per_socket: int = 1
    total_cores: int = 1
    total_threads: int = 1
    max_mhz: float = 0.0
    min_mhz: float = 0.0

    def to_compact_dict(self) -> dict:
        return {
            "model": self.model_name,
            "architecture": self.architecture,
            "cores": self.total_cores,
            "threads": self.total_threads,
            "sockets": self.sockets,
            "max_frequency_ghz": round(self.max_mhz / 1000.0, 2) if self.max_mhz > 0 else "Unknown",
        }


@dataclass
class MemoryUsage:
    total_bytes: int = 0
    used_bytes: int = 0
    free_bytes: int = 0
    available_bytes: int = 0
    swap_total_bytes: int = 0
    swap_used_bytes: int = 0

    def to_compact_dict(self) -> dict:
        return {
            "total_ram": bytes_to_human(self.total_bytes),
            "used_ram": bytes_to_human(self.used_bytes),
            "free_ram": bytes_to_human(self.free_bytes),
            "available_ram": bytes_to_human(self.available_bytes),
            "total_bytes": self.total_bytes,
        }


@dataclass
class MemorySlot:
    locator: str
    installed: bool = False
    size_bytes: int = 0
    form_factor: str = "SODIMM"  # SODIMM (laptops), DIMM (desktops), Soldered
    memory_type: str = "DDR4"   # DDR4, DDR5, LPDDR4, etc.
    speed_mhz: int = 0
    manufacturer: str = "Unknown"

    def to_compact_dict(self) -> dict:
        return {
            "locator": self.locator,
            "installed": self.installed,
            "size": bytes_to_human(self.size_bytes) if self.installed else "Empty",
            "form_factor": self.form_factor,
            "type": self.memory_type if self.installed else "N/A",
            "speed_mhz": self.speed_mhz if self.installed and self.speed_mhz > 0 else "N/A",
        }


@dataclass
class MemoryTopology:
    installed_bytes: int = 0
    total_slots: int = 0
    used_slots: int = 0
    empty_slots: int = 0
    max_capacity_bytes: int = 0
    upgradeable: bool = False
    max_per_slot_bytes: int = 0
    slots: List[MemorySlot] = field(default_factory=list)
    is_root_restricted: bool = False
    note: str = ""

    def to_compact_dict(self) -> dict:
        return {
            "installed_ram": bytes_to_human(self.installed_bytes),
            "slots_summary": f"{self.used_slots} of {self.total_slots} slots in use" if self.total_slots > 0 else "Slot details unavailable without root",
            "total_slots": self.total_slots,
            "used_slots": self.used_slots,
            "empty_slots": self.empty_slots,
            "max_supported_capacity": bytes_to_human(self.max_capacity_bytes) if self.max_capacity_bytes > 0 else "Unknown / Firmware restricted",
            "upgradeable": self.upgradeable,
            "max_per_slot": bytes_to_human(self.max_per_slot_bytes) if self.max_per_slot_bytes > 0 else "Unknown",
            "slots": [s.to_compact_dict() for s in self.slots],
            "root_restricted": self.is_root_restricted,
            "note": self.note,
        }


@dataclass
class StorageDevice:
    name: str
    size_bytes: int = 0
    device_type: str = "disk"   # disk, part, rom
    is_ssd: bool = True
    is_nvme: bool = False
    rotational: bool = False
    transport: str = "nvme"     # nvme, sata, usb, scsi
    mountpoint: Optional[str] = None
    model: str = "Unknown"

    def to_compact_dict(self) -> dict:
        return {
            "name": self.name,
            "model": self.model,
            "size": bytes_to_human(self.size_bytes),
            "is_nvme": self.is_nvme,
            "is_ssd": self.is_ssd,
            "transport": self.transport,
            "mountpoint": self.mountpoint,
        }


@dataclass
class StorageTopology:
    disks: List[StorageDevice] = field(default_factory=list)

    def to_compact_dict(self) -> dict:
        return {
            "total_disks": len(self.disks),
            "devices": [d.to_compact_dict() for d in self.disks],
            "has_nvme": any(d.is_nvme for d in self.disks),
            "has_ssd": any(d.is_ssd for d in self.disks),
        }


@dataclass
class GPUDevice:
    vendor: str = "Unknown"
    model: str = "Unknown"
    driver: str = "Unknown"
    bus_id: str = ""
    is_discrete: bool = False

    def to_compact_dict(self) -> dict:
        return {
            "vendor": self.vendor,
            "model": self.model,
            "driver": self.driver,
            "type": "Discrete GPU" if self.is_discrete else "Integrated GPU",
            "bus_id": self.bus_id,
        }


@dataclass
class MotherboardInfo:
    manufacturer: str = "Unknown"
    product_name: str = "Unknown"
    version: str = "Unknown"
    bios_version: str = "Unknown"

    def to_compact_dict(self) -> dict:
        return {
            "manufacturer": self.manufacturer,
            "product_name": self.product_name,
            "bios_version": self.bios_version,
        }
