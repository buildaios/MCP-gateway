import sys
import os
import httpx
from typing import TypedDict, Dict, Any, List

# Ensure phase0 is in path to import v3_engine
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "phase0")))
try:
    from v3_engine import WorkflowState
except ImportError:
    # Fallback if file is moved
    class WorkflowState:
        pass

class LangGraphState(TypedDict):
    data: Dict[str, Any]
    next_step_index: int
    completed_steps: List[str]
    status: str
    is_complete: bool
    run_id: str

def state_to_langgraph(state: 'WorkflowState') -> LangGraphState:
    return {
        "data": state.data,
        "next_step_index": state.next_step_index,
        "completed_steps": state.completed_steps,
        "status": state.status,
        "is_complete": state.is_complete,
        "run_id": state.run_id
    }

def langgraph_to_state(lg_state: LangGraphState) -> 'WorkflowState':
    from v3_engine import WorkflowState
    return WorkflowState(
        data=lg_state.get("data", {}),
        next_step_index=lg_state.get("next_step_index", 0),
        completed_steps=lg_state.get("completed_steps", []),
        status=lg_state.get("status", "RUNNING"),
        is_complete=lg_state.get("is_complete", False),
        run_id=lg_state.get("run_id", "")
    )

class MCPGatewayClient:
    """Client for LangGraph nodes to call out to the MCP Gateway."""
    def __init__(self, gateway_url: str = "http://localhost:8000"):
        self.gateway_url = gateway_url

    async def call_tool(self, agent_id: str, trust_level: int, method: str, params: dict) -> dict:
        async with httpx.AsyncClient() as client:
            headers = {
                "X-Agent-Id": agent_id,
                "X-Agent-Trust-Level": str(trust_level)
            }
            payload = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": "1"
            }
            response = await client.post(f"{self.gateway_url}/mcp", json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
