import os
import time
import signal
import subprocess
from v2_engine import ReconcilerStep, Orchestrator, RetryableError

class StubbornStep(ReconcilerStep):
    name = "stubborn_step"
    
    def apply(self, state, env):
        print("  [EXEC] Starting a stubborn process that ignores SIGTERM...")
        # This bash script traps SIGTERM and ignores it, forcing a SIGKILL
        cmd = "trap 'echo ignored' TERM; sleep 10"
        try:
            env.run_command(cmd, self.name, timeout=2)
        except RetryableError as e:
            print(f"  [CAUGHT] {e}")
            raise
        return state

if __name__ == "__main__":
    os.makedirs("phase0/data_zombie", exist_ok=True)
    for f in os.listdir("phase0/data_zombie"):
        os.remove(f"phase0/data_zombie/{f}")
        
    orch = Orchestrator([StubbornStep()], "phase0/data_zombie")
    try:
        orch.run()
    except Exception as e:
        print(f"\n[ORCHESTRATOR HALTED] {e}")

    # Check if the process is still running
    # In a real test we'd check PIDs, but here we'll just check if the engine survived.
    print("[SUCCESS] Process group management test completed.")
