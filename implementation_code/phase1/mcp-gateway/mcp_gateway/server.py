from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import httpx
from mcp_gateway.parser import parse_jsonrpc_request, JSONRPCParseError
from mcp_gateway.config import load_config
from mcp_gateway.router import forward_request, resolve_backend, RouterError
from mcp_gateway.validation import SchemaRegistry, validate_request_params, SchemaValidationError
from mcp_gateway.trust import trust_enforcer
import os

http_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient()
    yield
    await http_client.aclose()

app = FastAPI(title="MCP Gateway Server", lifespan=lifespan)

# Load config on startup
backends = []
try:
    backends.extend(load_config("config.yaml"))
    print(f"Loaded {len(backends)} backends from config.")
except Exception as e:
    print(f"Warning during startup: {e}")

# Load schema registry
SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "schemas")
schema_registry = SchemaRegistry(SCHEMA_DIR)
print(f"Loaded {len(schema_registry.schemas)} schemas from registry.")

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/mcp")
async def mcp_endpoint(request: Request):
    agent_id = request.headers.get("X-Agent-Id", "unknown_agent")
    try:
        agent_trust_level = int(request.headers.get("X-Agent-Trust-Level", "0"))
    except ValueError:
        agent_trust_level = 0
        
    body = await request.body()
    try:
        rpc_request = await parse_jsonrpc_request(body)
    except JSONRPCParseError as e:
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_request", "detail": str(e)}
        )
        
    method = rpc_request.get("method", "")
    try:
        backend = resolve_backend(method, backends)
    except RouterError as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": e.error_code, "detail": e.message}
        )
        
    # Trust Enforcement
    if not trust_enforcer.evaluate_request(agent_id, agent_trust_level, method):
        return JSONResponse(
            status_code=403,
            content={"error": "trust_enforcement_failed", "detail": f"Agent {agent_id} lacks trust level for {method}"}
        )
        
    try:
        validate_request_params(rpc_request, backend, schema_registry)
    except SchemaValidationError as e:
        return JSONResponse(
            status_code=400,
            content={"error": "validation_error", "field": e.field, "detail": e.message}
        )
        
    return await forward_request(rpc_request, backend, http_client)
