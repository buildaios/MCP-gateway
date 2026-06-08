import os
import json
import time
import subprocess
from datetime import datetime
from dataclasses import dataclass, asdict

# --- State Definition ---
@dataclass
class WorkflowState:
    python3_installed: bool = False
    git_installed: bool = False
    python3_version: str = ""
    git_version: str = ""
    report_generated: bool = False
    next_step: str = "step1_check_python3"
    crash_simulated: bool = False

# --- I/O Abstraction ---
class Environment:
    def __init__(self, workspace_dir="phase0/data"):
        self.workspace_dir = workspace_dir
        os.makedirs(self.workspace_dir, exist_ok=True)
    
    def write_file(self, filename, content, mode="w"):
        path = os.path.join(self.workspace_dir, filename)
        with open(path, mode) as f:
            f.write(content)
            
    def run_command(self, cmd: str):
        print(f"  [EXEC] {cmd}")
        result = subprocess.run(
            cmd, shell=True, text=True, capture_output=True
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }

class CheckpointStore:
    def __init__(self, directory="phase0/data"):
        self.directory = directory
        os.makedirs(self.directory, exist_ok=True)
    
    def get_path(self, step_name):
        return os.path.join(self.directory, f"{step_name}.ckpt")
    
    def is_completed(self, step_name):
        return os.path.exists(self.get_path(step_name))
    
    def mark_completed(self, step_name, result, state):
        ckpt_data = {
            "step_id": step_name,
            "timestamp": datetime.now().isoformat(),
            "result": result,
            "state": asdict(state)
        }
        with open(self.get_path(step_name), 'w') as f:
            json.dump(ckpt_data, f, indent=2)
        print(f"[CHECKPOINT] Saved for {step_name}")

    def load_latest_state(self, steps_order):
        latest_state = WorkflowState()
        last_step = None
        for step in steps_order:
            path = self.get_path(step)
            if os.path.exists(path):
                with open(path, 'r') as f:
                    data = json.load(f)
                    latest_state = WorkflowState(**data["state"])
                    last_step = step
            else:
                break
        return latest_state, last_step

# --- Workflow Steps ---

def step1_check_python3(state: WorkflowState, env: Environment):
    res = env.run_command("python3 --version")
    state.python3_installed = (res["exit_code"] == 0)
    state.next_step = "step2_check_git"
    return "Python3 checked", state

def step2_check_git(state: WorkflowState, env: Environment):
    res = env.run_command("git --version")
    state.git_installed = (res["exit_code"] == 0)
    state.next_step = "step3_install_packages"
    return "Git checked", state

def step3_install_packages(state: WorkflowState, env: Environment):
    if not state.git_installed:
        # In a real Fedora container, we'd use dnf. 
        # For this simulation, we'll just mock it or try it if we have permissions.
        res = env.run_command("dnf install -y git")
        if res["exit_code"] == 0:
            state.git_installed = True
            result_msg = "Git installed successfully"
        else:
            result_msg = f"Failed to install git: {res['stderr']}"
    else:
        result_msg = "Git already installed, skipping"
    
    state.next_step = "step4_verify_versions"
    return result_msg, state

def step4_verify_versions(state: WorkflowState, env: Environment):
    py_res = env.run_command("python3 --version")
    git_res = env.run_command("git --version")
    state.python3_version = py_res["stdout"]
    state.git_version = git_res["stdout"]
    state.next_step = "step5_generate_report"
    return f"Versions verified: PY={state.python3_version}, GIT={state.git_version}", state

def step5_generate_report(state: WorkflowState, env: Environment):
    report = f"""Workflow Report
---------------
Timestamp: {datetime.now().isoformat()}
Python3 Version: {state.python3_version}
Git Version: {state.git_version}
Status: Completed Successfully
"""
    env.write_file("report.txt", report)
    state.report_generated = True
    state.next_step = "END"
    return "Report generated", state

# --- Orchestrator ---

def run_workflow():
    env = Environment("phase0/data")
    store = CheckpointStore("phase0/data")
    
    steps_order = [
        "step1_check_python3",
        "step2_check_git",
        "step3_install_packages",
        "step4_verify_versions",
        "step5_generate_report"
    ]
    
    steps_impl = {
        "step1_check_python3": step1_check_python3,
        "step2_check_git": step2_check_git,
        "step3_install_packages": step3_install_packages,
        "step4_verify_versions": step4_verify_versions,
        "step5_generate_report": step5_generate_report
    }

    print("--- Initializing Workflow ---")
    state, last_completed_step = store.load_latest_state(steps_order)
    
    if last_completed_step:
        print(f"[RECOVERY] Resuming from after {last_completed_step}")
    else:
        print("[INFO] Starting fresh workflow run")

    while state.next_step != "END":
        current_step = state.next_step
        print(f"\n[RUNNING] {current_step}...")
        
        # Execute the step
        action = steps_impl[current_step]
        result_msg, state = action(state, env)
        
        # Save checkpoint
        store.mark_completed(current_step, result_msg, state)
        print(f"[SUCCESS] {result_msg}")

        # Crash Simulation
        if current_step == "step3_install_packages" and not state.crash_simulated:
            print("[CRASH SIMULATION] Deliberately terminating execution...")
            state.crash_simulated = True
            # We need to persist that we CRASHED but AFTER saving the checkpoint for step 3.
            # Actually, the requirement says "After completing the package installation step, deliberately terminate".
            # So step 3 checkpoint IS saved, then we crash.
            # Next run will load state with next_step="step4_verify_versions".
            raise Exception("Simulated system crash after package installation.")

    print("\n--- Workflow Completed ---")
    print(f"Final Summary: Report generated at data/report.txt")
    print(f"State: {state}")

if __name__ == "__main__":
    run_workflow()
