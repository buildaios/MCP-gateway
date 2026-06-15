from typing import Dict, Any, List
from pydantic import BaseModel
from mcp_gateway.audit import audit_logger

class TrustLevel:
    TRUST_0 = 0  # Read-only (Silent)
    TRUST_1 = 1  # Notification + undo
    TRUST_2 = 2  # Confirm/deny
    TRUST_3 = 3  # Modal approval

class TrustPolicy(BaseModel):
    tool_prefix: str
    required_trust_level: int
    requires_approval: bool = False

# Baseline policies for Fedora AI OS
DEFAULT_POLICIES = [
    # Read operations default to TRUST_0
    TrustPolicy(tool_prefix="linux.read", required_trust_level=TrustLevel.TRUST_0),
    TrustPolicy(tool_prefix="linux.get", required_trust_level=TrustLevel.TRUST_0),
    TrustPolicy(tool_prefix="github.read", required_trust_level=TrustLevel.TRUST_0),
    TrustPolicy(tool_prefix="docs2db.query", required_trust_level=TrustLevel.TRUST_0),
    
    # Mutating operations require elevated trust
    TrustPolicy(tool_prefix="linux.create", required_trust_level=TrustLevel.TRUST_1),
    TrustPolicy(tool_prefix="system.modify", required_trust_level=TrustLevel.TRUST_2, requires_approval=True),
    TrustPolicy(tool_prefix="system.install", required_trust_level=TrustLevel.TRUST_3, requires_approval=True)
]

class TrustEnforcer:
    def __init__(self):
        self.policies = DEFAULT_POLICIES

    def evaluate_request(self, agent_id: str, agent_trust_level: int, tool_name: str) -> bool:
        # Find applicable policy
        applicable_policy = None
        for policy in self.policies:
            if tool_name.startswith(policy.tool_prefix):
                applicable_policy = policy
                break
                
        if not applicable_policy:
            # For V1, if no policy matches, we reject. 
            # This ensures we are fail-closed by default.
            audit_logger.log_event("TRUST_REJECT", "gateway", {"agent_id": agent_id, "tool": tool_name, "reason": "No policy matched"})
            return False
            
        if agent_trust_level < applicable_policy.required_trust_level:
            audit_logger.log_event(
                "TRUST_REJECT", 
                "gateway", 
                {"agent_id": agent_id, "tool": tool_name, "reason": "Insufficient trust level", "required": applicable_policy.required_trust_level, "provided": agent_trust_level}
            )
            return False
            
        # If requires_approval is True, the gateway will eventually suspend the LangGraph workflow 
        # and wait for human approval via DBus/UI. For now, we enforce the static level.
        return True

trust_enforcer = TrustEnforcer()
