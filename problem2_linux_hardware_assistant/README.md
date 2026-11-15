# Problem 2: A Hardware Q&A Assistant for Your Linux Laptop

A private, secure, locally running hardware assistant that answers plain-language questions about a Linux machine's hardware by safely querying system tools and normalizing system telemetry.

---

## 1. High-Level Architecture & Core Flow

```
[User Natural Language Query]
           │
           ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   HARDWARE ASSISTANT CORE ENGINE                       │
│                                                                        │
│  ┌─────────────────────────┐         ┌───────────────────────────────┐ │
│  │ Multi-Turn Chat Memory  │         │ Tool Selection & Planner      │ │
│  │ • Follow-up resolution  │ ──────> │ • Maps user intent to tools   │ │
│  │ • Entity tracking (GPU) │         │ • Caches invariant hardware   │ │
│  └─────────────────────────┘         └──────────────┬────────────────┘ │
│                                                     │                  │
│                                                     ▼                  │
│  ┌─────────────────────────┐         ┌───────────────────────────────┐ │
│  │ Factual Grounding Guard │         │ Safe Tool Execution Layer     │ │
│  │ • Rejects hallucinations│ <────── │ • Strict command allowlist    │ │
│  │ • Bounds numbers        │         │ • shell=False, zero injection │ │
│  └────────────┬────────────┘         │ • Privilege Separation        │ │
│               │                      └──────────────┬────────────────┘ │
│               ▼                                     │                  │
│  ┌─────────────────────────┐                        ▼                  │
│  │ Plain-Language Answer   │         ┌───────────────────────────────┐ │
│  │ Synthesizer (Local/LLM) │ <────── │ Output Parsers & Normalizers  │ │
│  └─────────────────────────┘         │ • lscpu, lsblk, dmidecode     │ │
│                                      │ • Clean, compact JSON         │ │
│                                      └───────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Tool-Calling Design: Grounding vs. Guessing

Large Language Models should **never guess or estimate** hardware specs. Instead, the assistant uses a ReAct/Function Calling pattern:

1. **Tool Schema Declarations**: The LLM is provided with strict JSON schemas for:
   - `inspect_memory(include_slots: bool)`: Free/used RAM + physical slot topology & max capacity.
   - `inspect_storage()`: Block devices, NVMe vs SATA SSD, partitions, mountpoints.
   - `inspect_cpu()`: Sockets, cores, threads, architecture, frequency scaling.
   - `inspect_gpu()`: PCI graphics controllers, discrete vs integrated.
   - `inspect_motherboard()`: Manufacturer, product name, BIOS version.
2. **Caching Invariant Hardware**:
   - Motherboard limits, physical CPU model, and RAM slot topology do not change at runtime. These are inspected once and cached in memory to minimize system overhead.
   - Volatile metrics (e.g. `free -b` buffer/cache memory) are always queried live.

---

## 3. Parsing and Normalizing Output into Structured Data

Dumping 200 lines of unparsed terminal output into the LLM context causes context bloat, token exhaustion, and hallucination. The assistant parses raw command output into compact, typed dataclasses:

| Command | Parser Target | Normalized Representation Example |
| :--- | :--- | :--- |
| `lscpu -J` | `CPUInfo` | `{"model": "i7-12700H", "cores": 14, "threads": 20, "max_freq_ghz": 4.7}` |
| `free -b` | `MemoryUsage` | `{"total_ram": "15.6 GB", "available_ram": "11.0 GB", "used_ram": "4.0 GB"}` |
| `lsblk -J` | `StorageTopology` | `{"name": "nvme0n1", "model": "Samsung 980 PRO", "is_nvme": true, "size": "1 TB"}` |
| `lspci -mm` | `GPUDevice` | `[{"vendor": "Intel", "type": "Integrated"}, {"vendor": "NVIDIA", "type": "Discrete"}]` |
| `dmidecode -t memory` | `MemoryTopology` | `{"used_slots": 1, "total_slots": 2, "max_capacity": "64 GB", "max_per_slot": "32 GB"}` |

### RAM Upgrade Math Engine
Given:
$$\text{Max Board Capacity} = 64 \text{ GB}, \quad \text{Total Slots} = 2, \quad \text{Installed} = 16 \text{ GB in Slot 1 (Slot 2 Empty)}$$
$$\text{Max Per Slot} = \frac{64 \text{ GB}}{2} = 32 \text{ GB}$$
$$\text{Max Addable Stick} = \min(\text{Max Per Slot}, \text{Max Capacity} - \text{Installed}) = \min(32, 48) = 32 \text{ GB}$$
Result:
> *"You have 16 GB in 1 of 2 slots. The board supports up to 64 GB, so you can add a stick of up to 32 GB."*

---

## 4. Multi-Turn Follow-Ups & Conversational Memory

The agent tracks conversational context:
- User: *"How much RAM do I have?"* $\rightarrow$ Assistant calls `inspect_memory`.
- User: *"Can I add more RAM, and how much?"* $\rightarrow$ Recognizes follow-up on memory topology.
- User: *"and what about the GPU?"* $\rightarrow$ Detects entity transition to graphics, invokes `inspect_gpu`, and answers seamlessly without losing prior context.

---

## 5. Security & System Design Deep-Dive (Interviewer Probes)

### Probe 1: Safety & Zero Arbitrary Shell Execution
- **Threat Model**: Prevent prompt injection or malicious user input from executing arbitrary shell commands (e.g. `rm -rf /`, `curl | bash`, exfiltration of private keys).
- **Execution Shield**:
  - `shell=False` is strictly enforced on all `subprocess.run` calls. Command strings are never passed to `/bin/sh` or `/bin/bash`.
  - Immutable Argument Allowlist: Each binary has an exact schema of allowed argument tuples (e.g., `lscpu` allows only `("-J",)` or `()`).
  - Metacharacter Rejection: Input arguments containing `;`, `|`, `&`, `$`, `>`, `<`, `` ` ``, or `\n` raise an immediate `SecurityViolationError`.
  - Environment Sanitation: Subprocesses execute with minimal environment (`PATH=/usr/bin:/bin:/usr/sbin:/sbin`, `LANG=C.UTF-8`).
  - Timeout Enforced: Hard 5.0-second timeout on all child processes.

### Probe 2: Permissions & The Root Problem (`dmidecode`)
`dmidecode` requires root privileges to read `/dev/mem` or `/sys/firmware/dmi/tables`. How is this safely handled without giving the chatbot blanket root access?

1. **Option A: Pinned Sudoers Rule (Recommended Production Path)**
   - Configure a narrow `sudoers` drop-in (`/etc/sudoers.d/hardware-assistant`):
     ```sudoers
     youruser ALL=(ALL) NOPASSWD: /usr/sbin/dmidecode -t memory, /usr/sbin/dmidecode -t baseboard
     ```
   - Sudo is invoked with `-n` (non-interactive). If authentication is required or arguments do not match, sudo exits immediately without hanging on a password prompt.
2. **Option B: Privilege-Separated Unix Domain Socket Helper Daemon**
   - A tiny root daemon runs in the background listening on `/run/hardware-assistant.sock`.
   - The unprivileged chatbot connects via local IPC and requests an enum action: `GET_MEMORY_DMI`.
   - The daemon executes the specific C/system call, parses the SMBIOS table in memory, and returns sanitized JSON. The LLM process never holds root or sudo permissions.
3. **Option C: Graceful Non-Root Fallback (Zero Permissions Needed)**
   - When root is unavailable, the assistant falls back to unprivileged paths:
     * Reads `/proc/meminfo` for memory usage.
     * Reads `/sys/class/dmi/id/` (world-readable on modern Linux kernels) for system product name and vendor.
     * **Crucial Anti-Hallucination Behavior**: If physical slot counts cannot be obtained without root, the assistant states:
       > *"You have 16 GB of installed RAM. However, inspecting physical motherboard slots and maximum capacity requires root privileges. Run with sudo or configure a sudoers rule."*
       It **never hallucinates** slot numbers when unprivileged!

### Probe 3: Accuracy & Anti-Hallucination Framework
- **Strict Grounded Prompting**: LLM is instructed: *"Answer only using the provided facts. If a spec is missing from the tool JSON, explicitly state that it is unknown."*
- **Post-Generation Fact Checker**: A deterministic validation pass parses numbers in the generated response and cross-references them with the tool JSON. If the model invents a specification not present in the hardware store, the answer is replaced with the structured factual summary.

### Probe 4: Distro Portability & Hardware Diversity
- **Fallback Chains**:
  - Memory: `free -b` $\rightarrow$ `/proc/meminfo` $\rightarrow$ `sysinfo` syscall.
  - Storage: `lsblk -J` $\rightarrow$ `/proc/partitions` + `/sys/block/*/queue/rotational`.
  - CPU: `lscpu -J` $\rightarrow$ `/proc/cpuinfo`.
- **Handling Cloud VMs & Masked DMI**: In cloud instances (AWS EC2, GCP, Docker) or soldered RAM laptops (Apple Silicon / ThinkPad Carbon with LPDDR5), DMI tables often report `Maximum Capacity: Unknown` or `0 Slots`. The assistant detects this condition and informs the user that memory is soldered or virtualized.

### Probe 5: Privacy & Local Execution
- **Zero Network Egress**: The assistant operates completely air-gapped on the laptop.
- **Local Model Backends**:
  - Pluggable support for Ollama (`http://localhost:11434/v1`) running `llama3.2:3b` or `mistral`.
  - Built-in `GroundedDeterministicEngine` that operates 100% offline with zero dependencies.
