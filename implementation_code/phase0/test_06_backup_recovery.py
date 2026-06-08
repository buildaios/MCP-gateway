import os
import json
import shutil
from v2_engine import WorkflowState, CheckpointStore, FatalError

def test_backup_recovery():
    print("--- [PHASE 1] Testing Schema Integrity & Backup Recovery ---")
    data_dir = "phase0/data_backup_test"
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
    os.makedirs(data_dir)

    store = CheckpointStore(data_dir)
    
    # 1. Save an initial valid state (this creates the primary)
    state_v1 = WorkflowState(data={"version": 1})
    store.save(state_v1)
    print("  [STEP 1] Saved Version 1.")

    # 2. Save a second valid state (this moves v1 to .bak and creates a new primary v2)
    state_v2 = WorkflowState(data={"version": 2})
    store.save(state_v2)
    print("  [STEP 2] Saved Version 2 (v1 is now in .bak).")

    # 3. Manually corrupt the primary v2 file
    with open(store.primary_path, 'w') as f:
        f.write("{ CORRUPTED JSON ...")
    print("  [STEP 3] Manually corrupted the primary checkpoint.")

    # 4. Attempt to load. It should fallback to .bak (Version 1)
    recovered_state = store.load()
    print(f"  [STEP 4] Loaded state version: {recovered_state.data.get('version')}")

    if recovered_state.data.get("version") == 1:
        print("[SUCCESS] Engine successfully fell back to the .bak checkpoint.")
    else:
        print(f"[FAILURE] Engine failed to recover correctly. Version: {recovered_state.data.get('version')}")
        exit(1)

if __name__ == "__main__":
    test_backup_recovery()
