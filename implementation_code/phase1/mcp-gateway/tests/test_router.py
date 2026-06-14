import pytest
import httpx
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from mcp_gateway.server import app, backends, schema_registry
from mcp_gateway.config import Backend

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_backends():
    # Inject test backends
    backends.clear()
    backends.extend([
        Backend(name="echo", url="http://echo-server/mcp", prefix="echo", timeout=1),
        Backend(name="github", url="http://github-proxy/mcp", prefix="github", timeout=5)
    ])
    schema_registry.schemas.clear()
    schema_registry.schemas["echo"] = {
        "type": "object", "properties": {"text": {"type": "string"}}
    }
    schema_registry.schemas["github"] = {
        "type": "object"
    }

def test_resolve_exact_name():
    from mcp_gateway.router import resolve_backend
    b = resolve_backend("echo", backends)
    assert b.name == "echo"

def test_resolve_prefix():
    from mcp_gateway.router import resolve_backend
    b = resolve_backend("github.list_repos", backends)
    assert b.name == "github"

def test_resolve_unknown():
    from mcp_gateway.router import resolve_backend, RouterError
    with pytest.raises(RouterError):
        resolve_backend("unknown.tool", backends)

@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
def test_forward_success(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.content = b'{"jsonrpc": "2.0", "result": "hello", "id": 1}'
    mock_post.return_value.headers = {"content-type": "application/json"}
    
    payload = {
        "jsonrpc": "2.0",
        "method": "echo",
        "params": {"text": "hello"},
        "id": 1
    }
    response = client.post("/mcp", json=payload)
    
    assert response.status_code == 200
    assert response.json() == {"jsonrpc": "2.0", "result": "hello", "id": 1}
    mock_post.assert_called_once()
    assert mock_post.call_args[0][0] == "http://echo-server/mcp"

def test_unknown_tool_endpoint():
    payload = {
        "jsonrpc": "2.0",
        "method": "not_a_tool",
        "id": 1
    }
    response = client.post("/mcp", json=payload)
    assert response.status_code == 404
    assert response.json()["error"] == "unknown_tool"

@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
def test_backend_timeout(mock_post):
    mock_post.side_effect = httpx.TimeoutException("timeout")
    
    payload = {
        "jsonrpc": "2.0",
        "method": "github.list",
        "id": 1
    }
    response = client.post("/mcp", json=payload)
    assert response.status_code == 502
    assert response.json()["error"] == "backend_timeout"

@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
def test_backend_unreachable(mock_post):
    mock_request = httpx.Request("POST", "http://github-proxy/mcp")
    mock_post.side_effect = httpx.ConnectError("connection refused", request=mock_request)
    
    payload = {
        "jsonrpc": "2.0",
        "method": "github.list",
        "id": 1
    }
    response = client.post("/mcp", json=payload)
    assert response.status_code == 502
    assert response.json()["error"] == "backend_unreachable"
