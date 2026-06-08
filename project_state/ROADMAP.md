# Fedora AI OS — Roadmap

Last updated: 2026-06-07
Driven by implementation state, not architecture documents.

---

## V1 — Foundation (current focus)

### 1a. MCP Gateway — Core Proxy
**Estimate:** 2 weeks | **Difficulty:** Medium | **Depends on:** Nothing
- Accept MCP JSON-RPC, forward to configured backends, return responses
- No auth, no validation — pure proxy
- Components: Python MCP SDK, httpx
- Verifiable: curl → gateway → backend → response round-trip

### 1b. MCP Gateway — OAuth + Schema Validation
**Estimate:** 2 weeks | **Difficulty:** Medium | **Depends on:** 1a
- OAuth token storage, refresh, injection (Secret Service API)
- jsonschema validation on all requests
- Health-check pings to backends
- Components: oauthlib, jsonschema, Secret Service API

### 1c. MCP Gateway — Resilience Layer
**Estimate:** 1 week | **Difficulty:** Medium | **Depends on:** 1a
- Retry with exponential backoff
- Circuit breaker (3 failures → open 30s)
- Dead-letter queue for failed requests
- Components: tenacity or custom retry

### 1d. MCP Gateway — Audit + Dashboard
**Estimate:** 1 week | **Difficulty:** Medium | **Depends on:** 1a, 1b, 1c
- Log all gateway events to SQLite audit store
- Simple status page showing backend health
- Components: SQLite, basic HTML/CSS

### 1e. LangGraph Workflow Bridge
**Estimate:** 3 weeks | **Difficulty:** Hard | **Depends on:** 1a (MCP Gateway)
- Wrap existing v3 engine steps as LangGraph nodes
- Use LangGraph checkpointing alongside existing atomic store
- State serialization: WorkflowState ↔ LangGraph state
- Verifiable: run existing package workflow through LangGraph, survive crash

### 1f. Operational Memory (Redis)
**Estimate:** 1 week | **Difficulty:** Easy | **Depends on:** Nothing (standalone)
- Redis instance for active task state, session context
- TTL-managed keys
- Simple Python client wrapper
- Verifiable: store/fetch workflow context, keys expire

### 1g. Audit Memory (SQLite)
**Estimate:** 1 week | **Difficulty:** Easy | **Depends on:** Nothing
- Append-only, immutable SQLite store
- Schema: timestamp, agent_id, event_type, payload
- Tamper-evident (hash chain optional for V1)
- Can reuse/extend existing AuditLogger pattern

### 1h. Reflex Runtime — Systemd Service
**Estimate:** 1 week | **Difficulty:** Medium | **Depends on:** Nothing
- Minimal systemd service for direct DBus operations
- Mute/unmute, volume control, workspace switching
- Sub-100ms response (no LLM in path)
- Verifiable: `systemctl --user start reflex-runtime`, test DBus calls

### 1i. Goose in Rootless Podman
**Estimate:** 2 weeks | **Difficulty:** Hard | **Depends on:** Nothing (standalone)
- Quadlet container definition
- Goose Fedora 43+ RPM in rootless Podman
- Bind-mount workspace, terminal access
- Verifiable: Goose can execute terminal commands inside container

### 1j. OpenTelemetry Instrumentation
**Estimate:** 2 weeks | **Difficulty:** Medium | **Depends on:** 1a (MCP Gateway), 1e (LangGraph)
- OTel spans on all gateway requests and workflow steps
- Export to local collector
- Basic Grafana dashboard (request rate, latency, error rate)
- Verifiable: Jaeger/Grafana shows trace from gateway → backend

### V1 Go/No-Go Criteria
- Workflow completion >= 90% (already met with v2 engine)
- MCP Gateway > 99% routing success
- Reflex < 100ms response
- Traces visible in Grafana
- Goose functional in Podman

---

## V1.5 — Integration (after V1 foundation)

### 1.5a. CEO Agent — Task Decomposition
**Estimate:** 3 weeks | **Difficulty:** Hard | **Depends on:** 1e (LangGraph), 1f (Redis), 1g (SQLite)
- LLM-powered task decomposition
- Delegation to specialist agents via MCP Gateway
- Policy enforcement stub (TRUST levels)
- Verifiable: "install and verify git" → decomposed to sub-tasks → executed

### 1.5b. Security Agent — Trust Scoring
**Estimate:** 2 weeks | **Difficulty:** Hard | **Depends on:** 1.5a (CEO Agent)
- Rule-based trust scoring (TRUST_0 through TRUST_3)
- Capability token issuance and verification
- Runtime revocation (3 violations in 60s → suspend)
- Verifiable: agent requests escalate through trust levels correctly

### 1.5c. Memory Agent — Personal + Operational
**Estimate:** 2 weeks | **Difficulty:** Medium | **Depends on:** 1f (Redis), 1g (SQLite)
- Personal memory (preferences, habits) via Mem0
- Operational memory already in Redis
- Recurrence tracking (promote after >= 3 occurrences)
- Verifiable: user preference stored, recalled in subsequent sessions

### 1.5d. Desktop Agent — AT-SPI2 Stack
**Estimate:** 4 weeks | **Difficulty:** Hard | **Depends on:** 1h (Reflex Runtime)
- AT-SPI2 priority stack: Portals → DBus → GSettings → vision → synthetic
- Multi-app workflow automation
- Headless research capability
- Verifiable: open app, interact with UI elements via AT-SPI2

### 1.5e. DBus Bridge — Python ↔ Goose
**Estimate:** 1 week | **Difficulty:** Medium | **Depends on:** 1i (Goose), 1h (Reflex)
- Goose can call DBus methods
- Reflex Runtime can relay to Goose
- Verifiable: Goose triggers desktop action via Reflex

---

## V2 — Intelligence Expansion

### 2a. Semantic Memory
**Estimate:** 3 weeks | **Difficulty:** Hard | **Depends on:** 1.5c (Memory Agent)
- Vector store (embedding-based retrieval)
- Graph traversal for entity relationships (FalkorDB/Neo4j)
- Metadata filters for meaning-first file operations
- Verifiable: "find files about security" returns semantically relevant results

### 2b. GNOME Shell Extension
**Estimate:** 4 weeks | **Difficulty:** Hard | **Depends on:** 1.5d (Desktop Agent)
- Progressive disclosure UI
- Workspace switcher
- Notification tray for TRUST_1 events
- TRUST_3 modal approval dialogs
- Verifiable: extension surfaces agent activity, user can approve/deny

### 2c. SELinux Policies — Enforcing Mode
**Estimate:** 4 weeks | **Difficulty:** Hard | **Depends on:** 1.5b (Security Agent)
- udica-generated per-agent policies
- Permissive mode → audit logging → audit2allow refinement
- Graduated enforcing mode
- Upstream submission to Fedora SELinux SIG
- Verifiable: agent restricted to its SELinux domain, violations logged

### 2d. eBPF Network Policy
**Estimate:** 3 weeks | **Difficulty:** Hard | **Depends on:** 2c (SELinux)
- Per-agent network policy enforcement
- Fail-closed on eBPF failure
- Verifiable: agent's network access restricted, blocked traffic logged

### 2e. Adaptive Interruption
**Estimate:** 3 weeks | **Difficulty:** Hard | **Depends on:** 1.5a (CEO Agent)
- Contextual bandit for interruption timing
- Dismissal rate < 20% target
- Verifiable: interruption frequency and timing adapts to user behavior

### 2f. Habit Inference Module
**Estimate:** 2 weeks | **Difficulty:** Medium | **Depends on:** 2a (Semantic Memory)
- Offline pattern mining from operational memory
- Separate from Memory Agent to avoid circular dependency
- Verifiable: recurring user patterns detected and surfaced

### 2g. Plugin API v1.0
**Estimate:** 3 weeks | **Difficulty:** Medium | **Depends on:** 1a (MCP Gateway)
- Plugin marketplace structure
- Versioned plugin contracts
- Safe sandboxing via Podman
- Verifiable: third-party plugin installs and runs in isolation

---

## V3 — Advanced Cognition (months 19–30)

- OpenAdapt integration (record → generalize → replay)
- Speculative sandboxes (eBPF syscall tracing)
- Peer consensus for multi-agent decisions
- Cross-device agent coordination
- Deterministic replay of all agent actions
- Plugin registry with community contributions

---

## Long-Term Vision

- MCP Gateway → community standard for Fedora AI tool access
- SELinux policies → upstream Fedora (Phase 3 submission)
- GNOME extension → possibly upstream GNOME if adoption warrants
- All local inference via Ramalama/Ollama (no cloud dependency for sensitive data)
- Full audit trail for every agent action (compliance-ready)
