import sys
from mcp.server.fastmcp import FastMCP
import uvicorn

app = FastMCP("MCP-Gateway")

@app.get("/health")
async def health():
    return {"status": "ok"}

def serve():
    print("Starting MCP Gateway on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    serve()
