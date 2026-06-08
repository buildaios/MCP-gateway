# Fedora AI OS — Next Actions (Active Task Queue)

Last updated: 2026-06-07
Ordered by dependency graph, not importance.
Mark tasks `[ ]` → `[x]` when completed.

---

## 1. [ ] MCP Gateway — Project Scaffold

**Reason:** First line of code for the next layer. Nothing depends on this — it's the new foundation.
**Depends on:** Nothing
**Acceptance Criteria:**
- Python project at `implementation/phase1/mcp-gateway/` with pyproject.toml
- Dependencies: mcp (Python SDK), httpx
- `gateway serve` command starts HTTP server on configurable port
- Health endpoint returns 200
- README with setup and run instructions
**Estimate:** 2 hours | **Role:** Backend/Python

---

## 2. [ ] MCP Gateway — Core Proxy Routing

**Reason:** The gateway must accept MCP JSON-RPC and forward to backends.
**Depends on:** Task 1
**Acceptance Criteria:**
- Accept POST with standard MCP JSON-RPC body
- Route to configured backend based on tool name or server prefix
- Forward response back to caller unchanged
- Error if backend unreachable (502 with meaningful error)
- Config file (YAML) defining backend URL mappings
**Estimate:** 1 week | **Role:** Backend/Python

---

## 3. [ ] Audit Memory Tier — SQLite Store

**Reason:** Every other component needs audit logging. Build this early so every subsequent task can log to it.
**Depends on:** Nothing (use existing AuditLogger pattern from v2_engine.py)
**Acceptance Criteria:**
- `implementation/phase1/audit_memory/` Python package
- Append-only SQLite with schema: id, timestamp, agent_id, event_type, payload (JSON)
- Read API: query by agent, event_type, time range
- Immutability: no UPDATE or DELETE operations
- SHA-256 hash chain for tamper evidence (optional for initial version)
**Estimate:** 3 days | **Role:** Backend/Python

---

## 4. [ ] Operational Memory Tier — Redis Setup

**Reason:** Active task state and session context — needed by LangGraph bridge and all agents.
**Depends on:** Nothing
**Acceptance Criteria:**
- Redis running (Podman container acceptable)
- Python client wrapper: `store(key, value, ttl)`, `fetch(key)`, `delete(key)`
- TTL enforcement verified (key expires automatically)
- Connection pool with retry on disconnect
**Estimate:** 2 days | **Role:** Backend/Infra

---

## 5. [ ] MCP Gateway — Schema Validation

**Reason:** Prevent malformed requests from reaching backends. Parallel work with Tasks 3-4.
**Depends on:** Task 2
**Acceptance Criteria:**
- jsonschema validation on incoming requests
- Backend-specific schemas defined per route
- Invalid requests return 400 with validation error details
- Schema registry loaded from config
**Estimate:** 3 days | **Role:** Backend/Python

---

## 6. [ ] MCP Gateway — OAuth Token Management

**Reason:** Real backends need authentication. Parallel work with Tasks 3-5.
**Depends on:** Task 2
**Acceptance Criteria:**
- OAuth token stored in Secret Service API (not plaintext config)
- Token refresh before expiry (proactive)
- Inject Authorization header into proxied requests
- Multiple backends, each with own token
- Token rotation supported
**Estimate:** 4 days | **Role:** Backend/Security

---

## 7. [ ] MCP Gateway — Resilience Layer

**Reason:** Production readiness requires retry, circuit breaker, and dead-letter queue.
**Depends on:** Tasks 2, 3 (audit memory for dead-letter queue)
**Acceptance Criteria:**
- Retry: 3 attempts with exponential backoff (1s, 2s, 4s)
- Circuit breaker: 3 consecutive failures → open for 30s → half-open probe
- Dead-letter queue: failed requests written to audit memory for later inspection
- All events logged to audit memory
**Estimate:** 4 days | **Role:** Backend/Infra

---

## 8. [ ] MCP Gateway — Health Dashboard

**Reason:** Operators need visibility into gateway and backend health.
**Depends on:** Tasks 2, 5, 6, 7
**Acceptance Criteria:**
- Simple HTML status page at `/dashboard`
- Shows: each backend (name, URL, status: healthy/degraded/down)
- Circuit breaker state per backend
- Recent request count and error rate
- Auto-refresh every 5 seconds
**Estimate:** 3 days | **Role:** Full-stack

---

## 9. [ ] MCP Gateway — Integration Tests

**Reason:** Gateway is a critical path component — must be tested thoroughly.
**Depends on:** Task 8
**Acceptance Criteria:**
- Mock backend that can be configured to succeed, delay, or error
- Test: successful proxy round-trip
- Test: backend timeout → retry → success
- Test: backend down → circuit breaker opens
- Test: invalid JSON → 400
- Test: OAuth token refresh flow
- Test: dead-letter queue receives failed requests
**Estimate:** 3 days | **Role:** Backend/QA

---

## 10. [ ] LangGraph Bridge — Project Setup

**Reason:** Next major integration point after MCP Gateway.
**Depends on:** Task 2 (MCP Gateway proxy)
**Acceptance Criteria:**
- `implementation/phase1/langgraph-bridge/` Python package
- Dependencies: langgraph, langgraph-checkpoint-sqlite
- Loads existing v3 workflow steps as LangGraph nodes
- Minimal graph: sequential node chain
**Estimate:** 1 day | **Role:** ML/AI Engineer

---

## 11. [ ] LangGraph Bridge — State Adapter

**Reason:** v3_engine.WorkflowState and LangGraph State must interop.
**Depends on:** Task 10
**Acceptance Criteria:**
- Bidirectional conversion: WorkflowState ↔ LangGraph TypedDict state
- CheckpointStore.save() called after each LangGraph node completes
- CheckpointStore.load() used for LangGraph resume
- Existing v2_package_workflow runs through LangGraph with no behavior change
**Estimate:** 3 days | **Role:** ML/AI Engineer

---

## 12. [ ] LangGraph Bridge — Checkpoint Integration

**Reason:** LangGraph's checkpointing must coexist with our atomic checkpoint store.
**Depends on:** Task 11
**Acceptance Criteria:**
- LangGraph SQLite checkpointer configured
- Our CheckpointStore remains the authoritative state
- On resume: load from LangGraph checkpoint, validate against our .bak
- Crash during LangGraph step → resume from our checkpoint
- Existing chaos monkey test passes with LangGraph orchestration
**Estimate:** 3 days | **Role:** ML/AI Engineer

---

## 13. [ ] LangGraph Bridge — MCP Gateway Integration

**Reason:** LangGraph nodes need to call tools through the gateway.
**Depends on:** Tasks 8 (MCP Gateway complete), 12
**Acceptance Criteria:**
- LangGraph node can call MCP Gateway to invoke a backend tool
- Tool response flows back into LangGraph state
- Timeout and retry handled by gateway, not LangGraph
- Full round-trip: LangGraph node → Gateway → Backend → Gateway → LangGraph state
**Estimate:** 2 days | **Role:** ML/AI Engineer

---

## 14. [ ] Reflex Runtime — Systemd Service

**Reason:** Desktop automation needs a fast, LLM-free path for basic operations.
**Depends on:** Nothing (standalone)
**Acceptance Criteria:**
- `implementation/phase1/reflex-runtime/reflexd.py`
- Systemd user service: `reflex-runtime.service`
- DBus methods: mute, unmute, set_volume(0-100), switch_workspace(N)
- Sub-100ms response measured and verified
- Health check: `systemctl --user status reflex-runtime`
- Uses python-dbus or pydbus
**Estimate:** 4 days | **Role:** Desktop/Linux

---

## 15. [ ] Goose — Quadlet Container Definition

**Reason:** Goose is the primary runtime agent — must run isolated in Podman.
**Depends on:** Nothing (standalone)
**Acceptance Criteria:**
- `~/.config/containers/systemd/goose.container` Quadlet file
- goose:latest or Fedora 43+ image with goose RPM
- Bind-mount: `~/fedora-ai-os/workspace:/workspace:Z`
- Rootless, with dropped capabilities
- `systemctl --user start goose` works
- Goose can execute `whoami` inside container and return output
**Estimate:** 3 days | **Role:** Infra/Linux

---

## 16. [ ] OpenTelemetry — Gateway Instrumentation

**Reason:** Observability is a V1 requirement.
**Depends on:** Task 8 (MCP Gateway complete)
**Acceptance Criteria:**
- OTel spans on every gateway request (receive, route, forward, respond)
- Export to local OTel collector (Podman container)
- Span attributes: backend, method, status_code, duration_ms
- Errors recorded as span events
**Estimate:** 2 days | **Role:** Backend/Observability

---

## 17. [ ] OpenTelemetry — Workflow Instrumentation

**Reason:** Workflow steps must be traced alongside gateway requests.
**Depends on:** Task 12 (LangGraph Bridge)
**Acceptance Criteria:**
- OTel spans for each workflow step execution
- Span attributes: step_name, attempt, duration, status
- Correlated with gateway spans via trace context propagation
- Export to same collector as gateway
**Estimate:** 2 days | **Role:** Backend/Observability

---

## 18. [ ] Grafana — Basic Dashboards

**Reason:** Traces without dashboards are invisible.
**Depends on:** Tasks 16, 17
**Acceptance Criteria:**
- Grafana running in Podman
- Dashboard: Gateway request rate, latency p50/p95/p99, error rate
- Dashboard: Workflow step success rate, retry distribution
- Dashboard: Backend health status
- JSON dashboard definitions in `implementation/phase1/grafana/dashboards/`
**Estimate:** 2 days | **Role:** Observability

---

## 19. [ ] CEO Agent — Minimal Decomposition

**Reason:** First agent — proves the full stack: LangGraph + MCP Gateway + Memory + Audit.
**Depends on:** Tasks 8, 12, 13, 4, 3
**Acceptance Criteria:**
- LLM call that decomposes "install and verify git" into sub-tasks
- Sub-tasks expressed as LangGraph nodes
- Each node calls MCP Gateway for execution
- State persisted in Redis (operational) and SQLite (audit)
- User can see: task → sub-tasks → execution results
- Model: uses local Ollama or cloud API based on task complexity
**Estimate:** 1 week | **Role:** ML/AI Engineer

---

## 20. [ ] Security Agent — Trust Level Enforcement

**Reason:** Second agent — gates all subsequent agent actions through trust levels.
**Depends on:** Tasks 8 (MCP Gateway), 19 (CEO Agent)
**Acceptance Criteria:**
- TRUST_0: silent, read-only — auto-approved
- TRUST_1: notification + inline undo — logged, user notified
- TRUST_2: confirm/deny — requires explicit user approval
- TRUST_3: modal with diff preview — full modal approval
- Escalation: scope creep → +1 level; unexpected network → TRUST_3
- Revocation: 3 violations/60s → agent suspended
- Enforcement point: MCP Gateway middleware (intercepts all agent tool calls)
**Estimate:** 1 week | **Role:** Backend/Security
