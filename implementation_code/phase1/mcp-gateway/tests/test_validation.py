import pytest
from fastapi.testclient import TestClient
from mcp_gateway.server import app, backends, schema_registry
from mcp_gateway.config import Backend

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_env():
    backends.clear()
    backends.extend([
        Backend(name="echo", url="http://echo/mcp", timeout=1),
    ])
    schema_registry.schemas.clear()
    schema_registry.schemas["echo"] = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "count": {"type": "integer"}
        },
        "required": ["text"]
    }

def test_valid_request():
    payload = {
        "jsonrpc": "2.0",
        "method": "echo",
        "params": {"text": "hello"},
        "id": 1
    }
    # Mock routing is expected to fail with 502 since httpx isn't mocked, 
    # but validation happens before routing. If it reaches 502, validation passed.
    response = client.post("/mcp", json=payload)
    assert response.status_code == 502
    assert response.json()["error"] in ["backend_unreachable", "backend_timeout"]

def test_missing_required_field():
    payload = {
        "jsonrpc": "2.0",
        "method": "echo",
        "params": {"count": 1},  # missing 'text'
        "id": 1
    }
    response = client.post("/mcp", json=payload)
    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"
    assert "text" in response.json()["detail"]

def test_wrong_type():
    payload = {
        "jsonrpc": "2.0",
        "method": "echo",
        "params": {"text": "hello", "count": "not_an_int"},
        "id": 1
    }
    response = client.post("/mcp", json=payload)
    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"
    assert "count" in response.json()["detail"]

def test_pass_through_no_schema():
    backends.append(Backend(name="no_schema_tool", url="http://no-schema/mcp"))
    payload = {
        "jsonrpc": "2.0",
        "method": "no_schema_tool",
        "params": {"anything": "goes"},
        "id": 1
    }
    response = client.post("/mcp", json=payload)
    # Validation passes, hits router 502
    assert response.status_code == 502
