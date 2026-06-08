# Fedora AI OS — Current State

Last updated: 2026-06-07
Source of truth: `implementation/phase0/` code + `aios_done/` documents

---

## Completed

### Phase 0 — Development Environment
- Fedora Podman container with bind-mounted workspace
- SELinux relabeling (:Z) verified
- Python 3.14.4 runtime, git 2.54.0
- Persistent filesystem across container restarts

### Workflow Engine v2 (v2_engine.py, 249 lines)
- `DirectoryLock` — flock-based mutual exclusion (LOCK_EX | LOCK_NB)
- `WorkflowState` — dataclass: data dict, next_step_index, completed_steps, is_complete, run_id
- `CheckpointStore` — atomic write (tempfile + os.rename + fsync), .bak fallback on corruption
- `AuditLogger` — JSON-lines append-only audit trail per step
- `Environment` — subprocess wrapper with timeout (SIGTERM via killpg), stdout/stderr capture, audit logging
- `ReconcilerStep` — base class: check_done (idempotency), check_ready (preconditions), apply, compensate
- `Orchestrator` — reconcile loop, retry (3 attempts, 2s backoff), compensation rollback on fatal
- Exception hierarchy: WorkflowError → RetryableError, FatalError → PreconditionFailedError, LockAcquisitionError

### Workflow Engine v3 (v3_engine.py, 267 lines)
- Superset of v2
- `SuspendIntent` exception — file-based or timer-based wakeup conditions
- `WorkflowState.status` — RUNNING, SUSPENDED, COMPLETE
- `register_wakeup()` — systemd-run integration for file watches and timer-based resume
- Resume-aware orchestrator (`is_resume` parameter)
- Same checkpoint/store/audit/lock/compensation as v2

### Workflows Built and Verified
| Workflow | Engine | Steps | Features |
|----------|--------|-------|----------|
| recoverable_workflow.py | v1 (simple) | 5 steps: python3 → git → install → verify → report | Crash recovery demonstrated |
| main.py | v1 (simple) | 4 steps: file create → crash → final → system info | Retry with state isolation |
| v2_package_workflow.py | v2 | 5 steps: check python → check git → install git → verify → report | Full ReconcilerStep pattern |
| podman_workflow.py | v2 | 3 steps: pull alpine → create container → health check | Compensation (container rm), real Podman |
| deployment_workflow.py | v2 | 4 steps: atomic MOTD → git mirror → monitor daemon → health check | Compensation (daemon kill), real git ops |
| v3_suspend_workflow.py | v3 | 3 steps: mock install → wait approval(suspend) → verify | Suspend/resume with systemd |

### Test Suite (6 tests)
| Test | What it proves |
|------|---------------|
| test_01_split_brain.py | Two concurrent orchestrators — flock prevents split-brain |
| test_02_compensation_cascade.py | Fatal at step 3, step 2's compensate throws — step 1's compensate still runs |
| test_03_atomic_failure.py | os.rename failure during save — original checkpoint survives uncorrupted |
| test_04_time_jump.py | time.monotonic used — system clock jumps don't corrupt duration tracking |
| test_05_zombie_management.py | Process group SIGTERM on timeout — stubborn processes handled |
| test_06_backup_recovery.py | Primary corrupted manually — engine falls back to .bak |

### Stress Testing
- `production_readiness_suite.py` — Chaos Monkey: 30-step workflow, random SIGKILL (0.1–1.5s intervals), all 30 artifacts intact after recovery
- `v2_stress_test.py` — Zombie lock + config drift reconciliation

---

## In Progress

Nothing. No active development branches or WIP code detected.

---

## Not Started

Every component from the v4 ACTIONABLE blueprint above the workflow engine layer:

- LangGraph integration
- MCP Gateway (proxy, OAuth, schema validation, circuit breaker)
- All specialist agents: CEO, Security, Memory, Desktop, Runtime, Semantic, Demo Learn
- Reflex Runtime (DBus, <100ms operations)
- Goose integration
- OpenTelemetry + Grafana
- SELinux policies (udica)
- Trust enforcement (TRUST_0–3) + approval system
- eBPF network policies
- LLM routing (local/cloud hybrid)
- Memory tiers: Personal (Mem0), Operational (Redis), Graph (FalkorDB/Neo4j), Audit (SQLite)
- Capability tokens
- GNOME Shell extension / AT-SPI2 integration
- Plugin marketplace
- Typed inter-agent contracts (protobuf)
- Habit inference module
- Semantic memory / vector store

---

## Blocked

Nothing is technically blocked. All planned next steps (MCP Gateway, LangGraph) have no hard prerequisites beyond what already exists.

---

## Verified Capabilities

- Atomic state persistence survives OS crash, SIGKILL, disk-full errors
- Backup checkpoint fallback on primary corruption
- Idempotent step execution (re-running completed workflows is safe)
- Compensation rollback on fatal errors (completed steps undone in reverse)
- Split-brain prevention via directory-level flock
- Process group management (timeout kills entire process tree)
- Suspend/resume via systemd file watches and timers
- Chaos-tested resilience — 30 steps survive random kills

---

## Existing Code Components

```
implementation/phase0/
├── v2_engine.py                    # Core engine v2 (249 lines)
├── v3_engine.py                    # Core engine v3 with suspend (267 lines)
├── recoverable_workflow.py         # Phase 1 workflow (185 lines)
├── main.py                         # Phase 1 workflow variant (179 lines)
├── v2_package_workflow.py          # Package workflow on v2 (96 lines)
├── podman_workflow.py              # Podman workflow on v2 (75 lines)
├── deployment_workflow.py          # Deployment workflow on v2 (123 lines)
├── v3_suspend_workflow.py          # Suspend workflow on v3 (60 lines)
├── v2_stress_test.py               # Zombie/drift stress (55 lines)
├── production_readiness_suite.py   # Chaos monkey (104 lines)
├── test_01_split_brain.py          # Split-brain test (43 lines)
├── test_02_compensation_cascade.py # Compensation cascade test (45 lines)
├── test_03_atomic_failure.py       # Atomic failure test (42 lines)
├── test_04_time_jump.py            # Time jump test (44 lines)
├── test_05_zombie_management.py    # Zombie management test (34 lines)
└── test_06_backup_recovery.py      # Backup recovery test (41 lines)
```
