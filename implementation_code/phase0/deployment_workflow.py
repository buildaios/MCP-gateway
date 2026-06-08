import os
import time
import signal
import shutil
from v2_engine import ReconcilerStep, Orchestrator, WorkflowState, Environment, RetryableError, FatalError

# --- Real World Steps ---

class AtomicMotdStep(ReconcilerStep):
    """Workflow #2: Atomic Configuration Update"""
    name = "atomic_motd_update"
    target = "phase0/deploy_data/motd"
    desired_content = "WELCOME TO SECURE FEDORA AI OS\nAUTHORIZED ACCESS ONLY\n"

    def check_done(self, state, env):
        if os.path.exists(self.target):
            with open(self.target, 'r') as f:
                return f.read() == self.desired_content
        return False

    def apply(self, state, env):
        print(f"  [EXEC] Atomically updating {self.target}...")
        os.makedirs(os.path.dirname(self.target), exist_ok=True)
        # We use a temp file and rename to ensure atomicity even for the target file
        tmp_target = self.target + ".tmp"
        with open(tmp_target, 'w') as f:
            f.write(self.desired_content)
        os.rename(tmp_target, self.target)
        return state

class GitMirrorStep(ReconcilerStep):
    """Workflow #1: Git Repository Mirroring (Simulated with local repo)"""
    name = "git_repo_mirror"
    target_dir = "phase0/deploy_data/local-mirror"

    def check_done(self, state, env):
        return os.path.exists(os.path.join(self.target_dir, ".git"))

    def apply(self, state, env):
        print("  [EXEC] Creating local simulated git mirror...")
        if os.path.exists(self.target_dir):
            shutil.rmtree(self.target_dir)
        
        # Create a local source repo and clone from it
        src_repo = "phase0/deploy_data/local-src"
        if not os.path.exists(src_repo):
            os.makedirs(src_repo)
            # Configure local identity to avoid global config issues
            env.run_command(f"cd {src_repo} && git init && git config user.email 'test@example.com' && git config user.name 'Test' && touch file.txt && git add . && git commit -m 'initial'", self.name)
            
        env.run_command(f"git clone {src_repo} {self.target_dir}", self.name)
        return state

class MonitorDaemonStep(ReconcilerStep):
    """Workflow #3: Service Daemon Lifecycle (Simulated)"""
    name = "monitor_daemon_setup"
    pid_file = "phase0/deploy_data/monitor.pid"
    
    def check_done(self, state, env):
        # Check if the PID file exists and the process is alive
        if os.path.exists(self.pid_file):
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            try:
                os.kill(pid, 0) # Check if process exists
                return True
            except OSError:
                return False
        return False

    def apply(self, state, env):
        print("  [EXEC] Starting monitor daemon...")
        # Start a background "daemon" that just sleeps and logs
        # We use setsid to ensure it's a true background process
        cmd = f"nohup sh -c 'echo $$ > {self.pid_file} && while true; do date >> phase0/deploy_data/monitor.log; sleep 10; done' > /dev/null 2>&1 &"
        env.run_command(cmd, self.name)
        return state

    def compensate(self, state, env):
        if os.path.exists(self.pid_file):
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            print(f"  [UNDO] Killing monitor daemon (PID: {pid})...")
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
            os.remove(self.pid_file)

class HealthCheckStep(ReconcilerStep):
    """Final Verification Stage"""
    name = "system_health_check"

    def apply(self, state, env):
        print("  [EXEC] Performing system health checks...")
        # 1. Verify MOTD
        with open("phase0/deploy_data/motd", 'r') as f:
            if "SECURE" not in f.read():
                raise FatalError("MOTD verification failed.")
        
        # 2. Verify Git repo
        res = env.run_command(f"cd phase0/deploy_data/local-mirror && git log -1", self.name)
        if res["exit_code"] != 0:
            raise FatalError("Git repo verification failed.")
            
        print("  [SUCCESS] All health checks passed.")
        return state

# --- Main ---

if __name__ == "__main__":
    deploy_dir = "phase0/deploy_data"
    os.makedirs(deploy_dir, exist_ok=True)
    
    steps = [
        AtomicMotdStep(),
        GitMirrorStep(),
        MonitorDaemonStep(),
        HealthCheckStep()
    ]
    
    orchestrator = Orchestrator(steps, deploy_dir)
    orchestrator.run()
