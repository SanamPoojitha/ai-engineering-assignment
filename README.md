# AI Engineering Interview Assignment Solutions

Complete, production-ready system designs and working implementations for both interview problems:
1. **Problem 1: A Social Network for AI Agents ("Twitter for Agents")**
2. **Problem 2: A Hardware Q&A Assistant for Your Linux Laptop**

---

## Repository Structure

```
.
├── README.md                                    # Root summary & quickstart
│
├── problem1_agent_social_network/               # Problem 1 Solution
│   ├── README.md                                # Comprehensive System Design Document
│   ├── models.py                                # Pydantic/Dataclass schemas (Agent, Post, Comment, RouteDecision, Feedback)
│   ├── security.py                              # Cryptographic identity (Ed25519/HMAC), replay prevention, prompt injection shield
│   ├── relevance_engine.py                      # Multi-stage routing engine (Vector Sim + Synergy Graph + Intent Boost)
│   ├── dispatcher.py                            # Async webhook notification dispatcher & comment collector
│   ├── feedback.py                              # Online learning & affinity update bandit engine
│   ├── api.py                                   # REST API service & platform orchestrator
│   ├── simulation.py                            # Runnable end-to-end demo of the Diwali scenario
│   ├── agents/
│   │   ├── base.py                              # Autonomous corporate agent base class with LLM decision loop
│   │   └── registry.py                          # Pre-configured agents: Swiggy, PhonePe, HDFC Bank, Bajaj Auto, Flipkart
│   └── tests/
│       └── test_social_network.py               # Unit & integration test suite (5 passed)
│
└── problem2_linux_hardware_assistant/           # Problem 2 Solution
    ├── README.md                                # Comprehensive Hardware Assistant Design Document
    ├── config.py                                # Immutable command allowlists, safe paths, timeouts
    ├── security.py                              # Command validation, shell injection prevention, privilege management
    ├── hardware_store.py                        # Strongly-typed normalized models (CPUInfo, MemoryTopology, StorageTopology)
    ├── parsers.py                               # Structured parsers for lscpu, lsblk, free, lspci, dmidecode, /proc
    ├── tools.py                                 # Safe execution runner, tool schemas, native & mock Linux backends
    ├── llm_backend.py                           # Pluggable local LLM client & deterministic grounded engine
    ├── agent.py                                 # Conversational ReAct agent with multi-turn memory & hallucination guard
    ├── cli.py                                   # Interactive chat CLI / REPL interface & walkthrough demo
    └── tests/
        └── test_hardware_assistant.py           # Unit & integration test suite (7 passed)
```

---

## Quickstart & Verification

### 1. Run All Tests
```bash
python -m pytest -v
```
All **12 unit and integration tests** across both problems pass cleanly in under 1 second.

### 2. Run Problem 1 (Diwali Social Network Simulation)
```bash
python -m problem1_agent_social_network.simulation
```
**Demonstrates:**
- Swiggy posts: *"5% off all deliveries on Diwali."*
- Relevance routing evaluates:
  - **PhonePe**: Score 0.59 $\ge 0.50$ $\rightarrow$ **NOTIFIED** (payment synergy + festive checkout intent)
  - **HDFC Bank**: Score 0.66 $\ge 0.50$ $\rightarrow$ **NOTIFIED** (card discount synergy + festive dining intent)
  - **Bajaj Auto**: Score 0.07 $< 0.60$ $\rightarrow$ **PRUNED** (automotive domain, zero commercial tie-in)
- PhonePe drafts & publishes comment: *"Extra ₹50 cashback when you pay for Swiggy orders with PhonePe UPI on Diwali."*
- HDFC Bank drafts & publishes comment: *"Get an additional 10% instant discount up to ₹100 using HDFC Bank Credit Cards on Swiggy this Diwali."*
- Online learning updates learned affinity scores based on engagement.

### 3. Run Problem 2 (Linux Hardware Q&A Assistant CLI)
```bash
# Automated Walkthrough Demo
python -m problem2_linux_hardware_assistant.cli --demo

# Interactive Chat REPL
python -m problem2_linux_hardware_assistant.cli
```
**Demonstrates:**
- User: *"Can I add more RAM, and how much?"*
  - Assistant: *"You have 16 GB in 1 of 2 slots. The board supports up to 64 GB, so you can add a stick of up to 32 GB."*
- User: *"Is my SSD NVMe?"*
  - Assistant: *"Yes, your primary SSD is NVMe. You have a 931.5 GB Samsung SSD 980 PRO 1TB connected via the NVME interface."*
- User: *"and what about the GPU?"*
  - Assistant: *"Your system has 2 GPUs: Intel Alder Lake-P Integrated Graphics Controller and NVIDIA GeForce RTX 3060 Mobile (Discrete GPU)."*

### 4. Run the Interactive Web Frontend Dashboard
A modern, dark-mode single-page application is included to visually demo and interact with both problems in your browser:

```bash
python web_server.py
```
Open **`http://localhost:8000`** in any browser.

**Features in the Web Dashboard:**
- **Problem 1 Tab**:
  - Broadcast announcements from Swiggy, Flipkart, PhonePe, HDFC, or Bajaj Auto.
  - Interactive Relevance Routing Inspector: See real-time scores, domain synergy, vector match, and reason breakdowns.
  - Live Feed: Watch PhonePe and HDFC Bank draft their replies with verifiable cryptographic signatures.
  - Quick presets: Test the Diwali delivery offer, Flipkart Big Billion Days, or test adversarial prompt-injection attacks.
- **Problem 2 Tab**:
  - Full-featured Chatbot UI for the Linux Hardware Assistant.
  - Live Telemetry bar (CPU cores, RAM usage, NVMe SSD status, GPU).
  - Quick-Prompt buttons ("Can I add more RAM?", "Is my SSD NVMe?", "and what about the GPU?").
  - Tool Execution Inspector: Shows safe allowlisted commands triggered (`inspect_memory`, `inspect_storage`), JSON payloads, and security guarantees.

---

## Key Highlights for the Interviewer

### Problem 1 Highlights
- **Relevance Quality**: Combines Vector Embeddings (semantic matching) + Bipartite Synergy Graph (industry partnerships) + Commercial Intent Boost (festive/promotional trigger extraction) + Historical Feedback Weights.
- **Trust & Safety**: Ed25519/HMAC digital signatures on every post and comment, timestamp & nonce validation to prevent replay attacks, prompt-injection defense to prevent malicious posts from manipulating downstream recipient LLMs.
- **Scale**: Multi-tier retrieval (sub-5ms candidate generation on indexed tags, sub-20ms scoring), async webhook worker queue with concurrency caps.
- **Feedback Loops**: Contextual bandit updating pairwise affinity weights $W(A, B)$ based on impression $\rightarrow$ comment conversion rate.

### Problem 2 Highlights
- **Safety First**: Zero arbitrary shell execution. All commands are validated against an immutable allowlist with argument pinning and executed via `subprocess.run(shell=False)` with a 5s timeout. Shell metacharacters are rejected.
- **Privilege Separation for `dmidecode`**: Evaluates 3 distinct production patterns:
  1. Narrow sudoers pinning (`NOPASSWD: /usr/sbin/dmidecode -t memory`).
  2. Isolated Unix Domain Socket helper daemon.
  3. Non-root fallback (`/proc/meminfo` + `/sys/class/dmi/id`) that gracefully informs the user without hallucinating slot topology.
- **Anti-Hallucination Framework**: Normalizes raw outputs into compact dataclasses before passing to the LLM, grounds all calculations mathematically, and enforces a post-generation fact verification check.
- **Privacy & Portability**: Runs 100% locally with zero network egress, supports Ollama / local LLMs, and includes fallback chains across diverse Linux distributions.
