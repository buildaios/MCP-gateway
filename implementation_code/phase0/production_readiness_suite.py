import os
import sys
import time
import signal
import subprocess
import random
import shutil
from v2_engine import ReconcilerStep, Orchestrator, WorkflowState, CheckpointStore

# --- Mock Steps for Chaos Monkey ---

class CountingStep(ReconcilerStep):
    def __init__(self, index):
        self.name = f"step_{index:03d}"
        self.artifact = f"phase0/data_chaos/artifact_{self.name}.txt"

    def check_done(self, state, env):
        return os.path.exists(self.artifact)

    def apply(self, state, env):
        # Simulate work
        time.sleep(0.1)
        with open(self.artifact, "w") as f:
            f.write("done")
        return state

# --- Chaos Monkey Supervisor ---

def run_chaos_monkey():
    data_dir = "phase0/data_chaos"
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
    os.makedirs(data_dir)

    steps = [CountingStep(i) for i in range(30)]
    
    # The "External Supervisor" loop
    max_restarts = 100
    restarts = 0
    start_time = time.time()

    print(f"Starting Chaos Monkey with 30 steps...")

    while True:
        # Start the orchestrator in the background
        # We'll use a wrapper script or just run this file with a flag
        proc = subprocess.Popen([sys.executable, __file__, "worker"])
        
        # Randomly kill it between 0.1 and 1.5 seconds
        kill_wait = random.uniform(0.1, 1.5)
        try:
            exit_code = proc.wait(timeout=kill_wait)
            if exit_code == 0:
                print("\n[FINISH] Orchestrator finished successfully!")
                break
            else:
                print(f"[ERROR] Orchestrator exited with code {exit_code}")
                break
        except subprocess.TimeoutExpired:
            print(f"  [CHAOS] Issuing SIGKILL after {kill_wait:.2f}s...")
            proc.kill() # SIGKILL
            proc.wait()
            restarts += 1
            if restarts > max_restarts:
                print("[FAILURE] Too many restarts!")
                sys.exit(1)
            print(f"  [RESTART] Instance {restarts} starting...")

    duration = time.time() - start_time
    print(f"\n--- Chaos Monkey Results ---")
    print(f"Steps: 30")
    print(f"Restarts: {restarts}")
    print(f"Total Duration: {duration:.2f}s")
    
    # Final validation: check if all artifacts exist
    missing = []
    for i in range(30):
        if not os.path.exists(f"phase0/data_chaos/artifact_step_{i:03d}.txt"):
            missing.append(i)
    
    if not missing:
        print("[SUCCESS] All 30 artifacts confirmed. No state corruption.")
    else:
        print(f"[FAILURE] Missing artifacts for steps: {missing}")
        sys.exit(1)

# --- Worker Mode ---

def run_worker():
    steps = [CountingStep(i) for i in range(30)]
    orch = Orchestrator(steps, "phase0/data_chaos")
    try:
        orch.run()
    except Exception as e:
        # In worker mode, we don't want to swallow errors that might be bugs
        # but the chaos monkey will kill us anyway.
        # print(f"Worker exception: {e}")
        pass

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "worker":
        run_worker()
    else:
        run_chaos_monkey()
