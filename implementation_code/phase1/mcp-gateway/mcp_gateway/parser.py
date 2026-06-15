import json
from typing import Any, Dict

class JSONRPCParseError(Exception):
    pass

async def parse_jsonrpc_request(body: bytes) -> Dict[str, Any]:
    if not body:
        raise JSONRPCParseError("invalid JSON")
        
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        raise JSONRPCParseError("invalid JSON")
        
    if not isinstance(data, dict):
        raise JSONRPCParseError("invalid JSON")
        
    if "jsonrpc" not in data or data["jsonrpc"] != "2.0":
        raise JSONRPCParseError("missing jsonrpc version")
        
    if "method" not in data or not isinstance(data["method"], str):
        raise JSONRPCParseError("missing method")
        
    # 'id' is optional for notifications in JSON-RPC 2.0
        
    return data
