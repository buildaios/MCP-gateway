# Fedora AI OS — Critical Path

Last updated: 2026-06-07
Purpose: Narrow the decision space. This file exists so Hermes always knows the ONE thing to build next and what to avoid.

---

## Current Bottleneck

The runtime exists (v2/v3 engine — atomic checkpoints, compensation, suspend/resume, chaos-tested).

The next missing capability is:
**MCP Gateway — Core Proxy**

Why:
- Without the gateway, no component can talk to any other component
- LangGraph bridge, CEO agent, security agent, all specialist agents — every single one routes through the gateway
- Goose integration is standalone and can happen in parallel, but the gateway unblocks everything downstream
- Every task in NEXT_ACTIONS.md from #2 through #20 either directly or transitively depends on the gateway

---

## Current Phase

**Phase:** Runtime → Real Tool Execution

The workflow engine proved we can run steps reliably. Now we prove we can route tool calls through a gateway to real backends.

---

## Must Build Before (Hard Prerequisites)

These are the gates. Nothing else ships until these work:

- **MCP Gateway scaffold** — `implementation/phase1/mcp-gateway/`, pyproject.toml, `gateway serve`, health endpoint
- **MCP Gateway core proxy** — accept JSON-RPC, route to backend, forward response, YAML config
- **MCP Gateway schema validation** — reject malformed requests before they reach backends

---

## Must Not Work On Yet

These are out of scope for the current phase. Hermes must actively refuse to build these:

- Plugin marketplace
- Multi-agent federation / peer consensus
- V3 features (speculative sandboxes, deterministic replay, cross-device coordination)
- Advanced memory systems (Semantic Memory, Habit Inference, Mem0, vector stores)
- Any agent beyond CEO + Security (no Desktop, Memory, Semantic, Demo Learn agent yet)
- GNOME Shell extension
- eBPF network policies
- SELinux enforcing mode
- Grafana dashboards (need gateway + traces first)
- OpenTelemetry instrumentation (need gateway in place first)

If a task is on this list, it is explicitly blocked. Do not work on it. Point the user to this file.

---

## Success Condition

A user can:

```bash
cd implementation/phase1/mcp-gateway
pip install -e .
gateway serve &
curl -X POST http://localhost:8000/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"echo","arguments":{}},"id":1}'
# → response routed to backend, returned to caller
```

And the gateway handles: routing, validation, and backend errors (502 on unreachable).

---

## Decision-Making Priority

When Hermes makes any decision about what to build, fix, or plan:

1. **CURRENT_STATE.md** — what exists, what's verified
2. **CRITICAL_PATH.md** (this file) — what matters right now, what's blocked
3. **NEXT_ACTIONS.md** — concrete tasks with acceptance criteria
4. **ROADMAP.md** — long-term direction and phase boundaries
5. **Architecture docs** (aios/, aios_done/) — reference only, not decision input

### Rules

- **Always optimize for the critical path.** If a task doesn't move the critical path forward, it's lower priority regardless of how interesting it is.
- **Always prefer working software over future architecture.** A running gateway with no auth is better than a perfect architecture document about gateways with auth.
- **When in doubt, build the smallest thing that makes the success condition true.**
