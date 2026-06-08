import os
import sys
import shutil
from unittest.mock import patch
from v2_engine import ReconcilerStep, Orchestrator, FatalError, WorkflowState, CheckpointStore

class WriteStep(ReconcilerStep):
    name = "write_step"
    def apply(self, state, env):
        print("  [EXEC] Updating state to version 2...")
        state.data["version"] = 2
        return state

def mock_rename_failure(src, dst):
    raise OSError("[Errno 28] No space left on device")

if __name__ == "__main__":
    os.makedirs("phase0/data_atomic", exist_ok=True)
    for f in os.listdir("phase0/data_atomic"):
        os.remove(f"phase0/data_atomic/{f}")
        
    # Pre-seed a valid version 1 checkpoint
    store = CheckpointStore("phase0/data_atomic")
    initial_state = WorkflowState(data={"version": 1})
    store.save(initial_state)
    print("Initial state saved with version 1.")
    
    orch = Orchestrator([WriteStep()], "phase0/data_atomic")
    
    with patch('os.rename', side_effect=mock_rename_failure):
        try:
            orch.run()
        except Exception as e:
            print(f"\n[CRASHED AS EXPECTED] {e}")
            
    # Verification: Read the state back. It should still be version 1, not corrupted.
    final_state = store.load()
    print(f"Final state version: {final_state.data.get('version')}")
    if final_state.data.get("version") == 1:
        print("[SUCCESS] Original checkpoint was protected from atomic failure.")
    else:
        print("[FAILURE] State was mutated or corrupted!")
