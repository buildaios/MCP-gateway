import httpx
import asyncio
from typing import List, Dict, Any
from fastapi.responses import JSONResponse, Response
from mcp_gateway.config import Backend
from mcp_gateway.audit import audit_logger
from mcp_gateway.resilience import resilience_manager

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

async def forward_request(rpc_request: Dict[str, Any], backend: Backend, client: httpx.AsyncClient) -> Response:
    """Forward the JSON-RPC request to the resolved backend with resilience and audit."""
    breaker = resilience_manager.get_breaker(backend)
    
    if not breaker.can_execute():
        audit_logger.log_event("CIRCUIT_BREAKER_REJECT", backend.name, rpc_request, status_code=503)
        return JSONResponse(
            status_code=503,
            content={"error": "service_unavailable", "detail": f"Circuit breaker OPEN for backend {backend.name}"}
        )

    # Exponential backoff retry logic
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            response = await client.post(backend.url, json=rpc_request, timeout=backend.timeout)
            breaker.record_success()
            
            headers = {k: v for k, v in response.headers.items() if k.lower() not in ("content-length", "content-encoding", "transfer-encoding")}
            
            audit_logger.log_event("ROUTING_SUCCESS", backend.name, rpc_request, status_code=response.status_code)
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=headers,
                media_type=response.headers.get("content-type", "application/json")
            )
            
        except (httpx.TimeoutException, httpx.RequestError) as e:
            if attempt < max_attempts - 1:
                await asyncio.sleep(2 ** attempt)
                continue
                
            breaker.record_failure()
            error_type = "backend_timeout" if isinstance(e, httpx.TimeoutException) else "backend_unreachable"
            
            audit_logger.log_event("ROUTING_FAILURE", backend.name, rpc_request, error=str(e))
            
            return JSONResponse(
                status_code=502,
                content={"error": error_type, "detail": f"Failed to connect to backend {backend.name}: {str(e)}"}
            )
