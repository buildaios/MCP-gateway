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

class SuspendIntent(Exception):
    def __init__(self, condition_type: str, target: str):
        self.condition_type = condition_type # "file" or "timer"
        self.target = target

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
    status: str = "RUNNING" # "RUNNING", "SUSPENDED", "COMPLETE"
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
        if os.path.exists(self.primary_path):
            shutil.copy2(self.primary_path, self.backup_path)
        
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
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                raise RetryableError(f"Command timed out after {timeout}s")
        except Exception as e:
            if not isinstance(e, RetryableError):
                self.audit.log("CMD_ERROR", step_name, {"error": str(e)})
            raise

# --- Step Interface ---
class ReconcilerStep:
    name: str = "base"
    def check_done(self, state: WorkflowState, env: Environment) -> bool: return False
    def check_ready(self, state: WorkflowState, env: Environment) -> bool: return True
    def apply(self, state: WorkflowState, env: Environment) -> WorkflowState: return state
    def compensate(self, state: WorkflowState, env: Environment): pass

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

    def run(self, is_resume=False):
        self.lock.acquire()
        try:
            print(f"--- [v3] Orchestrator {'Resuming' if is_resume else 'Startup'} | RunID: {datetime.now().strftime('%H%M%S')} ---")
            state = self.store.load()
            
            if state.is_complete:
                print("[INFO] Workflow is already marked as complete.")
                return

            if state.status == "SUSPENDED" and not is_resume:
                print("[INFO] Workflow is suspended. Use --resume to force check.")
                return
            
            state.status = "RUNNING"

            while state.next_step_index < len(self.steps):
                step = self.steps[state.next_step_index]
                print(f"\n[STEP] {step.name}")
                
                try:
                    if step.check_done(state, self.env):
                        print(f"  [RECONCILED] Already in desired state. Skipping.")
                        state.next_step_index += 1
                        self.store.save(state)
                        continue
                except Exception as e:
                    print(f"  [ERROR] Reconcile failed for {step.name}: {e}")

                if not step.check_ready(state, self.env):
                    print(f"  [FATAL] Preconditions failed for {step.name}")
                    raise PreconditionFailedError(f"Step {step.name} blocked.")

                attempt = 0
                success = False
                while attempt < self.max_retries and not success:
                    try:
                        self.audit.log("STEP_START", step.name, {"attempt": attempt})
                        state = step.apply(state, self.env)
                        success = True
                        self.audit.log("STEP_SUCCESS", step.name, {})
                    except SuspendIntent as si:
                        self.audit.log("STEP_SUSPEND", step.name, {"type": si.condition_type, "target": si.target})
                        state.status = "SUSPENDED"
                        self.store.save(state)
                        self.register_wakeup(state, si)
                        print(f"  [SUSPENDED] Process exiting. Waiting for {si.condition_type}: {si.target}")
                        sys.exit(0)
                    except RetryableError as e:
                        attempt += 1
                        print(f"  [RETRY {attempt}/{self.max_retries}] {e}")
                        if attempt < self.max_retries:
                            time.sleep(2)
                        else:
                            self.initiate_compensation(state)
                            raise
                    except Exception as e:
                        print(f"  [FATAL] Non-retryable error in {step.name}: {e}")
                        self.initiate_compensation(state)
                        raise

                state.completed_steps.append(step.name)
                state.next_step_index += 1
                if state.next_step_index == len(self.steps):
                    state.is_complete = True
                
                self.store.save(state)
                print(f"  [CHECKPOINT] Progress saved.")

            print("\n--- [v3] Workflow Successfully Completed ---")
        finally:
            self.lock.release()

    def register_wakeup(self, state, si: SuspendIntent):
        unit_name = f"wf-wake-{state.run_id}"
        script_path = os.path.abspath(sys.argv[0])
        # Note: --resume is handled by the workflow script's main
        resume_cmd = f"{sys.executable} {script_path} --resume"
        
        srun_base = ["systemd-run", "--user", f"--unit={unit_name}", "--remain-after-exit"]
        
        if si.condition_type == "file":
            target_path = os.path.abspath(si.target)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            srun_cmd = srun_base + [f"--path-property=PathExists={target_path}", "sh", "-c", resume_cmd]
        elif si.condition_type == "timer":
            srun_cmd = srun_base + [f"--on-active={si.target}", "sh", "-c", resume_cmd]
        else:
            return

        print(f"  [SYSTEMD] Registering wake-up: {' '.join(srun_cmd)}")
        try:
            subprocess.run(srun_cmd, check=True, capture_output=True)
        except Exception as e:
            print(f"  [ERROR] Failed to register systemd wake-up: {e}")

    def initiate_compensation(self, state: WorkflowState):
        print("\n--- [COMPENSATION] Rolling back system changes ---")
        for i in range(state.next_step_index - 1, -1, -1):
            step = self.steps[i]
            print(f"  [UNDO] {step.name}")
            try:
                step.compensate(state, self.env)
            except Exception as e:
                print(f"    [ERROR] Failed to compensate {step.name}: {e}")
        print("--- [COMPENSATION] Finished ---")
