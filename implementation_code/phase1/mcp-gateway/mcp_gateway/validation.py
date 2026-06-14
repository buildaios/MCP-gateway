import os
import json
import jsonschema
from typing import Optional
from jsonschema.exceptions import ValidationError
from mcp_gateway.config import Backend

class SchemaValidationError(Exception):
    def __init__(self, message: str, field: str):
        self.message = message
        self.field = field
        super().__init__(self.message)

class SchemaRegistry:
    def __init__(self, schemas_dir: str):
        self.schemas = {}
        self.load_schemas(schemas_dir)

    def load_schemas(self, schemas_dir: str):
        if not os.path.exists(schemas_dir):
            return
            
        for filename in os.listdir(schemas_dir):
            if filename.endswith(".json"):
                backend_name = filename[:-5]
                filepath = os.path.join(schemas_dir, filename)
                try:
                    with open(filepath, "r") as f:
                        self.schemas[backend_name] = json.load(f)
                except Exception as e:
                    print(f"Failed to load schema {filename}: {e}")

    def get_schema(self, backend_name: str) -> Optional[dict]:
        return self.schemas.get(backend_name)

def validate_request_params(rpc_request: dict, backend: Backend, registry: SchemaRegistry):
    schema = registry.get_schema(backend.name)
    if not schema:
        # Pass through if no schema configured
        return
        
    params = rpc_request.get("params", {})
    
    try:
        jsonschema.validate(instance=params, schema=schema)
    except ValidationError as e:
        field = ".".join([str(p) for p in e.path]) if e.path else "root"
        raise SchemaValidationError(f"Validation failed for field '{field}': {e.message}", field)
