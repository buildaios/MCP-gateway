import os
import time
import signal
import subprocess
from v2_engine import WorkflowState, Environment, ReconcilerStep, Orchestrator, RetryableError, FatalError

class ZombieStep(ReconcilerStep):
    name = "zombie_lock"

    def check_done(self, state, env):
        # We check if the "final_artifact" exists
        return os.path.exists("phase0/data_v2/zombie_final.txt")

    def apply(self, state, env):
        # Create a "lock" file and sleep
        lock_file = "phase0/data_v2/zombie.lock"
        if os.path.exists(lock_file):
            print(f"  [DEBUG] Lock file {lock_file} exists. Resource busy!")
            # In real life, we'd check if the PID in the lock is alive
            raise RetryableError("Resource locked by another process.")
        
        # Simulate long running process that creates a lock
        # We use a background shell command that creates a file and sleeps
        cmd = f"echo $PPID > {lock_file} && sleep 60 && echo 'done' > phase0/data_v2/zombie_final.txt && rm {lock_file}"
        print("  [EXEC] Starting zombie process...")
        env.run_command(cmd, self.name, timeout=5) # This will timeout!
        return state

class DriftStep(ReconcilerStep):
    name = "drift_reconcile"
    
    def check_done(self, state, env):
        # Desired state: file contains "authorized"
        path = "phase0/data_v2/config.txt"
        if os.path.exists(path):
            with open(path, 'r') as f:
                return "authorized" in f.read()
        return False

    def apply(self, state, env):
        print("  [EXEC] Writing config...")
        with open("phase0/data_v2/config.txt", "w") as f:
            f.write("authorized")
        return state

if __name__ == "__main__":
    steps = [ZombieStep(), DriftStep()]
    os.makedirs("phase0/data_v2", exist_ok=True)
    
    # We'll run this script in a way that we can kill it
    orchestrator = Orchestrator(steps, "phase0/data_v2")
    try:
        orchestrator.run()
    except Exception as e:
        print(f"\n[CRASHED AS EXPECTED] {e}")
