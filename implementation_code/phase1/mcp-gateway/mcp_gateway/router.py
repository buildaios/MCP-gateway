import httpx
from typing import List, Dict, Any
from fastapi.responses import JSONResponse, Response
from mcp_gateway.config import Backend

class RouterError(Exception):
    def __init__(self, message: str, status_code: int = 500, error_code: str = "internal_error"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(self.message)

def resolve_backend(method: str, backends: List[Backend]) -> Backend:
    """Resolve a method name to a configured backend."""
    # 1. Exact match by backend name
    for backend in backends:
        if backend.name == method:
            return backend
            
    # 2. Prefix match (e.g. 'github.list_repos' matches prefix 'github')
    for backend in backends:
        if backend.prefix and method.startswith(f"{backend.prefix}."):
            return backend
            
    raise RouterError(f"No backend configured for tool: {method}", status_code=404, error_code="unknown_tool")

async def forward_request(rpc_request: Dict[str, Any], backends: List[Backend]) -> Response:
    """Forward the JSON-RPC request to the resolved backend."""
    method = rpc_request.get("method", "")
    
    try:
        backend = resolve_backend(method, backends)
    except RouterError as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": e.error_code, "detail": e.message}
        )
        
    # Forward the request to the backend URL
    try:
        async with httpx.AsyncClient(timeout=backend.timeout) as client:
            # We forward the exact JSON-RPC payload
            response = await client.post(backend.url, json=rpc_request)
            
            # Return the backend response unchanged, filtering out hop-by-hop headers
            headers = {k: v for k, v in response.headers.items() if k.lower() not in ("content-length", "content-encoding", "transfer-encoding")}
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=headers,
                media_type=response.headers.get("content-type", "application/json")
            )
            
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=502,
            content={"error": "backend_timeout", "detail": f"Backend {backend.name} timed out after {backend.timeout}s"}
        )
    except httpx.RequestError as e:
        return JSONResponse(
            status_code=502,
            content={"error": "backend_unreachable", "detail": f"Failed to connect to backend {backend.name}: {str(e)}"}
        )
