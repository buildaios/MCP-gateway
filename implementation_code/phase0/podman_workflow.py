import os
import json
from v2_engine import ReconcilerStep, Orchestrator, WorkflowState, Environment, RetryableError, FatalError

# --- Podman Workflow Steps ---

class PodmanImagePullStep(ReconcilerStep):
    """Step 1: Pull a small, reliable image (Alpine)"""
    name = "podman_image_pull"
    image = "alpine:latest"

    def check_done(self, state, env):
        res = env.run_command(f"podman image inspect {self.image}", self.name)
        return res["exit_code"] == 0

    def apply(self, state, env):
        print(f"  [EXEC] Pulling image {self.image}...")
        # Use a longer timeout for image pulls
        env.run_command(f"podman pull {self.image}", self.name, timeout=180)
        return state

class PodmanContainerCreateStep(ReconcilerStep):
    """Step 2: Create and Start a Container"""
    name = "podman_container_create"
    image = "alpine:latest"
    container_name = "workflow-test-container"

    def check_done(self, state, env):
        # Check if container exists and is running
        res = env.run_command(f"podman ps --filter name={self.container_name} --format '{{{{.Status}}}}'", self.name)
        return "Up" in res["stdout"]

    def apply(self, state, env):
        print(f"  [EXEC] Creating and starting container {self.container_name}...")
        # Check if it exists but is stopped
        res = env.run_command(f"podman ps -a --filter name={self.container_name} --format '{{{{.Names}}}}'", self.name)
        if self.container_name in res["stdout"]:
            env.run_command(f"podman start {self.container_name}", self.name)
        else:
            env.run_command(f"podman run -d --name {self.container_name} {self.image} sleep 3600", self.name)
        return state

    def compensate(self, state, env):
        print(f"  [UNDO] Removing container {self.container_name}...")
        env.run_command(f"podman rm -f {self.container_name}", self.name)

class PodmanHealthCheckStep(ReconcilerStep):
    """Step 3: Verify the container is actually working"""
    name = "podman_health_check"
    container_name = "workflow-test-container"

    def apply(self, state, env):
        print(f"  [EXEC] Verifying container {self.container_name} health...")
        res = env.run_command(f"podman exec {self.container_name} uname -a", self.name)
        if "Linux" not in res["stdout"]:
            raise FatalError("Container health check failed: Unexpected OS output.")
        
        state.data["container_os"] = res["stdout"]
        print(f"  [SUCCESS] Container is healthy: {res['stdout']}")
        return state

# --- Main ---

if __name__ == "__main__":
    data_dir = "phase0/podman_data"
    os.makedirs(data_dir, exist_ok=True)
    
    steps = [
        PodmanImagePullStep(),
        PodmanContainerCreateStep(),
        PodmanHealthCheckStep()
    ]
    
    orchestrator = Orchestrator(steps, data_dir)
    orchestrator.run()
