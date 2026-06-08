# Fedora AI OS — Architecture Index

Last updated: 2026-06-07
Source: `aios/FEDORA AI OS v4 0 ACTIONABLE.txt`
NOTE: This is reference-only. Implementation status comes from code and done documents, not this file.

---

## 7-Layer Stack

| Layer | Name | Key Components |
|-------|------|---------------|
| L7 | GNOME Shell UI | V2 extension, progressive disclosure, workspace switcher |
| L6 | CEO + Standby | Task decomposition, delegation, policy enforcement, passive failover |
| L5 | LangGraph | Workflows, checkpoint/replay, evaluation harness |
| L4 | Agent Kernel | LLM scheduling, context mgmt, lifecycle |
| L3 | Specialist Agents | CEO, Standby, Desktop, Runtime, Semantic, Memory, Security, Demo Learn, MCP Gateway |
| L2 | Runtime | Podman, MCP Gateway, Redis, OpenTelemetry, Grafana, eBPF |
| L1 | Unmodified Fedora | GNOME, Wayland, systemd, SELinux |

---

## Specialist Agents (L3)

- **CEO** — task decomposition, delegation, policy enforcement
- **Standby** — passive failover, resumes from LangGraph checkpoint
- **Desktop** — AT-SPI2 priority stack: Portals → DBus → GSettings → vision → synthetic
- **Runtime** — Goose (Fedora 43+ RPM) in rootless Podman: terminal, browser, files
- **Semantic** — vector store + graph traversal + metadata filters for meaning-first file ops
- **Memory** — 4 tiers: Personal, Operational, Graph, Audit (access-controlled)
- **Security** — rule-based trust scoring, capability tokens, runtime revocation
- **Demo Learn** — OpenAdapt V3: record → generalize → replay
- **MCP Gateway** — reverse proxy, schema validate, OAuth, circuit breakers, health checks

---

## Memory Tiers

| Tier | Backend | Purpose | Properties |
|------|---------|---------|------------|
| Personal | Mem0 / A-MEM | Long-term preferences & habits | Promoted after recurrence ≥ 3 |
| Operational | Redis | Active task state, session context | TTL-managed |
| Graph | FalkorDB / Neo4j | Entity relationships, project dependencies | Traversal queries |
| Audit | SQLite | Immutable event log | Append-only, tamper-evident |

---

## Security Stack

1. SELinux domain per agent (mcp_file_reader_t, mcp_desktop_t, etc.)
2. Rootless Podman with dropped capabilities
3. seccomp per container
4. Namespace isolation (user, network, mount, PID)
5. Capability tokens at Agent Kernel
6. Trust levels (TRUST_0 … TRUST_3) with escalation
7. MCP Gateway auth + schema validation + reverse proxy
8. eBPF network policy (V2)
9. Rollback for all mutating ops
10. Immutable audit logs + runtime capability revocation

---

## Trust Levels

| Level | Behavior | Example Actions |
|-------|----------|----------------|
| TRUST_0 | Silent, read-only | Read file |
| TRUST_1 | Notification + inline undo | Create file, open app |
| TRUST_2 | Confirm/deny prompt | Modify system setting |
| TRUST_3 | Modal with diff preview | Install software, edit security config |

Escalation: scope creep → +1 level; unexpected network → TRUST_3; trust degradation → +1 level
Revocation: 3 violations/60s, anomalous syscalls, trust score < 20 → suspend agent

---

## Failure Containment Matrix

| Failure | Containment |
|---------|-------------|
| Vision fail | → AT-SPI fallback |
| AT-SPI fail | → vision (GPU-metered) |
| CEO crash | → Standby Orchestrator, Reflex Runtime survives |
| Workflow crash | → LangGraph checkpoint recovery |
| Graph DB fail | → semantic search disabled, others continue |
| Cloud outage | → local LLM fallback, user notified |
| Memory tier fail | → isolate tier, others unaffected |
| Security Agent fail | → block TRUST_1+ actions, TRUST_0 continues |
| eBPF fail | → block network for agent, fail-closed |

---

## LLM Routing

| Complexity | Backend | Hardware |
|-----------|---------|----------|
| Trivial | Reflex Runtime (no LLM) | N/A |
| Simple | Local 1–3B quantized | 8 GB RAM, CPU |
| Medium | Local 7B Q4_K_M | 16 GB RAM, CPU |
| Complex | Local 13B+ or cloud API | User key or community pool |
| Sensitive | Local only (no cloud) | Hardware dependent |

---

## Benchmark Suite (V1 Targets)

- AT-SPI success rate: ≥ 85%
- Vision fallback rate: < 15%
- Workflow completion: ≥ 90%
- Rollback success: 100%
- Checkpoint recovery: < 5s
- Interruption dismissal: < 20%
- Memory retrieval: < 100ms
- MCP Gateway success: > 99%

---

## MCP Gateway Build Plan (4–6 weeks)

| Week | Deliverable |
|------|-----------|
| 1–2 | Core proxy: accept MCP, forward, return responses (no auth) |
| 3 | OAuth token storage, refresh, injection |
| 4 | JSON Schema validation, health-check pings |
| 5 | Retry with backoff, circuit breaker, dead-letter queue |
| 6 | Audit Memory integration, status dashboard |

---

## Community Pathway

1. Fedora AI/ML SIG participation (Matrix #ai:fedoraproject.org)
2. Innovation Lifecycle → Sandbox entry (time-limited trademark use, Council ticket)
3. MCP Gateway as first deliverable → solves immediate SIG pain point
4. V1 prototype demo → submit Sandbox Review metrics
5. Curation → FESCo, Infrastructure, Mindshare alignment
6. Integration → formal Change Proposal
