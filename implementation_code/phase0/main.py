import os
import json
import time
import copy
import subprocess
from dataclasses import dataclass, asdict

# --- State Definition ---
@dataclass
class WorkflowState:
    step1_id: str = None
    step2_status: str = None
    system_info: str = None
    final: bool = False
    next_step: str = "step1_create_file" # Initial routing state

# --- I/O Abstraction ---
class Environment:
    def __init__(self, workspace_dir="data"):
        self.workspace_dir = workspace_dir
        os.makedirs(self.workspace_dir, exist_ok=True)
    
    def write_file(self, filename, content, mode="w"):
        path = os.path.join(self.workspace_dir, filename)
        with open(path, mode) as f:
            f.write(content)
            
    def read_file(self, filename):
        path = os.path.join(self.workspace_dir, filename)
        with open(path, "r") as f:
            return f.read()

    def run_command(self, cmd: str):
        result = subprocess.run(
            cmd, shell=True, text=True, capture_output=True, cwd=self.workspace_dir
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }

class CheckpointStore:
    def __init__(self, directory="data"):
        self.directory = directory
        os.makedirs(self.directory, exist_ok=True)
    
    def get_path(self, step_name):
        return os.path.join(self.directory, f"{step_name}.ckpt")
    
    def is_completed(self, step_name, expected_artifacts=None):
        if not os.path.exists(self.get_path(step_name)):
            return False
            
        if expected_artifacts:
            for artifact in expected_artifacts:
                if not os.path.exists(artifact):
                    print(f"[WARNING] Checkpoint exists for {step_name}, but artifact {artifact} is missing. Re-running.")
                    return False
        return True
    
    def mark_completed(self, step_name, data):
        with open(self.get_path(step_name), 'w') as f:
            json.dump(data, f)

class WorkflowStep:
    def __init__(self, name, action, expected_artifacts=None, max_retries=0):
        self.name = name
        self.action = action
        self.expected_artifacts = expected_artifacts or []
        self.max_retries = max_retries

def run_pipeline(steps_dict, store, env: Environment, initial_state: WorkflowState):
    print("Starting pipeline execution...\n")
    state = initial_state
    cache_broken = False
    
    while state.next_step != "END":
        step_name = state.next_step
        
        if step_name not in steps_dict:
            raise KeyError(f"Attempted to route to unknown step: {step_name}")
            
        step = steps_dict[step_name]
        checkpoint_path = store.get_path(step_name)
        
        if not cache_broken and store.is_completed(step_name, step.expected_artifacts):
            print(f"[RECOVERED] {step_name}: skipping, already completed")
            with open(checkpoint_path, 'r') as f:
                ckpt_data = json.load(f)
                state = WorkflowState(**ckpt_data.get("state", {}))
            continue
        
        cache_broken = True
        
        print(f"[RUNNING] {step_name}...")
        
        # Execute the action with retry logic
        retries = 0
        success = False
        while retries <= step.max_retries and not success:
            try:
                isolated_state = copy.deepcopy(state)
                # Inject both state and environment
                new_state = step.action(isolated_state, env)
                state = new_state
                success = True
            except Exception as e:
                retries += 1
                if retries <= step.max_retries:
                    print(f"  [RETRY {retries}/{step.max_retries}] {step_name} failed with: {e}")
                    time.sleep(1) # Small backoff
                else:
                    print(f"  [FATAL] {step_name} exhausted retries. Pipeline halting.")
                    raise e
        
        # Save checkpoint immediately after success
        store.mark_completed(step_name, {"status": "success", "state": asdict(state)})
        print(f"[SAVED] {step_name}: step completed\n")
    
    print(f"Pipeline finished successfully. Final State: {state}")

# --- Actions ---
def step1_action(state: WorkflowState, env: Environment):
    env.write_file("test_output.txt", "Hello from Step 1!")
    state.step1_id = "id_12345"
    state.next_step = "step2_simulate_crash"
    return state

fail_count = 0
def step2_action(state: WorkflowState, env: Environment):
    global fail_count
    
    # Mutate state BEFORE crash
    state.step2_status = f"polluted_attempt_{fail_count}"
    
    if fail_count < 2:
        fail_count += 1
        raise Exception(f"Simulated transient network timeout! State is: {state.step2_status}")

    step1_id = state.step1_id or "UNKNOWN"
    env.write_file("test_output.txt", f"\nAnd hello from Step 2! (Using ID: {step1_id})", mode="a")
    state.step2_status = "appended_cleanly"
    state.next_step = "step3_final"
    return state

def step3_action(state: WorkflowState, env: Environment):
    state.final = True
    state.next_step = "step4_system_info"
    return state

def step4_system_info(state: WorkflowState, env: Environment):
    print("  [EXEC] Running 'uname -a'")
    result = env.run_command("uname -a")
    
    if result["exit_code"] != 0:
        raise Exception(f"Command failed: {result['stderr']}")
        
    state.system_info = result["stdout"]
    env.write_file("system_info.txt", result["stdout"])
    
    state.next_step = "END" # Terminal state
    return state

# --- Main ---
if __name__ == "__main__":
    store = CheckpointStore("data")
    env = Environment("data")
    
    # Define our pipeline as a dictionary for routing
    steps_dict = {
        "step1_create_file": WorkflowStep("step1_create_file", step1_action, expected_artifacts=["data/test_output.txt"]),
        "step2_simulate_crash": WorkflowStep("step2_simulate_crash", step2_action, expected_artifacts=["data/test_output.txt"], max_retries=3),
        "step3_final": WorkflowStep("step3_final", step3_action),
        "step4_system_info": WorkflowStep("step4_system_info", step4_system_info, expected_artifacts=["data/system_info.txt"])
    }
    
    initial_state = WorkflowState()
    run_pipeline(steps_dict, store, env, initial_state)
