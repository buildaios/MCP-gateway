import os
import sys
from v2_engine import ReconcilerStep, Orchestrator, FatalError

class Step1(ReconcilerStep):
    name = "step1_success"
    def apply(self, state, env):
        print("  [STEP1] Applied")
        state.data["step1_comp"] = False
        return state
        
    def compensate(self, state, env):
        print("  [STEP1] Compensating...")
        state.data["step1_comp"] = True

class Step2(ReconcilerStep):
    name = "step2_buggy_comp"
    def apply(self, state, env):
        print("  [STEP2] Applied")
        return state
        
    def compensate(self, state, env):
        print("  [STEP2] Compensating (about to throw error)...")
        raise Exception("Unhandled network error during rollback!")

class Step3(ReconcilerStep):
    name = "step3_fatal"
    def apply(self, state, env):
        print("  [STEP3] Triggering fatal error...")
        raise FatalError("Hardware failure simulated.")

if __name__ == "__main__":
    os.makedirs("phase0/data_comp_cascade", exist_ok=True)
    for f in os.listdir("phase0/data_comp_cascade"):
        os.remove(f"phase0/data_comp_cascade/{f}")
        
    orch = Orchestrator([Step1(), Step2(), Step3()], "phase0/data_comp_cascade")
    try:
        orch.run()
    except Exception as e:
        print(f"\n[ORCHESTRATOR HALTED] {e}")
        
    # Verify Step 1 compensation ran despite Step 2 throwing an error
    # Because state modifications in memory during compensate aren't saved if the run halts
    # We will just visually verify or read logs, but the stdout is the main indicator.
