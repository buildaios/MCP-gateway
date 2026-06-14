from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp_gateway.parser import parse_jsonrpc_request, JSONRPCParseError
from mcp_gateway.config import load_config
from mcp_gateway.router import forward_request

app = FastAPI(title="MCP Gateway Server")

# Load config on startup
backends = []
try:
    backends.extend(load_config("config.yaml"))
    print(f"Loaded {len(backends)} backends from config.")
except Exception as e:
    print(f"Warning during startup: {e}")

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/mcp")
async def mcp_endpoint(request: Request):
    body = await request.body()
    try:
        rpc_request = await parse_jsonrpc_request(body)
    except JSONRPCParseError as e:
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_request", "detail": str(e)}
        )
        
    return await forward_request(rpc_request, backends)
