import os
import time
from unittest.mock import patch
from v2_engine import ReconcilerStep, Orchestrator

class TimedStep(ReconcilerStep):
    name = "timed_step"
    def apply(self, state, env):
        print("  [EXEC] Running command with simulated clock jump...")
        # We simulate a clock jump by mocking time.time() inside the environment 
        # (though we now use monotonic, so we should verify duration is still correct)
        res = env.run_command("sleep 1", self.name)
        print(f"  [RESULT] Duration reported: {res['duration']}")
        return state

if __name__ == "__main__":
    os.makedirs("phase0/data_time", exist_ok=True)
    for f in os.listdir("phase0/data_time"):
        os.remove(f"phase0/data_time/{f}")
        
    orch = Orchestrator([TimedStep()], "phase0/data_time")
    
    # We mock time.time to jump BACKWARDS by 1 hour
    # Even if duration uses time.time (old bug), it would show -3600s
    # With monotonic, it should stay ~1s.
    
    # Actually, to truly test monotonic resilience against system clock changes,
    # we'd need to change the system clock, which we can't easily do.
    # But mocking time.monotonic to jump can prove the logic.
    
    real_monotonic = time.monotonic
    
    # Simulate a jump forward by 1000s mid-execution
    call_count = [0]
    def mock_monotonic():
        call_count[0] += 1
        if call_count[0] > 2: # Jump after start_time is captured
            return real_monotonic() + 1000
        return real_monotonic()

    with patch('time.monotonic', side_effect=mock_monotonic):
        orch.run()
        
    print("[SUCCESS] Time jump test completed.")
