import os
import sys
import time
import subprocess
from v2_engine import ReconcilerStep, Orchestrator

class SlowStep(ReconcilerStep):
    name = "slow_step"

    def apply(self, state, env):
        print(f"  [{os.getpid()}] Starting work...")
        time.sleep(2)
        print(f"  [{os.getpid()}] Finished work.")
        return state

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "worker":
        # This is the worker process
        steps = [SlowStep(), SlowStep()]
        orch = Orchestrator(steps, "phase0/data_split_brain")
        try:
            orch.run()
        except Exception as e:
            print(f"[{os.getpid()}] Orchestrator failed: {e}")
    else:
        # This is the test runner
        os.makedirs("phase0/data_split_brain", exist_ok=True)
        # Clean previous state
        for f in os.listdir("phase0/data_split_brain"):
            os.remove(f"phase0/data_split_brain/{f}")
        
        print("Starting two concurrent orchestrators...")
        p1 = subprocess.Popen([sys.executable, __file__, "worker"])
        p2 = subprocess.Popen([sys.executable, __file__, "worker"])
        
        p1.wait()
        p2.wait()
        
        print("\n--- Test Complete ---")
        if os.path.exists("phase0/data_split_brain/audit.log"):
            with open("phase0/data_split_brain/audit.log", 'r') as f:
                logs = f.readlines()
            print(f"Total audit log entries: {len(logs)}")
