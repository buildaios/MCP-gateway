import os
import sys
import json
import time
import signal
import subprocess
import tempfile
import shutil
import fcntl
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional

# --- Core Exceptions ---
class WorkflowError(Exception): pass
class RetryableError(WorkflowError): pass
class FatalError(WorkflowError): pass
class PreconditionFailedError(FatalError): pass
class LockAcquisitionError(FatalError): pass

# --- Directory Lock ---
class DirectoryLock:
    def __init__(self, directory: str):
        self.lock_path = os.path.join(directory, ".orchestrator.lock")
        self.lock_fd = None

    def acquire(self):
        self.lock_fd = open(self.lock_path, 'w')
        try:
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, IOError):
            raise LockAcquisitionError(f"Another instance is currently locking {self.lock_path}")

    def release(self):
        if self.lock_fd:
            fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
            self.lock_fd.close()
            self.lock_fd = None

# --- State ---
@dataclass
class WorkflowState:
    data: Dict[str, Any] = field(default_factory=dict)
    next_step_index: int = 0
    completed_steps: List[str] = field(default_factory=list)
    is_complete: bool = False
    run_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d-%H%M%S"))

# --- Atomic Checkpoint Store ---
class CheckpointStore:
    def __init__(self, directory: str):
        self.directory = directory
        os.makedirs(self.directory, exist_ok=True)
        self.primary_path = os.path.join(self.directory, "workflow_state.json")
        self.backup_path = self.primary_path + ".bak"

    def save(self, state: WorkflowState):
        # 1. Create backup of the current valid state before overwriting
        if os.path.exists(self.primary_path):
            shutil.copy2(self.primary_path, self.backup_path)
        
        # 2. Atomic Write with fsync
        temp_fd, temp_path = tempfile.mkstemp(dir=self.directory, prefix=".ckpt-tmp-")
        try:
            with os.fdopen(temp_fd, 'w') as f:
                json.dump(asdict(state), f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.rename(temp_path, self.primary_path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise FatalError(f"Atomic save failed: {e}")

    def load(self) -> WorkflowState:
        for path in [self.primary_path, self.backup_path]:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                    print(f"[STORE] Loaded state from {os.path.basename(path)}")
                    return WorkflowState(**data)
                except Exception as e:
                    print(f"[STORE] Warning: Failed to load {path}: {e}")
        return WorkflowState()

# --- Audit Logger ---
class AuditLogger:
    def __init__(self, directory: str):
        self.log_path = os.path.join(directory, "audit.log")
        os.makedirs(directory, exist_ok=True)

    def log(self, event_type: str, step_name: str, details: Dict[str, Any]):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "step": step_name,
            "details": details
        }
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(entry) + "\n")
            f.flush()

# --- Environment ---
class Environment:
    def __init__(self, audit_logger: AuditLogger):
        self.audit = audit_logger

    def run_command(self, cmd: str, step_name: str, timeout: int = 60) -> Dict[str, Any]:
        self.audit.log("CMD_START", step_name, {"cmd": cmd})
        start_time = time.monotonic()
        try:
            # os.setsid creates a new process group to allow killing child processes
            process = subprocess.Popen(
                cmd, shell=True, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                preexec_fn=os.setsid 
            )
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                duration = time.monotonic() - start_time
                res = {
                    "exit_code": process.returncode,
                    "stdout": stdout.strip(),
                    "stderr": stderr.strip(),
                    "duration": f"{duration:.2f}s"
                }
                self.audit.log("CMD_END", step_name, res)
                if process.returncode != 0:
                    raise RetryableError(f"Cmd failed ({process.returncode}): {res['stderr']}")
                return res
            except subprocess.TimeoutExpired:
                # Kill the entire process group
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                raise RetryableError(f"Command timed out after {timeout}s")
        except Exception as e:
            if not isinstance(e, RetryableError):
                self.audit.log("CMD_ERROR", step_name, {"error": str(e)})
            raise

# --- Step Interface ---
class ReconcilerStep:
    name: str = "base"

    def check_done(self, state: WorkflowState, env: Environment) -> bool:
        """Idempotency check: Is the system already in the desired state?"""
        return False

    def check_ready(self, state: WorkflowState, env: Environment) -> bool:
        """Precondition check: Is the environment ready for this step?"""
        return True

    def apply(self, state: WorkflowState, env: Environment) -> WorkflowState:
        """Action: Mutate the system to reach desired state."""
        return state

    def compensate(self, state: WorkflowState, env: Environment):
        """Rollback: Undo changes if a later fatal error occurs."""
        pass

# --- Orchestrator ---
class Orchestrator:
    def __init__(self, steps: List[ReconcilerStep], directory: str):
        self.steps = steps
        self.directory = directory
        self.audit = AuditLogger(directory)
        self.store = CheckpointStore(directory)
        self.env = Environment(self.audit)
        self.max_retries = 3
        self.lock = DirectoryLock(directory)

    def run(self):
        self.lock.acquire()
        try:
            print(f"--- [v2] Orchestrator Startup | RunID: {datetime.now().strftime('%H%M%S')} ---")
            state = self.store.load()
            
            if state.is_complete:
                print("[INFO] Workflow is already marked as complete.")
                return

            while state.next_step_index < len(self.steps):
                step = self.steps[state.next_step_index]
                print(f"\n[STEP] {step.name}")
                
                # 1. Reconciliation (Idempotency Check)
                try:
                    if step.check_done(state, self.env):
                        print(f"  [RECONCILED] Already in desired state. Skipping.")
                        state.next_step_index += 1
                        self.store.save(state)
                        continue
                except Exception as e:
                    print(f"  [ERROR] Reconcile failed for {step.name}: {e}")
                    # We don't fail here, we try to apply if reconcile is unsure

                # 2. Preconditions
                if not step.check_ready(state, self.env):
                    print(f"  [FATAL] Preconditions failed for {step.name}")
                    raise PreconditionFailedError(f"Step {step.name} blocked.")

                # 3. Apply with Retries
                attempt = 0
                success = False
                while attempt < self.max_retries and not success:
                    try:
                        self.audit.log("STEP_START", step.name, {"attempt": attempt})
                        state = step.apply(state, self.env)
                        success = True
                        self.audit.log("STEP_SUCCESS", step.name, {})
                    except RetryableError as e:
                        attempt += 1
                        print(f"  [RETRY {attempt}/{self.max_retries}] {e}")
                        if attempt < self.max_retries:
                            time.sleep(2)
                        else:
                            print(f"  [FATAL] Retries exhausted for {step.name}")
                            self.initiate_compensation(state)
                            raise
                    except Exception as e:
                        print(f"  [FATAL] Non-retryable error in {step.name}: {e}")
                        self.initiate_compensation(state)
                        raise

                # 4. Atomic Checkpoint
                state.completed_steps.append(step.name)
                state.next_step_index += 1
                if state.next_step_index == len(self.steps):
                    state.is_complete = True
                
                self.store.save(state)
                print(f"  [CHECKPOINT] Progress saved.")

            print("\n--- [v2] Workflow Successfully Completed ---")
        finally:
            self.lock.release()

    def initiate_compensation(self, state: WorkflowState):
        print("\n--- [COMPENSATION] Rolling back system changes ---")
        # Rollback completed steps in reverse order
        for i in range(state.next_step_index - 1, -1, -1):
            step = self.steps[i]
            print(f"  [UNDO] {step.name}")
            try:
                step.compensate(state, self.env)
            except Exception as e:
                print(f"    [ERROR] Failed to compensate {step.name}: {e}")
        print("--- [COMPENSATION] Finished ---")
