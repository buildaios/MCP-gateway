# Fedora AI OS – A Governed Cognitive Orchestration Layer for Fedora Linux

![Status](https://img.shields.io/badge/status-active_development-blue?style=flat-square)
![Platform](https://img.shields.io/badge/platform-fedora-blue?style=flat-square)
![Language](https://img.shields.io/badge/python-3.12+-green?style=flat-square)
![Architecture](https://img.shields.io/badge/architecture-agentic_os-purple?style=flat-square)
![Protocol](https://img.shields.io/badge/MCP-enabled-orange?style=flat-square)

> An AI-native operating environment built on Fedora Linux, combining durable workflow orchestration, recoverable execution, MCP-powered tool integration, and multi-agent intelligence.

Fedora AI OS is a security-first, AI-native orchestration layer built on top of Fedora Linux, designed to transform the operating system into a governed cognitive workspace. It augments Fedora/GNOME with a federation of specialized, SELinux-confined AI agents that coordinate tasks, memory, desktop interaction, and system management through auditable interfaces.

This project is NOT a chatbot, a shell wrapper, a voice assistant, or a custom distribution. It IS a cognitive orchestration layer built with Fedora’s own security primitives.

---

## 🏛️ Project Leadership & Attribution

### Founder & Chief Architect
**Lakshay Dabas**  
Founder of Fedora AI OS and primary architect of the core infrastructure:
* **Recoverable Runtime:** Building the fail-safe execution environment.
* **Workflow Orchestration Engine:** Powering agent task flow.
* **State Persistence:** Checkpointing and Suspend/Resume mechanisms.
* **Agentic Operating Environment Architecture:** Defining the structural blueprints.
* **Long-Term Project Vision:** Steering the cognitive OS roadmap.

### Repository Host & MCP Infrastructure Lead
**Lakshay Bharti** ([DAREDEVIL-OF-NEXUS](https://github.com/DAREDEVIL-OF-NEXUS))  
Responsible for the critical integration layer and repository operations:
* **MCP Gateway Development:** Building the core proxy and routing mechanisms.
* **Agent Tooling & Ecosystem:** Extending agent capabilities via tools.
* **API Infrastructure & Gateway Architecture.**
* **Repository Operations & Collaboration Infrastructure.**

---

## 👥 Core Development Teams

### Runtime & Agent Orchestration Department
**Department Head:** Lakshay Dabas  
**Team Members:** Jatin, Kapil, Ishita, Yuvraj  
**Responsibilities:** Runtime Engine, Workflow Orchestration, Recovery Systems, State Persistence, Checkpointing, and Agent Runtime Infrastructure.

### Gateway & Integrations Department
**Department Head:** Lakshay Bharti  
**Team Members:** Manish, Pratham, Prerit, Saksham  
**Responsibilities:** MCP Gateway, Tool Registry, Agent Communication Layer, API Development, MCP Servers & Clients, and External Integrations.

### Security & Governance Department
**Department Head:** Ojasvi  
**Team Members:** Mridul  
**Responsibilities:** Security Review, Threat Analysis, Governance Policies, Access Control, Audit Systems, and Security Architecture.

---

## 🔭 Project Vision

Fedora AI OS aims to fundamentally transform traditional operating systems.

**From the traditional model:**
`User → Operating System`

**To a cognitive, agent-driven model:**
`User → CEO Agent → Specialist Agents → MCP Gateway → Tools → Fedora Linux`

The long-term goal is to create a recoverable, agentic, AI-native operating environment capable of autonomous planning, execution, failure recovery, tool coordination, and proactive user assistance through intelligent workflows.

---

## 📜 Repository Governance

This repository is actively hosted under:  
[https://github.com/DAREDEVIL-OF-NEXUS/Fedora-AI-OS](https://github.com/DAREDEVIL-OF-NEXUS/Fedora-AI-OS)

Project leadership, architectural ownership, and authorship remain attributed to the Fedora AI OS team and its founder, **Lakshay Dabas**.

*Note: Repository hosting and project ownership should not be interpreted as equivalent concepts. Fedora AI OS is a collaborative engineering effort maintained by its dedicated contributors and department leads.*

---

## 🚀 Current Development Focus

**Phase:** `MCP Gateway & Agent Infrastructure Foundation`

Our current project sprint is focused on establishing the critical tool integration layer. The project is built on top of an already established recoverable workflow runtime capable of checkpointing, recovery, suspend/resume execution, orchestration, and durable state management.

**Current Priorities:**
* MCP Gateway Core Proxy
* Tool Registry Initialization
* Agent Communication Contracts
* Gateway APIs & Routing
* Integration Framework Foundation
* Agent Ecosystem Scaffolding

---


## Core Principles:

*   **Governed Autonomy:** AI acts within enforced, auditable boundaries.
*   **Security First:** Isolation before intelligence, always.
*   **Observability:** Every action is traceable, replayable, and attributed.
*   **Recoverability:** All failures must be reversible or compensatable.
*   **Modularity:** Components can be replaced independently.
*   **Upstream Alignment:** Built with Fedora and GNOME ecosystems, not around them.
*   **OS-Native Execution:** Direct DBus/Unix sockets for low latency; MCP Gateway for external tools.

## Project Status Snapshot:

Fedora AI OS has moved from an architectural concept to active implementation and community engagement.

**Implemented Core Components (V1/V2):**
*   **Secure Runtime:** Rootless Podman containers with SELinux confinement, running the Goose executor.
*   **Workflow Engine:** LangGraph-based durable, checkpointed, and recoverable workflows powered by `v3_engine.py`.
*   **Memory System:** Multi-tiered memory (Personal, Operational, Graph, Audit) for structured fact storage.
*   **MCP Gateway:** A foundational, secure gateway for external tool calls.
*   **Resilience Mechanisms:** Standby Orchestrator for CEO agent failures and crash simulation/recovery testing.

**Key Documentation Reviewed:**
*   **Architecture Blueprints (v3.0 & v4.0):** Detailed guides on the 7-layer structure, agent roles, security, LLM routing, and roadmaps.
*   **Agentic Flow:** Describes the multi-agent system, marketplace, security pre-flight, and MCP execution.
*   **Implementation Details:** Documentation of recoverable workflows and core engine logic.
*   **Project History & Community:** Chronological progress from idea to Fedora SIG engagement.
*   **External Validation:** Analysis of Red Hat's `coreos/ai-helpers` repository confirming architectural alignment.

The project is currently focused on maturing its core components and integrating further intelligence, memory, and agent capabilities in subsequent development phases.

## Project Structure:

*   **`implementation_code/`**: All live code.
    *   `implementation_code/phase0/` — Workflow engine (v2/v3, complete and chaos-tested)
    *   `implementation_code/phase1/` — MCP Gateway, LangGraph bridge, and future components
*   **`project_state/`**: Source of truth — authoritative project documents (5 files).
*   **`roles/`**: Team assignments for all 4 contributors.
*   **`proposals/`**: Architecture blueprints and reference documents (not implementation state).
*   **`aios_done/`**: Historical/completed milestone documentation.

## Next Steps:

The current critical path is building the **MCP Gateway Core Proxy** — the central routing layer that every agent uses to talk to external tools. See `project_state/CRITICAL_PATH.md` for details and `project_state/NEXT_ACTIONS.md` for the full 20-task queue.

---
* *This README was generated based on our project discussions and reviewed documentation.*

