import os
from v2_engine import WorkflowState, Environment, ReconcilerStep, Orchestrator, RetryableError

# --- Steps Implementation ---

class CheckPythonStep(ReconcilerStep):
    name = "check_python3"
    
    def check_done(self, state, env):
        res = env.run_command("python3 --version", self.name)
        if res["exit_code"] == 0:
            state.data["final_python"] = res["stdout"]
            return True
        return False

    def apply(self, state, env):
        res = env.run_command("python3 --version", self.name)
        state.data["final_python"] = res["stdout"]
        return state

class CheckGitStep(ReconcilerStep):
    name = "check_git"

    def check_done(self, state, env):
        res = env.run_command("git --version", self.name)
        if res["exit_code"] == 0:
            state.data["final_git"] = res["stdout"]
            return True
        return False

class InstallGitStep(ReconcilerStep):
    name = "install_git"

    def check_done(self, state, env):
        res = env.run_command("git --version", self.name)
        return res["exit_code"] == 0

    def apply(self, state, env):
        # In this environment, we'll try dnf but fallback to a mock success if it's already there
        # or if we are not root.
        res = env.run_command("dnf install -y git", self.name)
        if res["exit_code"] != 0:
            # If dnf fails due to permissions but git is already there, we are fine.
            # But check_done should have caught that.
            raise RetryableError(f"DNF failed: {res['stderr']}")
        return state

    def compensate(self, state, env):
        # Dangerous in real life, but for testing:
        # env.run_command("dnf remove -y git", self.name)
        print("  [MOCK] Uninstalling git...")

class VerifyVersionsStep(ReconcilerStep):
    name = "verify_versions"

    def apply(self, state, env):
        py_res = env.run_command("python3 --version", self.name)
        git_res = env.run_command("git --version", self.name)
        state.data["final_python"] = py_res["stdout"]
        state.data["final_git"] = git_res["stdout"]
        return state

class GenerateReportStep(ReconcilerStep):
    name = "generate_report"

    def check_done(self, state, env):
        return os.path.exists("phase0/data_v2/report_v2.txt")

    def apply(self, state, env):
        report = f"""Workflow v2 Report
------------------
Run ID: {state.run_id}
Python: {state.data.get('final_python', 'Unknown')}
Git: {state.data.get('final_git', 'Unknown')}
Status: Verified
"""
        with open("phase0/data_v2/report_v2.txt", "w") as f:
            f.write(report)
        return state

# --- Main ---

if __name__ == "__main__":
    steps = [
        CheckPythonStep(),
        CheckGitStep(),
        InstallGitStep(),
        VerifyVersionsStep(),
        GenerateReportStep()
    ]
    
    # Ensure data directory exists
    os.makedirs("phase0/data_v2", exist_ok=True)
    
    orchestrator = Orchestrator(steps, "phase0/data_v2")
    orchestrator.run()
