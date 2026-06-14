import pytest
from fastapi.testclient import TestClient
from mcp_gateway.server import app

client = TestClient(app)

def test_valid_jsonrpc():
    payload = {
        "jsonrpc": "2.0",
        "method": "echo",
        "params": {"text": "hello"},
        "id": 1
    }
    response = client.post("/mcp", json=payload)
    # The valid request is parsed but 'echo' isn't configured in test backends unless mocked
    # So it should hit the router and return 404 or 502 depending on the backend state
    assert response.status_code != 400

def test_missing_jsonrpc_field():
    payload = {
        "method": "echo",
        "id": 1
    }
    response = client.post("/mcp", json=payload)
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_request"
    assert response.json()["detail"] == "missing jsonrpc version"

def test_missing_method():
    payload = {
        "jsonrpc": "2.0",
        "id": 1
    }
    response = client.post("/mcp", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "missing method"

def test_invalid_json():
    response = client.post("/mcp", content="this is not json")
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid JSON"

def test_missing_id():
    payload = {
        "jsonrpc": "2.0",
        "method": "echo"
    }
    response = client.post("/mcp", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "missing id"
