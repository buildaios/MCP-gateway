import os
import sys
from v3_engine import ReconcilerStep, Orchestrator, SuspendIntent

# --- Steps Implementation ---

class MockInstallStep(ReconcilerStep):
    name = "mock_install"
    path = "phase0/v3_data/installed.txt"

    def check_done(self, state, env):
        return os.path.exists(self.path)

    def apply(self, state, env):
        print("  [EXEC] Mocking installation...")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            f.write("installed")
        return state

class WaitForApprovalStep(ReconcilerStep):
    name = "wait_for_approval"
    approval_file = "phase0/v3_data/approval.sig"

    def check_done(self, state, env):
        return os.path.exists(self.approval_file)

    def apply(self, state, env):
        # We raise SuspendIntent to tell the engine to go to sleep
        raise SuspendIntent("file", self.approval_file)

class VerifyStep(ReconcilerStep):
    name = "final_verify"
    
    def apply(self, state, env):
        print("  [EXEC] Final verification of system state...")
        if not os.path.exists("phase0/v3_data/installed.txt"):
            raise Exception("Verification failed: install artifact missing.")
        if not os.path.exists("phase0/v3_data/approval.sig"):
            raise Exception("Verification failed: approval signature missing.")
        print("  [SUCCESS] All systems verified.")
        return state

# --- Main ---

if __name__ == "__main__":
    data_dir = "phase0/v3_data"
    os.makedirs(data_dir, exist_ok=True)
    
    steps = [
        MockInstallStep(),
        WaitForApprovalStep(),
        VerifyStep()
    ]
    
    orchestrator = Orchestrator(steps, data_dir)
    
    # Simple CLI argument handling
    is_resume = "--resume" in sys.argv
    orchestrator.run(is_resume=is_resume)
